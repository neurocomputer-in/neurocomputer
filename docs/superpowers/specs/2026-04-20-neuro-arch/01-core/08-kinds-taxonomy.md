# 01-core · 08 · Kinds taxonomy

**Status**: drafted.

---

## 1 · Thesis

Everything in the system is a neuro. But not every neuro has the same job. A **kind** is a labeled, namespaced classification that tells the IDE, planner, and tooling *what this neuro is for* — without changing the runtime contract (every neuro still satisfies `async run(state, **kw) → dict`).

The current spec (as of `07-migration.md`) treats existing neuros as implicit **skill** neuros, and introduces three `kind` values for composition: `sequential_flow`, `parallel_flow`, `dag_flow`. This subdoc generalizes that seam into a full namespaced taxonomy.

## 2 · Kind as namespaced dotted path

`conf.json.kind` becomes a dotted path: `<namespace>.<subtype>` (or just `<namespace>` for the default subtype).

Examples:
```
kind: skill.leaf            # a skill neuro running code.py (default for existing neuros)
kind: skill.flow.sequential # a composite skill flow (was "sequential_flow")
kind: prompt.block          # a fragment of a prompt
kind: prompt.composer       # combines prompt blocks into a final prompt
kind: memory.store          # SQLite-backed persistent store wrapper
kind: memory.recall         # retrieval strategy (keyword, vector, PPR, hybrid)
kind: context.assembler     # builds purpose-specific context slices
kind: model.llm             # provider-specific LLM wrapper
kind: instruction.policy    # a rule/guideline injected into state
kind: agent                 # long-lived session runner
```

### 2.1 · Backward compat

- `kind` values shipped today (`sequential_flow`, `parallel_flow`, `dag_flow`) continue to work unchanged — they're treated as aliases for `skill.flow.sequential` etc.
- Neuros with no `kind` field default to `skill.leaf`.
- No existing neuro requires editing. Additive only.

## 3 · The full taxonomy (v1)

### 3.1 · `skill.*` — the doers (what we have today)

| kind                        | purpose                                          | shape                       |
|-----------------------------|--------------------------------------------------|-----------------------------|
| `skill.leaf`                | runs code.py (fn or class), default              | any BaseNeuro               |
| `skill.flow.sequential`     | ordered pipeline                                 | SequentialFlow              |
| `skill.flow.parallel`       | concurrent fan-out                               | ParallelFlow                |
| `skill.flow.dag`            | interprets a DAG at runtime                      | DagFlow                     |
| `skill.flow.react`          | ReAct orchestrator (future)                      | ReactFlow (`03-react-*`)    |

### 3.2 · `prompt.*` — the instructions-to-models

| kind                  | purpose                                                        |
|-----------------------|----------------------------------------------------------------|
| `prompt.block`        | a single reusable prompt fragment (system, user, example, rule)|
| `prompt.composer`     | assembles multiple blocks into a final prompt                  |
| `prompt.graph`        | a graph of blocks w/ conditional inclusion (future extension)  |

### 3.3 · `memory.*` — the persistent knowledge

(overlaps with `docs/MEMORY_ARCHITECTURE.md` 5-layer model)

| kind                  | purpose                                                  |
|-----------------------|----------------------------------------------------------|
| `memory.store`        | low-level backend (SQLite, Redis, vector DB)             |
| `memory.layer`        | serves a layer (L0 identity / L1 AAAK / L2 taxonomy / etc)|
| `memory.extract`      | LLM-extracts facts from messages                         |
| `memory.categorize`   | routes a fact to a category                              |
| `memory.recall`       | retrieves relevant nodes (keyword / vector / PPR / hybrid)|
| `memory.consolidate`  | merges duplicate categories / superseded facts           |

### 3.4 · `context.*` — the window-builders

| kind                  | purpose                                                  |
|-----------------------|----------------------------------------------------------|
| `context.slice`       | produces one slice (history, env, project-info)          |
| `context.assembler`   | composes slices into a full context for a given profile  |
| `context.profile`     | named profile (router / planner / reply / executor)      |

### 3.5 · `model.*` — the frontier-model wrappers

| kind                  | purpose                                                  |
|-----------------------|----------------------------------------------------------|
| `model.llm`           | chat-completion provider (OpenAI / Anthropic / Ollama)   |
| `model.embedding`     | embedding producer                                       |
| `model.reranker`      | cross-encoder reranker (for hybrid retrieval)            |

### 3.6 · `instruction.*` — the policies / tone

| kind                  | purpose                                                  |
|-----------------------|----------------------------------------------------------|
| `instruction.rule`    | a single policy ("always use markdown")                  |
| `instruction.tone`    | personality anchor (tone, voice)                         |
| `instruction.policy`  | a composed set of rules applied by an agent              |

### 3.7 · `agent` — the session runners

| kind                  | purpose                                                  |
|-----------------------|----------------------------------------------------------|
| `agent`               | long-lived entity handling sessions                      |

### 3.8 · `library` — the bundles

| kind                  | purpose                                                  |
|-----------------------|----------------------------------------------------------|
| `library`             | manifested collection of neuros w/ metadata (future)     |

## 4 · Every kind is fundamentally a hypergraph

Key insight: **within a kind namespace, the neuros of that kind form their own graph.** Compositions are not flat — they can nest arbitrarily.

- `skill.*` neuros compose via `skill.flow.*` — the existing DAG story.
- `prompt.*` blocks compose via `prompt.composer` — a block can reference other blocks → graph.
- `memory.*` nodes + edges literally are a hypergraph (n-ary typed edges per `MEMORY_ARCHITECTURE.md` §2).
- `context.*` slices compose via `context.assembler` — an assembler graph selects + merges slices by profile.
- `model.*` wrappers compose (chain or route) via a `model.router` neuro (future).

The *same fractal rule* applies at every kind: a composite neuro IS a neuro of its kind. So `prompt.composer` is itself a `prompt.*` neuro — can be referenced from a larger composer. Prompt graphs can nest.

### 4.1 · Cross-kind morphisms

When a neuro of kind X calls a neuro of kind Y, it's a **cross-kind morphism**.

Typical patterns:

- A `skill.leaf` (e.g., `reply`) calls a `context.assembler` to build its prompt context.
- The `context.assembler` calls `memory.recall` to enrich context with relevant lessons.
- `memory.recall` calls a `model.embedding` to embed the query.
- The composed chain crosses `skill → context → memory → model` kinds. Each hop is a well-typed call through `factory.run(name, state, **kw)`.

The runtime doesn't branch on kind; the kind is metadata. But **tooling** (IDE, planner, lint) can use kinds to enforce or recommend patterns:

- "Don't have a `skill.leaf` call another `skill.leaf` directly; route through `skill.flow.*`."
- "An `instruction.policy` must be applied before `reply`-kind neuros run."
- "A `memory.recall` should declare `uses: [model.embedding.*]` dependency."

## 5 · Kind parsing rules

- A `kind` is a dotted string: `namespace` or `namespace.subtype` or `namespace.subtype.variant`.
- The **namespace** (first segment) is authoritative — tooling groups on it.
- Subsequent segments are refinements for specificity.
- A kind `"skill"` alone is equivalent to `"skill.leaf"`.
- Unknown kinds are treated as `skill.leaf` (safe default — the runtime doesn't care anyway).

### 5.1 · Validation

- Valid namespaces (v1): `skill`, `prompt`, `memory`, `context`, `model`, `instruction`, `agent`, `library`.
- Factory warns on unknown namespace; still loads the neuro as `skill.leaf` fallback.
- Strict mode (opt-in via env var `NEURO_STRICT_KINDS=1`): unknown namespaces hard-fail at load.

## 6 · Relationship to existing fields

- `scope` remains orthogonal — any kind can declare `call | session | agent | singleton`.
- `uses` remains orthogonal — a neuro of any kind can declare dependencies.
- `category` (IDE folder tree) is independent of `kind` (behavioral classification). A `memory.recall` neuro might have `category: "memory"` or `category: "retrieval"` — pick one for library UX.
- Existing neuros keep working: no `kind` field = defaults to `skill.leaf`.

## 7 · Decisions locked

1. **Kind is a namespaced dotted string** on `conf.json`. Default `skill.leaf`.
2. **Eight top-level namespaces** v1: `skill`, `prompt`, `memory`, `context`, `model`, `instruction`, `agent`, `library`.
3. **Runtime is oblivious to kind** — it's a metadata field, not a runtime branch. Tooling, IDE, and planner use it.
4. **Every kind can form a graph within its namespace** — the fractal composition rule generalizes.
5. **Cross-kind morphisms are routine** — a skill can call a prompt composer can call a memory recall. All via `factory.run`.
6. **Back-compat**: shipped aliases (`sequential_flow`, etc.) preserved; missing `kind` = `skill.leaf`.
7. **Validation is permissive** by default; opt-in strict mode available.

## 8 · Incremental rollout

Land in this order (ship-first slice per kind):

1. **Taxonomy code**: `core/kinds.py` with parser + validator (this subdoc's §5).
2. **Prompt namespace**: `prompt.block` + `prompt.composer` as proof. Small, unlocks reusable prompt fragments immediately.
3. **Context namespace**: migrate `core/context.py` 4 profiles into `context.profile` neuros. Small, demonstrates runtime-unchanged behavior under the new kind.
4. **Memory namespace**: Stage 0 from `MEMORY_ARCHITECTURE.md` — graph substrate + flat L0/L1. Bigger effort.
5. **Model namespace**: `BaseBrain` refactor into `model.llm.openai`, `model.llm.anthropic`, `model.llm.ollama`. Medium effort.
6. **Instruction + Agent namespaces**: come naturally once 1–5 exist.

Each step commits independently. Each step adds tests. Each step preserves existing behavior (additive only).

## 9 · Deferred

- Graph edges between neuros **inside a kind** (e.g., a `prompt.block` referencing another `prompt.block`) as a declared dependency — for now `uses` covers it, but a richer `edges` field may appear in v2.
- Structural schemas per kind (JSON Schema per subtype) — YAGNI until real drift appears.
- Cross-agency kind overrides (this agency uses its own `memory.recall`) — `04-registry-and-lib.md §9` deferred territory.
