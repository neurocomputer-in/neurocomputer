"""Flow — composition of neuros.

A Flow is a tree of Steps. The two compositions:
- Sequential (`|`) : run children in order; output of one feeds the next as
  its single positional argument
- Parallel  (`&` AND, `+` OR) : run children concurrently; AND returns a
  tuple of all results; OR races and returns the first

Flows compose with each other and with neuros transparently.
"""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Iterable

from .budget import Budget, ZERO_BUDGET
from .effect import Effect


@dataclass
class Step:
    """Base step. Leaf wraps a neuro; composites have children."""
    neuro: Any  # Neuro for leaves; None for composites
    children: tuple = ()

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def effects(self) -> frozenset[Effect]:
        if self.is_leaf:
            return self.neuro.effects
        return frozenset().union(*(c.effects() for c in self.children))

    def budget(self) -> Budget:
        if self.is_leaf:
            return self.neuro.budget
        total = ZERO_BUDGET
        for c in self.children:
            total = total + c.budget()
        return total


class Sequential(Step):
    """A | B | C — sequential composition."""
    def __init__(self, children: Iterable[Step]):
        super().__init__(neuro=None, children=tuple(children))


class Parallel(Step):
    """A & B (AND) or A + B (OR)."""
    def __init__(self, children: Iterable[Step], strategy: str = "and"):
        super().__init__(neuro=None, children=tuple(children))
        self.strategy = strategy


@dataclass
class Flow:
    """A composed pipeline of steps. Composes further with operators."""
    root: Step

    # --- Composition ----------------------------------------------------------

    def __or__(self, other) -> "Flow":
        from .neuro import _to_step
        return Flow(Sequential([self.root, _to_step(other)]))

    def __and__(self, other) -> "Flow":
        from .neuro import _to_step
        return Flow(Parallel([self.root, _to_step(other)], strategy="and"))

    def __add__(self, other) -> "Flow":
        from .neuro import _to_step
        return Flow(Parallel([self.root, _to_step(other)], strategy="or"))

    # --- Introspection --------------------------------------------------------

    def effects(self) -> frozenset[Effect]:
        return self.root.effects()

    def budget(self) -> Budget:
        return self.root.budget()

    def cost_estimate(self) -> Budget:
        return self.budget()

    def effect_signature(self) -> set[str]:
        return {e.value for e in self.effects()}

    def neuros(self) -> list:
        """All leaf neuros in left-to-right traversal."""
        out = []
        def walk(s: Step):
            if s.is_leaf:
                out.append(s.neuro)
            else:
                for c in s.children:
                    walk(c)
        walk(self.root)
        return out

    # --- Plan + run -----------------------------------------------------------

    def plan(self, *args, **kwargs):
        from .plan import Plan
        return Plan.from_flow(self, args=args, kwargs=kwargs)

    def run(self, *args, memory=None, **kwargs) -> Any:
        return self.plan(*args, **kwargs).run(memory=memory)

    async def run_async(self, *args, memory=None, **kwargs) -> Any:
        return await self.plan(*args, **kwargs).run_async(memory=memory)

    # --- Rendering ------------------------------------------------------------

    def render(self, format: str = "mermaid") -> str:
        if format == "mermaid":
            from .render.mermaid import to_mermaid
            return to_mermaid(self)
        raise ValueError(f"Unknown render format: {format!r}")

    def to_mermaid(self) -> str:
        return self.render(format="mermaid")

    def __repr__(self) -> str:
        names = [n.name.split(".")[-1] for n in self.neuros()]
        return f"Flow<{' → '.join(names)}>"


# --- Execution ----------------------------------------------------------------

async def _call_leaf(step: Step, args: tuple, kwargs: dict) -> Any:
    """Call a single neuro, awaiting if async."""
    n = step.neuro
    if inspect.iscoroutinefunction(n.fn):
        return await n.fn(*args, **kwargs)
    return n.fn(*args, **kwargs)


async def _execute_step(step: Step, args: tuple, kwargs: dict) -> Any:
    """Run a step (leaf or composite) with the given initial args/kwargs.

    For Sequential: first child gets args/kwargs; subsequent children get
    the previous output threaded as a single positional argument.
    For Parallel: every child gets the same args/kwargs.
    """
    if step.is_leaf:
        return await _call_leaf(step, args, kwargs)

    if isinstance(step, Sequential):
        if not step.children:
            return None
        cur = await _execute_step(step.children[0], args, kwargs)
        for c in step.children[1:]:
            cur = await _execute_step(c, (cur,), {})
        return cur

    if isinstance(step, Parallel):
        if step.strategy == "and":
            results = await asyncio.gather(
                *(_execute_step(c, args, kwargs) for c in step.children)
            )
            return tuple(results)
        if step.strategy == "or":
            tasks = [asyncio.create_task(_execute_step(c, args, kwargs)) for c in step.children]
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for p in pending:
                p.cancel()
            return next(iter(done)).result()
        raise ValueError(f"Unknown parallel strategy: {step.strategy!r}")

    raise TypeError(f"Unknown step type: {type(step).__name__}")
