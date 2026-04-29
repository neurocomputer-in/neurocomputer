"""
Planner — converts a user goal into an execution plan.
Uses native tool/function calling for structured output.
"""
import json
from datetime import datetime, timezone
import pathlib

# ── Tool definitions ──────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Create an execution plan with one or more sequential steps",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "description": "Ordered list of steps to execute",
                        "items": {
                            "type": "object",
                            "properties": {
                                "neuro": {"type": "string", "description": "Name of the neuro/skill to run"},
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
            "description": "Reply to the user without executing any plan. Use for greetings, knowledge questions, smalltalk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string", "description": "The response text"},
                },
                "required": ["reply"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "description": "Ask the user a clarifying question when critical information is missing. Use sparingly — maximum 1 question per request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The clarifying question"},
                },
                "required": ["question"],
            },
        },
    },
]


def _steps_to_dag(steps: list[dict]) -> dict:
    """Convert a list of step dicts into a linear DAG."""
    nodes = {}
    for idx, step in enumerate(steps):
        node_id = f"n{idx}"
        next_node = f"n{idx + 1}" if idx + 1 < len(steps) else None
        nodes[node_id] = {
            "neuro": step.get("neuro", "reply"),
            "params": step.get("params", {}),
            "next": next_node,
        }
    return {"start": "n0", "nodes": nodes} if nodes else None


async def run(state, *, goal, catalogue, intent=None):
    llm = state["__llm"]
    system = state.get("__prompt", "")
    hist = state.get("__history", "")

    # ── Video keyword fast-path ───────────────────────────────────
    lower_goal = goal.lower().strip() if goal else ""
    if any(lower_goal.startswith(k) for k in ("create video", "generate video", "make video", "video about")):
        return {"plan": {
            "ok": True,
            "flow": {"start": "n0", "nodes": {"n0": {"neuro": "video_generator", "params": {"text": goal}, "next": None}}},
            "missing": [],
            "question": None,
        }}

    # ── Build messages for tool calling ───────────────────────────
    conv = state.get("__conv")
    if conv:
        from core.context import build_planner_context
        env_state = state.get("__env_state")
        ctx = build_planner_context(conv, [{"name": n, "desc": ""} for n in (catalogue or [])], env_state)
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nConversation context: {ctx['history']}"
        if ctx.get("env_context"):
            context_str += f"\nEnvironment: {ctx['env_context']}"
    else:
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nConversation history: {hist}"

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context_str},
    ]

    # ── Log prompt ────────────────────────────────────────────────
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_dir = pathlib.Path("logs") / "prompts"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"planner_prompt_{ts}.txt"
    log_file.write_text(
        (system or "") + "\n\nCONTEXT:\n" + context_str,
        encoding="utf-8",
    )

    try:
        result = await llm.agenerate_with_tools(messages, TOOLS)
    except Exception as e:
        print(f"[Planner] LLM error: {e}")
        return {"plan": {"ok": False, "flow": None, "missing": [], "question": "Sorry, could you rephrase?"}}

    # ── Log result ────────────────────────────────────────────────
    with log_file.open("a", encoding="utf-8") as f:
        f.write("\n\n### LLM OUTPUT ###\n" + json.dumps(result, indent=2) + "\n")

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

    # ── Fallback: plain text response → treat as reply ────────────
    return {"plan": {"ok": True, "flow": {"type": "reply"}, "missing": [], "question": None}}
