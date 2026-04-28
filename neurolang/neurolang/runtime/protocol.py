"""NeuroNet — the runtime contract.

A `NeuroNet` is the live network of running neuros. Implementations:
- `LocalNeuroNet` (in-process; ships in NeuroLang for standalone use)
- Neurocomputer (production runtime; ships in the neurocomputer repo)
- Any third-party runtime that satisfies this Protocol

NeuroLang defines the contract; environments implement it.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional, Protocol, runtime_checkable


@runtime_checkable
class NeuroNet(Protocol):
    """Structural contract for any NeuroLang runtime."""

    async def execute(self, plan, *, memory=None) -> Any:
        """Run a Plan to completion and return its result."""
        ...

    def submit(self, plan, *, memory=None):
        """Submit a Plan for asynchronous execution. Returns a handle (future-like)."""
        ...

    def topology(self) -> dict:
        """Return a snapshot of the live runtime topology."""
        ...

    def snapshot(self) -> dict:
        """Serialize the entire runtime state."""
        ...
