"""Tests for the coder workflow — proves the substrate handles a second domain.

Same mechanics as advisor, different prompts + policy. Same kind stack.
"""
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "coder.db"))
    monkeypatch.setenv("NEURO_GRAPH_DB",  str(tmp_path / "coder_graph.db"))
    return NeuroFactory(dir="neuros")


async def test_coder_system_prompt_has_code_focus(factory):
    """Composer should include coder persona + show-code rule."""
    state = {"__cid": "t"}
    out = await factory.run("coder_system_prompt", state)
    text = out["text"]
    assert "coder persona" in text.lower() or "neuro's coder" in text.lower()
    assert "fenced block" in text.lower()            # show-code rule
    assert "working code" in text.lower() or "produce working code" in text.lower()


async def test_coder_policy_priority_order(factory):
    """Show-code rule (80) > concise (70) > markdown (60) > helpful tone (40)."""
    out = await factory.run("instruction_policy_coder", {"__cid": "t"})
    priorities = [r["priority"] for r in out["rules"]]
    assert priorities == sorted(priorities, reverse=True)
    assert priorities[0] == 80   # show-code is top priority


async def test_coder_turn_calls_inference(factory):
    """coder_turn builds messages[system, user] and calls inference."""
    captured = {}
    class FakeModel:
        async def run(self, state, *, messages, **_):
            captured["messages"] = messages
            return {"content": "```python\nprint('hi')\n```"}

    state = {"__cid": "t", "text": "CODER SYSTEM PROMPT"}
    entry = factory.reg["coder_turn"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeModel()

    out = await factory.run("coder_turn", state, user_question="print hi in python")
    assert "```python" in out["reply"]
    assert captured["messages"][0]["content"] == "CODER SYSTEM PROMPT"
    assert captured["messages"][1]["content"] == "print hi in python"


async def test_coder_full_workflow(factory):
    """End-to-end: memory.read → system prompt → coder_turn → memory.write → librarian."""
    replies = iter([
        {"content": "```python\ndef fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)\n```\nRecursion is clearest; iterate if n > 30."},
        {"content": "```python\nfrom functools import lru_cache\n@lru_cache\ndef fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)\n```\nMemoization swap — O(n) now."},
    ])
    class FakeModel:
        async def run(self, state, *, messages, **_):
            return next(replies)
    class NoFacts:
        async def run(self, state, *, messages, **_):
            return {"content": '{"facts": []}'}

    state1 = {"__cid": "coder_session", "__agent_id": "neuro"}
    (await factory.pool.get(factory.reg["coder_turn"], state1)).inference = FakeModel()
    (await factory.pool.get(factory.reg["memory_extract"], state1)).inference = NoFacts()

    # Turn 1
    state_t1 = {**state1, "user_question": "fibonacci in python?"}
    await factory.run("coder", state_t1, user_question="fibonacci in python?")
    assert "def fib" in state_t1["reply"]
    assert "```python" in state_t1["reply"]

    # Turn 2 — memory should recall turn 1's topic
    state_t2 = {**state1, "user_question": "make it faster"}
    await factory.run("coder", state_t2, user_question="make it faster")
    assert "lru_cache" in state_t2["reply"]
    # Prior topic from flat-KV memory
    assert "fibonacci" in str(state_t2.get("value", "")).lower()


async def test_coder_vs_advisor_share_substrate_but_differ(factory):
    """Both workflows live in same factory, share L0 + memory blocks,
    but have different personas and policies."""
    rich = {e["name"]: e for e in factory.describe()}

    # Same kind
    assert rich["coder"]["kind"] == "skill.flow.dag"
    assert rich["advisor"]["kind"] == "skill.flow.dag"

    # Different categories
    assert rich["coder"]["category"] == "coder"
    assert rich["advisor"]["category"] == "advisor"

    # Both route through inference (via their respective _turn neuros)
    assert rich["coder_turn"]["uses"] == ["inference"]
    assert rich["advisor_turn"]["uses"] == ["inference"]

    # Shared infrastructure (memory_layer_identity, memory_recall_keyword)
    # both system-prompt composers pull from these.
    sp_coder   = set(rich["coder_system_prompt"]["uses"])
    sp_advisor = set(rich["advisor_system_prompt"]["uses"])
    shared = sp_coder & sp_advisor
    assert "memory_layer_identity" in shared
    assert "memory_recall_keyword" in shared

    # But different personas
    assert "prompt_block_coder_identity" in sp_coder
    assert "prompt_block_coder_identity" not in sp_advisor
    assert "prompt_block_advisor_identity" in sp_advisor
    assert "prompt_block_advisor_identity" not in sp_coder

    # Different policies
    assert "instruction_policy_coder" in sp_coder
    assert "instruction_policy_default" in sp_advisor
