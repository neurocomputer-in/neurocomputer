"""Tests for model.* kind — provider wrapper registration + attribute plumbing.

Actual LLM calls are not exercised here (require live API keys + network).
Integration tests live elsewhere; these verify the substrate is wired.
"""
import pytest
from core.neuro_factory import NeuroFactory


async def test_model_llm_openrouter_attrs():
    f = NeuroFactory(dir="neuros")
    entry = f.reg["model_llm_openrouter"]
    assert entry.cls.provider == "openrouter"
    assert entry.cls.default_model == "minimax/minimax-m2.5:free"
    assert entry.cls.scope == "singleton"


async def test_model_llm_openai_attrs():
    f = NeuroFactory(dir="neuros")
    entry = f.reg["model_llm_openai"]
    assert entry.cls.provider == "openai"
    assert entry.cls.default_model == "gpt-4o-mini"


async def test_model_llm_ollama_attrs():
    f = NeuroFactory(dir="neuros")
    entry = f.reg["model_llm_ollama"]
    assert entry.cls.provider == "ollama"
    assert entry.cls.default_model == "gemma4:e4b"


async def test_model_llm_opencode_zen_attrs():
    f = NeuroFactory(dir="neuros")
    entry = f.reg["model_llm_opencode_zen"]
    assert entry.cls.provider == "opencode-zen"
    assert entry.cls.default_model.startswith("opencode/")


async def test_model_llm_describe_rich():
    f = NeuroFactory(dir="neuros")
    rich = {e["name"]: e for e in f.describe()}

    for name in ("model_llm_openrouter", "model_llm_openai",
                 "model_llm_ollama", "model_llm_opencode_zen"):
        assert name in rich
        assert rich[name]["kind"] == "model.llm"
        assert rich[name]["kind_namespace"] == "model"
        assert rich[name]["category"] == "model.llm"


async def test_model_llm_bad_provider_returns_error_not_raise(monkeypatch):
    """If brain-init fails, neuro returns structured error, not raise."""
    import core.base_brain as bb

    class BoomBrain:
        def __init__(self, *a, **kw):
            raise RuntimeError("simulated init failure")

    monkeypatch.setattr(bb, "BaseBrain", BoomBrain)

    f = NeuroFactory(dir="neuros")
    out = await f.run("model_llm_openrouter", {"__cid": "t"}, user_msg="hi")
    assert out["content"] == ""
    assert "error" in out
    assert "simulated init failure" in out["error"]
