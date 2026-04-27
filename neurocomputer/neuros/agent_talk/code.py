from typing import Any, Dict
from core.talk import talk, TalkDepthExceeded


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    target = kwargs.get("target_agent_id") or ""
    message = kwargs.get("message") or ""
    timeout = float(kwargs.get("timeout") or 30.0)

    if not target:
        return {"error": "agent_talk: target_agent_id required"}
    if not message:
        return {"error": "agent_talk: message required"}

    caller = state.get("__caller_agent") or state.get("__agent_id")
    cid = f"agent_talk:{caller}:{target}" if caller else None

    try:
        reply = await talk(target, message, caller_agent_id=caller, cid=cid, timeout=timeout)
    except TalkDepthExceeded as exc:
        return {"error": "talk depth exceeded", "detail": str(exc)}
    except ValueError as exc:
        return {"error": str(exc)}
    except Exception as exc:
        return {"error": f"agent_talk failed: {exc}"}

    return {"reply": reply, "cid": cid or ""}
