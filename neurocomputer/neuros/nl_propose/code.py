from typing import Any, Dict
from neurolang import propose_plan


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    prompt = kwargs.get("prompt") or state.get("__prompt") or ""
    if not prompt:
        return {"error": "nl_propose: empty prompt"}
    try:
        plan = propose_plan(prompt)
        proposed = {
            "intents": plan.intents,
            "neuros": plan.neuros,
            "missing": plan.missing,
            "rationale": plan.rationale,
            "cost_estimate": plan.cost_estimate,
        }
    except Exception as exc:
        return {"error": str(exc)}
    return {"proposed": proposed}
