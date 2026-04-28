# Multi-provider LLM registry — Design Spec

**Status:** Drafted 2026-04-27. User-approved scope.

**Goal:** Replace NeuroLang's tiny 2-entry `_PROVIDERS` dict with a full multi-provider registry mirroring `/home/ubuntu/neurocomputer/neurocomputer/core/llm_registry.py`. Switch project default from `openai`/`gpt-4o-mini` to `opencode-zen`/`opencode/minimax-m2.5-free` so REPL and CLI work out-of-the-box on the user's existing OpenCode CLI auth (no `OPENAI_API_KEY` required).

Also fixes a known banner-counter bug in `repl.py` while in the area.

---

## 1. Locked design decisions

| # | Decision | Choice |
|---|---|---|
| 1 | Pattern source | **Mirror neurocomputer's `llm_registry.py`** verbatim (PROVIDER_CONFIGS + get_api_key + resolve_model + DEFAULT_PROVIDER env). Same field names, same auth-fallback mechanism. |
| 2 | Default provider | `opencode-zen` (env override via `DEFAULT_LLM_PROVIDER`) |
| 3 | Default model | `opencode/minimax-m2.5-free` |
| 4 | Provider list (v1) | `opencode-zen`, `openrouter`, `openai`, `anthropic`, `ollama` |
| 5 | Auth fallback | OpenCode Zen reads `~/.local/share/opencode/auth.json` if `OPENCODE_API_KEY` env not set (matches neurocomputer behaviour). |
| 6 | Anthropic SDK preservation | Keep dedicated `_llm_call_anthropic` (uses `anthropic` package, different request shape). All others share `_llm_call_via_openai_sdk` with provider-specific `base_url`. |
| 7 | Caller API | Keep existing `model=<provider_key>` kwarg semantics (despite the misleading name). `model=None` resolves to `DEFAULT_PROVIDER`. Existing `model="openai"` callers keep working. |
| 8 | Banner bug | Fix `_STDLIB_NAME_PREFIXES` to match `neurolang.stdlib.<x>` paths (current heuristic always sees first segment `"neurolang"` → counts 0 stdlib). |

---

## 2. Architecture

```
neurolang/_providers.py     [REWRITE]  — multi-provider registry mirroring neurocomputer
neurolang/compile.py        [MODIFY]   — model="openai" → model=None default
neurolang/propose.py        [MODIFY]   — model="openai" → model=None default
neurolang/cli.py            [MODIFY]   — subparsers: drop fixed choices=["openai","anthropic"]; default to None
neurolang/repl.py           [MODIFY]   — fix banner stdlib count; STDLIB_NAME_PREFIXES check
neurolang/stdlib/reason.py  [MODIFY]   — same default flip
neurolang/stdlib/model.py   [MODIFY]   — match new default routing in `llm.openai`/`.anthropic` callers (no shape change)
tests/test_compile.py       [MODIFY]   — fake_llm_*: still work since they're injected via llm_fn=, not _PROVIDERS
tests/test_propose.py       [MODIFY]   — _mk_llm fakes still work via llm_fn=
tests/test_cli.py           [MODIFY]   — smart provider patches `_PROVIDERS["opencode-zen"]` (or DEFAULT)
tests/test_repl.py          [MODIFY]   — same; banner test asserts non-zero stdlib count
tests/stdlib/test_reason.py [NO CHANGE] — uses monkeypatch on llm.openai/anthropic directly
```

Provider configs match neurocomputer's structure exactly. Single shared `_llm_call_via_openai_sdk` does the openai-SDK heavy lifting for opencode-zen / openrouter / openai / ollama; anthropic stays separate.

---

## 3. Component contracts

### 3.1 `neurolang/_providers.py`

```python
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
        "display_name": "OpenCode Zen",
        "env_key": "OPENCODE_API_KEY",
        "base_url": "https://opencode.ai/zen/v1",
        "default_model": "opencode/minimax-m2.5-free",
        "model_prefix": "opencode/",
        "headers": {},
        "aliases": {},
        "models": [
            "opencode/minimax-m2.5",
            "opencode/minimax-m2.5-free",
            "opencode/claude-sonnet-4-6",
            "opencode/claude-haiku-4-5",
            "opencode/claude-opus-4-7",
            "opencode/gemini-3-flash",
            "opencode/gemini-3.1-pro",
            "opencode/gpt-5.4",
            "opencode/gpt-5.4-mini",
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

PROVIDER_KINDS = ("compile", "decompile", "plan")


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
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=2048,
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
        max_tokens=2048,
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
```

### 3.2 Caller updates

**`compile.py:compile_source`:**
```python
def compile_source(
    prompt: str,
    *,
    model: Optional[str] = None,           # ← was "openai"
    output: str = "flow",
    use_cache: bool = True,
    cache: Optional[CompilerCache] = None,
    llm_fn: Optional[Callable[..., str]] = None,
    registry=None,
) -> Any:
    from ._providers import DEFAULT_PROVIDER, _PROVIDERS, normalize_provider
    provider = normalize_provider(model)
    ...
    if llm_fn is not None:
        raw = llm_fn(prompt, system, model=provider, kind="compile")
    else:
        if provider not in _PROVIDERS:
            raise ValueError(...)
        fn, default_model_name = _PROVIDERS[provider]
        raw = fn(prompt, system, model=default_model_name, kind="compile")
```

Same shape applies to `decompile_summary` and `propose_plan._get_or_call_llm`.

**`stdlib/reason.py`:**
```python
def brainstorm(topic: str, *, n: int = 5, model: Optional[str] = None) -> str:
    from .._providers import DEFAULT_PROVIDER
    effective = (model or DEFAULT_PROVIDER).lower()
    from .model import llm
    ...
    if effective == "anthropic":
        return llm.anthropic(prompt)
    # All openai-SDK-compatible providers route through llm.openai for now
    # (llm.openai uses openai SDK with base_url from PROVIDER_CONFIGS lookup).
    return llm.openai(prompt)
```

Wait — `llm.openai` in `stdlib/model.py` currently hardcodes the OpenAI SDK. Need to update it to honor provider routing too.

**`stdlib/model.py:llm.openai`** becomes:
```python
@neuro(...)
def openai(prompt: str, *, model: Optional[str] = None, system: Optional[str] = None,
           temperature: float = 0.0, max_tokens: int = 1024,
           provider: Optional[str] = None) -> str:
    """Call any OpenAI-SDK-compatible provider. Defaults to DEFAULT_PROVIDER."""
    from .._providers import (
        DEFAULT_PROVIDER, PROVIDER_CONFIGS, get_api_key, resolve_model
    )
    p = (provider or DEFAULT_PROVIDER).lower()
    cfg = PROVIDER_CONFIGS.get(p)
    if cfg is None:
        raise ValueError(f"Unknown provider {p!r}")
    oai = _require("openai")
    client = oai.OpenAI(
        api_key=get_api_key(p) or "missing-key",
        base_url=cfg.get("base_url"),
        default_headers=cfg.get("headers") or None,
    )
    resolved = resolve_model(p, model)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=resolved, messages=messages,
        temperature=temperature, max_tokens=max_tokens,
    )
    return resp.choices[0].message.content or ""
```

(Name stays `openai` for back-compat; semantically it's now "any openai-SDK-compatible provider, honoring DEFAULT_PROVIDER".)

**`cli.py` subparsers:**
```python
pc.add_argument("--model", default=None, help="Provider key (e.g., opencode-zen, openai, anthropic, ollama). Defaults to $DEFAULT_LLM_PROVIDER.")
```
Drop `choices=["openai", "anthropic"]` — too restrictive now.

### 3.3 `repl.py` banner fix

Current:
```python
_STDLIB_NAME_PREFIXES = frozenset({"web", "reason", "model", "voice", "memory"})
...
stdlib_count = sum(
    1 for n in default_registry
    if n.name.split(".", 1)[0] in _STDLIB_NAME_PREFIXES
)
```

Fix:
```python
# Stdlib neuros are registered with names like "neurolang.stdlib.web.search"
# — match on the third dotted segment.
def _is_stdlib_neuro(name: str) -> bool:
    parts = name.split(".")
    return len(parts) >= 3 and parts[0] == "neurolang" and parts[1] == "stdlib"
...
stdlib_count = sum(1 for n in default_registry if _is_stdlib_neuro(n.name))
```

Add a regression test: `test_banner_counts_actual_stdlib`.

### 3.4 Test updates

**`tests/test_cli.py`:** the smart-provider fake currently patches `_providers._PROVIDERS["openai"]`. Change to patch `_providers._PROVIDERS[DEFAULT_PROVIDER]` (i.e., `"opencode-zen"`) AND keep `"openai"` patched for test_compile.py-source-routing safety.

**`tests/test_repl.py`:** banner-counts test needs to assert `stdlib_count > 0` (with the actual fixture importing stdlib). Existing `test_namespace_includes_stdlib_namespaces` already imports stdlib; the banner test in this file just needs to verify the count is non-zero.

**`tests/test_compile.py`, `tests/test_propose.py`:** their fakes are injected via `llm_fn=` so they bypass `_PROVIDERS` entirely. No update needed.

**`tests/stdlib/test_reason.py`:** monkeypatches `llm.openai`/`.anthropic` directly. With the model.py rewrite, `llm.openai` still accepts the same call signature; tests stay green. May need a small tweak if the kwarg signature changes (will verify in implementation).

---

## 4. Data flow

```
User: neurolang repl
  ↓
$DEFAULT_LLM_PROVIDER (or "opencode-zen") → DEFAULT_PROVIDER constant
  ↓
:compile "prompt"
  → compile_source(prompt, model=None)
  → provider = normalize_provider(None) = "opencode-zen"
  → fn, default_model = _PROVIDERS["opencode-zen"]  # default_model = "opencode/minimax-m2.5-free"
  → fn(prompt, system, model="opencode/minimax-m2.5-free", kind="compile")
    → _llm_call_via_openai_sdk(provider="opencode-zen", model="opencode/minimax-m2.5-free", ...)
    → resolve_model strips "opencode/" prefix → "minimax-m2.5-free"
    → openai.OpenAI(base_url="https://opencode.ai/zen/v1", api_key=<from env or auth.json>)
    → client.chat.completions.create(model="minimax-m2.5-free", ...)
```

---

## 5. Error handling

- **No API key (env unset, auth.json missing)**: `_llm_call_via_openai_sdk` passes `"missing-key"` to the SDK; the API call returns 401; openai raises `AuthenticationError`. Caller (`compile_source`/`propose_plan`) catches via existing try/except → user sees `[compile error] AuthenticationError: ...` in REPL.
- **Unknown provider key**: `normalize_provider(strict=True)` raises `ValueError`. CLI surfaces it.
- **Ollama not running**: `openai.OpenAI(base_url="http://localhost:11434/v1")` connection refused → openai SDK raises `APIConnectionError` → caught upstream.
- **Banner failure modes preserved**: existing `try/except` patterns in `repl.py` unchanged.

---

## 6. Out of scope

- Per-call provider override at REPL meta-command level (`:compile --model=ollama "..."`) — defer; users can `export DEFAULT_LLM_PROVIDER=ollama` or call `compile_source(..., model="ollama")` from Python.
- A `:providers` meta-command listing available providers + auth status — defer; `python -c "from neurolang._providers import get_provider_catalog; ..."` works.
- Per-neuro budget recalibration based on the new default model's pricing — defer.

---

## 7. Estimated effort

~2 hours total: ~45 min for `_providers.py` rewrite, ~30 min cascading the default flip across callers, ~15 min for repl.py banner fix + regression test, ~30 min for test updates + smoke runs.
