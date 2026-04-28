# `agent.delegate` — Recursive Flow Composition

> Design spec — locks the 5 design decisions before plan + implementation.

## Goal

Enable one neuro inside a flow to spawn a sub-agent that itself runs the
NL → propose_plan → compile_source → execute pipeline against a sub-task.
This makes flows recursive: the outer flow author doesn't need to know
what the inner flow looks like — `agent.delegate("...")` figures it out.

## Architecture

A factory function `agent.delegate(task: str, **opts) -> Neuro` that
returns a fresh, dynamically-built leaf neuro. The returned neuro carries
the `task` description as a closure. When called with an upstream value,
it runs an internal `propose_plan(task) → compile_source(task) → flow.run(input)`
loop and returns the inner flow's result.

This composes naturally:

```python
flow = web.search | agent.delegate("summarize results and rank by recency")
flow.run("latest transformer papers")
```

Sub-agents inherit the parent's `Memory` context (per Q3) and respect a
`depth` budget (per Q4).

## Public API

```python
def delegate(
    task: str,
    *,
    catalog: Optional[list[str]] = None,
    depth: int = 1,
    model: Optional[str] = None,
) -> Neuro:
    """Build a sub-agent neuro that, at runtime, plans → compiles → runs
    its own flow against `task` and the upstream input."""
```

Returned neuro signature:

```python
def _agent(input_value: Any) -> Any:
    """Runtime: propose_plan(task) on a possibly-filtered registry, then
    compile_source(task) on the same filtered registry, then run that flow
    with input_value as positional input. Inherits active memory."""
```

## Locked Design Decisions

### Q1 — Composition pattern: **Factory** ✓

`agent.delegate(task, **opts)` returns a fresh `Neuro` with `task` baked
into its closure. The returned neuro is created via `@neuro(register=False)`
so dynamic sub-agents do NOT pollute `default_registry`.

The returned neuro's `name` is `f"agent.delegate<{task[:40]}>"` for repr
clarity in `Flow<...>` and Mermaid output. Effects = `frozenset({Effect.LLM})`
(planning is an LLM call). Budget is left at `ZERO_BUDGET` for v1 — accurate
estimation requires recursion into the sub-flow (Phase 2).

### Q2 — Catalog scoping: **Filterable via `catalog=`** ✓

```python
agent.delegate("...", catalog=None)                     # full registry
agent.delegate("...", catalog=["reason.*", "web.*"])    # glob filter
agent.delegate("...", catalog=["neurolang.stdlib.reason.summarize"])  # exact
```

`catalog` is a list of glob patterns matched against neuro names via
`fnmatch.fnmatchcase`. The matching neuros are collected into a fresh
`Registry` instance passed to both `propose_plan` and `compile_source`.

When `catalog=None`, the sub-agent sees `default_registry` as-is.

### Q3 — Memory propagation: **Inherit** ✓

Sub-agent reads/writes the same memory as the parent flow. The
`current_memory()` ContextVar already propagates via `Plan.run()`'s
`set_active_memory(memory)` — sub-flows running inside the agent neuro
inherit this automatically without any extra plumbing.

This means `memory_neuros.store/recall` work transparently across the
parent/sub-agent boundary.

### Q4 — Depth exhaustion: **Raise `DelegationBudgetExhausted`** ✓

```python
class DelegationBudgetExhausted(Exception):
    """Raised when agent.delegate is called with depth=0 or sub-flow
    attempts to recurse past the parent's depth budget."""
```

Each `delegate(...)` call decrements an internal depth counter. When
depth reaches 0, the next call raises. Implementation: pass `depth - 1`
through a ContextVar `_delegation_depth`, defaulting to whatever the
caller set; if a sub-agent inside another sub-agent's flow tries to
delegate, it sees the decremented value.

For v1, depth defaults to `1` — outer flow can delegate, but the
inner sub-flow CANNOT delegate further. Raising depth to 2+ unlocks
multi-level recursion.

### Q5 — Sub-prompt construction: **Just `task`, run with `input` separately** ✓

The agent calls `propose_plan(task)` and `compile_source(task)` using
ONLY the bound task description — the upstream `input_value` is NOT
embedded in the prompt sent to the LLM. After compilation, the sub-flow
is invoked with `flow.run(input_value)`, so the upstream value flows in
as the first positional arg (just like any normal flow).

Why this is cleaner: the LLM plans an abstract pipeline ("search → summarize"),
and the runtime supplies the concrete input. Embedding the input would
inflate prompt cost on every invocation and risk the LLM trying to
literally process the input inside its planning JSON.

## Error Handling

Three failure modes:

1. **Unknown capability** — `propose_plan` returns `missing != []`.
   The agent does NOT raise; it returns a string of the form:
   `f"[delegate: cannot satisfy task — missing: {', '.join(intents)}]"`.
   This is a soft failure that lets the outer flow continue. Hard failure
   would force every caller to wrap delegate in try/except.

2. **Compile failure** — `compile_source` raises `CompileError`. The agent
   catches and re-raises as `DelegationFailed(task, original_error)` so
   the caller's stack trace clearly shows which delegate failed.

3. **Sub-flow runtime error** — propagates up unchanged. The sub-flow's
   exception is the agent's exception.

## Files

| File | Action | Notes |
|---|---|---|
| `neurolang/stdlib/agent.py` | new | Defines `delegate`, `DelegationBudgetExhausted`, `DelegationFailed`, internal `_delegation_depth` ContextVar |
| `neurolang/stdlib/__init__.py` | modify | Add `agent` to imports + `__all__` |
| `tests/stdlib/test_agent.py` | new | 6+ tests (see below) |
| `examples/agent_delegate.py` | new | Live demo: `flow = web.search | agent.delegate(...)` |

## Test Plan

All tests use `llm_fn=` or `monkeypatch.setitem(_PROVIDERS, ...)` — fully
offline:

1. **Happy path** — `delegate("summarize")(text)` returns the summary
   string from a faked sub-flow.
2. **Catalog filter — glob match** — `catalog=["reason.*"]` excludes
   `web.search` from the sub-agent's view.
3. **Catalog filter — exact match** — `catalog=["neurolang.stdlib.reason.summarize"]`
   exposes only summarize.
4. **Unknown capability soft fail** — planner returns `missing=[{intent: "..."}]`,
   delegate returns `"[delegate: cannot satisfy task — missing: ...]"`.
5. **Depth budget exhausted** — `agent.delegate("x", depth=0)` raises
   `DelegationBudgetExhausted` on call.
6. **Memory inheritance** — sub-flow's `memory.store` is visible to parent's
   `memory.recall` after `flow.run(..., memory=mem)`.
7. **Compose with `|`** — `flow = upstream_neuro | agent.delegate("...")`
   builds a proper Flow; the returned neuro's name appears in
   `flow.neuros()`.
8. **No registry pollution** — `len(default_registry)` is unchanged after
   `agent.delegate("...")` is called.

## Out of Scope (v1)

- Accurate budget rollup (requires inner-flow introspection at delegate time —
  but `task` is just a string, so we don't know what neuros yet).
- Streaming sub-flow output to parent.
- Async sub-agents (the synchronous path runs `flow.run()` which spins its
  own event loop — fine for v1).
- Cycle detection beyond `depth` (`depth=1` makes cycles impossible at v1).
