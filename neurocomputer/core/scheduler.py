"""Persistent APScheduler wrapper for NeuroLang flow scheduling."""
import importlib.util
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from core import schedules_db as db
from core.trigger_parse import parse_interval, parse_cron

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self) -> None:
        self._aps = AsyncIOScheduler()
        self._started = False

    async def start(self) -> None:
        if self._started:
            return
        db.init_db()
        self._aps.start()
        self._started = True
        # Reload persisted schedules
        for row in db.list_all():
            if row.get("enabled"):
                try:
                    self._register(row)
                except Exception as exc:
                    logger.warning("Failed to reload schedule %s: %s", row["id"], exc)

    async def stop(self) -> None:
        if self._started:
            self._aps.shutdown(wait=False)
            self._started = False

    def add(
        self,
        target_path: str,
        trigger_kind: str,
        trigger_arg: str,
        kwargs: Optional[dict] = None,
    ) -> str:
        schedule_id = uuid.uuid4().hex
        row = {
            "id": schedule_id,
            "target_path": target_path,
            "trigger_kind": trigger_kind,
            "trigger_arg": trigger_arg,
            "kwargs_json": json.dumps(kwargs or {}),
            "enabled": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.insert(row)
        self._register(row)
        return schedule_id

    def cancel(self, schedule_id: str) -> bool:
        row = db.get(schedule_id)
        if not row:
            return False
        db.delete(schedule_id)
        try:
            self._aps.remove_job(schedule_id)
        except Exception:
            pass
        return True

    def list(self) -> list[dict]:
        return db.list_all()

    def _register(self, row: dict) -> None:
        trigger = self._build_trigger(row["trigger_kind"], row["trigger_arg"])
        self._aps.add_job(
            self._run_target,
            trigger,
            args=[row["id"], row["target_path"], json.loads(row.get("kwargs_json") or "{}")],
            id=row["id"],
            replace_existing=True,
        )

    def _build_trigger(self, kind: str, arg: str):
        if kind == "interval":
            kw = parse_interval(arg)
            return IntervalTrigger(**kw)
        elif kind == "cron":
            kw = parse_cron(arg)
            return CronTrigger(**kw)
        raise ValueError(f"Unknown trigger_kind: {kind!r}")

    async def _run_target(self, schedule_id: str, target_path: str, kwargs: dict) -> None:
        import asyncio, inspect
        start = datetime.now(timezone.utc).isoformat()
        status = "ok"
        try:
            spec = importlib.util.spec_from_file_location("_nl_sched", target_path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            flow = getattr(mod, "flow", None)
            if flow is None:
                raise AttributeError(f"No 'flow' in {target_path}")
            run_fn = getattr(flow, "run_async", None) or getattr(flow, "run", None)
            if inspect.iscoroutinefunction(run_fn):
                await run_fn(**kwargs)
            else:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, lambda: run_fn(**kwargs))
        except Exception as exc:
            status = f"error: {str(exc)[:200]}"
            logger.error("Schedule %s failed: %s", schedule_id, exc)
            db.update(schedule_id, {"enabled": 0})
        finally:
            db.update(schedule_id, {"last_run": start, "last_status": status})


scheduler = Scheduler()
