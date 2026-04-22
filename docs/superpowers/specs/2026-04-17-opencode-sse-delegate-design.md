# OpenCode Delegate — SSE-driven, concurrency-safe redesign

**Status:** Draft · 2026-04-17
**Owner:** backend (delegate) · **Frontend:** already integrated (see prior plan)

## Context

The OpenCode provider in NeuroComputer currently **drops every follow-up user message** in a session that is still processing the previous turn. Users see one reply, then silence forever. Direct log evidence (`/tmp/oc-delegate.log`, live SSE tap on `/global/event`):

- Turn 1 of any session replies fine.
- Turn 2+ sent while `session.status == busy` is stored by opencode (HTTP 200, visible in `/session/{id}/message`) but **never triggers model generation**. After the current turn completes, the queued messages stay orphaned — no `parent` assistant child is ever produced.
- The delegate polls for an assistant child that will never exist, times out after 300 s, and returns `"(no response)"`.

Two layers of pain compound the bug:

1. **Delegate architecture.** `neuros/opencode_delegate/code.py` on `dev` currently uses POST + polling. Multiple user turns = multiple threads POSTing concurrently to the same opencode session, with no serialization and no session-status awareness.
2. **Reverted SSE attempt.** Commit `a1541ce5` rewrote the delegate to use opencode's SSE event stream — the correct architecture — but it never worked because of four concrete bugs (see below) and was reverted to POST+polling. The frontend side of that work (OpenCodeMessage, ToolCallCard, `appendToolCall`/`appendStep` reducers, LiveKit handlers) shipped anyway and is still live; only the backend needs fixing.

This spec defines the backend-only rewrite to land the SSE architecture correctly, permanently, and without touching the shipped frontend.

## Goals

1. **Correctness under concurrent sends.** Two rapid messages in the same conversation both receive replies — no silent drops.
2. **Single authoritative event source.** opencode's `/global/event` SSE stream is the sole input for streaming text, tool calls, step progress, completion, and errors. No polling.
3. **Errors surface.** Model failures, rate limits, 402s, etc. come back to the user as error text, not as 300 s timeouts.
4. **Real-time streaming.** Token-by-token deltas via `message.part.delta` reach the frontend without polling jitter.
5. **Resilience.** SSE disconnect → reconnect with backoff, resync without losing in-flight turns.

## Non-goals

- Frontend changes. The UI (`OpenCodeMessage`, `ToolCallCard`, Redux reducers, LiveKit event handlers) is already wired and stays as-is.
- Upstream opencode changes. We adapt to its API; we do not modify it.
- Persisting SSE event state across NeuroComputer server restarts. A restart kills in-flight turns — acceptable, same as today.

## Why the previous SSE attempt (`a1541ce5`) failed

Four bugs, all diagnosable from the live SSE tap on a running `opencode serve 1.4.6`:

1. **Wrong endpoint.** Code opened `GET /event`. Real path is **`GET /global/event`** (confirmed in OpenAPI at `/doc`).
2. **Wrong envelope parsing.** Events arrive as
   `{"directory": "...", "project": "...", "payload": {"type": "...", "properties": {...}}}`.
   The code read `event["type"]` and `event["properties"]` at the top level — both always empty — so every branch fell through to a no-op.
3. **Wrong done-signal.** Code watched for a literal `session.idle` or `session.turn.close` event type. opencode 1.4.6 signals completion via
   - `message.updated` with `info.role == "assistant"`, matching `parentID`, and `info.finish in {"stop","length","error","cancelled"}`, and/or
   - `session.status` with `status.type == "idle"`.
   Neither `session.idle` nor `session.turn.close` appears in the v1.4.6 event stream.
4. **No busy-state gating.** Even with the stream parsed correctly, the delegate still POSTed on demand. Rapid sends while `session.status == busy` would still be dropped by opencode.

All four are addressed explicitly in this design.

**Doc-drift note.** `docs/opencode-sse-protocol.md` documents v1.4.3's flat envelope (`{type, properties}`). v1.4.6 wraps it in `payload`. Updating that doc is part of this work.

---

## Architecture

Single process-wide SSE consumer. Per-`oc_session_id` coordination primitives. Each `run()` call registers its interest, takes the session lock, gates on idle, POSTs, and consumes events from its session's queue until its own turn completes.

```
┌──────────────────────────────────────────────────────────────────┐
│  SSE consumer (singleton, background asyncio task)               │
│    GET /global/event   (persistent, reconnect w/ backoff)        │
│    parse data: lines → event.payload.{type, properties}          │
│    route by properties.sessionID | payload.aggregateID           │
│                     │                                             │
│                     ▼                                             │
│    SessionBus[sid] = {                                            │
│       lock:     asyncio.Lock                                      │
│       status:   "idle" | "busy" | "unknown"                       │
│       idle_ev:  asyncio.Event   (set when status flips to idle)   │
│       queue:    asyncio.Queue   (per-session fanout)              │
│    }                                                              │
└──────────────────────────────────────────────────────────────────┘
                               ▲
                               │ put(event)
                               │
┌──────────────────────────────┴───────────────────────────────────┐
│  run(state, task) — one per user turn                            │
│                                                                   │
│   cid = state["__cid"]                                            │
│   sid = get_or_create_opencode_session(cid)                       │
│   bus = SessionBus.get(sid)   # creates lazily                    │
│                                                                   │
│   async with bus.lock:                        ← serializes turns  │
│     await wait_for_idle(bus, timeout=60)      ← pre-POST gate     │
│     bus.status = "busy"  # optimistic                             │
│     msg_id = "msg_" + uuid4().hex[:20]                            │
│     await POST /session/{sid}/message {msg_id, parts:[text]}      │
│     async for evt in iter_bus(bus):                               │
│         dispatch(evt):                                            │
│            message.part.delta  → stream_callback(delta)           │
│            message.part.updated.tool      → pub("opencode.tool")  │
│            message.part.updated.step-*    → pub("opencode.step")  │
│            message.updated.info.error     → record err, break     │
│            message.updated.info.finish ∈  → record text, break    │
│                  {stop,length,error,cancelled} AND parentID==msg_id │
│     return {"response": text, "__streamed": True, ...}            │
└──────────────────────────────────────────────────────────────────┘
```

### Component 1: `SSEConsumer` (module-level singleton)

**Responsibility:** own one persistent `aiohttp` GET on `/global/event`; parse SSE; fan out events to per-session buses.

**Interface:**
- `await SSEConsumer.start()` — idempotent; launches the background task on first call.
- `bus = SSEConsumer.bus_for(sid)` — returns (or creates) the `SessionBus` for a given opencode session id.
- Internal: on each parsed event, look up `sid = event.payload.properties.sessionID` (or `aggregateID` for `sync` wrappers), push the event into `bus.queue`, and update `bus.status` / `bus.idle_ev` when the event is a `session.status`.

**Reconnection:**
- On disconnect (aiohttp raises, `resp.closed`, or natural EOF), sleep `min(2 ** n, 30)` seconds and reopen.
- After reconnect, mark all known buses as `status="unknown"` so the next turn re-gates. Do NOT replay missed events; in-flight turns inside `run()` that were mid-consume observe a local timeout instead of deadlocking (see Error Handling).

**Lifetime:** lives for the lifetime of the Python server process. No shutdown hook required — daemon task dies with interpreter.

### Component 2: `SessionBus` (per opencode session)

**Fields:**
- `lock: asyncio.Lock` — only one turn at a time per session. Any `run()` holding this lock "owns" the next POST-and-consume cycle.
- `status: Literal["idle","busy","unknown"]` — last seen `session.status.status.type`. `"unknown"` after reconnect or before first event.
- `idle_ev: asyncio.Event` — set when status transitions to `idle`, cleared on `busy`. Allows pre-POST waiting without polling.
- `queue: asyncio.Queue[dict]` — bounded (e.g. `maxsize=2048`); SSEConsumer puts, `run()` consumers get. Bound prevents runaway memory if a run is abandoned.

**Ownership:** created lazily by `SSEConsumer.bus_for(sid)` and kept in a process-wide dict keyed by `sid`. Never freed during the process lifetime — session count is bounded by distinct conversations and is small.

### Component 3: `run(state, task, …)` — the delegate entry

**Step-by-step:**
1. Resolve `cid`, `pub`, `stream_callback`, workdir from state as today.
2. `await SSEConsumer.start()` (idempotent).
3. `sid = await get_or_create_opencode_session(cid)` — keep today's logic, including `data/opencode_sessions.json` cache.
4. `bus = SSEConsumer.bus_for(sid)`.
5. `async with bus.lock:` (serializes concurrent turns on same session)
   - If `bus.status != "idle"`: `await asyncio.wait_for(bus.idle_ev.wait(), timeout=60)`. If it times out, proceed anyway **only if** status is `"unknown"` (post-reconnect); otherwise fail fast with "OpenCode session is stuck busy" so the user gets feedback instead of a 5-minute hang.
   - Generate `msg_id = "msg_" + uuid4().hex[:20]`.
   - `await POST /session/{sid}/message` with payload identical to today's delegate: `{"messageID": msg_id, "mode": "build", "parts": [{"id": "prt_…", "sessionID": sid, "messageID": msg_id, "type": "text", "text": task}]}`. Use a short POST timeout (10 s) — POST acknowledges storage, not completion; we get completion from SSE.
   - `bus.idle_ev.clear()` immediately after POST so nothing else enters the lock prematurely. (`status` will flip to `busy` via the next `session.status` event; clearing pre-emptively avoids a race.)
   - Consume from `bus.queue` until termination (see next section). For each event, accept it only if it belongs to our turn:
     - `message.part.*` events: look up the event's `messageID` in a local set of "my message ids" populated from `message.updated` events whose `info.parentID == msg_id`.
     - `message.updated` events: accept if `info.parentID == msg_id` (covers every assistant message opencode emits for our turn, including multi-step tool-call chains — each carries the same `parentID`).
     - All other sessions' events are already filtered upstream by `bus_for(sid)`.
6. Return `{"response": text, "status": "success" | "error", "reply": ..., "__streamed": True}`.

### Event dispatch inside `run()`

Event structure expected: `evt["payload"]["type"]`, `evt["payload"]["properties"]`.

| `payload.type` | condition | action |
|---|---|---|
| `message.part.delta` | `field == "text"` and part belongs to our turn's assistant msg | `await stream_callback(delta)`; append to `accumulated` |
| `message.part.updated` | `part.type == "text"`, has `text` | replace `accumulated` with full text (snapshot) |
| `message.part.updated` | `part.type == "tool"` | `await pub("opencode.tool", {...})` w/ `callID`, `tool`, `status`, `input`, `output`, `title`, `time` |
| `message.part.updated` | `part.type == "step-start"` | `await pub("opencode.step", {"type":"step-start", "stepID":…})` |
| `message.part.updated` | `part.type == "step-finish"` | `await pub("opencode.step", {"type":"step-finish", "stepID":…, "reason":…, "tokens":…})` |
| `message.updated` | `info.role == "assistant"`, `info.parentID == msg_id`, `info.error` non-null | capture `info.error` → error reply, break |
| `message.updated` | `info.role == "assistant"`, `info.parentID == msg_id`, `info.finish ∈ {stop,length,error,cancelled}` and `info.time.completed` present | break normally |
| `session.status` | `status.type == "idle"` | (handled by SSEConsumer — sets `bus.idle_ev`) only trust to break if we have ALSO seen our completion event; otherwise opencode may be idling between tool-call-driven sub-turns |
| anything else | — | ignore |

**Turn-termination rule:** completion requires a `message.updated` on an assistant message whose `parentID` matches our `msg_id` AND `finish ∈ {stop, length, error, cancelled}`. Multi-step turns (tool-calls → another assistant message → text) may produce intermediate `message.updated` with `finish == "tool-calls"` — these do NOT terminate; keep consuming.

### How this fixes the four old bugs

1. Endpoint is `/global/event`, not `/event`.
2. Envelope parsed as `evt.payload.type` / `evt.payload.properties`.
3. Completion uses `message.updated.info.finish`, not a non-existent `session.idle` event-type.
4. Per-session lock + `idle_ev` gate eliminates the "POST while busy → dropped" window entirely.

---

## Error handling

| Failure | Behavior |
|---|---|
| opencode server down at preflight | existing error reply ("OpenCode server not running…") |
| `get_or_create_opencode_session` fails | existing error reply |
| `POST /session/{sid}/message` returns non-2xx | surface body as error, release lock |
| POST succeeds but no matching `message.updated` arrives within `TURN_TIMEOUT` (default 300 s) | return "OpenCode turn timed out (no completion event received)" as error; `__streamed=True` if any text was accumulated |
| `info.error` seen on assistant message | return the error text from opencode to the user |
| SSE disconnects mid-turn | SSEConsumer reconnects transparently. In-flight `run()` keeps waiting on its queue; if nothing arrives within the turn timeout, it errors out as above. No resync of missed events in v1 — accepted tradeoff. |
| Bus queue overflows (`maxsize=2048`) | log a warning and drop oldest event to make room; this means a pathological runaway would degrade gracefully rather than OOM. In practice 2048 is >> one turn's event count (hundreds). |
| `wait_for_idle` pre-POST times out at 60 s while status is `busy` | error reply: "OpenCode session appears stuck in busy state". Tells us the upstream session is bad; user can switch convs. |

All error paths set `__streamed=True` if partial text was delivered so the brain knows not to double-render.

---

## Testing

Use `superpowers:test-driven-development`. Each test is written first as a failing test, then the code is changed to make it pass.

**Unit tests** (`tests/opencode_delegate/test_sse_consumer.py`, pytest + asyncio):

1. **envelope parser** — given a canned v1.4.6 SSE byte stream, `SSEConsumer` emits the right `{type, properties}` dicts for `message.part.delta`, `message.part.updated` (tool/text/step), `message.updated`, `session.status`.
2. **session filtering** — events for `ses_A` don't leak into `bus_for("ses_B")`.
3. **status tracking** — `session.status.busy` sets `bus.status="busy"` and clears `idle_ev`; `session.status.idle` sets `bus.status="idle"` and sets `idle_ev`.
4. **reconnect** — when the fake server closes the SSE connection, consumer reconnects with backoff; buses switch to `status="unknown"`.

**Integration tests** (`tests/opencode_delegate/test_delegate_run.py`, against a stub HTTP server that mimics opencode's POST + SSE):

5. **single-turn happy path** — POST a message, server emits `message.part.delta` × N, then `message.updated finish=stop` → `run()` returns the accumulated text, `stream_callback` received each delta in order.
6. **rapid follow-up** (regression test for THE bug) — two `run()` calls on the same cid launched concurrently with `asyncio.gather`; stub server emits a full turn for the first, then (on seeing the second POST after idle) emits a full turn for the second. **Both return their respective texts**, in order, with no drops. Without the per-session lock this test fails deterministically.
7. **tool-call multi-step** — stub emits `finish="tool-calls"` then a second assistant message under same `parentID` chain with `finish="stop"`. `run()` does NOT return on the first finish; waits for the real stop.
8. **error surfacing** — stub emits `message.updated.info.error = {message: "model not found"}` → `run()` returns a `status=error` reply with that text, not a timeout.
9. **pre-POST idle gate** — first test starts a slow turn; second `run()` observes `status=busy` and blocks on `idle_ev` until the first completes.
10. **reconnect mid-turn** — stub drops SSE halfway; consumer reconnects; turn times out cleanly with a partial-text error reply (no hang).

**Manual verification** (after unit + integration pass):

- Restart NeuroComputer server + frontend. Open opencode conv. Send two messages within 1 s of each other. Both must show replies (one after the other).
- Send one message, wait for reply. Use up OpenRouter credits if testing against a paid model to confirm `info.error` surfaces as visible text.
- Kill and restart `opencode serve` mid-turn. The current turn should error out with a clean message within `TURN_TIMEOUT`; subsequent turns should succeed.

---

## Rollout

One PR, one commit on `dev`. Frontend stays untouched. Deploy order is irrelevant because the delegate is a self-contained Python module loaded by the executor.

No feature flag; the delegate is the only consumer of opencode and the new implementation is strictly better than current.

## Critical files

- **Rewrite:** `neuros/opencode_delegate/code.py` — new SSE architecture described above.
- **Update:** `docs/opencode-sse-protocol.md` — correct the event envelope for v1.4.6 (`payload.{type, properties}` wrapper), document the `sync` meta-event, note that `session.idle` does not exist and completion is signaled via `message.updated.info.finish`.
- **No changes:** `core/executor.py`, `core/brain.py`, `core/chat_handler.py`, `core/neuro_factory.py`, `data/opencode_sessions.json` semantics, all frontend files.

## Verification

After landing:

1. `pytest tests/opencode_delegate/` — all 10 tests pass.
2. Restart opencode serve with stderr redirected somewhere visible: `nohup opencode serve --port 14096 >/tmp/opencode-serve.log 2>&1 &`
3. Restart NeuroComputer backend. Frontend dev server (`pnpm dev` in `neuro_web/`) stays up.
4. In the UI, open an opencode conversation. Send three rapid messages (within 2 s total). All three must receive replies in order. (Current code: only the first replies.)
5. Change the model to one that will reliably error (e.g. invalid id). Send a message. The UI must show an error text reply, not a spinner + eventual "(no response)".
6. Tail `/tmp/opencode-serve.log` during testing. It should remain near-silent under normal operation; any opencode internal error must surface in the UI before appearing here.

## Tradeoffs explicitly accepted

- **Reconnect dropping missed events.** v1 does not use `sync.seq` numbers to replay events after reconnect. An in-flight turn interrupted by reconnect will time out rather than resume. Acceptable because reconnects are rare and the timeout produces a clear error, not a hang.
- **Unbounded bus dict.** We never free `SessionBus` objects. Memory ≈ O(number of distinct conversations ever opened in this process). Small in practice; can revisit if we ever hit it.
- **No cancellation propagation to opencode.** If the user cancels a turn client-side, we release the lock but opencode keeps running the model. Fine for now; matches current behavior.
