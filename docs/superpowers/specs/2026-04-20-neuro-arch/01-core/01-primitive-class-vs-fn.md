# 01-core · 01 · Primitive — fn vs class vs hybrid

**Status**: drafted. Awaiting user approval.

---

## 1 · The one contract

Every neuro — leaf or composite, fn-authored or class-authored — satisfies a single runtime protocol:

```python
async def run(self, state: dict, **kwargs) -> dict
```

That is the only thing the rest of the system (factory, executor, IDE, planner) relies on. Everything else is authoring sugar.

- `state` — the shared session dict. Mutations persist, returned dict is merged in by the caller.
- `**kwargs` — the neuro's declared inputs. Filtered by the factory to only those the neuro accepts (existing behavior, preserved).
- return value — a `dict` of outputs. Non-dict returns are coerced to `{}` by the factory (existing behavior, preserved).

## 2 · Two authoring forms

Both forms compile down to a `BaseNeuro` subclass at load time. Callers see a uniform object.

### 2.1 · Fn form (unchanged from today)

Minimal. For stateless leaf neuros. **No migration required** — every existing neuro in `neuros/` already uses this form.

`neuros/echo/code.py`:

```python
async def run(state, *, text):
    return {"reply": f"Echo: {text}"}
```

`neuros/echo/conf.json`:

```json
{
  "name": "echo",
  "description": "Return the supplied text verbatim.",
  "inputs":  [{"name": "text", "type": "str"}],
  "outputs": [{"name": "reply", "type": "str"}]
}
```

The factory wraps the top-level `async def run` in a synthetic `BaseNeuro` subclass whose `run` delegates to the module function.

### 2.2 · Class form (new)

For neuros that need persistent state, lifecycle, sub-neuro ownership, or inheritance.

`neuros/research_flow/code.py`:

```python
from core.base_neuro import BaseNeuro

class ResearchFlow(BaseNeuro):
    uses  = ["search", "summarize", "rank"]   # declared deps, factory injects
    scope = "session"                          # session | agent | singleton | call

    async def setup(self):
        self.cache = {}

    async def run(self, state, *, query):
        hits     = await self.search.run(state, q=query)
        ranked   = await self.rank.run(state, items=hits["items"])
        summary  = await self.summarize.run(state, items=ranked["items"])
        return {"report": summary["text"]}

    async def teardown(self):
        self.cache.clear()
```

`neuros/research_flow/conf.json`:

```json
{
  "name": "research_flow",
  "description": "Search → rank → summarize pipeline.",
  "inputs":  [{"name": "query", "type": "str", "description": "what to research"}],
  "outputs": [{"name": "report", "type": "str"}],
  "scope":   "session",
  "uses":    ["search", "summarize", "rank"]
}
```

`scope` and `uses` are duplicated in `conf.json` on purpose: the IDE / neuro-list / docs tooling must read metadata without importing Python. At runtime, the class attribute is authoritative (if they diverge, factory warns and follows the class).

## 3 · Class inheritance

- Every class-neuro inherits from `BaseNeuro` (leaf) or `FlowNeuro` (composite; see `02-flow-as-neuro.md`).
- User classes may subclass other neuro classes — standard Python MRO applies.
- A `code.py` may define helper classes and utility functions. The factory identifies the neuro class by one of, in order:
  1. an explicit `__main_neuro__ = ClassName` module-level assignment, or
  2. the subclass of `BaseNeuro` / `FlowNeuro` whose `__name__` (case-insensitive) matches `conf.name` in CamelCase, or
  3. if exactly one `BaseNeuro` subclass exists in the module, that one.
- Ambiguity → factory raises a loud error at load time, listing candidates.

## 4 · Lifecycle hooks

| hook                          | required | when called                                            |
|-------------------------------|----------|--------------------------------------------------------|
| `async def setup(self)`       | no       | once per instance, before first `run`                  |
| `async def run(self, state, **kw)` | **yes** | per invocation                                    |
| `async def teardown(self)`    | no       | when instance is disposed (scope expired / reload)     |

- All are `async` for uniformity; sync implementations still work (factory awaits coroutines, calls sync fns directly).
- `setup` runs after `uses` deps are injected — the neuro can reference `self.<dep>` safely in `setup`.
- `teardown` must not raise; if it does, the factory logs and continues (never blocks reload on teardown failure).

## 5 · Dependency injection (`uses`)

- `uses` is a list of neuro names. The factory resolves each against the registry at **instance creation time** and attaches a handle:

  ```python
  self.search = <BaseNeuro proxy for "search">
  ```

- Calling `await self.search.run(state, **kw)` goes through the registry — it respects hot-reload. If `search` is edited on disk, next call uses the new version.
- **Missing dep is a hard error.** If any name in `uses` is not registered, instantiation fails loudly. This prevents silent partial loads.
- Circular `uses` is permitted (A uses B, B uses A): proxies are resolved lazily on first access, so cycle is fine unless mutual `setup` actually needs each other — then it's a runtime error on the first offending `setup`.

## 6 · Instance scope (`scope`)

Controls how long an instance of a class-neuro lives:

| scope         | lifetime                            | instance key       | typical use                          |
|---------------|-------------------------------------|--------------------|--------------------------------------|
| `call`        | per invocation                      | n/a (fresh)        | pure computation, fn-like            |
| `session`     | per session (cid) — **default**     | `cid`              | chat-bound memory, per-user state    |
| `agent`       | per agent, across sessions          | `agent_id`         | long-lived skills, warm caches       |
| `singleton`   | per factory                         | `"_singleton"`     | expensive setup (loaded model, pool) |

- Factory maintains an instance pool keyed on `(neuro_name, scope_key)`.
- Fn-neuros behave as `call` scope trivially (no state to keep).
- `scope` can be set in `conf.json` or as a class attribute; class attribute wins if both present.

## 7 · Hot-reload semantics

| form       | reload behavior                                                                        |
|------------|----------------------------------------------------------------------------------------|
| fn         | new code replaces old; next call uses new code (existing behavior).                    |
| class      | old instances get `teardown`; next call creates a new instance with the new class.     |
| singleton  | teardown on reload; next access triggers fresh `setup`.                                |
| in-flight  | an in-progress `run` finishes with its original class; the swap applies to next call.  |

Factory tracks class-neuro instances per scope key so teardown can run on reload.

## 8 · How factory wraps both forms

Pseudo-code for the unified load path:

```python
def _load(conf_path):
    conf = json.load(conf_path)
    module = exec_module(conf_path.parent / "code.py")

    if has_class(module, BaseNeuro):
        cls = pick_main_neuro_class(module, conf["name"])
        registry[conf["name"]] = ClassNeuroEntry(cls, conf)
    else:
        fn = getattr(module, "run")
        registry[conf["name"]] = FnNeuroEntry(fn, conf)

# Uniform call path:
async def run(name, state, **kw):
    entry = registry[name]
    instance = entry.get_or_create_instance(scope_key_for(state, entry.scope))
    return await instance.run(state, **filter_kwargs(kw, entry))
```

Callers (Executor, Brain, planners) never branch on fn vs class. They call `factory.run(name, state, **kw)` as today.

## 9 · Decisions locked by this subdoc

1. **Single contract**: `async run(state, **kw) -> dict`. Non-negotiable.
2. **Keep the triad** (`conf.json` / `code.py` / optional `prompt.txt`) for both forms. Conf is the machine-readable metadata, code is the implementation, prompt is optional LLM template.
3. **Explicit inheritance** from `BaseNeuro` / `FlowNeuro` for class form (not duck typing). Gives the IDE and linters a static signal.
4. **Async lifecycle hooks**: `setup` / `run` / `teardown`. Only `run` is required.
5. **`uses` declares deps** at class attr level; factory injects at instantiation; resolves via registry (hot-reload aware).
6. **`scope` controls instance lifetime**: `session` default, `agent` / `singleton` / `call` available.
7. **Missing dep = hard error**; ambiguous main class = hard error. No silent failures.
8. **v1 is single-file `code.py`**. Multi-file module directories deferred to v2.

## 10 · Deferred to later subdocs

- `FlowNeuro` specifics, `DagFlow` JSON interpreter → `02-flow-as-neuro.md`.
- Memory API the neuro uses to reach beyond session scope → `03-state-and-memory.md`.
- Registry details, version pinning, profile filtering → `04-registry-and-lib.md`.
- Factory implementation changes and executor collapse → `05-factory-and-executor.md`.
- Typed port format for `inputs` / `outputs` → `06-typed-io-and-ide-seams.md`.
- Zero-break rollout → `07-migration.md`.

## 11 · Impact on existing `core/base_neuro.py`

Current implementation is a wrapper around a fn (see `core/base_neuro.py`). It becomes an abstract parent class with `run` as the only required method. The fn-wrapping behavior moves into an internal `FnNeuroEntry` that is **not** part of the public class hierarchy. Public surface: `BaseNeuro` (leaf) and `FlowNeuro` (composite). No existing neuro imports `BaseNeuro` today, so the rename has zero external breakage.
