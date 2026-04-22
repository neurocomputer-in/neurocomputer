"""ToolLoop — multi-round tool-calling orchestrator.

Real agent behavior: the LLM can invoke neuros as tools mid-reply.

Pattern:
  messages, tools → inference
  if tool_calls in response:
      execute each tool via factory.run(tool_name, **args)
      append tool results to messages (OpenAI tool role format)
      loop with updated messages
  else:
      return final content

Loop bounded by `max_rounds`. State + __factory threaded through for
tools to share session scope (memory, agent id, etc).

Kind: skill.leaf (it's a callable — just a fancy one).
"""
import json
from core.base_neuro import BaseNeuro


class ToolLoop(BaseNeuro):
    uses = ["inference"]
    max_rounds: int = 5
    scope: str = "session"

    async def run(self, state, *,
                  messages,
                  tools,
                  tool_handlers: dict = None,
                  **kw):
        factory = state.get("__factory")
        handlers = dict(tool_handlers or {})   # map: tool_name → neuro_name
        messages = list(messages)              # don't mutate caller's list
        calls_log = []

        for round_num in range(self.max_rounds):
            out = await self.inference.run(
                state, messages=messages, tools=tools
            )
            if not isinstance(out, dict):
                return {"content": "", "rounds": round_num,
                        "error": "inference returned non-dict",
                        "tool_calls_made": calls_log}

            tool_calls = out.get("tool_calls") or []

            if not tool_calls:
                # Final answer — no more tools requested.
                return {
                    "content":         out.get("content", ""),
                    "thinking":        out.get("thinking"),
                    "rounds":          round_num,
                    "tool_calls_made": calls_log,
                    "provider_used":   out.get("provider_used"),
                    "model_used":      out.get("model_used"),
                }

            # Build OpenAI-compat assistant message + tool response messages.
            synth_calls = []
            for i, tc in enumerate(tool_calls):
                tc_id = tc.get("id") or f"call_{round_num}_{i}"
                synth_calls.append({
                    "id":   tc_id,
                    "type": "function",
                    "function": {
                        "name":      tc.get("name", ""),
                        "arguments": json.dumps(tc.get("arguments", {})),
                    },
                })
                calls_log.append({
                    "round": round_num,
                    "name":  tc.get("name", ""),
                    "args":  tc.get("arguments", {}),
                })

            messages.append({
                "role":       "assistant",
                "content":    None,
                "tool_calls": synth_calls,
            })

            # Execute each tool call sequentially.
            for sc, tc in zip(synth_calls, tool_calls):
                tool_name = tc.get("name", "")
                tool_args = tc.get("arguments", {}) or {}
                handler = handlers.get(tool_name, tool_name)

                if factory is None or handler not in factory.reg:
                    result = {"error": f"tool {tool_name!r} "
                              f"(handler {handler!r}) not in factory"}
                else:
                    try:
                        result = await factory.run(handler, state, **tool_args)
                    except Exception as e:
                        result = {"error": f"{type(e).__name__}: {e}"}

                messages.append({
                    "role":          "tool",
                    "tool_call_id":  sc["id"],
                    "name":          tool_name,
                    "content":       (result if isinstance(result, str)
                                      else json.dumps(result, default=str)),
                })

        # Max rounds exhausted.
        return {
            "content":         "",
            "rounds":          self.max_rounds,
            "error":           f"max_rounds ({self.max_rounds}) exhausted",
            "tool_calls_made": calls_log,
        }
