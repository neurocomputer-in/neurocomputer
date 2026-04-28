"""Memory stdlib neuros — wrappers over the active memory.

These read/write the memory currently bound to the running plan.
Standalone use also works: pass `memory=Memory.discrete()` to plan.run().
"""
from __future__ import annotations

from typing import Any, Optional

from ..neuro import neuro
from ..runtime.context import current_memory


@neuro(
    effect="memory",
    kind="memory.store",
    name="neurolang.stdlib.memory.store",
    writes=("any",),
)
def store(value: Any, *, key: str) -> Any:
    """Store `value` under `key` in active memory; return the value unchanged."""
    mem = current_memory()
    if mem is None:
        raise RuntimeError(
            "memory.store called without an active memory. "
            "Pass memory=Memory.discrete() to plan.run()."
        )
    mem.set(key, value)
    return value


@neuro(
    effect="memory",
    kind="memory.recall",
    name="neurolang.stdlib.memory.recall",
    reads=("any",),
)
def recall(*, key: str, default: Any = None) -> Any:
    """Recall the value stored under `key`."""
    mem = current_memory()
    if mem is None:
        raise RuntimeError(
            "memory.recall called without an active memory. "
            "Pass memory=Memory.discrete() to plan.run()."
        )
    return mem.get(key, default)
