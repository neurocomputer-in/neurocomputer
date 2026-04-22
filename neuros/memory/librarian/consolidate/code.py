"""memory_consolidate — LLM-driven periodic taxonomy maintenance.

Lists all currently-valid categories, asks the LLM to identify
near-duplicate pairs, and either returns the suggestions (dry_run) or
applies the merges by:
  1. re-parenting every part_of edge from from_id to to_id,
  2. invalidating the from_id category (sets valid_to=now).

History is preserved via temporal validity — nothing is hard-deleted.
"""
import json
import re
from core.base_neuro import BaseNeuro


_SYSTEM_PROMPT = """\
You maintain the taxonomy of an AI assistant's memory.

Given a list of current category names (with one-line definitions),
identify near-duplicate pairs that should be merged. Near-duplicate =
semantically the same concept with slightly different phrasing.

Rules:
- Do NOT merge distinct-but-related categories. Higher bar: they must
  feel interchangeable.
- Prefer keeping the more general / canonical name.
- Max {max_merges} merges per run.
- If nothing is clearly duplicated, return {{"merges": []}}.

Output JSON only:
  {{"merges": [{{"from_name": "loser", "to_name": "winner",
                  "reason": "brief why"}}]}}
No prose.\
"""


_JSON_BLOCK = re.compile(r"\{[\s\S]*?\}")


class MemoryConsolidate(BaseNeuro):
    uses = ["memory_graph", "inference"]

    async def run(self, state, *, dry_run=True, max_merges=5, **_):
        # List categories
        listed = await self.memory_graph.run(
            state, op="list_nodes", kind="category", limit=200
        )
        cats = listed.get("items", []) if isinstance(listed, dict) else []
        if len(cats) < 2:
            return {"merges": [], "applied": 0, "dry_run": dry_run}

        cat_summary = "\n".join(
            f"- {c['content']}: {c.get('props',{}).get('def','')}"
            for c in cats
        )
        merges = await self._ask_merges(state, cat_summary, max_merges)

        # Resolve names → ids
        by_name = {c["content"].strip().lower(): c for c in cats}
        resolved = []
        for m in merges:
            from_name = (m.get("from_name") or "").strip()
            to_name = (m.get("to_name") or "").strip()
            if not from_name or not to_name or from_name == to_name:
                continue
            src = by_name.get(from_name.lower())
            dst = by_name.get(to_name.lower())
            if not src or not dst or src["id"] == dst["id"]:
                continue
            resolved.append({
                "from_id":   src["id"],
                "from_name": src["content"],
                "to_id":     dst["id"],
                "to_name":   dst["content"],
                "reason":    m.get("reason", ""),
            })
            if len(resolved) >= max_merges:
                break

        if dry_run:
            return {"merges": resolved, "applied": 0, "dry_run": True}

        # Apply
        applied = 0
        for m in resolved:
            ok = await self._apply_merge(state, m["from_id"], m["to_id"])
            if ok:
                applied += 1
        return {"merges": resolved, "applied": applied, "dry_run": False}

    async def _ask_merges(self, state, cat_summary, max_merges):
        out = await self.inference.run(
            state,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT.format(max_merges=max_merges)},
                {"role": "user",   "content": f"Current categories:\n\n{cat_summary}"},
            ],
        )
        raw = out.get("content", "") if isinstance(out, dict) else ""
        parsed = _parse_json(raw)
        return parsed.get("merges", []) if isinstance(parsed, dict) else []

    async def _apply_merge(self, state, from_id, to_id):
        """Reparent all part_of edges from from_id to to_id, then
        invalidate the from_id category."""
        try:
            # Find edges that mention from_id
            nbrs = await self.memory_graph.run(
                state, op="neighbors", node_id=from_id, edge_type="part_of", limit=500
            )
            items = nbrs.get("items", []) if isinstance(nbrs, dict) else []
            for it in items:
                edge = it.get("edge", {})
                fact_id = next((n for n in edge.get("nodes", []) if n != from_id), None)
                if not fact_id:
                    continue
                # Invalidate old edge, create new pointing at to_id
                await self.memory_graph.run(
                    state, op="invalidate_edge", edge_id=edge["id"]
                )
                await self.memory_graph.run(
                    state, op="add_edge",
                    nodes=[fact_id, to_id],
                    roles=["fact", "category"],
                    edge_type="part_of",
                )
            # Invalidate the losing category
            await self.memory_graph.run(
                state, op="invalidate_node", node_id=from_id
            )
            return True
        except Exception:
            return False


def _parse_json(raw: str):
    if not raw:
        return {}
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\n?", "", s)
        s = re.sub(r"```$", "", s).strip()
    try:
        return json.loads(s)
    except (json.JSONDecodeError, ValueError):
        pass
    m = _JSON_BLOCK.search(s)
    if m:
        try:
            return json.loads(m.group(0))
        except (json.JSONDecodeError, ValueError):
            pass
    return {}
