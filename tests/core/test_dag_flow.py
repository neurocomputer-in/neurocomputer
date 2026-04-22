import pytest
from core.flows.dag_flow import DagFlow


class DummyFactory:
    def __init__(self):
        self.calls = []

    async def run(self, name, state, **params):
        self.calls.append((name, dict(params)))
        return {f"{name}_ran": True}


async def test_dag_flow_walks_chain():
    factory = DummyFactory()
    state = {"__factory": factory}
    dag = {
        "start": "n0",
        "nodes": {
            "n0": {"neuro": "a", "params": {"x": 1}, "next": "n1"},
            "n1": {"neuro": "b", "params": {},       "next": None},
        },
    }
    f = DagFlow()
    out = await f.run(state, dag=dag)

    assert [c[0] for c in factory.calls] == ["a", "b"]
    assert state["a_ran"] is True
    assert state["b_ran"] is True


class ReplanOnceFactory:
    """On 'maybe' returns needs_replan first, succeeds second."""
    def __init__(self):
        self.calls = 0

    async def run(self, name, state, **params):
        if name == "planner":
            return {"plan": {"ok": True, "flow": {
                "start": "n0",
                "nodes": {"n0": {"neuro": "final", "params": {}, "next": None}},
            }}}
        if name == "maybe":
            self.calls += 1
            return {"needs_replan": True} if self.calls == 1 else {"ok": True}
        if name == "final":
            return {"final_done": True}
        return {}

    def catalogue(self, cid=None):
        return ["planner", "maybe", "final"]


async def test_dag_flow_replans_via_planner():
    factory = ReplanOnceFactory()
    events = []
    async def pub(topic, data): events.append((topic, data))
    state = {
        "__factory": factory,
        "__pub": pub,
        "__planner": "planner",
        "__cid": "test",
        "goal": "x",
    }
    dag = {
        "start": "n0",
        "nodes": {"n0": {"neuro": "maybe", "params": {}, "next": None}},
    }
    f = DagFlow()
    await f.run(state, dag=dag)

    assert state.get("final_done") is True
    assert sum(1 for t, _ in events if t == "task.done") == 1


async def test_dag_flow_publishes_node_events():
    class F:
        async def run(self, name, state, **params):
            return {"x": 1}
    events = []
    async def pub(topic, data): events.append((topic, data))
    state = {"__factory": F(), "__pub": pub}
    dag = {"start": "n0", "nodes": {"n0": {"neuro": "a", "params": {}, "next": None}}}

    await DagFlow().run(state, dag=dag)

    topics = [t for t, _ in events]
    assert "node.start" in topics
    assert "node.done" in topics
    assert "task.done" in topics


async def test_dag_flow_on_error_skip_continues():
    class F:
        async def run(self, name, state, **params):
            if name == "broken":
                raise RuntimeError("boom")
            return {f"{name}_ok": True}

    events = []
    async def pub(topic, data): events.append((topic, data))
    state = {"__factory": F(), "__pub": pub}
    dag = {
        "start": "n0",
        "nodes": {
            "n0": {"neuro": "broken", "on_error": "skip", "next": "n1"},
            "n1": {"neuro": "good", "next": None},
        },
    }
    await DagFlow().run(state, dag=dag)
    assert state.get("good_ok") is True
