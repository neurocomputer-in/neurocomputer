"""advisor_turn — calls inference with the prepared system prompt.

Routes through the generic `inference` neuro so the concrete provider
(OpenCode Zen by default, fallback to OpenRouter/Ollama/OpenAI) is
chosen at call time. Swap providers without touching this code.

Reads:
  state["text"]          — composed system prompt (from advisor_system_prompt)
  kwarg user_question    — the question to answer

Returns:
  {"reply": str, "error": str?, "provider_used": str, "model_used": str}
"""
from core.base_neuro import BaseNeuro


class AdvisorTurn(BaseNeuro):
    uses = ["inference"]

    async def run(self, state, *, user_question, **_):
        system_text = state.get("text", "")
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user",   "content": user_question},
        ]
        out = await self.inference.run(state, messages=messages)
        if not isinstance(out, dict):
            out = {}
        reply = out.get("content", "")
        result = {
            "reply":         reply,
            "provider_used": out.get("provider_used"),
            "model_used":    out.get("model_used"),
        }
        if out.get("error"):
            result["error"] = out["error"]
        if out.get("fallback_from"):
            result["fallback_from"] = out["fallback_from"]
        return result
