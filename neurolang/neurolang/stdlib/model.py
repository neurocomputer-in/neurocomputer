"""Model stdlib neuros — uniform LLM access across providers.

Every model here is a neuro. Compose them like any other neuro.
Optional deps: `openai`, `anthropic`. Soft-imported at call time.
"""
from __future__ import annotations

from typing import Optional

from ..neuro import neuro
from ..budget import Budget


def _require(module_name: str):
    try:
        return __import__(module_name)
    except ImportError as e:
        raise ImportError(
            f"This neuro needs `{module_name}`. Install with: pip install {module_name}"
        ) from e


class llm:
    """Namespace for LLM provider neuros. Use `llm.openai(...)` etc."""

    @staticmethod
    @neuro(
        effect="llm",
        kind="model.llm.openai",
        name="neurolang.stdlib.model.llm.openai",
        budget=Budget(latency_ms=2000, cost_usd=0.005),
    )
    def openai(prompt: str, *, model: Optional[str] = None, system: Optional[str] = None,
               temperature: float = 0.0, max_tokens: int = 1024,
               provider: Optional[str] = None) -> str:
        """Call LLM via the configured provider (default: opencode-zen)."""
        from .._providers import normalize_provider, _PROVIDERS, resolve_model
        p = normalize_provider(provider)
        fn, default_model = _PROVIDERS[p]
        model_resolved = resolve_model(p, model) if model else default_model
        return fn(prompt, system or "", model=model_resolved, kind="compile")

    @staticmethod
    @neuro(
        effect="llm",
        kind="model.llm.anthropic",
        name="neurolang.stdlib.model.llm.anthropic",
        budget=Budget(latency_ms=2500, cost_usd=0.008),
    )
    def anthropic(prompt: str, *, model: str = "claude-sonnet-4-5", system: Optional[str] = None,
                  temperature: float = 0.0, max_tokens: int = 1024) -> str:
        """Call Anthropic messages API."""
        anthro = _require("anthropic")
        client = anthro.Anthropic()
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system
        resp = client.messages.create(**kwargs)
        # Concatenate all text blocks
        return "".join(getattr(b, "text", "") for b in resp.content)
