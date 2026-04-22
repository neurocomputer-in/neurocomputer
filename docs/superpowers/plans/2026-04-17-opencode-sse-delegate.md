# OpenCode SSE-Driven Delegate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite `neuros/opencode_delegate/code.py` to consume opencode's `/global/event` SSE stream with per-session serialization, so rapid follow-up messages no longer get silently dropped.

**Architecture:** One shared background `SSEConsumer` task parses opencode's SSE stream and routes events into per-session buses. Each user turn takes a per-session asyncio lock, waits for the session to report idle, POSTs the message, then consumes its own turn's events until `message.updated.info.finish` signals completion. Errors surface via `info.error` instead of silent timeouts.

**Tech Stack:** Python 3.12, `aiohttp` (already installed system-wide at 3.13.3), stdlib `asyncio`. Tests are plain-Python scripts using `asyncio.run` + `assert` + `print` (matches existing `tests/test_*.py` style — no new dependencies).

**Reference spec:** `docs/superpowers/specs/2026-04-17-opencode-sse-delegate-design.md`

---

## File Structure

### New files

| Path | Responsibility |
|---|---|
| `neuros/opencode_delegate/sse_consumer.py` | `SSEConsumer` singleton + `SessionBus`. Owns the single persistent connection to `/global/event`, parses events, fans out by `sessionID`, tracks busy/idle status per session. |
| `tests/opencode_delegate/__init__.py` | Empty package marker. |
| `tests/opencode_delegate/stub_opencode.py` | Mini aiohttp-based opencode impersonator: serves `/global/health`, `POST /session`, `POST /session/{id}/message`, and `GET /global/event` SSE with scriptable event sequences. Used by all integration tests. |
| `tests/opencode_delegate/test_sse_consumer.py` | Unit tests for `SSEConsumer` envelope parsing, session filtering, status tracking, reconnect. |
| `tests/opencode_delegate/test_delegate_run.py` | Integration tests for the full `run()` entry point against the stub server: happy path, rapid follow-up regression, multi-step tool-calls, error surfacing, pre-POST idle gate, reconnect mid-turn. |

### Rewritten files

| Path | Responsibility |
|---|---|
| `neuros/opencode_delegate/code.py` | Entry point. Keeps session-map persistence helpers (`_load_sessions`, `_save_sessions`, `_get_or_create_session`, `_get_conv_workdir`) and the `run()` async API the executor calls. Delegates all streaming/event work to `SSEConsumer`/`SessionBus`. |

### Updated files

| Path | Responsibility |
|---|---|
| `docs/opencode-sse-protocol.md` | Update envelope documentation for opencode v1.4.6 (events wrap in `payload.{type, properties}`, not top-level). Document the `sync` meta-event wrapper, the real completion signal (`message.updated.info.finish`), and note that no `session.idle` event-type exists. |

### Unchanged

`core/executor.py`, `core/brain.py`, `core/chat_handler.py`, `core/neuro_factory.py`, all frontend files, `data/opencode_sessions.json` on-disk format.

---

## Task 1: Scaffold test package and stub opencode server

**Files:**
- Create: `tests/opencode_delegate/__init__.py`
- Create: `tests/opencode_delegate/stub_opencode.py`

The stub is reused by every integration test. Making it usable and correct first keeps later tasks focused on behavior, not plumbing.

- [ ] **Step 1: Create the empty package marker**

```bash
mkdir -p tests/opencode_delegate
```

Create `tests/opencode_delegate/__init__.py` with content:
```python
```
(empty file)

- [ ] **Step 2: Write the stub server**

Create `tests/opencode_delegate/stub_opencode.py`:

```python
"""
Minimal aiohttp server that impersonates enough of `opencode serve` 1.4.6
for delegate tests. Scriptable: tests push event dicts into a per-session
event script; the stub's SSE endpoint flushes them when a POST arrives.

Usage (in a test):
    stub = StubOpenCode()
    await stub.start()  # returns {"url": "http://127.0.0.1:<port>"}
    stub.script_turn("ses_A", [
        {"type": "session.status", "properties": {"sessionID": "ses_A", "status": {"type": "busy"}}},
        {"type": "message.updated", "properties": {"sessionID": "ses_A",
            "info": {"id": "msg_asst_1", "parentID": "msg_user_1", "role": "assistant",
                     "time": {"created": 1}}}},
        {"type": "message.part.delta", "properties": {"sessionID": "ses_A",
            "messageID": "msg_asst_1", "partID": "prt_1", "field": "text", "delta": "hi"}},
        {"type": "message.updated", "properties": {"sessionID": "ses_A",
            "info": {"id": "msg_asst_1", "parentID": "msg_user_1", "role": "assistant",
                     "finish": "stop", "time": {"created": 1, "completed": 2}}}},
        {"type": "session.status", "properties": {"sessionID": "ses_A", "status": {"type": "idle"}}},
    ])
    # ...make requests against stub.url...
    await stub.stop()
"""
import asyncio
import json
import uuid
from typing import Any

from aiohttp import web


class StubOpenCode:
    def __init__(self):
        self._app = web.Application()
        self._app.router.add_get("/global/health", self._health)
        self._app.router.add_get("/global/event", self._event_stream)
        self._app.router.add_post("/session", self._create_session)
        self._app.router.add_get("/session/{sid}", self._get_session)
        self._app.router.add_post("/session/{sid}/message", self._post_message)
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._port: int = 0
        self._sessions: dict[str, dict] = {}
        self._scripts: dict[str, list[list[dict]]] = {}  # sid -> list of pending turns
        self._active_subscribers: list[asyncio.Queue] = []
        self._post_behavior: dict[str, str] = {}  # sid -> "normal" | "404" | "stall"
        self.post_log: list[dict] = []
        self.fail_next_event_connections: int = 0
        self.stall_event_stream: bool = False

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    async def start(self) -> None:
        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "127.0.0.1", 0)
        await self._site.start()
        # Discover assigned port from the socket.
        assert self._runner.sites, "stub runner has no sites"
        sock = list(self._runner.sites)[0]._server.sockets[0]
        self._port = sock.getsockname()[1]

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    # ── Test-facing scripting helpers ────────────────────────────────

    def script_turn(self, sid: str, events: list[dict]) -> None:
        """Queue one turn's worth of events to be flushed on the NEXT POST
        to /session/{sid}/message."""
        self._scripts.setdefault(sid, []).append(list(events))

    def set_post_behavior(self, sid: str, behavior: str) -> None:
        """behavior ∈ {'normal', '404', 'stall'}."""
        self._post_behavior[sid] = behavior

    def drop_next_sse_connection(self) -> None:
        self.fail_next_event_connections += 1

    # ── HTTP handlers ────────────────────────────────────────────────

    async def _health(self, _req: web.Request) -> web.Response:
        return web.json_response({"healthy": True, "version": "1.4.6-stub"})

    async def _create_session(self, req: web.Request) -> web.Response:
        body = await req.json() if req.can_read_body else {}
        sid = f"ses_{uuid.uuid4().hex[:18]}"
        self._sessions[sid] = {"id": sid, "title": body.get("title", ""),
                               "time": {"created": 1, "updated": 1}}
        return web.json_response(self._sessions[sid])

    async def _get_session(self, req: web.Request) -> web.Response:
        sid = req.match_info["sid"]
        if sid not in self._sessions:
            return web.Response(status=404)
        return web.json_response(self._sessions[sid])

    async def _post_message(self, req: web.Request) -> web.Response:
        sid = req.match_info["sid"]
        body = await req.json()
        self.post_log.append({"sid": sid, "body": body, "at": asyncio.get_event_loop().time()})

        behavior = self._post_behavior.get(sid, "normal")
        if behavior == "404":
            return web.Response(status=404, text="not found")
        if behavior == "stall":
            await asyncio.sleep(3600)  # will be cancelled when test ends

        # Flush the next scripted turn for this session (if any).
        pending = self._scripts.get(sid, [])
        if pending:
            events = pending.pop(0)
            for q in list(self._active_subscribers):
                for evt in events:
                    # Wrap in v1.4.6 envelope
                    wrapped = {"directory": "/stub", "project": "stub-proj",
                               "payload": evt}
                    try:
                        q.put_nowait(wrapped)
                    except asyncio.QueueFull:
                        pass
        return web.json_response({"ok": True})

    async def _event_stream(self, req: web.Request) -> web.StreamResponse:
        if self.fail_next_event_connections > 0:
            self.fail_next_event_connections -= 1
            return web.Response(status=500, text="stub forcing failure")

        resp = web.StreamResponse(
            status=200,
            headers={"Content-Type": "text/event-stream",
                     "Cache-Control": "no-cache"},
        )
        await resp.prepare(req)
        queue: asyncio.Queue = asyncio.Queue(maxsize=4096)
        self._active_subscribers.append(queue)
        # Emit the initial server.connected event, as opencode does.
        await queue.put({"payload": {"type": "server.connected", "properties": {}}})
        try:
            while True:
                if self.stall_event_stream:
                    await asyncio.sleep(0.1)
                    continue
                evt = await queue.get()
                line = f"data: {json.dumps(evt)}\n\n".encode("utf-8")
                try:
                    await resp.write(line)
                except ConnectionResetError:
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if queue in self._active_subscribers:
                self._active_subscribers.remove(queue)
        return resp
```

- [ ] **Step 3: Smoke-test the stub by hand**

Create a throwaway script at `/tmp/smoke_stub.py`:
```python
import asyncio, json, sys
sys.path.insert(0, "/home/ubuntu/neurocomputer-dev")
from tests.opencode_delegate.stub_opencode import StubOpenCode
import aiohttp

async def main():
    stub = StubOpenCode()
    await stub.start()
    try:
        async with aiohttp.ClientSession() as s:
            r = await s.get(f"{stub.url}/global/health")
            print("health:", r.status, await r.json())
            r = await s.post(f"{stub.url}/session", json={"title": "t"})
            sess = await r.json()
            print("session:", sess)
    finally:
        await stub.stop()

asyncio.run(main())
```
Run: `python3 /tmp/smoke_stub.py`
Expected:
```
health: 200 {'healthy': True, 'version': '1.4.6-stub'}
session: {'id': 'ses_...', 'title': 't', 'time': {'created': 1, 'updated': 1}}
```

- [ ] **Step 4: Commit**

```bash
git add tests/opencode_delegate/__init__.py tests/opencode_delegate/stub_opencode.py
git commit -m "test: add stub opencode server for delegate integration tests"
```

---

## Task 2: Write failing test for SSE envelope parsing

**Files:**
- Create: `tests/opencode_delegate/test_sse_consumer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/opencode_delegate/test_sse_consumer.py`:

```python
"""Unit tests for SSEConsumer envelope parsing, routing, and reconnect."""
import asyncio
import sys

sys.path.insert(0, "/home/ubuntu/neurocomputer-dev")

from neuros.opencode_delegate.sse_consumer import SSEConsumer
from tests.opencode_delegate.stub_opencode import StubOpenCode


async def test_parses_v146_envelope_and_routes_to_session_bus():
    """Events arrive as {directory, project, payload: {type, properties}}.
    The consumer must extract payload.{type,properties} and route by
    properties.sessionID into the right SessionBus.queue."""
    stub = StubOpenCode()
    await stub.start()
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus_a = consumer.bus_for("ses_A")

        # Script a single turn for ses_A via a synthetic POST.
        stub.script_turn("ses_A", [
            {"type": "message.part.delta",
             "properties": {"sessionID": "ses_A", "messageID": "msg_1",
                            "partID": "prt_1", "field": "text", "delta": "hello"}}
        ])
        # Trigger flush by posting any message.
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_A/message",
                         json={"messageID": "msg_u1", "parts": []})

        evt = await asyncio.wait_for(bus_a.queue.get(), timeout=2.0)
        assert evt["type"] == "message.part.delta", f"got type={evt['type']!r}"
        assert evt["properties"]["delta"] == "hello"
        assert evt["properties"]["sessionID"] == "ses_A"
        print("✅ envelope parsed & routed")
    finally:
        await consumer.stop()
        await stub.stop()


if __name__ == "__main__":
    asyncio.run(test_parses_v146_envelope_and_routes_to_session_bus())
    print("\n=== SSE consumer tests (1/4) passed ===")
```

- [ ] **Step 2: Run the test to confirm it fails**

Run: `python3 tests/opencode_delegate/test_sse_consumer.py`
Expected: `ModuleNotFoundError: No module named 'neuros.opencode_delegate.sse_consumer'`

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/opencode_delegate/test_sse_consumer.py
git commit -m "test: add failing test for SSE envelope parsing and routing"
```

---

## Task 3: Implement minimal SSEConsumer to pass the parse+route test

**Files:**
- Create: `neuros/opencode_delegate/sse_consumer.py`

- [ ] **Step 1: Write the minimal implementation**

Create `neuros/opencode_delegate/sse_consumer.py`:

```python
"""
Shared SSE consumer for opencode's /global/event stream.

One SSEConsumer instance per Python process owns a single persistent
connection, parses v1.4.6 envelopes, and routes events to per-session
SessionBus objects. Delegate turns (run()) coordinate via each bus's
lock + status + queue to serialize POSTs and consume their own events.
"""
from __future__ import annotations

import asyncio
import json
from typing import Literal

import aiohttp


SessionStatus = Literal["idle", "busy", "unknown"]


class SessionBus:
    def __init__(self, sid: str) -> None:
        self.sid = sid
        self.lock = asyncio.Lock()
        self.status: SessionStatus = "unknown"
        self.idle_ev = asyncio.Event()
        self.queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=2048)


class SSEConsumer:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._buses: dict[str, SessionBus] = {}
        self._task: asyncio.Task | None = None
        self._session: aiohttp.ClientSession | None = None
        self._stopping = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._session = aiohttp.ClientSession()
        self._task = asyncio.create_task(self._run_forever(), name="opencode-sse")

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._session:
            await self._session.close()
            self._session = None

    def bus_for(self, sid: str) -> SessionBus:
        if sid not in self._buses:
            self._buses[sid] = SessionBus(sid)
        return self._buses[sid]

    async def _run_forever(self) -> None:
        """Open /global/event, parse SSE, dispatch. Reconnect with backoff."""
        backoff = 1.0
        assert self._session is not None
        while not self._stopping:
            try:
                async with self._session.get(
                    f"{self._base_url}/global/event",
                    headers={"Accept": "text/event-stream"},
                    timeout=aiohttp.ClientTimeout(total=None, sock_read=None),
                ) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"/global/event returned {resp.status}")
                    backoff = 1.0  # reset on successful open
                    async for raw in resp.content:
                        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                        if not line.startswith("data:"):
                            continue
                        payload_str = line[5:].strip()
                        if not payload_str:
                            continue
                        try:
                            envelope = json.loads(payload_str)
                        except json.JSONDecodeError:
                            continue
                        self._dispatch(envelope)
            except asyncio.CancelledError:
                raise
            except Exception:
                # Mark all known buses as unknown before reconnecting.
                for bus in self._buses.values():
                    bus.status = "unknown"
                    bus.idle_ev.clear()
            if self._stopping:
                break
            await asyncio.sleep(min(backoff, 30.0))
            backoff = min(backoff * 2.0, 30.0)

    def _dispatch(self, envelope: dict) -> None:
        payload = envelope.get("payload") or {}
        etype = payload.get("type", "")
        props = payload.get("properties") or {}
        # Resolve sid. Most events put it under properties.sessionID; sync
        # wrappers use payload.aggregateID. Synthetic server-level events
        # (e.g. server.connected) have no session — skip routing.
        sid = props.get("sessionID") or payload.get("aggregateID")
        if not sid:
            return
        bus = self.bus_for(sid)
        # Keep the original payload envelope (type + properties) — consumers
        # don't need the directory/project outer wrapper.
        event = {"type": etype, "properties": props}
        try:
            bus.queue.put_nowait(event)
        except asyncio.QueueFull:
            # Drop oldest to make room — prevents runaway memory on abandoned turns.
            try:
                bus.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            bus.queue.put_nowait(event)
```

- [ ] **Step 2: Run the test, confirm it passes**

Run: `python3 tests/opencode_delegate/test_sse_consumer.py`
Expected:
```
✅ envelope parsed & routed

=== SSE consumer tests (1/4) passed ===
```

- [ ] **Step 3: Commit**

```bash
git add neuros/opencode_delegate/sse_consumer.py
git commit -m "feat(opencode): parse v1.4.6 SSE envelope and route events to per-session buses"
```

---

## Task 4: Add session-filtering test and verify it passes

**Files:**
- Modify: `tests/opencode_delegate/test_sse_consumer.py`

Session routing already works from Task 3, but we need an explicit test to guarantee events for session A do not leak to session B's bus.

- [ ] **Step 1: Append the test**

Append to `tests/opencode_delegate/test_sse_consumer.py` (above the `if __name__ == "__main__"` block):

```python
async def test_events_are_filtered_by_sessionID():
    """An event for ses_A must only appear in bus_for('ses_A'), not in bus_for('ses_B')."""
    stub = StubOpenCode()
    await stub.start()
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus_a = consumer.bus_for("ses_A")
        bus_b = consumer.bus_for("ses_B")

        stub.script_turn("ses_A", [
            {"type": "message.part.delta",
             "properties": {"sessionID": "ses_A", "field": "text", "delta": "A"}}
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_A/message",
                         json={"messageID": "m", "parts": []})

        evt = await asyncio.wait_for(bus_a.queue.get(), timeout=2.0)
        assert evt["properties"]["delta"] == "A"
        # bus_B must stay empty.
        assert bus_b.queue.empty(), "bus_B leaked an event from ses_A"
        print("✅ session filtering correct")
    finally:
        await consumer.stop()
        await stub.stop()
```

Update the bottom block:
```python
if __name__ == "__main__":
    asyncio.run(test_parses_v146_envelope_and_routes_to_session_bus())
    asyncio.run(test_events_are_filtered_by_sessionID())
    print("\n=== SSE consumer tests (2/4) passed ===")
```

- [ ] **Step 2: Run both tests**

Run: `python3 tests/opencode_delegate/test_sse_consumer.py`
Expected: both `✅` lines and the summary.

- [ ] **Step 3: Commit**

```bash
git add tests/opencode_delegate/test_sse_consumer.py
git commit -m "test(opencode): verify events are filtered per sessionID"
```

---

## Task 5: Status tracking — failing test

**Files:**
- Modify: `tests/opencode_delegate/test_sse_consumer.py`

- [ ] **Step 1: Append the failing test**

Append to `tests/opencode_delegate/test_sse_consumer.py`:

```python
async def test_session_status_tracks_busy_and_idle():
    """session.status events flip bus.status and bus.idle_ev accordingly."""
    stub = StubOpenCode()
    await stub.start()
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus = consumer.bus_for("ses_S")

        stub.script_turn("ses_S", [
            {"type": "session.status",
             "properties": {"sessionID": "ses_S", "status": {"type": "busy"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_S/message",
                         json={"messageID": "m", "parts": []})

        # Give the consumer a tick to process.
        for _ in range(20):
            if bus.status == "busy":
                break
            await asyncio.sleep(0.05)
        assert bus.status == "busy", f"expected busy, got {bus.status}"
        assert not bus.idle_ev.is_set(), "idle_ev must be clear when busy"

        stub.script_turn("ses_S", [
            {"type": "session.status",
             "properties": {"sessionID": "ses_S", "status": {"type": "idle"}}},
        ])
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_S/message",
                         json={"messageID": "m2", "parts": []})

        await asyncio.wait_for(bus.idle_ev.wait(), timeout=2.0)
        assert bus.status == "idle"
        print("✅ session.status tracking correct")
    finally:
        await consumer.stop()
        await stub.stop()
```

Update the runner block:
```python
if __name__ == "__main__":
    asyncio.run(test_parses_v146_envelope_and_routes_to_session_bus())
    asyncio.run(test_events_are_filtered_by_sessionID())
    asyncio.run(test_session_status_tracks_busy_and_idle())
    print("\n=== SSE consumer tests (3/4) passed ===")
```

- [ ] **Step 2: Run, confirm failure**

Run: `python3 tests/opencode_delegate/test_sse_consumer.py`
Expected: `AssertionError: expected busy, got unknown` — status tracking not yet implemented.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/opencode_delegate/test_sse_consumer.py
git commit -m "test(opencode): failing test for session.status → bus.status tracking"
```

---

## Task 6: Implement status tracking

**Files:**
- Modify: `neuros/opencode_delegate/sse_consumer.py`

- [ ] **Step 1: Add status handling in `_dispatch`**

Edit `neuros/opencode_delegate/sse_consumer.py`. Replace the body of `_dispatch` with:

```python
    def _dispatch(self, envelope: dict) -> None:
        payload = envelope.get("payload") or {}
        etype = payload.get("type", "")
        props = payload.get("properties") or {}
        sid = props.get("sessionID") or payload.get("aggregateID")
        if not sid:
            return
        bus = self.bus_for(sid)
        event = {"type": etype, "properties": props}

        # Track session status before queuing so consumers see consistent state.
        if etype == "session.status":
            status_type = (props.get("status") or {}).get("type", "")
            if status_type == "idle":
                bus.status = "idle"
                bus.idle_ev.set()
            elif status_type == "busy":
                bus.status = "busy"
                bus.idle_ev.clear()

        try:
            bus.queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                bus.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            bus.queue.put_nowait(event)
```

- [ ] **Step 2: Run all three tests, confirm pass**

Run: `python3 tests/opencode_delegate/test_sse_consumer.py`
Expected: three `✅` lines and `=== SSE consumer tests (3/4) passed ===`.

- [ ] **Step 3: Commit**

```bash
git add neuros/opencode_delegate/sse_consumer.py
git commit -m "feat(opencode): track session busy/idle status on SessionBus"
```

---

## Task 7: Reconnect — failing test

**Files:**
- Modify: `tests/opencode_delegate/test_sse_consumer.py`

- [ ] **Step 1: Append the failing test**

Append to `tests/opencode_delegate/test_sse_consumer.py`:

```python
async def test_reconnects_after_sse_drop_and_marks_status_unknown():
    """If the SSE connection fails, the consumer reconnects, and any known
    bus statuses are reset to 'unknown' so the next turn re-gates."""
    stub = StubOpenCode()
    await stub.start()
    try:
        consumer = SSEConsumer(base_url=stub.url)
        await consumer.start()
        bus = consumer.bus_for("ses_R")

        # Put the bus into idle state first.
        stub.script_turn("ses_R", [
            {"type": "session.status",
             "properties": {"sessionID": "ses_R", "status": {"type": "idle"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/ses_R/message",
                         json={"messageID": "m", "parts": []})
        await asyncio.wait_for(bus.idle_ev.wait(), timeout=2.0)

        # Force the consumer's current connection to drop by making the next
        # /global/event GET return 500. The consumer has to reconnect.
        stub.drop_next_sse_connection()

        # We need the consumer to actually re-issue the GET. Simulate a server
        # hiccup by restarting the current SSE connection: easiest way is to
        # stop+start stub. But we also want the same port. Instead, just give
        # it a beat and then verify bus status is reset to 'unknown'.
        # Trigger by temporarily stalling and letting the current stream die.
        # Close all active subscriber queues via stub internals.
        for q in list(stub._active_subscribers):
            await q.put({"payload": {"type": "__stub_close__", "properties": {}}})
        # The consumer's content iterator won't die from a synthetic event,
        # so we forcibly close the stub:
        await stub.stop()
        # Wait a moment for the consumer's request to raise.
        await asyncio.sleep(0.5)
        # Now restart the stub on a new port (can't reuse previous port reliably),
        # but consumer points at the old URL, so we instead flip its base_url.
        stub2 = StubOpenCode()
        await stub2.start()
        consumer._base_url = stub2.url.rstrip("/")  # test-only attr poke

        # Give it time to reconnect.
        for _ in range(40):
            if bus.status == "unknown":
                break
            await asyncio.sleep(0.1)
        assert bus.status == "unknown", f"expected unknown after drop, got {bus.status}"
        assert not bus.idle_ev.is_set()
        print("✅ reconnect resets bus status to unknown")
        await stub2.stop()
    finally:
        await consumer.stop()
        # stub already stopped above
        try:
            await stub.stop()
        except Exception:
            pass
```

Update the runner block:
```python
if __name__ == "__main__":
    asyncio.run(test_parses_v146_envelope_and_routes_to_session_bus())
    asyncio.run(test_events_are_filtered_by_sessionID())
    asyncio.run(test_session_status_tracks_busy_and_idle())
    asyncio.run(test_reconnects_after_sse_drop_and_marks_status_unknown())
    print("\n=== SSE consumer tests (4/4) passed ===")
```

- [ ] **Step 2: Run, confirm failure or noise**

Run: `python3 tests/opencode_delegate/test_sse_consumer.py`
Expected: the first three `✅` lines, then `AssertionError: expected unknown after drop, got idle` (or similar) because the current `_run_forever` already has the reconnect logic but we need to confirm it handles the "connection dropped by server dying" case. If the test already passes because Task 3's `_run_forever` did it, move to Step 3 as verification.

(Note: Task 3 already includes the "mark all buses unknown" reset in the `except` branch. This test codifies that behavior.)

- [ ] **Step 3: If the test fails, tighten the implementation**

If Step 2 showed the test failing, ensure the reconnect branch in `_run_forever` resets `bus.idle_ev.clear()` (Task 3 already does; this is a belt-and-suspenders check). Re-run until green.

- [ ] **Step 4: Commit**

```bash
git add tests/opencode_delegate/test_sse_consumer.py
git commit -m "test(opencode): verify SSE reconnect resets bus status to unknown"
```

---

## Task 8: Rewrite delegate `run()` — happy-path failing test

**Files:**
- Create: `tests/opencode_delegate/test_delegate_run.py`

- [ ] **Step 1: Write the happy-path integration test**

Create `tests/opencode_delegate/test_delegate_run.py`:

```python
"""Integration tests for the full opencode_delegate.run() entry point."""
import asyncio
import os
import sys
import tempfile

sys.path.insert(0, "/home/ubuntu/neurocomputer-dev")

from tests.opencode_delegate.stub_opencode import StubOpenCode


def _setup_stub_env(stub: StubOpenCode) -> str:
    """Point the delegate at the stub, and use an isolated session-map file."""
    os.environ["OPENCODE_SERVER_URL"] = stub.url
    tmpdir = tempfile.mkdtemp(prefix="oc_deleg_")
    os.makedirs(os.path.join(tmpdir, "data"), exist_ok=True)
    os.makedirs(os.path.join(tmpdir, "conversations"), exist_ok=True)
    # Force the delegate to use this dir as its project root by chdir.
    os.chdir(tmpdir)
    return tmpdir


async def _drain_stream(collected: list, chunk: str) -> None:
    collected.append(chunk)


async def test_happy_path_single_turn_streams_and_returns_text():
    """One user turn: stub emits busy → delta 'hi' → delta ' there' → assistant
    completion with finish=stop. Delegate must return 'hi there' and have
    streamed each delta via stream_callback in order."""
    # Fresh imports so the stub_env is in effect.
    import importlib, sys as _sys
    for m in list(_sys.modules):
        if m.startswith("neuros.opencode_delegate"):
            _sys.modules.pop(m, None)

    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        # Script a complete turn. Use a sentinel user msg id; the delegate
        # will generate its own msg_id, and we'll capture it from post_log.
        # Since our assistant events reference `parentID`, we need to emit
        # them AFTER we see the POST. The stub already flushes scripted
        # events on POST arrival, so we pre-script placeholder parentID
        # which we'll patch inside stub — simpler: emit events whose
        # parentID field is filled in at flush time by the stub.

        # Simpler strategy: the stub flushes its scripted events verbatim on
        # POST; we have the test itself call the delegate and, once it's
        # POSTed, observe stub.post_log[0]['body']['messageID'] and feed
        # the next script via stub.script_turn with that value. Two-phase.

        collected: list[str] = []
        state = {"__stream_cb": _drain_stream.__get__(collected)
                 if False else (lambda c: _drain_stream(collected, c)),
                 "__cid": "cid-happy", "__pub": None}

        async def driver():
            # Before calling run(), pre-script only the busy + session.status
            # events. We must know the assistant parentID = the msg_id the
            # delegate generates. Wait for the POST, then script the rest.
            delegate_task = asyncio.create_task(
                delegate.run(state, task="hi")
            )
            # Wait for the POST to arrive.
            for _ in range(50):
                if stub.post_log:
                    break
                await asyncio.sleep(0.02)
            assert stub.post_log, "delegate never POSTed"
            posted = stub.post_log[-1]
            sid = posted["sid"]
            user_msg_id = posted["body"]["messageID"]

            # Now script the assistant turn.
            stub.script_turn(sid, [
                {"type": "session.status",
                 "properties": {"sessionID": sid, "status": {"type": "busy"}}},
                {"type": "message.updated",
                 "properties": {"sessionID": sid,
                                "info": {"id": "msg_asst_1", "parentID": user_msg_id,
                                         "role": "assistant",
                                         "time": {"created": 1}}}},
                {"type": "message.part.delta",
                 "properties": {"sessionID": sid, "messageID": "msg_asst_1",
                                "partID": "prt_1", "field": "text", "delta": "hi"}},
                {"type": "message.part.delta",
                 "properties": {"sessionID": sid, "messageID": "msg_asst_1",
                                "partID": "prt_1", "field": "text", "delta": " there"}},
                {"type": "message.updated",
                 "properties": {"sessionID": sid,
                                "info": {"id": "msg_asst_1", "parentID": user_msg_id,
                                         "role": "assistant", "finish": "stop",
                                         "time": {"created": 1, "completed": 2}}}},
                {"type": "session.status",
                 "properties": {"sessionID": sid, "status": {"type": "idle"}}},
            ])
            # Trigger the flush by POSTing a no-op message to the stub
            # (the stub flushes on ANY POST). We use a distinct path that
            # won't disturb the delegate.
            import aiohttp
            async with aiohttp.ClientSession() as s:
                await s.post(f"{stub.url}/session/{sid}/message",
                             json={"messageID": "m_trigger", "parts": []})

            return await asyncio.wait_for(delegate_task, timeout=10)

        result = await driver()
        assert result["status"] == "success", result
        assert result["response"] == "hi there", f"response={result['response']!r}"
        assert "".join(collected) == "hi there", f"streamed={collected!r}"
        print("✅ happy-path single turn")
    finally:
        await stub.stop()


if __name__ == "__main__":
    asyncio.run(test_happy_path_single_turn_streams_and_returns_text())
    print("\n=== delegate run() tests (1/6) passed ===")
```

- [ ] **Step 2: Run, confirm it fails**

Run: `python3 tests/opencode_delegate/test_delegate_run.py`
Expected: failure, because the current `neuros/opencode_delegate/code.py` uses POST+polling and doesn't use the new `SSEConsumer`. The failure will manifest as either a timeout or a wrong-response assertion.

- [ ] **Step 3: Commit the failing test**

```bash
git add tests/opencode_delegate/test_delegate_run.py
git commit -m "test(opencode): failing happy-path integration test for new delegate run()"
```

---

## Task 9: Rewrite `neuros/opencode_delegate/code.py`

**Files:**
- Rewrite: `neuros/opencode_delegate/code.py`

- [ ] **Step 1: Replace the file contents**

Overwrite `neuros/opencode_delegate/code.py` with:

```python
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
_POST_TIMEOUT = 10.0
_IDLE_WAIT_TIMEOUT = 60.0
_FINISH_TERMINAL = {"stop", "length", "error", "cancelled"}


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


async def _ensure_server() -> bool:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{OPENCODE_SERVER_URL}/global/health",
                             timeout=aiohttp.ClientTimeout(total=3)) as r:
                return r.status == 200
    except Exception:
        return False


async def _get_or_create_session(cid: str) -> str:
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

    workdir = _get_conv_workdir(cid)
    payload: dict = {"title": f"neuro-{cid[:8]}"}
    if workdir:
        payload["cwd"] = workdir
    async with aiohttp.ClientSession() as s:
        async with s.post(f"{OPENCODE_SERVER_URL}/session", json=payload,
                          timeout=aiohttp.ClientTimeout(total=10)) as r:
            data = await r.json()
    sid = data["id"]
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


# ── Event dispatch for one turn ───────────────────────────────────────

async def _consume_turn(
    bus: SessionBus,
    my_msg_id: str,
    on_text,
    on_tool,
    on_step,
) -> dict:
    """Consume events from the bus until our turn completes. Returns
    {'text': str, 'error': str | None}."""
    accumulated: list[str] = []
    my_message_ids: set[str] = set()  # assistant msg ids parented by us
    error_text: str | None = None

    deadline = asyncio.get_event_loop().time() + _TURN_TIMEOUT
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
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
                    # Snapshot — replace accumulated.
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

    try:
        oc_sid = await _get_or_create_session(cid)
    except Exception as e:
        msg = f"Failed to create OpenCode session: {e}"
        return {"response": msg, "status": "error",
                "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

    consumer = await _get_consumer()
    bus = consumer.bus_for(oc_sid)

    my_msg_id = f"msg_{uuid4().hex[:20]}"

    async def on_text(delta: str) -> None:
        if stream_callback:
            await stream_callback(delta)

    async def on_tool(payload: dict) -> None:
        if pub:
            await pub("opencode.tool", payload)

    async def on_step(payload: dict) -> None:
        if pub:
            await pub("opencode.step", payload)

    async with bus.lock:
        # Pre-POST idle gate.
        if bus.status == "busy":
            try:
                await asyncio.wait_for(bus.idle_ev.wait(),
                                       timeout=_IDLE_WAIT_TIMEOUT)
            except asyncio.TimeoutError:
                msg = "OpenCode session appears stuck in busy state"
                return {"response": msg, "status": "error",
                        "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

        bus.idle_ev.clear()

        # Drain any stale events queued before our turn.
        while not bus.queue.empty():
            try:
                bus.queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # POST (short timeout — POST only acknowledges storage).
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
                    if r.status not in (200, 201):
                        body = await r.text()
                        msg = f"OpenCode POST error {r.status}: {body[:200]}"
                        return {"response": msg, "status": "error",
                                "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}
        except asyncio.TimeoutError:
            # Opencode sometimes holds POST open for the whole turn. That's
            # OK — storage happens before the hold. Continue to SSE consumption.
            pass
        except Exception as e:
            msg = f"OpenCode POST failed: {e}"
            return {"response": msg, "status": "error",
                    "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

        result = await _consume_turn(bus, my_msg_id, on_text, on_tool, on_step)

    text = (result.get("text") or "").strip()
    err = result.get("error")
    if err:
        return {"response": err, "status": "error",
                "badge": "\U0001f4bb", "reply": f"\U0001f4bb {err}",
                "__streamed": bool(text)}
    return {"response": text or "(no response)", "status": "success",
            "badge": "\U0001f4bb", "reply": f"\U0001f4bb {text or '(no response)'}",
            "__streamed": True}
```

- [ ] **Step 2: Run the happy-path test**

Run: `python3 tests/opencode_delegate/test_delegate_run.py`
Expected: `✅ happy-path single turn` and `=== delegate run() tests (1/6) passed ===`.

If it times out, the likeliest cause is the stub's flush-on-POST behavior colliding with the delegate's own POST. The driver in Task 8 uses a secondary POST (`m_trigger`) to flush scripted events AFTER the delegate has posted. Verify both POSTs reach the stub by printing `stub.post_log`.

- [ ] **Step 3: Re-run SSE consumer tests to make sure nothing regressed**

Run: `python3 tests/opencode_delegate/test_sse_consumer.py`
Expected: four `✅` lines.

- [ ] **Step 4: Commit**

```bash
git add neuros/opencode_delegate/code.py
git commit -m "feat(opencode): rewrite delegate to use SSE consumer with per-session serialization"
```

---

## Task 10: Rapid follow-up regression test

**Files:**
- Modify: `tests/opencode_delegate/test_delegate_run.py`

This is **the** test that proves the original bug is fixed.

- [ ] **Step 1: Add the rapid-send test**

Append to `tests/opencode_delegate/test_delegate_run.py` (above the `if __name__` block):

```python
async def test_two_rapid_turns_on_same_conversation_both_get_replies():
    """Concurrency regression: two run() calls on the same cid launched
    back-to-back must both produce replies, in order. Previously, the
    second turn's POST arrived while the session was still busy from turn 1
    and opencode silently dropped it."""
    import importlib, sys as _sys
    for m in list(_sys.modules):
        if m.startswith("neuros.opencode_delegate"):
            _sys.modules.pop(m, None)

    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        collected1: list[str] = []
        collected2: list[str] = []
        state1 = {"__stream_cb": lambda c: _drain_stream(collected1, c),
                  "__cid": "cid-rapid", "__pub": None}
        state2 = {"__stream_cb": lambda c: _drain_stream(collected2, c),
                  "__cid": "cid-rapid", "__pub": None}

        # Launch both runs concurrently. They share the same cid and therefore
        # the same opencode session → they must serialize through the bus lock.
        task1 = asyncio.create_task(delegate.run(state1, task="first"))
        task2 = asyncio.create_task(delegate.run(state2, task="second"))

        # Service POSTs one at a time.
        async def servicer():
            seen = 0
            while seen < 2:
                while len(stub.post_log) <= seen:
                    await asyncio.sleep(0.02)
                posted = stub.post_log[seen]
                sid = posted["sid"]
                umid = posted["body"]["messageID"]
                aid = f"msg_asst_{seen+1}"
                stub.script_turn(sid, [
                    {"type": "session.status",
                     "properties": {"sessionID": sid, "status": {"type": "busy"}}},
                    {"type": "message.updated",
                     "properties": {"sessionID": sid,
                                    "info": {"id": aid, "parentID": umid,
                                             "role": "assistant",
                                             "time": {"created": 1}}}},
                    {"type": "message.part.delta",
                     "properties": {"sessionID": sid, "messageID": aid,
                                    "partID": f"prt_{seen+1}", "field": "text",
                                    "delta": f"reply{seen+1}"}},
                    {"type": "message.updated",
                     "properties": {"sessionID": sid,
                                    "info": {"id": aid, "parentID": umid,
                                             "role": "assistant", "finish": "stop",
                                             "time": {"created": 1, "completed": 2}}}},
                    {"type": "session.status",
                     "properties": {"sessionID": sid, "status": {"type": "idle"}}},
                ])
                # Trigger the flush via a side-channel POST.
                import aiohttp
                async with aiohttp.ClientSession() as s:
                    await s.post(f"{stub.url}/session/{sid}/message",
                                 json={"messageID": f"trig_{seen}", "parts": []})
                seen += 1

        servicer_task = asyncio.create_task(servicer())

        r1 = await asyncio.wait_for(task1, timeout=10)
        r2 = await asyncio.wait_for(task2, timeout=10)
        await servicer_task

        assert r1["status"] == "success" and r1["response"] == "reply1", r1
        assert r2["status"] == "success" and r2["response"] == "reply2", r2
        assert "".join(collected1) == "reply1"
        assert "".join(collected2) == "reply2"
        print("✅ two rapid turns both get replies")
    finally:
        await stub.stop()
```

Update the runner block:
```python
if __name__ == "__main__":
    asyncio.run(test_happy_path_single_turn_streams_and_returns_text())
    asyncio.run(test_two_rapid_turns_on_same_conversation_both_get_replies())
    print("\n=== delegate run() tests (2/6) passed ===")
```

- [ ] **Step 2: Run**

Run: `python3 tests/opencode_delegate/test_delegate_run.py`
Expected: both `✅` lines. (Regression test passes because Task 9 already added the per-session lock + idle gate.)

- [ ] **Step 3: Commit**

```bash
git add tests/opencode_delegate/test_delegate_run.py
git commit -m "test(opencode): regression test for rapid follow-up messages on same session"
```

---

## Task 11: Multi-step tool-call test

**Files:**
- Modify: `tests/opencode_delegate/test_delegate_run.py`

- [ ] **Step 1: Add the test**

Append to `tests/opencode_delegate/test_delegate_run.py`:

```python
async def test_multi_step_tool_call_turn_returns_final_text_only_after_stop():
    """Turn has two assistant messages under same parentID:
        #1 finish='tool-calls' (intermediate — must NOT terminate)
        #2 finish='stop'       (terminal)
    Delegate must wait for #2 and return its text; tool events must be
    forwarded via pub('opencode.tool', ...) during #1."""
    import importlib, sys as _sys
    for m in list(_sys.modules):
        if m.startswith("neuros.opencode_delegate"):
            _sys.modules.pop(m, None)

    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        tool_events: list[dict] = []
        step_events: list[dict] = []

        async def pub(topic: str, payload: dict) -> None:
            if topic == "opencode.tool":
                tool_events.append(payload)
            elif topic == "opencode.step":
                step_events.append(payload)

        collected: list[str] = []
        state = {"__stream_cb": lambda c: _drain_stream(collected, c),
                 "__cid": "cid-tools", "__pub": pub}

        task = asyncio.create_task(delegate.run(state, task="do a tool thing"))

        # Wait for the POST.
        for _ in range(50):
            if stub.post_log:
                break
            await asyncio.sleep(0.02)
        sid = stub.post_log[-1]["sid"]
        umid = stub.post_log[-1]["body"]["messageID"]

        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            # Step 1: assistant msg that calls a tool, then stops-for-tool-calls.
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_1", "parentID": umid,
                                     "role": "assistant",
                                     "time": {"created": 1}}}},
            {"type": "message.part.updated",
             "properties": {"sessionID": sid,
                            "part": {"id": "prt_step1", "messageID": "msg_asst_1",
                                     "type": "step-start"}}},
            {"type": "message.part.updated",
             "properties": {"sessionID": sid,
                            "part": {"id": "prt_tool1", "messageID": "msg_asst_1",
                                     "type": "tool", "tool": "read",
                                     "callID": "call_1",
                                     "state": {"status": "completed",
                                               "input": {"filePath": "/x"},
                                               "output": "file contents",
                                               "title": "Read /x"}}}},
            {"type": "message.part.updated",
             "properties": {"sessionID": sid,
                            "part": {"id": "prt_stepf1", "messageID": "msg_asst_1",
                                     "type": "step-finish",
                                     "reason": "tool-calls",
                                     "tokens": {"input": 10, "output": 2}}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_1", "parentID": umid,
                                     "role": "assistant", "finish": "tool-calls",
                                     "time": {"created": 1, "completed": 2}}}},
            # Step 2: NEW assistant msg with same parentID, finish=stop.
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_2", "parentID": umid,
                                     "role": "assistant",
                                     "time": {"created": 3}}}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid, "messageID": "msg_asst_2",
                            "partID": "prt_text", "field": "text",
                            "delta": "done!"}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_asst_2", "parentID": umid,
                                     "role": "assistant", "finish": "stop",
                                     "time": {"created": 3, "completed": 4}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig", "parts": []})

        result = await asyncio.wait_for(task, timeout=10)
        assert result["status"] == "success", result
        assert result["response"] == "done!", f"got {result['response']!r}"
        assert any(e["tool"] == "read" for e in tool_events), tool_events
        assert any(e["type"] == "step-finish" for e in step_events), step_events
        print("✅ multi-step tool-call turn")
    finally:
        await stub.stop()
```

Update runner block:
```python
if __name__ == "__main__":
    asyncio.run(test_happy_path_single_turn_streams_and_returns_text())
    asyncio.run(test_two_rapid_turns_on_same_conversation_both_get_replies())
    asyncio.run(test_multi_step_tool_call_turn_returns_final_text_only_after_stop())
    print("\n=== delegate run() tests (3/6) passed ===")
```

- [ ] **Step 2: Run**

Run: `python3 tests/opencode_delegate/test_delegate_run.py`
Expected: three `✅` lines.

- [ ] **Step 3: Commit**

```bash
git add tests/opencode_delegate/test_delegate_run.py
git commit -m "test(opencode): multi-step tool-call turn waits for finish=stop"
```

---

## Task 12: Error surfacing test

**Files:**
- Modify: `tests/opencode_delegate/test_delegate_run.py`

- [ ] **Step 1: Add the test**

Append to `tests/opencode_delegate/test_delegate_run.py`:

```python
async def test_model_error_surfaces_as_error_reply_not_timeout():
    """If opencode emits message.updated with info.error, the delegate
    returns status=error with the error message — no 300s timeout."""
    import importlib, sys as _sys
    for m in list(_sys.modules):
        if m.startswith("neuros.opencode_delegate"):
            _sys.modules.pop(m, None)

    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        state = {"__stream_cb": lambda c: None, "__cid": "cid-err", "__pub": None}
        task = asyncio.create_task(delegate.run(state, task="x"))

        for _ in range(50):
            if stub.post_log:
                break
            await asyncio.sleep(0.02)
        sid = stub.post_log[-1]["sid"]
        umid = stub.post_log[-1]["body"]["messageID"]

        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a", "parentID": umid,
                                     "role": "assistant",
                                     "error": {"name": "ProviderAuthError",
                                               "data": {"message": "model not found",
                                                        "providerID": "ollama"}},
                                     "time": {"created": 1}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig", "parts": []})

        result = await asyncio.wait_for(task, timeout=10)
        assert result["status"] == "error"
        assert "model not found" in result["response"], result
        print("✅ model error surfaces in reply")
    finally:
        await stub.stop()
```

Update runner block accordingly (add the new `asyncio.run(...)` line before the print).

- [ ] **Step 2: Run**

Run: `python3 tests/opencode_delegate/test_delegate_run.py`
Expected: four `✅` lines.

- [ ] **Step 3: Commit**

```bash
git add tests/opencode_delegate/test_delegate_run.py
git commit -m "test(opencode): surface opencode provider errors as error replies"
```

---

## Task 13: Pre-POST idle gate explicit test

**Files:**
- Modify: `tests/opencode_delegate/test_delegate_run.py`

- [ ] **Step 1: Add the test**

Append:

```python
async def test_second_turn_waits_for_idle_before_posting():
    """Verify the timing: if bus.status=='busy' at run() entry, the POST
    does NOT fire until bus.idle_ev is set by an 'idle' session.status event."""
    import importlib, sys as _sys
    for m in list(_sys.modules):
        if m.startswith("neuros.opencode_delegate"):
            _sys.modules.pop(m, None)

    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        from neuros.opencode_delegate import code as delegate

        # Turn 1 — keeps session busy.
        state1 = {"__stream_cb": lambda c: None, "__cid": "cid-gate", "__pub": None}
        state2 = {"__stream_cb": lambda c: None, "__cid": "cid-gate", "__pub": None}

        t1 = asyncio.create_task(delegate.run(state1, task="t1"))
        # Wait for t1 POST.
        for _ in range(50):
            if stub.post_log:
                break
            await asyncio.sleep(0.02)
        sid = stub.post_log[-1]["sid"]
        umid1 = stub.post_log[-1]["body"]["messageID"]

        # Put session into busy but don't finish yet.
        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a1", "parentID": umid1,
                                     "role": "assistant",
                                     "time": {"created": 1}}}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig1", "parts": []})

        # Launch turn 2 now — it must NOT POST a message of its own while busy.
        t2 = asyncio.create_task(delegate.run(state2, task="t2"))
        await asyncio.sleep(0.5)
        # At this point, only one user-initiated POST should have landed
        # (t1's). Count POSTs whose messageID starts with "msg_".
        user_posts_before = [p for p in stub.post_log
                             if p["body"].get("messageID", "").startswith("msg_")]
        assert len(user_posts_before) == 1, \
            f"turn 2 POSTed while session was busy: {user_posts_before}"

        # Now finish turn 1.
        stub.script_turn(sid, [
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a1", "parentID": umid1,
                                     "role": "assistant", "finish": "stop",
                                     "time": {"created": 1, "completed": 2}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig_finish_1", "parts": []})

        r1 = await asyncio.wait_for(t1, timeout=10)
        assert r1["status"] == "success"

        # Now turn 2 should POST. Script its reply.
        for _ in range(50):
            user_posts = [p for p in stub.post_log
                          if p["body"].get("messageID", "").startswith("msg_")]
            if len(user_posts) >= 2:
                break
            await asyncio.sleep(0.02)
        umid2 = user_posts[-1]["body"]["messageID"]
        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a2", "parentID": umid2,
                                     "role": "assistant",
                                     "time": {"created": 3}}}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid, "messageID": "msg_a2",
                            "partID": "p", "field": "text", "delta": "ok"}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a2", "parentID": umid2,
                                     "role": "assistant", "finish": "stop",
                                     "time": {"created": 3, "completed": 4}}}},
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "idle"}}},
        ])
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig_finish_2", "parts": []})
        r2 = await asyncio.wait_for(t2, timeout=10)
        assert r2["status"] == "success" and r2["response"] == "ok", r2
        print("✅ idle gate delays second POST")
    finally:
        await stub.stop()
```

Add to runner block as the fifth test.

- [ ] **Step 2: Run**

Run: `python3 tests/opencode_delegate/test_delegate_run.py`
Expected: five `✅` lines.

- [ ] **Step 3: Commit**

```bash
git add tests/opencode_delegate/test_delegate_run.py
git commit -m "test(opencode): verify pre-POST idle gate delays second turn's POST"
```

---

## Task 14: Reconnect-mid-turn test

**Files:**
- Modify: `tests/opencode_delegate/test_delegate_run.py`

- [ ] **Step 1: Add the test**

Append:

```python
async def test_reconnect_mid_turn_times_out_cleanly_with_partial_text():
    """If SSE drops mid-turn and nothing more arrives, the delegate times
    out cleanly within _TURN_TIMEOUT seconds with an error reply carrying
    any partial text accumulated before the drop."""
    import importlib, sys as _sys
    for m in list(_sys.modules):
        if m.startswith("neuros.opencode_delegate"):
            _sys.modules.pop(m, None)

    stub = StubOpenCode()
    await stub.start()
    try:
        _setup_stub_env(stub)
        # Shorten the timeout for the test.
        from neuros.opencode_delegate import code as delegate
        delegate._TURN_TIMEOUT = 1.5  # override for fast test

        collected: list[str] = []
        state = {"__stream_cb": lambda c: _drain_stream(collected, c),
                 "__cid": "cid-drop", "__pub": None}

        task = asyncio.create_task(delegate.run(state, task="x"))

        for _ in range(50):
            if stub.post_log:
                break
            await asyncio.sleep(0.02)
        sid = stub.post_log[-1]["sid"]
        umid = stub.post_log[-1]["body"]["messageID"]

        # Emit some partial text, then kill the stub → SSE drops.
        stub.script_turn(sid, [
            {"type": "session.status",
             "properties": {"sessionID": sid, "status": {"type": "busy"}}},
            {"type": "message.updated",
             "properties": {"sessionID": sid,
                            "info": {"id": "msg_a", "parentID": umid,
                                     "role": "assistant",
                                     "time": {"created": 1}}}},
            {"type": "message.part.delta",
             "properties": {"sessionID": sid, "messageID": "msg_a",
                            "partID": "p", "field": "text", "delta": "partial"}},
        ])
        import aiohttp
        async with aiohttp.ClientSession() as s:
            await s.post(f"{stub.url}/session/{sid}/message",
                         json={"messageID": "trig", "parts": []})
        # Give consumer time to deliver the partial delta.
        await asyncio.sleep(0.2)
        # Now drop the SSE by stopping the stub entirely. No more events ever.
        await stub.stop()

        result = await asyncio.wait_for(task, timeout=5)
        assert result["status"] == "error"
        assert "timed out" in result["response"].lower()
        assert "partial" in "".join(collected), \
            f"partial text lost: {collected!r}"
        print("✅ mid-turn reconnect/drop → clean timeout with partial text")
    finally:
        try:
            await stub.stop()
        except Exception:
            pass
        # Restore default timeout.
        from neuros.opencode_delegate import code as delegate2
        delegate2._TURN_TIMEOUT = 300.0
```

Add to runner block as sixth test.

- [ ] **Step 2: Run**

Run: `python3 tests/opencode_delegate/test_delegate_run.py`
Expected: six `✅` lines.

- [ ] **Step 3: Commit**

```bash
git add tests/opencode_delegate/test_delegate_run.py
git commit -m "test(opencode): mid-turn SSE drop produces clean timeout with partial text"
```

---

## Task 15: Update SSE protocol doc for v1.4.6

**Files:**
- Modify: `docs/opencode-sse-protocol.md`

- [ ] **Step 1: Update the "Captured from" line + envelope section**

Open `docs/opencode-sse-protocol.md`. Near the top, change the capture header:

Replace:
```
Captured from `opencode serve` v1.4.3 on 2026-04-15.
```
With:
```
Captured from `opencode serve` v1.4.6 on 2026-04-17.

**Envelope change from v1.4.3:** events now wrap the type+properties in a
`payload` object, along with `directory` and `project` fields:

```json
{
  "directory": "/path/to/project",
  "project": "<project-hash>",
  "payload": {"type": "<event-type>", "properties": {...}}
}
```

The examples below show only the `payload` contents for clarity. When
implementing a parser, read `event.payload.type` and `event.payload.properties`
— the top-level `type`/`properties` fields do NOT exist in v1.4.6.

Some events (notably `sync`-wrapped events) use `payload.aggregateID`
instead of `properties.sessionID` to indicate which session they belong
to.
```

- [ ] **Step 2: Fix the "Session done" section**

Find the `### 12. session.idle` section and replace it with:

```markdown
### 12. Session done (v1.4.6 has no `session.idle` event-type)

Completion is signalled in two overlapping ways:

1. **`message.updated` with `info.finish` ∈ {stop, length, error, cancelled}**
   on an assistant message matching the user message's id as `parentID`,
   with `info.time.completed` set. This is the authoritative per-turn
   completion signal.
2. **`session.status` with `status.type == "idle"`** fires when the session
   transitions back to idle after a turn. Multiple turns may fire idle
   between them; do not rely on it alone to terminate a turn.

Intermediate `message.updated` with `finish == "tool-calls"` indicates
the assistant stopped to run tools; the same turn continues with a new
assistant message carrying the same `parentID`. Do NOT treat
`tool-calls` as terminal.
```

- [ ] **Step 3: Add a note at the bottom about `info.error`**

Append:

```markdown
## Surfacing provider errors

When a model call fails (auth error, rate limit, 402 credits exhausted,
invalid model id, etc.), opencode emits:

```json
{
  "type": "message.updated",
  "properties": {
    "sessionID": "ses_xxx",
    "info": {
      "id": "msg_xxx",
      "parentID": "msg_user_xxx",
      "role": "assistant",
      "error": {"name": "ProviderAuthError",
                "data": {"message": "…", "providerID": "…"}},
      "time": {"created": …}
    }
  }
}
```

A well-behaved client reads `info.error.data.message` and surfaces it to
the user immediately, rather than continuing to wait for `finish` (which
never arrives on errored turns).
```

- [ ] **Step 4: Commit**

```bash
git add docs/opencode-sse-protocol.md
git commit -m "docs: update opencode SSE protocol for v1.4.6 envelope and error surfacing"
```

---

## Task 16: End-to-end manual verification

**Files:** no edits. Live-server check against the running system.

- [ ] **Step 1: Ensure `opencode serve` is running with stderr captured**

```bash
pgrep -af "opencode serve" || nohup opencode serve --port 14096 >/tmp/opencode-serve.log 2>&1 &
curl -s http://127.0.0.1:14096/global/health
```
Expected: `{"healthy":true,"version":"1.4.6"}`

- [ ] **Step 2: Restart the NeuroComputer backend so the rewritten delegate is loaded**

The Python server on port 7000 must NOT be touched per memory. Restart only the test instance if any. If the real server uses hot-loaded neuros (check `core/neuro_factory.py`), the rewrite is picked up on next request; no restart needed. If a restart IS needed, confirm which process before acting and never kill the one on port 7000.

- [ ] **Step 3: Test rapid follow-up via the UI**

In the NeuroComputer web UI (`http://localhost:3000`), open an OpenCode conversation. Send three messages within ~2 seconds:
1. "hi"
2. "what can you do"
3. "list files"

Expected:
- All three receive replies, in order, no silent drops.
- Before this change, only #1 would reply; #2 and #3 would hang.

- [ ] **Step 4: Test error surfacing**

Temporarily set the opencode model to an invalid id via the UI's LLM selector (e.g., a mistyped model name). Send a message.

Expected: a visible error reply carrying opencode's error message (e.g., "model not found"). Not a spinner, not a 5-minute timeout.

- [ ] **Step 5: Confirm `/tmp/opencode-serve.log` stays quiet during normal use**

Tail it during normal chatting. There should be no error spam. Any error that happens must surface in the UI reply before appearing here.

- [ ] **Step 6: No commit — this task is verification only**

If any verification step fails, return to Task 9 or the relevant Task to debug against the live system.

---

## Self-review notes

- **Spec coverage:** Every spec section is implemented:
  - SSEConsumer singleton + per-session bus → Tasks 3, 6, 7.
  - Per-session lock + idle gate → Task 9.
  - Event dispatch table → Task 9 (`_consume_turn`).
  - Error handling → Tasks 9, 12, 14.
  - 10 tests mapped to Tasks 2 (envelope), 4 (filtering), 5-6 (status), 7 (reconnect), 8 (happy path), 10 (rapid regression — THE bug), 11 (multi-step), 12 (error), 13 (idle gate), 14 (mid-turn drop).
  - v1.4.6 envelope doc update → Task 15.
  - Manual verification → Task 16.
- **No placeholders.** Every step has real code or real commands.
- **Type consistency.** `SessionBus` fields (`lock`, `status`, `idle_ev`, `queue`) match between `sse_consumer.py` and callers in `code.py`. `_FINISH_TERMINAL` set used consistently. `_TURN_TIMEOUT` overridable by tests.
- **Scope.** Backend + docs + tests. Frontend untouched. One file rewrite, one new module, one new test package, one doc update.
