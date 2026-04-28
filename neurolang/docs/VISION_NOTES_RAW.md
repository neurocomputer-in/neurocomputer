# Vision Notes — Raw Braindump (2026-04-27)

> **Author:** User (transcribed and organized by assistant)
> **Purpose:** Capture the user's unfiltered vision. Cross-reference against what's already covered in docs/code and what's genuinely new.

---

## The Vision (User's Words, Lightly Cleaned)

### 1. Natural-Language Coding for Everyone
> "I want people to write agentic code, intelligent systems, regular ML model inference, or generic software code — right from their own language like Hindi, English, etc."

### 2. The Language Itself Is Modular and Modifiable
> "We will make everything modular as discussed. The user can modify the language itself to use it — that's better, because that's the best way to reuse."

### 3. Beyond the Linear REPL — 3D NeuroCode IDE
> "Even if we see the REPL, it's linear, one-by-one. We need to make it much more interactive and flexible — like a 3D Neuro IDE, a hyperdimensional graph to manage code. Basically like regular code with modules, libs, classes, methods, and so on."

### 4. NeuroCode IDE — General-Purpose, Not Just Agentic
> "That will evolve to NeuroCode IDE, which can write both agentic code OR general code OR any kind of code using natural language itself. That also will be written or assisted by AI, human-in-the-loop."

### 5. Python Model Integration
> "The user can easily integrate their Python models also, and with the help of NeuroCode and the agent which we will develop using NeuroLang can help write these software also."

### 6. ReAct-Pattern Focus
> "We also need to focus well on the ReAct part very well."

### 7. Robust Coding Agents — Compete with OpenCode / Claude Code
> "We also need to write really robust and reliable agents for coding so that it can pull off tasks complex such as OpenCode and Claude Code, etc. Because our foundations are solid and mathematically grounded, we can make it the best."

### 8. Direct Code Authoring — Not Just NL
> "We also need to give the option for the user to write code directly, instead of only going through the natural language route."

### 9. NeuroLang → NeuroNet → Neurocomputer Pipeline
> "Code created using NeuroLang is actually NeuroNet. Code written using NeuroLang is NeuroNet, and that NeuroNet can be plugged into the Neurocomputer runtime and then it can be run."

### 10. NeuroNet as a Separate, Shareable Repository
> "NeuroNet will have a separate repo. We can write all its aspects, examples, and so on. Users can build a NeuroNet and share it with other people so they can use it. NeuroNet can have examples which can be easily imported — by default into Neurocomputer. People can share, add more, and write their own."

### 11. Neurocomputer = The Hyperdimensional REPL / 3D IDE
> "The Neurocomputer itself is like that hyperdimensional REPL where you design in much higher dimensions, with IDE support, and code is designed — like how we discussed."

---

## Cross-Reference: What's Already Covered?

| # | Vision Point | Status | Where It Lives |
|---|-------------|--------|----------------|
| 1 | NL coding in Hindi/English/voice | ✅ **Covered in architecture + partially built** | [ARCHITECTURE.md §5](file:///home/ubuntu/neurolang/docs/ARCHITECTURE.md) — the NL authoring surface. Code: `compile_source()` already compiles English prompts → Python. Multi-NL input mentioned in Phase 2. REPL `:compile` command works today. |
| 2 | Modular, user-modifiable language | ✅ **Covered in design + partially built** | [COMPARISON.md §2.1](file:///home/ubuntu/neurolang/docs/COMPARISON.md) — neuros are typed, composable units. Code: `@neuro` decorator + `~/.neurolang/neuros/` auto-discovery lets users extend the language with their own modules. Registry + stdlib namespaces (`web`, `reason`, `model`, `voice`) are the modularity system. |
| 3 | 3D Neuro IDE / hyperdimensional graph | 🟡 **Planned but not built** | [ROADMAP.md Phase 3](file:///home/ubuntu/neurolang/docs/ROADMAP.md) — "Web 3D IDE: string-diagram authoring, voice input, live runtime visualization." [ARCHITECTURE.md §5](file:///home/ubuntu/neurolang/docs/ARCHITECTURE.md) — "3D string diagram rendering." [OPEN_DECISIONS.md §G2](file:///home/ubuntu/neurolang/docs/OPEN_DECISIONS.md) — discopy + mermaid rendering shipped for Phase 1; 3D is Phase 3. |
| 4 | General-purpose coding (not just agentic) | 🔴 **NEW — not yet in docs** | Current docs frame NeuroLang as an "agentic coding" framework. The user's vision extends this to **any kind of code** — web apps, data pipelines, CLI tools — all authored via NL. This is a scope expansion beyond what's documented. |
| 5 | Python model integration | ✅ **Covered in architecture** | [ARCHITECTURE.md §4](file:///home/ubuntu/neurolang/docs/ARCHITECTURE.md) — "This is just Python. Nothing exotic." Layer 3 is the full Python ecosystem. Code: `pip install -e ".[all]"` already supports custom deps. Users can wrap any Python model in a `@neuro` decorator and compose it into flows. |
| 6 | ReAct pattern | 🟡 **Partially considered, not deeply built** | [COMPARISON.md §2.9](file:///home/ubuntu/neurolang/docs/COMPARISON.md) mentions "ReAct loops (Yao et al.)" as the competitor approach. NeuroLang's `Plan` as a first-class value supersedes naive ReAct, but a dedicated `reason.react` or `agent.react` neuro implementing the Reasoning+Acting loop is not yet built. `agent.delegate` (next up) is the closest planned feature. |
| 7 | Coding agents rivaling OpenCode / Claude Code | 🔴 **NEW — not yet in docs or roadmap** | No existing doc discusses building a **coding agent** (file editing, terminal commands, codebase understanding, multi-file refactoring). This is a significant new capability that would sit on top of the NeuroLang primitives. |
| 8 | Direct code authoring (bypass NL) | ✅ **Covered in architecture + already works** | [ARCHITECTURE.md §4–5](file:///home/ubuntu/neurolang/docs/ARCHITECTURE.md) — "Three co-equal authoring modes." Layer 2 is direct Python using NeuroLang primitives. Code: users can write `flow = web.search | reason.summarize` in the REPL or in `.py` files today — no NL compilation needed. The `@neuro` decorator, `Flow` class, and `|` operator are the direct-code surface. |
| 9 | NeuroLang → NeuroNet → Neurocomputer pipeline | ✅ **Covered in README + architecture + partially built** | [README.md §The Trinity](file:///home/ubuntu/neurolang/README.md) — NeuroLang is the language, NeuroNet is the runtime graph, Neurocomputer is the execution environment. Code: `NeuroNet` Protocol + `LocalNeuroNet` already exist in `neurolang/runtime/`. Production Neurocomputer runtime is Phase 3. |
| 10 | NeuroNet as separate repo with shareable examples | 🟡 **Partially covered — repo split is new** | [README.md](file:///home/ubuntu/neurolang/README.md) mentions NeuroNet as "inside NeuroLang; production in Neurocomputer." The idea of a **separate `neurocomputer-in/neuronet` repo** with shareable example NeuroNets (importable into Neurocomputer by default) and a community sharing model is **new**. [ROADMAP.md Phase 4](file:///home/ubuntu/neurolang/docs/ROADMAP.md) mentions "Community neuro registry / package manager" which is adjacent but not the same as a shareable NeuroNet repo. |
| 11 | Neurocomputer = hyperdimensional REPL / 3D IDE | ✅ **Covered in architecture + roadmap** | [ARCHITECTURE.md §5](file:///home/ubuntu/neurolang/docs/ARCHITECTURE.md) — "IDE renders the resulting flow as a 3D string diagram." [ROADMAP.md Phase 3](file:///home/ubuntu/neurolang/docs/ROADMAP.md) — "Web 3D IDE: string-diagram authoring, voice input, live runtime visualization." The Neurocomputer repo already exists at `neurocomputer-in/neurocomputer`. |

---

## Gap Analysis: What's Genuinely New Here

### Gap A: General-Purpose NL Coding (Vision Point #4)
**Current framing:** NeuroLang = agentic coding framework.
**User's vision:** NeuroLang = **any** coding, via NL. Web frontends, React apps, data scripts, ML pipelines — all written by speaking/typing intent.

**What this requires:**
- Expanding the stdlib beyond agent-specific neuros to include `code.generate`, `code.refactor`, `code.test`, `code.review`.
- The LLM compiler needs to handle general software generation, not just agentic flow composition.
- The 3D IDE becomes a full-blown development environment, not just a flow visualizer.

### Gap B: Coding Agent Competing with OpenCode / Claude Code (Vision Point #7)
**Current framing:** NeuroLang helps you *compose* agents. It doesn't *be* a coding agent itself.
**User's vision:** Build a coding agent *using* NeuroLang that can autonomously write, refactor, debug, and ship software.

**What this requires:**
- **Code understanding neuros:** `code.parse_ast`, `code.search_codebase`, `code.understand_context`.
- **Code mutation neuros:** `code.edit_file`, `code.create_file`, `code.run_tests`, `code.run_terminal`.
- **Agentic loop:** A `coding_agent` that uses ReAct/Plan-and-Execute to break down coding tasks, write code, run tests, iterate.
- **The meta-play:** This coding agent would itself be written using NeuroLang, proving the framework's power (self-hosting of a sort).

### Gap C: Deep ReAct Integration (Vision Point #6)
**Current status:** `agent.delegate` is next on the roadmap — it does the inner `propose → compile → run` loop.
**Missing:** A first-class `ReAct` pattern — the Reasoning + Acting + Observation loop where the agent alternates between thinking and tool-use, observing results before deciding the next step.

**What this requires:**
- A `reason.react(question, tools=[...], max_steps=10)` neuro or flow pattern.
- The observation loop needs to feed back into the plan (plan modification mid-execution).

### Gap D: NeuroCode IDE as a Full Development Environment (Vision Points #3, #4)
**Current status:** Phase 3 roadmap mentions a 3D IDE for *flow visualization*.
**User's vision:** A full IDE that replaces VSCode — you author code (any code, not just flows) using NL + drag-and-drop + graph manipulation, assisted by AI.

**What this requires (beyond current Phase 3 plans):**
- File tree / project management UI.
- Terminal integration.
- Git integration.
- Code editing with AI assistance (the coding agent from Gap B lives here).
- The "hyperdimensional graph" for navigating modules, classes, and methods visually.

---

## Recommendations

1. **Update ROADMAP.md** to reflect the expanded scope: NeuroLang is not just for agentic coding — it's for **any** NL-authored coding. This changes the pitch from "better LangChain" to "better way to write all software."

2. **Add a new roadmap item** for the coding agent (Gap B). This could be a Phase 2.5 or Phase 3 deliverable: "Build `neurolang-coder` — an autonomous coding agent written entirely in NeuroLang, capable of multi-file editing, test-running, and iterative debugging."

3. **Prioritize `agent.delegate` + ReAct pattern** (already next on STATUS.md). These are the architectural prerequisites for the coding agent.

4. **Rename the 3D IDE plan** from "flow visualization" to "NeuroCode IDE" — a full NL-native development environment. This is the flagship product vision.

---

*Document at `/docs/VISION_NOTES_RAW.md`. This is a living braindump — not canonical architecture. Canonical docs remain ARCHITECTURE.md and ROADMAP.md.*
