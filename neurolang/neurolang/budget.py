"""Budget annotations — latency and cost bounds tracked through flows.

A budget on a neuro is a *promise*: when this neuro runs, it expects to
stay within these bounds. The runtime can enforce, warn, or just account.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class Budget:
    latency_ms: Optional[int] = None
    cost_usd: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None

    def __add__(self, other: "Budget") -> "Budget":
        """Add two budgets — used to roll up a flow's total budget."""
        def _add(a, b):
            if a is None and b is None:
                return None
            return (a or 0) + (b or 0)
        return Budget(
            latency_ms=_add(self.latency_ms, other.latency_ms),
            cost_usd=_add(self.cost_usd, other.cost_usd),
            tokens_in=_add(self.tokens_in, other.tokens_in),
            tokens_out=_add(self.tokens_out, other.tokens_out),
        )

    def is_unspecified(self) -> bool:
        return all(v is None for v in (self.latency_ms, self.cost_usd, self.tokens_in, self.tokens_out))

    def with_overrides(self, **kw) -> "Budget":
        return replace(self, **kw)


ZERO_BUDGET = Budget()
