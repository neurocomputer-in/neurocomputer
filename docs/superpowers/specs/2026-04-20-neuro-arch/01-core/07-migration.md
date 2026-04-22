# 01-core · 07 · Migration

**Status**: drafted. Awaiting user approval.

---

## 1 · Zero-break rule

Every existing neuro, profile, planner output, and event consumer must keep working after each phase of this migration, without any code change in the caller. If a phase breaks compat, it is wrong and gets reverted before the next phase.

Concretely, after every phase:

- `python -m pytest tests/` passes (or, absent tests, the current end-to-end smoke flow runs — start dev servers, send a chat message, see the expected reply).
- Every neuro in `neuros/*` still loads.
- Every existing profile still filters correctly.
- Every current event topic (`node.start`, `node.done`, `task.done`, `stream_chunk`, `thinking`, `node.log`, `task.cancelled`) still fires with identical payloads.

## 2 · Phased rollout

Six phases, each small enough to land in one focused session. Each phase commits independently and verifiable on its own.

### Phase A · Introduce `FlowNeuro` base classes (additive)

- Add `core/flows/__init__.py`, `core/flows/flow_neuro.py` with `FlowNeuro` abstract + hooks.
- Add `core/flows/sequential_flow.py`, `core/flows/parallel_flow.py`. Not yet used by anything.
- Add `core/flows/dag_flow.py` stubbed to forward to the existing `Executor` for now.
- **Runtime behavior unchanged.**
- Verify: existing chat flow end-to-end passes.

### Phase B · Route Brain through `dag_flow` (internal refactor)

- Move `core/executor.py` body into `core/flows/dag_flow.py` as `DagFlow.run`.
- Reduce `core/executor.py` to a thin forwarding shim that calls `DagFlow`.
- `core/brain.py` keeps instantiating `Executor(...)` (shim); behavior identical.
- **Runtime behavior unchanged.**
- Verify: events fire identically; replan loop still caps at 3; task.done still emits in `finally`.

### Phase C · Add class-neuro support (additive)

- Evolve `core/base_neuro.py` to the abstract form (`BaseNeuro` = abstract parent). Keep existing `BaseNeuro(name, fn, inputs, outputs, desc)` constructor signature working via an `@classmethod from_fn(...)` used internally by the fn path.
- Extend `core/neuro_factory.py` with: `ClassEntry`, `FnEntry`, `_pick_main_class`, `InstancePool`, `_inject_deps`, `NeuroHandle`.
- Introduce `_synthesize_flow_class` for pure-conf flows (`"kind": "sequential_flow"`, etc).
- **No existing neuro changes form.**
- Verify: loading `neuros/*` still produces the same catalogue; add a *trivial* new class-neuro (e.g., `neuros/_test_class/`) to verify the new path end-to-end; remove it before merge.

### Phase D · Typed ports + visual metadata (additive in `conf.json`)

- Factory normalizes string-form `inputs`/`outputs` to the object form at load.
- `describe()` emits the new rich shape.
- Add `category`, `icon`, `color`, `summary_md` as optional passthroughs.
- Add `layout.json` sidecar support (read if present, ignored otherwise).
- **No runtime behavior changes.** Only `describe()` output grows.
- Verify: `describe()` old callers still work; pick 3 existing neuros (`echo`, `reply`, `planner`) and upgrade their `conf.json` to the new port shape as a smoke test.

### Phase E · Memory API (new neuro)

- Add `core/memory.py` + a built-in neuro `memory` (accessible via `factory.run("memory", state, op=...)` ).
- Add SQLite backend (`agent_memory.db`).
- Register `memory` name as reserved in the registry.
- **No existing neuro uses it yet.** Pure addition.
- Verify: `memory` neuro reads/writes/lists/deletes. Opens the door for dev-agent and future class-neuros to use it.

### Phase F · Brain call site swap + Executor removal

- Change `core/brain.py` to call `self.factory.run("dag_flow", state, dag=flow)` instead of `Executor(...)`.
- Delete `core/executor.py` shim.
- **This is the only phase that changes a call site.** Verified by end-to-end replay of recent sessions (if logs available) or a manual smoke run covering: greet, skill invocation, planner multi-step, replan, streaming, cancellation.

After Phase F, the architecture defined in `01-core/00` – `06` is fully in place.

## 3 · Phase dependencies

```
A  →  B  →  F
          ↗
C  ─────
D  (independent of A/B/C; can land any time after A)
E  (independent; can land after A)
```

Phases A, C, D, E can be parallelized across sessions. Phase F is the only one requiring A + B + C done first.

## 4 · Rollback story

Each phase lands as a single commit (or small stack). If a phase is later found faulty:

- Phases A, C, D, E: revert the commit — nothing else depended on the additions.
- Phase B: revert replaces the internal relocation; behavior returns to the old Executor.
- Phase F: revert restores the Executor call site. Phases B and C remain; they are additive.

No schema files, no DB migrations, no live-traffic cutover. This is a code-only refactor.

## 5 · Schema version

Decision: **do not bump a `schema` field in `conf.json` during this migration.**

Reasoning:

- The change is additive. Old confs stay valid.
- Adding a version field forces us to define what "v2" means for every conf — premature.
- If we ever need a breaking change, *that* is when we bump.

## 6 · Candidate neuros to opportunistically convert to class form

Not required by the migration. Good candidates for a *separate*, post-migration pass:

- **`planner`**, **`dev_planner`**, **`smart_router`** — currently fn-neuros that produce flows. Class form would let them hold instance-level prompt caches and retry policy as attrs.
- **`opencode_delegate`**, **`openclaw_delegate`** — maintain per-session client connections; class form with `scope="session"` is a natural fit for connection reuse.
- **`neuro_crafter`** — benefits from `setup` to load its code-generation template library once.

None of these are part of this migration. Listed only as next-step candidates.

## 7 · Verification checklist (per phase)

Copy-paste friendly checklist for the session implementing each phase:

- [ ] Existing neuros all load — `len(factory.reg)` unchanged.
- [ ] `catalogue()` and `catalogue(cid)` return the same sets.
- [ ] `describe()` entries contain at least the old keys (`name`, `desc`, and — phase D onward — the new rich keys too).
- [ ] A sample chat request ends with the same reply text as before.
- [ ] `node.start` / `node.done` event sequence unchanged (record once pre-phase, compare post-phase).
- [ ] `task.done` emitted once at the end (no duplicates, no absence).
- [ ] Replan still fires on a neuro returning `replan=True`; still caps at 3.
- [ ] Streaming chunks still arrive with matching `stream_id`.
- [ ] Cancellation: interrupting a running task still surfaces `task.cancelled`.
- [ ] Hot-reload still works — edit a neuro's `code.py`, next call uses new code.

## 8 · Exit criteria for the migration

All of the following hold:

1. Phases A–F merged.
2. `core/executor.py` removed.
3. `core/flows/` exists and contains `FlowNeuro`, `DagFlow`, `SequentialFlow`, `ParallelFlow`.
4. `core/memory.py` ships with SQLite backend; `memory` neuro registered.
5. `core/base_neuro.py` is the abstract parent; fn-entry wrapping is internal.
6. Typed port shape is the default in `describe()`.
7. Zero existing neuro required a change to keep working.
8. End-to-end smoke covered: greet, skill, plan, replan, stream, cancel, hot-reload.

## 9 · Decisions locked

1. **Six phases, additive → call-site swap last.** Each independent + revertible.
2. **No schema version bump.** Additive changes don't need one.
3. **No DB migration.** Memory API is a new store, not a replacement.
4. **Opportunistic class-form conversions of `planner` / delegates** — *not* part of this migration, left as follow-up work.
5. **Per-phase verification checklist** (§7) is part of the definition of done.
6. **Rollback = revert commit.** No special cleanup needed in any phase.

## 10 · Deferred / out-of-scope here

- Multi-process / distributed agent deployments.
- Cross-machine hot-reload (git-sync based).
- Migrating `core/conversation.py` history into the `memory` API.
- Refactoring `core/chat_handler.py` or LiveKit room code — orthogonal.
- Any `neuro_web/` frontend changes — the IDE and UI are separate tracks.
