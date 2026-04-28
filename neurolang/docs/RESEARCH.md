# NeuroLang — Deep Research and Construction Path

> **Title:** A Differentiable, Higher-Categorical Language for Cognitive Systems
> **Status:** Pre-alpha research document. Captures the theoretical commitments + the construction path. Not yet implementation.

---

## 0. Thesis

NeuroLang is the language whose programs are simultaneously:

1. **Symbolic** — typed, inspectable, composable, deterministic where it matters.
2. **Neural** — differentiable, integrable, learnable end-to-end.
3. **Categorical** — higher-dimensional, structurally sound, composable at every level.
4. **Linguistic** — addressable in natural language (Hindi, English, …), with a cached bidirectional compiler.

A NeuroLang program is, mathematically, **a string diagram in a higher category** that doubles as **a hyperdimensional tensor graph**. These are not two views — they are the same object, because the higher-categorical formalism and the tensor-network formalism are mathematically identified.

Every primitive lives at a definite dimension on the categorical ladder. Every primitive is differentiable. Every primitive is decomposable into smaller primitives down to the substrate. Every primitive has a natural-language surface form, cached.

This is the foundation. The rest of this document derives the architecture from it.

---

## 1. The Three-Tower Identification

Three apparently distinct domains turn out to be the same mathematical structure:

| **Natural Language (Grammar)** | **Category Theory** | **Computation / Tensor Network** |
|--------------------------------|---------------------|----------------------------------|
| Noun | Object (dim 0) | Tensor index / vector slot |
| Verb | Morphism (dim 1) | Linear map / tensor contraction |
| Adverb | Natural transformation (dim 2) | Higher-order tensor operation |
| Sentence | Composed arrow / commutative diagram | Computation graph |
| Paragraph | Diagram in a category | Module of computation |
| Translation | Equivalence of categories | Reparameterization |
| Grammar itself | Category of grammatical types (Lambek) | Type system of the network |

This identification is rigorously established in:

- **Lambek (1958)** — grammatical types form a residuated monoid (a categorical structure); parsing is composition in this category.
- **Curry–Howard (1934, 1969)** — proofs ≅ programs; types ≅ propositions.
- **Curry–Howard–Lambek** — a three-way correspondence between programs, proofs, and grammatical compositions.
- **Coecke, Sadrzadeh, Clark (2008–)** — DisCoCat: distributional compositional categorical semantics, using the same mathematics as categorical quantum mechanics to do compositional NLP.
- **Penrose tensor diagrams (1971)** — string diagrams for tensor algebra are the same string diagrams as for monoidal categories.
- **Atiyah–Lurie cobordism hypothesis** — TQFT is an n-functor between cobordism categories and a target category. Physics IS higher-categorical.
- **Cruttwell, Gavranović, et al. (2022)** — categorical foundations of gradient-based learning. Backprop is a functor.

NeuroLang is the systematic exploitation of this triple identification for the design of a programming language.

---

## 2. The Dimensional Architecture

NeuroLang's primitives are organized strictly by their categorical dimension. A primitive may not be introduced unless its dimension is justified.

### Dimension 0 — Substrate
- **Values, tensors, hyperdimensional vectors** (Kanerva-style 10⁴-dim binary or real vectors with binding/bundling/permutation operators).
- **Memory cells** (typed, possibly compressed, possibly differentiable).
- **Atomic propositions / facts.**

### Dimension 1 — Arrows
- **Functions** (deterministic transforms).
- **Differentiable maps** (gradient-aware).
- **State transitions.**
- **Boolean and fuzzy implications.**
- **Effects** (`pure`, `llm`, `tool`, `human`, `time`) — each effect is an arrow in a particular sub-category.

### Dimension 2 — Functors and Natural Transformations
- **Higher-order functions, generics, monads.**
- **Adverbial modifiers** (a flow modulated by another flow).
- **Plans-as-values** — first-class structured plans, manipulable as data.
- **Memory scopes** (read/write declarations as functorial constraints).
- **Compositional flows** (sequential / parallel / DAG / loop).

### Dimension 3 — 2-Categories and Coherence
- **Plan transformations** — operations that rewrite plans.
- **Protocol transformations** between agents.
- **Effect handlers** that reinterpret effects.
- **Optimization passes** — gradient-based or symbolic refactoring of programs as 2-arrows.

### Dimension ∞ — Reflection and Self-Modification
- **Meta-neuros** that read, transform, and emit other neuros.
- **The compiler itself** as a NeuroLang program.
- **Learning loops** that modify the language's own primitives.

> **Design rule:** A primitive may be added at dimension *n* only if it cannot be expressed cleanly at dimension *n−1* without loss of structure.

---

## 3. Code as Hyperdimensional Tensor Graph

Every NeuroLang program compiles to a **typed, weighted, dimensioned graph** with the following properties:

- **Nodes** are neuros (typed units).
- **Edges** are typed data flows. Edge types may be tensors of arbitrary shape.
- **Composites** appear at every level: a node may itself be a graph (a composite). Composites of composites of composites are first-class — there is no "atomic" level that the user must reach. The language is *fractally compositional*.
- **Tensor structure** carries the semantic state through the graph. Each edge may carry a hyperdimensional vector or a low-rank tensor; each node may transform those tensors.
- **Differentiable everywhere it makes sense.** Every numerical computation participates in autodiff. Every learnable parameter is a node attribute.
- **Integrable.** Programs that represent functions over continuous domains support definite integration as a primitive operation, not a derived library call.
- **Decomposable.** Every node has a canonical factorization into smaller nodes, recursively, down to the substrate primitives.

This is what makes a NeuroLang program a *neural network in disguise* — but a neural network with **typed structure**, **categorical guarantees**, and **symbolic inspectability** that contemporary ML systems lack.

### Why this works

The fundamental lemma is the **isomorphism between string diagrams and tensor networks**, established by Penrose and formalized in the categorical-quantum-mechanics tradition:

> *A morphism in a monoidal category, drawn as a string diagram, is the same mathematical object as a tensor network.*

So when the user composes neuros into a flow, the diagram they construct is *literally* a tensor network. When the system trains, gradients flow through that network. When the user inspects, the same network is rendered as a categorical diagram. **No translation. No two systems. One object.**

---

## 4. The Differentiable Substrate

Every primitive in NeuroLang declares whether it supports:

| Capability | Required for | Mechanism |
|-----------|--------------|-----------|
| Forward execution | All primitives | Standard interpretation |
| Reverse-mode gradient | Differentiable primitives | Autodiff (JAX/PyTorch under the hood) |
| Forward-mode gradient | Sensitivity analysis | Optional |
| Definite integration | Continuous flows | Symbolic + numeric quadrature |
| Symbolic factorization | Decomposable primitives | Rewrite rules (categorical 2-arrows) |
| Hyperdimensional binding | Vector-symbolic primitives | Kanerva's binding/bundling |

The language enforces these declarations at the type level. A flow composed of differentiable primitives is itself differentiable, *automatically and provably*. A flow containing a non-differentiable primitive cannot be inserted into a gradient-based learning loop without an explicit handler.

This is **categorical functoriality of differentiability** — established in Cruttwell et al.'s work on the category of differentiable programs.

---

## 5. The Memory Hierarchy

Memory in NeuroLang is itself a categorical structure, organized as a hierarchy:

| Layer | Kind | Properties |
|-------|------|-----------|
| **Discrete** | Key–value, exact | Determinism, fast lookup, brittle |
| **Differentiable** | Soft attention store | Gradient flow through recall |
| **Compressed** | Sparse / low-rank / quantized | Capacity vs precision trade |
| **Hyperdimensional** | High-dim vectors with binding/bundling | Compositional, fault-tolerant, semantic |
| **Episodic** | Time-indexed | Sequence of experiences, retrievable by recency or relevance |
| **Semantic** | Concept-indexed | Long-term abstracted knowledge |
| **Procedural** | Skill-as-flow | Memory that executes |

Each layer is a *functor* into the substrate. They compose: a single read may pass through compressed → semantic → episodic before yielding a vector. Each transition is a typed arrow with cost and effect annotations.

Memory itself is **decomposable** — any compound memory can be factored into a tensor product or coproduct of simpler memories, and the language's optimizer can discover and exploit such factorizations.

---

## 6. The Logic Layer — Decomposable, Multi-Valued

NeuroLang does not commit to one logic. It admits a hierarchy:

| Logic | Truth values | Use |
|-------|--------------|-----|
| Boolean | {true, false} | Hard constraints, deterministic flow |
| Fuzzy | [0, 1] | Soft constraints, partial matches |
| Probabilistic | distributions | Bayesian inference, uncertainty propagation |
| Modal | possible-world indexed | Counterfactuals, planning |
| Higher-order | predicates of predicates | Meta-reasoning |
| Linear | resource-aware | Effect tracking, single-use credentials |

Every logical expression in NeuroLang is **decomposable** — it factors uniquely (up to canonical isomorphism) into a tree of primitive operators over atomic propositions. This is the categorical analogue of conjunctive normal form, but it works for all the logics above, because each logic is a category whose objects are propositions and whose arrows are inferences.

A consequence: **the symbolic and the neural meet in the logic layer.** A fuzzy logical formula is differentiable. A probabilistic formula admits gradient-based posterior inference. A Boolean formula is the deterministic limit of these. The user writes one expression; the runtime chooses the appropriate semantics.

---

## 7. The Two-Layer Language Surface (Refined)

Refining the vision document with the categorical machinery now in hand:

### Layer 1 — Natural Language
- A category whose objects are *intents* and whose arrows are *inferences in natural language* (paraphrase, entailment, qualification).
- Inhabited in any human language; the LLM compiler normalises.

### Layer 2 — Formal NeuroLang
- A category whose objects are *typed neuros and tensors* and whose arrows are *typed flows*.
- Inhabits the higher-categorical structure described in Section 2.
- Renders as a string diagram = tensor network.

### The Compiler — An Adjoint Pair of Functors

```
              left-adjoint:  L : NL → Formal     (compile)
                                ⊣
              right-adjoint: R : Formal → NL     (summarise)
```

- **Unit** of the adjunction: `η : 1_NL ⇒ R∘L` — every NL prompt round-trips through formal compilation back to a normalised NL summary. The cache stores `η` per prompt.
- **Counit** of the adjunction: `ε : L∘R ⇒ 1_Formal` — every formal program round-trips through summarisation back to an executable program. The cache stores `ε` per program.
- **Adjunction laws** (triangle identities) impose self-consistency: compile-then-summarise is identity-up-to-cache; summarise-then-compile is identity-up-to-cache.

This is not metaphor. It is the precise mathematical contract that the LLM compiler must satisfy. Caching is no longer a performance optimization — it is the *unit and counit data* of the adjunction, made into storage.

A consequence: when the LLM model changes (new version), the cache is invalidated, but **only the parts whose adjunction-coherence breaks**. This is verifiable. It is far stronger than "rebuild on new model" — it is *categorically principled cache invalidation*.

---

## 8. The 3D IDE — Per-Dimension Visualisation

Each categorical dimension has a *canonical* visual rendering. The 3D IDE chooses the rendering by the dimension of the structure being shown.

| Dimension | Visual | Render | User interaction |
|-----------|--------|--------|------------------|
| 0 | Spheres / nodes | 3D points in space | Tap to inspect type, edit value |
| 1 | Strings / arrows | Lines between nodes (string diagrams) | Drag endpoints; voice command "wire X to Y" |
| 2 | Surfaces | Filled regions between strings (2-cells) | Pinch to deform; "this should also work for Z" |
| 3 | Volumes | 3D solids (3-cells) | Rotate to inspect; "rewrite this protocol as that one" |
| ∞ | Animated, temporal | Time-evolving renderings | Scrub timeline; "show me how this evolved over training" |

**String diagrams in 3D** (the canonical visual notation for higher categories, established by Joyal–Street, Selinger, and others) **are also tensor networks**. The user is editing a diagram; the system is editing a tensor graph. Same object.

### IDE Interactions

The IDE supports three interaction modes, all editing the same underlying object:

1. **NL command** — "add a step that filters unread emails after the fetch step." The LLM compiler edits the formal layer; the diagram updates.
2. **Direct manipulation** — drag, drop, wire. The diagram updates; the formal layer updates; the NL summary regenerates.
3. **Code editing** — open the formal NeuroLang text. Edit. The diagram and NL update.

All three modes are co-equal. The cache (sec. 7) keeps them coherent. The user can speak Hindi to the IDE, drag a 3D block with a finger, and edit text in vim — *all at once*, on *the same program*.

### Composites of Composites of Composites

A node in the 3D IDE is itself a sub-graph. Tap to drill in. The sub-graph is itself made of nodes, each a sub-sub-graph. The fractal compositionality from Section 3 means *there is no atomic floor* — the user can always go deeper. At each level, the rendering matches the dimension of the structure at that level.

---

## 9. The Construction Path

A disciplined four-phase build, each phase yielding usable software.

### Phase 1 — Categorical Core (months 1–3)

**Goal:** A small, working interpreter for the formal layer. No NL, no IDE, no learning. Just the algebra.

- Define `Neuro`, `Flow`, `Plan`, `Effect`, `Memory`, `Budget` as Python classes with categorical contracts.
- Implement the composition operators (sequential, parallel, DAG, loop) as monoidal-category constructions.
- Implement effect tracking via free monad over an effect signature.
- String-diagram visualization via existing libraries (`discopy`, `tikz-cd`, or `manim`).
- Reference test suite: every categorical law (associativity, identity, naturality) is a property test.

**Deliverable:** `pip install neurolang` gives a Python library with `from neurolang import Neuro, Flow, ...` and runnable examples.

### Phase 2 — Differentiable Substrate (months 3–6)

**Goal:** Programs run end-to-end through autodiff.

- Wire JAX (preferred) or PyTorch under the categorical interface.
- Hyperdimensional substrate: implement `HDVector` with bind/bundle/permute operators.
- Memory hierarchy (Section 5) implemented at three layers (discrete, differentiable, hyperdimensional).
- Logic layer (Section 6) — at least Boolean + fuzzy + probabilistic — with gradient flow.
- Functorial differentiability check: any flow composed only of differentiable primitives is itself differentiable, type-checked.

**Deliverable:** A NeuroLang program can be trained end-to-end. Example: a small agent that learns to plan via gradient descent on a flow's parameters.

### Phase 3 — NL Compiler (months 6–9)

**Goal:** Bidirectional NL ↔ formal compilation, cached.

- Forward (`L`): NL → formal NeuroLang via prompted LLM, schema-constrained output.
- Reverse (`R`): formal → NL summary via prompted LLM.
- Cache schema: keyed by canonical formal-program hash *and* model version.
- Triangle-identity tests: round-trip consistency assertions on the cache.
- Multi-language NL: the formal layer is language-neutral; the cache is keyed by the *normalised* NL canonical form (English by convention), not the surface utterance.

**Deliverable:** `compile("summarise last week's emails")` produces an executable formal flow; `summarise(flow)` produces an English (or Hindi, etc.) description.

### Phase 4 — 3D IDE (months 9–12)

**Goal:** A working 3D IDE that lets users author, inspect, and run NeuroLang programs.

- WebGL / Three.js front-end.
- String-diagram rendering with per-dimension visualisation (Section 8).
- Voice input → NL compiler → formal layer → diagram update.
- Direct manipulation (drag, wire) → formal-layer mutation → NL re-summarisation.
- Drill-in to composites; fractal navigation.

**Deliverable:** A user can sit at the IDE, speak in any language, see a 3D diagram emerge, edit it by hand, and run it.

### Phase 5 — Self-Hosting and Evolution (year 2+)

**Goal:** The language begins to evolve itself.

- The LLM compiler is itself a NeuroLang program (a meta-neuro).
- Learning loops adjust primitive weights, propose new primitives.
- The IDE is implemented in NeuroLang — closing the loop.

**Deliverable:** A language that improves itself. This is the long horizon.

---

## 10. Open Research Questions

These are the questions the construction will surface and force decisions on. They are not blockers; they are markers of the frontier.

1. **Canonical normal form.** What is the unique canonical form of a formal NeuroLang program, used as the cache key? Likely: a normal form in the underlying free symmetric monoidal category.
2. **Determinism vs creativity in the compiler.** When the LLM compiler is faced with NL ambiguity, does it ask, sample, or commit? Probably: ask if confidence < threshold; cache the resolution.
3. **Effect–differentiability composition.** Some effects (LLM call, tool) are not classically differentiable. What is the right semantics for differentiating *through* an effectful flow? Likely: REINFORCE / score-function for non-differentiable effects, plus structured priors for LLM-call gradients.
4. **Type system depth.** Classical Hindley–Milner is too weak. Dependent types are too heavy for users. The likely sweet spot: a refinement-typed system with categorical kinds, similar to Liquid Haskell or Idris-with-restraint.
5. **Long-lived agents.** A neuro that runs for days has lifecycle, persistent memory, restart semantics. How does this fit the categorical framework? Likely: an *indexed monad* over time, or a coalgebraic treatment.
6. **Multi-natural-language parity.** Does Hindi-authored NL produce identical formal programs as English-authored NL? *Should* it? Probably yes for code; but the NL summaries should remain language-faithful (re-summarise into the user's language).
7. **What to do when the LLM is wrong.** The compiler's adjunction holds in the limit. In practice, the LLM produces flawed translations. The architecture must surface these (via failed triangle identities) and let the user correct, with the correction caching.
8. **Compositional learnability.** When a flow is trained, gradients flow through some primitives and not others. The system must signal where learning is happening and where it is fixed. Probably: a *learnability index* on each primitive, propagated functorially.

---

## 11. The Bet

The bet of NeuroLang, made plain:

> **There is one mathematical structure underneath grammar, logic, computation, neural networks, and physics. It is the higher-categorical / tensor-network / string-diagram structure. A language that exposes this structure as primitive — not as library, not as DSL on top of Python — will dominate the design of agentic systems for the next two decades.**

If the bet is right, NeuroLang is to agentic computing what:
- **SQL** was to databases.
- **Lisp** was to symbolic AI.
- **Solidity** was to blockchain.
- **Erlang** was to telephony.

A purpose-built language for a domain whose primitives general-purpose languages systematically obscure.

If the bet is wrong, NeuroLang is a beautiful experiment that taught its authors a great deal and left a small open-source legacy.

Either outcome is acceptable. **The bet is worth making.**

---

## 12. References (curated, foundational)

- Lambek, J. *The Mathematics of Sentence Structure.* (1958)
- Curry, H. B. & Feys, R. *Combinatory Logic.* (1958)
- Howard, W. A. *The Formulae-as-Types Notion of Construction.* (1969)
- Penrose, R. *Applications of Negative Dimensional Tensors.* (1971)
- Joyal, A. & Street, R. *The Geometry of Tensor Calculus.* (1991)
- Coecke, B., Sadrzadeh, M., Clark, S. *Mathematical Foundations for a Compositional Distributional Model of Meaning.* (2010)
- Selinger, P. *A Survey of Graphical Languages for Monoidal Categories.* (2009)
- Lurie, J. *Higher Topos Theory.* (2009)
- Univalent Foundations Program. *Homotopy Type Theory.* (2013)
- Cruttwell, G. S. H., Gavranović, B., et al. *Categorical Foundations of Gradient-Based Learning.* (2022)
- Kanerva, P. *Hyperdimensional Computing.* (2009)
- Bradley, T.-D. *What is Applied Category Theory?* (2018)
- Atiyah, M. *Topological Quantum Field Theories.* (1988)
- Lurie, J. *On the Classification of Topological Field Theories.* (2009) — cobordism hypothesis.

---

*Document maintained at `/docs/RESEARCH.md` in the `neurolang` repository. Pre-alpha. To be expanded as construction proceeds.*
