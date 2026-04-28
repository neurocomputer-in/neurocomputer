"""Tests for the LLM-backed reason.* stdlib neuros (brainstorm + deep_research).

Patches _PROVIDERS directly so tests run fully offline. The reason.* neuros
now route through _call_llm → _PROVIDERS rather than calling llm.openai/anthropic.
"""
from __future__ import annotations

import pytest

from neurolang.stdlib import reason
from neurolang import _providers


# ---- Fixtures ---------------------------------------------------------------

@pytest.fixture
def captured_default_calls(monkeypatch):
    """Patch the default provider (opencode-zen) in _PROVIDERS; capture calls."""
    captured: list = []
    def fake(prompt, system, *, model, kind, **kwargs):
        captured.append({"prompt": prompt, "system": system, "model": model, "kind": kind})
        return "FAKE_LLM_RESPONSE"
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (fake, "opencode/minimax-m2.5-free"))
    return captured


@pytest.fixture
def captured_anthropic_calls(monkeypatch):
    """Patch the anthropic provider in _PROVIDERS; capture calls."""
    captured: list = []
    def fake(prompt, system, *, model, kind, **kwargs):
        captured.append({"prompt": prompt, "system": system, "model": model, "kind": kind})
        return "FAKE_ANTHROPIC_RESPONSE"
    monkeypatch.setitem(_providers._PROVIDERS, "anthropic", (fake, "claude-sonnet-4-5"))
    return captured


# ---- reason.brainstorm tests ------------------------------------------------

def test_brainstorm_calls_openai_with_topic_and_n(captured_default_calls):
    out = reason.brainstorm("ways to learn category theory", n=3)
    assert out == "FAKE_LLM_RESPONSE"
    assert len(captured_default_calls) == 1
    prompt = captured_default_calls[0]["prompt"]
    assert "ways to learn category theory" in prompt
    # n appears in the prompt — both as the count of bullets and the directive
    assert "3" in prompt


def test_brainstorm_default_n_is_5(captured_default_calls):
    reason.brainstorm("any topic")
    prompt = captured_default_calls[0]["prompt"]
    # The n=5 default appears at least twice in the prompt:
    # "Brainstorm 5 distinct..." and "Output exactly 5 bullet lines..."
    assert prompt.count("5") >= 2


def test_brainstorm_anthropic_routing(captured_anthropic_calls):
    out = reason.brainstorm("topic", model="anthropic")
    assert out == "FAKE_ANTHROPIC_RESPONSE"
    assert len(captured_anthropic_calls) == 1


def test_brainstorm_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        reason.brainstorm("topic", model="grok")


# ---- reason.deep_research tests ----------------------------------------------

def test_deep_research_calls_openai_with_question(captured_default_calls):
    out = reason.deep_research("impact of microplastics on marine life")
    assert out == "FAKE_LLM_RESPONSE"
    prompt = captured_default_calls[0]["prompt"]
    assert "impact of microplastics on marine life" in prompt
    # The scaffolded prompt structure should be present
    assert "sub-questions" in prompt
    assert "Caveats" in prompt


def test_deep_research_default_depth_is_standard(captured_default_calls):
    reason.deep_research("any question")
    prompt = captured_default_calls[0]["prompt"]
    # standard depth → ~500 words target; 1500 must NOT appear
    assert "~500 words" in prompt
    assert "1500" not in prompt


def test_deep_research_deep_depth_uses_higher_target(captured_default_calls):
    reason.deep_research("any question", depth="deep")
    prompt = captured_default_calls[0]["prompt"]
    assert "~1500 words" in prompt


def test_deep_research_anthropic_routing(captured_anthropic_calls):
    out = reason.deep_research("question", model="anthropic")
    assert out == "FAKE_ANTHROPIC_RESPONSE"
    assert len(captured_anthropic_calls) == 1


def test_deep_research_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        reason.deep_research("question", model="grok")


def test_deep_research_unknown_depth_raises():
    """Typo guard: depth='deep' or 'standard' only — silent fallthrough was a footgun."""
    with pytest.raises(ValueError, match="Unknown depth"):
        reason.deep_research("question", depth="deeper")
