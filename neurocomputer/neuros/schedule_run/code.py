from typing import Any, Dict
from core.scheduler import scheduler
from core.trigger_parse import parse_any


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    target_path = kwargs.get("target_path") or ""
    trigger = kwargs.get("trigger") or ""
    extra_kwargs = kwargs.get("kwargs") or {}

    if not target_path:
        return {"error": "schedule_run: target_path required"}
    if not trigger:
        return {"error": "schedule_run: trigger required (e.g. '30m' or '0 9 * * 1-5')"}

    try:
        trigger_kind, _ = parse_any(trigger)
    except ValueError as exc:
        return {"error": str(exc)}

    try:
        schedule_id = scheduler.add(target_path, trigger_kind, trigger, kwargs=extra_kwargs or None)
    except Exception as exc:
        return {"error": f"schedule_run: {exc}"}

    return {"schedule_id": schedule_id}
