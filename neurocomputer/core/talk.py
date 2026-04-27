"""agent.talk — in-process cross-agent invocation with depth guard."""
import asyncio
from contextvars import ContextVar
from typing import Optional

from core.defaults import MAIN_AGENT_ID

_talk_depth: ContextVar[int] = ContextVar("_talk_depth", default=0)
MAX_TALK_DEPTH = 4


class TalkDepthExceeded(RuntimeError):
    """Raised when agent.talk recursion exceeds MAX_TALK_DEPTH."""


async def talk(
    target_agent_id: str,
    message: str,
    *,
    caller_agent_id: Optional[str] = None,
    cid: Optional[str] = None,
    timeout: float = 30.0,
) -> str:
    depth = _talk_depth.get()
    if depth >= MAX_TALK_DEPTH:
        raise TalkDepthExceeded(f"talk depth {depth} >= {MAX_TALK_DEPTH}")

    if caller_agent_id and target_agent_id == caller_agent_id:
        return "[talk: refusing to call self]"

    from core.agent_manager import agent_manager

    target = agent_manager.get_agent_or_default(target_agent_id)
    if target is None:
        raise ValueError(f"unknown agent: {target_agent_id}")

    if cid is None:
        caller = caller_agent_id or (MAIN_AGENT_ID)
        cid = f"agent_talk:{caller}:{target_agent_id}"

    token = _talk_depth.set(depth + 1)
    try:
        reply = await asyncio.wait_for(
            target.brain.handle(cid, message, agent_id=target_agent_id),
            timeout=timeout,
        )
    finally:
        _talk_depth.reset(token)

    return reply if isinstance(reply, str) else str(reply)
