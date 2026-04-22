"""Tests for model.inference — the uniform model-dispatch neuro."""
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory():
    return NeuroFactory(dir="neuros")


def _install_fake(inference_inst, name, fn):
    """Helper: replace a provider handle on the inference instance."""
    class _H:
        async def run(self, state, **kw):
            return await fn(state, **kw)
    setattr(inference_inst, name, _H())


async def test_inference_routes_to_default_provider(factory):
    """When no provider override, goes to default_provider (opencode-zen)."""
    entry = factory.reg["inference"]
    inf = await factory.pool.get(entry, {"__cid": "t"})
    called = {}

    async def fake_oz(state, **kw):
        called["oz"] = kw
        return {"content": "zen response", "thinking": None}
    _install_fake(inf, "model_llm_opencode_zen", fake_oz)

    out = await factory.run("inference", {"__cid": "t"}, user_msg="hello")
    assert out["content"] == "zen response"
    assert out["provider_used"] == "model_llm_opencode_zen"
    assert called["oz"]["user_msg"] == "hello"


async def test_inference_falls_back_when_primary_errors(factory):
    """If primary provider returns an error, inference tries next in chain."""
    entry = factory.reg["inference"]
    inf = await factory.pool.get(entry, {"__cid": "t"})

    async def fake_oz(state, **kw):
        return {"content": "", "error": "zen out of quota"}
    async def fake_or(state, **kw):
        return {"content": "from openrouter", "thinking": None}

    _install_fake(inf, "model_llm_opencode_zen", fake_oz)
    _install_fake(inf, "model_llm_openrouter",   fake_or)

    out = await factory.run("inference", {"__cid": "t"}, user_msg="hi")
    assert out["content"] == "from openrouter"
    assert out["provider_used"] == "model_llm_openrouter"
    assert out["fallback_from"] == "model_llm_opencode_zen"


async def test_inference_explicit_provider_override(factory):
    entry = factory.reg["inference"]
    inf = await factory.pool.get(entry, {"__cid": "t"})

    async def fake_ollama(state, **kw):
        return {"content": "local via ollama"}
    _install_fake(inf, "model_llm_ollama", fake_ollama)

    out = await factory.run("inference", {"__cid": "t"},
                            user_msg="hi",
                            provider="model_llm_ollama")
    assert out["content"] == "local via ollama"
    assert out["provider_used"] == "model_llm_ollama"


async def test_inference_all_providers_fail(factory):
    entry = factory.reg["inference"]
    inf = await factory.pool.get(entry, {"__cid": "t"})

    async def fail(state, **kw):
        return {"content": "", "error": "nope"}
    for p in ("model_llm_opencode_zen", "model_llm_openrouter",
              "model_llm_ollama", "model_llm_openai"):
        _install_fake(inf, p, fail)

    out = await factory.run("inference", {"__cid": "t"}, user_msg="hi")
    assert out["content"] == ""
    assert "error" in out
    # error string mentions at least one provider
    assert any(p in out["error"] for p in
               ("opencode_zen", "openrouter", "ollama", "openai"))


async def test_inference_describe_rich(factory):
    rich = {e["name"]: e for e in factory.describe()}
    inf = rich["inference"]
    assert inf["kind"] == "model.inference"
    assert inf["kind_namespace"] == "model"
    assert set(inf["uses"]) == {
        "model_llm_opencode_zen", "model_llm_openrouter",
        "model_llm_ollama", "model_llm_openai",
        "model_vision_openai",
    }


async def test_inference_unknown_modality_returns_error(factory):
    # 'audio' has no provider mapped (image routes to model_vision_openai now)
    entry = factory.reg["inference"]
    out = await factory.run("inference", {"__cid": "t"},
                            modality="audio", audio="/tmp/x.wav")
    assert out["content"] == ""
    assert "audio" in out["error"]


async def test_inference_image_modality_routes_to_vision(factory):
    """modality='image' routes to model_vision_openai per default conf."""
    entry = factory.reg["inference"]
    inf = await factory.pool.get(entry, {"__cid": "t"})
    captured = {}

    class FakeVision:
        async def run(self, state, **kw):
            captured.update(kw)
            return {"content": "I see a red cat."}

    inf.model_vision_openai = FakeVision()

    out = await factory.run("inference", {"__cid": "t"},
                            modality="image",
                            messages=[{"role": "user", "content": [
                                {"type": "text", "text": "what's this?"},
                                {"type": "image_url",
                                 "image_url": {"url": "data:image/jpeg;base64,..."}},
                            ]}])
    assert out["content"] == "I see a red cat."
    assert out["provider_used"] == "model_vision_openai"
    assert captured["messages"][0]["role"] == "user"


async def test_inference_custom_modality_mapping_via_conf(factory):
    """Pure-conf variant of inference that maps image → a specific provider."""
    import json, pathlib, textwrap
    # This test doesn't synthesize a new neuro — instead it verifies the
    # attribute passthrough by patching the shipped inference instance.
    entry = factory.reg["inference"]
    inf = await factory.pool.get(entry, {"__cid": "t"})
    inf.modality_providers = {"image": "model_llm_openai"}

    async def fake_oa(state, **kw):
        return {"content": "image described", "thinking": None}
    _install_fake(inf, "model_llm_openai", fake_oa)

    out = await factory.run("inference", {"__cid": "t"},
                            modality="image", image=[{"url": "..."}])
    assert out["content"] == "image described"
    assert out["provider_used"] == "model_llm_openai"
