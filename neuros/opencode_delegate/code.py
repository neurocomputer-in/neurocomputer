"""
OpenCode Delegate Neuro

Consumes opencode's /global/event SSE stream via a shared SSEConsumer.
Per-session asyncio.Lock + idle gate serializes concurrent user turns so
rapid follow-up messages don't get silently dropped by opencode.
"""
from __future__ import annotations

import asyncio
import json
import os
from typing import Callable, Optional
from uuid import uuid4

import aiohttp

from neuros.opencode_delegate.sse_consumer import SSEConsumer, SessionBus

OPENCODE_SERVER_URL = os.getenv("OPENCODE_SERVER_URL", "http://127.0.0.1:14096").rstrip("/")
_PROJECT_ROOT = os.getcwd()
_SESSION_MAP_PATH = os.path.join(_PROJECT_ROOT, "data", "opencode_sessions.json")

_TURN_TIMEOUT = 300.0
_POST_TIMEOUT = 300.0   # opencode holds POST open for the full turn; closing
                        # early aborts processing on the server side.
_POST_GRACE_AFTER_SSE = 30.0  # after SSE says finish=stop, how long to wait
                              # for POST to fully return before moving on.
_FINISH_TERMINAL = {"stop", "length", "error", "cancelled"}
_HEARTBEAT_INTERVAL = 3.0  # emit opencode.heartbeat every N seconds during
                           # a turn so the UI keeps its streaming/thinking
                           # state alive during long reasoning-only stretches.
_REASONING_THROTTLE = 1.5  # min seconds between opencode.reasoning events
                           # (reasoning deltas can fire many times per second;
                           # throttle to avoid flooding the data channel).

# Opencode v1.4.6 has an undocumented behavior: once a POST /session/{id}/message
# returns cleanly (body fully delivered), subsequent POSTs to the same session
# are no-ops — opencode returns the previous assistant message body instantly
# without running the model. Reproducing cleanly with both curl and aiohttp.
# Workaround: create a FRESH opencode session per user turn. We trade opencode-
# level conversation continuity for reliability; continuity is preserved at the
# NeuroComputer layer by prepending recent chat history into the task text.
_FRESH_SESSION_PER_TURN = True
_HISTORY_MAX_CHARS = 4000
_HISTORY_MAX_MESSAGES = 12


# ── session-map persistence (unchanged behaviour) ─────────────────────

def _load_sessions() -> dict:
    try:
        with open(_SESSION_MAP_PATH, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_sessions(sessions: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_SESSION_MAP_PATH), exist_ok=True)
        with open(_SESSION_MAP_PATH, "w") as f:
            json.dump(sessions, f)
    except Exception:
        pass


_sessions_cache: dict[str, str] | None = None


def _get_sessions() -> dict:
    global _sessions_cache
    if _sessions_cache is None:
        _sessions_cache = _load_sessions()
    return _sessions_cache


def _get_conv_workdir(cid: str) -> Optional[str]:
    try:
        conv_path = os.path.join(_PROJECT_ROOT, "conversations", f"{cid}.json")
        with open(conv_path) as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("workdir")
    except Exception:
        pass
    return None


def _build_history_prefix(cid: str, exclude_last_user: bool = True) -> str:
    """Read recent messages from the conversation JSON and format them as a
    context prefix. Caps by count and total chars so we never blow up prompts.
    Excludes the most recent user message (that's the current turn's task)."""
    try:
        conv_path = os.path.join(_PROJECT_ROOT, "conversations", f"{cid}.json")
        with open(conv_path) as f:
            data = json.load(f)
    except Exception:
        return ""
    msgs = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(msgs, list) or not msgs:
        return ""
    history = list(msgs)
    if exclude_last_user and history and history[-1].get("sender") == "user":
        history.pop()
    history = history[-_HISTORY_MAX_MESSAGES:]
    lines: list[str] = []
    for m in history:
        sender = m.get("sender", "").lower()
        text = (m.get("text") or "").strip()
        if not text:
            continue
        role = "User" if sender == "user" else "Assistant"
        lines.append(f"{role}: {text}")
    if not lines:
        return ""
    prefix = "\n".join(lines)
    if len(prefix) > _HISTORY_MAX_CHARS:
        prefix = prefix[-_HISTORY_MAX_CHARS:]
    return prefix


async def _ensure_server() -> bool:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OPENCODE_SERVER_URL}/global/health",
                             timeout=aiohttp.ClientTimeout(total=3)) as r:
                return r.status == 200
    except Exception:
        return False


async def _create_fresh_session(cid: str) -> str:
    """Create a new opencode session. With _FRESH_SESSION_PER_TURN, we never
    reuse one — opencode v1.4.6 drops the 2nd+ POST on any session whose first
    turn completed cleanly."""
    workdir = _get_conv_workdir(cid)
    import time as _t
    payload: dict = {"title": f"neuro-{cid[:8]}-{int(_t.time())}"}
    if workdir:
        payload["cwd"] = workdir
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{OPENCODE_SERVER_URL}/session", json=payload,
                          timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
    return data["id"]


async def _get_or_create_session(cid: str) -> str:
    if _FRESH_SESSION_PER_TURN:
        return await _create_fresh_session(cid)

    sessions = _get_sessions()
    if cid in sessions:
        existing = sessions[cid]
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{OPENCODE_SERVER_URL}/session/{existing}",
                                 timeout=aiohttp.ClientTimeout(total=5)) as r:
                    if r.status == 200:
                        return existing
        except Exception:
            pass
        del sessions[cid]

    sid = await _create_fresh_session(cid)
    sessions[cid] = sid
    _save_sessions(sessions)
    return sid


# ── Shared SSE consumer (process-wide singleton) ──────────────────────

_consumer: SSEConsumer | None = None
_consumer_lock = asyncio.Lock()


async def _get_consumer() -> SSEConsumer:
    global _consumer
    async with _consumer_lock:
        if _consumer is None or _consumer._base_url != OPENCODE_SERVER_URL:
            if _consumer is not None:
                await _consumer.stop()
            _consumer = SSEConsumer(OPENCODE_SERVER_URL)
            await _consumer.start()
        return _consumer


# Per-conversation-id lock: serializes turns for the same UI conversation so
# replies stay in order, even when each turn uses a fresh opencode session.
_cid_locks: dict[str, asyncio.Lock] = {}
_cid_locks_mu = asyncio.Lock()


async def _get_cid_lock(cid: str) -> asyncio.Lock:
    async with _cid_locks_mu:
        lock = _cid_locks.get(cid)
        if lock is None:
            lock = asyncio.Lock()
            _cid_locks[cid] = lock
        return lock


# ── Event dispatch for one turn ───────────────────────────────────────

async def _consume_turn(
    bus: SessionBus,
    my_msg_id: str,
    on_text,
    on_tool,
    on_step,
    on_reasoning=None,
) -> dict:
    """Consume events from the bus until our turn completes. Returns
    {'text': str, 'error': str | None}."""
    accumulated: list[str] = []
    my_message_ids: set[str] = set()
    error_text: str | None = None
    last_reasoning_emit = 0.0

    loop = asyncio.get_event_loop()
    deadline = loop.time() + _TURN_TIMEOUT
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            return {"text": "".join(accumulated),
                    "error": "OpenCode turn timed out (no completion event received)"}
        try:
            evt = await asyncio.wait_for(bus.queue.get(), timeout=remaining)
        except asyncio.TimeoutError:
            return {"text": "".join(accumulated),
                    "error": "OpenCode turn timed out (no completion event received)"}

        etype = evt.get("type", "")
        props = evt.get("properties", {})

        if etype == "message.updated":
            info = props.get("info") or {}
            if info.get("role") != "assistant":
                continue
            if info.get("parentID") != my_msg_id:
                continue
            asst_id = info.get("id", "")
            if asst_id:
                my_message_ids.add(asst_id)
            err = info.get("error")
            if err:
                if isinstance(err, dict):
                    error_text = (err.get("data") or {}).get("message") or str(err)
                else:
                    error_text = str(err)
                return {"text": "".join(accumulated), "error": error_text}
            finish = info.get("finish", "")
            if finish in _FINISH_TERMINAL and (info.get("time") or {}).get("completed"):
                return {"text": "".join(accumulated), "error": None}

        elif etype == "message.part.delta":
            if props.get("messageID") not in my_message_ids:
                continue
            if props.get("field") != "text":
                continue
            delta = props.get("delta", "")
            if delta:
                accumulated.append(delta)
                if on_text:
                    await on_text(delta)

        elif etype == "message.part.updated":
            part = props.get("part") or {}
            if part.get("messageID") and part.get("messageID") not in my_message_ids:
                continue
            ptype = part.get("type", "")
            if ptype == "text":
                full = part.get("text", "")
                if full:
                    accumulated.clear()
                    accumulated.append(full)
            elif ptype == "tool" and on_tool:
                state_obj = part.get("state") or {}
                await on_tool({
                    "tool": part.get("tool", "unknown"),
                    "callID": part.get("callID", ""),
                    "status": state_obj.get("status", ""),
                    "input": state_obj.get("input"),
                    "output": state_obj.get("output"),
                    "title": state_obj.get("title", ""),
                    "time": state_obj.get("time") or {},
                })
            elif ptype in ("step-start", "step-finish") and on_step:
                meta = {"type": ptype, "stepID": part.get("id", "")}
                if ptype == "step-finish":
                    meta["reason"] = part.get("reason", "")
                    meta["tokens"] = part.get("tokens", {})
                await on_step(meta)

            elif ptype == "reasoning" and on_reasoning:
                now = loop.time()
                if now - last_reasoning_emit >= _REASONING_THROTTLE:
                    last_reasoning_emit = now
                    rtext = (part.get("text") or "")
                    # Send a compact preview — UI just needs a sign of life
                    # plus optional text to display; avoid large payloads.
                    await on_reasoning({
                        "partID": part.get("id", ""),
                        "text": rtext[-240:],
                    })


# ── Entry point ───────────────────────────────────────────────────────

async def run(
    state,
    *,
    task: str,
    session_id: Optional[str] = None,
    stream_callback: Optional[Callable] = None,
):
    stream_callback = stream_callback or state.get("__stream_cb")
    pub = state.get("__pub")
    cid = session_id or state.get("__cid", "default")

    if not await _ensure_server():
        msg = (f"OpenCode server not running. Start with: "
               f"opencode serve --port {OPENCODE_SERVER_URL.split(':')[-1]}")
        return {"response": msg, "status": "error",
                "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

    cid_lock = await _get_cid_lock(cid)

    try:
        oc_sid = await _get_or_create_session(cid)
    except Exception as e:
        msg = f"Failed to create OpenCode session: {e}"
        return {"response": msg, "status": "error",
                "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

    consumer = await _get_consumer()
    bus = consumer.bus_for(oc_sid)

    my_msg_id = f"msg_{uuid4().hex[:20]}"

    # When using fresh sessions per turn, carry chat history forward via the
    # task prompt so opencode has conversational context.
    if _FRESH_SESSION_PER_TURN:
        history = _build_history_prefix(cid, exclude_last_user=True)
        if history:
            task = (
                "Previous conversation (for context only — do not repeat or"
                " summarise it unless asked):\n"
                f"{history}\n\n"
                f"Current request:\n{task}"
            )

    async def on_text(delta: str) -> None:
        if stream_callback:
            await stream_callback(delta)

    async def on_tool(payload: dict) -> None:
        if pub:
            await pub("opencode.tool", payload)

    async def on_step(payload: dict) -> None:
        if pub:
            await pub("opencode.step", payload)

    async def on_reasoning(payload: dict) -> None:
        if pub:
            await pub("opencode.reasoning", payload)

    async with cid_lock, bus.lock:
        # Serialization: cid_lock keeps replies ordered within a conversation
        # (each turn uses a fresh opencode session, so bus.lock alone would
        # not serialize across turns). Completion is driven by SSE
        # finish=stop — opencode's POST response is sometimes held open for
        # agent-loop iterations or doesn't return at all for bad-model
        # cases, so we can't rely on POST to signal "done".

        # Drain any stale events queued before our turn.
        while not bus.queue.empty():
            try:
                bus.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # POST runs as a background task. Its lifetime is bounded by
        # _POST_TIMEOUT; we ignore its return and cancel it as soon as
        # _consume_turn signals completion via finish=stop.
        post_result: dict = {}

        async def _do_post() -> None:
            try:
                async with aiohttp.ClientSession() as s:
                    async with s.post(
                        f"{OPENCODE_SERVER_URL}/session/{oc_sid}/message",
                        json={
                            "messageID": my_msg_id,
                            "mode": "build",
                            "parts": [{
                                "id": f"prt_{uuid4().hex[:20]}",
                                "sessionID": oc_sid,
                                "messageID": my_msg_id,
                                "type": "text",
                                "text": task,
                            }],
                        },
                        timeout=aiohttp.ClientTimeout(total=_POST_TIMEOUT),
                    ) as r:
                        post_result["status"] = r.status
                        post_result["body"] = await r.text()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                post_result["error"] = str(e)

        post_task = asyncio.create_task(_do_post())

        # Heartbeat: emit opencode.heartbeat every N seconds so the UI sees
        # continuous activity during long multi-step turns (reasoning phases,
        # tool runs) and doesn't give up on the stream.
        heartbeat_stop = asyncio.Event()

        async def _heartbeat_loop() -> None:
            import time as _t
            start = _t.time()
            while not heartbeat_stop.is_set():
                try:
                    await asyncio.wait_for(heartbeat_stop.wait(),
                                           timeout=_HEARTBEAT_INTERVAL)
                    return
                except asyncio.TimeoutError:
                    if pub:
                        try:
                            await pub("opencode.heartbeat", {
                                "messageID": my_msg_id,
                                "elapsed": int(_t.time() - start),
                            })
                        except Exception:
                            pass

        heartbeat_task = asyncio.create_task(_heartbeat_loop())

        try:
            result = await _consume_turn(bus, my_msg_id,
                                         on_text, on_tool, on_step,
                                         on_reasoning=on_reasoning)
        except BaseException:
            heartbeat_stop.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except BaseException:
                pass
            post_task.cancel()
            try:
                await post_task
            except BaseException:
                pass
            raise

        heartbeat_stop.set()
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except BaseException:
            pass

        # SSE said we're done. Cancel POST — it may still be held open by
        # opencode while it spins on follow-up generations or a bad-model
        # retry loop, and we don't care about its body anymore.
        post_task.cancel()
        try:
            await post_task
        except BaseException:
            pass

        # Only surface POST-level errors if SSE produced nothing usable.
        if (not result.get("text") and not result.get("error")
                and post_result.get("error")):
            result = {"text": "", "error": f"OpenCode POST failed: {post_result['error']}"}
        elif (not result.get("text") and not result.get("error")
                and post_result.get("status") not in (None, 200, 201)):
            body_preview = (post_result.get("body") or "")[:200]
            result = {"text": "",
                      "error": f"OpenCode POST error {post_result.get('status')}: {body_preview}"}

    text = (result.get("text") or "").strip()
    err = result.get("error")
    if err:
        return {"response": err, "status": "error",
                "badge": "\U0001f4bb", "reply": f"\U0001f4bb {err}",
                "__streamed": bool(text)}
    return {"response": text or "(no response)", "status": "success",
            "badge": "\U0001f4bb", "reply": f"\U0001f4bb {text or '(no response)'}",
            "__streamed": True}
