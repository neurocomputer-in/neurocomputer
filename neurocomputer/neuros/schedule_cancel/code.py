from typing import Any, Dict
from core.scheduler import scheduler


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    schedule_id = kwargs.get("schedule_id") or ""
    if not schedule_id:
        return {"error": "schedule_cancel: schedule_id required"}
    cancelled = scheduler.cancel(schedule_id)
    return {"cancelled": cancelled}
