from typing import Any, Dict
from neurolang import decompile_summary


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    source = kwargs.get("source") or state.get("source") or ""
    if not source:
        return {"error": "nl_summary: empty source"}
    try:
        summary = decompile_summary(source)
    except Exception as exc:
        return {"error": str(exc)}
    return {"summary": summary}
