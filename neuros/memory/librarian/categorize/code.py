"""memory_categorize — LLM-driven fact → category routing.

Single-fact mode: pass fact_content (+ optional fact_id); returns
{category_id, category_name, new}.

Batch mode: pass facts=[{content, id}]; returns {results: [...]} with
one entry per fact.

Taxonomy grows organically — when no existing category fits, a new
category node is created (kind='category', content=name, props.def=def).
"""
import json
import re
from core.base_neuro import BaseNeuro


_SYSTEM_PROMPT = """\
You route new facts into a taxonomy. Decide per fact: fits an existing
category, or deserves a new one?

Rules:
- Prefer existing categories when reasonable (semantic overlap, not just word match).
- Only create new when truly distinct. Max ~20 categories per level.
- new_category_name: lowercase snake_case, max 3 words.
- new_category_definition: one line, <=80 chars.

Output JSON only: {"use_existing": true, "category_name": "existing_name"} OR
{"use_existing": false, "new_category_name": "new_name",
 "new_category_definition": "short definition"}. No prose.\
"""


_JSON_BLOCK = re.compile(r"\{[\s\S]*?\}")


class MemoryCategorize(BaseNeuro):
    uses = ["memory_graph", "inference"]

    async def run(self, state, *,
                  fact_content=None,
                  fact_id=None,
                  facts=None,
                  max_categories=50,
                  **_):
        # Batch mode
        if facts:
            results = []
            for f in facts:
                r = await self._one(state, f.get("content", ""), f.get("id"))
                results.append(r)
            return {"results": results, "count": len(results)}

        # Single mode
        if fact_content is None:
            return {"error": "fact_content required (or facts=[...])"}
        r = await self._one(state, fact_content, fact_id)
        return r

    async def _one(self, state, fact_content, fact_id):
        if not fact_content:
            return {"error": "empty fact_content"}

        # 1. List existing categories
        out = await self.memory_graph.run(
            state, op="list_nodes", kind="category", limit=50
        )
        existing = out.get("items", []) if isinstance(out, dict) else []

        # 2. Ask LLM
        cat_list = "\n".join(
            f"- {c['content']}: {c.get('props',{}).get('def','')}"
            for c in existing
        ) if existing else "(none yet — the taxonomy is empty)"
        user_msg = (f"Fact: {fact_content}\n\n"
                    f"Existing categories:\n{cat_list}")
        decision = await self._decide(state, user_msg)

        # 3. Resolve category
        if decision.get("use_existing"):
            name = (decision.get("category_name") or "").strip()
            match = next((c for c in existing
                          if c["content"].strip().lower() == name.lower()), None)
            if match:
                category_id = match["id"]
                category_name = match["content"]
                new = False
            else:
                # LLM hallucinated a category; fall back to creating it.
                category_id = await self._create_category(
                    state, name or "uncategorized",
                    decision.get("definition", ""),
                )
                category_name = name or "uncategorized"
                new = True
        else:
            name = (decision.get("new_category_name") or "uncategorized").strip()
            definition = decision.get("new_category_definition", "")
            category_id = await self._create_category(state, name, definition)
            category_name = name
            new = True

        # 4. Link fact → category if fact_id provided
        if fact_id and category_id:
            await self.memory_graph.run(
                state, op="add_edge",
                nodes=[fact_id, category_id],
                roles=["fact", "category"],
                edge_type="part_of",
            )

        return {
            "category_id":   category_id,
            "category_name": category_name,
            "new":           new,
        }

    async def _decide(self, state, user_msg):
        out = await self.inference.run(
            state,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
        )
        raw = out.get("content", "") if isinstance(out, dict) else ""
        return _parse_json(raw)

    async def _create_category(self, state, name, definition):
        out = await self.memory_graph.run(
            state, op="add_node",
            kind="category",
            content=name,
            props={"def": definition},
        )
        return out.get("id") if isinstance(out, dict) else None


def _parse_json(raw: str) -> dict:
    if not raw:
        return {}
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\n?", "", s)
        s = re.sub(r"```$", "", s).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else {}
    except (json.JSONDecodeError, ValueError):
        pass
    m = _JSON_BLOCK.search(s)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else {}
        except (json.JSONDecodeError, ValueError):
            pass
    return {}
