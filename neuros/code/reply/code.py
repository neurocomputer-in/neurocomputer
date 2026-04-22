"""Code Reply — contextual response about code operations performed."""

async def run(state, *, text=None):
    llm = state["__llm"]
    system = state.get("__prompt", "")
    conv = state.get("__conv")
    user_text = text or state.get("goal", "")

    # Build conversation context
    if conv:
        from core.context import build_reply_context, ensure_history_summary
        try:
            await ensure_history_summary(conv, llm)
        except Exception:
            pass
        ctx = build_reply_context(conv)
        hist = ctx["history"]
    else:
        hist = state.get("__history", "")

    # Gather operation results from execution state
    ops = []
    written = state.get("file_path") or state.get("__written_files")
    if written:
        ops.append(f"Files written: {written if isinstance(written, str) else ', '.join(written)}")
    read_content = state.get("content") or state.get("__read_content")
    if read_content and isinstance(read_content, str):
        ops.append(f"File content:\n{read_content[:2000]}")
    result = state.get("result") or state.get("output")
    if result and isinstance(result, str):
        ops.append(f"Result:\n{result[:2000]}")
    ops_context = "\n".join(ops)

    prompt = "\n\n".join(filter(None, [
        system,
        f"Conversation:\n{hist}" if hist else None,
        f"Operations performed:\n{ops_context}" if ops_context else None,
        f"user: {user_text}",
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
