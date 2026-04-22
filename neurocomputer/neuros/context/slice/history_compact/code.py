"""context.slice.history_compact — wraps core.context.format_messages_compact."""
from core.context_neuro import ContextSlice
from core.context import format_messages_compact


class ContextSliceHistoryCompact(ContextSlice):
    async def run(self, state, *, limit=5, messages=None, **_):
        if messages is None:
            conv = state.get("__conv")
            if conv is not None and hasattr(conv, "history"):
                messages = conv.history()
            else:
                messages = state.get("messages", [])
        text = format_messages_compact(messages, limit=limit)
        return {"text": text, "tokens": max(1, len(text) // 4)}
