# 01-core · 03 · State and memory

**Status**: drafted. Awaiting user approval.

---

## 1 · Three scopes

Every neuro sees state through exactly three layers. No more, no less.

| layer           | lifetime                            | owned by    | access pattern                                       |
|-----------------|-------------------------------------|-------------|------------------------------------------------------|
| **session**     | while the session (cid) runs        | session     | in-process dict, passed to every `run`               |
| **agent**       | forever, per agent                  | agent       | `memory` API neuro (read/write), durable backend     |
| **shared**      | forever, cross-agent (opt-in)       | system      | `memory` API neuro with `scope="shared"`, governance |

A class-neuro's own `self.*` attributes inherit the scope declared on the class (see `01-primitive-class-vs-fn.md` §6). That's a *fourth kind of state* conceptually, but mechanically it's just Python instance state whose lifetime is managed by the factory pool — it is not part of the memory contract.

## 2 · Session state (the `state` dict)

Unchanged from today in shape: a plain `dict` passed to every `run`. Mutations persist for the rest of the session. Returned dicts are merged in by the caller.

### 2.1 · Namespacing rules

To keep composition sane when flows contain flows, we formalize three key kinds:

| prefix       | meaning                                                    | who writes                          |
|--------------|------------------------------------------------------------|-------------------------------------|
| `__<name>`   | system-owned (e.g. `__llm`, `__cid`, `__pub`, `__factory`) | runtime / factory / brain           |
| `<name>.<k>` | neuro-owned, namespaced by neuro name                      | the neuro that owns the key         |
| `<plain>`    | flow-level scratch (e.g. `goal`, `reply`)                  | any neuro in the current flow frame |

Rules:

- System keys (`__*`) are reserved. User neuros may read, may not write.
- Neuro-owned keys use `neuro_name.key` form: `research_flow.last_query`, `memory.pending_writes`. Factory does not enforce this — it's a convention, but linters / the IDE can warn on unnamespaced writes from class-neuros.
- Plain keys are fair game within a flow. Collisions across sibling neuros are the flow author's problem.

### 2.2 · Scoping inside composite flows

Today: all children share the same `state`. A child's `out` is merged in, subsequent children see it.

Keep this as v1 default (zero migration). But allow flows to **scope** children by wrapping in a sub-dict:

```python
class ScopedFlow(FlowNeuro):
    async def run(self, state, **kw):
        child_state = dict(state)       # shallow copy of system keys
        child_out   = await self.child.run(child_state, **kw)
        # only promote explicit outputs
        return {"child_result": child_out}
```

This is a flow-level decision, not a runtime feature. No magic. Just a pattern.

### 2.3 · Current reserved keys

Catalog the ones in use today (from `core/brain.py` and `core/executor.py`):

- `__factory`, `__history`, `__conv`, `__cid`, `__dev`, `__planner`
- `__llm`, `__prompt`, `__llm_provider`, `__llm_model`, `__llm_selection_type`
- `__env_state`, `__env_context`
- `__pub`, `__stream_cb`, `__streamed`
- `__needs_replan`, `__logs`, `__thinking`

These stay. Documenting them here as the canonical list. Future additions must follow the `__` convention and be listed in this doc.

## 3 · Agent memory (persistent)

Agent memory is any state that must outlive a session. It is stored via a backend (filesystem / sqlite / vector DB — see §6) and accessed through the `memory` API neuro.

### 3.1 · Why not `self.foo` on a class-neuro?

Because:

- `self.foo` has no durability guarantee — agent restart drops it unless the neuro manually persists.
- `self.foo` has no query / search / TTL / atomic update.
- `self.foo` doesn't share across neuros in the same agent.

Class-neuro instance state is appropriate for *warm caches and working state*. For durable memory, go through the API. This keeps persistence policy in one place.

### 3.2 · Key shape

```
<scope>:<agent_id>/<neuro_name>/<key>
```

- `scope`: `agent` or `shared`.
- `agent_id`: the agent owning this memory (e.g., `neuro`, `neuro_abc123`).
- `neuro_name`: the neuro that stored the record (prevents cross-neuro clobbering).
- `key`: user-chosen, free-form.

A neuro writing `agent://user.preferences.theme` gets keyed as `agent:<agent_id>/<caller_name>/user.preferences.theme`. The API neuro injects `<agent_id>` and `<caller_name>` from the session state.

## 4 · Shared memory (cross-agent, opt-in)

Cross-agent memory exists for scenarios where multiple agents need a common view (e.g., a team of agents working on the same project, a global knowledge base).

- Access requires the neuro to declare `memory.shared` intent (either in `conf.json` `permissions: ["memory.shared"]` or at call time via a dedicated API).
- Writes from one agent are visible to others by key (not by agent id).
- Governance (who can write, conflict resolution, quota) is deferred — v1 ships a permissive open model, documentation warns callers, tightening comes later.

## 5 · The `memory` API neuro

A single built-in neuro named `memory` exposes read / write / list / search.

### 5.1 · Operations (v1)

```json
{"op": "read",   "key": "user.preferences.theme"}
{"op": "write",  "key": "user.preferences.theme", "value": "dark", "ttl": null}
{"op": "delete", "key": "user.preferences.theme"}
{"op": "list",   "prefix": "user.preferences."}
{"op": "search", "query": "theme", "top_k": 5}   // vector-backed if available, keyword fallback
```

Usage inside another neuro:

```python
async def run(state, **kw):
    theme = (await state["__factory"].run("memory", state,
                                          op="read",
                                          key="user.preferences.theme")).get("value")
    ...
```

### 5.2 · Scope selector

All ops accept `scope="agent" | "shared"` (default `"agent"`).

### 5.3 · Shape of results

Read/list/search return `{"value": ..., "meta": {"ts", "ttl", "source_neuro"}}` or `{"items": [...]}` (for list/search). Write returns `{"ok": true, "ts": ...}`.

## 6 · Pluggable backends

- v1 ship a single backend: **SQLite** file at `agent_memory.db`, table `kv(scope, agent_id, neuro_name, key, value_json, ts, ttl_ts)`. Simple, durable, easy to inspect.
- v2 add: filesystem (dir-tree), Redis (ephemeral), vector DB (embedding search).
- Backend choice is a single line in agent config: `memory.backend: "sqlite" | "fs" | ...`. Neuros don't see the backend.

## 7 · Migration / compatibility

- **All current `state["__*"]` keys remain.** No neuro needs to change.
- **Factory injection (`__llm`, `__prompt`) keeps working.** See `05-factory-and-executor.md` for the factory's role.
- **No existing neuro uses a durable memory store today.** This subdoc introduces the API; nothing is replaced, only added.
- Later, we may migrate `conv` history (currently in `core/conversation.py` + `db.py`) to use the `memory` API under the hood. That is a *refactor*, not a behavior change.

## 8 · Decisions locked

1. **Three scopes only**: session (dict), agent (persistent), shared (cross-agent). Simpler than arbitrary scopes; covers every real use case.
2. **Keep `state` as a dict** for v1. Typed context object is deferred — no forcing function today, would churn every existing neuro.
3. **Naming convention for session keys**: `__system`, `neuro_name.key`, `plain_scratch`. Enforced by convention + lint, not runtime.
4. **Agent memory accessed only through the `memory` API neuro**. No direct DB access from neuros.
5. **Key shape**: `<scope>:<agent_id>/<neuro_name>/<key>`. Implicit fields injected by the API neuro.
6. **Shared memory opt-in** via `permissions` in `conf.json`. Governance deferred.
7. **SQLite backend ships v1**. Filesystem / vector / Redis v2+.
8. **`__*` reserved key list** is documented here and is the canonical registry. Any new reserved key must be added here.

## 9 · Deferred

- Typed context object (migrating `state` dict to a structured record): evaluate after v1.
- Cross-agent governance (quotas, conflict resolution, permission model beyond coarse allow/deny).
- Vector search integration (backend-specific, picks up with first memory-aware neuro that needs it).
- Neuro-Dream hooks (background memory consolidation / summarization) — belongs in `99-future/`.
- Migrating `Conversation` history into the memory API — non-blocking refactor, separate effort.
