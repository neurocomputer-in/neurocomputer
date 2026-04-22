# 01-core · 05 · Factory and executor

**Status**: drafted. Awaiting user approval.

---

## 1 · Scope of this subdoc

Concrete changes to `core/neuro_factory.py` and retirement of `core/executor.py`. Everything in `01-core/01`–`04` is realized here.

## 2 · Current shape (baseline)

`core/neuro_factory.py` today:

- `_load_all()` walks `neuros/**/conf.json`, calls `_load(path)` per conf.
- `_load` reads `conf.json` + `code.py` + optional `prompt.txt`, `exec`'s the code into a synthetic module, wraps `mod.run` in a `BaseNeuro(name, fn=_runner, ...)` instance, stores in `self.reg`.
- `_runner` is a closure that: resolves provider/model via `model_library`, instantiates `BaseBrain` into `state["__llm"]`, captures stdout, merges LLM thinking into the result.
- `_watch()` polls `conf.json` mtimes every 1s and re-`_load`s on change.
- `run(name, state, **kw)` = `self.reg[name].run(state, **kw)`.
- `set_pattern`/`_filter`/`catalogue`/`describe` implement per-cid visibility.

`core/executor.py` today:

- `Executor(flow, factory, state, pub)` walks the DAG.
- `_run_once()` iterates nodes, calls `factory.run`, merges out into state, publishes events, handles `__needs_replan`.
- `run()` loops `_run_once` up to 3 replan rounds.

## 3 · Target shape

Factory becomes a **two-form loader + instance pool**, with pure-conf flow synthesis. Executor becomes the body of `DagFlow.run`.

### 3.1 · Load-time detection

```python
def _load(path):
    conf = json.load(path)
    module = _exec_module(path.parent / "code.py") if (path.parent / "code.py").exists() else None

    if module and _has_neuro_class(module):
        cls = _pick_main_class(module, conf["name"])
        entry = ClassEntry(cls=cls, conf=conf)
    elif conf.get("kind") in BUILTIN_FLOW_KINDS:
        cls = _synthesize_flow_class(conf)            # pure-conf flow
        entry = ClassEntry(cls=cls, conf=conf)
    elif module and hasattr(module, "run"):
        entry = FnEntry(fn=module.run, conf=conf)     # today's behavior
    else:
        raise LoadError(f"Neuro {conf['name']}: no class, no fn, no kind.")

    self.reg[conf["name"]] = entry
```

`_synthesize_flow_class(conf)` builds a throwaway subclass of the appropriate built-in based on `conf["kind"]`:

```python
def _synthesize_flow_class(conf):
    base = FLOW_KIND_REGISTRY[conf["kind"]]   # {"sequential_flow": SequentialFlow, ...}
    attrs = {
        "uses":     conf.get("uses", []),
        "children": conf.get("children", []),
        "scope":    conf.get("scope", "session"),
    }
    return type(f"_ConfFlow_{conf['name']}", (base,), attrs)
```

### 3.2 · Instance pool

```python
class InstancePool:
    def __init__(self):
        self._instances: dict[tuple[str, str], BaseNeuro] = {}   # (name, scope_key) → instance

    async def get(self, entry, state):
        scope = entry.scope              # "call" | "session" | "agent" | "singleton"
        if scope == "call":
            return await self._create(entry, state)
        key = (entry.name, self._scope_key(scope, state))
        if key not in self._instances:
            self._instances[key] = await self._create(entry, state)
        return self._instances[key]

    def _scope_key(self, scope, state):
        if scope == "session":   return state.get("__cid", "_nosess")
        if scope == "agent":     return state.get("__agent_id", "_default")
        if scope == "singleton": return "_singleton"
        raise ValueError(scope)

    async def _create(self, entry, state):
        if isinstance(entry, FnEntry):
            return entry.as_synthetic_class()()   # always works; scope irrelevant for fns
        cls = entry.cls
        inst = cls()
        inst.name = entry.name
        inst.factory = self._factory_ref
        await self._inject_deps(inst, entry)
        if hasattr(inst, "setup"):
            await _maybe_await(inst.setup())
        return inst
```

### 3.3 · Dependency injection

```python
async def _inject_deps(self, inst, entry):
    for dep_name in getattr(inst, "uses", []):
        if dep_name not in self._factory_ref.reg:
            raise LoadError(f"{entry.name}: unknown dependency '{dep_name}'")
        handle = NeuroHandle(self._factory_ref, dep_name)   # lazy proxy
        setattr(inst, dep_name, handle)
```

`NeuroHandle.run(state, **kw)` forwards to `factory.run(dep_name, state, **kw)`. Going through the factory keeps hot-reload transparent: if `dep_name`'s code changes, the next call picks up the new version.

### 3.4 · Hot-reload

```python
async def _reload(self, path):
    conf = json.load(path)
    name = conf["name"]
    old_entry = self.reg.get(name)

    # Tear down any live instances of the old class
    if old_entry and isinstance(old_entry, ClassEntry):
        for key, inst in list(self.pool._instances.items()):
            if key[0] == name:
                if hasattr(inst, "teardown"):
                    try:    await _maybe_await(inst.teardown())
                    except: pass
                del self.pool._instances[key]

    self._load(path)   # rebuilds entry, reinjects on next use
```

Fn-neuros behave as today: code swap, next call runs new code. No teardown necessary.

### 3.5 · LLM / prompt injection (unchanged pattern)

Today the factory's `_runner` puts `__llm` and `__prompt` into `state` before calling the neuro's `run`. Keep that. In the new path:

- For **fn entries**, the `FnEntry.wrap_call` still does the injection (same code, relocated).
- For **class entries**, injection happens in the factory's `run(name, state, **kw)` method, right before dispatching to the instance's `run` — so the class-neuro sees `state["__llm"]` identically.

Class-neuros may also opt to resolve LLM at `setup` time (once per instance) instead of per-call — but the default `state["__llm"]` contract is preserved.

### 3.6 · `factory.run(name, state, **kw)` — unified call

```python
async def run(self, name, state, **kw):
    entry  = self.reg[name]
    self._inject_system_state(state, entry)            # __llm, __prompt, __factory, ...
    instance = await self.pool.get(entry, state)
    safe_kw  = filter_kwargs(kw, instance, entry)
    out = await instance.run(state, **safe_kw)
    return _coerce_dict(out)
```

Callers (Brain, executor, other neuros) do not change.

## 4 · Executor collapse

`core/executor.py`'s `Executor` class becomes the body of `DagFlow.run`. Translation is literal — lift the loop, keep the event names, keep the replan logic.

### 4.1 · Mapping

| current Executor                                    | new location                                        |
|-----------------------------------------------------|-----------------------------------------------------|
| `Executor._run_once`                                | `DagFlow._run_once` (private)                       |
| `Executor.run`                                      | `DagFlow.run(state, *, dag)`                        |
| `self.pub("node.start", …)`                         | via `state["__pub"]`                                 |
| `self.pub("node.done", …)`                          | via `state["__pub"]`                                 |
| replan loop (≤3)                                    | `DagFlow._run(state, dag)`; cap = `replan_policy`   |
| `asyncio.CancelledError` → `task.cancelled`         | `DagFlow.run`'s `finally`                            |
| `task.done` emission                                 | `DagFlow.run`'s `finally`                            |

### 4.2 · Brain call site

Current (`core/brain.py`):

```python
exe = Executor(flow, self.factory, state, lambda t, d: self._pub(cid, t, d))
self._launch(cid, exe, state)
return "🚀 task started"
```

New:

```python
state["__pub"] = lambda t, d, cid=cid: self._pub(cid, t, d)
task = asyncio.create_task(self.factory.run("dag_flow", state, dag=flow))
self._launch(cid, task, state)
return "🚀 task started"
```

`_launch` keeps its current responsibility: store the task, wire `done_callback` for surfacing failures.

### 4.3 · Shim

For one release, keep `core/executor.py` but reduce it to:

```python
class Executor:
    def __init__(self, flow, factory, state, pub):
        self._factory, self._flow, self._state = factory, flow, state
        state["__pub"] = pub

    async def run(self):
        await self._factory.run("dag_flow", self._state, dag=self._flow)
```

This keeps any third-party code that imports `Executor` working. Remove in the release after `07-migration.md` ships.

## 5 · Compilation model

v1 keeps `exec`-based module compilation. Reasons:

- Hot-reload today is `exec` → new module object; works without dance around `importlib.reload` and stale references.
- `importlib.reload` has subtle traps (module caches, closures capturing old objects). `exec` dodges these by always producing a fresh namespace.
- No observed downside so far. Revisit if v2 needs real module graphs for static analysis.

## 6 · Pub injection

Decision: **`__pub` goes in the `state` dict**, not the instance constructor.

Rationale:

- A class-neuro with `scope="agent"` or `"singleton"` outlives any single session, so a constructor-injected `pub` would be stale.
- `state["__pub"]` is already set per-call today. Keeps uniformity.
- The brain sets `state["__pub"]` per-cid before dispatching.

Inside a flow, children inherit `__pub` by reading the same state. No extra work.

## 7 · Concurrency safety

- `InstancePool` protects `_instances` with an `asyncio.Lock` per `(name, scope_key)` during `_create` — only one `setup` runs per scope, even if two sessions race.
- Hot-reload acquires a registry-level lock briefly; no call enters a half-reloaded entry.
- `ParallelFlow` children share the same state dict; concurrent writers must use `merge_key` or disjoint keys. Documented in `02-flow-as-neuro.md` §4.2.

## 8 · Backward compat

- Every existing neuro in `neuros/*` loads unchanged (fn-entry path).
- Every existing planner/smart_router JSON DAG runs unchanged via `DagFlow`.
- Every existing event (`node.start`, `node.done`, `stream_chunk`, `thinking`, `node.log`, `task.done`, `task.cancelled`) continues to fire with identical payloads.
- `set_pattern`, `catalogue`, `describe` keep working; `describe` gains extra fields but existing callers see a superset.
- `Brain`'s public methods (`handle`, `add_listener`, profile commands) are unchanged.

## 9 · File-level impact

| file                          | change                                                                 |
|-------------------------------|------------------------------------------------------------------------|
| `core/base_neuro.py`          | becomes abstract parent; fn wrapping moves to `FnEntry` (private).     |
| `core/neuro_factory.py`       | load path branches (fn / class / kind); add `InstancePool`; reload handles teardown. |
| `core/executor.py`            | body moves into `DagFlow.run`; shim stays one release.                  |
| `core/brain.py`               | call site of Executor swaps to `factory.run("dag_flow", ...)`.          |
| `core/flows/` (new)           | `__init__.py`, `flow_neuro.py`, `dag_flow.py`, `sequential_flow.py`, `parallel_flow.py`. |
| `core/memory.py` (new)        | memory API neuro (from `03-state-and-memory.md`).                       |
| `neuros/*`                    | no forced changes.                                                      |
| `profiles/*`                  | no changes.                                                             |

## 10 · Decisions locked

1. **Load branches three ways**: existing fn path, new class path, new pure-conf-flow synthesis path.
2. **`InstancePool` manages lifecycle** keyed on `(name, scope_key)`. Scopes: `call | session | agent | singleton`.
3. **Dependency injection via `NeuroHandle` lazy proxies** — hot-reload transparent, no stale references.
4. **Hot-reload tears down live class instances** (`teardown` best-effort, never blocks).
5. **`__pub`, `__llm`, `__prompt` stay in state dict** — uniform for fn and class.
6. **Executor retires into `DagFlow.run`.** Shim keeps existing imports working one release.
7. **`exec`-based compilation stays** for v1. Revisit only if static analysis becomes necessary.
8. **Concurrency safety via per-key `asyncio.Lock`** during instantiation; registry lock during reload.
9. **Zero forced changes to existing neuros / profiles / planners.**
10. **New code organized under `core/flows/`** to keep flow types grouped and imports clear.

## 11 · Deferred

- Real `importlib`-based loader (if/when v2 needs static analysis).
- Distributed instance pool (multi-process agents) — out of scope.
- Per-neuro resource limits (max memory, max duration in `run`) — later.
- Pluggable kind registry for user-defined flow kinds — easy to add, no current driver.
