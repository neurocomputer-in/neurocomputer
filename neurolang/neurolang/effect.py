"""Effect categories tracked by the runtime.

Every neuro declares its effect set. The runtime uses this for cost
accounting, budgeting, and (later) compile-time checks via mypy phantom
types. For now: runtime tags + decorator.
"""
from __future__ import annotations
from enum import Enum
from typing import Iterable


class Effect(str, Enum):
    PURE = "pure"          # deterministic, no side effects
    LLM = "llm"            # model invocation (cost, latency, nondeterminism)
    TOOL = "tool"          # external API / system call
    HUMAN = "human"        # blocks for human input
    TIME = "time"          # time-aware (sleep, schedule, deadline)
    VOICE = "voice"        # voice/audio surface (TTS, STT, calling)
    MEMORY = "memory"      # reads or writes persistent memory


def normalize_effects(effects: str | Effect | Iterable[str | Effect] | None) -> frozenset[Effect]:
    """Coerce loose effect declarations into a normalized frozenset."""
    if effects is None:
        return frozenset({Effect.PURE})
    if isinstance(effects, (str, Effect)):
        return frozenset({Effect(effects)})
    return frozenset(Effect(e) for e in effects)
