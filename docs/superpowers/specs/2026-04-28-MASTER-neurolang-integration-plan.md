# MASTER PLAN — NeuroLang Integration + Multi-Agent Architecture

**Status:** DRAFT — pending review
**Owner:** sabkiapp-dev
**Last updated:** 2026-04-28
**Target completion:** Working prototype within hours of approval

---

## What this is

The single index and dependency graph for a coordinated set of changes to **neurocomputer** that:

1. Add a **NeuroLang authoring profile** to the existing 3D IDE so users can write `@neuro`-decorated NeuroLang flows from voice/text and have them saved + scheduled + rendered as nodes in the 3D graph.
2. Formalise the **`Main agency` / `Main project` / `Main agent`** defaults concept so that profiles, agents, and agencies all have well-defined fall-throughs.
3. Build the **abstract multi-agent talk primitive** (`agent.talk(other, msg)`) so any agent can invoke any other agent uniformly — the substrate that makes Meeting Rooms (existing DRAFT) executable.
4. Refresh the **Meeting Rooms** spec from DRAFT → executable using the talk primitive.
5. Make the **3D IDE profile-aware** so when `neurolang_dev` is active, NL neuros are visually distinguished and the IDE talks to NeuroLang-aware backend endpoints.
6. Add a **schedule/cron neuro** so saved NeuroLang flows can run on timers or intervals.

Every change is small, has a checklist, and is independently reviewable.

---

## Why now

- **Phase 1.9 of NeuroLang** just shipped the `email` stdlib; the library is stable, 172 tests passing, and ready to be embedded.
- **Neurocomputer** already has the agency/agent/profile substrate, the 3D IDE, voice/LiveKit, and 68+ neuros — adding a new profile is a tested-pattern operation.
- **User goal:** an agent that helps the user *write* neuros — using either the existing neurocomputer framework OR the new NeuroLang library — both surfaced in the same IDE.

---

## Sub-specs (six files, alphabetised)

| ID | Title | File | Status |
|---|---|---|---|
| **S1** | NeuroLang dev profile + `nl_*` neuros | `2026-04-28-S1-neurolang-dev-profile.md` | DRAFT |
| **S2** | Main agency / project / agent defaults | `2026-04-28-S2-main-defaults.md` | DRAFT |
| **S3** | Multi-agent meeting rooms (refresh) | `2026-04-28-S3-multi-agent-meeting-rooms.md` | DRAFT |
| **S4** | 3D IDE profile mode | `2026-04-28-S4-3d-ide-profile-mode.md` | DRAFT |
| **S5** | Schedule / orchestration neuro | `2026-04-28-S5-schedule-orchestration.md` | DRAFT |
| **S6** | Abstract multi-agent talk neuro | `2026-04-28-S6-abstract-multiagent-talk-neuro.md` | DRAFT |

---

## Dependency DAG

```
                    ┌──────────────┐
                    │  S2 defaults │   (foundational — no deps)
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
    ┌───────────┐   ┌──────────┐   ┌───────────┐
    │ S6 talk   │   │ S1 NL    │   │ S5 sched  │  (independent)
    │ primitive │   │ profile  │   │           │
    └─────┬─────┘   └─────┬────┘   └───────────┘
          │               │
          ▼               ▼
    ┌──────────┐    ┌──────────┐
    │ S3 rooms │    │ S4 IDE   │
    └──────────┘    │ mode     │
                    └──────────┘
```

**Critical path:** S2 → S1 → S4 → demo.
**Parallel:** S5 can ship any time after S1.
**Optional this round:** S6 → S3 (multi-agent comms — bigger investment, lands when time permits).

---

## Implementation order (recommended)

| # | Step | ETA | Why this order |
|---|---|---|---|
| 1 | Write all six specs (this batch) | 1 hr | Specs are the contract; every later step refers to them |
| 2 | **S2 — Main defaults** | 30 min | Trivial change; defines fall-through that S1/S6 both use |
| 3 | **S1 — NL profile + neuros** | 60–90 min | Headline feature; everything visible flows from this |
| 4 | **S4 — IDE profile mode** | 30–45 min | Closes the user-visible loop (text → save → render) |
| 5 | First demo + STATUS update | 15 min | Validate the slice end-to-end before adding more |
| 6 | **S5 — Schedule neuro** | 60–90 min | Independent; adds the user's "set timer" ask |
| 7 | **S6 — Talk primitive** | 60 min | Substrate for S3; small but enables a lot |
| 8 | **S3 — Meeting Rooms refresh** | 90+ min | Largest piece; only if time remains |

---

## Working principles

- **One concept per file.** A "dumber agent" reading a single sub-spec must be able to ship that piece without reading the others. Cross-references are explicit; required reading is named.
- **Checklist-first.** Every spec ends with a `## Implementation Checklist` ordered top-to-bottom. Tick boxes as you ship.
- **Acceptance criteria are testable.** Each spec lists how to verify it works (a command, a UI state, a file existing).
- **Out-of-scope is explicit.** Each spec lists what it does NOT do, so the agent doesn't drift.
- **Edits to existing files name exact line ranges or function names** wherever practical.
- **Reuse beats refactor.** We add files where possible; we change existing files only when the change is tightly scoped.

---

## File-touch budget (estimated)

| Area | New files | Edited files |
|---|---|---|
| `neurocomputer/profiles/` | 1 (`neurolang_dev.json`) | 0 |
| `neurocomputer/neuros/` | ~8 (`nl_planner`, `nl_reply`, `nl_compile`, `nl_propose`, `nl_save`, `nl_run`, `nl_summary`, `schedule_run`) | 0 |
| `neurocomputer/core/` | ~3 (`schedules.py`, `talk.py`, optional `defaults.py`) | 2–3 (`agent.py`, `agency.py`, `agent_configs.py`) |
| `neurocomputer/server.py` | 0 | minor (mount endpoints) |
| `neuro_web/components/neuroide/` | 0 | 1 (`Graph3D.tsx` — color entry + pulse class) |
| `neuro_web/components/` | 1 (a tiny `ProfileBadge.tsx`) | 0 |
| `docs/superpowers/specs/` | 7 (master + 6) | 0 |
| `STATUS.md` | 1 | 0 |

**Net:** ~14 new files; 4–6 edits. Aggressively small.

---

## Open questions for the user

- *(none right now — all scoping resolved in pre-spec dialogue. Re-opens if any sub-spec surfaces a contradiction.)*

---

## Status board

(Updated end of every working session. See `/STATUS.md` for the live rollup.)

| Sub-spec | Status | Last action |
|---|---|---|
| MASTER | DRAFT | 2026-04-28 — initial draft |
| S1 | DRAFT | 2026-04-28 — initial draft |
| S2 | DRAFT | 2026-04-28 — initial draft |
| S3 | DRAFT | 2026-04-28 — initial draft |
| S4 | DRAFT | 2026-04-28 — initial draft |
| S5 | DRAFT | 2026-04-28 — initial draft |
| S6 | DRAFT | 2026-04-28 — initial draft |
