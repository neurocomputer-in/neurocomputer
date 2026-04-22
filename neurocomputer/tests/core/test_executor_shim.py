import pytest
from core.executor import Executor


class RememberFactory:
    def __init__(self):
        self.called_with = None

    async def run(self, name, state, **params):
        self.called_with = (name, dict(params), state)
        return {"ok": True}


async def test_executor_shim_forwards_to_dag_flow():
    factory = RememberFactory()
    pub_log = []
    async def pub(t, d): pub_log.append((t, d))
    dag = {"start": "n0",
           "nodes": {"n0": {"neuro": "whatever", "params": {}, "next": None}}}
    state = {}

    exe = Executor(dag, factory, state, pub)
    await exe.run()

    assert factory.called_with is not None
    assert factory.called_with[0] == "dag_flow"
    assert factory.called_with[1].get("dag") == dag
    assert state["__pub"] is pub
