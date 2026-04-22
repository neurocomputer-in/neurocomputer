"""Model-kind base classes.

A `model.llm` wraps a chat-completion provider (OpenAI / Anthropic /
Ollama / OpenRouter / OpenCode Zen) as a neuro. The concrete provider
is configured via class attributes (set from conf.json at factory
synthesis time).

The goal: make model selection swap-by-config. A neuro that needs an
LLM declares `uses: ["model_llm_openrouter"]` (or any alias) and calls
`self.model_llm_openrouter.run(state, messages=[...])`. Swapping the
provider means editing one field in one conf.json.

Internally wraps `core.base_brain.BaseBrain` for provider abstraction
(keys, base_url, headers, aliases) — no need to reimplement.

Spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/09-kind-formats.md §6
"""
import re
from core.base_neuro import BaseNeuro


_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)


def _strip_thinking(text: str):
    if not text:
        return "", None
    match = _THINK_RE.search(text)
    if not match:
        return text, None
    thinking = match.group(1).strip()
    clean = _THINK_RE.sub("", text).strip()
    return clean, (thinking or None)


class ModelLLM(BaseNeuro):
    """Chat-completion neuro.

    Class attributes (set from conf.json):
      provider       — "openrouter" | "openai" | "ollama" | "opencode-zen" | ...
      default_model  — fallback model name if caller doesn't specify
      temperature    — default sampling temperature

    Call forms (all return dicts; `run` dispatches by kwargs):
      - messages + tools  → {"tool_calls": [...]} OR {"content", "thinking"}
      - messages (no tools) → {"content", "thinking"}
      - user_msg + system_prompt → {"content", "thinking"}  (legacy convenience)
    """
    provider: str = "openrouter"
    default_model: str = ""
    temperature: float = 0.7
    scope: str = "singleton"

    def _ensure_brain(self, model=None, temperature=None):
        """Lazily build a BaseBrain for this provider. Returns None on failure."""
        from core.base_brain import BaseBrain
        cached = getattr(self, "_brain", None)
        want_model = model or self.default_model
        want_temp = temperature if temperature is not None else self.temperature

        if (cached is not None
                and cached.model == want_model
                and cached.temp == want_temp
                and cached.provider == self.provider):
            return cached

        try:
            brain = BaseBrain(want_model, want_temp, provider=self.provider)
        except Exception as e:
            self._last_error = f"BaseBrain init failed for {self.provider}/{want_model}: {e}"
            return None
        self._brain = brain
        return brain

    async def run(self, state, *,
                  messages=None,
                  user_msg=None,
                  system_prompt=None,
                  tools=None,
                  tool_choice="auto",
                  temperature=None,
                  model=None,
                  json_mode=False,
                  **_):
        brain = self._ensure_brain(model=model, temperature=temperature)
        if brain is None:
            return {"content": "", "error": getattr(self, "_last_error", "brain init failed")}

        # --- tools call
        if messages and tools:
            try:
                return await brain.agenerate_with_tools(messages, tools, tool_choice=tool_choice)
            except Exception as e:
                return {"content": "", "error": str(e)}

        # --- messages list (no tools)
        if messages:
            try:
                params = {"model": brain.model,
                          "temperature": temperature if temperature is not None else brain.temp}
                if json_mode:
                    params["response_format"] = {"type": "json_object"}
                rsp = await brain.aclient.chat.completions.create(messages=messages, **params)
                raw = rsp.choices[0].message.content or ""
                clean, thinking = _strip_thinking(raw)
                return {"content": clean, "thinking": thinking}
            except Exception as e:
                return {"content": "", "error": str(e)}

        # --- legacy user_msg + system_prompt
        if user_msg is not None:
            try:
                if json_mode:
                    text = await brain.agenerate_json(user_msg, system_prompt or "")
                else:
                    text = await brain.agenerate_text(user_msg, system_prompt or "")
                return {"content": text, "thinking": getattr(brain, "last_thinking", None)}
            except Exception as e:
                return {"content": "", "error": str(e)}

        return {"content": "", "error": "provide `messages` or `user_msg`"}


class ModelEmbedding(BaseNeuro):
    """Embedding producer. Minimal stub — v1 delegates to provider SDK."""
    provider: str = "openai"
    default_model: str = "text-embedding-3-small"
    scope: str = "singleton"

    async def run(self, state, *, text, model=None, **_):
        # Intentional stub: real implementation lands when first memory.recall
        # neuro demands it. Returns empty vector on call so the registry
        # entry exists + can be swapped later.
        return {"vector": [], "dim": 0, "stub": True}


class ModelReranker(BaseNeuro):
    """Cross-encoder reranker. Stub for registry placeholder."""
    scope: str = "singleton"

    async def run(self, state, *, query, candidates, **_):
        return {"ranked": [{"item": c, "score": 0.0} for c in candidates], "stub": True}
