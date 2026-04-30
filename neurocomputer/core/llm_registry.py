import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


PROVIDER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "minimax/minimax-m2.5:free",
        "headers": {
            "HTTP-Referer": "https://neurocomputer.dev",
            "X-Title": "Neurocomputer",
        },
        "aliases": {
            "gpt-4o-mini": "minimax/minimax-m2.5:free",
            "gpt-4o": "minimax/minimax-m2.5:free",
            "gpt-4": "minimax/minimax-m2.5:free",
            "gpt-3.5-turbo": "minimax/minimax-m2.5:free",
        },
        "models": [
            "minimax/minimax-m2.5:free",
            "openai/gpt-4o-mini",
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-001",
        ],
    },
    "openai": {
        "env_key": "OPENAI_API_KEY",
        "base_url": None,
        "default_model": "gpt-4o-mini",
        "headers": {},
        "aliases": {},
        "models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1",
        ],
    },
    "ollama": {
        "env_key": "OLLAMA_API_KEY",
        "base_url": "http://localhost:11434/v1",
        "default_model": "gemma4:e4b",
        "headers": {},
        "aliases": {},
        "models": [
            "gemma4:e4b",
            "gemma4:27b",
            "qwen3:8b",
        ],
    },
    "opencode-zen": {
        # OpenCode Zen — curated gateway of coding-agent-tuned models.
        # Docs: https://opencode.ai/docs/zen/  Catalog: mastra.ai/models/providers/opencode
        # Note: the ``opencode/`` prefix is the opencode CLI's config-level
        # identifier, but the HTTP /v1/chat/completions endpoint expects the
        # bare model id. We keep the prefixed ids in ``models`` (matches the
        # opencode CLI convention and the model-picker UX) and strip the
        # prefix in ``resolve_model`` via ``model_prefix`` before each call.
        "display_name": "OpenCode Zen",
        "env_key": "OPENCODE_API_KEY",
        "base_url": "https://opencode.ai/zen/v1",
        "default_model": "opencode/gpt-5.4-nano",
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
}

DEFAULT_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "opencode-zen").strip().lower() or "opencode-zen"

# opencode CLI stores API keys at ~/.local/share/opencode/auth.json. If the
# user has already run `opencode auth login`, we can reuse that key for the
# OpenCode Zen provider so they don't have to set OPENCODE_API_KEY separately.
_OPENCODE_AUTH_PATH = Path.home() / ".local" / "share" / "opencode" / "auth.json"
# Each provider can declare an auth-file fallback. The key is the provider
# entry name inside ``auth.json`` (matches what ``opencode auth`` writes).
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
    """Resolve the API key for a provider. Checks the declared env var
    first, then falls back to the opencode CLI's auth.json for providers
    that share credentials with it."""
    cfg = PROVIDER_CONFIGS.get(provider) or {}
    env_key = cfg.get("env_key", "")
    if env_key:
        val = os.getenv(env_key, "").strip()
        if val:
            return val
    fallback_entry = _PROVIDER_AUTH_FALLBACK.get(provider)
    if fallback_entry:
        return _read_opencode_auth_key(fallback_entry)
    return ""


def normalize_provider(provider: Optional[str], strict: bool = False) -> str:
    candidate = (provider or DEFAULT_PROVIDER).strip().lower()
    if candidate not in PROVIDER_CONFIGS:
        if strict:
            raise ValueError(
                f"Unknown LLM provider '{provider}'. Available: {', '.join(sorted(PROVIDER_CONFIGS))}"
            )
        # Accept unknown providers (e.g. OpenCode Zen, MiniMax Coding Plan)
        return candidate
    return candidate


def resolve_model(provider: str, model_name: Optional[str]) -> str:
    cfg = PROVIDER_CONFIGS[provider]
    name = (model_name or "").strip()
    if not name:
        name = cfg["default_model"]
    name = cfg.get("aliases", {}).get(name, name)
    # Some gateways (OpenCode Zen) use a namespaced id at the config layer
    # (e.g. ``opencode/gpt-5-nano``) but want the bare id on the wire.
    prefix = cfg.get("model_prefix", "")
    if prefix and name.startswith(prefix):
        name = name[len(prefix):]
    return name


def get_provider_catalog() -> List[Dict[str, Any]]:
    providers = []
    for provider, cfg in PROVIDER_CONFIGS.items():
        env_key = cfg["env_key"]
        providers.append({
            "id": provider,
            "name": cfg.get("display_name") or provider.capitalize(),
            "envKey": env_key,
            "available": bool(get_api_key(provider)),
            "defaultModel": cfg["default_model"],
            "models": cfg["models"],
        })
    return providers


def get_default_llm_settings() -> Dict[str, str]:
    provider = normalize_provider(DEFAULT_PROVIDER)
    # Return the configured default_model verbatim (with any namespace prefix
    # like `opencode/...`). resolve_model() — which would strip the prefix —
    # is applied later at API-call time, the same way user-PATCHed settings
    # flow. Stripping here would diverge the persisted format between
    # default-bootstrap and explicit-pick conversations.
    cfg = PROVIDER_CONFIGS.get(provider) or {}
    model = cfg.get("default_model") or resolve_model(provider, None)
    return {
        "provider": provider,
        "model": model,
    }
