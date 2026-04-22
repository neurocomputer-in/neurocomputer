import asyncio
import pytest
from core.flows.parallel_flow import ParallelFlow


class SleeperChild:
    def __init__(self, name, delay):
        self.name = name
        self.delay = delay

    async def run(self, state, **kw):
        await asyncio.sleep(self.delay)
        return {self.name: True}


async def test_parallel_fans_out():
    f = ParallelFlow()
    f.children = ["a", "b", "c"]
    f.a = SleeperChild("a", 0.01)
    f.b = SleeperChild("b", 0.01)
    f.c = SleeperChild("c", 0.01)

    out = await f.run({})
    assert out == {"a": True, "b": True, "c": True}


async def test_parallel_merge_key_scoping():
    f = ParallelFlow()
    f.children = ["x", "y"]
    f.merge_key = "per_child"
    f.x = SleeperChild("shared", 0.001)
    f.y = SleeperChild("shared", 0.001)

    out = await f.run({})
    assert "per_child" in out
    assert set(out["per_child"].keys()) == {"x", "y"}
