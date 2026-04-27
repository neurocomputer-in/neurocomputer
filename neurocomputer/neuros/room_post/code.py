from typing import Any, Dict
import importlib.util, os


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    room_id = kwargs.get("room_id") or ""
    message = kwargs.get("message") or ""

    if not room_id or not message:
        return {"error": "room_post: room_id and message required"}

    # Delegate to room_mediator
    mediator_path = os.path.join(os.path.dirname(__file__), "..", "room_mediator", "code.py")
    spec = importlib.util.spec_from_file_location("room_mediator", mediator_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return await mod.run(state, room_id=room_id, message=message)
