"""Context-kind base classes.

A `context.slice` produces one named fragment of context (history,
skills list, env snapshot, retrieved memory, …).

A `context.assembler` composes slices into a single keyed dict for a
specific LLM-call profile (router / planner / reply / executor).

All neuros satisfy `async run(state, **kw) -> dict`. The conventional
return shape for a slice is `{"text": str, "tokens": int}`. The
assembler labels each slice's text under a per-slice key.

Spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/09-kind-formats.md §4
"""
from core.base_neuro import BaseNeuro


def _rough_tokens(s: str) -> int:
    """Cheap token estimate: ~4 chars/token. Good enough for budgeting."""
    return max(1, len(s) // 4) if s else 0


class ContextSlice(BaseNeuro):
    """Produces a single named slice of context text.

    Subclass and override `run` to read from `state` (e.g. __conv,
    __env_state, __neuros_md) or from kwargs.
    """
    async def run(self, state, **kw):
        return {"text": "", "tokens": 0}


class ContextAssembler(BaseNeuro):
    """Composite: collects labeled slices into one context dict.

    `slices_spec` = list of dicts:
        [{"label": "history", "source": "context_slice_history", "params": {"limit": 5}},
         {"label": "skills",  "source": "context_slice_skills"}]

    Each source neuro name is looked up via the NeuroHandle injected by
    the factory (the assembler must declare all sources in `uses`).
    Each source is expected to return `{"text": str, "tokens": int}`.
    The assembler emits `{<label>: <text>, ..., "tokens": <total>}`.
    """
    slices_spec: list = []
    token_budget: int = 4000     # advisory; does not truncate by default

    async def run(self, state, **kw):
        result = {}
        total_tokens = 0
        for spec in self.slices_spec:
            label = spec.get("label")
            source = spec.get("source")
            params = spec.get("params", {}) or {}
            if not label or not source:
                continue
            handle = getattr(self, source, None)
            if handle is None:
                # missing dependency — label blank, no tokens
                result[label] = ""
                continue
            merged_kw = {**params, **kw}
            out = await handle.run(state, **merged_kw)
            if not isinstance(out, dict):
                out = {}
            text = out.get("text", "")
            tokens = out.get("tokens", _rough_tokens(text))
            result[label] = text
            total_tokens += tokens
        result["tokens"] = total_tokens
        result["within_budget"] = total_tokens <= self.token_budget
        return result
