import pytest
from core.flows.sequential_flow import SequentialFlow


class FakeChild:
    def __init__(self, payload):
        self.payload = payload

    async def run(self, state, **kw):
        state.setdefault("trace", []).append(self.payload["name"])
        return self.payload


async def test_sequential_runs_children_in_order():
    f = SequentialFlow()
    f.children = ["a", "b", "c"]
    f.a = FakeChild({"name": "a", "key_a": 1})
    f.b = FakeChild({"name": "b", "key_b": 2})
    f.c = FakeChild({"name": "c", "key_c": 3})

    state = {}
    out = await f.run(state)

    assert state["trace"] == ["a", "b", "c"]
    assert out == {"name": "c", "key_a": 1, "key_b": 2, "key_c": 3}
    assert state["key_a"] == 1
    assert state["key_b"] == 2
    assert state["key_c"] == 3
