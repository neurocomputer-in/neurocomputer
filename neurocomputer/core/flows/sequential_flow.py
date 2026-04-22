"""SequentialFlow — orchestrates `self.children` in declared order."""
from core.flows.flow_neuro import FlowNeuro


class SequentialFlow(FlowNeuro):
    async def run(self, state, **kw):
        acc = {}
        for name in self.children:
            child = getattr(self, name)
            await self.before_child(name, kw, state)
            child_out = await child.run(state, **kw)
            if not isinstance(child_out, dict):
                child_out = {}
            state.update(child_out)
            acc.update(child_out)
            await self.after_child(name, child_out, state)
        return acc
