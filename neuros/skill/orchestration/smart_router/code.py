"""
Smart Router — decides reply vs skill invocation using native tool calling.
Uses the context assembler for optimized token usage.
"""
import json

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "reply_directly",
            "description": "Reply to the user directly. Use for greetings, knowledge questions, conversation, advice, and anything answerable without performing an action.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {
                        "type": "string",
                        "description": "The response text to send to the user"
                    }
                },
                "required": ["reply"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_skill",
            "description": "Invoke a neuro skill to perform an action. Use only when the user explicitly requests a concrete action like generating code, writing files, or controlling the system.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "The exact skill name from the available skills list"
                    },
                    "params": {
                        "type": "object",
                        "description": "Parameters required by the skill"
                    }
                },
                "required": ["skill"]
            }
        }
    },
]


async def run(state, **kwargs):
    llm = state["__llm"]
    system_prompt = state.get("__prompt", "")

    # Use context from assembler if available, fall back to kwargs
    history = kwargs.get("history", state.get("__router_history", ""))
    text = kwargs.get("text", "")
    skills = kwargs.get("skills", state.get("__router_skills", ""))

    final_system = (
        system_prompt
        .replace("{{skills}}", str(skills))
        .replace("{{history}}", str(history))
        .replace("{{text}}", str(text))
    )

    messages = [
        {"role": "system", "content": final_system},
        {"role": "user", "content": text},
    ]

    try:
        result = await llm.agenerate_with_tools(messages, TOOLS)
    except Exception as e:
        err = str(e)
        print(f"[SmartRouter] LLM error: {e}")
        if "429" in err or "rate" in err.lower():
            provider = getattr(llm, "provider", "configured provider")
            model = getattr(llm, "model", "configured model")
            return {
                "action": "reply",
                "reply": f"Rate limit reached on `{provider}` / `{model}`. Please retry in a moment or switch provider with /provider.",
            }
        return {"action": "reply", "reply": f"Something went wrong: {err[:120]}"}

    # Parse tool call
    if "tool_calls" in result and result["tool_calls"]:
        call = result["tool_calls"][0]
        fn_name = call["name"]
        args = call.get("arguments", {})

        if fn_name == "reply_directly":
            return {
                "action": "reply",
                "reply": args.get("reply", "I'm not sure how to respond."),
                "skill": None,
                "params": {},
            }

        if fn_name == "invoke_skill":
            return {
                "action": "skill",
                "reply": None,
                "skill": args.get("skill", ""),
                "params": args.get("params", {}),
            }

    # Fallback: plain text response
    content = result.get("content", "")
    if content:
        return {"action": "reply", "reply": content, "skill": None, "params": {}}

    return {"action": "reply", "reply": "I'm not sure how to respond."}
