import json

async def run(state):
    """
    Build a *structured* catalogue, hand it to the LLM for a friendly
    explanation, and return {"reply": …}.
    """
    llm     = state["__llm"]              # injected by neuroFactory
    system  = state["__prompt"]           # our prompt.txt, see below

    cid    = state.get("__cid")
    neuros = state["__factory"].describe(cid)

    # Instead: return raw data, let result_to_reply format it
    return {"neuros": neuros}
