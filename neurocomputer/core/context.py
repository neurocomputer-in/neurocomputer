"""
Context Assembler — builds purpose-specific context for each LLM call type.

Instead of dumping raw conversation history into every call, each profile
curates the optimal token set: router gets 5 compact messages, reply gets
20 full messages + a summary of older ones.
"""


def format_messages_compact(messages: list[dict], limit: int = 5) -> str:
    """Format last N messages as 'role: text' with truncation per message."""
    recent = messages[-limit:] if limit else messages
    lines = []
    for m in recent:
        text = m.get("text", "")
        if len(text) > 200:
            text = text[:200] + "..."
        lines.append(f"{m['sender']}: {text}")
    return "\n".join(lines)


def format_messages_full(messages: list[dict], limit: int = 20) -> str:
    """Format last N messages with full text."""
    recent = messages[-limit:] if limit else messages
    return "\n".join(f"{m['sender']}: {m['text']}" for m in recent)


def build_skills_compact(neuros: list[dict]) -> str:
    """One-line per skill: '- name: description'."""
    return "\n".join(f"- {n['name']}: {n['desc']}" for n in neuros)


def build_router_context(conv, neuros: list[dict]) -> dict:
    """Context for smart_router: compact recent history + skills list.

    Target: ~2K tokens. Router only needs to classify intent.
    """
    messages = conv.history()
    summary = conv.get_history_summary()

    history_parts = []
    if summary:
        history_parts.append(f"Earlier: {summary}")
    history_parts.append(format_messages_compact(messages, limit=5))

    return {
        "history": "\n".join(history_parts),
        "skills": build_skills_compact(neuros),
    }


def build_planner_context(conv, neuros: list[dict], env_state=None) -> dict:
    """Context for planners: more history + full skill catalogue + env state.

    Target: ~6K tokens. Planner needs to understand the task deeply.
    """
    messages = conv.history()
    summary = conv.get_history_summary()

    history_parts = []
    if summary:
        history_parts.append(f"Earlier in conversation: {summary}")
    history_parts.append(format_messages_full(messages, limit=10))

    env_ctx = ""
    if env_state:
        env_ctx = env_state.format_for_prompt()

    return {
        "history": "\n".join(history_parts),
        "skills": build_skills_compact(neuros),
        "env_context": env_ctx,
    }


def build_reply_context(conv, personality: str = "") -> dict:
    """Context for reply neuros: rich history with personality.

    Target: ~8K tokens. Reply needs full conversational context.
    """
    messages = conv.history()
    summary = conv.get_history_summary()

    history_parts = []
    if summary:
        history_parts.append(f"Earlier in conversation: {summary}")
    history_parts.append(format_messages_full(messages, limit=20))

    return {
        "history": "\n".join(history_parts),
        "personality": personality,
    }


async def ensure_history_summary(conv, llm) -> None:
    """Summarize old messages if conversation exceeds 20 messages.

    Summary is cached on the conversation object. Only recomputed when
    message count changes past the threshold.
    """
    messages = conv.history()
    if len(messages) <= 20:
        return

    # Check if summary is still valid
    current_summary_count = getattr(conv, '_summary_msg_count', 0)
    if current_summary_count == len(messages):
        return

    # Summarize messages 0..(len-20)
    old_messages = messages[:-20]
    text = "\n".join(f"{m['sender']}: {m['text'][:150]}" for m in old_messages[-30:])

    summary = await llm.agenerate_text(
        f"Summarize this conversation excerpt in 2-3 sentences. Focus on key topics, decisions, and any unresolved questions:\n\n{text}",
        "You are a concise summarizer. Output only the summary, no preamble."
    )
    conv.set_history_summary(summary.strip())
    conv._summary_msg_count = len(messages)
