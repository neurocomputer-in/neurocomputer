"""Execution context — propagates per-run state (e.g., active memory)
through nested coroutines without polluting every neuro signature."""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from ..memory import MemoryLike


_active_memory: ContextVar[Optional[MemoryLike]] = ContextVar(
    "neurolang_active_memory", default=None
)


def current_memory() -> Optional[MemoryLike]:
    """Return the currently-active memory, or None if not in a run."""
    return _active_memory.get()


def set_active_memory(memory: Optional[MemoryLike]):
    """Set the active memory and return a token for resetting."""
    return _active_memory.set(memory)


def reset_active_memory(token) -> None:
    _active_memory.reset(token)
