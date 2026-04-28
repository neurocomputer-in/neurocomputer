"""Reasoning stdlib neuros — summarize, classify, etc.

These are LLM-backed by default; the user can override the model arg.
"""
from __future__ import annotations

from typing import Optional

from ..neuro import neuro
from ..budget import Budget


def _call_llm(prompt: str, model: Optional[str] = None, *, kind: str = "reason") -> str:
    """Route to the configured LLM provider (default: opencode-zen)."""
    from .._providers import normalize_provider, _PROVIDERS
    p = normalize_provider(model, strict=True)
    fn, default_model = _PROVIDERS[p]
    return fn(prompt, "", model=default_model, kind=kind)


@neuro(
    effect="llm",
    kind="skill.reason",
    name="neurolang.stdlib.reason.summarize",
    budget=Budget(latency_ms=3000, cost_usd=0.005),
)
def summarize(text: str, *, max_words: int = 200, model: Optional[str] = None) -> str:
    """Summarize the given text into ≤ max_words."""
    prompt = (
        f"Summarize the following in at most {max_words} words. "
        f"Keep all factual content; drop only filler.\n\n{text}"
    )
    return _call_llm(prompt, model)


@neuro(
    effect="llm",
    kind="skill.reason",
    name="neurolang.stdlib.reason.classify",
    budget=Budget(latency_ms=2000, cost_usd=0.003),
)
def classify(text: str, *, labels: list[str], model: Optional[str] = None) -> str:
    """Classify `text` into one of `labels`. Returns the chosen label."""
    label_list = ", ".join(labels)
    prompt = (
        f"Classify the following text into exactly one of these labels: {label_list}.\n"
        f"Reply with ONLY the chosen label, no other words.\n\n{text}"
    )
    out = _call_llm(prompt, model).strip()
    # Snap to nearest label (case-insensitive)
    lower_labels = {l.lower(): l for l in labels}
    if out.lower() in lower_labels:
        return lower_labels[out.lower()]
    # Soft fallback: return first label that appears in output
    for l in labels:
        if l.lower() in out.lower():
            return l
    return out  # raw — caller decides


@neuro(
    effect="llm",
    kind="skill.reason",
    name="neurolang.stdlib.reason.brainstorm",
    budget=Budget(latency_ms=4000, cost_usd=0.008),
)
def brainstorm(topic: str, *, n: int = 5, model: Optional[str] = None) -> str:
    """Generate `n` divergent angles / approaches / ideas for the given topic.

    Returns a newline-delimited bulleted list (one bullet per idea).
    Caller can `.split("\\n")` for list semantics.
    """
    prompt = (
        f"Brainstorm {n} distinct, non-overlapping angles for the following:\n\n"
        f"{topic}\n\n"
        f"Output exactly {n} bullet lines, each starting with `- `. "
        f"Each bullet should be a complete thought, 1-2 sentences. "
        f"Cover diverse perspectives — don't cluster on one approach."
    )
    return _call_llm(prompt, model)


@neuro(
    effect="llm",
    kind="skill.reason",
    name="neurolang.stdlib.reason.deep_research",
    budget=Budget(latency_ms=8000, cost_usd=0.02),
)
def deep_research(question: str, *, depth: str = "standard", model: Optional[str] = None) -> str:
    """Multi-perspective research synthesis on `question`.

    `depth`: "standard" (~500 words) or "deep" (~1500 words).
    Returns a synthesized brief in plain prose. Limited to the LLM's
    parametric knowledge — for fresh-web-grounded research, compose
    with `web.search` / `web.scrape` (a future Phase-2 bundle will ship
    a composite `reason.deep_research_grounded` neuro).
    """
    if depth == "standard":
        target_words = 500
        llm_kind = "reason"
    elif depth == "deep":
        target_words = 1500
        llm_kind = "reason.deep"
    else:
        raise ValueError(f"Unknown depth: {depth!r} (use 'standard' or 'deep')")
    prompt = (
        f"Research and synthesize a brief on:\n\n{question}\n\n"
        f"Approach:\n"
        f"  1. Identify 3-5 key sub-questions implicit in the request.\n"
        f"  2. For each, summarize what is known (be explicit when uncertain).\n"
        f"  3. Synthesize a coherent brief covering all sub-questions, ~{target_words} words.\n"
        f"  4. End with a 'Caveats' line noting what would benefit from fresh sources.\n\n"
        f"Output the final synthesis only — no meta-commentary about your process."
    )
    return _call_llm(prompt, model, kind=llm_kind)
