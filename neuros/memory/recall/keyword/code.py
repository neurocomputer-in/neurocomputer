"""memory_recall_keyword — retrieves top-K matching nodes via keyword search.

Tries the full query first; if nothing hits, tokenizes the query and
tries each word ≥4 chars, deduplicating + preserving rank order.

Output is prefixed with a human-readable header so it reads sensibly
when dropped into a prompt.composer child slot.
"""
import re
from core.base_neuro import BaseNeuro


_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


class MemoryRecallKeyword(BaseNeuro):
    uses = ["memory_graph"]

    async def run(self, state, *, query=None, kind=None, top_k=5, **_):
        if not query:
            return {"items": [], "text": "", "tokens": 0}

        # 1) full-string substring match
        out = await self.memory_graph.run(
            state, op="search", query=query, kind=kind, top_k=top_k
        )
        items = out.get("items", []) if isinstance(out, dict) else []

        # 2) fallback: per-token search
        if not items:
            seen = set()
            tokens = [t for t in _TOKEN_RE.findall(query.lower())
                      if len(t) >= 4]
            for tok in tokens:
                r = await self.memory_graph.run(
                    state, op="search", query=tok, kind=kind, top_k=top_k
                )
                for node in (r.get("items", []) if isinstance(r, dict) else []):
                    if node["id"] in seen:
                        continue
                    seen.add(node["id"])
                    items.append(node)
                    if len(items) >= top_k:
                        break
                if len(items) >= top_k:
                    break

        items = items[:top_k]
        if not items:
            return {"items": [], "text": "", "tokens": 0}

        lines = ["Relevant notes from memory:"]
        for i, node in enumerate(items, 1):
            content = (node.get("content") or "").strip()
            if content:
                lines.append(f"  {i}. {content}")
        text = "\n".join(lines)
        return {
            "items":  items,
            "text":   text,
            "tokens": max(1, len(text) // 4),
        }
