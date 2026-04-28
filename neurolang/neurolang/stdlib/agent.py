"""agent.delegate — recursive flow composition.

A factory that returns a fresh sub-agent neuro per call. The returned neuro,
when invoked, runs propose_plan → compile_source → flow.run() against its
bound `task` description. See docs/specs/2026-04-27-agent-delegate-design.md.
"""
from __future__ import annotations

import fnmatch
from contextvars import ContextVar
from typing import Any, Optional

from ..neuro import neuro, Neuro
from ..registry import Registry, default_registry
from ..runtime.context import current_memory


class DelegationBudgetExhausted(Exception):
    """Raised when agent.delegate is called with depth=0 (no recursion budget left)."""


class DelegationFailed(Exception):
    """Wraps a CompileError or planning failure with the originating task description."""

    def __init__(self, task: str, cause: BaseException):
        super().__init__(f"agent.delegate({task!r}) failed: {cause}")
        self.task = task
        self.cause = cause


_delegation_depth: ContextVar[Optional[int]] = ContextVar("_delegation_depth", default=None)


def _short(s: str, n: int = 40) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def _filtered_registry(patterns: Optional[list[str]]):
    """Return either the default registry (patterns=None) or a fresh
    Registry containing only neuros whose names match any glob pattern."""
    if patterns is None:
        return default_registry
    sub = Registry()
    for n in default_registry:
        if any(fnmatch.fnmatchcase(n.name, p) for p in patterns):
            sub.add(n)
    return sub


def delegate(
    task: str,
    *,
    catalog: Optional[list[str]] = None,
    depth: int = 1,
    model: Optional[str] = None,
) -> Neuro:
    """Build a sub-agent neuro that plans → compiles → runs at call time.

    The returned neuro, when called with an upstream value, runs an inner
    `propose_plan(task) → compile_source(task) → flow.run(value)` loop and
    returns the inner flow's result. `task` is bound; only `value` flows
    in at runtime.
    """
    if depth < 0:
        raise ValueError(f"delegate depth must be >= 0, got {depth!r}")

    @neuro(
        effect="llm",
        kind="skill.agent",
        name=f"agent.delegate<{_short(task)}>",
        register=False,
    )
    async def _agent(input_value: Any) -> Any:
        # async because the outer flow already owns an event loop when this
        # neuro is invoked — we must `await` the inner flow rather than
        # asyncio.run() it (which would deadlock).
        residual = _delegation_depth.get()
        effective = depth if residual is None else residual
        if effective <= 0:
            raise DelegationBudgetExhausted(
                f"delegate({task!r}) called with no remaining depth budget"
            )

        from .. import compile_source, propose_plan

        sub_registry = _filtered_registry(catalog)

        try:
            plan = propose_plan(task, model=model, registry=sub_registry)
            if plan.missing:
                intents = ", ".join(m.intent for m in plan.missing)
                return f"[delegate: cannot satisfy task — missing: {intents}]"
            flow = compile_source(task, model=model, registry=sub_registry)
        except DelegationBudgetExhausted:
            raise
        except Exception as e:
            raise DelegationFailed(task, e) from e

        # Inherit parent's active memory: the inner Plan.run_async would
        # otherwise default memory=None and clobber the parent's ContextVar.
        parent_memory = current_memory()
        token = _delegation_depth.set(effective - 1)
        try:
            return await flow.run_async(input_value, memory=parent_memory)
        finally:
            _delegation_depth.reset(token)

    return _agent
