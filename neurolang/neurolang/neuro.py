"""The `Neuro` — the fundamental typed unit of NeuroLang.

A neuro is created by the @neuro decorator on a Python function. It carries:
- behavior (the function)
- identity (a stable id derived from the qualified name)
- declared effects, budget, kind, and optional NL-surface description (docstring)
- a stable Protocol-friendly interface so any caller can treat it uniformly

Composition with operators (`|`, `&`, `+`) lifts a Neuro into a Flow.
"""
from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Protocol, runtime_checkable

from .budget import Budget, ZERO_BUDGET
from .effect import Effect, normalize_effects


@runtime_checkable
class NeuroLike(Protocol):
    """Structural type any callable Neuro satisfies. Used for duck-typing
    composition without forcing inheritance."""
    name: str
    effects: frozenset[Effect]
    budget: Budget
    kind: str

    def __call__(self, *args: Any, **kwargs: Any) -> Any: ...


@dataclass
class Neuro:
    """A typed, composable unit. Wraps a Python callable with metadata."""
    fn: Callable[..., Any]
    name: str
    effects: frozenset[Effect] = field(default_factory=lambda: frozenset({Effect.PURE}))
    budget: Budget = ZERO_BUDGET
    kind: str = "skill"
    description: str = ""
    reads: tuple[str, ...] = ()
    writes: tuple[str, ...] = ()

    def __call__(self, *args, **kwargs) -> Any:
        return self.fn(*args, **kwargs)

    # --- Convenience: a bare neuro behaves like a one-step Flow --------------

    def plan(self, *args, **kwargs):
        """Treat this neuro as a one-step Flow and build a Plan."""
        from .flow import Flow
        from .plan import Plan
        return Plan.from_flow(Flow(_to_step(self)), args=args, kwargs=kwargs)

    def run(self, *args, memory=None, **kwargs) -> Any:
        return self.plan(*args, **kwargs).run(memory=memory)

    async def run_async(self, *args, memory=None, **kwargs) -> Any:
        return await self.plan(*args, **kwargs).run_async(memory=memory)

    # --- Composition operators -------------------------------------------------
    # `|` sequential, `&` parallel-AND (both run, tuple result), `+` parallel-OR
    # (race, first wins). All return a Flow.

    def __or__(self, other: "NeuroLike | Flow") -> "Flow":
        from .flow import Flow, Sequential
        return Flow(Sequential([_to_step(self), _to_step(other)]))

    def __and__(self, other: "NeuroLike | Flow") -> "Flow":
        from .flow import Flow, Parallel
        return Flow(Parallel([_to_step(self), _to_step(other)], strategy="and"))

    def __add__(self, other: "NeuroLike | Flow") -> "Flow":
        from .flow import Flow, Parallel
        return Flow(Parallel([_to_step(self), _to_step(other)], strategy="or"))

    def __repr__(self) -> str:
        eff = ",".join(sorted(e.value for e in self.effects))
        return f"Neuro<{self.name} eff=[{eff}] kind={self.kind}>"


def _to_step(x):
    """Lift a neuro/flow into a Flow step. Imported lazily to avoid cycles."""
    from .flow import Flow, Step
    if isinstance(x, Flow):
        return x.root
    if isinstance(x, Neuro):
        return Step(neuro=x)
    if callable(x):
        # Bare callable — wrap as an anonymous neuro
        n = Neuro(fn=x, name=getattr(x, "__name__", "anonymous"))
        return Step(neuro=n)
    raise TypeError(f"Cannot compose {type(x).__name__} into a Flow")


def neuro(
    fn: Optional[Callable] = None,
    *,
    effect: str | Effect | Iterable[str | Effect] | None = None,
    budget: Optional[Budget] = None,
    kind: str = "skill",
    name: Optional[str] = None,
    reads: Iterable[str] = (),
    writes: Iterable[str] = (),
    register: bool = True,
):
    """Decorator that turns a Python function into a Neuro.

    Examples:
        @neuro(effect="llm", budget=Budget(cost_usd=0.01))
        def summarize(text: str) -> str: ...

        @neuro
        def add_one(n: int) -> int: return n + 1
    """
    def decorate(f: Callable) -> Neuro:
        n = Neuro(
            fn=f,
            name=name or f"{f.__module__}.{f.__qualname__}",
            effects=normalize_effects(effect),
            budget=budget or ZERO_BUDGET,
            kind=kind,
            description=(inspect.getdoc(f) or "").strip(),
            reads=tuple(reads),
            writes=tuple(writes),
        )
        if register:
            from .registry import default_registry
            default_registry.add(n)
        return n

    if fn is not None and callable(fn):
        # Bare @neuro usage
        return decorate(fn)
    return decorate
