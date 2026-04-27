# S5 — Schedule / Orchestration Neuro

**Master plan:** [`2026-04-28-MASTER-neurolang-integration-plan.md`](./2026-04-28-MASTER-neurolang-integration-plan.md)
**Status:** DRAFT
**Depends on:** S1 (saved NeuroLang flows exist to be scheduled)
**Blocks:** none
**ETA:** 60–90 minutes

---

## Goal

Let a user say "run the arxiv summariser every weekday at 9 am" and have neurocomputer **persistently schedule** that NeuroLang flow, surviving server restarts, with a visible list of schedules in the UI and a `cancel` action.

---

## Background

Neurocomputer already has:

- A persistent SQLite DB at `agent_graph.db` (and `agent_memory.db`).
- A FastAPI server (`neurocomputer/server.py`) running asyncio.
- Watchdog services (`neurocomputer.service`, `neurocomputer-watchdog.service`).

What we need:

- An **APScheduler** instance attached to the FastAPI lifespan.
- A **`schedules.db`** (SQLite) storing each schedule's `id`, `target_path`, `cron_or_interval`, `created_at`, `last_run`, `last_status`, `next_run`, `enabled`.
- Two new neuros: **`schedule_run`** (creates a schedule) and **`schedule_cancel`** (cancels one).
- A small UI surface: a "Schedules" tab/list in the IDE side panel.

---

## What "scheduling" means here

A schedule binds an existing saved NeuroLang flow (a `.py` under `~/.neurolang/neuros/`) to a recurring trigger. Two trigger flavours:

| Type | Example value | Semantics |
|---|---|---|
| `interval` | `"every 30m"`, `"every 1d"` | Run at fixed periodicity |
| `cron` | `"0 9 * * 1-5"` | Standard 5-field cron expression |

We use APScheduler's `IntervalTrigger` and `CronTrigger`. No custom scheduling.

---

## Files to add / edit

### New

- `neurocomputer/core/scheduler.py` — `Scheduler` singleton: starts on app startup, owns the APScheduler `AsyncIOScheduler`, persists to `schedules.db`, exposes `add(target_path, trigger, kwargs)` / `cancel(schedule_id)` / `list()`.
- `neurocomputer/core/schedules_db.py` — thin SQLite wrapper (DDL + CRUD).
- `neurocomputer/neuros/schedule_run/{conf.json, code.py}` — async neuro that calls `scheduler.add(...)`.
- `neurocomputer/neuros/schedule_cancel/{conf.json, code.py}` — calls `scheduler.cancel(...)`.
- `neurocomputer/neuros/schedule_list/{conf.json, code.py}` — read-only.
- `neuro_web/components/neuroide/SchedulesList.tsx` — small list view (~80 LoC).

### Edit

- `requirements.txt` — add `apscheduler>=3.10`.
- `neurocomputer/server.py` — start the scheduler on FastAPI `startup` event, stop on `shutdown`. Add `GET /api/schedules`, `POST /api/schedules`, `DELETE /api/schedules/{id}` endpoints.
- `neurocomputer/profiles/neurolang_dev.json` — add `schedule_run`, `schedule_cancel`, `schedule_list` to its neuro list.

---

## DB schema

```sql
CREATE TABLE IF NOT EXISTS schedules (
  id           TEXT PRIMARY KEY,            -- ulid or uuid4 hex
  target_path  TEXT NOT NULL,                -- absolute path to the saved .py file
  trigger_kind TEXT NOT NULL,                -- 'interval' | 'cron'
  trigger_arg  TEXT NOT NULL,                -- raw expression as user typed it
  kwargs_json  TEXT NOT NULL DEFAULT '{}',   -- kwargs passed to flow.run()
  enabled      INTEGER NOT NULL DEFAULT 1,   -- 0 = paused, 1 = active
  created_at   TEXT NOT NULL,                -- ISO 8601
  last_run     TEXT,                          -- ISO 8601 or NULL
  last_status  TEXT,                          -- 'ok' | 'error: ...'
  next_run     TEXT                           -- ISO 8601, advisory only
);
```

---

## Scheduler API (Python)

```python
class Scheduler:
    def __init__(self, db_path: str = "schedules.db") -> None: ...
    async def start(self) -> None: ...
    async def stop(self) -> None: ...

    def add(self, target_path: str, trigger_kind: str, trigger_arg: str,
            kwargs: dict | None = None) -> str:
        """Returns schedule_id."""

    def cancel(self, schedule_id: str) -> bool: ...
    def list(self) -> list[dict]: ...
```

The `add` method:
1. Validates the trigger (parse cron / interval).
2. Inserts into `schedules.db`.
3. Calls `aps.add_job(self._run_target, trigger, args=[target_path, kwargs], id=schedule_id, replace_existing=True)`.

The `_run_target(target_path, kwargs)` worker:
1. `importlib.util.spec_from_file_location(...)` to load the `.py`.
2. Find the `flow` symbol (saved files always export `flow`).
3. `result = await flow.run_async(**kwargs)` (or `flow.run(...)` in a worker thread).
4. Update `last_run` + `last_status`.

---

## Trigger parsing

`trigger_arg` from the user message comes as natural language (`"every 30 minutes"`, `"every weekday at 9am"`). The `nl_planner` (S1) is responsible for normalising this into either:

- `trigger_kind="interval"`, `trigger_arg="30m"` (m / h / d suffixes), OR
- `trigger_kind="cron"`, `trigger_arg="0 9 * * 1-5"`.

A small `core/trigger_parse.py` helper:

```python
def parse_interval(s: str) -> dict:
    # "30m" → {"minutes": 30}; "1h" → {"hours": 1}; "2d" → {"days": 2}
    ...

def parse_cron(s: str) -> dict:
    # "0 9 * * 1-5" → {"minute": "0", "hour": "9", "day_of_week": "1-5", ...}
    ...
```

---

## Implementation Checklist

- [ ] **5.1** `pip install apscheduler>=3.10` and add to `requirements.txt`.
- [ ] **5.2** Create `core/schedules_db.py` (DDL + `insert`, `delete`, `update`, `list_all`).
- [ ] **5.3** Create `core/trigger_parse.py` (`parse_interval`, `parse_cron`, `parse_any` that dispatches).
- [ ] **5.4** Create `core/scheduler.py` (`Scheduler` class). On `start()`, load all enabled schedules from DB and re-register them with APScheduler.
- [ ] **5.5** In `server.py`, instantiate `Scheduler` as a singleton (e.g., `app.state.scheduler`), start in FastAPI `startup`, stop in `shutdown`.
- [ ] **5.6** Add HTTP endpoints `GET/POST /api/schedules` and `DELETE /api/schedules/{id}`.
- [ ] **5.7** Create `neuros/schedule_run/` (conf + code calling `scheduler.add`).
- [ ] **5.8** Create `neuros/schedule_cancel/` (calls `scheduler.cancel`).
- [ ] **5.9** Create `neuros/schedule_list/` (calls `scheduler.list`).
- [ ] **5.10** Update `profiles/neurolang_dev.json` to include `schedule_*` neuros.
- [ ] **5.11** Create `neuro_web/components/neuroide/SchedulesList.tsx`. Render in a tab next to the catalog.
- [ ] **5.12** Test: schedule a flow with `interval=every 1m`, wait 70 seconds, confirm `last_run` updates and a log line appears.
- [ ] **5.13** Test: restart the server (`systemctl restart neurocomputer`), confirm schedule survives and runs again on next tick.
- [ ] **5.14** Mark spec `Status: SHIPPED`.

---

## Acceptance criteria

1. **Persistence.** A schedule created at T survives a server restart at T+5 and runs on its next tick.
2. **Both trigger kinds work.** Interval (`every 30m`) and cron (`0 9 * * 1-5`) both fire on schedule.
3. **Cancellation works.** `DELETE /api/schedules/{id}` removes the row AND the APScheduler job; subsequent ticks don't fire.
4. **Visible in UI.** The `SchedulesList` shows id, target, trigger, last_run, last_status, next_run, with a Cancel button.
5. **Last status updates.** Successful run → `last_status="ok"`; exception → `last_status="error: <truncated>"`.

---

## Out of scope

- **Distributed scheduling** (multi-server, leader election) — single process this round.
- **Per-schedule retry policy** — APScheduler defaults; no custom backoff.
- **User notifications when a schedule fails** — log only this round.
- **Scheduling things other than NeuroLang flows** — would need to generalise `_run_target`. Defer.
- **Graphical cron editor** — text input only this round.

---

## Open questions

- **Should `schedule_run` accept the `prompt` directly (and run S1's compile-and-save first), or only accept an already-saved `target_path`?** Recommend: only `target_path` this round, to keep scheduling decoupled from compilation. Composition: user's NL planner emits two-step DAG `nl_compile → nl_save → schedule_run(target_path)` if scheduling was requested.
- **Where does scheduler logging go?** Same logger as the rest of `core/*`. No separate file.

---

## Notes for the executing agent

- APScheduler's `AsyncIOScheduler` is the right choice — works with the existing FastAPI asyncio loop, no thread-pool gymnastics.
- Use `aps.add_job(..., id=schedule_id, replace_existing=True)` so reloading on startup is idempotent.
- Each schedule's `kwargs_json` is stored as a string; deserialize lazily when running.
- If the saved `.py` raises on import, **mark the schedule disabled** and log the error rather than tearing down the scheduler.
- Test with `interval=every 30s` for fast iteration, then change to a real cadence.
