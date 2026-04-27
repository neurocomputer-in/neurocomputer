import json
from typing import Any, Dict


_STANDARD_DAG = {
    "start": ["nl_propose"],
    "nodes": {
        "nl_propose": {
            "neuro": "nl_propose",
            "params": {"prompt": "var:__prompt"},
            "next": ["nl_compile"],
        },
        "nl_compile": {
            "neuro": "nl_compile",
            "params": {"prompt": "var:__prompt"},
            "next": ["nl_save"],
        },
        "nl_save": {
            "neuro": "nl_save",
            "params": {"source": "ref:nl_compile.source"},
            "next": [],
        },
    },
}


def _fallback_dag(rationale: str) -> dict:
    return {
        "start": ["nl_reply"],
        "nodes": {
            "nl_reply": {
                "neuro": "nl_reply",
                "params": {"rationale": rationale, "source": ""},
                "next": [],
            }
        },
    }


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    message = kwargs.get("message") or state.get("__prompt") or ""
    if not message or not message.strip():
        return {"dag": _fallback_dag("No message provided — please describe the flow you want to build.")}

    llm = state.get("__llm")
    system_prompt = (
        "You are the NeuroLang dev planner. Your ONLY job is to emit a JSON DAG. "
        "If the request is clear, emit the standard 3-node DAG (nl_propose→nl_compile→nl_save). "
        "If the request is unclear or missing info, emit the fallback DAG with nl_reply and a rationale. "
        "Respond with ONLY raw JSON. No markdown, no explanation.\n\n"
        "Standard DAG:\n"
        + json.dumps(_STANDARD_DAG)
        + "\n\nFallback DAG: {\"start\":[\"nl_reply\"],\"nodes\":{\"nl_reply\":{\"neuro\":\"nl_reply\","
          "\"params\":{\"rationale\":\"<missing info>\",\"source\":\"\"},\"next\":[]}}}"
    )

    if llm:
        try:
            raw = llm.generate_text(f"User request: {message}\n\nEmit the correct DAG JSON:", system_prompt)
            raw = raw.strip().strip("```json").strip("```").strip()
            dag = json.loads(raw)
            return {"dag": dag}
        except Exception:
            pass

    # Fallback: always emit the standard DAG (nl_compile handles bad prompts gracefully)
    return {"dag": _STANDARD_DAG}
