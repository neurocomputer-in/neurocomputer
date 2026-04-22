"""Tests for instruction.* kind — rule + tone + policy."""
import pytest
from core.neuro_factory import NeuroFactory


async def test_instruction_rule_emits_structured_output():
    f = NeuroFactory(dir="neuros")
    out = await f.run("instruction_rule_markdown", {"__cid": "t"})
    assert "markdown" in out["text"].lower()
    assert out["category"] == "formatting"
    assert out["priority"] == 60


async def test_instruction_tone_adds_voice():
    f = NeuroFactory(dir="neuros")
    out = await f.run("instruction_tone_helpful", {"__cid": "t"})
    assert out["voice"] == "warm-expert"
    assert out["priority"] == 40


async def test_instruction_policy_orders_rules_by_priority():
    f = NeuroFactory(dir="neuros")
    out = await f.run("instruction_policy_default", {"__cid": "t"})
    assert out["count"] == 3
    assert isinstance(out["rules"], list)

    # Sorted priority desc: concise(70) > markdown(60) > helpful(40)
    priorities = [r["priority"] for r in out["rules"]]
    assert priorities == [70, 60, 40]

    # Combined text joins all rule texts
    assert "markdown" in out["text"].lower()
    assert "direct" in out["text"].lower()
    assert "warm" in out["text"].lower()


async def test_instruction_policy_filters_by_category_when_override():
    """Pure-conf policy can be synthesized with filter_category to subset rules."""
    f = NeuroFactory(dir="neuros")
    # The shipped default policy has no filter. Verify filter attr works
    # via the synthesized class of instruction_policy_default.
    entry = f.reg["instruction_policy_default"]
    inst = await f.pool.get(entry, {"__cid": "_"})
    # Runtime override (simulates an alternate policy)
    inst.filter_category = "style"
    out = await inst.run({"__cid": "_"})
    assert out["count"] == 1
    assert out["rules"][0]["category"] == "style"


async def test_instruction_describe_rich():
    f = NeuroFactory(dir="neuros")
    rich = {e["name"]: e for e in f.describe()}
    policy = rich["instruction_policy_default"]
    assert policy["kind"] == "instruction.policy"
    assert policy["kind_namespace"] == "instruction"
    rule = rich["instruction_rule_markdown"]
    assert rule["kind"] == "instruction.rule"
    tone = rich["instruction_tone_helpful"]
    assert tone["kind"] == "instruction.tone"
