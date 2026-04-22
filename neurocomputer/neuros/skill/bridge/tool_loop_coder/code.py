"""tool_loop_coder — coder-turn that uses tool_loop with real tools.

Exposes 4 tools to the LLM:
  code_file_read       — read a file's contents
  code_file_list       — list a directory
  memory_recall_keyword — high-level recall from the memory graph
  memory_graph          — low-level graph ops (search/list/stats/neighbors)

Tool specs are inline OpenAI function schemas. The LLM decides when
and how to use them; tool_loop handles the back-and-forth.
"""
from core.base_neuro import BaseNeuro


_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "code_file_read",
            "description": "Read and return the contents of a text file from the active project.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Relative path within the project (e.g. 'core/brain.py').",
                    }
                },
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "code_file_list",
            "description": "List files in a project directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dirpath": {
                        "type": "string",
                        "description": "Relative directory (e.g. 'core' or '.' for project root).",
                    }
                },
                "required": ["dirpath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_recall_keyword",
            "description": "Search the memory graph for facts relevant to a keyword/phrase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "keyword or phrase"},
                    "top_k": {"type": "integer", "description": "max hits", "default": 5},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "memory_graph",
            "description": "Raw memory graph operations: stats, list_nodes (by kind), search, neighbors.",
            "parameters": {
                "type": "object",
                "properties": {
                    "op":    {"type": "string", "enum": ["stats", "list_nodes", "search", "neighbors"]},
                    "kind":  {"type": "string", "description": "filter by node kind (fact/category/entity)"},
                    "query": {"type": "string", "description": "for op=search"},
                    "node_id": {"type": "string", "description": "for op=neighbors"},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["op"],
            },
        },
    },
]


class ToolLoopCoder(BaseNeuro):
    uses = ["tool_loop"]

    async def run(self, state, *, user_question, **_):
        system_text = state.get("text", "")
        messages = [
            {"role": "system", "content": system_text},
            {"role": "user",   "content": user_question},
        ]
        out = await self.tool_loop.run(
            state, messages=messages, tools=_TOOLS
        )
        if not isinstance(out, dict):
            out = {}
        result = {
            "reply":           out.get("content", ""),
            "rounds":          out.get("rounds", 0),
            "tool_calls_made": out.get("tool_calls_made", []),
            "provider_used":   out.get("provider_used"),
            "model_used":      out.get("model_used"),
        }
        if out.get("error"):
            result["error"] = out["error"]
        return result
