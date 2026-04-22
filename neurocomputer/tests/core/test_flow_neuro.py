import pytest
from core.flows.flow_neuro import FlowNeuro


class DemoFlow(FlowNeuro):
    async def run(self, state, **kw):
        state["ran"] = True
        return {"ok": True}


async def test_flow_neuro_is_callable():
    f = DemoFlow()
    state = {}
    out = await f.run(state)
    assert out == {"ok": True}
    assert state["ran"] is True


async def test_flow_neuro_has_default_hooks():
    f = DemoFlow()
    await f.before_child("x", {}, {})
    await f.after_child("x", {}, {})
    assert await f.on_child_error("x", ValueError("boom"), {}) == "replan"


async def test_flow_neuro_class_attrs_defaults():
    assert FlowNeuro.uses == []
    assert FlowNeuro.children == []
    assert FlowNeuro.replan_policy == "inherit"
