# NeuroLang — Architecture (Revised)

> **Status:** This document supersedes the "new programming language" framing in earlier docs. NeuroLang is a **Python framework with an AI-native natural-language authoring surface**, not a greenfield programming language. The categorical research stays — it shapes the framework's API design and runtime semantics. The Python ecosystem stays — we don't reinvent it.

---

## 0. The Pivot, In One Paragraph

NeuroLang is **a Python framework** that lets you write agentic code in **natural language** (Hindi, English, voice). Your NL is compiled by an LLM into **Python code that uses NeuroLang's primitives** — typed neuros, composable flows, plans-as-values, scoped memory, tracked effects, budgeted execution. The compilation is **bidirectional and cached**: change the prompt, get new code; change the code, get an updated NL summary. Programs are simultaneously inspectable as Python AND as categorical string diagrams AND as tensor networks (where differentiable). The result: anyone — and any AI — can write robust agentic code without learning Python idioms first, while the underlying programs retain the rigor of a typed, categorically-grounded library.

This is **not a new language**. This is **the right Python library + the right authoring surface** for agentic coding.

---

## 1. What Changes vs. the Earlier Plan

| Previous framing | Revised framing |
|------------------|-----------------|
| Build a new programming language with own syntax | Build a Python framework — keep all of Python's ecosystem |
| Write a parser, type checker, custom runtime | None of these — Python tooling does the work |
| Two layers: NL surface + formal NeuroLang | Two layers: NL surface + **Python code using NeuroLang library** |
| 5-phase construction; full language ships in 12 months | Same primitives, much faster shipping; Phase 1 in 4–6 weeks |
| New language adoption requires evangelism | Python adoption is `pip install neurolang` |
| Risk: language-design failure modes | Risk: we are now in DSPy / LangChain / Pydantic AI's competitive zone |

---

## 2. What Stays (Almost Everything from the Research)

The pivot does not invalidate the research. It re-targets where the research lives:

| Research item | Where it now lives |
|---------------|--------------------|
| Higher-categorical primitive types | Python class/Protocol design with categorical contracts |
| Dimensional ladder (dim 0–∞) | API hierarchy (objects → arrows → functors → 2-cats → reflection) |
| Effects as types | Effect tags via decorators; mypy-checked phantom types |
| Budget enforcement | Decorator + runtime enforcement |
| Plans-as-values | Python `Plan` class — immutable, hashable, replayable, diffable |
| Memory hierarchy | Backend protocol with discrete / differentiable / HD / episodic implementations |
| Bidirectional NL ↔ formal cached adjunction | NL ↔ **Python source code** (using NeuroLang primitives) cached via content hash |
| Programs as string diagrams = tensor networks | `flow.render()` produces both; differentiable backend wires JAX |
| 3D IDE per categorical dimension | Phase 3+; renders the SAME Python program at multiple dimensions |
| Multi-natural-language input | LLM compiler accepts any language; canonical formal output is Python |
| Hyperdimensional substrate | Phase 2; available as `neurolang.hd` |
| Decomposable logic | Phase 2; available as `neurolang.logic` |
| Self-hosting | Phase 4; compiler is itself a NeuroLang program |

The categorical insights become **the design constraints on the Python API.** They are not lost — they are channeled.

---

## 3. The New Architecture (Three Layers)

```
┌──────────────────────────────────────────────────────────────┐
│  LAYER 1 — Authoring Surface                                 │
│  Natural language (Hindi/English/voice)                      │
│  Neurocomputer (the IDE + runtime — flagship; VSCode plugin; CLI; direct API)                   │
└──────────────────────────────────────────────────────────────┘
                            ▲
                            │  bidirectional, cached
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 2 — NeuroLang Python Library                          │
│  Typed neuros, flows, plans, memory, context, prompts        │
│  Effect tracking, budget annotations, recovery primitives    │
│  Categorically grounded; mypy-checked; renderable            │
└──────────────────────────────────────────────────────────────┘
                            ▲
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 3 — Python Runtime + Ecosystem                        │
│  CPython, JAX, asyncio, Pydantic, transformers, ...          │
│  Everything pip-installable                                  │
└──────────────────────────────────────────────────────────────┘
```

**Layer 1** is what users touch. Most users live here.
**Layer 2** is what Layer 1 compiles into. Power users author here directly.
**Layer 3** is what runs. Nobody worries about it — it just works.

---

## 4. What "Neuralang Python Library" Looks Like

A user installs:

```bash
pip install neurolang
```

And writes:

```python
from neurolang import neuro, Flow, Plan, Memory, Effect, Budget

@neuro(effect="llm", budget=Budget(latency_ms=500, cost_usd=0.01))
def summarize(emails: list[str]) -> str:
    """Summarize a list of emails into a single paragraph."""
    ...

@neuro(effect="tool")
def fetch_emails(days_back: int = 7) -> list[str]:
    """Fetch unread emails from the last N days."""
    ...

# Composition is categorical
weekly_digest: Flow = fetch_emails | summarize

# Plans are first-class
plan = weekly_digest.plan(days_back=7)
plan.cost_estimate()              # rolled-up budget
plan.steps                        # inspect
plan.run(memory=Memory.discrete()) # execute
plan.replay(trace)                # deterministic replay

# Render as string diagram or mermaid
weekly_digest.render(format="discopy")
weekly_digest.to_mermaid()
```

This is **just Python**. Nothing exotic. But every primitive carries the categorical/effect/budget contracts.

---

## 5. What "NL Authoring Surface" Looks Like

User runs:

```bash
neurolang compile "summarize my unread emails from last week"
```

The CLI:
1. Sends NL prompt + library catalog to LLM
2. LLM produces Python code using NeuroLang primitives
3. Cache stores: `hash(prompt + model_version) → generated_code`
4. Reverse direction: `neurolang summarize weekly_digest.py` produces NL description

Or in the IDE / 3D environment:
- User speaks: "fetch unread emails, classify them, then send me a daily summary"
- IDE renders the resulting flow as a 3D string diagram
- User drags to add a step; IDE updates the Python source; cache regenerates the NL summary
- Three co-equal authoring modes (NL / drag / direct Python edit), all kept in sync

---

## 6. The Compiler is a Bidirectional, Cached LLM Pipeline

**Forward (NL → Python):**

```
Input:  "summarize my unread emails from last week"
Step 1: LLM with prompt + NeuroLang library reference + cache lookup
Step 2: Schema-constrained decoding (Outlines / Instructor) ensures
        output is valid Python using NeuroLang primitives
Step 3: AST validation — must type-check; must use only registered neuros
Step 4: Cache: hash(prompt + model_id + library_version) → generated_code
Output: Valid Python module
```

**Reverse (Python → NL):**

```
Input:  weekly_digest.py
Step 1: Parse + extract structural summary (flows, neuros, types, effects)
Step 2: LLM produces NL summary in user's preferred language
Step 3: Cache: hash(canonical_python_form + model_id) → summary_text
Output: "Fetches unread emails from the last 7 days, summarizes them..."
```

**Triangle identity (the adjunction's coherence):**

Compile → summarize round-trips back to a normalized NL form (cached as identity).
Summarize → compile round-trips back to canonical Python (cached as identity).

When the round-trip fails (LLM drift), the user is shown the diff — they can confirm or correct, and the correction caches.

**This is the same theoretical structure described in `RESEARCH.md`.** It just compiles into Python now, not into a new language.

---

## 7. What Differentiates Us From DSPy / LangChain / Pydantic AI

| Capability | LangChain | DSPy | Pydantic AI | **NeuroLang** |
|------------|-----------|------|-------------|---------------|
| Compositional programs | ✓ | ✓ | partial | ✓ (categorical) |
| NL authoring surface | ✗ | partial (signatures) | ✗ | ✓ **bidirectional cached** |
| Plans as first-class values | ✗ | ✗ | ✗ | ✓ |
| Effects in types | ✗ | ✗ | partial | ✓ |
| Budget annotations | ✗ | ✗ | ✗ | ✓ |
| Recovery as language primitive | library | library | library | ✓ **language-level** |
| Memory hierarchy with scoping | flat | flat | flat | ✓ (Phase 2+) |
| Hyperdimensional substrate | ✗ | ✗ | ✗ | ✓ (Phase 2+) |
| End-to-end differentiable flows | ✗ | partial | ✗ | ✓ (Phase 2+) |
| Multi-NL input | ✗ | ✗ | ✗ | ✓ |
| 3D IDE / categorical visualization | ✗ | ✗ | ✗ | ✓ (Phase 3+) |
| Self-hosting compiler | ✗ | partial | ✗ | ✓ (Phase 4+) |

We are not picking a fight with all three at once. We **complement** Pydantic AI's typing rigor, **extend** DSPy's compositional ideas, and **replace** LangChain's untyped chains with a categorically-grounded equivalent.

---

## 8. The New Construction Path (Aggressive but Achievable)

### Phase 1 — Library MVP (4–6 weeks)

**Deliverable:** `pip install neurolang` produces a working Python library.

- `Neuro`, `Flow`, `Plan`, `Memory`, `Context`, `Prompt`, `Effect`, `Budget`, `Recovery` as Python classes/Protocols.
- `@neuro` decorator + Protocol for authoring.
- Composition operators (`|` sequential, `&` parallel-AND, `+` parallel-OR).
- Discrete memory backend.
- Property-based tests for categorical laws (associativity, identity, naturality).
- `flow.render()` → discopy string diagram.
- `flow.to_mermaid()` → Mermaid for docs.
- Effect tracking via decorators + runtime tags.
- Plan as immutable typed DAG with `.run()`, `.replay()`, `.modify()`, `.diff()`, `.hash()`.
- Public API documented; tutorial notebook.

**Reviewer audience:** category theorists (sanity check on the categorical contracts) + practicing LLM-agent builders (sanity check on practical usefulness). If both groups give a thumbs-up, Phase 1 has succeeded.

### Phase 2 — NL Compiler + Differentiability (4–8 weeks)

**Deliverable:** `neurolang compile "..."` produces valid Python that runs.

- LLM-based bidirectional compiler with cache.
- Schema-constrained decoding via Outlines/Instructor.
- Triangle-identity verification on the cache.
- Multi-language NL input (English + Hindi at minimum).
- VSCode plugin: NL command → generates `.py` file.
- JAX backend for differentiable flows.
- Soft-attention memory backend (differentiable).
- Hyperdimensional substrate (`neurolang.hd`) — Kanerva primitives.

### Phase 3 — 3D IDE + Memory Hierarchy (3–6 months)

**Deliverable:** Web-based 3D IDE; full memory hierarchy.

- WebGL string-diagram rendering (per-dimension visualization).
- Voice input → NL compiler → diagram update.
- Drag manipulation → Python source mutation → NL re-summary.
- Episodic + semantic + procedural memory layers.
- Compressed memory (sparse / low-rank).
- Decomposable logic library (`neurolang.logic`).

### Phase 4 — Self-Hosting + Ecosystem (12+ months)

**Deliverable:** The NL compiler is itself written in NeuroLang. A small standard library of neuros exists. Third parties have started extending.

- Self-hosting compiler.
- Standard neuro library (`neurolang-stdlib`).
- Community contribution model.
- Production deployment guides.

---

## 9. What We Build Around (Don't Reinvent)

| What we use | Why |
|-------------|-----|
| **Python + Pydantic** | Type-safe data + ecosystem |
| **anyio / asyncio** | Async runtime for LLM calls |
| **JAX** | Differentiable backend (Phase 2) |
| **discopy** | String diagram rendering (Phase 1) |
| **Outlines / Instructor** | Schema-constrained LLM output (Phase 2) |
| **mypy** | Static type checking with phantom types |
| **hypothesis** | Property-based testing of categorical laws |
| **MLflow / Weave** | Trace + observability (Phase 2+) |
| **VSCode extension API** | Editor integration (Phase 2) |
| **Three.js / WebGL** | 3D visualization (Phase 3) |

We compose existing tools. We do not rebuild any of them.

---

## 10. The New Top-Level Pitch

> **NeuroLang is the Python framework for AI-native agentic coding.**
>
> Write agents in natural language — Hindi, English, voice — and NeuroLang compiles your prompts into typed, composable, inspectable Python programs. Your code stays human-readable both ways: the prompt produces Python; the Python produces a summary in your language. Plans are first-class values you can inspect, replay, and diff. Memory has scoping. Effects have types. Budgets are enforced. Recovery is a language primitive, not a library hack.
>
> Under the hood, your programs are categorically-grounded string diagrams. Where they're differentiable, they're also tensor networks. The framework's bones are the same mathematics that powers compositional NLP, categorical quantum mechanics, and modern type theory — wrapped in an API that feels like writing Python.
>
> **You don't learn a new language. You write what you mean.**

---

## 11. The Implementation Plan, Practically

### Week 1
- Repo skeleton with hatchling, MIT, smoke tests (DONE — already in `/home/ubuntu/neurolang/`)
- `Neuro` Protocol + `@neuro` decorator
- `Flow` with `|` operator only (sequential first)
- Property tests for associativity, identity

### Week 2
- `&` and `+` operators (parallel)
- Discrete `Memory` backend behind a Protocol
- `Plan` immutable DAG; `run()`, `hash()`, `serialize()`
- First end-to-end example: `fetch | filter | summarize` runnable

### Week 3
- Effect tracking via `@effect("llm")`, `@effect("tool")`
- Budget decorator; runtime enforcement
- Recovery primitives: `fallback`, `retry`, `escalate`
- discopy + mermaid rendering

### Week 4
- Documentation, tutorial notebook
- Type stubs + mypy clean
- Publish to TestPyPI; gather feedback from 5 reviewers
- Iterate

### Week 5
- Address feedback
- Cut Phase 1 release: `0.1.0`
- Public announcement, blog post, demo video

After this, Phase 2 (NL compiler) starts, with everything Phase 1 already validated.

---

## 12. The Single Most Important Thing

> **Write the smallest, most beautiful Python library that proves the categorical claims hold and that the API actually feels good. Do NOT yet build the NL compiler, the IDE, the differentiable substrate, the hyperdimensional memory.** Those come once Phase 1 has won reviewer trust.
>
> If a category theorist says "your composition operators satisfy the laws," and an LLM-agent builder says "I'd actually use this over LangChain," Phase 1 has succeeded. Everything else follows.

---

*Document at `/docs/ARCHITECTURE.md`. This is the canonical architecture going forward. Earlier docs (VISION, RESEARCH, LANDSCAPE, COMPARISON, OPEN_DECISIONS) remain useful as background — read them as the *why*; read this as the *what* and *how*.*
