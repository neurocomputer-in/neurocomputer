from typing import Any, Dict, List
from core.rooms import room_manager


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    name = kwargs.get("name") or "Room"
    agents: List[str] = kwargs.get("agents") or []
    turn_policy = kwargs.get("turn_policy") or "round_robin"
    max_turns = int(kwargs.get("max_turns") or 20)
    voice_room_id = kwargs.get("voice_room_id") or None

    if not agents:
        return {"error": "room_create: at least one agent required"}

    room = room_manager.create(
        name=name,
        agents=agents,
        voice_room_id=voice_room_id,
        turn_policy=turn_policy,
        max_turns=max_turns,
    )
    return {"room_id": room.room_id, "room": room.to_dict()}
