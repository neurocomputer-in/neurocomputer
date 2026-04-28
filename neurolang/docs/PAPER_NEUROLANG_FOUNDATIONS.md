# NeuroLang: A Higher-Categorical Framework for Natural-Language Agentic Programming

**Draft research-paper section — Foundations, Framework, and Implementation Status**

*Compiled 2026-04-28. Synthesizes the project's research artifacts (RESEARCH.md, VISION.md, ARCHITECTURE.md, COMPARISON.md, LITERATURE_REVIEW_CATEGORICAL_DL.md, RESEARCH_BRAINSTORM_CATEGORICAL_TRAINING.md), the implemented Phase 1.1–1.9 codebase, and the design specs accumulated through April 2026.*

---

## Abstract

We present **NeuroLang**, a Python framework for agentic programming whose primitives are derived directly from higher-category theory and whose authoring surface is natural language. NeuroLang's central design claim is that grammar, computation, and tensor networks are three faces of the *same* underlying mathematical structure — the higher-categorical / string-diagrammatic / monoidal-categorical formalism — and that exposing this structure as the primitive vocabulary of a programming environment yields a substrate qualitatively different from existing agent frameworks (LangChain, DSPy, AutoGPT, CrewAI). A NeuroLang program is simultaneously: (i) a typed Python program, (ii) a string diagram in a higher category, and (iii) a tensor network where its primitives are differentiable. The natural-language compiler is realised mathematically as the **unit and counit of an adjoint pair of functors**, with the cache literally instantiating the adjunction's coherence data. We describe the framework's theoretical foundations, its three-layer architecture, the implemented standard library (currently 17 stdlib neuros plus the recursive-composition factory `agent.delegate`), the bidirectional NL ↔ Python compiler, and the long-horizon research programme that interprets a trained neural network itself as a NeuroLang program. The implementation, available open source at `github.com/neurocomputer-in/neurolang`, currently passes 172 offline tests and ships an interactive REPL with live-LLM compilation.

---

## 1. Introduction

The current generation of agent-orchestration frameworks treats large language models as opaque functions and the programs that call them as untyped pipelines of prompts and tools. This works for prototypes, but as flows grow in size and recursion depth, three pathologies emerge: (a) lack of compositional reasoning — a flow's behaviour cannot be derived from the behaviour of its parts; (b) untracked side-effects — agents write to mailboxes, billing systems, or production code without surfacing the relevant capability boundary; and (c) opaque planning — the orchestrator's "decision" lives inside an LLM's context window, irretrievable, irreproducible, and unverifiable.

We argue that these pathologies are not accidental. They are the inevitable consequence of building agentic systems on substrates (Python dictionaries, JSON tool descriptors, prompt templates) that systematically erase compositional structure. The solution is not to layer further library abstractions over those substrates, but to design a substrate whose primitives **are** the relevant compositional structure.

That structure exists, and has been studied for sixty years. It is the mathematical structure that simultaneously underlies:

- the **grammar** of natural language (Lambek 1958, Coecke–Sadrzadeh–Clark 2010),
- the **proofs** of intuitionistic and linear logic (Curry–Howard 1969, Girard 1987),
- the **tensor networks** of theoretical physics (Penrose 1971, Joyal–Street 1991),
- the **gradient flow** of deep learning (Fong–Spivak–Tuyéras 2019, Cruttwell–Gavranović et al. 2022),
- and the **morphisms of higher categories** (Mac Lane 1971, Lurie 2009).

This is the *higher-categorical / string-diagrammatic* formalism. Its surprising universality across domains is not a coincidence; it is the content of the **three-tower identification** that we describe in Section 3.

NeuroLang is a deliberate, systematic exploitation of this identification for the design of a programming framework. We claim:

> **Thesis.** A framework whose primitives are typed at definite categorical dimensions, whose composition operators are the canonical monoidal-categorical operations, whose effects are tracked as morphism kinds, and whose natural-language authoring surface is realised as the unit/counit of an adjunction with the formal layer, will dominate the design of agentic systems for the next two decades.

This document collects the theoretical foundations behind that thesis, surveys the related work (Section 4), describes the framework's architecture and current standard library (Sections 5–8), articulates the long-horizon research programme that views trained neural networks as themselves NeuroLang programs (Section 9), and reports the implementation status as of Phase 1.9 (Section 11).

---

## 2. Background and Motivation

### 2.1 The Agentic-Programming Landscape

We focus on three contemporary frameworks for comparison: **LangChain** (Chase 2022) — chains of LLM calls and tools, dynamically typed; **DSPy** (Khattab et al. 2023) — declarative LLM programs with signatures and compilation passes; and **Pydantic AI** (Pydantic 2024) — typed structured LLM outputs with strict schemas. These represent the empirical practices of the field.

The LangChain model is a flexible but type-poor "lego of strings." DSPy introduces compositional signatures (objects → objects) but does not commit to categorical structure. Pydantic AI brings rigour to single-call typing but offers no compositional algebra over multi-call flows. None of these systems treats a *plan* as a first-class, inspectable, replayable value. None tracks effects in the type system. None offers natural-language authoring as an integral, bidirectional, mathematically-grounded surface.

### 2.2 What is Missing

The following capabilities are absent or weakly present in existing frameworks:

| Capability | LangChain | DSPy | Pydantic AI | NeuroLang |
|---|---|---|---|---|
| Compositional programs | ✓ untyped | ✓ partial | partial | ✓ categorical |
| NL authoring surface | ✗ | partial (signatures) | ✗ | ✓ bidirectional, cached |
| Plans as first-class values | ✗ | ✗ | ✗ | ✓ |
| Effects in types | ✗ | ✗ | partial | ✓ |
| Budget annotations | ✗ | ✗ | ✗ | ✓ |
| Recovery as language primitive | library | library | library | ✓ language-level |
| Memory hierarchy with scoping | flat | flat | flat | ✓ (Phase 2+) |
| Hyperdimensional substrate | ✗ | ✗ | ✗ | ✓ (Phase 2+) |
| End-to-end differentiable flows | ✗ | partial | ✗ | ✓ (Phase 2+) |
| Multi-language NL input | ✗ | ✗ | ✗ | ✓ |
| Categorical / 3D visualisation | ✗ | ✗ | ✗ | ✓ (Phase 3+) |
| Self-hosting compiler | ✗ | partial | ✗ | ✓ (Phase 4+) |

Table 1 — Comparison along capability axes (see also `docs/COMPARISON.md`).

The NeuroLang programme is the systematic supply of all twelve.

---

## 3. Theoretical Foundations

### 3.1 The Three-Tower Identification

The core observation that motivates NeuroLang's design is that three apparently distinct domains share a common mathematical structure:

| Natural Language (Grammar) | Category Theory | Computation / Tensor Network |
|---|---|---|
| Noun | Object (dim 0) | Tensor index / vector slot |
| Verb | Morphism (dim 1) | Linear map / tensor contraction |
| Adverb | Natural transformation (dim 2) | Higher-order tensor operation |
| Sentence | Composed arrow / commutative diagram | Computation graph |
| Paragraph | Diagram in a category | Module of computation |
| Translation | Equivalence of categories | Reparameterization |
| Grammar itself | Category of grammatical types | Type system of the network |

Table 2 — The three-tower identification (after RESEARCH.md §1).

This identification is rigorously established by:

- **Lambek (1958)** — grammatical types form a residuated monoid (a categorical structure); parsing is composition in this category.
- **Curry–Howard (1934, 1969)** — proofs ≅ programs; types ≅ propositions.
- **Curry–Howard–Lambek** — the three-way correspondence between programs, proofs, and grammatical compositions.
- **Coecke, Sadrzadeh, Clark (2010)** — DisCoCat: distributional compositional categorical semantics, demonstrating that the same mathematics underlies categorical quantum mechanics and compositional NLP.
- **Penrose (1971)** — string diagrams for tensor algebra are isomorphic to the diagrams of monoidal categories.
- **Joyal & Street (1991)** — formalisation of string-diagrammatic calculus for monoidal categories; the geometric proof that string diagrams *are* tensor networks.
- **Atiyah (1988), Lurie (2009)** — the cobordism hypothesis: physics is higher-categorical (TQFT is an n-functor between cobordism categories and a target category).
- **Cruttwell, Gavranović, et al. (2022)** — categorical foundations of gradient-based learning. Backpropagation is a functor.

The mathematical content of the three-tower identification can be stated as the following meta-theorem:

> **Meta-theorem (three-tower).** *The category of grammatical compositions in a residuated monoid (Lambek), the category of types in a Curry–Howard system, and the category of pre-tensor-networks under monoidal composition (Penrose / Joyal–Street) are equivalent up to coherence.*

NeuroLang is the systematic exploitation of this equivalence as the basis of a programming framework.

### 3.2 The Dimensional Ladder

NeuroLang's primitives are organised strictly by their categorical dimension. A primitive may not be introduced unless its dimension is justified. The ladder runs from Dim 0 (substrate) to Dim ∞ (reflection):

| Dimension | NeuroLang Primitive | Neural-Network Counterpart |
|---|---|---|
| **Dim 0 — Substrate** | Values, tensors, hyperdimensional vectors, memory cells | Weights, activations, embeddings, attention scores |
| **Dim 1 — Arrows** | Functions, differentiable maps, state transitions, effects | Individual layers (Linear, Conv, Attention head), activation functions |
| **Dim 2 — Functors / Natural Transformations** | Higher-order functions, plans-as-values, flows, memory scopes | Multi-head attention (functor over heads), residual / skip connections (η : Id ⇒ F), layer normalisation (natural transformation) |
| **Dim 3 — 2-Categories** | Plan transformations, optimisation passes, protocol rewrites | Architecture search (NAS), pruning, knowledge distillation |
| **Dim ∞ — Reflection** | Meta-neuros, self-modifying compiler | Self-modifying architectures, learned optimisers, neural architecture search |

Table 3 — The dimensional ladder, applied to programs (left) and neural networks (right).

The right-hand column is a non-trivial extension of the framework. We return to it in Section 9.

The design rule is strict:

> **A primitive may be added at dimension *n* only if it cannot be expressed cleanly at dimension *n*−1 without loss of structure.**

This rule prevents the API from sprawling; each primitive earns its place by exhibiting structure unavailable at lower dimensions.

### 3.3 The Compiler as an Adjoint Pair of Functors

The natural-language authoring surface (Section 6) is mathematically realised as a pair of functors between two categories:

```
              left-adjoint:  L : NL → Formal     (compile)
                                ⊣
              right-adjoint: R : Formal → NL     (summarise)
```

Where **NL** is the category whose objects are intents and whose arrows are inferences in natural language (paraphrase, entailment, qualification), and **Formal** is the category whose objects are typed Python programs using the NeuroLang library and whose arrows are typed flows.

The adjunction has two associated natural transformations:

- The **unit** η : 1\_NL ⇒ R∘L of the adjunction asserts that every NL prompt round-trips through formal compilation back to a normalised NL summary. The cache *is* η, materialised.
- The **counit** ε : L∘R ⇒ 1\_Formal asserts that every formal program round-trips through summarisation back to an executable program. The cache stores ε.
- The **triangle identities** impose self-consistency: compile-then-summarise is identity-up-to-cache; summarise-then-compile is identity-up-to-cache.

This is not a metaphor. It is the precise mathematical contract that the LLM compiler must satisfy. Caching is not a performance optimisation; it is the *unit and counit data* of the adjunction, made into storage. When the LLM model changes (new version), the cache is invalidated, but **only the parts whose adjunction-coherence breaks** — verifiable, principled cache invalidation.

### 3.4 String Diagrams Are Tensor Networks

The fundamental geometric lemma underlying the framework is:

> **Lemma (Penrose / Joyal–Street).** *A morphism in a monoidal category, drawn as a string diagram, is the same mathematical object as a tensor network.*

**Consequence for NeuroLang.** When the user composes neuros into a flow, the diagram they construct is *literally* a tensor network. When the system trains, gradients flow through that network. When the user inspects, the same network is rendered as a categorical diagram. **No translation. No two systems. One object.**

This is why the framework's `flow.render()` method can produce a `discopy` string diagram, a Mermaid graph, and (in Phase 3) a 3D-IDE renderable structure all from the same underlying typed graph: there is one canonical object — the typed flow — and all renderings are projections of it.

---

## 4. Related Work

We survey six research threads that the NeuroLang programme either subsumes, extends, or unifies. The full literature review is in `docs/LITERATURE_REVIEW_CATEGORICAL_DL.md`; the summary follows.

### 4.1 Backprop as Functor

Fong, Spivak, and Tuyéras (2019) proved that gradient descent and backpropagation form a symmetric monoidal functor from parameterised functions to learning algorithms, with the consequence that modular training is equivalent to end-to-end training under categorical conditions. Cruttwell, Gavranović, Ghani, Wilson, and Zanasi (2022) extended this to a unified treatment of SGD, Adam, AdaGrad, and other optimisers using lenses, parameterised maps, and reverse-derivative categories. Gavranović's PhD thesis (2024) provides the most comprehensive categorical treatment of deep learning to date. The CatGrad project (2023–24) demonstrates that these ideas are implementable, not merely theoretical.

**NeuroLang's contribution.** Embed this in a user-facing framework; apply the dimensional ladder to model internals.

### 4.2 Mechanistic Interpretability

Elhage et al. (Anthropic 2022) showed that neural networks represent more features than they have dimensions — features are superimposed, a structural property of the substrate. Anthropic's *Scaling Monosemanticity* (2024) demonstrated that sparse autoencoders can extract interpretable, compositional features from large language models. Kornblith et al. (2019) introduced Centred Kernel Alignment (CKA) and showed that adjacent layers often have measurably high similarity. Raghu et al. (2017) introduced SVCCA for measuring intrinsic dimensionality and convergence dynamics.

**NeuroLang's contribution.** Give mechanistic interpretability a categorical formalism — features as objects, circuits as morphisms, superposition as a categorical phenomenon. Where CKA *measures* similarity, categorical natural isomorphisms would *explain* it.

### 4.3 Tensor Networks for Machine Learning

Stoudenmire and Schwab (NeurIPS 2016) demonstrated that Matrix Product States — a tensor network from quantum physics — achieve <1% error on MNIST with far fewer parameters than dense networks. Novikov et al. (2015) compressed FC layers using Tensor Train decomposition with 200,000× compression and minimal accuracy loss on CIFAR-10. The 2020–24 survey literature documents wide application of Tucker, CP, TT, and MERA decompositions to ML.

**NeuroLang's contribution.** Use categorical structure to *guide* decomposition during composition rather than apply it post-hoc as compression.

### 4.4 Geometric Deep Learning

Cohen and Welling (2016) introduced Group Equivariant CNNs. Bronstein, Bruna, Cohen, and Veličković (2021) provided a unified framework — *Geometric Deep Learning: Grids, Groups, Graphs, Geodesics, and Gauges* — recognising CNNs, GNNs, and Transformers as instances of equivariant maps on geometric domains. Cohen, Weiler et al. (2018–2021) generalised G-CNNs to arbitrary manifolds via fibre bundles and gauge theory.

**NeuroLang's contribution.** Subsume group-theoretic equivariance under categorical equivariance (strictly more general: groups are special cases of categories). The connection between Fong–Spivak's categorical learning and Bronstein et al.'s geometric deep learning has not yet been made in the literature; NeuroLang's framework provides the natural setting for that connection.

### 4.5 LoRA and Weight Sharing

Hu et al. (Microsoft, 2021) introduced LoRA: weight updates for fine-tuning lie in a low-rank subspace. Tied-LoRA (2023) showed that LoRA matrices can be shared across layers with 90%+ parameter reduction. TensLoRA (2024) extended this to tensor decompositions across layers, heads, and projections.

**NeuroLang's contribution.** Provide a categorical explanation: LoRA is a natural transformation; Tied-LoRA is parameter sharing along a natural isomorphism. Automate the discovery of which layers can be tied via categorical structure.

### 4.6 DisCoCat and Compositional NLP

Coecke, Sadrzadeh, and Clark (2010) introduced DisCoCat: sentence meaning as tensor contraction guided by grammatical types that form a category. Higher-Order DisCoCat (2023–24) extends to adverbs, negation, and quantifiers as higher categorical structure. DisCoCirc (2021+) extends from sentences to entire texts (discourse), recognising language as a 2D circuit rather than a 1D string.

**NeuroLang's contribution.** DisCoCat is the NLP arm of the same mathematical structure NeuroLang exploits. NeuroLang unifies DisCoCat (language), Backprop as Functor (learning), and tensor networks (computation) in **one framework**. To our knowledge no prior work has performed this three-way unification.

### 4.7 The Genuine Gap

| Research Thread | Established | NeuroLang's Contribution |
|---|---|---|
| Backprop as Functor | ✓ Proven | Embed in user-facing framework; apply dimensional ladder to model internals |
| Mechanistic Interpretability | ✓ Active | Give it categorical formalism (features as objects, circuits as morphisms) |
| Tensor Networks for ML | ✓ Proven | Use categorical structure to *guide* decomposition (not just post-hoc compression) |
| Geometric Deep Learning | ✓ Unified | Subsume under categorical equivariance (strictly more general) |
| LoRA / Weight Sharing | ✓ Empirical | Categorical explanation; automated discovery of natural isomorphisms |
| DisCoCat / Compositional NLP | ✓ Foundational | Unify with learning and computation in one framework |

Table 4 — What exists, and what NeuroLang adds.

> **No existing work unifies all six threads under a single dimensional ladder and embeds them in a practical programming framework.**
>
> The closest is Gavranović's 2024 PhD thesis, which provides a categorical theory of deep learning. But it stops at theory — no user-facing framework, no dimensional classification of model components, no connection to mechanistic interpretability or geometric deep learning. NeuroLang's unique position is that it already has the dimensional ladder (RESEARCH.md), the programming framework (the library, currently 172 tests passing), and the tensor-network identification (string diagrams via discopy + Mermaid).

---

## 5. The NeuroLang Framework

### 5.1 Three-Layer Architecture

NeuroLang is a Python framework. Its architecture has three layers:

```
┌──────────────────────────────────────────────────────────────┐
│  LAYER 1 — Authoring Surface                                 │
│  Natural language (Hindi/English/voice), CLI, REPL,         │
│  Neurocomputer IDE (Phase 3+), VSCode plugin (deferred)      │
└──────────────────────────────────────────────────────────────┘
                            ▲
                            │  bidirectional, cached adjunction
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 2 — NeuroLang Python Library                          │
│  Typed neuros, flows, plans, memory, context, prompts,      │
│  effect tracking, budget annotations, recovery primitives,  │
│  categorically grounded, mypy-checked, renderable           │
└──────────────────────────────────────────────────────────────┘
                            ▲
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  LAYER 3 — Python Runtime + Ecosystem                        │
│  CPython, JAX (Phase 2+), asyncio, Pydantic, transformers,  │
│  LLM provider SDKs (OpenAI, Anthropic, OpenRouter, ollama)  │
└──────────────────────────────────────────────────────────────┘
```

Most users live in Layer 1; power users author directly in Layer 2; nobody worries about Layer 3 — it is the Python ecosystem.

### 5.2 The Core Primitives

NeuroLang's Layer 2 vocabulary, drawn directly from the dimensional ladder:

```python
from neurolang import (
    neuro, Flow, Plan, Memory, Effect, Budget, Registry,
    compile_source, decompile_summary, propose_plan, discover_neuros,
)
```

The fundamental unit is the **Neuro** — a typed Python callable carrying:

- `name` — a stable, qualified identity (`"neurolang.stdlib.email.send"`).
- `effects` — a `frozenset[Effect]` from `{PURE, LLM, TOOL, HUMAN, TIME, VOICE, MEMORY}`.
- `budget` — a `Budget(latency_ms=..., cost_usd=...)`.
- `kind` — a string tag (`"skill.email"`, `"reason"`, `"memory.store"`).
- `description` — the function's docstring, used by the NL compiler as catalog material.
- `reads` / `writes` — declared memory keys (functorial constraints).

A neuro is created by the `@neuro` decorator on a Python function:

```python
@neuro(
    effect="tool",
    kind="skill.email",
    name="neurolang.stdlib.email.send",
    budget=Budget(latency_ms=1500, cost_usd=0.0),
)
def send(to: str | list[str], subject: str, body: str, *,
         cc=None, bcc=None, html=False) -> dict:
    """Send an email via SMTP."""
    ...
```

### 5.3 Composition Operators as Monoidal Structure

NeuroLang exposes three composition operators, each implementing a canonical monoidal-categorical operation:

| Operator | Semantics | Categorical structure |
|---|---|---|
| `f \| g` | Sequential composition: run f, pass output to g | Composition of morphisms in the underlying category |
| `f & g` | Parallel-AND: run both, return tuple of results | Tensor product (monoidal product) |
| `f + g` | Parallel-OR: race, first result wins | Coproduct in the appropriate category |

Table 5 — Composition operators and their categorical meanings.

The associativity, identity, and naturality laws are enforced by property-based tests (`hypothesis`), satisfying the categorical contracts required by Section 3.

### 5.4 Plans as First-Class Values

A `Plan` is the immutable, hashable, replayable value resulting from binding arguments to a flow:

```python
weekly_digest: Flow = fetch_emails | reason.summarize
plan = weekly_digest.plan(days_back=7)
plan.cost_estimate()              # rolled-up budget from each step
plan.steps                         # inspect the typed DAG
plan.run(memory=Memory.discrete()) # execute
plan.replay(trace)                 # deterministic replay
plan.hash()                        # content-addressable identity
```

This is in stark contrast to LangChain's runtime-state-only model: in NeuroLang, one *can* hold a plan in one's hand, diff two plans, ship a plan as a value, replay a plan deterministically.

### 5.5 Effects as Types

Every neuro declares its effect set. Effects are tracked structurally; they propagate functorially through composition. A flow's effect set is the union of its constituents' effect sets. The runtime uses effects for cost accounting, budget enforcement, and (in the planned mypy-phantom-typed extension) for compile-time checking of effect-purity boundaries.

This is the categorical analogue of an indexed monad over an effect signature, in the sense of Plotkin and Pretnar's algebraic effects.

### 5.6 Memory Hierarchy

Memory in NeuroLang is itself a categorical structure:

| Layer | Kind | Properties |
|---|---|---|
| Discrete | Key–value, exact | Determinism, fast lookup, brittle |
| Differentiable | Soft attention store | Gradient flow through recall (Phase 2+) |
| Compressed | Sparse / low-rank / quantised | Capacity vs. precision trade |
| Hyperdimensional | High-dimensional vectors with bind/bundle/permute | Compositional, fault-tolerant, semantic (Phase 2+) |
| Episodic | Time-indexed | Sequence of experiences |
| Semantic | Concept-indexed | Long-term abstracted knowledge |
| Procedural | Skill-as-flow | Memory that executes |

Table 6 — The memory hierarchy. Each layer is a functor into the substrate; layers compose.

In the current (Phase 1.9) implementation, the discrete layer is shipped via `Memory.discrete()`. Phases 2+ implement the remaining layers behind the same Protocol.

---

## 6. The Natural-Language Authoring Surface

### 6.1 Bidirectional Compilation

The NL compiler is realised by two functions:

```python
compile_source("research microplastics impact") -> str  # Python source
decompile_summary(python_source) -> str                 # NL description
propose_plan("send weekly summary to team") -> ProposedPlan
```

The forward direction (`compile_source`) sends an NL prompt + the registry's catalog (rendered as Markdown) to an LLM and returns Python code that uses the registered neuros. Schema validation ensures the output references only registered neuros; the AST is typechecked before being returned.

The reverse direction (`decompile_summary`) sends a Python program and asks the LLM for a normalised NL summary in the user's preferred language.

Both directions are cached. The cache key is `sha256(prompt + model_version + system_prompt + few_shot + catalog_fingerprint)[:8]` — that is, the cache invalidates automatically when the prompt, the model, the system prompt, the few-shot examples, *or the available neuros* change. This is the engineering realisation of Section 3.3's adjunction-coherence invariant.

### 6.2 Catalog-Driven Planning

`propose_plan(prompt)` is a single-LLM-call planner that returns a `ProposedPlan` dataclass:

```python
@dataclass
class ProposedPlan:
    intents: list[str]            # decomposition of the goal
    neuros: list[str]             # which registered neuros to use
    missing: list[str]            # capabilities not in the registry
    rationale: str                # natural-language explanation
    cost_estimate: Budget         # rolled-up budget from each chosen neuro
    cache_hit: bool
```

The catalog is the NL surface of the registry. Each neuro contributes its name, signature, docstring, and effect tags to a Markdown rendering that the LLM consumes. The planner is therefore aware of the user's installed standard library, custom neuros (loaded from `~/.neurolang/neuros/`), and project-local neuros (`<project>/neuros/`) — at the moment of the call.

### 6.3 The Discovery System

NeuroLang ships a deliberate, eager-at-startup discovery system (`neurolang/discover.py`):

- `~/.neurolang/neuros/` — the user's personal neuro library, persistent across projects.
- `<project>/neuros/` — project-local neuros, auto-detected via project markers (`pyproject.toml`, `.git/`, etc.).
- Explicit `extra_paths` for non-standard layouts.

This is the substrate of the **user-extensible language** vision (VISION_NOTES_RAW.md item #2): drop a `@neuro`-decorated Python file in the right place and the planner can reference it the next time it runs. The framework's vocabulary grows with each user.

---

## 7. Recursive Composition: `agent.delegate`

Phase 1.8 introduced `agent.delegate`, a higher-order primitive that lets a flow *spawn a sub-flow* whose contents are decided at runtime by the planner:

```python
flow = passthrough | agent.delegate(
    "given input text, produce a two-sentence summary",
    catalog=["neurolang.stdlib.reason.*"],
    depth=1,
)
```

The outer author specifies WHAT the sub-task is; the inner sub-agent figures out WHICH neuros to compose to achieve it. This is the recursive-composition primitive that makes NeuroLang flows self-referential.

Implementation details (`neurolang/stdlib/agent.py`, ~250 LOC):

- **Factory pattern.** Each `delegate(...)` call returns a fresh `@neuro(register=False)` closure with `task` baked in. The inner neuro is `async`, sharing the parent's event loop (sync `flow.run()` would deadlock).
- **Catalog scoping.** A `catalog=["neurolang.stdlib.reason.*"]` glob list constructs a fresh `Registry` containing only matching neuros. The sub-planner cannot wander outside its assigned scope.
- **Memory inheritance.** The agent captures `current_memory()` at call time and passes it through to the sub-flow's `run_async`, preserving the parent's memory ContextVar.
- **Depth budget.** A `_delegation_depth: ContextVar[Optional[int]]` enforces recursion limits. `depth=0` raises `DelegationBudgetExhausted`; default `depth=1` permits one level of recursion.
- **Failure modes.** Planner-returns-`missing` produces a soft-fail string `"[delegate: cannot satisfy task — missing: {intents}]"`. Compile-time errors wrap as `DelegationFailed(task, cause)`.

Categorically, `agent.delegate` is a **higher-order morphism** (Dim 2) in the dimensional ladder: a functor from `(task: NL_string)` to `Neuro`. The factory pattern is the realisation of this functor as a Python closure.

---

## 8. The Standard Library — Building a Vocabulary

The NeuroLang stdlib provides the minimal vocabulary on which the NL compiler can plan. Each stdlib neuro is a unit of capability the planner can compose.

| Module | Neuros | Role | Effect |
|---|---|---|---|
| `web` | `search`, `scrape` | Information retrieval | tool |
| `reason` | `summarize`, `classify`, `brainstorm`, `deep_research` | LLM-backed cognition | llm |
| `memory_neuros` | `store`, `recall` | Persistent memory wrappers | memory |
| `model` | `llm.openai` | LLM dispatch primitive | llm |
| `voice` | `transcribe`, `synthesize` | Speech I/O | voice |
| `agent` | `delegate` (factory) | Recursive composition | llm + tool |
| `email` | `send`, `read`, `search`, `mark` | Mail integration (Phase 1.9) | tool |

Table 7 — The standard library as of Phase 1.9: 17 stdlib neuros plus the `agent.delegate` factory.

### 8.1 The Email Stdlib (Phase 1.9)

The most recently shipped stdlib module is `email`. It exemplifies the design philosophy:

- **Zero new dependencies.** Built on Python's stdlib `imaplib` + `smtplib` + `email.message`. Default backend is IMAP/SMTP with SSL (port 993 / 465), application-password authentication.
- **Domain auto-detect.** Gmail, Outlook/Hotmail, Yahoo hosts are inferred from the `EMAIL_ADDR` suffix; explicit `EMAIL_IMAP_HOST`/`EMAIL_SMTP_HOST` always overrides.
- **Composable shape.** `read(folder, n, unread_only)` and `search(query)` return `list[dict]` with stable schema — `uid`, `from`, `to`, `cc`, `subject`, `date` (ISO 8601), `body` (text/plain preferred; HTML stripped via stdlib `html.parser`), `snippet`, `unread`, `flagged`. `send(to, subject, body, *, cc, bcc, html)` builds correct MIME (BCC routed via SMTP envelope, not headers).
- **Error semantics.** A custom `EmailError(operation, cause)` wraps `imaplib.IMAP4.error`, `smtplib.SMTPException`, and `OSError` to surface a single named failure mode. Per-call `try/finally` closes connections cleanly.
- **Pluggable backend.** `EMAIL_BACKEND=gmail` is reserved for a future Gmail-API + OAuth backend (currently `NotImplementedError`); the seam is wired so v1.1 lands without breaking changes.
- **Test discipline.** 25 tests offline via `MagicMock` on `IMAP4_SSL` and `SMTP_SSL`; canned RFC822 fixtures built from real `EmailMessage`. The full suite is 172 tests passing in ~0.67s.

The shipping of `email.send` is theoretically significant: it is the first stdlib neuro whose effect crosses an irreversible threshold (an SMTP send cannot be unsent). It thus tests whether the framework's effect-tracking discipline holds at the boundary where agent autonomy meets external consequence. The current implementation tags `send` as `effect="tool"`, which is correct under the seven-effect taxonomy (Section 5) but suggests a future refinement: a dedicated `EXTERNAL` effect for irreversible outbound actions, propagating functorially through composition so that planners and humans-in-the-loop can identify the exact dimension at which a flow becomes un-replayable.

### 8.2 Why a Stdlib Matters

The thesis embedded in the stdlib's growth is **unit economics**: each new neuro is a vocabulary atom that the NL compiler can compose. Adding `email.send` does not just add the ability to send mail — it adds the ability for the planner to *route to* `email.send` automatically when a user prompt implies it. With the planner's catalog filter, `email.search` becomes a tool the agent can choose, and combined with `agent.delegate`, a flow can decide *mid-run* that it needs to send mail and do so without further user intervention.

The composition algebra (`|`, `&`, `+`) means that *n* stdlib neuros yield combinatorially many runnable flows. A research agenda becomes plottable as a flow-vocabulary growth curve.

---

## 9. The Long Bet: Neural Networks Are NeuroNets

The most ambitious extension of the framework — not yet implemented, but research-active in `docs/RESEARCH_BRAINSTORM_CATEGORICAL_TRAINING.md` — is the claim that the same dimensional ladder applies *inside* trained neural networks.

### 9.1 The Categorical Decomposition of a Transformer

If the dimensional ladder of Section 3.2 is applied to a Transformer architecture:

| Transformer Component | Categorical Dimension | Categorical Role |
|---|---|---|
| Token embedding vector | Dim 0 — Object | A vector in the representation space |
| Single attention head | Dim 1 — Morphism | An arrow mapping queries to weighted values |
| Multi-head attention | Dim 2 — Functor | A functor over the category of heads; applies each head and merges |
| Layer normalisation | Dim 2 — Natural transformation | Normalises uniformly across all representations |
| Residual connection | Dim 2 — Natural transformation | η : Id ⇒ F — the identity-plus-transformation structure |
| Encoder-decoder cross-attention | Dim 2 — Adjunction (conjectured) | Relates encoder and decoder representation categories |
| The full transformer stack | Dim 1 — Composed morphism | Sequential composition of layer-arrows |
| Architecture search (NAS) | Dim 3 — 2-arrow | A morphism *between* architectures |
| A training loop | Dim 3 — 2-arrow | Endomorphism on the space of model parameters |

Table 8 — A Transformer, dimensionally classified.

Each row is a precise mathematical claim. The sum of the rows is the meta-claim:

> **A trained neural network is a NeuroNet — that is, a typed, dimensionally-classified categorical object — written in NeuroLang.**

### 9.2 What This Enables

If correct, the categorical decomposition admits four families of optimisations, surveyed in `RESEARCH_BRAINSTORM_CATEGORICAL_TRAINING.md`:

**(a) Shared substructure across layers (Dim 1 factorisation).** Empirically (Geva et al., Elhage et al.), adjacent transformer layers have similar weight eigenstructure. Categorically, these layers are *naturally isomorphic*: there exists a natural transformation between them. Identifying the transformation enables principled parameter sharing — a categorical interpretation of LoRA, Tied-LoRA, and TensLoRA.

**(b) Functorial gradient flow (Dim 2 optimisation).** Multi-head attention is functorial; backpropagation through a functor is itself a functor (Cruttwell et al. 2022). Gradient computation can therefore be decomposed along functorial boundaries — each functor boundary being a natural point for gradient checkpointing or parallel gradient computation.

**(c) Categorical compression (Dim 0 quotients).** Each tensor decomposition (Tucker, CP, TT) is a categorical quotient. The categorical view tells us *which* quotients are semantics-preserving — those that commute with the layer's morphism role — guiding pruning and quantisation principled rather than heuristic.

**(d) Quantum-inspired contraction (string diagram ↔ tensor network).** The forward pass of a transformer is a tensor network contraction. Tensor-network methods from quantum physics (MPS, MERA, DMRG) provide optimal contraction orders; minimum-cost contraction is an NP-hard combinatorial optimisation problem with structural shortcuts in low-rank regimes. This is the sense in which NeuroLang is "quantum-inspired": not quantum hardware, but quantum *algorithms* for finding optimal ways to contract the tensor network that *is* the neural network.

### 9.3 The Practical Vision

A NeuroLang user could one day load a PyTorch model into the framework, and the system would:

1. Decompose it into typed categorical components (Dim 0 / 1 / 2 / 3).
2. Render it as a string diagram = tensor network.
3. Identify redundant structure (natural isomorphisms between layers).
4. Suggest optimisations (parameter sharing, pruning, factorisation).
5. Re-export an optimised model.

This is a bridge between *agentic programming* (the framework's primary surface) and *model engineering* (a much larger market). The same framework that lets a user write `web.search | reason.summarize` would let a researcher write `attention_head | layer_norm | residual` — both expressions inhabiting the same categorical structure.

---

## 10. Discussion

### 10.1 What Is Genuinely New

NeuroLang's novelty resides not in any single primitive (each has antecedents in the literature) but in their **systematic combination under one dimensional ladder**:

- **Plans as first-class values** — DSPy has compiled programs but not plan-as-data; LangChain has runtime state but not inspectable plans.
- **Effects as types with budget** — Pydantic AI has structured outputs but not effect-typing of compositions.
- **Bidirectional cached NL ↔ code** — DSPy's signatures are forward-only; LangChain has no NL surface.
- **Categorically grounded composition** — none of the three has the categorical contracts (associativity, identity, naturality) as enforced laws.
- **Recursive composition (`agent.delegate`)** — flows that spawn flows, with depth budgeting, catalog scoping, and memory inheritance — appears, to our knowledge, novel.
- **Catalog-aware planning** — the user's installed neuro vocabulary informs the planner at the moment of the call.
- **Adjunction-grounded cache** — the cache is not a performance hack but a mathematical commitment.

### 10.2 What Is Provisional

We make no claim that the framework is complete. The following are research questions that the construction will surface and force decisions on (RESEARCH.md §10):

1. **Canonical normal form.** What is the unique canonical form of a Layer-2 program used as the cache key? Likely: a normal form in the underlying free symmetric monoidal category.
2. **Effect-differentiability composition.** Some effects (LLM call, tool) are not classically differentiable. The right semantics for differentiating *through* an effectful flow is open. Likely: REINFORCE / score-function for non-differentiable effects, plus structured priors for LLM-call gradients.
3. **Type system depth.** Hindley–Milner is too weak; full dependent types are too heavy for users. The likely sweet spot is a refinement-typed system with categorical kinds, similar to Liquid Haskell or Idris-with-restraint.
4. **Long-lived agents.** A neuro that runs for days has lifecycle, persistent memory, and restart semantics. This likely fits as an *indexed monad over time*, or a coalgebraic treatment.
5. **Multi-NL parity.** Does Hindi-authored NL produce identical formal programs as English-authored NL? Probably yes for code; but NL summaries should remain language-faithful.

### 10.3 Risks

The principal risks are:

- **LLM-compiler reliability.** The adjunction holds in the limit; in practice, LLMs produce flawed translations. The framework surfaces these (via failed triangle identities) and lets users correct, with corrections caching. But the user experience depends on this loop being short.
- **Adoption friction.** A framework that requires users to think categorically is harder to evangelise than one that does not. Our bet is that the *output* feels like Python, even if the *internals* are categorical.
- **Competitive pressure.** LangChain, DSPy, and Pydantic AI are well-funded and rapidly evolving. NeuroLang's differentiator (categorical grounding + NL surface + recursive composition) must continue to outpace incremental improvements in those frameworks.

---

## 11. Implementation Status

As of Phase 1.9 (2026-04-28):

| Phase | Deliverable | Status |
|---|---|---|
| 1.0 — Categorical core | `Neuro`, `Flow`, `Plan`, `Memory`, `Effect`, `Budget`, `Recovery`, `Registry`, `LocalNeuroNet`, Mermaid + discopy rendering | ✓ shipped |
| 1.1 — NL ↔ Python compiler | `compile_source`, `decompile_summary`, file cache, CLI | ✓ shipped |
| 1.5 — Discover + strict + plan | Eager FS scan, strict reference validation, `propose_plan`, `suggest`, CLI `plan` subcommand | ✓ shipped |
| 1.6 — Architectural cleanup | Public renames, `_providers.py` extraction, kind-aware provider callables | ✓ shipped |
| 1.6b — Multi-provider | opencode-zen, openrouter, openai, anthropic, ollama; `DEFAULT_LLM_PROVIDER` env | ✓ shipped |
| 1.6c — REPL | `NeuroLangConsole`, `:plan`/`:compile`/`:catalog`, async displayhook, persistent history | ✓ shipped |
| 1.7 — Cache fingerprint | `make_key` includes system_fingerprint + catalog hash | ✓ shipped |
| 1.8 — `agent.delegate` | Recursive composition, depth budget, catalog scoping, memory inheritance | ✓ shipped |
| 1.9 — Email stdlib | `email.{send, read, search, mark}`, IMAP/SMTP, domain auto-detect, EmailError | ✓ shipped |
| 2.x — Calendar / voice / coding agent | Google Calendar, LiveKit/Twilio, code.* neuros for self-hosted coding | planned |
| 2.x — JAX backend | Differentiable substrate; HD vectors; soft-attention memory | planned |
| 2.x — Multi-NL input | Hindi compilation; canonical-form cache | planned |
| 3.x — 3D IDE / Neurocomputer | WebGL string-diagram editor; voice input; drag manipulation; per-dimension visualisation | planned |
| 3.x — Mech-interp neuros | `code.parse_ast`, model decomposition, natural-isomorphism detection | planned |
| 4.x — Self-hosting | The compiler is itself a NeuroLang program | planned |

The codebase currently passes **172 offline tests in approximately 0.67 seconds**, including 25 tests for the email stdlib shipped in Phase 1.9. The repository is at `git@github.com:neurocomputer-in/neurolang.git` (private during pre-alpha).

---

## 12. Conclusion: The Bet

We close with the bet, stated plainly:

> **There is one mathematical structure underneath grammar, logic, computation, neural networks, and physics. It is the higher-categorical / tensor-network / string-diagrammatic structure. A language that exposes this structure as primitive — not as library, not as DSL on top of Python — will dominate the design of agentic systems for the next two decades.**

If the bet is right, NeuroLang is to agentic computing what:

- **SQL** was to databases,
- **Lisp** was to symbolic AI,
- **Solidity** was to blockchain,
- **Erlang** was to telephony.

A purpose-built framework for a domain whose primitives general-purpose languages systematically obscure.

If the bet is wrong, NeuroLang is a beautiful experiment that leaves a small open-source legacy and teaches its authors a great deal.

**Either outcome is acceptable. The bet is worth making.**

---

## References

### Foundational

- Atiyah, M. (1988). *Topological Quantum Field Theories.* Publications Mathématiques de l'IHÉS.
- Coecke, B., Sadrzadeh, M., Clark, S. (2010). *Mathematical Foundations for a Compositional Distributional Model of Meaning.* Linguistic Analysis.
- Cruttwell, G. S. H., Gavranović, B., Ghani, N., Wilson, P., Zanasi, F. (2022). *Categorical Foundations of Gradient-Based Learning.*
- Curry, H. B., Feys, R. (1958). *Combinatory Logic.*
- Fong, B., Spivak, D. I., Tuyéras, R. (2019). *Backprop as Functor.*
- Gavranović, B. (2024). *Fundamental Components of Deep Learning: A Category-Theoretic Approach.* PhD thesis.
- Howard, W. A. (1969). *The Formulae-as-Types Notion of Construction.*
- Joyal, A., Street, R. (1991). *The Geometry of Tensor Calculus.*
- Lambek, J. (1958). *The Mathematics of Sentence Structure.*
- Lurie, J. (2009). *Higher Topos Theory.*
- Penrose, R. (1971). *Applications of Negative Dimensional Tensors.*
- Selinger, P. (2009). *A Survey of Graphical Languages for Monoidal Categories.*

### Deep Learning, Mechanistic Interpretability, Geometric Deep Learning

- Bronstein, M. M., Bruna, J., Cohen, T., Veličković, P. (2021). *Geometric Deep Learning: Grids, Groups, Graphs, Geodesics, and Gauges.*
- Cohen, T., Welling, M. (2016). *Group Equivariant Convolutional Networks.* ICML.
- Elhage, N., et al. (2022). *Toy Models of Superposition.* Anthropic.
- Hu, E. J., et al. (2021). *LoRA: Low-Rank Adaptation of Large Language Models.* Microsoft.
- Kornblith, S., Norouzi, M., Lee, H., Hinton, G. (2019). *Similarity of Neural Network Representations Revisited.* ICML.
- Novikov, A., Podoprikhin, D., Osokin, A., Vetrov, D. (2015). *Tensorizing Neural Networks.* NeurIPS.
- Raghu, M., Gilmer, J., Yosinski, J., Sohl-Dickstein, J. (2017). *SVCCA: Singular Vector Canonical Correlation Analysis.*
- Stoudenmire, E. M., Schwab, D. J. (2016). *Supervised Learning with Quantum-Inspired Tensor Networks.* NeurIPS.
- Anthropic (2024). *Scaling Monosemanticity.*

### Hyperdimensional Computing & Vector Symbolic Architectures

- Kanerva, P. (2009). *Hyperdimensional Computing.*

### Frameworks and Comparative Systems

- Chase, H. (2022). *LangChain.*
- Khattab, O., et al. (2023). *DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines.*
- Pydantic (2024). *Pydantic AI.*

### Project Documents (NeuroLang Repository)

- `docs/RESEARCH.md` — the original research / construction document.
- `docs/ARCHITECTURE.md` — the canonical Python-framework architecture.
- `docs/VISION.md` — early vision document.
- `docs/COMPARISON.md` — capability axes vs. competitors.
- `docs/LITERATURE_REVIEW_CATEGORICAL_DL.md` — six-thread survey of related work.
- `docs/RESEARCH_BRAINSTORM_CATEGORICAL_TRAINING.md` — the *Neural Networks Are NeuroNets* programme.
- `docs/STATUS.md` — phase-by-phase implementation status.
- `docs/superpowers/specs/2026-04-28-email-stdlib-design.md` — Phase 1.9 design spec.

---

*Document maintained at `/docs/PAPER_NEUROLANG_FOUNDATIONS.md` in the `neurolang` repository. Compiled 2026-04-28 to consolidate the project's theoretical commitments and implementation status into a single research-paper section. This is a living document; sections will be revised as the construction proceeds and the research questions of Section 10.2 are settled.*
