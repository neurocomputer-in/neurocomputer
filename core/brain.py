import asyncio, json, os
from core.neuro_factory import NeuroFactory
# core.executor retired in Phase F; execution routes through
# factory.run("dag_flow", state, dag=flow) — see docs spec 01-core.
from core.conversation  import Conversation
from core.pubsub        import hub
from core.environment_state import EnvironmentState
from core.llm_registry import get_default_llm_settings, get_provider_catalog, normalize_provider
from core import model_library
import json

import os, json

class Brain:
    def __init__(self, factory=None):
        
        self.factory   = factory or NeuroFactory()
        self.loop      = asyncio.get_event_loop()
        self.listeners = {}
        self.tasks     = {}
        self.convs     = {}
        self.dev_ctx        = {}
        self.active_profile = {}   # cid → profile name
        self.profile_cfg    = {}   # cid → loaded config
        self.dev_flag       = {}   # cid → is-dev-mode?
        self.env_states     = {}   # cid → EnvironmentState for ReAct tracking
        self.llm_settings   = {}   # cid → {"provider": ..., "model": ...}

    # ---------------------------------------------------------------- task mgmt
    def _launch(self, cid, flow, state):
        """Create a background task running the given DAG through DagFlow."""
        state["__pub"] = lambda t, d, _cid=cid: self._pub(_cid, t, d)
        task = self.loop.create_task(
            self.factory.run("dag_flow", state, dag=flow)
        )
        task.add_done_callback(lambda t, c=cid: self._on_task_done(c, t))
        self.tasks[cid] = (task, state)

    def _on_task_done(self, cid: str, task: asyncio.Task):
        """Last-resort callback: surface exceptions that escaped the executor."""
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            print(f"[BRAIN] Background task for {cid} failed: {exc}")
            async def _notify():
                try:
                    await self._pub(cid, "assistant",
                                    f"⚠️ Internal error: {exc}")
                    await self._pub(cid, "task.done", {"error": str(exc)})
                except Exception:
                    pass
            try:
                self.loop.create_task(_notify())
            except RuntimeError:
                pass  # loop closed

    # ---------------------------------------------------------------- events
    def add_listener(self, cid, cb):
        self.listeners.setdefault(cid, []).append(cb)

    async def _pub(self, cid, topic, data, *, _dc_chat=True):
        """Publish event to hub queue and LiveKit DataChannel.

        _dc_chat: when True AND topic=="assistant", also send as an
                  agent_response DataChannel message (chat bubble).
                  Set to False when the caller already handles DataChannel
                  delivery (e.g. fast-path replies sent by chat_handler).
        """
        # publish to websocket hub (skip if suppressed, but continue to LiveKit)
        if getattr(self, '_suppress_hub', False):
            print(f"[BRAIN] Skipping hub publish (suppressed): {cid}, topic: {topic}")
        else:
            print(f"[BRAIN] Publishing to hub queue: {cid}, topic: {topic}")
            await hub.queue(cid).put({"topic": topic, "data": data})
            print(f"[BRAIN] Published to hub queue successfully: {cid}, topic: {topic}")

        # ALSO broadcast via LiveKit DataChannel to handle events without WebSocket
        # Skip during voice calls — voice pipeline handles its own delivery
        if getattr(self, '_suppress_dc', False):
            return
        try:
            from core.chat_handler import chat_manager, ChatMessage
            from core.db import db
            room = await chat_manager.get_room(cid)
            if room:
                # "assistant" messages are actual chat replies — send as agent_response
                # so the mobile app displays them as chat bubbles
                if _dc_chat and topic == "assistant" and isinstance(data, str) and data.strip():
                    agent_msg = ChatMessage(
                        msg_type="text",
                        sender="agent",
                        content=data,
                    )
                    await db.add_message_with_id(
                        message_id=agent_msg.id,
                        conversation_id=cid,
                        sender="agent",
                        msg_type="text",
                        content=data,
                    )
                    asyncio.create_task(room.send_to_all(agent_msg, topic="agent_response"))
                else:
                    system_msg = ChatMessage(
                        msg_type="system",
                        sender="system",
                        content=topic,
                        metadata=data if isinstance(data, dict) else {"data": data}
                    )
                    # Fire and forget to not block pub loop
                    asyncio.create_task(room.send_to_all(system_msg, topic="system_event"))
        except Exception as e:
            print(f"[BRAIN] Error broadcasting to LiveKit: {e}")

        for cb in self.listeners.get(cid, []):
            print(f"[BRAIN] Calling listener callback for: {cid}")
            await cb(topic, data)

  

    def _profile_cfg(self, cid):
        # first time: default to “general”
        if cid not in self.active_profile:
            self.active_profile[cid] = "general"
        name = self.active_profile[cid]
        # cache load
        if cid not in self.profile_cfg:
            path = os.path.join("profiles", f"{name}.json")
            if not os.path.exists(path):
                raise FileNotFoundError(f"Profile '{name}' not found")
            with open(path, "r", encoding="utf-8") as f:
                self.profile_cfg[cid] = json.load(f)

        # ↳ restrict visible neuros for this conversation
        self.factory.set_pattern(
            cid,
            self.profile_cfg[cid].get("neuros", ["*"])
        )
        return self.profile_cfg[cid]

    def _apply_profile(self, cid, name):
        # validate & reload
        path = os.path.join("profiles", f"{name}.json")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Profile '{name}' not found")
        with open(path, "r", encoding="utf-8") as f:
            self.profile_cfg[cid]    = json.load(f)
        self.active_profile[cid] = name
        # turn on “dev” neuros if we’re in neuro_dev (or code_dev) profile
        self.dev_flag[cid] = (name in ("neuro_dev", "code_dev"))

        # ↳ apply neuro filtering for the new profile
        self.factory.set_pattern(
            cid,
            self.profile_cfg[cid].get("neuros", ["*"])
        )

    def _get_llm_settings(self, cid, conv: Conversation | None = None):
        # Precedence (highest → lowest):
        #   1. Session role — explicit /role PATCH wins over raw pick. Resolved
        #      each call so library edits (repin, rename) apply without restart.
        #   2. Raw pick — persisted llm_settings on the conv. Explicit
        #      selection_type="raw" OR inferred when provider+model exist and
        #      no session_role is set. Covers pre-fix convs lacking the flag.
        #   3. Default.
        stored_selection = conv.get_selection_type() if conv is not None else None
        session_role = conv.get_session_role() if conv is not None else None

        # Role wins only when it was the most recent explicit choice. If the
        # user later set a raw pick, selection_type="raw" flips precedence
        # back to the raw branch even if a stale session_role lingers.
        if session_role and stored_selection != "raw":
            resolved = model_library.resolve_role(session_role)
            if resolved:
                out = dict(resolved)
                out["selection_type"] = "role"
                self.llm_settings[cid] = dict(out)
                return dict(out)

        saved = conv.get_llm_settings() if conv is not None else {}
        if saved.get("provider") and saved.get("model"):
            out = {
                "provider": normalize_provider(saved["provider"]),
                "model": saved["model"],
                "selection_type": stored_selection or "raw",
            }
            self.llm_settings[cid] = dict(out)
            return dict(out)

        if cid not in self.llm_settings:
            base = get_default_llm_settings()
            base["selection_type"] = None
            self.llm_settings[cid] = base
        return dict(self.llm_settings[cid])

    def _set_llm_settings(self, cid, conv: Conversation, provider=None, model=None):
        current = self._get_llm_settings(cid, conv)
        if provider is not None:
            current["provider"] = normalize_provider(provider)
        if model is not None:
            current["model"] = model.strip()
        self.llm_settings[cid] = current
        conv.set_llm_settings(current["provider"], current["model"])
        return dict(current)

    def _format_llm_status(self, settings):
        return f"LLM provider: `{settings['provider']}`\nLLM model: `{settings['model']}`"

    async def _handle_llm_command(self, cid, conv: Conversation, user_text: str):
        parts = user_text.strip().split()
        if not parts:
            return None

        cmd = parts[0].lower()
        if cmd not in ("/llm", "/provider", "/model"):
            return None

        current = self._get_llm_settings(cid, conv)
        providers = get_provider_catalog()
        provider_names = ", ".join(p["id"] for p in providers)

        if cmd == "/provider":
            if len(parts) == 1:
                return f"Current provider: `{current['provider']}`\nAvailable providers: {provider_names}"
            updated = self._set_llm_settings(cid, conv, provider=parts[1])
            return f"Switched provider to `{updated['provider']}`.\nCurrent model: `{updated['model']}`"

        if cmd == "/model":
            if len(parts) == 1:
                return f"Current model: `{current['model']}`"
            updated = self._set_llm_settings(cid, conv, model=" ".join(parts[1:]))
            return f"Switched model to `{updated['model']}` on `{updated['provider']}`."

        if len(parts) == 1 or parts[1].lower() in ("status", "show"):
            return self._format_llm_status(current)

        if parts[1].lower() == "providers":
            lines = []
            for provider in providers:
                availability = "configured" if provider["available"] else f"missing {provider['envKey']}"
                lines.append(
                    f"- `{provider['id']}`: default `{provider['defaultModel']}`, {availability}"
                )
            return "Available providers:\n" + "\n".join(lines)

        if parts[1].lower() == "models":
            provider = current["provider"]
            if len(parts) > 2:
                provider = normalize_provider(parts[2])
            provider_cfg = next((p for p in providers if p["id"] == provider), None)
            if not provider_cfg:
                return f"Unknown provider `{provider}`."
            models = "\n".join(f"- `{model}`" for model in provider_cfg["models"])
            return f"Models for `{provider}`:\n{models}"

        provider = parts[1] if len(parts) > 1 else None
        model = " ".join(parts[2:]) if len(parts) > 2 else None
        updated = self._set_llm_settings(cid, conv, provider=provider, model=model)
        return self._format_llm_status(updated)

    async def handle(self, cid: str, user_text: str, agent_id: str = None, publish_to_hub: bool = True, audio_url: str = None, is_voice: bool = False) -> str:
        dev_ctx = self.dev_ctx.setdefault(cid, {})
        # ensure we have a profile
        cfg = self._profile_cfg(cid)

        # ------------------------------------------------------------------
        # Names the active profile wants to use.  We **must** fetch them
        # before any early-return paths (e.g. greeting/small-talk fast-path)
        # to avoid UnboundLocalError.
        # ------------------------------------------------------------------
        planner_name  = cfg.get("planner", "planner")
        replier_neuro = cfg.get("replier", "reply")

        # 1. persist user message
        if cid in self.convs:
            conv = self.convs[cid]
            # Set agent_id if not already set
            if agent_id and not conv.agent_id:
                conv.set_agent_id(agent_id)
        else:
            conv = Conversation(cid, agent_id=agent_id)
            self.convs[cid] = conv
        llm_settings = self._get_llm_settings(cid, conv)
        print(f"[BRAIN] Using LLM provider={llm_settings['provider']} model={llm_settings['model']} selection_type={llm_settings.get('selection_type')} for cid={cid}")
        conv.add("user", user_text, audio_url=audio_url, is_voice=is_voice)

        # handle profile commands -----------------------------
        cmd = user_text.lower().strip()
        llm_reply = await self._handle_llm_command(cid, conv, user_text)
        if llm_reply:
            await self._pub(cid, "assistant", llm_reply)
            return llm_reply

        if cmd.startswith("/profile"):
            parts = cmd.split(maxsplit=1)
            if len(parts) == 1:
                reply = f"Current profile: {self.active_profile.get(cid, 'general')}"
                await self._pub(cid, "assistant", reply)
                return reply
            name = parts[1].strip()
            try:
                self._apply_profile(cid, name)
                reply = f"switched to profile **{name}**."
                await self._pub(cid, "assistant", reply)
                return reply
            except FileNotFoundError:
                reply = f"unknown profile '{name}'."
                await self._pub(cid, "assistant", reply)
                return reply

        # compatibility: /dev on | off map to profiles
        if cmd == "/dev on":
            self._apply_profile(cid, "neuro_dev")
            reply = "neuro-dev profile enabled."
            await self._pub(cid, "assistant", reply)
            return reply
        if cmd == "/dev off":
            self._apply_profile(cid, "general")
            reply = "Back to general profile."
            await self._pub(cid, "assistant", reply)
            return reply

        # ── workflow / agent slash commands ─────────────────────────────
        # Prefer routing through agent neuros (kind=agent) when they exist,
        # so memory is partitioned by agent's memory_scope. Fall back to the
        # raw workflow neuro when no matching agent is registered.
        #
        # /advisor <msg>  → agent_default (default_workflow=advisor)
        # /coder <msg>    → agent_coder   (default_workflow=coder)
        # /agent_<x> <msg>→ agent_<x> directly
        WORKFLOW_TO_AGENT = {
            "advisor": "agent_default",
            "coder":   "agent_coder",
        }
        workflow_name = None
        dispatch_target = None     # the neuro we'll actually invoke
        dispatch_params = None     # its kwargs
        if cmd.startswith("/"):
            first, _, rest = user_text.strip().partition(" ")
            key = first.lstrip("/").lower()
            payload = rest.strip()

            if key.startswith("agent_"):
                # Direct agent dispatch
                if key in self.factory.reg:
                    dispatch_target = key
                    workflow_name = key
                    dispatch_params = {"user_text": payload}
            elif key in WORKFLOW_TO_AGENT:
                # Workflow shortcut → route via mapped agent if present,
                # else fall back to the raw workflow neuro.
                mapped_agent = WORKFLOW_TO_AGENT[key]
                if mapped_agent in self.factory.reg:
                    dispatch_target = mapped_agent
                    workflow_name = mapped_agent
                    dispatch_params = {"user_text": payload}
                elif key in self.factory.reg:
                    dispatch_target = key
                    workflow_name = key
                    dispatch_params = {"user_question": payload}

            if dispatch_target is not None:
                if not payload:
                    reply = f"usage: /{key} <your message>"
                    await self._pub(cid, "assistant", reply)
                    return reply
                flow = {
                    "start": "n0",
                    "nodes": {
                        "n0": {
                            "neuro":  dispatch_target,
                            "params": dispatch_params,
                            "next":   None,
                        }
                    },
                }
                state = {
                    "goal":               payload,
                    "user_question":      payload,
                    "user_text":          payload,
                    "__factory":          self.factory,
                    "__conv":             conv,
                    "__cid":              cid,
                    "__agent_id":         agent_id or "neuro",
                    "__dev":              dev_ctx,
                    "__llm_provider":     llm_settings["provider"],
                    "__llm_model":        llm_settings["model"],
                    "__llm_selection_type": llm_settings.get("selection_type"),
                }
                await self._pub(cid, "debug",
                                {"stage":     "workflow",
                                 "workflow":  workflow_name,
                                 "target":    dispatch_target,
                                 "invoked":   key})
                self._launch(cid, flow, state)
                return f"🧠 {dispatch_target} is on it"

        from core.context import build_router_context, build_skills_compact, format_messages_full

        # Build neuros list
        dev = self.dev_flag.get(cid, False)
        neuros = self.factory.describe(cid) if dev else self.factory.describe()
        neuros_md = "\n".join(f"- **{t['name']}**: {t['desc']}" for t in neuros)

        # Build context for router (compact — only last 5 messages)
        router_ctx = build_router_context(conv, neuros)

        # Full history still needed for planner/executor fallback
        hist = format_messages_full(conv.history())

        # ── Initialize/get environment state for ReAct tracking ──────────
        env_state = self.env_states.setdefault(cid, EnvironmentState())
        env_state.current_goal = user_text

        shared_state = {
            "__factory": self.factory,
            "__history":  hist,
            "__neuros_md": neuros_md,
            "__conv": conv,
            "__cid": cid,
            "__dev": dev_ctx,
            "__env_state": env_state,
            "__env_context": env_state.format_for_prompt(),
            "__llm_provider": llm_settings["provider"],
            "__llm_model": llm_settings["model"],
            "__llm_selection_type": llm_settings.get("selection_type"),
        }

        # ── AGENT DELEGATION: bypass router when a specific agent is selected ─
        AGENT_DELEGATES = {
            "openclaw": "openclaw_delegate",
            "opencode": "opencode_delegate",
        }
        effective_agent = agent_id or "neuro"
        # Match both exact type ("openclaw") and instance IDs ("openclaw_abc12345")
        agent_type = effective_agent.split("_")[0] if "_" in effective_agent else effective_agent
        delegate_neuro = AGENT_DELEGATES.get(effective_agent) or AGENT_DELEGATES.get(agent_type)
        print(f"[BRAIN] agent_id={agent_id!r}, effective_agent={effective_agent!r}, agent_type={agent_type!r}, delegate={delegate_neuro!r}")

        if delegate_neuro:
            flow = {
                "start": "n0",
                "nodes": {
                    "n0": {
                        "neuro": delegate_neuro,
                        "params": {"task": user_text, "session_id": cid},
                        "next": None,
                    }
                },
            }
            state = {
                "goal": user_text,
                "__factory": self.factory,
                "__history": hist,
                "__conv": conv,
                "__cid": cid,
                "__dev": dev_ctx,
                "__planner": planner_name,
                "__llm_provider": llm_settings["provider"],
                "__llm_model": llm_settings["model"],
                "__llm_selection_type": llm_settings.get("selection_type"),
            }
            await self._pub(cid, "debug", {"stage": "agent_delegate", "agent": effective_agent, "neuro": delegate_neuro})
            self._launch(cid, flow, state)
            return f"🚀 {effective_agent} is on it"

        # ── 0.  SMART ROUTER: Unified routing + reply in one call ────────
        # This replaces the old intent_classifier + separate reply flow
        print(f"[BRAIN] Calling smart_router for: {user_text[:60]}")
        router_out = await self.factory.run(
            "smart_router",
            shared_state,
            history=router_ctx["history"],
            text=user_text,
            skills=router_ctx["skills"],
        )

        action = router_out.get("action", "reply")
        print(f"[BRAIN] Router returned: action={action}, skill={router_out.get('skill')}")
        await self._pub(cid, "debug", {
            "stage": "router",
            "action": action,
            "skill": router_out.get("skill"),
            "rationale": str(router_out.get("reply", ""))[:100] if action == "reply" else f"Invoking {router_out.get('skill')}",
        })
        
        # ── Handle profile toggle commands (these are detected in router) ──
        # Check for profile-related keywords in user text
        cmd = user_text.lower().strip()
        current_profile = self.active_profile.get(cid, "code_dev")
        
        # Profile commands - handle before smart router decision
        if "/dev on" in cmd or "enable dev mode" in cmd:
            self._apply_profile(cid, "neuro_dev")
            reply = "neuro-dev profile enabled."
            conv.add("assistant", reply)
            return reply
        if "/dev off" in cmd or "disable dev mode" in cmd:
            self._apply_profile(cid, "code_dev")
            reply = "Switched to code-dev profile."
            conv.add("assistant", reply)
            return reply
        
        # ── FAST PATH: Direct reply (no skill needed) ────────────────────
        if action == "reply":
            reply_text = router_out.get("reply", "I'm not sure how to respond.")
            conv.add("assistant", reply_text)
            
            # Publish for voice/UI — _pub sends via DataChannel too
            await self._pub(cid, "debug", {"stage": "smart_router", "action": "reply"})
            await self._pub(cid, "assistant", reply_text)
            await self._pub(cid, "node.done", {"neuro": "smart_router", "output": {"reply": reply_text}})
            
            return reply_text
        
        # ── SKILL PATH: Execute a skill ──────────────────────────────────
        if action == "skill":
            skill_name = router_out.get("skill", "")
            skill_params = router_out.get("params", {})
            print(f"[BRAIN] Skill path: {skill_name}, params={skill_params}")

            await self._pub(cid, "debug", {"stage": "smart_router", "action": "skill", "skill": skill_name})
            print(f"[BRAIN] Published debug event for skill {skill_name}")
            
            # Simple skills that can be executed directly (no planner needed)
            DIRECT_SKILLS = {
                "screen_lock_ubuntu", "unlock_pc", "neuro_list",
                "screenshot_shortcut", "screenshot_windows",
                "open_file_explorer", "move_mouse_to_center", "move_mouse_top_right",
                "openclaw_delegate",
                "advisor", "coder",             # workflow neuros (auto-route)
            }

            # Remap workflow picks to agent neuros when available,
            # so memory partitioning kicks in transparently.
            _WORKFLOW_TO_AGENT = {
                "advisor": "agent_default",
                "coder":   "agent_coder",
            }
            if skill_name in _WORKFLOW_TO_AGENT:
                agent_candidate = _WORKFLOW_TO_AGENT[skill_name]
                if agent_candidate in self.factory.reg:
                    skill_name = agent_candidate
                    skill_params = {"user_text": user_text}

            if skill_name in DIRECT_SKILLS or skill_name.startswith("agent_"):
                # Ensure openclaw_delegate always gets session_id
                if skill_name == "openclaw_delegate":
                    skill_params.setdefault("session_id", cid)
                    skill_params.setdefault("task", user_text)
                # Workflow neuros expect user_question; fall back to user_text
                # if smart_router didn't include it in params.
                if skill_name in ("advisor", "coder"):
                    skill_params.setdefault("user_question", user_text)
                flow = {
                    "start": "n0",
                    "nodes": {
                        "n0": {
                            "neuro": skill_name,
                            "params": skill_params,
                            "next": None
                        }
                    }
                }
                state = {
                    "goal": user_text,
                    "__factory": self.factory,
                    "__history": hist,
                    "__conv": conv,
                    "__cid": cid,
                    "__dev": dev_ctx,
                    "__planner": planner_name,
                    "__llm_provider": llm_settings["provider"],
                    "__llm_model": llm_settings["model"],
                    "__llm_selection_type": llm_settings.get("selection_type"),
                }
                self._launch(cid, flow, state)
                return "🚀 task started"

            # Complex skills go to the planner for multi-step execution
            # Fall through to planner section below
            intent = "code_request"  # Hint for planner
        else:
            intent = "generic"
        
        # ── LEGACY INTENT HANDLING (for backwards compatibility) ──────────
        # These are now mostly handled by smart_router, but kept as fallback
        
        # ── Handle capability queries directly ───────────────────────────
        if intent == "capability_query":
            flow = {
                "start": "n0",
                "nodes": {
                    "n0": {
                        "neuro": "neuro_list",
                        "params": {},
                        "next": None
                    }
                }
            }
            state = {
                "goal": user_text,
                "__factory": self.factory,
                "__history": hist,
                "__conv": conv,
                "__cid": cid,
                "__dev": dev_ctx,
                "__planner": planner_name,
                "__llm_provider": llm_settings["provider"],
                "__llm_model": llm_settings["model"],
                "__llm_selection_type": llm_settings.get("selection_type"),
            }
            await self._pub(cid, "debug", {"stage": "fast_path", "intent": intent})
            self._launch(cid, flow, state)
            return "🚀 task started"
        
        # ── Handle OpenClaw delegation requests ──────────────────────────
        if intent == "openclaw_request":
            # Extract the actual task from user_text by removing trigger words
            task_text = user_text
            for trigger in ["ask openclaw", "let openclaw", "openclaw", "delegate to openclaw", "give hook to"]:
                task_text = task_text.lower().replace(trigger, "").strip()
            
            # Use original text if cleaning removed everything
            if not task_text or len(task_text) < 3:
                task_text = user_text
            
            flow = {
                "start": "n0",
                "nodes": {
                    "n0": {
                        "neuro": "openclaw_delegate",
                        "params": {"task": task_text, "session_id": cid},
                        "next": None
                    }
                }
            }
            state = {
                "goal": user_text,
                "__factory": self.factory,
                "__history": hist,
                "__conv": conv,
                "__cid": cid,
                "__dev": dev_ctx,
                "__planner": planner_name,
                "__llm_provider": llm_settings["provider"],
                "__llm_model": llm_settings["model"],
                "__llm_selection_type": llm_settings.get("selection_type"),
            }
            await self._pub(cid, "debug", {"stage": "openclaw_delegation", "task": task_text})
            self._launch(cid, flow, state)
            return "🚀 task started"

        if intent == "unlock_request":
            flow = {
                "start": "n0",
                "nodes": {
                    "n0": {
                        "neuro": "unlock_pc",
                        "params": {},
                        "next": None
                    }
                }
            }
            state = {
                "goal": user_text,
                "__factory": self.factory,
                "__history": hist,
                "__conv": conv,
                "__cid": cid,
                "__dev": dev_ctx,
                "__planner": planner_name
            }
            await self._pub(cid, "debug", {"stage": "unlock_pc"})
            self._launch(cid, flow, state)
            return "🚀 unlocking..."

        # ── Handle Lock PC requests ────────────────────────────────────
        if intent == "lock_request":
            flow = {
                "start": "n0",
                "nodes": {
                    "n0": {
                        "neuro": "screen_lock_ubuntu",
                        "params": {},
                        "next": None
                    }
                }
            }
            state = {
                "goal": user_text,
                "__factory": self.factory,
                "__history": hist,
                "__conv": conv,
                "__cid": cid,
                "__dev": dev_ctx,
                "__planner": planner_name
            }
            await self._pub(cid, "debug", {"stage": "lock_pc"})
            self._launch(cid, flow, state)
            return "🚀 locking..."

        # 2. ask the (dev_)planner for a task-flow (for code_request, file_op, etc.)
        cat           = self.factory.catalogue(cid)
        plan = (await self.factory.run(
            planner_name, shared_state,
            goal=user_text,
            catalogue=cat,
            intent=intent)              # ← pass hint to planner
        )["plan"]
        await self._pub(cid, "debug", {"stage": "plan", "plan": plan})

        # ─────────────────────────────────────────────────────────
        # Some planners mistakenly wrap their real status one level
        # deeper, e.g.  {ok:true, flow:{ok:false, …}}.  Detect and
        # unwrap so the normal "missing / question" branches fire.
        # ─────────────────────────────────────────────────────────
        if (
            plan.get("ok") is True
            and isinstance(plan.get("flow"), dict)
            and plan["flow"].get("ok") is False
        ):
            plan = plan["flow"]          # unwrap one level

        # ── ACCEPT *bare* flows when planner forgets "ok/flow" wrapper ──
        if "ok" not in plan or "flow" not in plan:
            plan = {
                "ok":       True,
                "flow":     plan,       # treat the object itself as the flow
                "missing":  [],
                "question": None,
            }

        # ── NORMALISE short-form flows (strings / {type:name}) ────────────
        if plan.get("ok"):
            flow_data = plan.get("flow")
            def _wrap(neuro, params=None):
                return {
                    "start": "n0",
                    "nodes": {
                        "n0": {
                            "neuro": neuro,
                            "params": params or {},
                            "next": None
                        }
                    }
                }

            # plain string → single node
            if isinstance(flow_data, str):
                if flow_data == "reply":
                    plan["flow"] = _wrap(replier_neuro, {"text": user_text})
                else:
                    plan["flow"] = _wrap(flow_data)

            # short‐form dict → either {type:…} or {name:…,params:…}
            elif isinstance(flow_data, dict):
                # { "type":"reply" }
                if flow_data.get("type") == "reply":
                    plan["flow"] = _wrap(replier_neuro, {"text": user_text})
                # { "name":"neuro", "params":{…} }
                elif "name" in flow_data:
                    name   = flow_data["name"]
                    params = flow_data.get("params", {})
                    plan["flow"] = _wrap(name, params)
                # else: assume it's already a full DAG, leave it



        # 3. handle clarification / missing neuros
        if not plan.get("ok"):
            if plan.get("question"):
                conv.add("assistant", plan["question"])
                return plan["question"]
            if plan.get("missing"):
                miss = [m for m in plan["missing"]
                        if m not in self.factory.catalogue()]
                if miss:
                    msg = f"⚠️ missing neuro(s): {', '.join(miss)}."
                    conv.add("assistant", msg)
                    return msg

        # 4. if planner gave us a valid flow, run it (even single-node short-form)
        flow = plan.get("flow")
        if plan.get("ok") and isinstance(flow, dict) and "start" in flow and "nodes" in flow:
            # executor will read __planner when it needs to re-plan
            state = {
                "goal":      user_text,
                "__factory": self.factory,
                "__history": hist,
                "__conv":    conv,
                "__cid":     cid,          # Make cid available to executor
                "__dev":     dev_ctx,
                "__planner": planner_name,
                "__llm_provider": llm_settings["provider"],
                "__llm_model": llm_settings["model"],
                "__llm_selection_type": llm_settings.get("selection_type"),
            }
            print(f"[BRAIN] Creating executor with flow: {flow}")
            print(f"[BRAIN] Launching dag_flow for flow")
            self._launch(cid, flow, state)
            print(f"[BRAIN] Created task and stored in tasks dictionary")
            await self._pub(cid, "debug", {"stage": "execute"})
            print(f"[BRAIN] Published debug event, returning task started message")
            return "🚀 task started"

        # 5. planner "junk" fall-through
        junk = (
            "⚠️ Planner produced an invalid flow:\n"
            f"{json.dumps(plan, indent=2)}"
        )
        return junk
