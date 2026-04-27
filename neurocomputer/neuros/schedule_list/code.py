from typing import Any, Dict
from core.scheduler import scheduler


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    return {"schedules": scheduler.list()}
