from typing import Any, Dict
from core.rooms import room_manager


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    room_id = kwargs.get("room_id") or ""
    if not room_id:
        return {"error": "room_close: room_id required"}
    closed = room_manager.close(room_id)
    return {"closed": closed}
