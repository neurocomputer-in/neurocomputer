# S6 — Abstract Multi-Agent Talk Neuro

**Master plan:** [`2026-04-28-MASTER-neurolang-integration-plan.md`](./2026-04-28-MASTER-neurolang-integration-plan.md)
**Status:** DRAFT
**Depends on:** S2 (defaults — uses `MAIN_AGENT_ID`)
**Blocks:** S3 (Meeting Rooms refresh)
**ETA:** 60 minutes

---

## Goal

Add a single, uniform primitive **`agent.talk(target_agent_id, message, *, agency_id=None, project_id=None, timeout=30) -> str`** that lets any agent invoke any other agent and receive the reply, without caring whether they're in the same agency, the same project, or even on the same process. This is the substrate the Meeting Rooms feature (S3) needs to become executable, and it's also what enables future "agent-to-agent" features generically.

The neuro is **abstract** in the sense that it works for any pair of agents — `neuro` ↔ `nl_dev`, `nl_dev` ↔ `opencode`, `proposal_writer` ↔ `proposal_reviewer` — without per-pair plumbing.

---

## Background

Each agent already has a `Brain` instance with `Brain.handle(cid, message, agent_id) -> str`. Today, `Brain.handle` is invoked by the user via the chat / WebSocket layer; there's no in-process API for one agent to call another.

`AgentManager` (`core/agent_manager.py`) is the registry; it can resolve `agent_id` → `Agent` → `Brain`. So inter-agent calls only need:

1. A new neuro `agent_talk` that takes `target_agent_id` + `message`, looks up the target via `AgentManager`, and returns the reply.
2. A `cid` (conversation id) convention so multi-turn agent dialogues persist.
3. A loop / depth guard (`MAX_TALK_DEPTH = 4`) using the same `ContextVar` pattern NeuroLang's `agent.delegate` uses.

---

## API contract

```python
# neuros/agent_talk/code.py

async def run(state: dict, **kwargs) -> dict:
    """
    Talk to another agent and return its reply.

    Inputs:
      target_agent_id: str            — required; agent to call
      message:         str            — required; what to say
      agency_id:       str | None     — optional; defaults to MAIN_AGENCY_ID
      project_id:      str | None     — optional; defaults to MAIN_PROJECT_ID
      cid:             str | None     — optional; conversation id; auto-derived if absent
      timeout:         float          — default 30s
    Outputs:
      reply: str                      — target's reply
      cid:   str                      — conversation id used (echo for chaining)
    """
```

Convention: `cid` for an agent-to-agent dialogue is derived as `f"agent_talk:{caller}:{target}"` so successive turns share context. This avoids creating a new conversation per call.

---

## Files to add / edit

### New

- `neurocomputer/core/talk.py` — `talk(target_agent_id, message, *, ...)` async function. Owns the depth-guard ContextVar.
- `neurocomputer/neuros/agent_talk/{conf.json, code.py}` — neuro wrapper around `talk()`.
- `neurocomputer/neuros/agent_list/{conf.json, code.py}` — read-only: returns the list of available `agent_id`s the caller can talk to (filtered by agency).

### Edit

- `neurocomputer/core/agent_manager.py` — expose a `get_agent_or_default(agent_id)` helper that uses `MAIN_AGENT_ID` if `agent_id` is None or unknown.
- `neurocomputer/profiles/neurolang_dev.json` — add `agent_talk`, `agent_list` to its neuro list (so the NL planner can choose them).
- `neurocomputer/profiles/general.json` — same (so `neuro` agent can also call `agent.talk`).

---

## Depth guard

Mirror NeuroLang's `agent.delegate` pattern (see `neurolang/stdlib/agent.py`):

```python
import contextvars
_talk_depth: contextvars.ContextVar[int] = contextvars.ContextVar("_talk_depth", default=0)
MAX_TALK_DEPTH = 4

class TalkDepthExceeded(RuntimeError): ...

async def talk(target_agent_id, message, *, ...):
    depth = _talk_depth.get()
    if depth >= MAX_TALK_DEPTH:
        raise TalkDepthExceeded(f"talk depth {depth} ≥ {MAX_TALK_DEPTH}")
    token = _talk_depth.set(depth + 1)
    try:
        ...
    finally:
        _talk_depth.reset(token)
```

This stops two agents from infinite-looping ("A talks to B, B talks to A, ...") at four turns.

---

## Loop detection — soft fail

If `target_agent_id == caller_agent_id`, return early with an error reply instead of recursing:

```python
if target_agent_id == state.get("__caller_agent"):
    return {"reply": "[talk: refusing to call self]", "cid": cid}
```

**Implementation note:** `__caller_agent` must be injected into `state` by the executor (`core/executor.py`) at the start of each neuro run. Today the executor sets `state["__llm"]`, `state["__prompt"]`, and a streaming callback; this spec adds **one line**: `state["__caller_agent"] = agent_id` (where `agent_id` is the agent_id of the agent that owns this brain instance). If that edit is impractical, fall back to `state.get("__agent_id")` if present, else accept that self-call detection is best-effort.

---

## Implementation Checklist

- [ ] **6.1** Create `core/talk.py` with the `talk()` function, `_talk_depth` ContextVar, `MAX_TALK_DEPTH = 4`, `TalkDepthExceeded`.
- [ ] **6.2** Inside `talk()`, resolve target via `agent_manager.get_agent_or_default(target_agent_id)`. If still unresolvable, raise `ValueError(f"unknown agent: {target_agent_id}")`.
- [ ] **6.3** Compute `cid = f"agent_talk:{caller}:{target}"` if not provided.
- [ ] **6.4** Call `await asyncio.wait_for(target.brain.handle(cid, message, agent_id=target_id), timeout=timeout)`.
- [ ] **6.5** Add `get_agent_or_default(agent_id)` helper to `core/agent_manager.py`.
- [ ] **6.6** Create `neuros/agent_talk/` (`conf.json` + `code.py` calling `talk()`).
- [ ] **6.7** Create `neuros/agent_list/` (returns a list of `{id, name, agency_id}` for all agents in the active agency).
- [ ] **6.8** Add the two new neuros to `profiles/general.json` and `profiles/neurolang_dev.json`.
- [ ] **6.9** Smoke test: from a Python REPL, `await talk("nl_dev", "what is your role?")`. Should return a reply describing the NL dev agent.
- [ ] **6.10** Loop test: build a tiny synthetic test where `agent A` calls `agent B` calls `agent A` — verify `TalkDepthExceeded` raises at depth 4.
- [ ] **6.11** UI test: from the IDE, with the `neuro` agent active, send "ask the nl_dev agent to summarise email Y". Verify the reply contains content authored by `nl_dev`.
- [ ] **6.12** Mark spec `Status: SHIPPED`.

---

## Acceptance criteria

1. **Cross-agent call returns a real reply.** `await talk("nl_dev", "...")` returns a non-empty string from the NL dev agent's brain.
2. **Conversation continuity.** Two successive `talk` calls with the same `(caller, target)` pair share context (verifiable: ask "what was the previous question?" — target should reference it).
3. **Depth limit triggers.** Recursion through 5 levels raises `TalkDepthExceeded`. The neuro converts this into a soft-fail dict `{"error": "talk depth exceeded"}` (not an unhandled exception).
4. **Self-call refused.** `talk("neuro", ...)` from the `neuro` agent returns the refusal string, doesn't recurse.
5. **Catalog visibility.** Both `agent_talk` and `agent_list` appear in the IDE's neuro graph under `kind_namespace="agent"` (existing).

---

## Out of scope

- **Streaming replies.** This round, talk is synchronous (request/reply). Streaming via SSE is a future iteration.
- **Voice agent-to-agent calls** — this primitive is text-only. Voice is the LiveKit / Meeting Rooms layer (S3).
- **Cross-process agents.** All agents live in the same `AgentManager` instance for now.
- **Permissions / rate limits.** Trust all agents in the same agency. Cross-agency talk allowed but not specially gated this round.

---

## Open questions

- **Should `agent.talk` propagate memory / blackboard context?** This round: no — each call uses its own `cid`-keyed conversation. If the caller wants to share state, it should pass it explicitly in the `message`. Future S6.1 may add a `share_memory=True` flag.
- **Should `agent_list` filter by capability ("agents that can do X")?** Defer — listing by id/name/agency is enough for v1.

---

## Notes for the executing agent

- The cleanest analogue is NeuroLang's `agent.delegate` (in `/home/ubuntu/neurolang/neurolang/stdlib/agent.py`). Read it first; the patterns (factory closure, ContextVar depth, soft-fail strings) translate directly.
- `Brain.handle` may be heavy (LLM calls, tool runs). Wrap the `await` in `asyncio.wait_for` with the user's `timeout` so a stuck target doesn't hang the caller.
- Don't add a queue / message bus. This is a direct call.
- Keep `core/talk.py` under 80 lines.
