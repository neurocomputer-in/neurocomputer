"""Recovery primitives — fallback / retry / escalate as language constructs.

Phase 1 ships these as flow-wrappers. Phase 2 will lift them into the
type system so the compiler can reason about recovery topology.
"""
from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .neuro import Neuro, neuro as neuro_decorator
from .effect import Effect


def with_retry(target, *, attempts: int = 3, backoff_s: float = 0.5):
    """Wrap a neuro/flow so failures retry up to `attempts` times.
    Uses exponential-ish backoff (backoff_s, 2*backoff_s, ...)."""
    from .flow import Flow

    async def _retry_async(*args, **kwargs):
        last_exc = None
        for i in range(attempts):
            try:
                if isinstance(target, Flow):
                    return await target.run_async(*args, **kwargs)
                if isinstance(target, Neuro):
                    if inspect.iscoroutinefunction(target.fn):
                        return await target.fn(*args, **kwargs)
                    return target.fn(*args, **kwargs)
                if callable(target):
                    return target(*args, **kwargs)
                raise TypeError("with_retry target must be Neuro/Flow/callable")
            except Exception as e:
                last_exc = e
                if i < attempts - 1:
                    await asyncio.sleep(backoff_s * (2 ** i))
        raise last_exc

    return neuro_decorator(
        _retry_async,
        effect=getattr(target, "effects", frozenset({Effect.PURE})),
        kind="recovery.retry",
        name=f"retry({getattr(target, 'name', 'anon')}, {attempts})",
        register=False,
    )


def with_fallback(primary, fallback):
    """Try `primary`; if it raises, run `fallback` with the same args."""
    from .flow import Flow

    async def _fallback_async(*args, **kwargs):
        try:
            if isinstance(primary, Flow):
                return await primary.run_async(*args, **kwargs)
            if isinstance(primary, Neuro):
                if inspect.iscoroutinefunction(primary.fn):
                    return await primary.fn(*args, **kwargs)
                return primary.fn(*args, **kwargs)
            return primary(*args, **kwargs)
        except Exception:
            if isinstance(fallback, Flow):
                return await fallback.run_async(*args, **kwargs)
            if isinstance(fallback, Neuro):
                if inspect.iscoroutinefunction(fallback.fn):
                    return await fallback.fn(*args, **kwargs)
                return fallback.fn(*args, **kwargs)
            return fallback(*args, **kwargs)

    return neuro_decorator(
        _fallback_async,
        kind="recovery.fallback",
        name=f"fallback({getattr(primary, 'name', 'p')}, {getattr(fallback, 'name', 'f')})",
        register=False,
    )


def with_escalation(primary, *, escalate_to: Callable):
    """Try `primary`; if it raises, hand control to `escalate_to(exc, args, kwargs)`."""
    from .flow import Flow

    async def _escalate_async(*args, **kwargs):
        try:
            if isinstance(primary, Flow):
                return await primary.run_async(*args, **kwargs)
            if isinstance(primary, Neuro):
                if inspect.iscoroutinefunction(primary.fn):
                    return await primary.fn(*args, **kwargs)
                return primary.fn(*args, **kwargs)
            return primary(*args, **kwargs)
        except Exception as exc:
            res = escalate_to(exc, args, kwargs)
            if inspect.iscoroutine(res):
                res = await res
            return res

    return neuro_decorator(
        _escalate_async,
        effect=Effect.HUMAN,
        kind="recovery.escalate",
        name=f"escalate({getattr(primary, 'name', 'p')})",
        register=False,
    )
