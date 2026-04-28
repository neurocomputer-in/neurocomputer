"""Tests for the hybrid suggestion utility."""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from neurolang.suggest import suggest_alternatives


# A minimal fake registry that satisfies the duck-typed interface
# (iterable of objects with .name and .description). We don't depend on
# the real Registry here — keeps the test focused on suggest's logic.

@dataclass
class FakeNeuro:
    name: str
    description: str = ""


class FakeRegistry:
    def __init__(self, neuros: list[FakeNeuro]):
        self._neuros = neuros

    def __iter__(self):
        return iter(self._neuros)


def test_suggest_typo_returns_close_match_first():
    reg = FakeRegistry([
        FakeNeuro("web.search"),
        FakeNeuro("reason.summarize"),
        FakeNeuro("memory.store"),
    ])
    out = suggest_alternatives("web.serach", reg, top_k=3)
    assert out, "expected at least one suggestion"
    assert out[0] == "web.search"


def test_suggest_substring_match_in_description():
    reg = FakeRegistry([
        FakeNeuro("web.scrape", description="Scrape an HTML page from a URL"),
        FakeNeuro("model.llm.openai", description="Call the OpenAI Chat Completions API"),
    ])
    # Unknown that has no Levenshtein neighbor but shares 'scrape' as a token
    out = suggest_alternatives("page_scrape_helper", reg, top_k=3)
    assert "web.scrape" in out


def test_suggest_returns_empty_when_no_matches():
    reg = FakeRegistry([FakeNeuro("memory.store")])
    out = suggest_alternatives("zzzzzzzzzzzzzz", reg, top_k=3)
    assert out == []


def test_suggest_dedup_and_top_k_respected():
    reg = FakeRegistry([
        FakeNeuro("web.search", description="search the web"),
        FakeNeuro("web.scrape", description="scrape pages"),
        FakeNeuro("reason.summarize", description="summarize text"),
        FakeNeuro("memory.store", description="store a value"),
    ])
    # 'web' triggers both Levenshtein-ish + substring matches for both web.* names
    out = suggest_alternatives("web", reg, top_k=2)
    assert len(out) <= 2
    assert len(out) == len(set(out)), "results must be deduplicated"


def test_suggest_dedup_collapses_overlap():
    """Same name hit by BOTH Levenshtein AND substring strategies → 1 entry.

    Construction:
      - unknown="web.serch" → Levenshtein matches "web.search" (close typo).
      - "web.search" has description "search the web"; tokens of unknown
        ({"web","serch"}) intersect haystack tokens ({"web","search","the"})
        on "web" → substring path also emits "web.search".
      - Dedup must collapse to a single entry.
    """
    reg = FakeRegistry([
        FakeNeuro("web.search", description="search the web"),
    ])
    out = suggest_alternatives("web.serch", reg, top_k=3)
    assert out == ["web.search"]
    assert out.count("web.search") == 1
    assert len(out) == 1


class FakeNeuroNoDesc:
    """Registry item missing the optional `.description` attribute."""

    def __init__(self, name: str):
        self.name = name


def test_suggest_handles_missing_description_attribute():
    """`getattr(n, "description", "") or ""` must not raise on attr-less items."""
    reg = FakeRegistry([
        FakeNeuroNoDesc("web.scrape"),
    ])
    # Substring path is the one that reads .description; pick a name whose
    # tokens intersect "web.scrape" so we exercise that path.
    out = suggest_alternatives("page_scrape_helper", reg, top_k=3)
    assert "web.scrape" in out


def test_suggest_empty_unknown_returns_empty():
    reg = FakeRegistry([FakeNeuro("anything")])
    assert suggest_alternatives("", reg) == []
