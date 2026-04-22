"""
Code Planner — plans file/project scaffolding and code generation tasks.
Uses native tool/function calling for structured output.
"""
import json
import logging
from datetime import datetime, timezone

# ── Alias map for neuro name normalization ────────────────────────────
ALIAS = {
    "write_file":      "code_file_write",
    "project_creator": "code_project_manager",
    "mkdir":           "code_project_manager",
}

logger = logging.getLogger("code_planner")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("[CODE_PLANNER] %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.DEBUG)


# ── Tool definitions ──────────────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_plan",
            "description": "Create a code execution plan with one or more sequential steps. Use neuros from the available catalogue.",
            "parameters": {
                "type": "object",
                "properties": {
                    "steps": {
                        "type": "array",
                        "description": "Ordered list of steps to execute",
                        "items": {
                            "type": "object",
                            "properties": {
                                "neuro": {"type": "string", "description": "Name of the neuro/skill to run (must be from catalogue)"},
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
            "description": "Reply without executing any code plan. Use for greetings, questions, knowledge.",
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
            "description": "Ask a clarifying question. Maximum 1 per request — prefer action with sensible defaults.",
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
    """Convert step list to linear DAG, applying alias normalization."""
    nodes = {}
    for idx, step in enumerate(steps):
        neuro = step.get("neuro", "reply")
        neuro = ALIAS.get(neuro, neuro)
        params = step.get("params", {})

        # Normalize param keys for known neuros
        if neuro == "code_file_write":
            if "path" in params and "filepath" not in params:
                params["filepath"] = params.pop("path")
            if "filename" in params and "filepath" not in params:
                params["filepath"] = params.pop("filename")
            if "file_name" in params and "filepath" not in params:
                params["filepath"] = params.pop("file_name")

        if neuro == "code_project_manager":
            if "name" in params and "project_name" not in params:
                params["project_name"] = params.pop("name")
            if "path" in params and "project_name" not in params:
                params["project_name"] = params.pop("path")

        node_id = f"n{idx}"
        next_node = f"n{idx + 1}" if idx + 1 < len(steps) else None
        nodes[node_id] = {"neuro": neuro, "params": params, "next": next_node}

    return {"start": "n0", "nodes": nodes} if nodes else None


async def run(state, *, goal: str = None, catalogue: list = None, intent: str = None):
    llm = state["__llm"]
    system = state.get("__prompt", "")

    # ── Capability queries → neuro_list ──────────────────────────
    if goal:
        gl = goal.lower().strip()
        cap_queries = ["what can you do", "what are your neuros", "list neuros", "available neuros"]
        if any(gl.startswith(q) for q in cap_queries):
            logger.debug(f"Capability query: '{goal}'")
            dag = {"start": "n0", "nodes": {"n0": {"neuro": "neuro_list", "params": {}, "next": None}}}
            return {"plan": {"ok": True, "flow": dag, "missing": [], "question": None}}

    # ── Build messages ────────────────────────────────────────────
    conv = state.get("__conv")
    if conv:
        from core.context import build_planner_context
        env_state = state.get("__env_state")
        ctx = build_planner_context(conv, [{"name": n, "desc": ""} for n in (catalogue or [])], env_state)
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nIntent: {intent or 'not specified'}\nContext: {ctx['history']}"
    else:
        context_str = f"Goal: {goal}\nAvailable neuros: {json.dumps(catalogue)}\nIntent: {intent or 'not specified'}"

    context_str += "\n\nIMPORTANT: Output limit is 8,192 tokens. For large files (>150 lines), split into multiple code_file_write steps. Generate complete, runnable code."

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": context_str},
    ]

    try:
        result = await llm.agenerate_with_tools(messages, TOOLS)
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return {"plan": {"ok": False, "flow": None, "missing": [], "question": "Sorry, could you rephrase?"}}

    logger.debug(f"LLM result: {result}")

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

    # ── Fallback → reply ──────────────────────────────────────────
    return {"plan": {"ok": True, "flow": {"type": "reply"}, "missing": [], "question": None}}
