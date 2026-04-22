# 01-core · 09 · Kind formats — formal contracts per namespace

**Status**: research + design. Not yet implemented for most kinds.

---

## 0 · Why formal contracts

Every neuro satisfies the same runtime protocol (`async run(state, **kw) → dict`). But the **shape of `**kw` and the return dict** differs per kind — that's what makes a `memory.recall` different from a `prompt.block` even though both are neuros.

Formal contracts buy us:
1. **Typed composition** — IDE + planner can check that a `skill.leaf` calling `memory.recall` passes the right kwargs.
2. **Replaceability** — any `prompt.composer` can be swapped with any other `prompt.composer`; the contract guarantees safe substitution.
3. **Tooling** — the dev-agent can auto-generate a scaffold for any kind because the contract is known.
4. **Cross-kind morphisms** (see §11) — a well-typed `context.assembler → memory.recall → model.embedding` chain is self-documenting.

Every kind in this doc has: **contract · conf.json shape · composition rules · example neuro · existing-neuro backfill · prior art.**

---

## 1 · Universal conventions (every kind)

All neuros share these fields regardless of kind:

| field         | type          | meaning                                                        |
|---------------|---------------|----------------------------------------------------------------|
| `name`        | str (required)| unique identifier                                              |
| `description` | str           | one-line purpose                                               |
| `kind`        | str           | namespaced dotted path (default `skill.leaf`)                  |
| `scope`       | str           | `call` \| `session` \| `agent` \| `singleton` (default per kind)|
| `uses`        | [str]         | declared neuro dependencies, injected as `self.<name>`         |
| `children`    | [str]         | declared ordered children (for composite kinds)                |
| `inputs`      | [port]        | typed input ports                                              |
| `outputs`     | [port]        | typed output ports                                             |
| `category`    | str           | IDE tree folder (free-form dotted path)                        |
| `icon`/`color`| str           | IDE visual metadata                                            |
| `summary_md`  | str           | IDE english-mode description                                   |

Port shape (from `06-typed-io-and-ide-seams.md`):
```json
{"name": "text", "type": "str", "description": "...", "optional": false}
```

---

## 2 · `skill.*` — doers

**Purpose**: execute an action or produce a domain-specific output. The default kind. What most existing neuros are.

### 2.1 · Contract

| subtype                 | `run(state, **kw)` contract                                    |
|-------------------------|---------------------------------------------------------------|
| `skill.leaf`            | arbitrary — kw defined per neuro, returns per neuro           |
| `skill.flow.sequential` | `(state, **kw) → dict` — runs `children` in order, merges     |
| `skill.flow.parallel`   | `(state, **kw) → dict` — runs `children` concurrently, merges |
| `skill.flow.dag`        | `(state, *, dag) → dict` — interprets `dag` at runtime        |
| `skill.flow.react`      | `(state, *, goal, max_steps?, wall_budget_s?) → dict` (future)|

### 2.2 · conf.json shape (pure-conf flow)
```json
{
  "name": "research_flow",
  "kind": "skill.flow.sequential",
  "children": ["search", "rank", "summarize"],
  "uses":     ["search", "rank", "summarize"],
  "inputs":  [{"name": "query", "type": "str"}],
  "outputs": [{"name": "report", "type": "str"}]
}
```

### 2.3 · Composition

- flow children receive the parent's kwargs unchanged.
- each child's return dict is merged into `state` before next runs.
- DagFlow-specific: `params` on each node come from the DAG, not parent kwargs.

### 2.4 · Prior art

- LangChain: Chain, AgentExecutor. Separate class trees; skills ≠ flows.
- LangGraph: state-machine nodes; closer to our model.
- n8n: node + sub-workflow; sub-workflow is second-class.

**Our edge**: `skill.flow.*` *is* a `skill`. Uniform protocol, infinite nesting.

### 2.5 · Existing backfill

Almost every current neuro is `skill.leaf`. Examples: `echo`, `reply`, `planner`, `smart_router`, all `code_*`, all `dev_*`, all `upwork_*`, `unlock_pc`, `screenshot_*`, etc.

---

## 3 · `prompt.*` — model instructions as composable text

**Purpose**: construct the prompt string(s) sent to an LLM. Composable fragments, dynamic substitution, graph-linkable.

### 3.1 · Contract

| subtype           | `run(state, **vars)` contract                                    |
|-------------------|-----------------------------------------------------------------|
| `prompt.block`    | returns `{"text": str}` — renders `template` with `**vars`      |
| `prompt.composer` | returns `{"text": str}` — joins children's `text` with separator|
| `prompt.graph`    | returns `{"text": str, "trace": list}` (future) — conditional composition across a DAG of blocks |

### 3.2 · conf.json shape
```json
{
  "name": "reply_prompt",
  "kind": "prompt.composer",
  "children": ["block_identity", "block_tone", "block_history", "block_lessons"],
  "uses":     ["block_identity", "block_tone", "block_history", "block_lessons"],
  "separator": "\n\n",
  "vars": [
    {"name": "agent",   "type": "str"},
    {"name": "history", "type": "str"}
  ],
  "outputs": [{"name": "text", "type": "str"}]
}
```

For a `prompt.block`:
```json
{
  "name": "block_identity",
  "kind": "prompt.block",
  "template": "You are {{agent}}, a helpful assistant.",
  "vars":    [{"name": "agent", "type": "str"}],
  "outputs": [{"name": "text", "type": "str"}]
}
```

### 3.3 · Composition

- composer → block → (possibly) composer. fractal, same as skill flows.
- block's `template` supports `{{var}}` substitution from `**vars`.
- composer skips blocks that return empty text.
- a block can itself call other neuros (memory.recall for RAG-style prompts) via `uses`.

### 3.4 · Variable resolution rules

1. kwargs passed to composer's `run` are forwarded unchanged to each child.
2. a block may declare `uses: ["memory.recall"]` and pull dynamic content inside its `run` override.
3. circular prompt references (block A uses composer B uses block A) → detected at load time by factory (future: lint pass).

### 3.5 · Prior art

| system      | prompt primitive                  | composable? | graph-capable? |
|-------------|-----------------------------------|-------------|----------------|
| LangChain   | PromptTemplate, ChatPromptTemplate| partial     | no             |
| DSPy        | Signature (python class)          | no (monolithic) | no         |
| Haystack    | PromptBuilder                     | yes         | no             |
| LlamaIndex  | PromptTemplate                    | partial     | no             |
| **ours**    | `prompt.block`/`composer`/`graph` | **yes, fractal** | **yes (composer=graph)** |

### 3.6 · Existing backfill

- `prompt.txt` sibling files in every current neuro → stay as data (simple case).
- For complex / dynamic / reused prompts, promote to `prompt.block` neuros. Start with: `reply`, `code_reply`, `planner`, `dev_planner`, `smart_router`, `neuro_crafter` — each has a substantial `prompt.txt` that would benefit from being decomposed.

### 3.7 · Why graph?

Real prompts have conditional structure: *"if memory has a matching lesson, include it; otherwise fall through to defaults"*. A `prompt.graph` node can express this:
- nodes are `prompt.block`s
- edges carry **inclusion predicates** (resolved via neuro calls)
- the graph walks, evaluates predicates, collects included blocks, composes

Not v1. But the contract reserves room.

---

## 4 · `context.*` — window builders

**Purpose**: assemble the right slice of state (history, memory, env, skills, personality) into a bounded-token context for one specific LLM call (router/planner/reply/executor/…).

### 4.1 · Contract

| subtype             | `run(state, **kw)` contract                                        |
|---------------------|-------------------------------------------------------------------|
| `context.slice`     | returns `{"<slice_name>": str, "tokens": int}` — produces one named slice |
| `context.assembler` | returns `{<slice>: str, …, "tokens": int}` — combines slices, enforces budget |
| `context.profile`   | returns per-profile dict (e.g. `{history, skills, env}` for planner) — a named assembler |

### 4.2 · conf.json shape
```json
{
  "name": "context_planner",
  "kind": "context.profile",
  "profile": "planner",
  "slices": [
    {"name": "history",     "source": "context.slice.history_rolling", "params": {"limit": 10}},
    {"name": "skills",      "source": "context.slice.skills_compact"},
    {"name": "env",         "source": "context.slice.env_state"},
    {"name": "memory_hits", "source": "memory.recall",                  "params": {"top_k": 5}}
  ],
  "token_budget": 6000,
  "outputs": [
    {"name": "history",     "type": "str"},
    {"name": "skills",      "type": "str"},
    {"name": "env",         "type": "str"},
    {"name": "memory_hits", "type": "str"},
    {"name": "tokens",      "type": "int"}
  ]
}
```

### 4.3 · Composition

- an **assembler** calls each slice in order, collects outputs, and enforces `token_budget` via truncation policy (e.g., drop oldest history messages until under budget).
- a **profile** is just a named assembler bound to a use-case (router/planner/reply/executor).
- slices read from: `state["__conv"]`, `state["__env_state"]`, memory neurons, registry, etc.

### 4.4 · Backfill from `core/context.py`

Today `core/context.py` has 4 functions + some helpers:

| today (`core/context.py`)      | new neuro                                              |
|--------------------------------|--------------------------------------------------------|
| `format_messages_compact`      | `context.slice.history_compact` (block)                |
| `format_messages_full`         | `context.slice.history_rolling`                         |
| `build_skills_compact`         | `context.slice.skills_compact`                          |
| `build_router_context`         | `context.profile.router` (assembler)                    |
| `build_planner_context`        | `context.profile.planner`                               |
| `build_reply_context`          | `context.profile.reply`                                 |
| `ensure_history_summary`       | `context.slice.history_summary` (uses model.llm)        |

Keep `core/context.py` as the initial implementation; wrap each fn into a neuro. Later migrations optional.

### 4.5 · Prior art

- LangChain: no direct analog; closest is ConversationBufferMemory + custom templating.
- LlamaIndex: ResponseBuilder, ServiceContext (heavier abstraction).
- Haystack: InMemoryDocumentStore + Retriever for context window.
- **ours**: context is a *neuro*, so it's swappable, overridable per-agent, and graph-trackable in IDE.

---

## 5 · `memory.*` — persistent knowledge

**Purpose**: durable store + retrieval of facts, lessons, categories, entities across sessions and agents.

(Aligns with `docs/MEMORY_ARCHITECTURE.md` 5-layer model — L0 identity, L1 critical, L2 taxonomy, L3 facts, L4 drawers.)

### 5.1 · Contract

| subtype               | `run(state, **kw)` contract                                                  |
|-----------------------|-------------------------------------------------------------------------------|
| `memory.store`        | `(state, *, op, …) → dict` — low-level CRUD on nodes/edges                    |
| `memory.layer`        | `(state) → {"text": str, "tokens": int}` — serves always-loaded layer content|
| `memory.extract`      | `(state, *, messages) → {"facts": [{entity, attr, value, confidence}]}`      |
| `memory.categorize`   | `(state, *, fact) → {"category": str, "new_category": bool}`                 |
| `memory.recall`       | `(state, *, query, top_k?, filters?) → {"items": [node, …], "tokens": int}` |
| `memory.consolidate`  | `(state) → {"merged": int, "renamed": int, "split": int}`                    |

### 5.2 · conf.json shape (for `memory.recall`)
```json
{
  "name": "memory_recall_hybrid",
  "kind": "memory.recall",
  "strategy": "hybrid",
  "uses": ["memory.store.sqlite", "model.embedding.local"],
  "inputs":  [
    {"name": "query",   "type": "str"},
    {"name": "top_k",   "type": "int", "optional": true, "default": 5},
    {"name": "filters", "type": "dict","optional": true}
  ],
  "outputs": [
    {"name": "items",   "type": "list"},
    {"name": "tokens",  "type": "int"}
  ],
  "scope": "singleton"
}
```

### 5.3 · Node format (memory.store schema, already in MEMORY_ARCHITECTURE.md §2)

```sql
CREATE TABLE nodes (
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,            -- "fact" | "entity" | "category" | "turn" | "neuro" | "index"
  content TEXT,
  embedding BLOB,
  props TEXT NOT NULL,           -- JSON
  valid_from TEXT NOT NULL,
  valid_to TEXT,
  created_at TEXT NOT NULL,
  access_count INTEGER DEFAULT 0,
  last_accessed TEXT
);
```

N-ary typed edges (hypergraph-ready) as specified in MEMORY_ARCHITECTURE.md.

### 5.4 · Composition

- `memory.recall` uses `memory.store` for raw read, `model.embedding` for embed, and potentially graph walks (PPR).
- `memory.layer` serves identity/AAAK text → used by `context.slice` or `prompt.block`.
- `memory.extract` called on turn-batch cadence (every 15 msgs) by a background scheduler neuro.

### 5.5 · Existing backfill

Current system has one `memory` neuro (just shipped, SQLite-only). Rename + split:

| today        | new name(s)                        | kind                  |
|--------------|------------------------------------|-----------------------|
| `memory`     | `memory.store.sqlite`              | `memory.store`        |
|              | `memory.recall.keyword`            | `memory.recall`       |
|              | `memory.layer.identity` (static)   | `memory.layer`        |

Stage 0 from MEMORY_ARCHITECTURE.md (graph substrate) → new neuros under `memory.*`.

### 5.6 · Prior art

| system      | memory primitive                          | graph? | temporal? |
|-------------|-------------------------------------------|--------|-----------|
| LangChain   | ConversationBufferMemory + others         | no     | partial   |
| LlamaIndex  | VectorStoreIndex, SummaryIndex            | partial| no        |
| Mem0        | vector + entity graph                     | yes    | partial   |
| Zep         | temporal KG + vectors                     | yes    | yes       |
| MemPalace   | SQLite temporal KG (fixed taxonomy)       | yes    | yes       |
| **ours**    | uniform node/edge hypergraph + LLM librarian | yes | yes + emergent taxonomy |

---

## 6 · `model.*` — frontier model wrappers

**Purpose**: call external models (LLM chat, embedding, reranker) through a uniform neuro protocol so the specific provider/model is swappable via config.

### 6.1 · Contract

| subtype           | `run(state, **kw)` contract                                                            |
|-------------------|----------------------------------------------------------------------------------------|
| `model.llm`       | `(state, *, messages, tools?, temperature?, json_mode?) → {"content": str, "tool_calls": [...]?, "thinking": str?}` |
| `model.embedding` | `(state, *, text) → {"vector": [float], "dim": int}`                                  |
| `model.reranker`  | `(state, *, query, candidates) → {"ranked": [{"item": ..., "score": float}]}`         |

### 6.2 · conf.json shape
```json
{
  "name": "model_llm_openai",
  "kind": "model.llm",
  "provider": "openai",
  "default_model": "gpt-4o-mini",
  "env_key": "OPENAI_API_KEY",
  "base_url": null,
  "scope": "singleton",
  "inputs":  [
    {"name": "messages",    "type": "list"},
    {"name": "tools",       "type": "list", "optional": true},
    {"name": "temperature", "type": "float","optional": true, "default": 0.7},
    {"name": "json_mode",   "type": "bool", "optional": true, "default": false}
  ],
  "outputs": [
    {"name": "content",     "type": "str"},
    {"name": "tool_calls",  "type": "list","optional": true},
    {"name": "thinking",    "type": "str", "optional": true}
  ]
}
```

### 6.3 · Composition

- any `skill.leaf` needing an LLM declares `uses: ["model.llm"]` (or a specific provider).
- agent profile can override which `model.llm` concrete neuro is used via config.
- `model.embedding` used by `memory.recall`.
- `model.reranker` is optional; used in hybrid retrieval.

### 6.4 · Existing backfill

`core/base_brain.py` → set of `model.llm.<provider>` neuros:
- `model.llm.openai`
- `model.llm.anthropic`
- `model.llm.openrouter`
- `model.llm.ollama` (local Gemma4 per user's setup)
- `model.llm.sarvam` (if used)

`BaseBrain` stays as an internal SDK wrapper; the neuros wrap it.

### 6.5 · Prior art

- LangChain: `BaseLLM`, `BaseChatModel` — hierarchies; one subclass per provider.
- LlamaIndex: `LLM` abstraction.
- DSPy: `LM` class.
- **ours**: model IS a neuro. can be A/B-tested, chain-routed, logged, and edited by the dev-agent.

---

## 7 · `instruction.*` — policies / tone

**Purpose**: first-class "rules the agent follows". Injected into prompts, consulted by planners, visible in IDE as behavior modifiers.

### 7.1 · Contract

| subtype               | `run(state, **kw)` contract                                 |
|-----------------------|-------------------------------------------------------------|
| `instruction.rule`    | `(state) → {"text": str, "category": str, "priority": int}` |
| `instruction.tone`    | `(state) → {"text": str, "voice": str}`                     |
| `instruction.policy`  | `(state) → {"rules": [rule_dict]}` — composite bundle       |

### 7.2 · conf.json shape
```json
{
  "name": "rule_markdown_output",
  "kind": "instruction.rule",
  "category": "formatting",
  "priority": 50,
  "template": "Respond in markdown.",
  "outputs": [{"name": "text", "type": "str"}]
}
```

### 7.3 · Composition

- policy assembles rules by category + priority.
- prompts include policy via `uses: ["instruction.policy"]` and embed rules as `prompt.block` children.
- agent profiles declare which policies apply.

### 7.4 · Why this is distinct from `prompt.block`

A `prompt.block` is text. An `instruction.rule` is a *structured behavior constraint* — it has category, priority, can be toggled, and may be consulted by planners (not just by prompts). Conflating them loses that.

### 7.5 · Existing backfill

Today implicit in `prompt.txt` files ("Always reply in markdown", "Be concise", etc.). Extract into `instruction.rule` neuros for reuse + visibility.

---

## 8 · `agent` — session runners

**Purpose**: long-lived entity that accepts user input and runs sessions. What `core/brain.py` + `core/agency.py` currently implement as classes.

### 8.1 · Contract

```
agent.run(state, *, user_text, cid, **kw) → {"reply": str, "events": [...]}
```

- stateful (session-scoped instance).
- manages conversation, profile, memory, task launches.
- emits events via `state["__pub"]`.

### 8.2 · conf.json shape
```json
{
  "name": "agent_neuro",
  "kind": "agent",
  "profile": "general",
  "uses": [
    "memory.recall.hybrid",
    "context.profile.reply",
    "instruction.policy.default",
    "model.llm.openrouter"
  ],
  "default_planner": "planner",
  "default_replier": "reply",
  "scope": "agent"
}
```

### 8.3 · Composition

- one agent neuro = one personality/config bundle.
- sessions multiplex under the agent (`InstancePool` scope=`agent`).
- multi-agent: just have multiple `kind: agent` neuros.

### 8.4 · Existing backfill

- `core/brain.py` class → `agent.neuro` neuro.
- `core/agent.py` (WIP) + `core/agency.py` → `agent.*` neuros with profiles.
- `openclaw_delegate` / `opencode_delegate` → stay as `skill.leaf` (they're *wrappers around external agents*, not native agents).

---

## 9 · `library` — bundled collections

**Purpose**: a manifest/package of related neuros that can be imported as a unit. Deferred v1; format reserved.

```json
{
  "name": "upwork_pack",
  "kind": "library",
  "exports": ["upwork_analyze", "upwork_proposal", "upwork_list", "..."],
  "version": "0.1.0"
}
```

No runtime effect yet. Future: `lib/<pack>/` tree + `pack.json` — see `04-registry-and-lib.md §8`.

---

## 10 · `code.*` — coding workflows (NEW)

**Purpose**: first-class classification for the code-editing workflow. Captures common coding operations as kinds so a code-focused agent knows where to look.

### 10.1 · Why a separate namespace

Today `code_*` is a **naming convention** (`code_file_read`, `code_file_write`, …). Promoting to `kind: code.*` gives:
- IDE grouping (library tree by kind)
- Planner hints ("for a coding task, prefer `code.*` neuros")
- Substitution via contract (any `code.read` can replace another `code.read`)

### 10.2 · Contract

| subtype            | `run(state, **kw)` contract                                                      |
|--------------------|---------------------------------------------------------------------------------|
| `code.read`        | `(state, *, path, range?) → {"text": str, "lang": str, "lines": int}`          |
| `code.write`       | `(state, *, path, content, mode?) → {"ok": bool, "bytes": int}`                |
| `code.patch`       | `(state, *, path, diff) → {"ok": bool, "hunks_applied": int}`                  |
| `code.scan`        | `(state, *, root?, query?) → {"matches": [{"path", "line", "snippet"}]}`       |
| `code.index`       | `(state, *, root?) → {"symbols": int, "refs": int, "index_id": str}`           |
| `code.lint`        | `(state, *, path) → {"issues": [{"line", "severity", "rule", "message"}]}`      |
| `code.test`        | `(state, *, path?, pattern?) → {"passed": int, "failed": int, "log": str}`    |
| `code.plan`        | `(state, *, goal, repo_ctx?) → {"plan": {"steps": [...]}}`                      |
| `code.review`      | `(state, *, diff, style_rules?) → {"findings": [...]}`                          |
| `code.diff`        | `(state, *, before, after) → {"diff": str, "lang": str}`                        |

### 10.3 · conf.json shape (example)
```json
{
  "name": "code_file_read",
  "kind": "code.read",
  "category": "code.file_ops",
  "icon": "file-code",
  "inputs":  [
    {"name": "path",  "type": "file_path"},
    {"name": "range", "type": "dict", "optional": true, "description": "{start, end}"}
  ],
  "outputs": [
    {"name": "text",  "type": "str"},
    {"name": "lang",  "type": "str"},
    {"name": "lines", "type": "int"}
  ]
}
```

### 10.4 · Composition — a "coding assistant agent"

```
agent.coder (kind=agent)
 └─ uses:
     memory.recall.codebase        # repo-specific memory
     context.profile.code          # code-focused context (file, diff, tree)
     code.scan                     # find relevant files
     code.read                     # read before edit
     code.plan                     # multi-step plan
     code.patch / code.write       # apply
     code.test                     # verify
     code.review                   # self-review before commit
     model.llm.anthropic           # strong model for code
```

### 10.5 · Existing backfill (concrete)

| today                         | proposed kind         | notes                                    |
|-------------------------------|-----------------------|------------------------------------------|
| `code_file_read`              | `code.read`           | shape matches                            |
| `code_file_write`             | `code.write`          | shape matches                            |
| `code_file_diff`              | `code.diff`           |                                          |
| `code_file_list`              | `code.scan`           | (subtype: list mode)                     |
| `code_scan`                   | `code.scan`           |                                          |
| `code_reader_with_context`    | `code.read` (enriched)| or keep as skill.leaf; needs more thought|
| `code_project_manager`        | `skill.leaf`          | session-level ops, not an atomic code op |
| `code_planner`                | `code.plan`           |                                          |
| `code_reply`                  | `skill.leaf`          | it's a responder, not a code op          |
| `write_file`                  | `code.write`          | generalize alias                         |
| `delete_file`                 | `code.write` variant  | or `code.delete` subtype                 |
| `dev_diff`                    | `code.diff`           |                                          |
| `dev_patch`                   | `code.patch`          |                                          |
| `dev_codegen`                 | `code.plan` → generates| or `skill.leaf` if non-trivial shape    |

Non-code `dev_*` (dev_new, dev_save, dev_edit, dev_reset) stay in the dev-agent track — they're about editing neuros, not user code. May eventually warrant their own `dev.*` kind.

### 10.6 · Prior art

- **Cursor** / **Claude Code** / **SWE-agent**: treat code ops as tool calls with typed args (path, range, diff). Our `code.*` kinds formalize the same idea.
- **aider**: git-based diff-apply loop; our `code.patch` maps there.
- **Sourcegraph / Cody**: scan + read as primary ops; matches `code.scan` / `code.read`.

### 10.7 · Why formalize now

The coding workflow is one of the most valuable end-to-end uses of the system. Giving it a proper kind namespace:
- lets a `code.plan` planner be generic across repos
- lets `code.test` be swapped (pytest, jest, go test) per language
- lets the IDE show a "code workflow" tree distinct from other skills

---

## 11 · Composition matrix — who calls whom

Typical call patterns (arrows = "uses"):

```
agent ──▶ context.profile ──▶ context.slice(s) ──▶ memory.recall ──▶ memory.store
                                               └─▶ model.embedding
agent ──▶ skill.flow.*   ──▶ skill.leaf(s)    ──▶ model.llm
agent ──▶ instruction.policy ──▶ instruction.rule(s)
prompt.composer ──▶ prompt.block ──▶ (sometimes) memory.recall
code.plan ──▶ code.scan + code.read + code.patch + code.test + model.llm
memory.extract ──▶ model.llm
memory.categorize ──▶ model.llm + memory.store
```

Rules:
- no cycles allowed (enforced at graph-build time; factory load-time check future).
- `model.*` is a *leaf* kind — it never calls other neuros (it IS the external boundary).
- `memory.store` is a *leaf* kind — it's the storage boundary.
- `instruction.*` is typically *consumed* by prompts, rarely consumed by other instructions.

---

## 12 · Graph dimension per kind

Each kind has its own internal graph structure (per user's "hyperdimensional graph" framing):

| kind           | graph nodes                    | graph edges                       | graph purpose                    |
|----------------|--------------------------------|-----------------------------------|----------------------------------|
| `skill.*`      | skill.leaf neuros              | DagFlow edges (start/next)        | execution order                  |
| `prompt.*`     | prompt.block neuros            | composer children + conditional   | prompt assembly                  |
| `context.*`    | context.slice neuros           | assembler ordering                | context layout                   |
| `memory.*`     | fact/entity/category nodes     | n-ary typed edges (hypergraph)    | knowledge graph                  |
| `model.*`      | single neuro (usually)         | n/a (leaf boundary)               | external boundary                |
| `instruction.*`| rule neuros                    | policy membership                 | behavior constraints             |
| `agent`        | single neuro (usually)         | uses dependencies                 | agent personality bundle         |
| `code.*`       | code op neuros                 | code.plan step order              | coding workflow                  |

→ every kind has a graph. but the *type* of graph differs. unified substrate, differentiated semantics.

---

## 13 · Validation (future factory upgrade)

Once formats are locked, the factory can enforce on load:

1. **Required fields** per kind (e.g., `prompt.block` requires `template` OR a `code.py`).
2. **Typed inputs/outputs match contract** per subtype.
3. **`uses` declarations valid** and not cyclical.
4. **`scope` compatible** with kind semantics (e.g., `model.llm` should be `singleton`, warning otherwise).

Kept permissive by default (warn, don't fail), strict mode via env var `NEURO_STRICT_KINDS=1`.

---

## 14 · Decisions locked (by this doc)

1. **Every kind has a formal contract** — specified in §2–§10.
2. **`code.*` is a new kind namespace** — formalizing what's today a naming convention.
3. **Existing neuros backfill** — non-breaking; adds `kind` field, no code change required.
4. **Composition matrix** (§11) is the informal lint rule; formal enforcement in future.
5. **Graph dimension** (§12) is explicit per-kind — aligns with the "hyperdimensional graph" vision.
6. **Validation deferred to strict-mode flag** — ship permissive default.

## 15 · Open questions / deferred

- Should `code.patch` fail-atomic (all hunks or none) or partial-ok?
- How does `memory.recall` rank mixed-modality hits (text + embedding + graph)?
- Should `agent` kind support agent-calls-agent (multi-agent routing)? yes eventually; scope out in agent spec.
- `instruction.rule` priority semantics — numeric (like CSS z-index) or topological?
- `prompt.graph` inclusion predicates — expression language or just neuro-call boolean?
- Do we need `model.streaming` as a subtype or is it a flag on `model.llm`? (probably a flag.)

---

## 16 · Implementation order (recommended after this doc locks)

1. **Backfill existing neuros** (`10-kind-backfill.md`) — add `kind` field to ~60 conf.json files. purely metadata, no behavior change. ship in one commit.
2. **`code.*` kind** — promote `code_*` neuros to `kind: code.*` during backfill.
3. **`context.profile.*`** — migrate `core/context.py` 4 functions into neuros. small, proves context-as-neuro.
4. **`model.llm.*`** — extract BaseBrain into `model.llm.<provider>` neuros. medium.
5. **`memory.*` Stage 0** — the MEMORY_ARCHITECTURE.md substrate.
6. **`instruction.*`** — extract policies from existing prompt.txt files.
7. **`agent`** — finish core/agency.py + agent.py refactor to `kind: agent`.

Each step committable + testable on its own.
