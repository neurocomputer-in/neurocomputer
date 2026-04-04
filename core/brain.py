import asyncio, json, os
from core.neuro_factory import NeuroFactory
from core.executor      import Executor
from core.conversation  import Conversation
from core.pubsub        import hub
from core.environment_state import EnvironmentState
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

    # ---------------------------------------------------------------- events
    def add_listener(self, cid, cb):
        self.listeners.setdefault(cid, []).append(cb)

    async def _pub(self, cid, topic, data):
        # publish to websocket hub (skip if suppressed)
        if getattr(self, '_suppress_hub', False):
            print(f"[BRAIN] Skipping hub publish (suppressed): {cid}, topic: {topic}")
            return
        print(f"[BRAIN] Publishing to hub queue: {cid}, topic: {topic}")
        await hub.queue(cid).put({"topic": topic, "data": data})
        print(f"[BRAIN] Published to hub queue successfully: {cid}, topic: {topic}")
        
        # ALSO broadcast via LiveKit DataChannel to handle events without WebSocket
        try:
            from core.chat_handler import chat_manager, ChatMessage
            room = await chat_manager.get_room(cid)
            if room:
                system_msg = ChatMessage(
                    msg_type="system",
                    sender="system",
                    content=topic,
                    metadata=data if isinstance(data, dict) else {"data": data}
                )
                # Fire and forget to not block pub loop
                asyncio.create_task(room.send_to_all(system_msg, topic="system_event"))
        except Exception as e:
            print(f"[BRAIN] Error broadcasting system event to LiveKit: {e}")

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
        conv.add("user", user_text, audio_url=audio_url, is_voice=is_voice)

        # handle profile commands -----------------------------
        cmd = user_text.lower().strip()
        if cmd.startswith("/profile"):
            parts = cmd.split(maxsplit=1)
            if len(parts) == 1:
                return f"Current profile: {self.active_profile.get(cid, 'general')}"
            name = parts[1].strip()
            try:
                self._apply_profile(cid, name)
                return f"switched to profile **{name}**."
            except FileNotFoundError:
                return f"unknown profile '{name}'."

        # compatibility: /dev on | off map to profiles
        if cmd == "/dev on":
            self._apply_profile(cid, "neuro_dev")
            return "neuro-dev profile enabled."
        if cmd == "/dev off":
            self._apply_profile(cid, "general")
            return "Back to general profile."

        # pass the full conversation history instead of just the last 10 turns
        hist = "\n".join(f"{m['sender']}: {m['text']}"
                        for m in conv.history())  # no arg = all messages

        # build a simple neuros list for the LLM
        dev = self.dev_flag.get(cid, False)
        neuros = self.factory.describe(cid) if dev else self.factory.describe()
        neuros_md = "\n".join(f"- **{t['name']}**: {t['desc']}" for t in neuros)

        # ── Initialize/get environment state for ReAct tracking ──────────
        env_state = self.env_states.setdefault(cid, EnvironmentState())
        env_state.current_goal = user_text

        shared_state = {
            "__factory": self.factory,
            "__history":  hist,
            "__neuros_md": neuros_md,
            "__dev": dev_ctx,
            "__env_state": env_state,
            "__env_context": env_state.format_for_prompt(),
        }

        # ── 0.  SMART ROUTER: Unified routing + reply in one call ────────
        # This replaces the old intent_classifier + separate reply flow
        router_out = await self.factory.run(
            "smart_router",
            shared_state,
            history=hist,
            text=user_text,
            skills=neuros_md
        )
        
        action = router_out.get("action", "reply")
        
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
            
            # Publish for voice/UI (only publish once - no executor involved)
            await self._pub(cid, "debug", {"stage": "smart_router", "action": "reply"})
            await self._pub(cid, "assistant", reply_text)
            await self._pub(cid, "node.done", {"neuro": "smart_router", "output": {"reply": reply_text}})
            
            return reply_text
        
        # ── SKILL PATH: Execute a skill ──────────────────────────────────
        if action == "skill":
            skill_name = router_out.get("skill", "")
            skill_params = router_out.get("params", {})
            
            await self._pub(cid, "debug", {"stage": "smart_router", "action": "skill", "skill": skill_name})
            
            # Simple skills that can be executed directly (no planner needed)
            DIRECT_SKILLS = {
                "screen_lock_ubuntu", "unlock_pc", "neuro_list", 
                "screenshot_shortcut", "screenshot_windows",
                "open_file_explorer", "move_mouse_to_center", "move_mouse_top_right"
            }
            
            if skill_name in DIRECT_SKILLS:
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
                    "__planner": planner_name
                }
                exe = Executor(flow, self.factory, state,
                               lambda t, d: self._pub(cid, t, d))
                self.tasks[cid] = (self.loop.create_task(exe.run()), state)
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
                "__planner": planner_name
            }
            await self._pub(cid, "debug", {"stage": "fast_path", "intent": intent})
            exe = Executor(flow, self.factory, state,
                           lambda t, d: self._pub(cid, t, d))
            self.tasks[cid] = (self.loop.create_task(exe.run()), state)
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
                "__planner": planner_name
            }
            await self._pub(cid, "debug", {"stage": "openclaw_delegation", "task": task_text})
            exe = Executor(flow, self.factory, state,
                           lambda t, d: self._pub(cid, t, d))
            self.tasks[cid] = (self.loop.create_task(exe.run()), state)
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
            exe = Executor(flow, self.factory, state,
                           lambda t, d: self._pub(cid, t, d))
            self.tasks[cid] = (self.loop.create_task(exe.run()), state)
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
            exe = Executor(flow, self.factory, state,
                           lambda t, d: self._pub(cid, t, d))
            self.tasks[cid] = (self.loop.create_task(exe.run()), state)
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
                "__planner": planner_name
            }
            print(f"[BRAIN] Creating executor with flow: {flow}")
            exe = Executor(flow, self.factory, state,
                           lambda t, d: self._pub(cid, t, d))
            print(f"[BRAIN] Created task executor, starting execution")
            self.tasks[cid] = (self.loop.create_task(exe.run()), state)
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
