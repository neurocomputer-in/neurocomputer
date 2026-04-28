# `reason.*` stdlib expansion — Design Spec

**Status:** Drafted 2026-04-27. Pending user review, then writing-plans.

**Goal:** Add two new leaf neuros to `neurolang/stdlib/reason.py` — `reason.brainstorm` (divergent ideation) and `reason.deep_research` (multi-perspective synthesis) — extending the catalog so `propose_plan` can offer richer compositions when an NL prompt mentions research/ideation/exploration.

The killer demo:

```
$ neurolang repl
>>> :compile "research the impact of microplastics on marine ecosystems"
[planner returns: flow = reason.deep_research]
Bound to `flow` — run via flow.run(...)
>>> flow.run("research the impact of microplastics on marine ecosystems")
"Microplastics affect marine ecosystems through three primary pathways:
  ingestion-induced toxicity, ... [synthesized brief] ...
  Caveats: emerging-research areas would benefit from fresh peer-reviewed sources."
```

---

## 1. Locked design decisions (from brainstorming)

| # | Decision | Choice |
|---|---|---|
| 1 | `reason.brainstorm` output type | **`str`** — newline-delimited bullets. Matches existing `reason.summarize`/`reason.classify` pattern. Caller can `.split("\n")` if list semantics needed. |
| 2 | `reason.deep_research` shape (the one real fork) | **(b) Deliberate-reasoning single-LLM call** — one prompt scaffolded with sub-question identification + per-question synthesis + "Caveats" footer. NOT (a) naive single-LLM, NOT (c) composite-with-web-grounding. (c) deferred to its own bundle once usage patterns crystallize. |
| 3 | Test mocking surface | Tests patch `neurolang.stdlib.model.llm.openai` (and `.anthropic`) directly via `monkeypatch.setattr`. This sits below the `_PROVIDERS` dispatch and avoids requiring the smart-provider kind-based fake. |
| 4 | New tests directory | `tests/stdlib/test_reason.py` (creating `tests/stdlib/` for future per-stdlib-module test files). Pytest auto-discovers nested test dirs; no conftest needed. |

---

## 2. Architecture

One file modified + one new test file.

```
neurolang/stdlib/reason.py    [MODIFY]  — add `brainstorm` and `deep_research` @neuro fns
tests/stdlib/test_reason.py    [NEW]    — 9 tests covering both, fully offline
```

`tests/stdlib/` doesn't exist yet — this commit creates it.

Module boundaries:
- `reason.py` keeps its single responsibility: leaf reasoning neuros backed by LLM. The two new fns follow the exact pattern of `summarize`/`classify`.
- Tests use `monkeypatch.setattr` on `neurolang.stdlib.model.llm.openai` to inject a recording fake. No new test infrastructure.

---

## 3. Component contracts

### 3.1 `reason.brainstorm`

```python
@neuro(
    effect="llm",
    kind="skill.reason",
    name="neurolang.stdlib.reason.brainstorm",
    budget=Budget(latency_ms=4000, cost_usd=0.008),
)
def brainstorm(topic: str, *, n: int = 5, model: str = "openai") -> str:
    """Generate `n` divergent angles / approaches / ideas for the given topic.

    Returns a newline-delimited bulleted list (one bullet per idea).
    Caller can `.split("\n")` for list semantics.
    """
    from .model import llm
    prompt = (
        f"Brainstorm {n} distinct, non-overlapping angles for the following:\n\n"
        f"{topic}\n\n"
        f"Output exactly {n} bullet lines, each starting with `- `. "
        f"Each bullet should be a complete thought, 1-2 sentences. "
        f"Cover diverse perspectives — don't cluster on one approach."
    )
    if model == "openai":
        return llm.openai(prompt)
    if model == "anthropic":
        return llm.anthropic(prompt)
    raise ValueError(f"Unknown model: {model}")
```

**Why this shape:**
- Single positional arg + kwargs matches `summarize`/`classify` ergonomics.
- Returning `str` keeps the type signature flat across all `reason.*` fns; no special-cased iterables.
- `n=5` default is empirically a "sweet spot" for divergent-thinking prompts (more becomes redundant, fewer is too narrow). Configurable for power users.
- Prompt explicitly demands diverse perspectives — counters the LLM's tendency to cluster around one obvious framing.

### 3.2 `reason.deep_research`

```python
@neuro(
    effect="llm",
    kind="skill.reason",
    name="neurolang.stdlib.reason.deep_research",
    budget=Budget(latency_ms=8000, cost_usd=0.02),
)
def deep_research(question: str, *, depth: str = "standard", model: str = "openai") -> str:
    """Multi-perspective research synthesis on `question`.

    `depth`: "standard" (~500 words) or "deep" (~1500 words).
    Returns a synthesized brief in plain prose. Limited to the LLM's
    parametric knowledge — for fresh-web-grounded research, compose
    with `web.search` / `web.scrape` (Phase 2 will ship a composite
    `reason.deep_research_grounded` for that).
    """
    from .model import llm
    target_words = 500 if depth == "standard" else 1500
    prompt = (
        f"Research and synthesize a brief on:\n\n{question}\n\n"
        f"Approach:\n"
        f"  1. Identify 3-5 key sub-questions implicit in the request.\n"
        f"  2. For each, summarize what is known (be explicit when uncertain).\n"
        f"  3. Synthesize a coherent brief covering all sub-questions, ~{target_words} words.\n"
        f"  4. End with a 'Caveats' line noting what would benefit from fresh sources.\n\n"
        f"Output the final synthesis only — no meta-commentary about your process."
    )
    if model == "openai":
        return llm.openai(prompt)
    if model == "anthropic":
        return llm.anthropic(prompt)
    raise ValueError(f"Unknown model: {model}")
```

**Why this shape:**
- Same leaf pattern as `summarize`/`classify`/`brainstorm` — predictable and trivial to test.
- Two-mode `depth` covers the common "quick brief vs. detailed dive" UX without exploding the API surface.
- The scaffolded prompt structurally forces the LLM to do the work that makes "research" different from "summarize" — sub-question identification + per-question coverage + synthesis. Single call, but rigor higher than naive.
- `Caveats` footer sets honest expectations: parametric-only research has limits. The wording does NOT block the LLM from producing useful output; just flags what's brittle.
- `Budget(cost_usd=0.02)` reflects ~2x summarize cost since output is longer. Conservative enough that planner cost-rollups stay realistic.

### 3.3 Tests (`tests/stdlib/test_reason.py`)

```python
"""Tests for the LLM-backed reason.* stdlib neuros (brainstorm + deep_research).

Mocks `neurolang.stdlib.model.llm.openai` (and `.anthropic`) directly so the
tests run fully offline and don't depend on the kind-dispatch _PROVIDERS
infrastructure used by compile_source / propose_plan tests.
"""
from __future__ import annotations

import pytest

from neurolang.stdlib import reason
from neurolang.stdlib import model as model_mod


@pytest.fixture
def captured_openai_calls(monkeypatch):
    """Record every `llm.openai(prompt, **kwargs)` invocation; return canned response."""
    captured: list = []
    def fake(prompt, **kwargs):
        captured.append({"prompt": prompt, "kwargs": kwargs})
        return "FAKE_LLM_RESPONSE"
    monkeypatch.setattr(model_mod.llm, "openai", fake)
    return captured


@pytest.fixture
def captured_anthropic_calls(monkeypatch):
    """Same as above but for the anthropic backend."""
    captured: list = []
    def fake(prompt, **kwargs):
        captured.append({"prompt": prompt, "kwargs": kwargs})
        return "FAKE_ANTHROPIC_RESPONSE"
    monkeypatch.setattr(model_mod.llm, "anthropic", fake)
    return captured


# ---- reason.brainstorm tests --------------------------------------------------

def test_brainstorm_calls_openai_with_topic_and_n(captured_openai_calls):
    out = reason.brainstorm("ways to learn category theory", n=3)
    assert out == "FAKE_LLM_RESPONSE"
    assert len(captured_openai_calls) == 1
    prompt = captured_openai_calls[0]["prompt"]
    assert "ways to learn category theory" in prompt
    assert "3" in prompt  # n appears in the prompt


def test_brainstorm_default_n_is_5(captured_openai_calls):
    reason.brainstorm("any topic")
    prompt = captured_openai_calls[0]["prompt"]
    # Two places the n=5 default appears: "Brainstorm 5 distinct..." and
    # "Output exactly 5 bullet lines..."
    assert prompt.count("5") >= 2


def test_brainstorm_anthropic_routing(captured_anthropic_calls):
    out = reason.brainstorm("topic", model="anthropic")
    assert out == "FAKE_ANTHROPIC_RESPONSE"
    assert len(captured_anthropic_calls) == 1


def test_brainstorm_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        reason.brainstorm("topic", model="grok")


# ---- reason.deep_research tests ----------------------------------------------

def test_deep_research_calls_openai_with_question(captured_openai_calls):
    out = reason.deep_research("impact of microplastics on marine life")
    assert out == "FAKE_LLM_RESPONSE"
    prompt = captured_openai_calls[0]["prompt"]
    assert "impact of microplastics on marine life" in prompt
    # The scaffolded prompt structure should be present
    assert "sub-questions" in prompt
    assert "Caveats" in prompt


def test_deep_research_default_depth_is_standard(captured_openai_calls):
    reason.deep_research("any question")
    prompt = captured_openai_calls[0]["prompt"]
    assert "500" in prompt  # standard target word count
    assert "1500" not in prompt


def test_deep_research_deep_depth_uses_higher_target(captured_openai_calls):
    reason.deep_research("any question", depth="deep")
    prompt = captured_openai_calls[0]["prompt"]
    assert "1500" in prompt
    assert "500" not in prompt or prompt.count("500") < prompt.count("1500")


def test_deep_research_anthropic_routing(captured_anthropic_calls):
    out = reason.deep_research("question", model="anthropic")
    assert out == "FAKE_ANTHROPIC_RESPONSE"
    assert len(captured_anthropic_calls) == 1


def test_deep_research_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        reason.deep_research("question", model="grok")
```

That's 9 tests (4 for `brainstorm` + 5 for `deep_research`) — slightly more than the design's earlier "~6" estimate because covering anthropic routing + unknown-model errors per fn doubles the count. All offline.

---

## 4. Data flow

```
User code or :compile output:
  flow = reason.brainstorm | reason.deep_research
  ↓
At runtime, .run("topic"):
  brainstorm("topic")
    → from .model import llm
    → llm.openai("Brainstorm 5 distinct...")
    → openai.OpenAI().chat.completions.create(...)  ← real HTTP in production
    → returns "- idea 1\n- idea 2\n..."
  ↓ (output threads through Sequential composition)
  deep_research("- idea 1\n- idea 2\n...")
    → from .model import llm
    → llm.openai("Research and synthesize... [ideas]")
    → returns synthesized brief
```

In tests, `monkeypatch.setattr(model_mod.llm, "openai", fake)` short-circuits the openai library call entirely. No HTTP, no API key required.

---

## 5. Error handling

Two failure modes:

**5.1 Unknown model kwarg** — `model="grok"` etc. → `ValueError(f"Unknown model: {model}")`. Same shape as existing `summarize`/`classify`. Tests verify per fn.

**5.2 Underlying LLM call fails** — `openai`/`anthropic` package raises `ImportError` (not installed) or HTTP error. Propagates. Caller decides how to handle. NOT wrapped in try/except — keeps the error path debuggable. Existing pattern.

No new error categories introduced.

---

## 6. Out of scope (explicit)

- **Composite `deep_research` with real web grounding** (option (c) from brainstorming) — Phase 2 bundle. Will likely ship as `reason.deep_research_grounded` so both forms can coexist. Brief mention in `deep_research`'s docstring already points at this.
- **`brainstorm` returning `list[str]`** — defer; prompt and post-processing make `.split("\n")` easy enough.
- **Streaming output** — defer; matches existing reason.* (full-string return).
- **Per-bullet length config** for brainstorm — defer; prompt asks for "1-2 sentences".
- **Custom prompts via kwarg** — defer; would balloon the API and dilute the "ergonomic stdlib" promise.
- **Citations / source attribution** in `deep_research` — N/A for parametric-only mode; will be central to the future composite version.

---

## 7. Estimated effort

~1.5-2 hours total:

- Add the 2 `@neuro` fns to `reason.py`: 30 min
- Create `tests/stdlib/test_reason.py` with 9 tests: 45 min
- STATUS.md + CHANGELOG.md update + push: 15 min

After implementation:
- Confirm `python -c "from neurolang.stdlib import reason; print(reason.brainstorm.name, reason.deep_research.name)"` works
- Confirm `neurolang catalog` shows the new entries
- Update STATUS.md "Just shipped" + pick the next-up bundle from the stdlib list (`agent.delegate` next per the recommended order)
