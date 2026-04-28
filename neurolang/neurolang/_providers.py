"""LLM provider plumbing — multi-provider, multi-model.

Mirrors /home/ubuntu/neurocomputer/neurocomputer/core/llm_registry.py.
Each provider has env_key + base_url + default_model + aliases + model_prefix
+ models list. API keys fall back to ~/.local/share/opencode/auth.json for
providers that share creds with the OpenCode CLI.

Both compile_source and propose_plan dispatch through this module via _PROVIDERS.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from .registry import default_registry


PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "opencode-zen": {
        # OpenCode Zen — curated gateway of coding-agent-tuned models.
        # Docs: https://opencode.ai/docs/zen/  Catalog: mastra.ai/models/providers/opencode
        # The `opencode/` prefix is the opencode CLI's config-level identifier;
        # the HTTP /v1/chat/completions endpoint expects the bare model id.
        # `resolve_model` strips the prefix before each call.
        "display_name": "OpenCode Zen",
        "env_key": "OPENCODE_API_KEY",
        "base_url": "https://opencode.ai/zen/v1",
        "default_model": "opencode/minimax-m2.5-free",
        "model_prefix": "opencode/",
        "headers": {},
        "aliases": {},
        "models": [
            "opencode/big-pickle",
            "opencode/claude-3-5-haiku",
            "opencode/claude-haiku-4-5",
            "opencode/claude-opus-4-1",
            "opencode/claude-opus-4-5",
            "opencode/claude-opus-4-6",
            "opencode/claude-opus-4-7",
            "opencode/claude-sonnet-4",
            "opencode/claude-sonnet-4-5",
            "opencode/claude-sonnet-4-6",
            "opencode/gemini-3-flash",
            "opencode/gemini-3.1-pro",
            "opencode/glm-5",
            "opencode/glm-5.1",
            "opencode/gpt-5",
            "opencode/gpt-5-codex",
            "opencode/gpt-5-nano",
            "opencode/gpt-5.1",
            "opencode/gpt-5.1-codex",
            "opencode/gpt-5.1-codex-max",
            "opencode/gpt-5.1-codex-mini",
            "opencode/gpt-5.2",
            "opencode/gpt-5.2-codex",
            "opencode/gpt-5.3-codex",
            "opencode/gpt-5.3-codex-spark",
            "opencode/gpt-5.4",
            "opencode/gpt-5.4-mini",
            "opencode/gpt-5.4-nano",
            "opencode/gpt-5.4-pro",
            "opencode/kimi-k2.5",
            "opencode/minimax-m2.5",
            "opencode/minimax-m2.5-free",
            "opencode/nemotron-3-super-free",
            "opencode/qwen3.5-plus",
            "opencode/qwen3.6-plus",
        ],
    },
    "openrouter": {
        "display_name": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "minimax/minimax-m2.5:free",
        "headers": {
            "HTTP-Referer": "https://github.com/neurocomputer-in/neurolang",
            "X-Title": "NeuroLang",
        },
        "aliases": {},
        "models": [
            "minimax/minimax-m2.5:free",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-001",
        ],
    },
    "openai": {
        "display_name": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": None,  # SDK default
        "default_model": "gpt-4o-mini",
        "headers": {},
        "aliases": {},
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1"],
    },
    "anthropic": {
        "display_name": "Anthropic",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": None,
        "default_model": "claude-sonnet-4-5",
        "headers": {},
        "aliases": {},
        "models": ["claude-sonnet-4-5", "claude-haiku-4-5", "claude-opus-4-7"],
    },
    "ollama": {
        "display_name": "Ollama (local)",
        "env_key": "OLLAMA_API_KEY",
        "base_url": "http://localhost:11434/v1",
        "default_model": "gemma4:e4b",
        "headers": {},
        "aliases": {},
        "models": ["gemma4:e4b", "gemma4:27b", "qwen3:8b"],
    },
}


DEFAULT_PROVIDER = (
    os.getenv("DEFAULT_LLM_PROVIDER", "opencode-zen").strip().lower()
    or "opencode-zen"
)

PROVIDER_KINDS = ("compile", "decompile", "plan", "reason", "reason.deep")

# Max output tokens by call kind.
# "reason.deep" targets ~1500 words (~2000 tokens) so needs headroom above 2048.
_KIND_MAX_TOKENS: dict[str, int] = {
    "compile": 2048,
    "decompile": 512,
    "plan": 2048,
    "reason": 2048,
    "reason.deep": 4096,
}


# OpenCode CLI's auth file — fallback for OpenCode Zen if env var unset.
_OPENCODE_AUTH_PATH = Path.home() / ".local" / "share" / "opencode" / "auth.json"
_PROVIDER_AUTH_FALLBACK: Dict[str, str] = {
    "opencode-zen": "opencode",
}


def _read_opencode_auth_key(auth_entry: str) -> str:
    try:
        with open(_OPENCODE_AUTH_PATH) as f:
            data = json.load(f)
        entry = data.get(auth_entry) or {}
        key = entry.get("key") if isinstance(entry, dict) else None
        return key.strip() if isinstance(key, str) else ""
    except Exception:
        return ""


def get_api_key(provider: str) -> str:
    """Resolve API key: env var first, then opencode auth.json fallback."""
    cfg = PROVIDER_CONFIGS.get(provider) or {}
    env_key = cfg.get("env_key", "")
    if env_key:
        val = os.getenv(env_key, "").strip()
        if val:
            return val
    fallback = _PROVIDER_AUTH_FALLBACK.get(provider)
    if fallback:
        return _read_opencode_auth_key(fallback)
    return ""


def resolve_model(provider: str, model_name: Optional[str]) -> str:
    """Resolve a model name through aliases + model_prefix stripping."""
    cfg = PROVIDER_CONFIGS[provider]
    name = (model_name or "").strip()
    if not name:
        name = cfg["default_model"]
    name = cfg.get("aliases", {}).get(name, name)
    prefix = cfg.get("model_prefix", "")
    if prefix and name.startswith(prefix):
        name = name[len(prefix):]
    return name


def normalize_provider(provider: Optional[str], strict: bool = False) -> str:
    candidate = (provider or DEFAULT_PROVIDER).strip().lower()
    if candidate not in PROVIDER_CONFIGS:
        if strict:
            raise ValueError(
                f"Unknown LLM provider {candidate!r}. "
                f"Available: {', '.join(sorted(PROVIDER_CONFIGS))}"
            )
        return candidate
    return candidate


# ---------------------------------------------------------------------------
# Generic OpenAI-SDK dispatch (used by all providers except anthropic)
# ---------------------------------------------------------------------------

def _llm_call_via_openai_sdk(
    prompt: str,
    system: str,
    *,
    model: str,            # incoming = model_id (already resolved)
    kind: str,
    provider: str,
    temperature: float = 0.0,
) -> str:
    """OpenAI-SDK-compatible call for any provider with an openai-compat base_url."""
    try:
        import openai
    except ImportError as e:
        raise ImportError("LLM call needs `openai`. Install: pip install openai") from e
    cfg = PROVIDER_CONFIGS[provider]
    api_key = get_api_key(provider) or "missing-key"  # ollama tolerates anything
    client = openai.OpenAI(
        api_key=api_key,
        base_url=cfg.get("base_url"),
        default_headers=cfg.get("headers") or None,
    )
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    # Strip provider's `model_prefix` (e.g. "opencode/") so the HTTP endpoint
    # receives the bare model id even when the caller passed the prefixed form.
    api_model = resolve_model(provider, model)
    resp = client.chat.completions.create(
        model=api_model,
        messages=messages,
        temperature=temperature,
        max_tokens=_KIND_MAX_TOKENS.get(kind, 2048),
    )
    return resp.choices[0].message.content or ""


def _llm_call_anthropic(
    prompt: str,
    system: str,
    *,
    model: str,
    kind: str,
    temperature: float = 0.0,
) -> str:
    """Anthropic SDK — preserved separately because the request shape differs."""
    try:
        import anthropic
    except ImportError as e:
        raise ImportError("LLM call needs `anthropic`. Install: pip install anthropic") from e
    client = anthropic.Anthropic()
    kwargs: Dict[str, Any] = dict(
        model=model,
        max_tokens=_KIND_MAX_TOKENS.get(kind, 2048),
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system
    resp = client.messages.create(**kwargs)
    return "".join(getattr(b, "text", "") for b in resp.content)


def _make_provider_callable(provider_name: str) -> Callable:
    """Build the (prompt, system, *, model, kind) callable for a provider.

    The returned callable knows its provider implicitly so the existing
    _PROVIDERS[provider] = (callable, default_model) shape survives.
    """
    if provider_name == "anthropic":
        return _llm_call_anthropic

    def _call(prompt: str, system: str, *, model: str, kind: str, **_extra) -> str:
        return _llm_call_via_openai_sdk(
            prompt, system, model=model, kind=kind, provider=provider_name,
        )
    _call.__name__ = f"_llm_call_{provider_name.replace('-', '_')}"
    return _call


_PROVIDERS: Dict[str, Tuple[Callable, str]] = {
    name: (_make_provider_callable(name), cfg["default_model"])
    for name, cfg in PROVIDER_CONFIGS.items()
}


# ---------------------------------------------------------------------------
# Catalog rendering — unchanged from before, just lives here for cohesion
# ---------------------------------------------------------------------------

def _render_catalog(registry=None) -> str:
    """Markdown rendering of registered neuros for LLM system prompts."""
    reg = registry or default_registry
    lines = ["# Available NeuroLang neuros\n"]
    if not list(reg):
        lines.append("(no neuros registered)")
        return "\n".join(lines)
    by_kind: Dict[str, list] = {}
    for n in reg:
        by_kind.setdefault(n.kind, []).append(n)
    for kind in sorted(by_kind):
        lines.append(f"## {kind}\n")
        for n in sorted(by_kind[kind], key=lambda x: x.name):
            short = n.name.split(".")[-1]
            eff = ", ".join(sorted(e.value for e in n.effects))
            desc = (n.description or "").splitlines()[0] if n.description else ""
            lines.append(f"- **{short}** (`{n.name}`)  effects=[{eff}]")
            if desc:
                lines.append(f"  > {desc}")
        lines.append("")
    return "\n".join(lines)
