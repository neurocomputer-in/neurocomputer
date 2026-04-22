"""coder_turn — parallel to advisor_turn but for the coder persona.

Identical mechanics: state.text (from coder_system_prompt) as system
message, user_question as user message, routed through inference.
"""
from core.base_neuro import BaseNeuro


class CoderTurn(BaseNeuro):
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
        result = {
            "reply":         out.get("content", ""),
            "provider_used": out.get("provider_used"),
            "model_used":    out.get("model_used"),
        }
        if out.get("error"):
            result["error"] = out["error"]
        if out.get("fallback_from"):
            result["fallback_from"] = out["fallback_from"]
        return result
