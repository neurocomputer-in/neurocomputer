"""Tests for the NL → ProposedPlan planner."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from neurolang import neuro, Budget
from neurolang.cache import CompilerCache
from neurolang.propose import (
    propose_plan,
    ProposedPlan,
    NeuroChoice,
    MissingCapability,
    ProposeError,
)
from neurolang.registry import Registry


# ---- Test fixtures: a small dedicated registry for propose tests ---------

@pytest.fixture
def reg():
    """A fresh Registry seeded with two neuros that have explicit Budgets."""
    r = Registry()

    @neuro(
        name="prop.web.search",
        effect="tool",
        budget=Budget(cost_usd=0.001, latency_ms=500),
        register=False,
    )
    def _search(q: str) -> list:
        """Search the web."""
        return [q]

    @neuro(
        name="prop.reason.summarize",
        effect="llm",
        budget=Budget(cost_usd=0.005, latency_ms=1500),
        register=False,
    )
    def _summarize(items: list) -> str:
        """Summarize a list of items."""
        return ""

    @neuro(
        name="prop.no_budget",
        effect="pure",
        register=False,
    )
    def _no_budget(x: int) -> int:
        """Returns the input."""
        return x

    r.add(_search)
    r.add(_summarize)
    r.add(_no_budget)
    return r


# ---- LLM mocks: return canned JSON --------------------------------------

def _mk_llm(payload: dict):
    """Build an llm_fn that ignores input and returns the JSON-serialized payload."""
    def fn(prompt, system, *, model, **kwargs):
        return json.dumps(payload)
    return fn


# ---- Tests ---------------------------------------------------------------

def test_propose_basic(reg, tmp_path):
    cache = CompilerCache(tmp_path)
    payload = {
        "neuros": ["prop.web.search", "prop.reason.summarize"],
        "composition": "flow = prop.web.search | prop.reason.summarize",
        "missing": [],
    }
    plan = propose_plan(
        "search the web and summarize",
        llm_fn=_mk_llm(payload),
        registry=reg,
        cache=cache,
        use_cache=False,
    )
    assert isinstance(plan, ProposedPlan)
    assert plan.prompt == "search the web and summarize"
    assert plan.composition_source == payload["composition"]
    assert [n.name for n in plan.neuros] == payload["neuros"]
    assert plan.missing == []


def test_propose_cost_rolled_up_from_budgets(reg, tmp_path):
    cache = CompilerCache(tmp_path)
    payload = {
        "neuros": ["prop.web.search", "prop.reason.summarize"],
        "composition": "flow = prop.web.search | prop.reason.summarize",
        "missing": [],
    }
    plan = propose_plan(
        "x", llm_fn=_mk_llm(payload), registry=reg, cache=cache, use_cache=False,
    )
    assert plan.cost_estimate_usd == pytest.approx(0.006)
    assert plan.latency_estimate_ms == 2000


def test_propose_cost_zero_for_undeclared_budgets(reg, tmp_path):
    cache = CompilerCache(tmp_path)
    payload = {
        "neuros": ["prop.no_budget"],
        "composition": "flow = prop.no_budget",
        "missing": [],
    }
    plan = propose_plan(
        "x", llm_fn=_mk_llm(payload), registry=reg, cache=cache, use_cache=False,
    )
    assert plan.cost_estimate_usd == 0.0
    assert plan.latency_estimate_ms == 0


def test_propose_missing_capabilities_get_suggestions(reg, tmp_path):
    cache = CompilerCache(tmp_path)
    payload = {
        "neuros": ["prop.web.search"],
        "composition": "flow = prop.web.search",
        "missing": [{"intent": "search the web"}],
    }
    plan = propose_plan(
        "x", llm_fn=_mk_llm(payload), registry=reg, cache=cache, use_cache=False,
    )
    assert len(plan.missing) == 1
    m = plan.missing[0]
    assert m.intent == "search the web"
    # Substring match: "search" is a token in "prop.web.search"
    assert "prop.web.search" in m.suggestions


def test_propose_invalid_json_raises(reg, tmp_path):
    cache = CompilerCache(tmp_path)
    def bad_llm(prompt, system, *, model, **kwargs):
        return "not json at all"
    with pytest.raises(ProposeError):
        propose_plan("x", llm_fn=bad_llm, registry=reg, cache=cache, use_cache=False)


def test_propose_invalid_shape_raises(reg, tmp_path):
    """Even valid JSON must have the right shape — list, str, list."""
    cache = CompilerCache(tmp_path)

    # composition is null instead of str
    bad_payload = {"neuros": [], "composition": None, "missing": []}
    def bad_llm(prompt, system, *, model, **kwargs):
        return json.dumps(bad_payload)

    with pytest.raises(ProposeError):
        propose_plan("x", llm_fn=bad_llm, registry=reg, cache=cache, use_cache=False)


def test_propose_empty_registry(tmp_path):
    cache = CompilerCache(tmp_path)
    payload = {
        "neuros": [],
        "composition": "",
        "missing": [{"intent": "do anything"}],
    }
    plan = propose_plan(
        "x", llm_fn=_mk_llm(payload), registry=Registry(),
        cache=cache, use_cache=False,
    )
    assert plan.neuros == []
    assert len(plan.missing) == 1
    # No registry → no suggestions
    assert plan.missing[0].suggestions == []


def test_propose_resolves_short_neuro_names(reg, tmp_path):
    """LLMs commonly emit 'reason.summarize' when the registry stores
    'prop.reason.summarize' — propose_plan should resolve unique suffixes."""
    cache = CompilerCache(tmp_path)
    payload = {
        # Short names — should resolve to 'prop.web.search' and 'prop.reason.summarize'
        "neuros": ["web.search", "reason.summarize"],
        "composition": "flow = prop.web.search | prop.reason.summarize",
        "missing": [],
    }
    plan = propose_plan(
        "search and summarize",
        llm_fn=_mk_llm(payload),
        registry=reg,
        cache=cache,
        use_cache=False,
    )
    assert [n.name for n in plan.neuros] == ["prop.web.search", "prop.reason.summarize"]
    assert plan.missing == []


def test_propose_ambiguous_short_name_falls_through(reg, tmp_path):
    """If two registered neuros share a suffix, treat as unknown (no guess)."""
    # Add a second neuro that ALSO ends in '.summarize'
    @neuro(name="other.reason.summarize", effect="llm", register=False)
    def _other_summarize(text: str) -> str:
        return ""
    reg.add(_other_summarize)

    cache = CompilerCache(tmp_path)
    payload = {
        "neuros": ["reason.summarize"],  # ambiguous — two matches now
        "composition": "flow = prop.reason.summarize",
        "missing": [],
    }
    plan = propose_plan(
        "x", llm_fn=_mk_llm(payload), registry=reg, cache=cache, use_cache=False,
    )
    assert plan.neuros == []
    assert any("reason.summarize" in m.intent for m in plan.missing)


def test_propose_serializable_to_json(reg, tmp_path):
    cache = CompilerCache(tmp_path)
    payload = {
        "neuros": ["prop.web.search"],
        "composition": "flow = prop.web.search",
        "missing": [{"intent": "x"}],
    }
    plan = propose_plan(
        "x", llm_fn=_mk_llm(payload), registry=reg, cache=cache, use_cache=False,
    )
    # asdict + json roundtrip without exceptions
    d = dataclasses.asdict(plan)
    s = json.dumps(d, default=str)
    parsed = json.loads(s)
    assert parsed["composition_source"] == "flow = prop.web.search"
