"""Neuro registry — the catalog the AI compiler reads from.

Every `@neuro`-decorated function registers here by default. Used for:
- discovery (`neurolang docs` lists every registered neuro)
- agentic search (the AI compiler queries by capability)
- composition lookup ("which neuros do `voice.transcribe`?")
"""
from __future__ import annotations

from typing import Iterator, Optional


class Registry:
    """In-process registry of neuros, indexed by name and kind."""

    def __init__(self):
        self._by_name: dict = {}

    def add(self, neuro) -> None:
        self._by_name[neuro.name] = neuro

    def get(self, name: str):
        return self._by_name.get(name)

    def __contains__(self, name: str) -> bool:
        return name in self._by_name

    def __iter__(self) -> Iterator:
        return iter(self._by_name.values())

    def __len__(self) -> int:
        return len(self._by_name)

    def by_kind(self, kind: str) -> list:
        return [n for n in self._by_name.values() if n.kind == kind]

    def by_effect(self, effect: str) -> list:
        return [n for n in self._by_name.values() if effect in {e.value for e in n.effects}]

    def search(self, query: str) -> list:
        """Naive substring search across name + description.
        Phase 2+ will replace with semantic embedding search."""
        q = query.lower()
        return [
            n for n in self._by_name.values()
            if q in n.name.lower() or q in n.description.lower()
        ]

    def catalog(self) -> list[dict]:
        """Structured catalog suitable for handing to an LLM as context."""
        return [
            {
                "name": n.name,
                "kind": n.kind,
                "effects": sorted(e.value for e in n.effects),
                "description": n.description,
                "reads": list(n.reads),
                "writes": list(n.writes),
            }
            for n in self._by_name.values()
        ]


default_registry = Registry()


def register(neuro) -> None:
    """Public helper to register a neuro into the default registry."""
    default_registry.add(neuro)
