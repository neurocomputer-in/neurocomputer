"""Reply neuro — generates conversational responses with context awareness."""

async def run(state, *, text):
    llm = state["__llm"]
    system = state.get("__prompt", "")
    conv = state.get("__conv")

    # Build context: prefer assembled context, fall back to raw history
    if conv:
        from core.context import build_reply_context, ensure_history_summary
        try:
            await ensure_history_summary(conv, llm)
        except Exception:
            pass  # summarization failure is non-fatal
        ctx = build_reply_context(conv)
        hist = ctx["history"]
    else:
        hist = state.get("__history", "")

    prompt = "\n\n".join(filter(None, [
        system,
        f"Conversation:\n{hist}" if hist else None,
        f"user: {text}",
        "assistant:",
    ])).strip()

    stream_cb = state.get("__stream_cb")
    answer = ""

    if stream_cb:
        for chunk in llm.stream_text(prompt, ""):
            answer += chunk
            await stream_cb(chunk)
    else:
        answer = await llm.agenerate_text(prompt, "")

    return {"reply": answer, "__streamed": bool(stream_cb)}
