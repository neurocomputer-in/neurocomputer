# Neurocomputer — Current Status

> **For any new session:** read this file first. Update at end of every working session.

---

## Last updated: 2026-04-28

## Current phase: NeuroLang integration — S1–S6 ALL SHIPPED ✓

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

2. **S5 + S6 — Schedule neuro + agent.talk (2026-04-28).**
   - `core/schedules_db.py`, `core/trigger_parse.py`, `core/scheduler.py` (APScheduler).
   - 3 neuros: `schedule_run`, `schedule_cancel`, `schedule_list`.
   - `core/talk.py` — `talk()` with depth guard (MAX=4), `TalkDepthExceeded`.
   - 2 neuros: `agent_talk`, `agent_list`.
   - `server.py` — `/api/schedules` + `/api/rooms` endpoints.

3. **S3 — Meeting Rooms (2026-04-28).**
   - `core/rooms_db.py`, `core/rooms.py` — Room model + RoomManager + round-robin `_pick_next_agent`.
   - 4 neuros: `room_create`, `room_post`, `room_close`, `room_mediator`.
   - `neuro_web/components/rooms/RoomPanel.tsx` — transcript view + create/close + send.

4. **Spec batch — NeuroLang integration + multi-agent (DRAFT, 2026-04-28).**
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

All 6 specs implemented. Ready for end-to-end testing.

## Next up

1. **End-to-end test** — start server, switch to nl_dev agent, send "fetch arxiv papers and email me a summary", verify .py lands in ~/.neurolang/neuros/ and reply contains summary.
2. **Meeting Rooms live test** — create room with neuro+nl_dev, post a message, verify alternating replies.
3. **S4 ProfileBadge** — UI badge showing active profile name (optional polish).

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
