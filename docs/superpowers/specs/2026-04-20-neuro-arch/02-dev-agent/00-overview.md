# 02-dev-agent · 00 · Overview

**Status**: drafted.

---

## 1 · Why this track exists

The dev agent (profiles `neuro_dev` / `code_dev`) is the primary mechanism by which the system modifies itself. Every time the system writes, edits, or patches a neuro, it goes through a dev-agent neuro (`neuro_crafter`, `dev_new`, `dev_edit`, `dev_patch`, etc.). If the dev agent is flaky, every self-modification is flaky. That blocks the ambition of this whole spec.

This track hardens the dev agent so AI-driven changes are:

- **Reversible** — bad writes are caught and rolled back before they corrupt the registry.
- **Inspectable** — every write emits a structured event the IDE and humans can audit.
- **Self-correcting** — when the LLM emits malformed output, the dev pipeline repairs rather than fails silently.

## 2 · Current state (as of 2026-04-20)

Profiles:
- `profiles/neuro_dev.json`
- `profiles/code_dev.json`

Dev neuros in `neuros/`:
- `neuro_crafter` — compose a whole neuro from a spec.
- `dev_new` — create a new neuro folder.
- `dev_edit` — edit an existing neuro.
- `dev_patch` — apply a patch.
- `dev_diff` — show diff.
- `dev_codegen` — generate code for a neuro.
- `dev_planner` — plan a multi-step dev task.
- `dev_save` — persist changes.
- `dev_reset` — discard changes.
- `dev_show` — display a neuro's current code.
- `dev_reply` — dev-mode reply wrapper.

Support:
- `NeuroFactory._watch()` polls `conf.json` mtimes every 1s and hot-reloads.
- `NeuroFactory._safe_exec` wraps `exec` of `code.py`.

## 3 · Observed pain points

From inspection of the code and recent `logs/prompts/dev_new_*` / `planner_prompt_*` outputs:

1. **Silent compile failures.** A broken `code.py` logs `[factory] skipping invalid JSON in ...` or raises during `exec` — both get swallowed in `_watch()`. The agent has no idea its write failed until a later call fails.
2. **No rollback.** If `dev_save` writes a `code.py` that doesn't import cleanly, the previous version is already gone. Only git history saves the day.
3. **LLM schema drift.** `neuro_crafter` / `dev_new` often produce `conf.json` missing fields, or with wrong types. Caught later, not earlier.
4. **Unstructured errors.** When a dev neuro fails, the user gets "⚠️ Internal error: ..." with no context the agent can self-correct on.
5. **No observability.** There's no persistent changelog of what the dev agent did. Harder to debug regressions.
6. **No safety gate on protected neuros.** The dev agent can overwrite `planner`, `smart_router`, `reply`, etc. — core neuros that, if broken, take down the whole agent. No confirm step.

## 4 · Goals for this track

1. Every dev-agent write goes through a **validation pipeline** that can: reject, repair, or promote.
2. Every dev-agent write is **atomic** — either the new version is fully in place and reloadable, or the old version is still there untouched.
3. Every dev-agent action emits a **structured event** (`dev.event`) that the IDE and operators can watch.
4. Every failure returns a **structured error** the LLM can act on: `{error_type, file, line, suggestion}`.
5. A minimal **safety net** around protected neuros — list of names that require extra confirmation or human review.
6. Retain **full hot-reload responsiveness** — no validation step adds more than ~200ms to a good-path write.

## 5 · Non-goals

- Replacing the LLMs used by dev neuros. Model choice is orthogonal.
- Building a visual dev editor in this track. That's the 3D IDE, separate project.
- Sandboxed execution of AI-authored neuros. Covered lightly in `02-self-mod-safety.md`, but not a full container/runtime isolation story.
- Tests of the new neuros' *behavior*. Syntax check + import check are in scope; semantic test is follow-up work.

## 6 · Subdocs in this track

| file                               | purpose                                                            | status  |
|------------------------------------|--------------------------------------------------------------------|---------|
| `01-robustness-patterns.md`        | schema validation, retry-with-repair, atomic save, rollback        | pending |
| `02-self-mod-safety.md`            | syntax gate, contract check, protected-neuro policy, diff review   | pending |

## 7 · Relation to the core spec

- Builds on `01-core/` — the dev agent is just another agent using the new neuro primitives. No change to core needed for this track.
- Uses the `memory` API from `01-core/03-state-and-memory.md` to log the `dev.event` changelog and keep rollback snapshots.
- Relies on the `describe()` contract from `01-core/04` / `06` for the IDE side of its changelog.
- Interacts with hot-reload semantics from `01-core/05-factory-and-executor.md`: validation must complete *before* the reload happens, so bad code never enters the registry.
