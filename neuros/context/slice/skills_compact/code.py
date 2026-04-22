"""context.slice.skills_compact — wraps core.context.build_skills_compact."""
from core.context_neuro import ContextSlice
from core.context import build_skills_compact


class ContextSliceSkillsCompact(ContextSlice):
    async def run(self, state, *, neuros=None, **_):
        if neuros is None:
            neuros = state.get("__neuros", [])
        text = build_skills_compact(neuros)
        return {"text": text, "tokens": max(1, len(text) // 4)}
