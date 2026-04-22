"""
Dev Planner — plans neuro development tasks (create, edit, show, save neuros).
Uses native tool/function calling for structured output.
"""
import json

# ── Tool definitions ──────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Create a dev execution plan with one or more steps using dev_* neuros",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "neuro": {"type": "string", "description": "Name of the dev neuro to run"},
                                "params": {"type": "object", "description": "Parameters for the neuro"},
                            },
                            "required": ["neuro"],
                        },
                    },
                },
                "required": ["steps"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "reply_directly",
            "description": "Reply without executing any dev plan. Use for code discussions, general questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string"},
                },
                "required": ["reply"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Ask a clarifying question. Maximum 1 per request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                },
                "required": ["question"],
            },
        },
    },
]


def _steps_to_dag(steps: list[dict]) -> dict:
    """Convert step list to linear DAG."""
    nodes = {}
    for idx, step in enumerate(steps):
        node_id = f"n{idx}"
        next_node = f"n{idx + 1}" if idx + 1 < len(steps) else None
        nodes[node_id] = {
            "neuro": step.get("neuro", "dev_reply"),
            "params": step.get("params", {}),
            "next": next_node,
        }
    return {"start": "n0", "nodes": nodes} if nodes else None


async def run(state, *, goal, catalogue, intent=None):
    llm = state["__llm"]
    system = state.get("__prompt", "")
    hist = state.get("__history", "")

    context = f"""Goal: {goal}
Available neuros: {json.dumps(catalogue)}
Conversation history: {hist}"""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context},
    ]

    try:
        result = await llm.agenerate_with_tools(messages, TOOLS)
    except Exception as e:
        return {"plan": {"ok": False, "flow": None, "missing": [], "question": "Sorry, could you rephrase?"}}

    # ── Parse tool call ───────────────────────────────────────────
    if "tool_calls" in result and result["tool_calls"]:
        call = result["tool_calls"][0]
        fn_name = call["name"]
        args = call.get("arguments", {})

        if fn_name == "create_plan":
            steps = args.get("steps", [])
            flow = _steps_to_dag(steps)
            if flow:
                return {"plan": {"ok": True, "flow": flow, "missing": [], "question": None}}
            return {"plan": {"ok": True, "flow": {"type": "reply"}, "missing": [], "question": None}}

        if fn_name == "reply_directly":
            reply_text = args.get("reply", "")
            return {"plan": {"ok": True, "flow": {"type": "reply", "text": reply_text}, "missing": [], "question": None}}

        if fn_name == "ask_clarification":
            return {"plan": {"ok": False, "flow": None, "missing": [], "question": args.get("question", "Could you clarify?")}}

    return {"plan": {"ok": True, "flow": {"type": "reply"}, "missing": [], "question": None}}
