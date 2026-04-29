> **⚠ Reframing note (2026-04-30):** Since this document was written, the
> Trinity has been reframed. **NeuroNet is now the *program*** (the compiled,
> runnable, shareable artifact), not the *runtime*. The runtime concept moves
> under Neurocomputer (the environment). See
> [`docs/TRINITY.md`](../../docs/TRINITY.md) for the canonical definition.
> This document retains the old framing in §2 ("The Live Network") and is
> queued for a full rewrite alongside the code rename (tracked in
> [`OPEN_DECISIONS.md`](./OPEN_DECISIONS.md)).

---


# The NeuroLang Framework — The Trinity

> **NeuroLang** (the library) · **NeuroNet** (the live network) · **Neurocomputer** (the IDE + execution environment)
>
> Three names; one system. Each is a different view of the same primitives.

> **Naming alignment:** The existing `neurocomputer` repository (https://github.com/neurocomputer-in/neurocomputer) **is** the reference Neurocomputer. It is the canonical IDE + runtime for NeuroLang programs — the environment where you author, compile, execute, and visualize. Just as a Lisp Machine was both the IDE and the runtime for Lisp, Neurocomputer is both the IDE and the runtime for NeuroLang. Other implementations are possible; ours is the flagship.

---

## 0. The Trinity, In One Picture

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   NeuroLang  ◄────────►  NeuroNet  ◄────────►  Neurocomputer     │
│   (what you write)       (what runs)           (where you author │
│                                                 and execute)     │
│                                                                  │
│   - Python library       - Live graph of      - IDE + runtime    │
│     w/ NL surface          neuros + agents      (one environment)│
│   - Typed primitives       + memory + plans   - VSCode plugin    │
│   - @neuro decorator     - Topology you can   - Web 3D IDE       │
│   - Flow composition       inspect, replay,   - Voice + NL       │
│   - Plans-as-values        mutate             - Live lint        │
│                                                - Compile + run   │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

- **NeuroLang** is the *language layer* — the primitives, the library, the API.
- **NeuroNet** is the *runtime layer* — the live network of running neuros, agents, memories, and plans-in-flight.
- **Neurocomputer** is the *environment layer* — the IDE *and* the runtime, fused. Like a Lisp Machine: you author, compile, execute, and visualize all in one continuous environment. (Reference implementation: the existing `neurocomputer` repo.)

---

## 1. NeuroLang — The Library Layer

The pip-installable Python library. The thing developers (and AI agents) write code against.

### 1.1 Core primitives

| Primitive | What it is | Example |
|-----------|------------|---------|
| `Neuro` | Typed, composable unit | `@neuro(effect="llm") def summarize(...)` |
| `Flow` | Composition of neuros | `fetch \| filter \| summarize` |
| `Plan` | First-class plan object | `plan = flow.plan(args)` |
| `Memory` | Scoped store hierarchy | `Memory.discrete()`, `Memory.differentiable()` |
| `Context` | Read declarations | `@neuro(reads=["user.name"])` |
| `Effect` | Effect tag | `@effect("llm")`, `@effect("tool")`, `@effect("voice")` |
| `Budget` | Cost/latency bound | `@budget(cost_usd=0.01, latency_ms=500)` |
| `Recovery` | Fallback/retry/escalate | `flow.with_fallback(cheaper).with_retry(3).with_escalation(human)` |
| `Mailbox` | Inter-agent messages | `agent.send(message)` |
| `Agent` | Long-lived neuro w/ identity + mailbox | `agent = Agent(role="researcher", memory=...)` |

### 1.2 Authoring feel

The library is designed so that **writing Python with NeuroLang feels close to writing natural language**:

```python
from neurolang import neuro, Flow, Memory, Budget

@neuro(effect="tool")
def fetch_emails(days_back: int = 7) -> list[Email]:
    """Fetch unread emails from the last N days."""
    ...

@neuro(effect="llm", budget=Budget(cost_usd=0.01))
def classify_priority(emails: list[Email]) -> list[Email]:
    """Sort emails by inferred priority."""
    ...

@neuro(effect="llm", budget=Budget(cost_usd=0.02))
def summarize(emails: list[Email]) -> str:
    """Produce a short paragraph summary."""
    ...

# A flow reads like a sentence
weekly_digest: Flow = fetch_emails | classify_priority | summarize
```

### 1.3 Custom neuros — instant, registered, documented

Users (and AI) can write their own neuros that **enter the system instantly**:

```python
from neurolang import neuro, register

@neuro(effect="tool")
def extract_product_reviews(url: str) -> list[Review]:
    """Scrape product reviews from a given Amazon URL."""
    ...

# Available immediately to all flows + the AI agent's context
register(extract_product_reviews)
```

Auto-discovery options:
- **Filesystem**: drop a `.py` in `~/.neurolang/neuros/` → discovered on next run
- **Decorator side-effect**: `@neuro` without explicit register adds to in-process registry
- **Programmatic**: `register(my_neuro)` for fine control

Every registered neuro **carries its own documentation** (docstring, types, effect, budget, examples) — extracted automatically and made available to:
- Other developers (rendered docs)
- AI agents (LLM context)
- The IDE (hover, completion, lint)

### 1.4 The standard library — `neurolang-stdlib`

Ships with high-quality neuros for the common agentic surface:

| Domain | Standard neuros |
|--------|-----------------|
| Web | `skill.web.scrape`, `skill.web.search`, `skill.web.fetch_html` |
| Voice | `skill.voice.call`, `skill.voice.message`, `skill.voice.transcribe`, `skill.voice.synthesize` |
| Email | `skill.email.read`, `skill.email.send`, `skill.email.draft` |
| Calendar | `skill.calendar.read`, `skill.calendar.create`, `skill.calendar.find_slot` |
| Files | `skill.files.read`, `skill.files.write`, `skill.files.search` |
| Reasoning | `skill.reason.brainstorm`, `skill.reason.deep_research`, `skill.reason.classify`, `skill.reason.summarize` |
| Code | `skill.code.read`, `skill.code.diff`, `skill.code.write`, `skill.code.test` |
| Memory | `memory.store`, `memory.recall`, `memory.search` |
| Models | `model.llm.openai`, `model.llm.anthropic`, `model.llm.local`, `model.embed.*` |
| Flows | `flow.dag`, `flow.parallel`, `flow.loop`, `flow.race` |
| Agents | `agent.delegate`, `agent.escalate`, `agent.handoff` |

These are not magic — they are well-typed neuros built using the same primitives as user neuros. The standard library sets the example.

---

## 2. NeuroNet — The Live Network

When NeuroLang code runs, what exists at runtime is **NeuroNet** — a live, inspectable, mutable graph of:

- Running neuros (active executions)
- Agents (long-lived, with mailboxes and persistent memory)
- Memory cells (the store, indexed by scope)
- Plans-in-flight (the structured plan objects, with execution state)
- Effects in motion (LLM calls, tool calls, human approvals pending)

### 2.1 NeuroNet is a first-class object

```python
from neurolang import neuronet

net = neuronet.current()      # the live network in this process
net.agents                    # all running agents
net.plans_in_flight           # active plans
net.memory_scopes             # memory layout
net.effects_pending           # in-progress effects (e.g., awaiting human approval)
net.topology()                # returns a graph object
net.render()                  # visualize as string diagram or 3D
net.snapshot()                # serialize the entire state for replay
```

### 2.2 NeuroNet is inspectable in the IDE

The IDE's runtime view shows:
- **Active flows** as live string diagrams (string color = state: pending, running, complete, errored)
- **Memory** as a side panel with scoped keys + tensors
- **Agents** as nodes with mailbox queue depth
- **Plans** as expandable trees showing what's running, what's done, what's queued
- **Effects** with cost-meter and latency-meter live updates

### 2.3 NeuroNet is replayable

Every run produces an immutable plan snapshot (`Plan.serialize()`). Reload, modify, re-run:
- Identical inputs + identical neuros → identical outputs (modulo LLM stochasticity, which is captured)
- Step-by-step replay for debugging
- Branched replay ("what if I change step 3?")

---

## 3. Neurocomputer — The Authoring Environment

The place where humans + AI compose NeuroLang programs.

### 3.1 Layered authoring (Phase 2 → Phase 3+)

| Phase | Surface | What it is |
|-------|---------|-----------|
| 2 | VSCode + LSP plugin | Colored primitives, hover docs, live lint, NL → code via inline command |
| 2 | CLI | `neurolang compile "summarize my emails"` → produces a `.py` file |
| 3 | Web 3D IDE | String diagram canvas; voice input; drag manipulation |
| 4 | Self-hosted IDE | Built in NeuroLang itself |

### 3.2 Colored primitives — visual signal as you type

Every neuro decorator/usage is **colored by its kind**, so the developer sees the structure of their program at a glance:

| Kind | Visual cue |
|------|-----------|
| `effect="llm"` | Purple highlight (cost-relevant) |
| `effect="tool"` | Green highlight (external side effect) |
| `effect="human"` | Yellow highlight (blocks for approval) |
| `effect="voice"` | Cyan highlight (voice/audio surface) |
| `effect="time"` | Orange highlight (time-aware) |
| `effect="pure"` | No highlight (plain Python) |
| `model.llm.*` | Italic (model invocation) |
| `memory.*` | Underline (memory access) |
| `agent.*` | Bold (agent boundary) |

Flow operators (`|`, `&`, `+`) get distinct colors so composition structure is visually parseable.

### 3.3 Live linting

The LSP server validates as you type:

- **Composition errors:** `fetch_emails | classify_image` → red squiggle ("type mismatch — `list[Email]` cannot feed `Image`").
- **Effect contradictions:** A flow declared `effect="pure"` containing an `llm` neuro → red ("flow contains effect 'llm' not declared").
- **Budget overruns:** `flow.budget()` exceeds annotated bound → yellow warning.
- **Missing neuros:** `web_scrape | nonexistent` → red (suggest similarly-named neuros).
- **Circular imports / dependencies:** flagged at compose time.
- **Runtime hints:** "this neuro has not been used in 30 days; deprecation candidate?"

### 3.4 Natural-language coding

In the IDE:

```
> fetch all unread emails from this week, classify them by priority,
> and send me a summary at 8am tomorrow
```

The LSP/AI:
1. Searches the registered neuros via semantic search
2. Identifies: `fetch_emails` ✓, `classify_priority` ✓, `summarize` ✓, `schedule.daily` ✓
3. Composes a flow
4. Inserts the generated Python at the cursor (with cache hit → identical output for identical prompt)
5. Highlights the flow with the colored primitives above

If a neuro is missing:

```
AI: "I don't have a neuro for 'classify_priority_via_calendar_context'.
     Should I:
     (a) Generate a temporary one for this session
     (b) Generate a permanent one and save to your library
     (c) Suggest you write it manually
     "
```

### 3.5 Documentation as agent context

The IDE's AI assistant always has, in its prompt context:

- The full registered neuro catalog (compressed via semantic embeddings; top-K relevant pulled per query)
- The user's recent conversation
- The current file's flows and types
- The runtime state of NeuroNet (if connected)

**This is the difference between LangChain (where the AI doesn't know what tools exist) and NeuroLang (where the AI knows the entire toolbox and can compose intelligently).**

---

## 4. Agentic Discovery — How AI Finds and Composes Neuros

The killer interaction:

```
USER: "I need to write my master's thesis on the impact of microplastics
       on marine life. Help me build a research workflow."

AI: [searches registered neuros]
    "I found these relevant neuros:
     • skill.reason.deep_research  (multi-source research synthesis)
     • skill.web.scrape            (extract from URLs)
     • skill.web.search            (semantic + keyword search)
     • skill.code.read             (read citation BibTeX files)
     • skill.reason.summarize      (compress long text)
     • skill.reason.brainstorm     (divergent ideation for outline)
     • memory.store                (save findings)
     • agent.delegate              (sub-agents per chapter)

     Proposed flow:

     brainstorm_outline
       | for_each_section (
           web.search → web.scrape → reason.summarize → memory.store
         )
       | reason.deep_research
       | code.write_bibliography

     Estimated cost: $1.20–$3.40 depending on scope.
     Estimated time: ~20 min for first draft outline.

     Want me to:
     (a) Generate this as Python and run it now
     (b) Save as a reusable 'thesis_research' neuro
     (c) Modify the flow first
     "
```

This is what natural-language coding *actually means*. Not "let an LLM hallucinate code" — but **AI proposes a composition of typed primitives the user already has**.

---

## 5. Temporary vs Persistent Neuros

| Kind | Lifecycle | Use case |
|------|-----------|----------|
| **Persistent** | Saved to `~/.neurolang/neuros/` (or a project's `neuros/` dir); loaded on every run | A neuro the user wants to reuse forever |
| **Project-scoped** | Lives in the project repo; checked into git | A neuro tied to one app or thesis |
| **Session-scoped** | In-memory only; flushed when the process ends | AI generates for a single complex task |
| **Ephemeral / streaming** | Built mid-flow, lives only for that flow's execution | One-off transformations |

The user (or AI) chooses the lifecycle when generating. Default for AI-generated: **session-scoped**, with prompt to promote to persistent if used > 3 times.

---

## 6. Voice, Calling, and Multi-Modal

Every neuro can opt into a voice surface:

```python
@neuro(effect="voice")
def voice_call(number: str, prompt: str) -> CallResult:
    """Initiate a voice call and conduct the conversation per `prompt`."""
    ...

@neuro(effect="voice")
def voice_message(audio: AudioBytes) -> str:
    """Transcribe a voice message to text."""
    ...
```

The standard library includes adapters for:
- LiveKit (real-time voice/video)
- Twilio / Plivo (telephony)
- ElevenLabs / OpenAI TTS (synthesis)
- Whisper / Deepgram / Sarvam (transcription)

A flow involving voice is **just a flow** — composes the same way as any other:

```python
incoming_call = receive_call | transcribe | classify_intent | dispatch_agent
```

The IDE shows voice neuros with the cyan highlight; runtime view shows live audio waveforms in NeuroNet.

---

## 7. The Phase 1 Reality Check — What Actually Ships First

Phase 1's job is to **build the bones of the trinity**, not all of it. Concretely:

### 7.1 Phase 1 — NeuroLang library only (4–6 weeks)

Ships:
- `Neuro`, `Flow`, `Plan`, `Memory` (discrete), `Context`, `Effect`, `Budget`, `Recovery` primitives
- `@neuro` decorator + Protocol; in-process + filesystem registry
- Composition operators (`|`, `&`, `+`)
- Property tests for categorical laws
- Basic standard library (~10 neuros to demonstrate the surface): `web.scrape`, `web.search`, `reason.summarize`, `reason.classify`, `memory.store`, `memory.recall`, `model.llm.openai`, `model.llm.anthropic`, `voice.transcribe`, `voice.synthesize`
- Mermaid + discopy rendering
- Documentation extraction tool (`neurolang docs` lists registered neuros)
- Tutorial notebook + example agentic apps

Does NOT ship in Phase 1:
- LLM-based NL compiler (Phase 2)
- VSCode plugin (Phase 2)
- Live linting (Phase 2)
- Differentiable substrate (Phase 2)
- 3D IDE (Phase 3)
- NeuroNet visualization beyond static rendering (Phase 3)

### 7.2 Phase 2 — Neurocomputer basics + NL compiler (4–8 weeks)

- `neurolang compile "..."` CLI
- VSCode plugin: colored primitives, live lint, hover, NL command
- Bidirectional cached compilation
- JAX-backed differentiable backend
- Hyperdimensional substrate
- Soft-attention memory

### 7.3 Phase 3 — Web 3D IDE + full NeuroNet (3–6 months)

- WebGL string diagram authoring
- Voice input → flow generation
- Live runtime visualization of NeuroNet
- Episodic + semantic memory layers
- Decomposable logic library

### 7.4 Phase 4 — Self-hosting + ecosystem (12+ months)

- Compiler is a NeuroLang program
- Community neuro registry
- Production deployment guides
- Plugin / theme ecosystem for the IDE

---

## 8. The Demo That Proves Phase 1 Works

By end of Phase 1, this should run, and run well:

```python
# Pure Python; no NL compiler; no IDE
from neurolang import neuro, Flow, Memory, Budget
from neurolang.stdlib import web, reason, model, memory_neuros

# User defines a custom neuro
@neuro(effect="tool")
def extract_book_metadata(url: str) -> dict:
    """Scrape book title, author, summary from URL."""
    ...

# Compose using stdlib + custom
research_flow: Flow = (
    web.search                    # find candidate URLs
    | extract_book_metadata       # extract info from each
    | reason.summarize            # condense findings
    | memory_neuros.store         # save for later
)

# Inspect
research_flow.render(format="mermaid")  # for the README
research_flow.cost_estimate()           # rolled-up budget
research_flow.effect_signature()        # what effects are involved

# Run
plan = research_flow.plan(query="best books on category theory")
result = plan.run(memory=Memory.discrete())

# Replay
plan.serialize() → "plan.json"
plan.replay()  # deterministic re-execution
```

If a category theorist looks at this and says *"the composition operators are categorically sound"*, AND a working LLM-agent builder says *"I'd actually use this over LangChain"*, **Phase 1 has succeeded.**

---

## 9. Why This Is Now Achievable

We have:

- A **clear three-layer architecture** (NeuroLang / NeuroNet / Neurocomputer)
- A **library-first approach** (no parser, no custom runtime, no language-design failure modes)
- A **categorically-grounded API design** (proven by Lambek, Curry-Howard-Lambek, Coecke et al.)
- **40% of the design already in our heads** (from neurocomputer's experience)
- **A clear demo bar for Phase 1** that's small enough to ship in 4–6 weeks

The risk is no longer "can we build a programming language?" — that risk is gone.

The risk now is "can we build a Python library so well-designed that practitioners adopt it?" — and that is a risk we can manage by being disciplined about Phase 1 scope.

---

*Document at `/docs/FRAMEWORK.md`. This is the consolidated user-facing description of the trinity. Pair with `ARCHITECTURE.md` for the formal architecture decisions and `OPEN_DECISIONS.md` for the unresolved implementation choices.*
