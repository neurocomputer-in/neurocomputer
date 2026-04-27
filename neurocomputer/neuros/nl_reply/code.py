from typing import Any, Dict


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    source = kwargs.get("source") or state.get("source") or ""
    rationale = kwargs.get("rationale") or state.get("rationale") or ""
    path = state.get("path") or ""

    if source and source.strip():
        try:
            from neurolang import decompile_summary
            text = decompile_summary(source)
            if path:
                text = text.rstrip() + f"\n\nSaved to: `{path}`"
        except Exception as exc:
            text = f"Flow compiled successfully. (Summary unavailable: {exc})"
            if path:
                text += f"\n\nSaved to: `{path}`"
    elif rationale:
        text = rationale
    else:
        text = "The NeuroLang planner completed but produced no output."

    return {"text": text, "reply": text}
