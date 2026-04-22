"""ParallelFlow — concurrent fan-out over `self.children`."""
import asyncio
from core.flows.flow_neuro import FlowNeuro


class ParallelFlow(FlowNeuro):
    merge_key: str = None

    async def run(self, state, **kw):
        async def _one(name):
            child = getattr(self, name)
            out = await child.run(state, **kw)
            return name, (out if isinstance(out, dict) else {})

        pairs = await asyncio.gather(*(_one(n) for n in self.children))

        if self.merge_key:
            bucket = state.setdefault(self.merge_key, {})
            for name, out in pairs:
                bucket[name] = out
            return {self.merge_key: bucket}

        merged = {}
        for _, out in pairs:
            merged.update(out)
        state.update(merged)
        return merged
