# Neurocomputer — Current Status

> **For any new session:** read this file first. Update at end of every working session.

---

## Last updated: 2026-04-28

## Current phase: NeuroLang integration — S2 + S1 + S4 (partial) SHIPPED

## Just shipped (most recent first)

1. **S2 + S1 + S4(partial) — Main defaults + NL profile + IDE color (2026-04-28).**
   - `core/defaults.py` — MAIN_AGENCY_ID/AGENT_ID/PROJECT_ID constants.
   - `core/project.py` + `core/project_configs.py` — Project model + default project.
   - `core/agency.py` — `default_project` field on AgencyConfig.
   - `core/agent_manager.py` — removed hardcoded `"neuro"`, added `get_agent_or_default()`.
   - `core/agent_configs.py` — `nl_dev` agent entry.
   - `core/agency_configs.py` — `nl_dev` in default agency, `default_project="default"`.
   - `profiles/neurolang_dev.json` — new profile for `nl_dev`.
   - 7 neuros: `nl_compile`, `nl_propose`, `nl_summary`, `nl_save`, `nl_run`, `nl_planner`, `nl_reply`.
   - `Graph3D.tsx` — `nl: '#22d3ee'` added to NS_COLOR palette.
   - `server.py` — `/api/profile/list`, `/api/profile/active`, `/api/profile/switch` endpoints.

2. **Spec batch — NeuroLang integration + multi-agent (DRAFT, 2026-04-28).**
   - Master plan: `docs/superpowers/specs/2026-04-28-MASTER-neurolang-integration-plan.md`
   - Six sub-specs under `docs/superpowers/specs/2026-04-28-S{1..6}-*.md` covering:
     - **S1** — `neurolang_dev` profile + 8 `nl_*` neuros wrapping NeuroLang's `compile_source`/`propose_plan`/`decompile_summary`.
     - **S2** — `Main agency / Main project / Main agent` defaults contract; new `core/defaults.py`, `core/project.py`.
     - **S3** — Meeting Rooms refresh (executable rewrite of existing DRAFT).
     - **S4** — 3D IDE profile mode (visual highlight when `neurolang_dev` is active).
     - **S5** — Schedule / cron neuro persisting to `schedules.db` via APScheduler.
     - **S6** — Abstract `agent.talk(target, msg)` primitive — substrate for S3.
   - All six are checklist-first so a "dumber agent" can execute step-by-step.
   - Dependency DAG documented; recommended order S2 → S1 → S4 → demo → S5 → S6 → S3.

## Working on now

S5 (schedule neuro) → S6 (agent.talk) → S3 (meeting rooms)

## Next up

### Critical path (ship next)

1. **S5 — Schedule neuro** (60–90 min) — APScheduler + schedules.db + 3 neuros.
2. **S6 — agent.talk primitive** (60 min) — core/talk.py + agent_talk/agent_list neuros.
3. **S3 — Meeting Rooms refresh** (90+ min) — rooms + mediator + RoomPanel.tsx.

### Then (independent, any order)

6. **S5 — Schedule** (60–90 min) — adds the user's "set timer" capability.
7. **S6 — Talk primitive** (60 min) — substrate for multi-agent comms.
8. **S3 — Meeting Rooms refresh** (90+ min) — uses S6; largest piece, ship last.

### Later (deferred)

- Multi-project UI (project picker in IDE) — covered in S2 "out of scope".
- Cross-agency rooms — covered in S3 "out of scope".
- Streaming agent-to-agent replies — covered in S6 "out of scope".
- Voice in/out for room participants (full STT/TTS loop) — partial in S3, full later.

## Open questions for the user

- **Approve the spec batch** before implementation begins. Six files in `docs/superpowers/specs/2026-04-28-*.md`. Master at `2026-04-28-MASTER-neurolang-integration-plan.md`.

## Environmental notes

- **NeuroLang library at `/home/ubuntu/neurolang/`** — Phase 1.9 shipped (email stdlib + `agent.delegate` + 17 stdlib neuros + 172 tests passing). Install in neurocomputer's env via `pip install -e /home/ubuntu/neurolang` before S1 ships.
- **Neurocomputer 3D IDE** lives at `neuro_web/` (Next.js + Chakra + `@react-three/fiber`). Backend on `localhost:7001`. LiveKit voice infra already running.
- **Existing DRAFT specs** referenced by the new batch: `docs/MULTI_AGENCY_ARCHITECTURE.md` (4-layer architecture) and `docs/AGENT_MEETING_ROOMS.md` (refreshed by S3).
- **Existing profiles:** `general.json`, `code_dev.json`, `neuro_dev.json`. New: `neurolang_dev.json`.
- **Existing agents:** `neuro`, `upwork`, `openclaw`, `opencode`. New: `nl_dev`.

## Quick reference

```
Repo:        /home/ubuntu/neurocomputer/
Webapp:      /home/ubuntu/neurocomputer/neuro_web/   (Next.js + R3F)
Python core: /home/ubuntu/neurocomputer/neurocomputer/
Backend:     localhost:7001 (FastAPI)
NeuroLang:   /home/ubuntu/neurolang/   (Phase 1.9, 172 tests passing)
Specs:       docs/superpowers/specs/2026-04-28-*.md  (master + S1..S6)
This file:   /home/ubuntu/neurocomputer/STATUS.md
```

## Hierarchy (canonical, after S2 ships)

```
Agency  ──▶ Project  ──▶ Agent  ──▶ Neuro
   │            │            │          │
default     default       neuro    smart_router, planner, reply, ...
                            │
                          nl_dev   smart_router, nl_planner, nl_reply, nl_*
```

Defaults: `MAIN_AGENCY_ID="default"`, `MAIN_PROJECT_ID="default"`, `MAIN_AGENT_ID="neuro"`.
