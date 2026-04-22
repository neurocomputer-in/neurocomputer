# 02-dev-agent · 02 · Self-modification safety

**Status**: drafted.

---

## 1 · Scope

The dev agent can, by design, overwrite any neuro in the system — including neuros that the rest of the system depends on (`planner`, `smart_router`, `reply`, the built-in flows). That power needs guardrails strong enough that AI drift doesn't brick the running agent, but loose enough that iteration stays fast.

This subdoc is the policy layer on top of the pipeline from `01-robustness-patterns.md`.

## 2 · Contract check (pipeline stage 5, detailed)

A neuro is valid only if it satisfies the runtime contract after load. Checks, in order:

1. `code.py` imports successfully in a throwaway namespace.
2. At least one of:
   - Module-level `async def run(state, **kw)` (fn form).
   - A class inheriting `BaseNeuro` (directly or transitively).
3. For class form: main class resolvable (explicit `__main_neuro__` hint, CamelCase-matched name, or single-candidate fallback — see `01-core/01` §3).
4. For class form: `run` is an async method.
5. For class form: every name in `uses` exists in the registry (or in the pending load batch, for simultaneous registration).
6. `conf.json` `inputs` entries match the function/method signature (kwargs coverage).

Each failure produces a structured error envelope (`01-robustness-patterns.md` §7).

## 3 · Protected neuros

A small list of names that the dev agent can **propose** edits to but cannot **apply** without explicit human confirmation.

Default protected list:

- `planner`, `dev_planner`
- `smart_router`
- `reply`, `dev_reply`
- All built-in flows: `dag_flow`, `sequential_flow`, `parallel_flow`, `retry_flow`
- `memory`

Policy when a dev neuro targets a protected name:

- Pipeline runs all validations as usual.
- Instead of `rename` to final path, snapshot + write to `neuros/<name>/.proposed/` directory.
- Emit `dev.event {"type": "proposed", "neuro": ..., "diff": ..., "proposed_path": ...}`.
- A human-triggered `/dev apply <name>` (or IDE button) promotes `.proposed/` to live.
- `/dev reject <name>` discards.

Configurable: the protected list lives in `core/schemas/protected_neuros.json`; operators can extend. Deployments that prefer unconstrained AI writes can empty the list (not recommended).

## 4 · Forbidden patterns in AI-authored code

Static checks that run on AI-authored `code.py` (not on human-authored). Applied as an AST walk during the syntax stage.

| check                                                         | action                 |
|---------------------------------------------------------------|------------------------|
| `os.system(...)`, `subprocess.*` without allowlist            | reject, suggest alternative |
| `open(..., 'w')` outside the neuro's own dir                   | reject                 |
| `eval` / `exec` with non-constant arg                          | reject                 |
| `import *`                                                     | reject                 |
| Accessing `state["__*"]` keys not in the reserved list         | warn                   |
| Writing `state["__*"]` keys                                    | reject                 |
| Network calls without declared `permissions: ["network.out"]` in conf | reject         |
| Shell escapes (`` ` ``, `$(`, `&&`, `||`) in strings passed to `os.system`-family | reject |

Human-authored code bypasses these checks by default. The distinction is marked by a `author: "ai" | "human"` field on `dev.event`, set by the dev neuro that issued the write.

Deployments that want uniform checking can flip a flag (`safety.strict = true`) to apply the static checks to all writes.

## 5 · Dry-run sandbox (v2, scoped here for completeness)

v1 does not run AI-authored neuros with real inputs before promotion. v2 will:

- Create a fresh Python namespace, import the module, instantiate the class (if class-form).
- Call `setup` if present.
- Call `run` with a synthetic state object and sample inputs (from `conf.inputs[].example` if provided).
- Catch exceptions; require the call to return a dict.
- Tear down.

Budget: ≤1s. Skip for neuros declaring `permissions: ["side_effects"]` (they might launch processes, hit networks, etc., which are not safe to invoke without intent).

Decision: spec'd here, **not shipped v1**. Ship when a concrete need arises (e.g., a run of repeated post-promotion regressions traceable to code that imports fine but crashes on first real call).

## 6 · Diff-review step

For `dev_edit` / `dev_patch` on any neuro:

- The pre-change `conf.json` / `code.py` / `prompt.txt` snapshot is diffed against the proposed new state.
- Diff is posted to the `dev.event` stream alongside the write outcome.
- For protected neuros, the diff is what the human reviewer sees before promoting.

Diff format: unified (`diff -u`). Works with standard tools and IDE renderers.

## 7 · Quota / cooldown (v1, light)

Guardrails against runaway loops (an AI session churning out edits):

- Per-neuro write rate limit: **max 10 writes per neuro per hour**, soft.
- Per-session total writes: **max 100 per hour**, soft.
- Exceeding soft limits emits `dev.event {"type": "rate_warn"}` but does not block.
- Hard ceiling: 100 writes per neuro per day; block until next day.

Counters live in `agent_memory.db` under `scope: agent, key: dev.rate.<neuro_or_session>`.

## 8 · Audit trail

Every successful dev-agent action writes:

1. A snapshot directory entry (already covered in `01-robustness-patterns.md` §6).
2. A `dev.event` row in the memory API log.
3. Optional: a git commit if `safety.git_commits = true` in operator config (default off; keeps hot iteration lightweight).

The audit trail is queryable via the memory API: `memory.search scope=agent prefix=dev.event`.

## 9 · Escape hatch

Humans can always:

- Directly edit `neuros/<name>/code.py` with their own editor. Factory picks up on mtime change, same as AI writes. No validation pipeline for human writes by default (toggle via `safety.strict`).
- Delete a neuro folder. Factory's `_watch()` drops it from the registry on next tick.
- Restore from `.neuros_history/` manually.
- Stop the agent, edit on disk, restart.

No safety layer gates humans. The dev agent gates itself.

## 10 · Decisions locked

1. **Contract check is part of pipeline stage 5** — formalized list (§2).
2. **Protected neuros list** — propose-only path for core names; human confirmation required. Operator-configurable.
3. **Forbidden-pattern AST scan** for AI-authored code — rejection table (§4). Human code bypasses by default.
4. **Dry-run sandbox deferred to v2** — design noted for future.
5. **Diff in `dev.event`** on every edit/patch — standard unified format.
6. **Rate limits**: per-neuro 10/hour soft, 100/day hard; per-session 100/hour soft.
7. **Audit trail**: snapshots + memory events; optional git commits off by default.
8. **Humans bypass everything** — dev agent gates only itself.

## 11 · Deferred

- Proper sandbox execution (Docker / nsjail / wasm) for running AI-authored neuros with untrusted side effects.
- Fine-grained permissions beyond `network.out` / `side_effects`.
- Per-agent vs per-user rate limits.
- Formal ACLs (this dev-agent instance may not touch certain categories).
- Multi-agent "peer review" (dev-agent A writes, dev-agent B reviews before promotion).
- Semantic behavioral tests (beyond the syntactic/import dry-run sandbox).
