"""
BaseBrain — provider-aware LLM interface.

Supports OpenAI-compatible providers such as OpenRouter and OpenAI.
Handles:
  • provider/model resolution
  • <think>…</think> tag stripping
  • native tool / function calling
  • streaming with thinking separation
  • conservative in-process rate limiting
"""

import asyncio, json, os, re, time
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
from core.llm_registry import (
    PROVIDER_CONFIGS,
    get_api_key,
    get_default_llm_settings,
    normalize_provider,
    resolve_model,
)

load_dotenv()


# ── Rate limiter (singleton) ─────────────────────────────────────────
class _RateLimiter:
    def __init__(self, rpm: int = 20, rpd: int = 200):
        self.rpm = rpm
        self.rpd = rpd
        self._minute: list[float] = []
        self._day: list[float] = []

    def check(self):
        now = time.time()
        self._minute = [t for t in self._minute if now - t < 60]
        self._day    = [t for t in self._day    if now - t < 86400]
        if len(self._minute) >= self.rpm:
            raise RuntimeError(
                f"LLM rate limit: {self.rpm} requests/min exceeded. "
                "Wait a moment and retry."
            )
        if len(self._day) >= self.rpd:
            raise RuntimeError(
                f"LLM daily limit: {self.rpd} requests/day exceeded. "
                "Try again tomorrow or upgrade to a paid plan."
            )
        self._minute.append(now)
        self._day.append(now)

_rate_limiter = _RateLimiter()


# ── Think-tag parser ──────────────────────────────────────────────────
_THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

def _extract_json(text: str) -> str:
    """Best-effort extraction of a JSON object from LLM output.

    Handles: raw JSON, markdown-fenced JSON, preamble text before JSON.
    Returns the extracted JSON string, or the original text if no JSON found.
    """
    if not text:
        return text
    s = text.strip()

    # Strip markdown code fences
    if s.startswith("```json"):
        s = s[7:]
    elif s.startswith("```"):
        s = s[3:]
    if s.endswith("```"):
        s = s[:-3]
    s = s.strip()

    # Try parsing directly first
    try:
        json.loads(s)
        return s
    except (json.JSONDecodeError, ValueError):
        pass

    # Find the first { ... } block (greedy to capture nested objects)
    match = re.search(r'\{.*\}', s, re.DOTALL)
    if match:
        candidate = match.group()
        try:
            json.loads(candidate)
            return candidate
        except (json.JSONDecodeError, ValueError):
            pass

    # Last resort: return cleaned text
    return s


def _strip_thinking(text: str) -> tuple[str, str | None]:
    """Return (clean_response, thinking_content | None)."""
    if not text:
        return ("", None)
    match = _THINK_RE.search(text)
    if not match:
        return (text, None)
    thinking = match.group(1).strip()
    clean = _THINK_RE.sub("", text).strip()
    return (clean, thinking or None)


# ── BaseBrain ─────────────────────────────────────────────────────────
class BaseBrain:
    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.7,
        provider: str | None = None,
    ):
        defaults = get_default_llm_settings()
        self.provider = normalize_provider(provider or defaults["provider"])
        provider_cfg = PROVIDER_CONFIGS[self.provider]
        api_key = get_api_key(self.provider)
        if not api_key:
            raise EnvironmentError(
                f"No API key for provider '{self.provider}'. Set "
                f"{provider_cfg['env_key']} in your environment "
                f"(or run `opencode auth login` for opencode-zen)."
            )

        client_kwargs = {
            "api_key": api_key,
        }
        if provider_cfg.get("base_url"):
            client_kwargs["base_url"] = provider_cfg["base_url"]
        if provider_cfg.get("headers"):
            client_kwargs["default_headers"] = provider_cfg["headers"]

        self.client = OpenAI(**client_kwargs)
        self.aclient = AsyncOpenAI(**client_kwargs)
        self.model = resolve_model(self.provider, model_name or defaults["model"])
        self.temp  = temperature
        # stash last thinking for callers that want it
        self.last_thinking: str | None = None
        print(f"[BaseBrain] Initialized provider={self.provider} model={self.model}")

    # ── internal ──────────────────────────────────────────────────────

    def _call_sync(self, messages: list[dict], *, json_mode: bool = False) -> str:
        """Actual blocking LLM call. Strips <think> tags, returns clean content.
        Graceful degradation on API errors."""
        _rate_limiter.check()
        print(f"[BaseBrain] chat.completions.create provider={self.provider} model={self.model} json_mode={json_mode}")

        params: dict = dict(model=self.model, temperature=self.temp)
        if json_mode:
            params["response_format"] = {"type": "json_object"}

        try:
            rsp = self.client.chat.completions.create(messages=messages, **params)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                print(f"[BaseBrain] Rate limited by provider {self.provider}: {e}")
                raise RuntimeError("I'm temporarily at capacity. Please try again in a moment.") from e
            if "500" in err_str or "502" in err_str or "503" in err_str:
                print(f"[BaseBrain] Provider server error ({self.provider}): {e}")
                raise RuntimeError("The AI service is temporarily unavailable. Please try again shortly.") from e
            print(f"[BaseBrain] Unexpected API error: {e}")
            raise

        raw = rsp.choices[0].message.content or ""
        clean, thinking = _strip_thinking(raw)
        self.last_thinking = thinking
        return clean.strip()

    def _call(self, messages: list[dict], *, json_mode: bool = False) -> str:
        """Non-blocking wrapper: offloads to thread if inside a running event loop."""
        # If we're inside a running event loop, the sync HTTP call would block it.
        # But this method is called synchronously by neuros, so we can't await here.
        # The actual offloading happens in the async wrappers (agenerate_*).
        # This sync version is for neuros that don't care about blocking.
        return self._call_sync(messages, json_mode=json_mode)

    def _call_with_thinking(
        self, messages: list[dict], *, json_mode: bool = False
    ) -> tuple[str, str | None]:
        """Same as _call but returns (content, thinking)."""
        content = self._call_sync(messages, json_mode=json_mode)
        return (content, self.last_thinking)

    # ── public helpers ────────────────────────────────────────────────

    def generate_json(self, user_msg: str, system_prompt: str) -> str:
        """Generate a JSON response.

        NOTE: MiniMax M2.5's mandatory reasoning mode conflicts with
        response_format=json_object (returns None).  We enforce JSON via
        prompt instructions and extract JSON from the response.
        """
        msgs = [
            {"role": "system", "content": system_prompt + "\n\nYou MUST respond with ONLY a valid JSON object. No markdown, no explanation, no extra text."},
            {"role": "user",   "content": user_msg},
        ]
        raw = self._call(msgs, json_mode=False)
        return _extract_json(raw)

    def generate_text(self, user_msg: str, system_prompt: str) -> str:
        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ]
        return self._call(msgs, json_mode=False)

    def generate_text_with_thinking(
        self, user_msg: str, system_prompt: str
    ) -> tuple[str, str | None]:
        """Like generate_text but also returns the <think> content."""
        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ]
        return self._call_with_thinking(msgs, json_mode=False)

    # ── async methods (native async client, no thread pool) ─────────

    async def agenerate_json(self, user_msg: str, system_prompt: str) -> str:
        _rate_limiter.check()
        msgs = [
            {"role": "system", "content": system_prompt + "\n\nYou MUST respond with ONLY a valid JSON object. No markdown, no explanation, no extra text."},
            {"role": "user", "content": user_msg},
        ]
        params = dict(model=self.model, temperature=self.temp)
        rsp = await self.aclient.chat.completions.create(messages=msgs, **params)
        raw = rsp.choices[0].message.content or ""
        clean, thinking = _strip_thinking(raw)
        self.last_thinking = thinking
        return _extract_json(clean.strip())

    async def agenerate_text(self, user_msg: str, system_prompt: str) -> str:
        _rate_limiter.check()
        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ]
        params = dict(model=self.model, temperature=self.temp)
        rsp = await self.aclient.chat.completions.create(messages=msgs, **params)
        raw = rsp.choices[0].message.content or ""
        clean, thinking = _strip_thinking(raw)
        self.last_thinking = thinking
        return clean.strip()

    async def agenerate_with_tools(
        self, messages: list[dict], tools: list[dict], *, tool_choice: str = "auto"
    ) -> dict:
        _rate_limiter.check()
        print(f"[BaseBrain] async tools call provider={self.provider} model={self.model}")
        params = dict(
            model=self.model,
            temperature=self.temp,
            tools=tools,
            tool_choice=tool_choice,
        )
        try:
            rsp = await self.aclient.chat.completions.create(messages=messages, **params)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                raise RuntimeError("Rate limit reached. Try again in a moment.") from e
            if "500" in err_str or "502" in err_str or "503" in err_str:
                raise RuntimeError("AI service temporarily unavailable.") from e
            raise
        msg = rsp.choices[0].message

        if msg.tool_calls:
            calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                calls.append({"name": tc.function.name, "arguments": args})
            return {"tool_calls": calls}

        raw = msg.content or ""
        clean, thinking = _strip_thinking(raw)
        self.last_thinking = thinking
        return {"content": clean.strip(), "thinking": thinking}

    # ── streaming ─────────────────────────────────────────────────────

    def stream_text(self, user_msg: str, system_prompt: str, *, thinking_cb=None):
        """
        Yields chunks of the LLM reply, stripping <think> blocks.

        Strategy: buffer everything until </think> is found (thinking phase),
        then stream the rest normally.  If no <think> tag appears, stream
        everything immediately.

        Optional `thinking_cb(text)` is called once with the full thinking
        content after the </think> tag is detected.
        """
        _rate_limiter.check()
        print(f"[BaseBrain] stream chat.completions.create provider={self.provider} model={self.model}")

        msgs = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ]
        params = dict(model=self.model, temperature=self.temp, stream=True)
        response = self.client.chat.completions.create(messages=msgs, **params)

        buf = ""
        thinking_done = False
        in_think = False

        for chunk in response:
            delta = chunk.choices[0].delta.content
            if not delta:
                continue

            if not thinking_done:
                buf += delta
                # detect opening tag
                if not in_think and "<think>" in buf:
                    in_think = True
                    # yield anything before <think>
                    pre = buf.split("<think>", 1)[0]
                    if pre.strip():
                        yield pre
                    buf = buf.split("<think>", 1)[1]

                # detect closing tag
                if in_think and "</think>" in buf:
                    thinking_text = buf.split("</think>", 1)[0].strip()
                    remainder = buf.split("</think>", 1)[1]
                    self.last_thinking = thinking_text
                    if thinking_cb and thinking_text:
                        thinking_cb(thinking_text)
                    thinking_done = True
                    # yield any remainder after </think>
                    if remainder.strip():
                        yield remainder
                    buf = ""
                    continue

                # if we've accumulated a lot without seeing <think>, it's not coming
                if not in_think and len(buf) > 50:
                    thinking_done = True
                    yield buf
                    buf = ""
            else:
                yield delta

        # flush anything left in buffer (no think tags found at all)
        if buf.strip() and not in_think:
            yield buf

    # ── tool / function calling ───────────────────────────────────────

    def generate_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        *,
        tool_choice: str = "auto",
    ) -> dict:
        """
        Call LLM with OpenAI-compatible tool definitions.

        Returns a dict:
          {"tool_calls": [...]}          — if model chose tool(s)
          {"content": "...", "thinking": "..."}  — if model replied directly
        """
        _rate_limiter.check()
        print(f"[BaseBrain] tools chat.completions.create provider={self.provider} model={self.model}")

        params: dict = dict(
            model=self.model,
            temperature=self.temp,
            tools=tools,
            tool_choice=tool_choice,
        )
        try:
            rsp = self.client.chat.completions.create(messages=messages, **params)
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "rate" in err_str.lower():
                raise RuntimeError("I'm temporarily at capacity. Please try again in a moment.") from e
            if "500" in err_str or "502" in err_str or "503" in err_str:
                raise RuntimeError("The AI service is temporarily unavailable.") from e
            raise
        msg = rsp.choices[0].message

        # tool calls present?
        if msg.tool_calls:
            calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {}
                calls.append({
                    "name": tc.function.name,
                    "arguments": args,
                })
            return {"tool_calls": calls}

        # plain text response
        raw = msg.content or ""
        clean, thinking = _strip_thinking(raw)
        self.last_thinking = thinking
        return {"content": clean.strip(), "thinking": thinking}

    # ── planner convenience ───────────────────────────────────────────

    async def plan(self, query, *, system_prompt: str = "") -> dict:
        """
        JSON-mode call that returns a parsed Python dict.
        Used by planner neuros.
        """
        if not isinstance(query, str):
            query = json.dumps(query, ensure_ascii=False)

        raw = self.generate_json(query, system_prompt=system_prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "ok": False,
                "flow": None,
                "missing": [],
                "question": "Sorry – I produced invalid JSON. Could you rephrase?",
            }
