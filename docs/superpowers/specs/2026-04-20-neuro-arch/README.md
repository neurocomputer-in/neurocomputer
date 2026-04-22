# Neuro Architecture — Design Spec (2026-04-20)

**Status**: all subdocs drafted (2026-04-20). Ready for user review. After review, invoke `writing-plans` skill for `01-core/` implementation plan.

## Goal

Lock a unified, OOP-capable, fractal architecture for neuros so that:

- any workflow (universal) can be built by composing neuros
- flows are themselves neuros (category closed under composition)
- humans and AI agents can author, edit, and reload neuros live
- a future 3D IDE can render, zoom, collapse, and voice-edit the graph
- the foundation leaves room for a tier-5 extensible neuro-lang (d) later

## Scope

Three parallel tracks, each in its own subfolder. Items fill in order (top → bottom), but tracks can progress independently.

### 01-core/ — primary design (what this spec commits to)

| # | file                            | topic                                                   | status  |
|---|----------------------------------|---------------------------------------------------------|---------|
| 00| `00-overview.md`                 | primitive + category closure + layering                 | drafted |
| 01| `01-primitive-class-vs-fn.md`    | BaseNeuro contract, fn form, class form, hybrid factory | drafted |
| 02| `02-flow-as-neuro.md`            | FlowNeuro, DagFlow, fractal composition, Y-combinator   | drafted |
| 03| `03-state-and-memory.md`         | session / agent / shared scopes, memory API             | drafted |
| 04| `04-registry-and-lib.md`         | global lib, agent profile filtering, naming, versions   | drafted |
| 05| `05-factory-and-executor.md`     | factory reload, executor subsumed into FlowNeuro.run    | drafted |
| 06| `06-typed-io-and-ide-seams.md`   | port types, visual metadata, semantic-zoom modes        | drafted |
| 07| `07-migration.md`                | keep all current neuros, wrap JSON flows via DagFlow    | drafted |
| 08| `08-kinds-taxonomy.md`           | namespaced kinds: skill/prompt/memory/context/model/... | drafted |
| 09| `09-kind-formats.md`             | formal contracts per kind + `code.*` namespace          | drafted |
| 10| `10-kind-backfill.md`            | assign kind to every existing neuro (metadata-only)     | drafted |

### 02-dev-agent/ — make dev profile robust + reliable

| # | file                            | topic                                                   | status  |
|---|----------------------------------|---------------------------------------------------------|---------|
| 00| `00-overview.md`                 | dev profile goals, pain points in current `neuro_dev`   | drafted |
| 01| `01-robustness-patterns.md`      | retries, schema validation, rollback, structured errors | drafted |
| 02| `02-self-mod-safety.md`          | guard rails for AI-authored neuros (syntax, tests, diff)| drafted |

### 03-react-orchestrator/ — RESEARCH (not committed design)

Open research docs on a ReAct-style orchestrator neuro that handles long, dynamic-environment tasks. Outputs questions and options, not a locked design.

| # | file                            | topic                                                   | status  |
|---|----------------------------------|---------------------------------------------------------|---------|
| 00| `00-research-brief.md`           | problem statement, success criteria, open questions     | drafted |
| 01| `01-prior-art.md`                | ReAct, Reflexion, ToT, AutoGPT, OpenAgents — contrast   | drafted |
| 02| `02-env-state-tracking.md`       | build on `core/environment_state.py`, what to log       | drafted |
| 03| `03-dynamic-replan.md`           | replan triggers, budget, rollback, loop termination     | drafted |

### 99-future/ — deferred

| # | file                            | topic                                                   | status  |
|---|----------------------------------|---------------------------------------------------------|---------|
| 01| `01-dsl-and-macros.md`           | extensible neuro-lang (d), tier-5 homoiconic substrate  | drafted |

## Review protocol

- Each subdoc is drafted → user reviews → committed on approval.
- `README.md` status table updated as items move `pending → drafted → approved`.
- Final step: `writing-plans` skill after all `01-core/` subdocs approved.

## Non-goals

- IDE implementation (separate project; this spec only reserves seams).
- Real DSL/parser now (`99-future/`).
- 3rd-party delegate agents (opencode, openclaw) — unchanged, treated as leaf neuros.
