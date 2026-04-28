# Literature Review — Categorical, Tensor Network, and Quantum-Inspired Approaches to Deep Learning

> **Purpose:** Analyze existing research related to our brainstorm thesis: "neural networks have exploitable categorical structure at every dimension."
> **Date:** 2026-04-27

---

## Overview

The ideas in our brainstorm are **not isolated** — they sit at the intersection of several active research programs. What IS novel is the proposal to **unify** them under NeuroLang's dimensional ladder and apply them simultaneously. Below is a thread-by-thread analysis.

---

## Thread 1: Backprop as Functor — Category Theory for Deep Learning

### Key Papers

| Paper | Authors | Year | Core Claim |
|---|---|---|---|
| **Backprop as Functor** | Fong, Spivak, Tuyéras | 2019 | Gradient descent + backprop = a symmetric monoidal functor from parameterized functions to learning algorithms. Modular training ≅ end-to-end training under categorical conditions. |
| **Categorical Foundations of Gradient-Based Learning** | Cruttwell, Gavranović, Ghani, Wilson, Zanasi | 2022 | Unifies SGD, Adam, AdaGrad etc. using lenses, parameterized maps, and reverse derivative categories. Generalizes beyond smooth maps (e.g., to boolean circuits). |
| **Fundamental Components of Deep Learning: A Category-Theoretic Approach** | Bruno Gavranović (PhD thesis) | 2024 | The most comprehensive categorical treatment of deep learning to date. Covers architectures, loss functions, optimizers as instances of the same categorical structures. |
| **CatGrad** | Gavranović et al. | 2023–24 | **Working implementation** of categorical gradient-based learning. A Python/Haskell framework at [catgrad.com](https://catgrad.com). Proves the ideas are implementable, not just theoretical. |

### Assessment for Our Thesis

> **Strong validation.** The "Backprop as Functor" program proves that our Dim 1–2 claims are mathematically sound. Gradient computation IS functorial. The CatGrad implementation proves it's practical. Our contribution would be to **embed this into NeuroLang's framework** — so the same `|` operator that composes neuros also composes layers within a model, and gradients flow functorially through both.

### What's NOT been done (our gap)
- Nobody has connected this to a **user-facing programming framework** (CatGrad is research code, not a library for practitioners).
- Nobody has applied the dimensional ladder (our Dim 0–∞ structure) to classify model components.

---

## Thread 2: Mechanistic Interpretability — Understanding Model Internals

### Key Papers

| Paper | Authors | Year | Core Claim |
|---|---|---|---|
| **Toy Models of Superposition** | Elhage, Anthropic | 2022 | Neural networks represent more features than they have dimensions — features are superimposed. This is a structural property, not an accident. |
| **Scaling Monosemanticity** | Anthropic | 2024 | Sparse autoencoders can extract interpretable features from large language models (Claude 3 Sonnet). Features are compositional. |
| **Similarity of Neural Network Representations Revisited (CKA)** | Kornblith et al. (Google) | 2019 | Centered Kernel Alignment reliably measures layer similarity across different initializations. Adjacent layers often have high CKA similarity. |
| **SVCCA: Singular Vector CCA** | Raghu et al. (Google Brain) | 2017 | Measures intrinsic dimensionality of layers and how representations converge during training. |

### Assessment for Our Thesis

> **Strongly supports our claim that models are not black boxes.** Mechanistic interpretability is empirically proving that models have internal structure — features, circuits, composition patterns. CKA/SVCCA prove that layers have measurable similarity (our "natural isomorphisms" between layers). Our contribution would be to give this a **formal categorical framework** — instead of ad-hoc circuit analysis, classify features by categorical dimension.

### What's NOT been done (our gap)
- Nobody has connected mechanistic interpretability to **category theory**. The Anthropic team uses informal "circuit" language; we could give it the precise language of string diagrams and natural transformations.
- CKA measures similarity but doesn't explain **why** layers are similar. Categorical natural isomorphisms would.

---

## Thread 3: Tensor Networks for Machine Learning

### Key Papers

| Paper | Authors | Year | Core Claim |
|---|---|---|---|
| **Supervised Learning with Quantum-Inspired Tensor Networks** | Stoudenmire & Schwab | 2016 (NeurIPS) | Matrix Product States (MPS) — a tensor network from quantum physics — achieve <1% error on MNIST with far fewer parameters than dense networks. |
| **Tensorizing Neural Networks** | Novikov et al. | 2015 | Compress FC layers using Tensor Train decomposition — 200,000× compression with minimal accuracy loss on CIFAR-10. |
| **Tensor Networks for ML** (survey) | Various | 2020–24 | Tensor decompositions (Tucker, CP, TT, MERA) applied to compress neural networks, speed up inference, and enable interpretability. |

### Assessment for Our Thesis

> **Direct validation of the "string diagram = tensor network" claim.** Stoudenmire & Schwab prove that tensor network methods from quantum physics are practical for ML. Our RESEARCH.md already states this identification (via Penrose diagrams). Our contribution would be to make this **automatic** — NeuroLang's categorical structure would identify which tensor decompositions are applicable to a given model component.

### What's NOT been done (our gap)
- Existing work applies tensor networks as a **compression technique** after training. Nobody uses the categorical structure to **guide training** from the start.
- Nobody has connected tensor network ML to a **programming framework** — it's all one-off research code.

---

## Thread 4: Equivariant Networks and Geometric Deep Learning

### Key Papers

| Paper | Authors | Year | Core Claim |
|---|---|---|---|
| **Group Equivariant CNNs** | Cohen & Welling | 2016 | CNNs should respect symmetry groups (rotation, reflection). G-CNNs generalize translational equivariance to arbitrary groups. |
| **Geometric Deep Learning: Grids, Groups, Graphs, Geodesics, and Gauges** | Bronstein, Bruna, Cohen, Veličković | 2021 | A unified framework for all geometric deep learning — CNNs, GNNs, Transformers are all instances of equivariant maps on geometric domains. |
| **Steerable CNNs / Gauge Equivariant CNNs** | Cohen, Weiler et al. | 2018–2021 | Generalize G-CNNs to arbitrary manifolds using fiber bundles and gauge theory. |

### Assessment for Our Thesis

> **Strong parallel to our approach.** Geometric deep learning uses group theory to constrain architectures — exploiting symmetry for efficiency and generalization. Our categorical approach is strictly **more general**: groups are a special case of categories. Where GDL says "this layer must be equivariant under rotation," we could say "this layer must be a natural transformation in this category." The categorical framework subsumes the group-theoretic one.

### What's NOT been done (our gap)
- The connection between **categorical approaches (Fong/Spivak) and geometric deep learning (Cohen/Bronstein)** is not yet made in the literature. This is a significant gap we could fill.
- Nobody has a **single framework** that handles both compositional structure (categorical) and geometric symmetry (group-theoretic).

---

## Thread 5: LoRA and Weight Sharing — Empirical Evidence for Categorical Structure

### Key Papers

| Paper | Authors | Year | Core Claim |
|---|---|---|---|
| **LoRA: Low-Rank Adaptation** | Hu et al. (Microsoft) | 2021 | Weight updates for fine-tuning lie in a low-rank subspace (ΔW ≈ BA). Freeze base model, train only the low-rank adapters. |
| **Tied-LoRA** | Various | 2023 | Share LoRA matrices across layers — 90%+ parameter reduction with comparable performance. Proves layers have shared structure. |
| **TensLoRA** | Various | 2024 | Tensor decompositions to share parameters jointly across layers, heads, and projections. |

### Assessment for Our Thesis

> **Empirical proof of our "natural isomorphism" claim.** LoRA works because weight updates ARE low-rank — there ARE shared substructures. Tied-LoRA works because adjacent layers ARE naturally isomorphic. TensLoRA uses tensor decompositions — connecting to Thread 3. Our contribution: give this a **categorical explanation** (LoRA = a natural transformation; Tied-LoRA = parameter sharing along a natural isomorphism) and **automate** the discovery of which layers can be tied.

---

## Thread 6: DisCoCat and Compositional NLP

### Key Papers

| Paper | Authors | Year | Core Claim |
|---|---|---|---|
| **DisCoCat** | Coecke, Sadrzadeh, Clark | 2010 | Sentence meaning = tensor contraction of word vectors guided by grammar. Grammar types form a category; meaning is a functor. |
| **Higher-Order DisCoCat** | Various | 2023–24 | Extends to adverbs, negation, quantifiers — higher-order functions as higher categorical structure. |
| **DisCoCirc** | Coecke et al. | 2021+ | Extends DisCoCat from sentences to entire texts (discourse). Language as a circuit — 2D structure, not 1D strings. |

### Assessment for Our Thesis

> **Already cited in our RESEARCH.md.** DisCoCat is the NLP arm of the same mathematical structure we're using. DisCoCirc's move from 1D strings to 2D circuits mirrors our dimensional ladder. Our contribution: NeuroLang unifies DisCoCat (language), Backprop as Functor (learning), and tensor networks (computation) in **one framework**. Nobody else has done this unification.

---

## Summary: What Exists vs What's New

| Research Thread | Exists? | Our Novel Contribution |
|---|---|---|
| Backprop as Functor | ✅ Proven (Fong/Spivak, Cruttwell/Gavranović) | Embed in a user-facing framework (NeuroLang); apply the dimensional ladder to model internals |
| Mechanistic Interpretability | ✅ Active (Anthropic, Google) | Give it categorical formalism — features as objects, circuits as morphisms, superposition as a categorical phenomenon |
| Tensor Networks for ML | ✅ Proven (Stoudenmire/Schwab, Novikov) | Use categorical structure to **guide** decomposition (not just post-hoc compression) |
| Geometric Deep Learning | ✅ Unified (Bronstein et al.) | Subsume group-theoretic equivariance under categorical equivariance (strictly more general) |
| LoRA / Weight Sharing | ✅ Empirical (Hu et al., Tied-LoRA) | Categorical explanation (natural isomorphisms); automated discovery of sharing opportunities |
| DisCoCat / Compositional NLP | ✅ Foundational (Coecke et al.) | Unify with learning and computation in one framework |

### The Genuine Gap We Would Fill

> **No existing work unifies all six threads under a single dimensional ladder and embeds them in a practical programming framework.**
>
> The closest is Gavranović's PhD thesis (2024), which provides a categorical theory of deep learning. But it stops at theory — no user-facing framework, no dimensional classification of model components, no connection to mechanistic interpretability or geometric deep learning.
>
> NeuroLang's unique position: it already has the dimensional ladder (RESEARCH.md), the programming framework (the library), and the tensor-network identification (string diagrams). The research brainstorm extends this **inward** — from orchestrating models to understanding their internals.

---

## Recommended Reading Order (for deep dive)

1. **Gavranović (2024)** — "Fundamental Components of Deep Learning" PhD thesis (the most comprehensive single source)
2. **Fong, Spivak, Tuyéras (2019)** — "Backprop as Functor" (the foundational paper)
3. **Bronstein et al. (2021)** — "Geometric Deep Learning" (the GDL unified framework)
4. **Stoudenmire & Schwab (2016)** — "Supervised Learning with Quantum-Inspired Tensor Networks"
5. **Kornblith et al. (2019)** — "Similarity of Neural Network Representations Revisited" (CKA)
6. **Coecke, Sadrzadeh, Clark (2010)** — "Mathematical Foundations for a Compositional Distributional Model of Meaning" (DisCoCat)

---

*This document is a literature review, not a commitment. Research directions will be refined after deeper reading of the papers listed above.*
