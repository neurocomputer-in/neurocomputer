"""LocalNeuroNet — minimal in-process runtime.

Sufficient for standalone use of the NeuroLang library. Production
deployments use Neurocomputer or another full implementation.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Optional

from .context import set_active_memory, reset_active_memory


@dataclass
class _Handle:
    task: asyncio.Task

    def result(self):
        return self.task.result()

    def cancel(self):
        return self.task.cancel()

    def done(self) -> bool:
        return self.task.done()


@dataclass
class LocalNeuroNet:
    """In-process runtime. No persistence, no IDE — just runs Plans."""

    _live_plans: list = field(default_factory=list)

    async def execute(self, plan, *, memory=None) -> Any:
        token = set_active_memory(memory)
        try:
            return await plan.run_async(memory=memory) if False else \
                   await plan.run_async(memory=memory)
        finally:
            reset_active_memory(token)

    def submit(self, plan, *, memory=None) -> _Handle:
        loop = asyncio.get_event_loop()
        task = loop.create_task(self.execute(plan, memory=memory))
        h = _Handle(task=task)
        self._live_plans.append(h)
        return h

    def topology(self) -> dict:
        return {
            "kind": "LocalNeuroNet",
            "live_plans": len([h for h in self._live_plans if not h.done()]),
            "completed_plans": len([h for h in self._live_plans if h.done()]),
        }

    def snapshot(self) -> dict:
        return {"topology": self.topology()}

    def __repr__(self) -> str:
        return f"LocalNeuroNet<live={len([h for h in self._live_plans if not h.done()])}>"
