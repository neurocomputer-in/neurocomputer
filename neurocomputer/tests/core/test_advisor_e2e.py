"""End-to-end prototype test for the 'advisor' workflow — everything-as-neuro.

Exercises the full cross-kind chain:
  memory.store → prompt.composer (w/ instruction.policy + prompt.blocks)
              → skill.leaf → model.llm → memory.store

LLM calls are mocked to keep tests deterministic + network-free.
"""
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "advisor.db"))
    monkeypatch.setenv("NEURO_GRAPH_DB",  str(tmp_path / "advisor_graph.db"))
    return NeuroFactory(dir="neuros")


async def test_advisor_system_prompt_composes_everything(factory):
    """prompt.composer threads identity + role + policy + memory block."""
    state = {"__cid": "t", "last_topic": "gradient descent"}
    out = await factory.run("advisor_system_prompt", state)
    t = out["text"]
    assert "You are Neuro" in t                    # identity
    assert "lead with the answer" in t.lower() or "Lead with the answer" in t  # role or policy
    assert "markdown" in t.lower()                  # policy (markdown rule)
    assert "gradient descent" in t                  # memory block picked up last_topic


async def test_advisor_turn_calls_model(factory, monkeypatch):
    """advisor_turn passes system + user messages to model.llm, returns reply."""
    captured = {}

    class FakeModel:
        async def run(self, state, *, messages, **_):
            captured["messages"] = messages
            return {"content": "mock answer here"}

    # Monkey-patch the inference instance to not hit the network.
    state = {"__cid": "t", "text": "YOU ARE A TEST"}
    # Force creation via pool, then replace.
    entry = factory.reg["advisor_turn"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeModel()

    out = await factory.run("advisor_turn", state, user_question="what is 2+2?")
    assert out["reply"] == "mock answer here"
    assert captured["messages"][0]["role"] == "system"
    assert "YOU ARE A TEST" in captured["messages"][0]["content"]
    assert captured["messages"][1]["role"] == "user"
    assert captured["messages"][1]["content"] == "what is 2+2?"


async def test_advisor_full_workflow(factory, monkeypatch):
    """End-to-end: memory.read → prompt.compose → advisor_turn → memory.write."""
    replies = iter([
        {"content": "Gradient descent is an optimization algorithm that..."},
        {"content": "The learning rate controls how big a step you take..."},
    ])

    class FakeModel:
        async def run(self, state, *, messages, **_):
            return next(replies)

    # Pre-create advisor_turn + memory_extract instances and stub both.
    state1 = {"__cid": "advisor_session", "__agent_id": "neuro",
              "user_question": "what is gradient descent?"}
    entry = factory.reg["advisor_turn"]
    inst = await factory.pool.get(entry, state1)
    inst.inference = FakeModel()

    # Stub memory_extract's inference too (n4 runs it after every reply) —
    # emit an empty facts list so the librarian step is a no-op.
    class NoFactsModel:
        async def run(self, state, *, messages, **_):
            return {"content": '{"facts": []}'}
    extract_entry = factory.reg["memory_extract"]
    extract_inst = await factory.pool.get(extract_entry, state1)
    extract_inst.inference = NoFactsModel()

    # Turn 1 — no prior topic in memory, so memory block degrades gracefully.
    out1 = await factory.run("advisor", state1, user_question="what is gradient descent?")
    assert "gradient descent" in state1["reply"].lower()

    # Turn 2 — memory now has last_topic=user_question from turn 1.
    # advisor_system_prompt's memory block should pick it up via {{state.value}}.
    state2 = {"__cid": "advisor_session", "__agent_id": "neuro",
              "user_question": "what about learning rate?"}
    # Advisor_turn instance is session-scoped; still attached to FakeModel.
    out2 = await factory.run("advisor", state2, user_question="what about learning rate?")

    assert state2["reply"] != state1["reply"]
    # Prior topic flowed from memory into system prompt on turn 2
    prev_topic = state2.get("last_topic") or state2.get("value")
    assert "gradient descent" in str(prev_topic).lower()


async def test_advisor_describe_rich(factory):
    rich = {e["name"]: e for e in factory.describe()}
    adv = rich["advisor"]
    assert adv["kind"] == "skill.flow.dag"
    assert adv["category"] == "advisor"
    assert set(adv["uses"]) == {"memory", "advisor_system_prompt", "advisor_turn",
                                "memory_ingest"}

    sp = rich["advisor_system_prompt"]
    assert sp["kind"] == "prompt.composer"
    # Cross-kind: composer's uses span prompt.* + instruction.* + memory.*
    expected_uses = {
        "memory_layer_identity",
        "prompt_block_advisor_identity",
        "prompt_block_advisor_role",
        "instruction_policy_default",
        "prompt_block_advisor_memory",
        "memory_recall_keyword",
    }
    assert set(sp["uses"]) == expected_uses

    turn = rich["advisor_turn"]
    assert turn["uses"] == ["inference"]
