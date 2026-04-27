from typing import Any, Dict
from neurolang import compile_source


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    prompt = kwargs.get("prompt") or state.get("__prompt") or ""
    if not prompt:
        return {"error": "nl_compile: empty prompt"}
    try:
        source = compile_source(prompt)
    except Exception as exc:
        return {"error": str(exc)}
    return {"source": source, "prompt": prompt}
