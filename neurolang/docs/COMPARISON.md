# NeuroLang — Structural Plan + 3-Way Comparison

> How NeuroLang structures every core agentic concept, contrasted with what *our current neurocomputer system* does today and what *the public state-of-the-art* (LangChain, LangGraph, DSPy, AutoGen, CrewAI, OpenAI Assistants, Anthropic Computer Use, Pydantic AI, etc.) does.

---

## 1. The Structural Skeleton

NeuroLang's structure rests on a small set of typed primitives, each living at a specific dimension on the categorical ladder:

| Primitive | Dimension | Role |
|-----------|-----------|------|
| **Neuro** | 0–1 | The fundamental unit — typed, composable, optionally differentiable, optionally with a prompt surface |
| **Flow** | 1–2 | Composition of neuros (sequential, parallel, DAG, loop) — categorical morphism composition |
| **Memory** | 0–2 | Hierarchical store (discrete → differentiable → HD → episodic/semantic/procedural), with scoped read/write declarations |
| **Plan** | 2–3 | First-class structured plan; inspectable, modifiable, replayable as a value |
| **Context** | 1–2 | Typed slice of memory + prompt assembly, declared explicitly per neuro |
| **Prompt** | 1 | Prompt neuro with typed slots; composes categorically; cached round-trip with NL |
| **Effect** | 2 | `pure` / `llm` / `tool` / `human` / `time` — tracked in types, enforced by compiler |
| **Budget** | 1 | Latency + cost bounds, runtime-enforced, compile-time-warned |
| **Recovery** | 2 | `fallback`, `retry`, `escalate` as language primitives |
| **Mailbox** | 9 (in PL terms) / 2-cat | Message-passing between agents, no shared mutable state |
| **Agent** | 2–3 | A long-lived neuro with mailbox, memory, role, and identity |
| **Adjunction** | 2 | Bidirectional NL ↔ formal compiler, with cached unit/counit |

Every NeuroLang program is a *string diagram* in the category these primitives generate. The same diagram is also a *tensor network* end-to-end-differentiable where the primitives allow.

---

## 2. The Comparison Table

For each concept: how NeuroLang handles it, how our current neurocomputer handles it today, and how the public state-of-the-art handles it.

### 2.1 The Fundamental Unit ("the neuron / neuro / agent / module")

| **NeuroLang** | **Our current system (neurocomputer)** | **Public best practice** |
|---|---|---|
| `Neuro` — typed, dimensioned, with declared effect, cost, differentiability, and optional NL surface. Composable by categorical operators. Has a canonical normal form. | `BaseNeuro` abstract class + `conf.json` + `code.py` + optional `prompt.txt`. ~68 modules in `neurocomputer/neuros/`. Kind taxonomy (`skill.*`, `prompt.*`, `model.*`, `agent.*`) — a partial language already. | LangChain: Python class instances (`Tool`, `Agent`, `Chain`). DSPy: `Module` subclasses with `Signature`. AutoGen: `ConversableAgent`. OpenAI Assistants: JSON-specified tools + functions. Almost all are Python objects with ad-hoc typing. |

### 2.2 Composition / Orchestration

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| Categorical composition operators: `\|>` (sequential), `\|\|` (parallel), `&` (DAG fan-in), `*>` (loop). Flows are first-class **arrows** in a monoidal category. Composition laws hold (associativity, identity). | `FlowNeuro` → `SequentialFlow` / `ParallelFlow` / `DagFlow` with hooks. `Brain.handle()` (~550 lines) routes between routes, plans, smart-router, intent classifier, planner, direct skill dispatch. | LangChain: chains (`SequentialChain`, `RouterChain`). LangGraph: state-machine graphs with explicit nodes and edges. DSPy: Python function composition + `Signature` types. AutoGen: conversation patterns. CrewAI: declarative role/goal lists. **All of these are runtime-typed at best.** |

### 2.3 Memory

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| Typed hierarchy: discrete (key-value) / differentiable (soft attention) / compressed (sparse, low-rank) / hyperdimensional (Kanerva VSA) / episodic / semantic / procedural. **Scoped read/write declarations per neuro** (Rust-ownership-style). Memory itself is a functor; recall is gradient-aware. | SQLite (`db.py`, ~25KB, monolith) + `agent_memory.db`. Memory neuros (`memory.store`, `memory.recall`, `memory.graph`). Conversation history via tabs and projects. **No scoping discipline; no differentiable recall; no hyperdimensional substrate.** | Vector stores (Pinecone, Weaviate, Chroma, Qdrant) for semantic memory. LangChain `BufferMemory`, `SummaryMemory`, `VectorStoreRetrieverMemory`. OpenAI Assistants threads (auto-managed). DSPy: explicit retrievers. **Almost universally: vector store + sliding window. No formal scoping.** |

### 2.4 Prompt

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **Prompts are first-class neuros** (`prompt.block`, `prompt.composer`) with typed slots. Compose categorically. Bidirectional NL ↔ formal cached as adjunction unit/counit. Multi-natural-language input → single normalized formal target. | `prompt.txt` files alongside `code.py` per neuro. `PromptBlock` typed base. Some prompt composers. **Prompts are textual artefacts, not compositional language objects.** | LangChain: `PromptTemplate`, `ChatPromptTemplate`, `FewShotPromptTemplate`. DSPy: `Signature` (the closest match — declarative input/output schemas optimized at compile time). LiteLLM/Magentic: f-strings + schemas. **Most: f-strings and Jinja templates with no formal semantics.** |

### 2.5 Context

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| `Context` neuro with explicit read declarations (which memory keys, which time-window, which embedding). Assembly is functorial. Multi-modal (text, vector, image). Differentiable when needed. | `ContextSlice` typed base. Context assembly logic in code.py files. **Per-neuro context handling is ad-hoc; no compile-time guarantee that context covers what the neuro reads.** | LangChain: `Document` lists, retriever chains, ad-hoc concatenation. RAG patterns (manual). OpenAI Assistants: thread-based, auto-managed. **Mostly: retrieve → concat → truncate → hope.** |

### 2.6 Tools / Skills

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| Tools are typed effectful neuros (`effect: tool`). Cost-annotated. Recovery (`fallback`, `retry`, `escalate`) as language primitives. Differentiable boundaries explicit (gradient stops at tool call unless score-function estimator is wired). | `Skill` neuros (`skill.smart_router`, `skill.planner`, `skill.reply`, `skill.dev_*`, `skill.code_*`, etc.). Skills as code with optional prompts. **Effect category is implicit; cost is uncounted; recovery is Python try/except.** | LangChain: `Tool` class; `@tool` decorator. OpenAI: function calling JSON schemas. AutoGen: `register_function`. DSPy: tools as Python callables. Anthropic Computer Use: action protocol. **All untyped on effects; recovery is application code.** |

### 2.7 Models / LLM Integration

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| `model.llm.*` neuros — same primitive as any other neuro. Composable. Cost/latency annotations. **Cache invalidation tied to model version + program version, principled via adjunction.** | `ModelLLM` typed base + `BaseBrain` interface. Multi-provider support (Ollama Gemma, etc.) via `llm_registry`. **Solid foundation; closer to NeuroLang's structure than most public frameworks.** | LiteLLM, OpenAI/Anthropic SDKs directly, LangChain `ChatOpenAI` etc. **Mostly provider-specific or thin abstraction. No principled cache invalidation tied to model identity.** |

### 2.8 Agents

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| Agents are **2-categorical objects** — long-lived neuros with mailbox + memory + role. Protocols between agents are 2-arrows. Multi-agent systems are 2-categories. | `AgentNeuro` typed base + `agent_router` + `AGENT_DELEGATES` map + profiles. Brain.handle() routes to agent neuros. **Solid agent abstraction; no formal protocol typing between agents.** | LangChain: `BaseAgent` subclasses. AutoGen: `ConversableAgent` (conversation-based). CrewAI: roles + goals + backstories. **All untyped on inter-agent protocols; coordination is conversation transcripts or shared state.** |

### 2.9 Plans (the deepest differentiator)

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **`Plan` is a first-class value.** Inspect, modify, persist, replay, hash, compare. Plans compose. Plans can be edited by the user mid-execution. Plans are *the only* artefact that survives a run for audit. | `skill.planner` neuro produces a plan; tool_loop and smart_router execute. **Plans exist transiently — produced by an LLM, executed, lost.** | ReAct loops (Yao et al.) plan inside one LLM call — ephemeral. LangGraph: state graphs are static templates, not plans-as-values. DSPy: optimized at compile time, not at runtime. **Almost no system treats the plan itself as a reified object.** |

### 2.10 Effects / I/O

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| Effects tracked in **types**: `pure`, `llm`, `tool`, `human`, `time`. Compiler enforces composability. A `pure` flow can run anywhere; an `llm` flow needs a model bound; a `human` flow blocks until approval. | Implicit through neuro kind. **No effect tracking in types.** | LangChain: `Callbacks` for logging side-effects, but no type-level tracking. DSPy: pure-ish at module level, but Python side effects are uncontrolled. **Effects are uniformly untyped in current AI frameworks.** |

### 2.11 Cost / Budget

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **`@budget(latency: 500ms, cost: $0.01)`** annotations on signatures. Compiler warns if a flow exceeds its budget statically. Runtime enforces (kills tasks that exceed). | Some LLM-call accounting; mostly post-hoc analysis. **No declarative budget; surprise bills possible.** | LangChain `Callbacks` for token tracking. LangSmith for trace analysis. OpenAI usage dashboards. **Almost universally: discover cost via $ on credit card.** |

### 2.12 Recovery / Errors

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| `fallback`, `retry`, `escalate` as **language primitives**, not library imports. Composable: a flow can declare "retry 3× then fall back to a cheaper model then escalate to human." Type-checked. | Standard Python try/except + manual fallback logic in code.py files. **Recovery is ad-hoc per neuro.** | Tenacity (Python retry library), LangChain `RunnableRetry` / `RunnableFallback`. AutoGen: conversation reset on error. **Recovery is library-level glue, not language-level structure.** |

### 2.13 Multi-Agent Communication

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **Mailboxes** (Erlang/Actor model): no shared mutable state. Messages are typed. Protocols are 2-categorical. Deadlock and starvation analyzable from types. | Brain delegation via `AGENT_DELEGATES` map; agents don't really talk to each other — Brain mediates. **Single-orchestrator pattern; no peer-to-peer typed protocol.** | AutoGen: free-form conversations. CrewAI: sequential or hierarchical roles. LangGraph: shared state in a graph. OpenAI Swarm: handoffs. **All ad-hoc; no typed inter-agent protocols.** |

### 2.14 Authoring Surface

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **Three co-equal modes:** (1) NL command (any language), (2) drag manipulation in 3D IDE, (3) text editing of formal NeuroLang. All sync via cached adjunction. | Python + `conf.json` + `prompt.txt` per neuro. NeuroIDE web component for some viewing/editing. **Authoring is text-only Python; no NL surface.** | LangChain: Python in a notebook or editor. DSPy: Python with Signature classes. CrewAI: Python or YAML. OpenAI Playground: GUI for prompts. **No system has bidirectional NL ↔ formal as the primary surface.** |

### 2.15 Type Safety

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **Refinement-typed** with categorical kinds. Effects in types. Budgets in types. Dimensional kind discipline. Compile-time errors for ill-typed flows. | Python type hints in some places. Pydantic for I/O schemas in some neuros. **Mostly dynamic; type errors at runtime.** | Pydantic AI: typed agents (closest existing match). DSPy: typed signatures (input/output). LangChain: minimal typing. **Industry trend is toward more types, but no system reaches NeuroLang's depth.** |

### 2.16 Caching / Determinism

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **The cache IS the unit/counit data of an adjunction.** Triangle identities give principled invalidation. Cache key = canonical normal form of formal program × model version. Cache survives across conversations and projects when keys match. | Some caching in `agent_memory.db`. **Not principled; not versioned.** | LangChain `set_llm_cache()` for response caching. Anthropic prompt caching (provider-side). Semantic caches (GPTCache). **Caching is performance optimization, not language semantics.** |

### 2.17 Observability / Debugging

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| Plans-as-values means **every execution emits an inspectable plan trace**. Categorical types mean type errors are caught at compile. The 3D IDE renders the live execution as a string diagram with state. | Logs, traces in Brain.handle(). NeuroIDE shows some structure. **Standard Python observability.** | LangSmith (LangChain), Weave (W&B), Phoenix (Arize), OpenTelemetry. **Trace-based; assumes opaque LLM calls; reconstructs structure post-hoc.** |

### 2.18 Self-Modification / Learning

| **NeuroLang** | **Our current system** | **Public best practice** |
|---|---|---|
| **Differentiable substrate** enables gradient-based optimization of flows end-to-end. Phase 5: the compiler is itself a NeuroLang program; the language begins to evolve itself. | Manual prompt editing, manual neuro updates. **No learning loop.** | DSPy `compile()` (the closest match — optimizes prompts via bootstrap + few-shot). RLHF (closed, vendor-side). Fine-tuning pipelines. **Most systems do not learn; they are configured.** |

---

## 3. What This Comparison Shows

### 3.1 Where we are already ahead of public best practice

Our current neurocomputer system is, surprisingly, **closer to NeuroLang's vision than most public frameworks**, on several axes:

- **Typed neuro taxonomy** (kind namespaces) — no public framework has this.
- **Multi-provider LLM abstraction with hot-swappable backends** — better than most.
- **Flow neurons with categorical-shaped composition** (sequential / parallel / DAG) — already aligned.
- **Memory neuros with explicit kinds** (store / recall / graph) — better than ad-hoc vector stores.

This is why the modularity refactor + NeuroLang extraction is a **realistic** project. **We have already built ~40% of NeuroLang accidentally.** What's left is to formalise the categorical structure, add the differentiable substrate, build the NL compiler, and ship the IDE.

### 3.2 Where the public best practice is currently ahead of us

We must honestly admit:

- **DSPy compiles prompts.** We don't optimize anything automatically — the user hand-writes prompts.
- **LangSmith / Phoenix have polished trace UIs.** Our observability is Python logs.
- **OpenAI Assistants and Anthropic Computer Use have native function-calling reliability** that small open models lack.
- **Vector stores like Weaviate / Qdrant** scale and tune in ways our SQLite-based memory does not.
- **The LangChain ecosystem has integrations with everything** (databases, APIs, model providers).

We compete on architecture, not feature count. We will not "win" on integrations, scale, or observability polish in year one. We can win on architectural correctness and bidirectional NL — both of which compound over time.

### 3.3 Where NeuroLang is genuinely new (no current equivalent)

These rows in the table have no competitor:

- **Plans as first-class values** (table 2.9)
- **Effects in types** (table 2.10)
- **Budget in types** (table 2.11)
- **Categorical mailbox protocols** (table 2.13)
- **Bidirectional NL ↔ formal cached compilation** (tables 2.4, 2.16)
- **3D IDE per categorical dimension** (table 2.14)
- **Hyperdimensional substrate as language primitive** (table 2.3)
- **Differentiable end-to-end flows with categorical kinds** (table 2.18)

Any one of these alone is a publishable contribution. Together, they constitute a new kind of language.

---

## 4. The Strategic Read

**For our existing neurocomputer:** the compatibility is high. The neuros, kinds, flows, brains we have map cleanly onto NeuroLang's primitives. The migration path is *additive, not destructive* — extract the framework, formalise the contracts, add the missing primitives.

**For the public ecosystem:** we are not competing where competition is fiercest (integrations, model availability, scale of vector store). We are competing where the field is shallow — type-level guarantees, plans-as-values, NL surface, categorical correctness. These compound; integrations don't.

**The single most important observation:** our existing system is **architecturally aligned** with NeuroLang. We are not starting from zero. We are formalising, separating, and elevating what we already partly have. That is a much shorter path than greenfield language design.

---

## 5. The Action Implication

Given this comparison, the action sequence is:

1. **Extract** the categorical primitives we already have (`BaseNeuro`, `kinds.py`, `FlowNeuro`, typed bases) from `neurocomputer/` into `neurolang/`. **This is mostly mechanical — the structure already exists.**

2. **Formalise** the categorical contracts (composition laws, effect tracking, budget annotations). **This is where the language is actually born.**

3. **Add** the differentiable substrate (Phase 2 of the construction path) — JAX/PyTorch under the categorical interface, hyperdimensional primitives.

4. **Add** the NL compiler (Phase 3) — bidirectional cached adjunction.

5. **Backport** improvements to neurocomputer as the framework stabilises. The neurocomputer becomes the first production user of NeuroLang.

This is the path that respects what we already have, leverages our existing architectural advantages, and avoids both naïve greenfield rewriting and "Python with extra decorators."

---

*Document at `/docs/COMPARISON.md`. Last reviewed: pre-alpha.*
