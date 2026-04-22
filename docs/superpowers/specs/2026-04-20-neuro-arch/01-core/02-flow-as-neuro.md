# 01-core · 02 · Flow as neuro

**Status**: drafted. Awaiting user approval.

---

## 1 · Thesis

Composition is itself a neuro. The category of neuros is closed under composition: combining neuros yields another neuro with the same contract (`async run(state, **kw) → dict`).

Implementation: introduce `FlowNeuro` — a `BaseNeuro` subclass whose `run` orchestrates children. Every composite form (DAG interpreter, sequential pipeline, parallel fan-out, loop, ReAct orchestrator) is a `FlowNeuro` subclass. The executor class disappears as a separate concept; its logic lives inside `FlowNeuro.run`.

## 2 · Class hierarchy

```
BaseNeuro             ← abstract; defines async run(state, **kw) -> dict
 ├─ (user leaf neuros, or fn-neuros wrapped by the factory)
 └─ FlowNeuro         ← abstract composite; has children, orchestration hooks
     ├─ DagFlow       ← interprets a JSON DAG at runtime (backward compat)
     ├─ SequentialFlow ← runs children in declared order, passes state through
     ├─ ParallelFlow  ← runs children concurrently, merges outputs
     └─ (user composite neuros)
```

All of these remain callable as `factory.run("name", state, **kw)`. The caller never branches on leaf vs flow.

## 3 · The `FlowNeuro` base

```python
class FlowNeuro(BaseNeuro):
    uses:     list[str] = []   # inherited — children are deps, by name
    children: list[str] = []   # ordered list of child names (for flows that care about order)
    replan_policy: str = "inherit"  # "inherit" | "never" | "bounded:N"

    async def run(self, state, **kw) -> dict:
        raise NotImplementedError  # concrete flows implement

    # Optional hooks subclasses can override; default no-ops.
    async def before_child(self, name, params, state): pass
    async def after_child(self, name, out, state): pass
    async def on_child_error(self, name, exc, state) -> str:
        # Return: "skip" | "replan" | "abort"
        return "replan"
```

- `uses` and `children` may overlap. `uses` is the set of dependency names (injected as handles); `children` is the subset the default iteration will walk in order. Flows that build their graph dynamically (like `DagFlow`) don't populate `children` — the graph comes from params.
- `replan_policy` is *per-flow*. `"inherit"` defers to the caller (current behavior). `"never"` disables replanning inside this flow. `"bounded:N"` caps replan rounds at N.

## 4 · Built-in flows

### 4.1 · `SequentialFlow` — ordered pipeline

```python
class SequentialFlow(FlowNeuro):
    async def run(self, state, **kw):
        out = {}
        for name in self.children:
            await self.before_child(name, kw, state)
            child_out = await getattr(self, name).run(state, **kw)
            state.update(child_out)
            out.update(child_out)
            await self.after_child(name, child_out, state)
        return out
```

Usage (conf only, zero code):

```json
{
  "name": "greet_then_echo",
  "description": "Say hi, then echo the user.",
  "kind": "sequential_flow",
  "children": ["greet", "echo"],
  "uses": ["greet", "echo"]
}
```

The factory sees `"kind": "sequential_flow"` and builds a `SequentialFlow` subclass on the fly. No `code.py` needed for pure-conf flows.

### 4.2 · `ParallelFlow` — fan-out

```python
class ParallelFlow(FlowNeuro):
    merge_key: str = None   # if set, each child's output is stored under state[merge_key][name]

    async def run(self, state, **kw):
        tasks = {
            name: asyncio.create_task(getattr(self, name).run(state, **kw))
            for name in self.children
        }
        results = {name: await t for name, t in tasks.items()}
        if self.merge_key:
            state.setdefault(self.merge_key, {}).update(results)
            return {self.merge_key: state[self.merge_key]}
        merged = {}
        for r in results.values():
            merged.update(r)
        return merged
```

Concurrency safety: `ParallelFlow` assumes children don't write conflicting keys; if they do, later-finishing task's write wins (merge order is arrival order). `merge_key` scopes outputs per-child to avoid collisions.

### 4.3 · `DagFlow` — JSON DAG interpreter (backward compat)

`DagFlow` subsumes today's `core/executor.py`. It accepts a DAG as a parameter and walks it the same way the current executor does.

```python
class DagFlow(FlowNeuro):
    async def run(self, state, *, dag, **kw):
        node = dag["start"]
        nodes = dag["nodes"]
        out_acc = {}

        while node:
            spec = nodes[node]
            name = spec["neuro"]
            params = spec.get("params", {})
            try:
                child_out = await self.factory.run(name, state, **params)
            except Exception as exc:
                action = await self.on_child_error(name, exc, state)
                if action == "skip":
                    node = spec.get("next"); continue
                if action == "abort":
                    break
                state["__needs_replan"] = True
                break
            state.update(child_out)
            out_acc.update(child_out)
            await self.after_child(name, child_out, state)
            node = spec.get("next")

        return out_acc
```

Key property: **every existing planner/smart_router output (JSON DAG) runs via `DagFlow` unchanged.** The Brain calls `factory.run("dag_flow", state, dag=plan["flow"])` instead of instantiating `Executor` directly. Behavior is identical; locus is now a neuro.

Replan, thinking-extraction, streaming, ReAct observation logging — all the side channels the current `Executor` manages — live inside `DagFlow.run` by consuming the same `state["__env_state"]` / `state["__pub"]` / `state["__stream_cb"]` conventions.

## 5 · Fractal composition

Because a `FlowNeuro` is itself a `BaseNeuro`, a flow may appear *inside* another flow anywhere a neuro name is allowed.

```json
{
  "name": "research_then_write",
  "kind": "sequential_flow",
  "children": ["research_flow", "draft_reply"],
  "uses":     ["research_flow", "draft_reply"]
}
```

Here `research_flow` is itself a `SequentialFlow` (search → rank → summarize). The outer flow neither knows nor cares about the inner's shape — it just awaits its `run`. The IDE renders this as a collapsible node.

## 6 · Children declaration — `uses` vs `children` vs dynamic

Three ways a flow knows its children:

| mechanism                 | when to use                                                          | where declared          |
|---------------------------|----------------------------------------------------------------------|-------------------------|
| `uses` + `children` attrs | static, named children, order matters                                | class attr or conf.json |
| `uses` only               | named deps, graph built dynamically in `run`                          | class attr or conf.json |
| dynamic / param-driven    | children come from a `dag`/`flow` param at call time                  | runtime (e.g. `DagFlow`)|

Mixing is fine: a flow can declare static `uses` plus accept runtime children.

## 7 · Executor collapse

The current `core/executor.py` becomes the implementation body of `DagFlow.run`. The `Executor` class is **not** deleted in the same change — it is kept as a thin forwarding shim for one release, then removed in `07-migration.md`.

Side effects the current executor handles and where they move:

| current Executor concern         | new home                                                            |
|----------------------------------|---------------------------------------------------------------------|
| walking `{start, nodes}`         | `DagFlow.run`                                                       |
| publishing `node.start/node.done`| `DagFlow` (unchanged event names)                                    |
| streaming chunks                 | `DagFlow` (unchanged contract)                                       |
| replan loop (≤3)                 | `DagFlow`; `replan_policy` attr makes it tunable                     |
| `on_error` per-node              | `DagFlow` consults `on_child_error` hook                             |
| ReAct observation logging        | `DagFlow` (unchanged `__env_state` writes)                           |
| task-level `task.done` finally   | `DagFlow.run`'s `finally`                                           |

External call sites in `core/brain.py` change from:

```python
exe = Executor(flow, factory, state, pub)
self._launch(cid, exe, state)
```

to:

```python
state["__pub"] = self._pub_for(cid)
await self.factory.run("dag_flow", state, dag=flow)
```

Behavior observed by agents, UI, and tests is unchanged.

## 8 · Replan semantics live inside the flow

Today, replanning is a fixed policy baked into `Executor` (max 3 rounds, always re-invokes `__planner`). In the new shape:

- `DagFlow` keeps the existing 3-round replan (backward compat).
- A new `ReactFlow` (defined in `03-react-orchestrator/`) can choose a richer replan strategy — replan on observation divergence, budget-bounded, hierarchical.
- A user-authored `FlowNeuro` subclass can set `replan_policy = "never"` to opt out.

Flow owns its own orchestration discipline.

## 9 · Writing a custom flow (example)

Retry-with-backoff, as a reusable `FlowNeuro`:

```python
class RetryFlow(FlowNeuro):
    uses = []  # child name comes from param at call time

    async def run(self, state, *, neuro, params=None, retries=3, backoff=1.0):
        params = params or {}
        last_exc = None
        for attempt in range(retries):
            try:
                return await self.factory.run(neuro, state, **params)
            except Exception as e:
                last_exc = e
                await asyncio.sleep(backoff * (2 ** attempt))
        raise last_exc
```

Used inline in a DAG:

```json
{"neuro": "retry_flow", "params": {"neuro": "flaky_api_call", "retries": 5}, "next": "n1"}
```

`retry_flow` is itself a neuro, so it slots into any composition.

## 10 · Decisions locked

1. **`FlowNeuro` is a `BaseNeuro`**. Composition produces a neuro. Uniform contract at every depth.
2. **Built-ins shipped v1**: `SequentialFlow`, `ParallelFlow`, `DagFlow`. Users can subclass any of these.
3. **Pure-conf flows allowed**: setting `"kind": "sequential_flow"` in `conf.json` with a `children` list needs no `code.py`. Factory synthesizes a subclass.
4. **`DagFlow` is the backward-compat path** — all current JSON flows keep working unchanged.
5. **Executor class retires** — its code lives inside `DagFlow.run`. A shim stays for one release, then gone.
6. **Orchestration policy is per-flow** — replan, error handling, streaming, observation logging are decisions the flow itself makes, not global constants.
7. **Fractal guarantee** — flows inside flows to any depth, because a flow is a neuro.
8. **Hooks (`before_child` / `after_child` / `on_child_error`)** are the extension points that keep subclasses small.

## 11 · Deferred to later subdocs

- State scoping rules (how `state` namespaces interact when a flow contains flows) → `03-state-and-memory.md`.
- Factory changes to support `"kind"` dispatch for pure-conf flows → `05-factory-and-executor.md`.
- Typed children / edge declarations for IDE rendering → `06-typed-io-and-ide-seams.md`.
- `Executor`-to-`DagFlow` migration sequence → `07-migration.md`.
- `ReactFlow` design → `03-react-orchestrator/`.
