# NeuroCode ↔ NeuroNet — The Perfect Pair

> **NeuroCode** is what you write. **NeuroNet** is what it becomes.
>
> The two must be a perfect pair — transparent, verifiable, and taxonomically sound.

---

## 0. The Core Insight

In traditional programming you write code and then _hope_ the running system matches your intent. Bugs hide because the gap between source code and runtime behavior is opaque.

NeuroLang eliminates that gap by making **the code you author (NeuroCode)** and **the network it produces (NeuroNet)** into two co-equal, inspectable views of the same structure — kept in sync by construction, not by testing alone.

| | What it is | Analogy |
|---|---|---|
| **NeuroCode** | The authored program — neuros, flows, plans, effects, budgets, memory declarations | Source code |
| **NeuroNet** | The live runtime graph — running neuros, agents, memory cells, plans-in-flight, effects in motion | The running process |

**The perfect pair:** every structural property visible in NeuroCode is _also_ visible — and verifiable — in NeuroNet, and vice versa. There is no hidden state.

---

## 1. Two Parts of the Pair

### Part 1 — Authoring (NeuroCode → NeuroNet)

You write NeuroCode using NeuroLang's primitives:

```python
from neurolang import neuro, Flow, Memory, Budget

@neuro(effect="tool")
def fetch_data(query: str) -> list[dict]: ...

@neuro(effect="llm", budget=Budget(cost_usd=0.02))
def analyze(data: list[dict]) -> str: ...

@neuro(effect="llm")
def summarize(analysis: str) -> str: ...

pipeline: Flow = fetch_data | analyze | summarize
```

This NeuroCode **compiles into a NeuroNet** — a live graph with:
- Three neuro nodes (`fetch_data`, `analyze`, `summarize`)
- Sequential edges between them
- Effect annotations on each node (`tool`, `llm`, `llm`)
- Budget bounds on `analyze`
- Type contracts on every edge (`str → list[dict] → str → str`)

### Part 2 — Verification (NeuroNet → NeuroCode)

The inverse direction: given a running NeuroNet, you can always **read back** the structure as if it were code:

- **Topology** — which neuros are connected, in what order, with what composition strategy
- **Effects** — what kinds of side effects are declared vs. what actually happened
- **Budget** — what was budgeted vs. what was spent
- **Types** — what types flowed across each edge
- **Memory** — what was read, what was written, by whom

This is not a debugger bolted on after the fact. The NeuroNet **is** the NeuroCode, just viewed at runtime.

---

## 2. What "Perfect Pair" Means Concretely

The pairing is perfect when these identities hold:

### Identity 1 — Structural Fidelity
```
render(compile(neurocode)) ≡ neurocode
```
If you compile NeuroCode into a NeuroNet and then render the NeuroNet as a diagram, the diagram is structurally identical to the authored flow. No hidden nodes. No implicit connections.

### Identity 2 — Effect Transparency
```
declared_effects(neurocode) ≡ observed_effects(neuronet)
```
Every effect declared in the code (`effect="llm"`, `effect="tool"`) is the exact set of effects the runtime tracks. No unmarked side effects.

### Identity 3 — Budget Accountability
```
budget_estimate(neurocode) ≥ actual_cost(neuronet)
```
The budget declared at authoring time is an upper bound on what the runtime actually spends. If violated, the runtime raises — not silently.

### Identity 4 — Type Coherence
```
type_signature(neuro_A.output) ≡ type_signature(neuro_B.input)
```
Where neuro A feeds into neuro B via `|`, the output type of A matches the input type of B. Verified at composition time (not at runtime surprise).

### Identity 5 — Memory Scope Integrity
```
reads(neuro) ∩ writes(other_neuro) → explicitly declared
```
No neuro reads memory that another neuro wrote without both declaring the dependency. Ownership is explicit, like Rust's borrow checker but for memory scope.

---

## 3. The Taxonomical Advantage

Traditional neural networks are black boxes — you can't inspect, name, or organize their parts.

NeuroLang's NeuroNet is **taxonomically organized** — every part has:

| Property | Description |
|---|---|
| **Identity** | A stable, qualified name (`neurolang.stdlib.reason.summarize`) |
| **Kind** | A classification (`skill`, `agent`, `model`, `memory`, `flow`) |
| **Effect** | What it touches (`pure`, `llm`, `tool`, `voice`, `human`, `time`) |
| **Budget** | What it costs (latency, money) |
| **Type signature** | What it takes and produces |
| **Docstring** | What it does in natural language |

This taxonomy means you can:

- **Search** — "show me all neuros with effect `llm` and budget under $0.01"
- **Classify** — "group all tool-effect neuros by domain (web, email, voice)"
- **Compare** — "diff two versions of the same flow to see what changed"
- **Substitute** — "replace `reason.summarize` with a cheaper alternative that has the same type signature"
- **Compose** — "given these types, what are the valid compositions?"

This is the advantage over opaque neural networks: **NeuroNets are networks you can read, name, search, and reason about**, just like code.

---

## 4. Transparency at Every Layer

```
┌──────────────────────────────────────────────────────────┐
│  NeuroCode (what you write)                               │
│                                                           │
│   @neuro(effect="llm")                                    │
│   def summarize(text: str) -> str: ...                    │
│                                                           │
│   flow = fetch | analyze | summarize                      │
│                                                           │
├─────────── compile / plan ────────────────────────────────┤
│                                                           │
│  NeuroNet (what runs)                                     │
│                                                           │
│   ┌─────────┐     ┌─────────┐     ┌───────────┐          │
│   │  fetch  │────▶│ analyze │────▶│ summarize │          │
│   │  [tool] │     │  [llm]  │     │   [llm]   │          │
│   └─────────┘     └─────────┘     └───────────┘          │
│                                                           │
│  Topology:   3 nodes, 2 edges, sequential                 │
│  Effects:    {tool, llm}                                  │
│  Budget:     $0.05 max                                    │
│  Types:      str → list → str → str                       │
│                                                           │
├─────────── render / decompile ────────────────────────────┤
│                                                           │
│  Natural Language (what you read back)                    │
│                                                           │
│  "Fetches data for the query, analyzes the results        │
│   using an LLM, then summarizes the analysis."            │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

Every layer is derivable from the others:
- **NeuroCode → NeuroNet** via `flow.plan()` (compile)
- **NeuroNet → Diagram** via `flow.render()` or `net.topology()` (inspect)
- **NeuroNet → NL** via `decompile_summary()` (summarize)
- **NL → NeuroCode** via `compile_source()` (author)

The round-trip is the coherence check. If any direction produces something unexpected, the diff is shown to the user.

---

## 5. Use Cases This Enables

### 5.1 — Debugging by Inspection
Instead of adding print statements, inspect the NeuroNet:

```python
net = neuronet.current()
net.topology()      # see every node, edge, state
net.effects_log()   # what effects actually fired
net.budget_spent()  # what was the cost
```

### 5.2 — Compositional Verification
Before running, verify the flow is well-formed:

```python
flow = fetch | analyze | summarize
flow.effects()           # frozenset({tool, llm})
flow.budget()            # Budget(cost_usd=0.05, latency_ms=2000)
flow.effect_signature()  # {'tool', 'llm'}
flow.render("mermaid")   # visual topology
```

### 5.3 — Taxonomical Discovery
Find neuros by their taxonomy:

```python
from neurolang import default_registry

# All LLM neuros under $0.01
cheap_llm = [n for n in default_registry
             if Effect.LLM in n.effects
             and n.budget.cost_usd < 0.01]

# All neuros in the "web" domain
web_neuros = [n for n in default_registry
              if n.name.startswith("neurolang.stdlib.web")]
```

### 5.4 — Substitution-Safe Refactoring
Replace a neuro with another that has the same type signature:

```python
# Old: expensive summarizer
flow = fetch | analyze | expensive_summarize

# New: cheaper one, same type (str -> str), same effect (llm)
flow = fetch | analyze | cheap_summarize
# Verified at composition time — types match, effects match
```

### 5.5 — Flexible & Transparent Neural Networks
When neuros are differentiable (Phase 2), flows become tensor networks:

```
NeuroCode description  ←→  NeuroNet graph  ←→  Tensor network
```

Same transparency applies: every node has a name, a type, an effect. The network is not a black box — it is a **named, typed, inspectable, composable graph** that you authored in code and can always read back.

---

## 6. Summary — Why This Matters

| Traditional Neural Networks | NeuroLang NeuroNet |
|---|---|
| Black box | Transparent graph |
| No names on parts | Every part has a qualified name |
| No type contracts between layers | Every edge is typed |
| No effect tracking | Every side effect is declared and tracked |
| No cost visibility | Budget is part of the contract |
| Hard to refactor | Substitution-safe via types and effects |
| Hard to inspect at runtime | Runtime graph is a first-class object |
| One authoring mode (code) | Three modes: NL, code, visual — kept in sync |

**NeuroCode is the spec. NeuroNet is the implementation. They are the same structure viewed from two angles.** This is the perfect pair.

---

*Document at `/docs/NEUROCODE_NEURONET.md`. Complements `FRAMEWORK.md` (the trinity), `ARCHITECTURE.md` (the three-layer stack), and `RESEARCH.md` (the categorical foundations).*
