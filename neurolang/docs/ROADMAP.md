# NeuroLang — Roadmap

> The long-term phase plan. Updated only when scope changes.
> For the current state of work, see [`STATUS.md`](./STATUS.md).
> For a chronological log, see [`../CHANGELOG.md`](../CHANGELOG.md).

---

## Mission

Build the Python framework for AI-native agentic coding. Anyone — human or AI — should be able to write robust agents in natural language (Hindi, English, voice) and get back typed, composable, inspectable Python that runs. Underneath: categorically-grounded primitives, plans-as-values, scoped memory, tracked effects, budgeted execution.

Three names, one system:

| | What | Repo |
|---|---|---|
| **NeuroLang** | The Python library | `neurocomputer-in/neurolang` (this) |
| **NeuroNet** | The runtime contract + minimal local impl | inside NeuroLang; production in Neurocomputer |
| **Neurocomputer** | The IDE + production runtime | `neurocomputer-in/neurocomputer` |

---

## Phase Tree

### ✅ Phase 0 — Scaffolding (DONE)
- Repo, pyproject, MIT, smoke test
- Doc set: VISION, RESEARCH, LANDSCAPE, COMPARISON, OPEN_DECISIONS, ARCHITECTURE, FRAMEWORK

### ✅ Phase 1 — Core Library (DONE)
**Goal:** A working, pip-installable categorical core.

Shipped:
- Primitives: `Neuro`, `Flow`, `Plan`, `Memory`, `Effect`, `Budget`, `Recovery`, `Mailbox` (interface only), `Agent` (interface only)
- Composition operators: `|` `&` `+`
- Registry (in-process; FS auto-discovery in P1.5)
- Runtime: `NeuroNet` Protocol + `LocalNeuroNet`
- Mermaid rendering
- Stdlib (minimal): `web.search/scrape`, `reason.summarize/classify`, `memory.store/recall`, `model.llm.openai/anthropic`, `voice.transcribe/synthesize`
- 30 tests passing on categorical laws, plan determinism, effects, budgets, recovery, rendering

### ✅ Phase 1.1 — NL ↔ Python Compiler (DONE)
**Goal:** `neurolang.compile_source("...")` returns runnable Flow. (Originally `neurolang.compile()`; renamed to `compile_source` in Phase 1.6.)

Shipped:
- `compile(prompt)` — NL → validated NeuroLang Python
- `decompile(flow)` — Python → NL summary
- File-based cache (`~/.neurolang/cache/`) keyed by `hash(prompt + model + library_version)`
- AST validation (parses, imports neurolang, declares `flow`)
- Code-fence stripping for sloppy LLM output
- Pluggable LLM (openai / anthropic / custom `llm_fn`)
- CLI: `compile / summarize / catalog / cache`
- 15 new tests — all mocked LLM, fully offline

### 🟡 Phase 1.5 — Power + Polish (CURRENT)
**Goal:** Make NeuroLang feel like a real, helpful language to use day-to-day.

Tasks (in order):
1. **Agentic discovery** — `neurolang plan "..."` proposes a flow + cost preview before compiling. Asks user to confirm. ([details in STATUS.md](./STATUS.md))
2. **Stricter compiler validation** — walk the AST, confirm every referenced neuro exists in the registry. Suggest similar names on miss.
3. **Filesystem auto-discovery** — drop `.py` files in `~/.neurolang/neuros/` or `./neuros/` → loaded into registry on import.
4. **REPL** — `neurolang repl` for interactive composition with completion.
5. **More stdlib** — `agent.delegate`, `agent.escalate`, `reason.deep_research`, `reason.brainstorm`, `voice.call`, `voice.live_room`, `email.*`, `calendar.*`.

### ⬜ Phase 2 — Differentiable + Hyperdimensional Substrate
**Goal:** Flows are end-to-end trainable; HD memory is first-class.

- JAX backend for differentiable primitives
- Hyperdimensional / VSA substrate (Kanerva: bind/bundle/permute)
- Soft-attention memory backend (`Memory.differentiable()`)
- Effect-gradient composition (REINFORCE for non-differentiable; explicit boundaries)
- Decomposable logic library (Boolean / fuzzy / probabilistic / modal)

### ⬜ Phase 3 — Neurocomputer Integration
**Goal:** The existing neurocomputer repo becomes the flagship runtime.

- Refactor neurocomputer to use NeuroLang library
- Production `NeuroNet` implementation in Neurocomputer (persistent, multi-agent, observable)
- Web 3D IDE: string-diagram authoring, voice input, live runtime visualization
- VSCode plugin: colored primitives, live lint, NL command (this was deferred per direction)
- Episodic + semantic memory layers

### ⬜ Phase 4 — Self-Hosting + Ecosystem
**Goal:** The language begins to evolve itself.

- Compiler is itself a NeuroLang program
- Community neuro registry / package manager
- Production deployment guides
- Standard library expansion (community)

### ⬜ Phase 5 — Research Frontier
- Higher-categorical implementations (2-cats, ∞-cats)
- Plan-as-value optimization (gradient over the plan, not just leaves)
- Multi-natural-language parity (Hindi/English/etc. canonical equivalence)
- Self-modifying agents (compiler refines itself via training)

---

## Process Rules — How We Don't Lose Context

This is the rule. Treat it as canonical.

### Three living documents

| Document | Purpose | When updated |
|----------|---------|--------------|
| `ROADMAP.md` (this file) | Long-term plan, phases | Only when scope changes |
| `STATUS.md` | Current state — last task, next task, blockers | **At the end of every working session** |
| `CHANGELOG.md` | Append-only log of shipped features | When a phase or task ships |

### Session protocol

1. **Start of session:** read `STATUS.md`. Get oriented in 30 seconds.
2. **During session:** work on the task at the top of "Next."
3. **End of session:** update `STATUS.md` (move completed → "Just shipped"; pick the new "Next"; capture any open questions).
4. **If a phase ships:** also append to `CHANGELOG.md` and bump status in `ROADMAP.md`.

### What to put in STATUS.md

- Date of last update
- Current phase + sub-task
- Just shipped (last 1–3 things)
- Working on now (if any)
- Next up (the thing that gets done next session)
- Open questions for the user
- Any environmental notes (e.g., "GitHub remote not yet created")

### What NOT to put

- Implementation details (that's in code + CHANGELOG)
- Speculation (that's in research docs)
- Old completed work beyond the last 3 items (that's in CHANGELOG)

### When in doubt

If a future session is unsure what to do next, the order of authority is:

1. The user's explicit instruction in the current message
2. `STATUS.md` "Next up"
3. `ROADMAP.md` current phase
4. Ask the user

---

*Roadmap last updated: 2026-04-26.*
