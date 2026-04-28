"""Memory — scoped storage hierarchy.

Phase 1 ships only the discrete (key-value) layer behind a Protocol so
later phases can add: differentiable / compressed / hyperdimensional /
episodic / semantic / procedural — all without breaking the user API.
"""
from __future__ import annotations

from typing import Any, Iterator, Optional, Protocol, runtime_checkable


@runtime_checkable
class MemoryLike(Protocol):
    """Structural type any Memory implementation satisfies."""
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def delete(self, key: str) -> None: ...
    def keys(self) -> Iterator[str]: ...
    def has(self, key: str) -> bool: ...


class LocalMemory:
    """Discrete in-process key-value memory. The Phase 1 default."""

    def __init__(self, initial: Optional[dict] = None):
        self._store: dict[str, Any] = dict(initial or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def keys(self) -> Iterator[str]:
        return iter(self._store.keys())

    def has(self, key: str) -> bool:
        return key in self._store

    def __repr__(self) -> str:
        return f"LocalMemory<{len(self._store)} keys>"

    def snapshot(self) -> dict:
        """Return a deep-ish copy for serialization / replay."""
        return dict(self._store)


class Memory:
    """Factory + entry-point for memory backends. `Memory.discrete()` is the
    Phase 1 default. Future: `.differentiable()`, `.hyperdimensional()`, etc."""

    @staticmethod
    def discrete(initial: Optional[dict] = None) -> LocalMemory:
        return LocalMemory(initial=initial)

    # Reserved for Phase 2+:
    # @staticmethod
    # def differentiable(...) -> ...
    # @staticmethod
    # def hyperdimensional(...) -> ...
