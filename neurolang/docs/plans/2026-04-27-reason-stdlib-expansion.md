# `reason.*` stdlib expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two leaf `@neuro` functions to `neurolang/stdlib/reason.py` — `reason.brainstorm` (divergent ideation) and `reason.deep_research` (multi-perspective synthesis) — extending the catalog so `propose_plan` can offer richer compositions on research/ideation prompts.

**Architecture:** Both new functions follow the existing `summarize`/`classify` pattern: leaf `@neuro` decorator, single LLM call via `model.llm.openai`/`anthropic`, return `str`. No new external dependencies. Tests sit in a new `tests/stdlib/` directory and mock the LLM at `neurolang.stdlib.model.llm.openai/anthropic` directly via `monkeypatch.setattr`.

**Tech Stack:** Python 3.10+, stdlib-only for the new code. Tests use `pytest` + `monkeypatch` fixtures. No new runtime dependencies.

**Spec:** `/home/ubuntu/neurolang/docs/specs/2026-04-27-reason-stdlib-expansion-design.md` (commit `c6e40d0`).

---

## File map

| File | Action | Purpose |
|---|---|---|
| `neurolang/stdlib/reason.py` | Modify | Append `brainstorm` and `deep_research` `@neuro` functions; no changes to existing `summarize`/`classify`. |
| `tests/stdlib/__init__.py` | Create | Empty file so pytest treats `tests/stdlib/` as a package (avoids potential conftest/import-path edge cases). |
| `tests/stdlib/test_reason.py` | Create | 9 unit tests covering both functions. Mocks LLM via `monkeypatch.setattr(model_mod.llm, "openai", fake)`. |
| `docs/STATUS.md` | Modify | Move `reason.*` bundle to "Just shipped"; update next-up to `agent.delegate`. |
| `CHANGELOG.md` | Modify | Append new `### Added` block under `[Unreleased]`. |

**Order: bottom-up so each commit lands without breaking prior tests.** Brainstorm first (small, isolated). Then deep_research (slightly more nuanced prompt). Then docs + push. Three commits total.

**Working directory for all commands:** `/home/ubuntu/neurolang/`. Run tests with `python -m pytest tests/ -q`. Baseline before starting: 112 passing.

---

## Task 1: `reason.brainstorm` + `tests/stdlib/` scaffold

**Files:**
- Modify: `neurolang/stdlib/reason.py` (append after existing `classify`)
- Create: `tests/stdlib/__init__.py`
- Create: `tests/stdlib/test_reason.py`

This task ships the `brainstorm` function plus the new `tests/stdlib/` directory infrastructure. The test file imports a `captured_anthropic_calls` fixture even though the brainstorm tests only need the OpenAI fixture — that's intentional so Task 2's `deep_research` tests can use it without modifying the file structure.

- [ ] **Step 1: Verify baseline tests pass**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/ -q
```
Expected: `112 passed in <1s`. If not, stop and investigate.

- [ ] **Step 2: Create `tests/stdlib/__init__.py`**

Run:
```
cd /home/ubuntu/neurolang && touch tests/stdlib/__init__.py
```

(Empty file. Just makes the directory a package for pytest collection clarity.)

- [ ] **Step 3: Write `tests/stdlib/test_reason.py` with 4 brainstorm tests + both fixtures**

Create `tests/stdlib/test_reason.py`:

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


# ---- Fixtures ---------------------------------------------------------------

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
    """Same as captured_openai_calls but routed through the anthropic backend."""
    captured: list = []
    def fake(prompt, **kwargs):
        captured.append({"prompt": prompt, "kwargs": kwargs})
        return "FAKE_ANTHROPIC_RESPONSE"
    monkeypatch.setattr(model_mod.llm, "anthropic", fake)
    return captured


# ---- reason.brainstorm tests ------------------------------------------------

def test_brainstorm_calls_openai_with_topic_and_n(captured_openai_calls):
    out = reason.brainstorm("ways to learn category theory", n=3)
    assert out == "FAKE_LLM_RESPONSE"
    assert len(captured_openai_calls) == 1
    prompt = captured_openai_calls[0]["prompt"]
    assert "ways to learn category theory" in prompt
    # n appears in the prompt — both as the count of bullets and the directive
    assert "3" in prompt


def test_brainstorm_default_n_is_5(captured_openai_calls):
    reason.brainstorm("any topic")
    prompt = captured_openai_calls[0]["prompt"]
    # The n=5 default appears at least twice in the prompt:
    # "Brainstorm 5 distinct..." and "Output exactly 5 bullet lines..."
    assert prompt.count("5") >= 2


def test_brainstorm_anthropic_routing(captured_anthropic_calls):
    out = reason.brainstorm("topic", model="anthropic")
    assert out == "FAKE_ANTHROPIC_RESPONSE"
    assert len(captured_anthropic_calls) == 1


def test_brainstorm_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        reason.brainstorm("topic", model="grok")
```

- [ ] **Step 4: Run the new tests — confirm they fail**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_reason.py -v
```

Expected: All 4 tests FAIL with `AttributeError: module 'neurolang.stdlib.reason' has no attribute 'brainstorm'`.

- [ ] **Step 5: Append `brainstorm` to `neurolang/stdlib/reason.py`**

Open `neurolang/stdlib/reason.py`. After the existing `classify` function (which ends with `return out  # raw — caller decides`), append a blank line and then:

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
    Caller can `.split("\\n")` for list semantics.
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

- [ ] **Step 6: Run the new tests — confirm they pass**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_reason.py -v
```
Expected: `4 passed`.

- [ ] **Step 7: Run the full suite**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/ -q
```
Expected: `116 passed` (112 + 4).

- [ ] **Step 8: Commit**

```
cd /home/ubuntu/neurolang && git add neurolang/stdlib/reason.py tests/stdlib/__init__.py tests/stdlib/test_reason.py && git commit -m "feat(stdlib): reason.brainstorm — divergent-ideation neuro

Single-LLM-call leaf neuro that prompts for n distinct, non-overlapping
angles on a topic. Returns newline-delimited bullets; caller can split
for list semantics. Matches the existing reason.summarize / .classify
pattern verbatim.

Also creates the tests/stdlib/ test directory with an empty __init__.py
plus the captured_openai_calls + captured_anthropic_calls fixtures
shared by Task 2's deep_research tests. 4 new tests, 116/116 passing."
```

---

## Task 2: `reason.deep_research`

**Files:**
- Modify: `neurolang/stdlib/reason.py` (append after `brainstorm` from Task 1)
- Modify: `tests/stdlib/test_reason.py` (append 5 new tests)

Same leaf-neuro pattern as `brainstorm`, but with a scaffolded prompt that forces the LLM to identify sub-questions, summarize each, then synthesize. Adds a `depth` kwarg toggling between ~500-word and ~1500-word output.

- [ ] **Step 1: Append the 5 new deep_research tests to `tests/stdlib/test_reason.py`**

Open `tests/stdlib/test_reason.py`. After the existing `test_brainstorm_unknown_model_raises` (the last brainstorm test), append:

```python


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
    # standard depth → ~500 words target; 1500 should NOT appear
    assert "500" in prompt
    assert "1500" not in prompt


def test_deep_research_deep_depth_uses_higher_target(captured_openai_calls):
    reason.deep_research("any question", depth="deep")
    prompt = captured_openai_calls[0]["prompt"]
    assert "1500" in prompt


def test_deep_research_anthropic_routing(captured_anthropic_calls):
    out = reason.deep_research("question", model="anthropic")
    assert out == "FAKE_ANTHROPIC_RESPONSE"
    assert len(captured_anthropic_calls) == 1


def test_deep_research_unknown_model_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        reason.deep_research("question", model="grok")
```

- [ ] **Step 2: Run the new tests — confirm they fail**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_reason.py -v -k "deep_research"
```

Expected: All 5 deep_research tests FAIL with `AttributeError: module 'neurolang.stdlib.reason' has no attribute 'deep_research'`.

- [ ] **Step 3: Append `deep_research` to `neurolang/stdlib/reason.py`**

Open `neurolang/stdlib/reason.py`. After the `brainstorm` function (which ends with `raise ValueError(f"Unknown model: {model}")`), append a blank line and then:

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
    with `web.search` / `web.scrape` (a future Phase-2 bundle will ship
    a composite `reason.deep_research_grounded` neuro).
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

- [ ] **Step 4: Run the new tests — confirm they pass**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_reason.py -v
```
Expected: `9 passed` (4 brainstorm + 5 deep_research).

- [ ] **Step 5: Run the full suite**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/ -q
```
Expected: `121 passed` (116 + 5).

- [ ] **Step 6: Smoke test the catalog**

Run:
```
cd /home/ubuntu/neurolang && python -c "
from neurolang.stdlib import reason
print('brainstorm:', reason.brainstorm.name)
print('deep_research:', reason.deep_research.name)
"
```

Expected:
```
brainstorm: neurolang.stdlib.reason.brainstorm
deep_research: neurolang.stdlib.reason.deep_research
```

- [ ] **Step 7: Commit**

```
cd /home/ubuntu/neurolang && git add neurolang/stdlib/reason.py tests/stdlib/test_reason.py && git commit -m "feat(stdlib): reason.deep_research — multi-perspective synthesis

Single-LLM-call leaf neuro with a scaffolded prompt that forces the
model to identify sub-questions, summarize each, then synthesize.
\`depth\` kwarg toggles between ~500-word (standard) and ~1500-word
(deep) output. Ends with a Caveats line about parametric-only
research limits.

Composite version with web grounding deferred to a Phase-2 bundle as
\`reason.deep_research_grounded\`. 5 new tests, 121/121 passing."
```

---

## Task 3: STATUS + CHANGELOG + push

**Files:**
- Modify: `docs/STATUS.md`
- Modify: `CHANGELOG.md`

Final docs sweep. Move the `reason.*` bundle to "Just shipped"; pick `agent.delegate` as the new "Next up" per the recommended order in the previous bundle's STATUS update. Append a CHANGELOG entry. Push everything to origin.

- [ ] **Step 1: Update `docs/STATUS.md`**

Open `docs/STATUS.md`. Update `## Last updated:` to today's date.

In `## Just shipped (most recent first)`, prepend a new entry as #1 (and renumber existing entries):

```markdown
1. **`reason.*` stdlib expansion — brainstorm + deep_research.**
   - `reason.brainstorm(topic, *, n=5, model="openai") → str` — divergent
     ideation. Single-LLM-call leaf neuro; returns newline-delimited bullets
     covering distinct angles. Caller can `.split("\n")` for list semantics.
   - `reason.deep_research(question, *, depth="standard", model="openai") → str` —
     multi-perspective synthesis. Scaffolded prompt forces sub-question
     identification + per-question summary + synthesis. `depth="deep"` switches
     from ~500-word to ~1500-word output. Caveats footer flags parametric-only
     limits.
   - Tests in new `tests/stdlib/test_reason.py` mock the LLM via
     `monkeypatch.setattr(model_mod.llm, "openai", fake)` — no kind-dispatch
     fake needed since these neuros call `llm.openai`/`anthropic` directly.
   - 9 new tests (4 brainstorm + 5 deep_research). 121/121 total, fully offline.
```

(Renumber existing entries: REPL becomes #2, Phase 1.6 cleanup becomes #3, Phase 1.5 bundle becomes #4, NL ↔ Python compiler becomes #5, Phase 1 core library becomes #6.)

In `## Next up`, replace the current "More stdlib" task block with the next-up bundle from the previous STATUS update's "Then (in order)" list:

```markdown
## Next up

### Task: `agent.delegate` — recursive flow composition

**Why this is next:** `reason.*` extended the catalog with two pure-LLM
capabilities. The next architectural unlock is letting one neuro spawn
a sub-agent with its own catalog — fan-out for tasks too big for a flat
flow. This is the foundation for multi-agent compositions (the eventual
agentic-OS pattern).

**What to build:**
- `neurolang.stdlib.agent.delegate(task, *, catalog=None, depth=1, model="openai")`
  — leaf neuro that takes a sub-task description, optionally a filtered catalog
  of neuros the sub-agent may use, and a recursion-depth limit; runs an inner
  `propose_plan` → `compile_source` → execute loop.
- Tests covering: happy path (delegated sub-flow returns a string), unknown
  capability path (`missing` populated → fallback string returned),
  depth-limit guard (depth=0 raises or returns "delegation budget exhausted").
- A short example in `examples/agent_delegate.py` demonstrating
  `flow = web.search | agent.delegate("summarize and rank by recency")`.

**Estimated time:** 4-6 hours; architecturally the most interesting piece
shipped to date — the inner `propose → compile → run` loop becomes
recursive.

**Files to add/modify:**
- `neurolang/stdlib/agent.py` — new (defines the `agent` namespace + `delegate`)
- `neurolang/stdlib/__init__.py` — re-export `agent`
- `tests/stdlib/test_agent.py` — new

### Then (in order)
1. **Email stdlib** — `email.read` / `email.send` via IMAP/SMTP. Needs OAuth-style credentials handling; touches privacy. Pause to confirm scope before starting.
2. **Calendar stdlib** — `calendar.read` / `calendar.create` via Google Calendar API.
3. **Voice stdlib** — `voice.call` via LiveKit/Twilio adapter.
4. **First end-to-end live demo** — record `neurolang repl` + `:compile "research microplastics impact"` against a real LLM with a custom user neuro loaded from `~/.neurolang/neuros/`.
5. ~~**GitHub remote creation**~~ — DONE 2026-04-26.
```

In the `## Quick reference` block at the bottom, update:

```
Repo:     /home/ubuntu/neurolang/  (origin: github.com:neurocomputer-in/neurolang.git)
Branch:   main
Commits:  ~37 (Phase 1.5: 11 + Phase 1.6: 4 + REPL: 12 + reason.*: 3 + spec/plan/docs)
Tests:    121/121 passing offline
Stdlib:   web, reason (incl. brainstorm + deep_research), memory_neuros, model, voice (12 neuros total)
CLI:      neurolang {compile, summarize, catalog, cache, plan, repl}
API:      compile_source, decompile_summary, propose_plan, discover_neuros (renamed in Phase 1.6)
```

(Run `git log --oneline | wc -l` after Task 3's commit and adjust the count to the actual number.)

- [ ] **Step 2: Update `CHANGELOG.md`**

Open `CHANGELOG.md`. In the `## [Unreleased]` section, prepend (above the existing `### Added (REPL)` block):

```markdown
### Added (reason.* stdlib expansion)

- **`neurolang.stdlib.reason.brainstorm(topic, *, n=5, model="openai") → str`** —
  divergent-ideation leaf neuro. Single LLM call; output is newline-delimited
  bullets covering `n` distinct, non-overlapping angles on the topic.
- **`neurolang.stdlib.reason.deep_research(question, *, depth="standard", model="openai") → str`** —
  multi-perspective synthesis leaf neuro. Scaffolded prompt drives sub-question
  identification → per-question summary → synthesis. `depth="deep"` switches
  output target from ~500 to ~1500 words. Closes with a Caveats line about
  parametric-only research limits.
- Tests in new `tests/stdlib/test_reason.py` mock LLM at
  `neurolang.stdlib.model.llm.{openai,anthropic}` directly via `monkeypatch`,
  avoiding the kind-dispatch `_PROVIDERS` infrastructure used by
  `compile_source` / `propose_plan`.
- 9 new tests (4 brainstorm + 5 deep_research). 121/121 total.
- Composite-with-web-grounding `reason.deep_research_grounded` deferred to a
  Phase-2 bundle (will compose `web.search` / `web.scrape` / `reason.summarize`
  internally for fresh-source research).
```

- [ ] **Step 3: Run the full suite one last time**

Run:
```
cd /home/ubuntu/neurolang && python -m pytest tests/ -q
```
Expected: `121 passed`.

- [ ] **Step 4: Commit**

```
cd /home/ubuntu/neurolang && git add docs/STATUS.md CHANGELOG.md && git commit -m "docs: STATUS + CHANGELOG for reason.* stdlib expansion"
```

- [ ] **Step 5: Push**

```
cd /home/ubuntu/neurolang && git push 2>&1 | tail -5
```
Expected: 3 task commits + this docs commit (4 total) land on `origin/main`.

- [ ] **Step 6: Show the resulting log**

Run:
```
cd /home/ubuntu/neurolang && git log --oneline -8
```

Expected (top to bottom): the 3 task commits from this plan + the docs commit, then `c6e40d0` (the spec commit), then earlier work.

---

## Self-review notes (for the implementer)

Verify these properties hold after each commit:

1. `python -m pytest tests/ -q` finishes in under 1 second (offline pattern preserved).
2. `python -m neurolang catalog 2>&1 | head -20` lists `reason.brainstorm` and `reason.deep_research` (after Task 2 lands; verify by running and inspecting the markdown).
3. `python -c "from neurolang.stdlib import reason; print(reason.brainstorm.budget.cost_usd, reason.deep_research.budget.cost_usd)"` prints `0.008 0.02` (cost rollup will use these).
4. The `Budget(...)` cost values match the spec exactly — `propose_plan`'s cost-rollup arithmetic depends on them.

If any of these break between commits, stop and bisect rather than continuing.
