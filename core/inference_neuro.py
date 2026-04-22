"""Inference-kind base class — uniform entry for any model call.

The `inference` neuro is the single point of entry all other neuros
use when they need a model. Inference routes to a concrete provider
neuro (model.llm.*, model.vision.*, model.audio.*, model.video.*)
based on modality + override. Graceful fallback chain when the primary
provider fails.

This keeps everything-is-a-neuro clean: callers never touch providers
directly — they say "inference this" and the router handles the rest.

Kind:  model.inference
Shape: `(state, *, messages?, user_msg?, system_prompt?, modality?, provider?,
         model?, temperature?, tools?, image?, audio?, video?) → dict`

Class attrs (settable from conf.json):
  default_provider      — primary provider neuro name for text (e.g. model_llm_opencode_zen)
  default_fallback      — fallback chain, either str or list[str]
  modality_providers    — dict mapping modality → provider-neuro-name
                          e.g. {"text": "model_llm_opencode_zen",
                                "image": "model_vision_openai"}
"""
from core.base_neuro import BaseNeuro


class Inference(BaseNeuro):
    # Provider defaults — overridable from conf.json per inference variant.
    default_provider: str = "model_llm_opencode_zen"
    default_fallback = [
        "model_llm_openrouter",
        "model_llm_ollama",
        "model_llm_openai",
    ]
    modality_providers: dict = {}   # {"image": "model_vision_openai", ...}

    scope: str = "session"

    async def run(self, state, *,
                  messages=None,
                  user_msg=None,
                  system_prompt=None,
                  modality: str = "text",
                  provider: str = None,
                  model: str = None,
                  temperature: float = None,
                  tools: list = None,
                  image=None, audio=None, video=None,
                  **extra):
        chosen = provider or self._pick_provider(modality)
        if chosen is None:
            return {
                "content": "",
                "error":  f"no provider configured for modality={modality!r}",
            }

        fallbacks = self._build_fallback_chain(chosen)

        last_error = None
        for prov_name in fallbacks:
            handle = getattr(self, prov_name, None)
            if handle is None:
                last_error = f"provider {prov_name!r} not in this inference's uses list"
                continue

            kwargs = _build_provider_kwargs(
                messages=messages,
                user_msg=user_msg,
                system_prompt=system_prompt,
                model=model,
                temperature=temperature,
                tools=tools,
                image=image, audio=audio, video=video,
                modality=modality,
                extra=extra,
            )

            try:
                out = await handle.run(state, **kwargs)
            except Exception as e:
                last_error = f"{prov_name}: {e}"
                continue

            if not isinstance(out, dict):
                out = {"content": str(out) if out is not None else ""}

            # Provider-level error → try next in chain
            if out.get("error") and not out.get("content") and not out.get("tool_calls"):
                last_error = f"{prov_name}: {out.get('error')}"
                continue

            # Success — stamp provenance + return
            out.setdefault("provider_used", prov_name)
            out.setdefault("model_used",    model or "default")
            if prov_name != chosen:
                out["fallback_from"] = chosen
            return out

        # All providers failed
        return {
            "content":      "",
            "error":        last_error or "all providers failed",
            "provider_used": chosen,
            "model_used":    model or "default",
        }

    # ── routing ─────────────────────────────────────────────────────

    def _pick_provider(self, modality: str):
        """Resolve provider neuro name for a given modality."""
        if modality in self.modality_providers:
            return self.modality_providers[modality]
        if modality == "text":
            return self.default_provider
        # Unknown modality w/ no explicit mapping → let caller see error
        return None

    def _build_fallback_chain(self, primary: str) -> list:
        """Build an ordered unique list starting with primary."""
        raw = self.default_fallback
        if isinstance(raw, str):
            raw = [raw]
        chain = [primary]
        for p in (raw or []):
            if p and p not in chain:
                chain.append(p)
        return chain


def _build_provider_kwargs(*, messages, user_msg, system_prompt, model,
                           temperature, tools, image, audio, video,
                           modality, extra):
    kw = {}
    if messages is not None:
        kw["messages"] = messages
    if user_msg is not None:
        kw["user_msg"] = user_msg
    if system_prompt is not None:
        kw["system_prompt"] = system_prompt
    if model is not None:
        kw["model"] = model
    if temperature is not None:
        kw["temperature"] = temperature
    if tools is not None:
        kw["tools"] = tools
    if image is not None:
        kw["image"] = image
    if audio is not None:
        kw["audio"] = audio
    if video is not None:
        kw["video"] = video
    # Pass through any extra kwargs the caller provided (unknown to us but
    # possibly meaningful to the provider neuro)
    for k, v in (extra or {}).items():
        if k not in kw:
            kw[k] = v
    return kw
