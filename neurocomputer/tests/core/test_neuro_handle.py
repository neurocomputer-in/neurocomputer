import pytest
from core.neuro_handle import NeuroHandle


class FakeFactory:
    def __init__(self):
        self.calls = []

    async def run(self, name, state, **params):
        self.calls.append((name, dict(params)))
        return {"n": name}


async def test_handle_forwards_to_factory():
    factory = FakeFactory()
    h = NeuroHandle(factory, "search")
    out = await h.run({}, q="x")
    assert out == {"n": "search"}
    assert factory.calls == [("search", {"q": "x"})]


async def test_handle_identity_carries_name():
    h = NeuroHandle(FakeFactory(), "plan")
    assert h.name == "plan"
    assert "plan" in repr(h)
