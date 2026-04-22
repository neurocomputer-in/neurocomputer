"""memory_store_facts — writes extracted facts to the memory graph.

Each fact becomes a node(kind='fact') with content + props.confidence.
Simple dedup: skip if an existing valid fact has identical content.
"""
from core.base_neuro import BaseNeuro


class MemoryStoreFacts(BaseNeuro):
    uses = ["memory_graph"]

    async def run(self, state, *, facts=None, **_):
        # In a sequential pipeline, facts come from the previous step's
        # output merged into state. Fall back to state.facts if not
        # passed explicitly.
        if facts is None:
            facts = state.get("facts", [])
        if not facts:
            return {"ids": [], "count": 0}

        # Pull existing fact contents for quick dedup.
        existing = await self.memory_graph.run(state, op="list_nodes",
                                               kind="fact", limit=200)
        existing_contents = {
            (n.get("content") or "").strip().lower()
            for n in (existing.get("items", []) if isinstance(existing, dict) else [])
        }

        ids = []
        for f in facts:
            content = str(f.get("content", "")).strip()
            if not content:
                continue
            if content.lower() in existing_contents:
                continue
            existing_contents.add(content.lower())
            r = await self.memory_graph.run(
                state, op="add_node",
                kind="fact",
                content=content,
                props={"confidence": float(f.get("confidence", 1.0))},
            )
            if isinstance(r, dict) and r.get("ok") and r.get("id"):
                ids.append(r["id"])

        return {"ids": ids, "count": len(ids)}
