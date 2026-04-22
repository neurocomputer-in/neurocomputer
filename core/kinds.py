"""Kind taxonomy parser and validator.

A `kind` is a namespaced dotted string on conf.json:
    skill.leaf            → runs code.py
    skill.flow.sequential → ordered pipeline (equiv. alias: "sequential_flow")
    prompt.block          → reusable prompt fragment
    memory.recall         → retrieval strategy
    ...

See docs/superpowers/specs/2026-04-20-neuro-arch/01-core/08-kinds-taxonomy.md
"""
from dataclasses import dataclass
from typing import Optional


KNOWN_NAMESPACES = frozenset({
    "skill", "prompt", "memory", "context",
    "model", "instruction", "agent", "library",
})


LEGACY_ALIASES = {
    "sequential_flow": "skill.flow.sequential",
    "parallel_flow":   "skill.flow.parallel",
    "dag_flow":        "skill.flow.dag",
}


# Default subtype per namespace when kind is just "skill" or "prompt" etc.
DEFAULT_SUBTYPE = {
    "skill":       "leaf",
    "prompt":      "block",
    "memory":      "store",
    "context":     "slice",
    "model":       "llm",
    "instruction": "rule",
    "agent":       "",          # agent has no subtype by default
    "library":     "",
}


@dataclass
class Kind:
    namespace: str
    subtype: str = ""
    variant: str = ""

    @property
    def full(self) -> str:
        parts = [self.namespace]
        if self.subtype:
            parts.append(self.subtype)
        if self.variant:
            parts.append(self.variant)
        return ".".join(parts)

    def is_known(self) -> bool:
        return self.namespace in KNOWN_NAMESPACES

    def __str__(self) -> str:
        return self.full


def parse_kind(raw: Optional[str]) -> Kind:
    """Parse a kind string into a structured Kind.

    - `None` or empty → `skill.leaf`.
    - Legacy aliases (e.g. `sequential_flow`) mapped to canonical dotted form.
    - Namespace-only input (`skill`) fills default subtype.
    - Up to 3 dotted segments honored; extras ignored.
    """
    if not raw:
        return Kind(namespace="skill", subtype="leaf")

    s = raw.strip()
    if s in LEGACY_ALIASES:
        s = LEGACY_ALIASES[s]

    parts = s.split(".")
    ns = parts[0]
    sub = parts[1] if len(parts) > 1 else DEFAULT_SUBTYPE.get(ns, "")
    var = parts[2] if len(parts) > 2 else ""
    return Kind(namespace=ns, subtype=sub, variant=var)


def validate_kind(raw: Optional[str], *, strict: bool = False) -> Kind:
    """Parse + validate. In strict mode, unknown namespace raises."""
    k = parse_kind(raw)
    if strict and not k.is_known():
        raise ValueError(
            f"unknown kind namespace {k.namespace!r} "
            f"(known: {', '.join(sorted(KNOWN_NAMESPACES))})"
        )
    return k
