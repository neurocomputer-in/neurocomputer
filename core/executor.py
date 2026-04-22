"""Executor — thin compatibility shim. Body moved into core.flows.DagFlow.

Removed in Phase F of the 01-core migration. Kept here so any import
`from core.executor import Executor` keeps working during rollout.
"""


class Executor:
    def __init__(self, flow, factory, state, pub):
        self._flow = flow
        self._factory = factory
        self._state = state
        self._state["__pub"] = pub

    async def run(self):
        await self._factory.run("dag_flow", self._state, dag=self._flow)
