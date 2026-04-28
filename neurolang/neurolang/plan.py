"""Plan — a first-class, immutable, inspectable execution unit.

A Plan freezes a Flow + initial args into a runnable, hashable object.
Run it, replay it, hash it, serialize it.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

from .budget import Budget
from .flow import Flow, _execute_step


@dataclass(frozen=True)
class Plan:
    """An immutable plan: flow + initial inputs, ready to run."""
    flow: Flow
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)

    @classmethod
    def from_flow(cls, flow: Flow, args=(), kwargs=None) -> "Plan":
        return cls(flow=flow, args=tuple(args), kwargs=dict(kwargs or {}))

    # --- Introspection --------------------------------------------------------

    @property
    def steps(self) -> list:
        """Leaf neuros in left-to-right order (a flat view of the flow)."""
        return self.flow.neuros()

    def cost_estimate(self) -> Budget:
        return self.flow.cost_estimate()

    def effect_signature(self) -> set[str]:
        return self.flow.effect_signature()

    def hash(self) -> str:
        """Stable content hash. Used as cache key / identity."""
        payload = {
            "neuros": [
                {
                    "name": n.name,
                    "kind": n.kind,
                    "effects": sorted(e.value for e in n.effects),
                }
                for n in self.steps
            ],
            "args_repr": [repr(a) for a in self.args],
            "kwargs_repr": {k: repr(v) for k, v in sorted(self.kwargs.items())},
        }
        blob = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]

    def serialize(self) -> dict:
        """JSON-able representation. Replay-able via deserialize."""
        return {
            "hash": self.hash(),
            "neuros": [n.name for n in self.steps],
            "args_repr": [repr(a) for a in self.args],
            "kwargs_repr": {k: repr(v) for k, v in self.kwargs.items()},
            "effects": sorted(self.effect_signature()),
            "budget": {
                "latency_ms": self.cost_estimate().latency_ms,
                "cost_usd": self.cost_estimate().cost_usd,
            },
        }

    # --- Execution ------------------------------------------------------------

    async def run_async(self, memory=None) -> Any:
        # Memory is optional; propagated via ContextVar so neuros that want
        # access can call `current_memory()` without taking it as an arg.
        from .runtime.context import set_active_memory, reset_active_memory
        token = set_active_memory(memory)
        try:
            return await _execute_step(self.flow.root, self.args, self.kwargs)
        finally:
            reset_active_memory(token)

    def run(self, memory=None) -> Any:
        """Synchronous entry point. Spins up an event loop if needed."""
        try:
            loop = asyncio.get_running_loop()
            # Already in async context — caller should use run_async
            raise RuntimeError(
                "Plan.run() called from inside a running event loop; "
                "use `await plan.run_async(...)` instead."
            )
        except RuntimeError as e:
            if "no running event loop" not in str(e):
                # Re-raise non-loop errors
                if "called from inside" in str(e):
                    raise
        return asyncio.run(self.run_async(memory=memory))

    def replay(self, memory=None) -> Any:
        """Re-execute deterministically. Same plan + same memory ⇒ same result
        for pure flows; LLM/tool flows produce fresh results."""
        return self.run(memory=memory)

    def __repr__(self) -> str:
        return f"Plan<{self.hash()} {self.flow!r}>"
