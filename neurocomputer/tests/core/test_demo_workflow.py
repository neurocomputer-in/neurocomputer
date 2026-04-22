"""End-to-end test for the pure-conf cross-kind demo workflow.

Exercises:
  - prompt.block pure-conf synthesis (template substitution)
  - prompt.composer pure-conf synthesis (joining blocks)
  - skill.flow.dag pure-conf synthesis (DAG embedded in conf.json)
  - cross-kind composition (memory → prompt)
  - InstancePool (session-scoped composer instance)
"""
import os
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "demo.db"))
    return NeuroFactory(dir="neuros")


async def test_demo_prompt_blocks_render(factory):
    out = await factory.run("demo_block_identity", {"__cid": "t"}, agent_name="Gemma")
    assert out == {"text": "I am Gemma, a local-first AI assistant built on the neuro substrate."}

    out = await factory.run("demo_block_greet", {"__cid": "t"}, user_name="Alex")
    assert out == {"text": "Hello, Alex! How can I help today?"}

    out = await factory.run("demo_block_capabilities", {"__cid": "t"})
    assert "compose workflows" in out["text"]


async def test_demo_welcome_prompt_composes(factory):
    out = await factory.run(
        "demo_welcome_prompt",
        {"__cid": "t"},
        agent_name="Neuro",
        user_name="Gopal",
    )
    assert "I am Neuro" in out["text"]
    assert "compose workflows" in out["text"]
    assert "Hello, Gopal" in out["text"]
    assert out["text"].count("\n\n") == 2   # 3 blocks → 2 separators


async def test_demo_greet_workflow_end_to_end(factory):
    """Pure-conf skill.flow.dag that threads memory + prompt."""
    state = {"__cid": "demo_session", "__agent_id": "neuro"}
    out = await factory.run("demo_greet_workflow", state)

    # The DAG wrote 'Gopal' to memory, then read it back, then composed a prompt.
    # The final composer output's 'text' should be in state.
    assert "Hello, Gopal" in state["text"]
    assert "I am Neuro" in state["text"]
    # Memory read result also populates state['value'].
    assert state.get("value") == "Gopal"


async def test_demo_greet_workflow_describe_rich(factory):
    rich = {e["name"]: e for e in factory.describe()}
    wf = rich["demo_greet_workflow"]
    assert wf["kind"] == "skill.flow.dag"
    assert wf["kind_namespace"] == "skill"
    assert wf["category"] == "demo.workflow"

    composer = rich["demo_welcome_prompt"]
    assert composer["kind"] == "prompt.composer"
    assert composer["kind_namespace"] == "prompt"

    block = rich["demo_block_identity"]
    assert block["kind"] == "prompt.block"
    assert block["kind_namespace"] == "prompt"
