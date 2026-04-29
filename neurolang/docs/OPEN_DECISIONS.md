# NeuroLang — Open Implementation Decisions

> Every decision listed here must be made (explicitly or implicitly) before Phase 1 lands. Many cascade across the rest of the language. The document records the question, the options, the trade-offs, and my recommendation. **Where I recommend, the user has the final call.**

---

## Cluster A — Phase 1 Skeleton (must decide before any code)

### A1. The concrete Python representation of `Neuro`

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| (a) ABC + dataclass | Abstract base class with abstract methods, dataclass for config | Explicit, discoverable, easy to introspect | Ceremonial; user writes a lot |
| (b) Protocol (PEP 544) | Structural subtyping; any class with the right shape "is" a Neuro | Flexible, light syntax | Less discoverable; harder to error-message |
| (c) Pydantic BaseModel | Validation built-in, declarative | Free input/output validation | Framework lock; schema overhead |
| (d) `@neuro` decorator on functions | Minimal user code; functions become neuros | Smallest authoring surface | Hard to attach metadata, harder to subclass |
| (e) **Hybrid: Protocol + `@neuro` + dataclass** | Protocol defines what counts; decorator wraps user code; dataclass holds config | Best of all; idiomatic Python | More moving parts to design |

**Recommendation: (e)** — Protocol for the type, `@neuro` decorator for ergonomic authoring, dataclass for config. Matches Python idioms, minimizes user friction, supports introspection.

---

### A2. Composition operator surface

| Option | Example | Pros | Cons |
|--------|---------|------|------|
| (a) `\|` (pipe) | `fetch \| filter \| summarize` | Reads naturally; bash-like | Conflicts with bitwise OR; can be confusing |
| (b) `>>` | `fetch >> filter >> summarize` | Used in many FP libs | Less Pythonic |
| (c) Method chaining | `fetch.then(filter).then(summarize)` | Explicit, no magic | Verbose for long flows |
| (d) `+` and `*` | `fetch + filter` (compose), `fetch * 3` (repeat) | Mathematical | Overloads natural arithmetic confusingly |
| (e) Builder API | `Flow().add(fetch).add(filter)` | No magic | Verbose, not "linguistic" |

**Recommendation: (a) `|` for sequential, `&` for parallel-AND, `+` for parallel-OR.** Reads like a sentence; matches how users describe flows. The categorical justification is direct: `|` is morphism composition, `&` is product, `+` is coproduct. Method chaining (`.then()`, `.parallel()`) is a secondary surface for users who prefer it.

---

### A3. Runtime model — sync vs async

| Option | Pros | Cons |
|--------|------|------|
| (a) Synchronous everywhere | Simplest | LLM calls block; no concurrency |
| (b) Async-first (asyncio) | Natural fit for LLM calls | All user code becomes async |
| (c) Both, explicit conversion | Maximum flexibility | Doubles surface area |
| (d) anyio (works on asyncio + Trio) | Async-first but allows Trio's better cancellation | Slightly more dependency |

**Recommendation: (d) anyio.** LLM calls are inherently async; structured concurrency (Trio's model) is the right pattern for agent flows; anyio gives both worlds.

---

### A4. State / context propagation through flows

How does data flow between steps?

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| (a) Implicit threading | Each step gets the previous output | Simple, terse | Hidden, hard to debug |
| (b) Named context dict | Each step reads/writes named keys | Auditable | Verbose; user picks names |
| (c) Lens-based | FP-style state lenses | Composable, type-safe | Steep learning curve |
| (d) Explicit `Context` param | Every neuro takes `(input, context) -> output` | Clear contracts | Boilerplate |

**Recommendation: (b) named context, with sugar for the common case.** The default case (`fetch | filter`) implicitly threads the previous result; advanced flows can name keys: `fetch -> "emails" | filter from "emails" | summarize`. Auditability matters; we'll thank ourselves at debugging time.

---

## Cluster B — Categorical Formalism

### B1. Which monoidal structure?

| Option | What it allows | Use case |
|--------|----------------|----------|
| Cartesian monoidal | Free duplication and discarding of values | Most general code; what Python already is |
| Symmetric monoidal | Parallel composition with reordering | Concurrent flows |
| Compact closed | Feedback loops, "cup/cap" | Recursive agents, fixed-points |
| Markov category | Built-in probability + nondeterminism | Probabilistic agents (matches Coecke et al.) |

**Recommendation: Start with Cartesian + Symmetric. Lift to Markov when probabilistic primitives are added (Phase 2). Compact closed only if loops force it.** Most agent code does not need feedback loops at the categorical level; they're handled by the runtime.

---

### B2. Effect tracking encoding

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| (a) Type-level via `Generic[T, EffectSet]` | Effects in type signatures, mypy-checked | Compile-time guarantees | Python's type system is awkward for this |
| (b) Runtime tag + decorator (`@effect("llm")`) | Each neuro carries an effect set as runtime metadata | Easy to author and inspect | No compile-time guarantee |
| (c) Free monad (effect tree) | Effects are values; interpreter handles them | Mathematically clean | Heavy, slow, alien to Python users |
| (d) Algebraic effects via `effect` library | Continuation-based handlers | Powerful | Niche library, debugging complex |

**Recommendation: (b) runtime tag + decorator for Phase 1; revisit type-level (a) in Phase 2.** Pragmatic, debuggable, doesn't fight Python. The type-level claim in marketing materials becomes "effects are tracked and inspectable" — accurate for (b).

---

### B3. Type system depth

| Option | What it gives | What it costs |
|--------|---------------|---------------|
| (a) Python typing + dataclasses + Pydantic | Familiar, decent IDE support | No real proof of correctness |
| (b) Add phantom types (`TypeVar` + `Generic`) for effects/budgets | Compile-time hints via mypy | Extra machinery, mypy-friendly only |
| (c) Refinement types via library (`deal`, `returns`) | Pre/postconditions enforced | Library lock-in |
| (d) Custom typechecker | Full control, all guarantees | Major project unto itself |

**Recommendation: Phase 1 = (a) + (b). Phase 2+ = consider (c). Defer (d) to Phase 5+ (or never).** We get most of the rigor with mypy-checked phantom types; users who don't run mypy still get the runtime checks.

---

## Cluster C — Plan Representation

### C1. What is a `Plan` concretely?

| Option | Structure | Pros | Cons |
|--------|-----------|------|------|
| (a) Linear AST (tree) | List of typed steps with sub-trees | Easy to render, simple to inspect | Awkward for DAGs and parallels |
| (b) Graph (DAG of nodes) | Nodes are operations, edges are data flow | Natural for agentic patterns | More complex API |
| (c) String diagram object | First-class categorical diagram | Mathematically correct | Library required (`discopy`?) |
| (d) Flat step list + DAG metadata | Linear order + adjacency | Compact, serializable | Loses structure |

**Recommendation: (b) Graph, with (c) string diagram as the rendering view.** Internally a typed DAG of nodes; we can render to string diagram (via discopy or our own renderer) for IDE; we can serialize to a flat form for cache.

---

### C2. Plan API — what can the user do with a plan?

Minimum API to commit to in Phase 1:

```python
plan = compile(intent)        # NL → Plan (Phase 3)
plan.steps                    # list of typed steps
plan.graph                    # the DAG
plan.cost_estimate()          # rolled-up budget
plan.run(context)             # execute, return Result + new Plan with state
plan.replay(trace)            # re-execute from a saved trace
plan.modify(step_id, ...)     # mutate a step; returns new Plan
plan.diff(other)              # structural diff against another plan
plan.hash()                   # canonical content hash for caching
plan.serialize() / .deserialize()  # persistence
```

**Decision:** is the plan **immutable** (functional, every modification returns a new plan) or **mutable**? Recommendation: immutable. Diffs and replays become trivial; cache is sound; bug-resistant.

---

## Cluster D — NL Surface (Phase 3, but Phase 1 must reserve hooks)

### D1. NL form — what counts as input?

| Option | Description |
|--------|-------------|
| (a) Plain sentence | "summarize last week's emails" |
| (b) Markdown with semantic blocks | `## Goal\n...\n## Constraints\n...` |
| (c) JSON with intent slots | `{"goal": "...", "constraints": [...]}` |
| (d) Voice transcript | Raw audio → text via STT |
| (e) All of the above, normalized | LLM compiler accepts any, emits canonical |

**Recommendation: (e) all of the above, with English/Hindi as the primary canonical surface forms.** The LLM compiler normalizes input; the cache key is the canonical formal program hash.

---

### D2. The cache key formula

What goes into the cache key for an NL→formal compilation?

```
key = hash(
  canonical_form(formal_program),
  llm_model_fingerprint,
  prompt_template_version,
)
```

**Open question:** does the cache key depend on the user's project context (memory state, prior conversations)? If yes, caching is tighter; if no, sharing across projects works. **Recommendation: cache key is context-independent; context is supplied at execution, not compilation.** This preserves the adjunction structure.

---

### D3. What about LLM stochasticity?

LLMs don't produce identical formal programs from identical NL prompts. Options:

| Option | Description |
|--------|-------------|
| (a) Temperature 0 always for the compiler | Deterministic-ish, but still drifts across model versions |
| (b) Sample N outputs, pick canonical-form-equivalent ones, vote | Robust but slow |
| (c) Fine-tuned compiler model | Highest quality, requires training |
| (d) Schema-constrained decoding (Outlines, Instructor) | Forces valid output; reduces drift dramatically |

**Recommendation: (a) + (d) for Phase 3 launch. (c) for Phase 4 when we have data.** Schema-constrained decoding is the under-appreciated stable foundation.

---

## Cluster E — Differentiability (Phase 2, but Phase 1 must not lock it out)

### E1. Substrate library

| Option | Pros | Cons |
|--------|------|------|
| (a) JAX | Functional, beautiful gradients, compile to GPU/TPU | Smaller ecosystem |
| (b) PyTorch | Largest ecosystem, easy Python | More mutable; harder for purity claims |
| (c) Both, abstracted | Maximum reach | Doubles maintenance |

**Recommendation: (a) JAX as the canonical, (c) abstracted such that PyTorch is a possible backend later.** JAX's functional purity matches our categorical claims; users who insist on PyTorch can be served by an adapter.

---

### E2. Effect-gradient interaction

How do we backpropagate through a flow that contains an LLM call?

| Option | Description |
|--------|-------------|
| (a) Stop-gradient at non-differentiable boundaries | Simple; many real-world workflows accept this |
| (b) Score-function (REINFORCE) for stochastic effects | Differentiate through expectation |
| (c) Surrogate gradients (use a small differentiable model as proxy) | Practical, lossy |
| (d) Explicit "differentiable" / "non-differentiable" markers per neuro | User-decided |

**Recommendation: (a) + (d) — by default stop-gradient at non-differentiable boundaries; expose markers so users can opt into REINFORCE for specific neuros.**

---

## Cluster F — Memory in Phase 1

### F1. Minimum viable memory layer

What ships in Phase 1?

| Option | Inclusion |
|--------|-----------|
| (a) Just discrete (dict) | Yes — must |
| (b) Differentiable (soft attention) | Phase 2 |
| (c) Compressed | Phase 2+ |
| (d) Hyperdimensional | Phase 2+ |
| (e) Episodic / semantic / procedural | Phase 3 |

**Recommendation:** Phase 1 ships **(a) discrete only, behind a `Memory` Protocol**. The Protocol is shaped to admit (b)–(e) later without breaking changes. Memory in Phase 1 is intentionally boring; the categorical contract is what matters.

---

## Cluster G — Strategic & Scope

### G1. Extraction from neurocomputer vs greenfield

| Option | Description |
|--------|-------------|
| (a) Pure greenfield | Write `neurolang/` from scratch |
| (b) Aggressive extraction | Move `BaseNeuro`, `kinds.py`, `FlowNeuro` etc. into `neurolang/` |
| (c) Read-only learning from neurocomputer | Don't touch neurocomputer; learn shape; rewrite cleanly |

**Recommendation: (c)** — clean rewrite, but informed by neurocomputer's hard-won lessons. Aggressive extraction couples the two repos and slows neurocomputer's evolution. Greenfield without learning ignores 40% of the work already done. Read the existing code carefully; rewrite small and right.

---

### G2. The IDE — even a minimal demo for Phase 1?

| Option | Phase 1 deliverable |
|--------|---------------------|
| (a) None | Pure library, no visualization |
| (b) discopy rendering | `flow.render()` produces a string diagram (PNG/SVG) |
| (c) Mermaid output | `flow.to_mermaid()` for github-renderable diagrams |
| (d) Both (b) + (c) | Two rendering paths |

**Recommendation: (d) both.** Each is a few hundred lines and pays off in demos, docs, and Phase 1 reviewer trust. Mermaid is for docs, discopy is for users who want to verify categorical correctness.

---

### G3. Open-source model

| Option | Rationale |
|--------|-----------|
| (a) MIT (current) | Most permissive, encourages adoption |
| (b) Apache 2.0 | Includes patent grant, cleaner for enterprise |
| (c) AGPL | Forces ecosystem to stay open |
| (d) Dual: MIT + commercial | Standard SaaS strategy |

**Recommendation: keep (a) MIT for now.** Adoption beats monetization in year one. Dual-licensing becomes possible once there is something worth charging for.

---

### G4. Versioning strategy

| Option | Description |
|--------|-------------|
| (a) SemVer with 0.x freedom | `0.0.1` → `0.1.0` → `1.0.0` once stable |
| (b) Hash-based (content-addressed) | Each neuro version is its content hash |
| (c) CalVer | Date-based releases |

**Recommendation: (a) SemVer for the package; (b) content-addressed for *individual neuros* once Phase 2 lands.** The package version is for humans; the neuro hash is for the cache.

---

## Cluster H — Long-Lived Agents (Architectural Question)

A neuro that runs for days has lifecycle, persistent memory, restart semantics.

### H1. How does this fit?

| Option | Description |
|--------|-------------|
| (a) Treat as a special category (coalgebraic) | Mathematically right but heavy |
| (b) Indexed monad over time | Captures lifecycle naturally |
| (c) Just `Agent = Neuro + Mailbox + persistent state` | Pragmatic, less mathematically rigorous |

**Recommendation: (c) for Phase 1, with the understanding that we'll revisit when the categorical pressure forces us.** Don't over-engineer the lifecycle until we have real long-running agents to teach us what's needed.

---

## Cluster I — Things That Cannot Be Decided Yet (and that's OK)

Some questions REQUIRE building something to answer:

1. **What's the canonical normal form for a NeuroLang program?** Won't know until we have flows in production.
2. **How does multi-NL parity actually behave?** Empirical question; depends on LLM strength in target languages.
3. **What's the right "primitive set" — i.e., the standard library?** Will emerge from real usage.
4. **At what flow size does the categorical interpreter stop being fast enough?** Performance numbers come from real workloads.
5. **Is the 3D IDE actually usable, or a marketing liability?** Real user testing required.

**These do not need to be decided now.** They need to be acknowledged as known unknowns, with the architecture flexible enough to absorb the answers when they come.

---

## Cluster J — The Decisions That Need YOUR Input Right Now

Of everything above, these are the ones I need your call on before Phase 1 code can start:

1. **A1** — `Neuro` representation: ABC, Protocol, decorator, hybrid? *(I recommend hybrid)*
2. **A2** — Composition operators: `|` `&` `+`? Or `>>`? Or method chaining? *(I recommend `|` `&` `+`)*
3. **A3** — Async model: anyio? *(I recommend anyio)*
4. **A4** — Context flow: implicit-threading or named-context? *(I recommend named)*
5. **B2** — Effects: runtime tag + decorator first, type-level later? *(I recommend yes)*
6. **C1** — Plan = typed DAG + render to string diagram? Immutable? *(I recommend yes)*
7. **G1** — Greenfield-but-informed (don't extract from neurocomputer)? *(I recommend yes)*
8. **G2** — Ship discopy + mermaid rendering in Phase 1? *(I recommend yes)*

The other clusters (E, F, D) are decisions for Phase 2 / Phase 3; I have recommendations but they don't block Phase 1.

---

## Cluster K — The Single Hardest Question

Before code: are we **actually** going to:

(α) Build a small, beautiful, working NeuroLang library — Phase 1 only — and validate the categorical claims hold, then iterate?

OR

(β) Try to ship Phases 1–3 quickly to demonstrate the full vision, accepting more risk per phase?

**Recommendation: (α).** Small and right beats large and ambitious at Phase 1. The validation we get from a working categorical core (with reviewer trust from category theorists AND working LLM-agent builders) is worth more than a half-baked NL compiler. Speed comes after correctness.

---

*Document at `/docs/OPEN_DECISIONS.md`. Maintained as decisions are resolved.*

---

## Cluster L — Trinity Rename (Deferred)

**Status: deferred — docs reframed 2026-04-30, code unchanged.**

The Trinity was reframed: NeuroNet now means *the program* (the artifact),
not *the runtime contract*. Docs, README, and website already reflect the
new framing. Code still uses the old meaning:

- `NeuroNet` (Protocol) in `neurolang/runtime/protocol.py`
- `LocalNeuroNet` in `neurolang/runtime/local.py`
- Re-exports in `neurolang/__init__.py`

### L1. Pending rename

When we have appetite (pre-alpha, no external consumers — safe window):

| Symbol | Current | Rename to |
|---|---|---|
| `NeuroNet` (Protocol) | runtime contract | `Runtime` (or `Host` / `NeuroHost` — TBD) |
| `LocalNeuroNet` | in-process runtime impl | `LocalRuntime` |
| `Plan` (or `Plan` + manifest wrapper) | compiled flow | `NeuroNet` (the program) |

**Recommendation:** rename to `Runtime` for the Protocol (short, clear, no brand conflict). Expose a `NeuroNet` type as `Plan` + a manifest dataclass (`name: str`, `version: str`, `deps: list[str]`, `signature: str`) so a NeuroNet can be serialized, packaged, and installed.

### L2. Blast radius

- `neurolang/__init__.py` — re-export names change
- `neurolang/runtime/protocol.py` — class rename
- `neurolang/runtime/local.py` — class rename + `__repr__`
- Any consumer in `neurocomputer/` that imports `NeuroNet` or `LocalNeuroNet` from `neurolang`
- `FRAMEWORK.md` and `NEUROCODE_NEURONET.md` body text (already flagged for rewrite)

### L3. Doc drift rule (until rename lands)

In **Python imports**: `NeuroNet` means the old "runtime contract".
In **prose**: `NeuroNet` means the new "program / artifact". Imports are
the only surviving use of the old sense.
