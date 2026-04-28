# Research Brainstorm — Neural Networks Are NeuroNets: The Categorical Decomposition of Deep Learning

> **Status:** Early brainstorm. Not part of any current phase. Captures a research direction for investigation.
> **Date:** 2026-04-27

---

## 0. The Core Thesis

**Neural networks should not be treated as black boxes.**

NeuroLang's RESEARCH.md establishes a dimensional ladder for programs:

| Dimension | In NeuroLang (programs) | In a Neural Network (models) |
|-----------|------------------------|------------------------------|
| **Dim 0 — Substrate** | Values, tensors, HD vectors, memory cells | Weights, activations, embeddings, attention scores |
| **Dim 1 — Arrows** | Functions, differentiable maps, state transitions | Individual layers (Linear, Conv, Attention head), activation functions |
| **Dim 2 — Functors / NatTrans** | Higher-order functions, plans-as-values, flows | Multi-head attention (functor over heads), skip connections (natural transformations), residual blocks |
| **Dim 3 — 2-Categories** | Plan transformations, optimization passes | Architecture search (NAS), pruning strategies, knowledge distillation |
| **Dim ∞ — Reflection** | Meta-neuros, self-modifying compiler | Self-modifying architectures, neural architecture search, learned optimizers |

**The claim:** A transformer, a diffusion model, or any deep network has categorical structure at every dimension — just like a NeuroLang program. If we identify this structure, we can:

1. **Decompose** the model into typed, categorical components
2. **Share computation** between components at the same categorical dimension
3. **Optimize training** by exploiting functorial structure (gradient flow respects the categorical decomposition)
4. **Compress** models by factoring out shared substructure (categorical quotients)

---

## 1. The Three-Tower Identification Applied to Neural Networks

RESEARCH.md establishes three equivalent views of the same structure:

| Natural Language | Category Theory | Computation / Tensor Network |
|---|---|---|
| Noun | Object (dim 0) | Tensor index |
| Verb | Morphism (dim 1) | Linear map |
| Adverb | Natural transformation (dim 2) | Higher-order tensor op |

**Applying this to a Transformer:**

| Transformer Component | Categorical Dimension | Categorical Role |
|---|---|---|
| Token embedding vector | Dim 0 — Object | A vector in the representation space |
| Single attention head | Dim 1 — Morphism | An arrow mapping queries to weighted values |
| Multi-head attention | Dim 2 — Functor | A functor over the category of heads; applies each head and merges |
| Layer normalization | Dim 2 — Natural transformation | A natural transformation that normalizes *across* all representations uniformly |
| Residual connection | Dim 2 — Natural transformation | `η : Id ⇒ F` — the identity-plus-transformation structure |
| Encoder-Decoder cross-attention | Dim 2 — Adjunction? | Relates two representation categories (encoder space ↔ decoder space) |
| The entire transformer stack | Dim 1 — Composed morphism | Sequential composition of layer-arrows |
| Architecture search (NAS) | Dim 3 — 2-arrow | A morphism *between* architectures (rewriting one model into another) |
| A training loop | Dim 3 — 2-arrow | An endomorphism on the space of model parameters |

**This is not metaphor.** Each row is a precise mathematical claim. If correct, each row enables specific optimizations.

---

## 2. What This Enables — Concrete Optimizations

### 2a. Shared Substructure Across Layers (Dim 1 Factorization)

**Observation:** In many transformers, adjacent layers have weight matrices with similar eigenstructure (empirically observed by Geva et al., Elhage et al.).

**Categorical interpretation:** These layers are *naturally isomorphic* — there exists a natural transformation between them. If we identify it, we can:
- **Share parameters** between naturally isomorphic layers (reducing model size)
- **Factor** the transformation into a base layer + a small perturbation (low-rank adaptation — this is what LoRA does empirically; the categorical view gives it theoretical grounding)

### 2b. Functorial Gradient Flow (Dim 2 Optimization)

**Observation:** Multi-head attention is a functor: it maps each head (a morphism) to its output, then merges. Backprop through this structure should respect the functorial decomposition.

**Categorical interpretation:** "Backprop as Functor" (Cruttwell, Gavranović et al., 2022) — already cited in RESEARCH.md — proves that reverse-mode differentiation is itself a functor. If the *model* is also described functorially, then:
- Gradient computation can be **decomposed along functorial boundaries**
- Each functor boundary is a natural point for **gradient checkpointing**
- Functorial structure enables **parallel gradient computation** by processing each functor image independently

### 2c. Categorical Compression (Dim 0 Quotients)

**Observation:** Tensor decomposition (Tucker, CP, Tensor Train) reduces storage and computation by factoring weight tensors.

**Categorical interpretation:** Each decomposition is a *categorical quotient* — identifying equivalent elements. The categorical view tells us *which* quotients are semantics-preserving (those that commute with the layer's morphism role). This could guide:
- **Principled pruning** (remove components that are categorically redundant — i.e., naturally isomorphic to the identity)
- **Principled quantization** (quantize along dimensions where the categorical structure is preserved)

### 2d. Quantum-Inspired Speedups (String Diagram ↔ Tensor Network)

**Observation:** RESEARCH.md already states: "A morphism in a monoidal category, drawn as a string diagram, is the same mathematical object as a tensor network" (Penrose, Joyal–Street).

**Consequence for DNN training:**
- The forward pass of a transformer IS a tensor network contraction
- Tensor network methods from quantum physics (Matrix Product States, MERA, DMRG) provide optimal contraction orders
- **Optimal contraction order = minimal computation for the same result**
- This is where "quantum-inspired" enters: not quantum hardware, but quantum algorithms for **finding optimal ways to contract the tensor network that IS the neural network**

---

## 3. The Meta-Claim: A Neural Network IS a NeuroNet

If we accept the categorical decomposition above, then:

> **A trained neural network is a NeuroNet written in NeuroLang.**

Every layer is a `@neuro`. Every skip connection is a `Flow` operator. Every attention mechanism is a functor. The model's architecture is its `Plan`. The training loop is a Dim-3 optimization pass.

**What this means practically:**
- NeuroLang's tools (inspection, replay, decomposition, budget tracking) apply to neural networks directly
- A user could load a PyTorch model into NeuroLang, and the framework would:
  1. Decompose it into typed categorical components
  2. Render it as a string diagram
  3. Identify redundant structure (natural isomorphisms between layers)
  4. Suggest optimizations (parameter sharing, pruning, factorization)
  5. Re-export as an optimized model

---

## 4. Research Questions / Next Steps

| # | Question | Existing Work to Find |
|---|---|---|
| 1 | Does the categorical decomposition of a transformer match empirical observations about layer similarity? | Geva et al. (2021), Elhage et al. (2022) on mechanistic interpretability |
| 2 | Can "Backprop as Functor" be applied to real training speedups, or is it purely theoretical? | Cruttwell, Gavranović et al. (2022) — need to check for implementations |
| 3 | Do tensor network contraction algorithms from quantum physics give practical speedups for DNN inference? | Tensor network ML literature (Stoudenmire & Schwab, 2016; Novikov et al., 2015) |
| 4 | Can we auto-detect natural isomorphisms between layers in a trained model? | CKA similarity (Kornblith et al., 2019), SVCCA (Raghu et al., 2017) |
| 5 | Does the categorical structure predict which layers are safe to prune? | Structured pruning literature + lottery ticket hypothesis (Frankle & Carlin, 2019) |
| 6 | Can we implement a "NeuroLang model loader" that ingests a PyTorch model and decomposes it categorically? | Phase 2+ — requires JAX/PyTorch interop + the categorical decomposition algorithm |

---

## 5. Connection to NeuroLang Roadmap

| Roadmap Item | Connection |
|---|---|
| Phase 2 — JAX differentiable backend | Natural place to prototype categorical model decomposition |
| Phase 2 — HD substrate (`neurolang.hd`) | HD vectors could replace dense embeddings at Dim 0 |
| Phase 5 — Higher-categorical implementations | Dim 3+ structure (architecture search as 2-arrows) |
| RESEARCH.md §3 — "Code as Hyperdimensional Tensor Graph" | The same structure, applied inward to model internals |
| RESEARCH.md §1 — Three-Tower Identification | The theoretical foundation for the entire argument |

---

## 6. The Pitch (One Paragraph)

> Current ML treats neural networks as black boxes: train them, deploy them, pray. NeuroLang's categorical framework — the same dimensional ladder that structures agentic programs — reveals that neural networks have rich, exploitable internal structure at every categorical dimension. Embeddings are Dim-0 objects. Layers are Dim-1 morphisms. Multi-head attention is a Dim-2 functor. Residual connections are natural transformations. Architecture search is a Dim-3 rewrite. By identifying this structure, we can decompose, compress, and optimize models with mathematical precision — not heuristically, but functorially. The same framework that lets you write `web.search | reason.summarize` also lets you write `attention_head | layer_norm | residual`. A trained model IS a NeuroNet. NeuroLang is the language that makes this visible.

---

*This document is a brainstorm, not a commitment. Research directions will be refined after literature review.*
