"""memory_extract — LLM-powered durable fact extraction.

Takes a batch of messages (or a pre-formatted exchange string), asks
the configured model.llm neuro to extract durable facts as JSON, and
returns them as a list.

Durable facts = things the agent should remember across sessions —
user preferences, decisions, domain knowledge, project state. Skips
chitchat, meta-questions, and transient conversation.
"""
import json
import re
from core.base_neuro import BaseNeuro


_SYSTEM_PROMPT = """\
You extract durable facts from conversations for an AI assistant's long-term memory.

Rules:
- Emit ONLY facts worth remembering across sessions (decisions, preferences, durable knowledge, project state).
- SKIP: small talk, pure questions, ephemeral state, anything obvious.
- Each fact must be self-contained — readable months later without the original convo.
- Max {max_facts} facts. If nothing durable was said, return {{"facts": []}}.
- Respond with ONLY valid JSON: {{"facts": [{{"content": "...", "confidence": 0.0-1.0}}]}}
- No markdown, no preamble.\
"""


_JSON_BLOCK = re.compile(r"\{[^{}]*\"facts\"[\s\S]*?\]\s*\}")


class MemoryExtract(BaseNeuro):
    uses = ["inference"]

    async def run(self, state, *, messages=None, exchange=None, max_facts=5, **_):
        text = exchange
        if text is None:
            if not messages:
                return {"facts": [], "count": 0}
            text = "\n".join(
                f"{m.get('sender','?')}: {m.get('text','')}" for m in messages
            )
        if not text.strip():
            return {"facts": [], "count": 0}

        system_prompt = _SYSTEM_PROMPT.format(max_facts=max_facts)
        out = await self.inference.run(
            state,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": f"Exchange:\n\n{text}"},
            ],
        )
        raw = out.get("content", "") if isinstance(out, dict) else ""
        facts = _parse_facts(raw, max_facts=max_facts)
        return {"facts": facts, "count": len(facts)}


def _parse_facts(raw: str, max_facts: int = 5) -> list:
    """Tolerant JSON extraction: handles code fences, prose preamble, etc."""
    if not raw:
        return []
    s = raw.strip()

    # Strip code fences
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\n?", "", s)
        s = re.sub(r"```$", "", s).strip()

    # Try raw parse
    try:
        obj = json.loads(s)
        return _coerce_facts(obj, max_facts)
    except (json.JSONDecodeError, ValueError):
        pass

    # Find a JSON-looking block
    m = _JSON_BLOCK.search(s)
    if m:
        try:
            obj = json.loads(m.group(0))
            return _coerce_facts(obj, max_facts)
        except (json.JSONDecodeError, ValueError):
            pass

    return []


def _coerce_facts(obj, max_facts: int) -> list:
    if isinstance(obj, dict):
        facts = obj.get("facts", [])
    elif isinstance(obj, list):
        facts = obj
    else:
        return []
    out = []
    for f in facts[:max_facts]:
        if isinstance(f, str):
            out.append({"content": f, "confidence": 1.0})
        elif isinstance(f, dict) and "content" in f:
            out.append({
                "content":    str(f["content"]).strip(),
                "confidence": float(f.get("confidence", 1.0)),
            })
    return [x for x in out if x["content"]]
