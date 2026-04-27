from typing import Any, Dict
from core.rooms import room_manager, _pick_next_agent
from core.talk import talk


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    room_id = kwargs.get("room_id") or ""
    message = kwargs.get("message") or ""

    if not room_id:
        return {"error": "room_mediator: room_id required"}

    room = room_manager.get(room_id)
    if room is None:
        return {"error": f"room_mediator: room {room_id} not found"}
    if room.status == "closed":
        return {"transcript": room.transcript, "done": True}

    # Append the incoming user message
    if message:
        room = room_manager.append_message(room_id, "user", message)

    done = False
    turn_count = 0

    while not done:
        room = room_manager.get(room_id)
        if len(room.transcript) >= room.max_turns:
            room_manager.close(room_id)
            done = True
            break

        next_agent = _pick_next_agent(room, turn_count)
        if not next_agent:
            break

        latest = room.transcript[-1]["text"] if room.transcript else message
        if "[room: done]" in latest.lower():
            room_manager.close(room_id)
            done = True
            break

        try:
            reply = await talk(next_agent, latest, cid=f"room:{room_id}:{next_agent}")
        except Exception as exc:
            reply = f"[{next_agent} error: {exc}]"

        room = room_manager.append_message(room_id, next_agent, reply)

        if "[room: done]" in reply.lower():
            room_manager.close(room_id)
            done = True
            break

        # Only run one round-robin turn per call (caller can invoke again for next turn)
        break

    room = room_manager.get(room_id)
    return {"transcript": room.transcript, "done": done}
