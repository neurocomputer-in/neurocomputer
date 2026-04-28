"""Hybrid suggestion utility for "did you mean...?" hints.

Combines `difflib.get_close_matches` (Levenshtein-style edit distance) with
substring search across each neuro's name + description. Used by:
  - `compile.validate_source` strict mode (flag unknown refs)
  - `propose.propose` (suggest neuros for missing capabilities)

This is intentionally small and stdlib-only. When Phase 2 lands embedding
search, that becomes the third strategy here without changing the call site.
"""
from __future__ import annotations

import difflib
import re
from typing import Iterable


_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def _tokenize(s: str) -> set[str]:
    """Split on non-alphanum boundaries; lowercase. Used for substring match."""
    return {t.lower() for t in _TOKEN_RE.findall(s)}


def suggest_alternatives(
    unknown_name: str,
    registry: Iterable,
    *,
    top_k: int = 3,
    levenshtein_cutoff: float = 0.6,
) -> list[str]:
    """Return up to `top_k` registered neuro names that look like `unknown_name`.

    Strategy:
      1. Levenshtein-ish via `difflib.get_close_matches` over all neuro names.
      2. Substring/token match over each neuro's name + description.
      3. Combine, dedupe, return up to top_k preserving Levenshtein-first order.

    `registry` only needs to be iterable of objects with `.name` and
    (optionally) `.description` attributes.
    """
    if not unknown_name:
        return []

    neuros = list(registry)
    if not neuros:
        return []

    all_names = [n.name for n in neuros]

    # Strategy 1: Levenshtein
    lev_hits = difflib.get_close_matches(
        unknown_name, all_names, n=top_k, cutoff=levenshtein_cutoff,
    )

    # Strategy 2: substring/token match
    unknown_tokens = _tokenize(unknown_name)
    sub_hits: list[str] = []
    if unknown_tokens:
        for n in neuros:
            haystack_tokens = _tokenize(n.name) | _tokenize(getattr(n, "description", "") or "")
            if unknown_tokens & haystack_tokens:
                sub_hits.append(n.name)

    # Combine, dedupe (Levenshtein first), cap at top_k
    seen: set[str] = set()
    out: list[str] = []
    for name in (*lev_hits, *sub_hits):
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
        if len(out) >= top_k:
            break
    return out
