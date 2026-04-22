# Memory Architecture — Design Spec

**Status**: Draft (brainstorming, not yet implemented)
**Last Updated**: 2026-04-21
**Scope**: Single-user, personal, long-lived, local-first
**Inspired by**: MemPalace (2026-04), A-MEM, Mem0, Zep — adapted to neurocomputer's fractal-neuro architecture

---

## 0. Goals & Philosophy

### What we want the memory system to do

1. **Persist across conversations.** Today each `conversations/<cid>.json` is isolated. Facts the user tells us in one session are forgotten in the next.
2. **Scale to years of use** without prompt-bloat. Cheap always-loaded footprint, deep recall on demand.
3. **Organize itself.** No hardcoded taxonomy. The system's librarian (a local LLM) creates, merges, and renames categories as the corpus grows.
4. **Stay local-first and private.** Runs on Ollama + Gemma4 E4B (already installed). No cloud fact extraction.
5. **Unify with neuros.** Memory nodes and neuros live on the same graph substrate. Skills, observations, and facts are one queryable fabric.
6. **Preserve verbatim source.** Never destructively summarize. Closets (summaries) reference drawers (originals).

### Non-goals (explicitly out of scope)

- Multi-tenancy, ACL, team sharing
- Training large models from memory data
- Real-time streaming memory across agent fleets
- Absolute global consistency (eventual is fine)

### Design philosophy — three pillars

- **Modular**: each memory capability is a neuro (extract, categorize, recall, save, forget, consolidate). Substrate code is thin; behavior is neuros.
- **Hierarchical**: MemPalace-style L0–L4 with bounded token budgets per layer. Cheap recall first, expensive recall only when needed.
- **Taxonomical but emergent**: categories exist and are used as a query prior — BUT the taxonomy is maintained by an LLM librarian, not hardcoded, and grows with the data.

---

## 1. Architecture Overview

### The 5 layers

| Layer | Name | Content | Token cost | Load trigger | Writer | Maintainer |
|---|---|---|---|---|---|---|
| **L0** | Identity | Core agent identity + user identity (hand-authored) | ~50 | always | human | human |
| **L1** | Critical facts | Top-priority facts in AAAK-compressed form | ~120 | always | LLM (nightly) | LLM (consolidation) |
| **L2** | Categories | Taxonomy tree: wings / rooms / halls. Names + one-line defs. | ~200 | always (as index) | LLM on new fact | LLM weekly merge pass |
| **L3** | Facts | Structured facts in temporal KG + embedding | dynamic | on topic relevance | extractor neuro | consolidator neuro |
| **L4** | Drawers | Verbatim source (existing `conversations/*.json`) | dynamic | explicit deep-dive | existing code | never touched (lossless) |

**Always in prompt:** L0 + L1 + L2-index ≈ **370 tokens**.
**Loaded on match:** L3 slice relevant to query (~500–2000 tok).
**Loaded on deep-dive:** L4 drawer excerpts via vector/keyword (~1000–4000 tok).

### Mental model

```
┌─────────────────────────────────────────┐
│ L0 identity   (who am I, who is user)   │  always loaded
│ L1 facts      (AAAK top-20 facts)       │  always loaded
│ L2 taxonomy   (categories + 1-line defs)│  always loaded
├─────────────────────────────────────────┤
│ L3 facts      (temporal KG + vectors)   │  loaded on topic match
├─────────────────────────────────────────┤
│ L4 drawers    (verbatim raw JSONs)      │  loaded on deep-dive only
└─────────────────────────────────────────┘
```

### Why layered

- Bounds token cost. Context window is precious — don't burn it on facts the user isn't asking about.
- Matches human cognition (working set vs recall vs archive).
- Cheap common case (L0–L2 covers 80% of turns).
- Lossless fallback (L4 always exists for deep recall).

---

## 2. Storage Substrate

### Graph-first, hierarchy-as-view

**Decision**: underlying storage is a **typed property graph** from day one. The 5-layer hierarchy is a *query pattern*, not a schema constraint. This keeps the door open for hypergraph evolution without migration.

### Tables (SQLite — embedded, no server)

```sql
-- Every "thing" in memory is a node. Uniform type.
CREATE TABLE nodes (
  id          TEXT PRIMARY KEY,         -- uuid
  kind        TEXT NOT NULL,            -- "fact" | "entity" | "category" | "turn" | "neuro" | "index"
  content     TEXT,                     -- verbatim text; null for pure-structural nodes
  embedding   BLOB,                     -- float32[d]; null for structural nodes
  props       TEXT NOT NULL,            -- JSON
  valid_from  TEXT NOT NULL,            -- ISO ts
  valid_to    TEXT,                     -- ISO ts; null = still valid
  created_at  TEXT NOT NULL,
  access_count INTEGER DEFAULT 0,
  last_accessed TEXT
);

-- N-ary typed edge (binary is just n=2). Hypergraph-ready.
CREATE TABLE edges (
  id          TEXT PRIMARY KEY,
  nodes       TEXT NOT NULL,            -- JSON array of node_ids
  roles       TEXT NOT NULL,            -- JSON array parallel to nodes
  type        TEXT NOT NULL,            -- "part_of" | "owns" | "caused_by" | "supersedes" | ...
  weight      REAL DEFAULT 1.0,
  props       TEXT,
  valid_from  TEXT NOT NULL,
  valid_to    TEXT,
  created_at  TEXT NOT NULL
);

CREATE INDEX idx_nodes_kind       ON nodes(kind);
CREATE INDEX idx_nodes_valid      ON nodes(valid_to);
CREATE INDEX idx_edges_type       ON edges(type);
CREATE INDEX idx_edges_valid      ON edges(valid_to);
-- vector index via sqlite-vss or chromadb sidecar on nodes.embedding
```

### Why this schema

- **Uniform node type**: no subclass proliferation. `kind` is a tag, not a class. Matches fractal-neuro spec (every neuro = same type).
- **Temporal validity**: `(valid_from, valid_to)` on both nodes and edges. Lets us model changing state ("Kai was owner until 2026-04-20, then Pri took over").
- **N-ary edges**: `nodes` is an array, not src/dst. A "meeting" hyperedge links `[Kai, Pri, auth_refactor, 2026-04-20]` as one unit. Binary edges fall out as the n=2 case.
- **No wing/room/hall tables**: those become **labeled index nodes** (`kind="category"`), linked to their members via `part_of` edges. Taxonomy is data, not schema.

### Storage stack

| Store | Use | Why |
|---|---|---|
| SQLite (`nodes`, `edges`) | source of truth | embedded, familiar, temporal queries |
| sqlite-vss **or** ChromaDB | vector index on `nodes.embedding` | ANN search for L3 retrieval |
| NetworkX (in-memory, rebuilt) | graph walks (PPR, BFS) | fast on working subset |
| `mem/l0.md`, `mem/l1.aaak` | flat files | human-editable, always-loaded |
| `conversations/*.json` (existing) | drawers | zero migration, already verbatim |

---

## 3. LLM-as-Librarian — Emergent Taxonomy

### The core insight

MemPalace hardcodes `hall_facts`, `hall_events`, `hall_discoveries`, `hall_prefs`, `hall_advice`. Works okay but fights your actual domain. **We let a local LLM propose, merge, split, and rename categories as it sees data.**

This replaces the rigid schema with a **self-organizing palace**.

### What the LLM does vs what code does

| Job | Owner | Frequency | Model |
|---|---|---|---|
| Extract facts from msgs | LLM (`memory_extract` neuro) | after every turn-batch | Gemma4 E4B local |
| Route fact to category | LLM (`memory_categorize` neuro) | per new fact | Gemma4 E4B local |
| Invalidate superseded facts | LLM (`memory_supersede` neuro) | on contradiction | Gemma4 E4B local |
| Refresh L1 critical facts | LLM (`memory_l1_refresh`) | nightly | Gemma4 E4B local |
| Merge duplicate categories | LLM (`memory_consolidate`) | weekly | Gemma4 E4B local |
| Split bloated categories | LLM (`memory_split`) | when cat size > 200 | Gemma4 E4B local |
| Rename unclear categories | LLM (`memory_rename`) | weekly | Gemma4 E4B local |
| Graph walk / retrieval | code (PPR + vector hybrid) | every read | no LLM |
| Storage / schema / indexing | code | always | no LLM |

### Initial taxonomy seeds (bootstrapping)

Start with MemPalace-inspired seeds so cold-start isn't empty:

- `hall_facts` — decisions, durable truths
- `hall_events` — things that happened, sessions
- `hall_discoveries` — insights, breakthroughs
- `hall_preferences` — user preferences, habits
- `hall_people` — entities (people, teams)
- `hall_projects` — project-level nodes

LLM can create new categories beside these. Seeds are just warm-start, not hardcoded.

---

## 4. Write Flow

### On every user↔assistant turn

```
[user msg + assistant response arrive]
        │
        ▼
  append to conversation (existing code, drawer)
        │
        ▼
  check: is it time to extract?  (every N turns, e.g. 15)
        │                   no → done
        yes
        ▼
┌─────────────────────────────────────────────┐
│ memory_extract neuro (Gemma4 local)         │
│  prompt: "emit durable facts as JSON,        │
│   skip chitchat, return []"                  │
└─────────────────────────────────────────────┘
        │ facts: [{entity, attr, value, confidence}, ...]
        ▼
  for each fact:
   ┌───────────────────────────────────────────┐
   │ embed fact content                         │
   │ top-3 nearest existing categories (vector) │
   │                                            │
   │ if nearest cosine > 0.85:                  │
   │     auto-assign to that category           │
   │ else:                                      │
   │   memory_categorize neuro:                 │
   │    prompt: "here are top-3 candidates.     │
   │     does this fit one? or propose new      │
   │     name + 1-line def. JSON answer."       │
   │                                            │
   │ if new category:                           │
   │     create node(kind="category")           │
   │     embed category name+def                │
   │                                            │
   │ create node(kind="fact", content=...)      │
   │ create edge(part_of, [fact, category])     │
   │                                            │
   │ check for contradiction with existing:     │
   │   if entity+attr already has value:        │
   │     memory_supersede:                      │
   │      "do these conflict? JSON {yes/no}"    │
   │     if yes: close old edge valid_to=now    │
   └───────────────────────────────────────────┘
        │
        ▼
  persist to SQLite + vector index
```

### Cadence and batching

- Extraction runs **every 15 msgs** (MemPalace cadence) or on PreCompact hook — not per-msg. Reduces LLM calls.
- One extraction call yields multiple facts in one LLM round-trip.
- Categorization batched: send all new facts + all existing cats once, get back routing map.

---

## 5. Read Flow

### On every new user turn

```
[user turn arrives]
        │
        ▼
  L0 + L1 + L2-index already in prompt (always loaded)
        │
        ▼
  embed user msg
        │
        ▼
  retrieval pipeline (hybrid, no LLM):
   ┌───────────────────────────────────────────┐
   │ 1. seeds = top-k nearest nodes (vector)   │
   │    + entities mentioned in user msg       │
   │                                            │
   │ 2. Personalized PageRank from seeds        │
   │    edge weights = recency × confidence     │
   │    restart prob 0.15                       │
   │                                            │
   │ 3. candidates = top-M nodes by PPR score   │
   │                                            │
   │ 4. temporal filter: valid_to IS NULL       │
   │    OR valid_to > now                       │
   │                                            │
   │ 5. pack_greedy(candidates, token_budget)   │
   │    dedupe by category                      │
   │                                            │
   │ 6. if packed confidence low:               │
   │      L4 fallback: keyword+vector over      │
   │      drawers; return excerpts w/ provenance│
   └───────────────────────────────────────────┘
        │
        ▼
  inject into context.py build_*_context():
   - router:  1 hit
   - planner: 3 hits
   - reply:   5 hits
        │
        ▼
  tag every inserted slice with provenance:
   "[from fact #abc, valid 2026-04-01..now, cat:hall_projects]"
```

### Why PPR + vector hybrid, not GNN

- Single-user scale. GNN needs training labels we won't have for years.
- PPR is parameter-free, interpretable, handles multi-hop.
- Vector handles "semantically similar" where graph has no direct edge.

---

## 6. Modularity — Everything is a Neuro

### Memory neuros (new)

| Neuro | Purpose | Called by |
|---|---|---|
| `memory_extract` | msgs → facts JSON | brain after each turn-batch |
| `memory_categorize` | route fact to category (or propose new) | write pipeline |
| `memory_supersede` | detect contradiction, close old valid_to | write pipeline |
| `memory_recall` | user-facing semantic query | user ("what did we decide about X?") |
| `memory_save` | explicit save ("remember that Y") | user |
| `memory_forget` | explicit delete | user |
| `memory_browse` | show categories / wings / rooms | user or planner |
| `memory_consolidate` | merge/rename categories | cron (weekly) |
| `memory_l1_refresh` | regenerate AAAK L1 file | cron (nightly) |
| `memory_split` | split bloated categories | cron (on threshold) |

All follow the existing `neuros/*/conf.json` pattern. All use Gemma4 E4B local for cheap/private ops.

### Substrate code (new)

- `core/memory/__init__.py` — facade
- `core/memory/node.py`, `edge.py` — data classes
- `core/memory/store.py` — SQLite + vector wrapper
- `core/memory/walk.py` — PPR, BFS, hybrid retrieval
- `core/memory/aaak.py` — AAAK compress/decompress helpers
- `core/memory/hooks.py` — turn-count & pre-compact triggers

### Integration points (changes to existing code)

- `core/context.py` — `build_*_context()` funcs prepend L0+L1+L2-index, append retrieved L3 slices
- `core/brain.py` — after each turn, fire `memory_extract` async (non-blocking)
- `core/conversation.py` — on load, register conv's turns as nodes (lazy, optional)
- `core/neuro_factory.py` — register new memory neuros

---

## 7. Hierarchy Rules (Taxonomy Discipline)

### Category bounds

- Max categories per parent: **20** (soft cap — LLM prompted to split beyond)
- Max facts per category: **200** (triggers auto-split)
- Max depth: **4 levels** (prevents pathological trees)
- Orphan categories (< 3 facts after 30 days) flagged for merge

### Naming discipline

- Categories named with lowercase snake_case: `hall_facts`, `project_neurocomputer`, `pattern_debugging`
- Definition line required (≤ 80 chars)
- LLM weekly pass renames unclear ones

### Supersession rules

- New fact about same `(entity, attr)` pair → LLM decides: conflict or refinement?
- If conflict: old edge `valid_to = now`, new edge created
- If refinement (same value, more detail): update props, no new edge
- Never delete — always supersede (preserves history)

---

## 8. Failure Modes & Mitigations

| Risk | Mitigation |
|---|---|
| **Category drift** (duplicates: "backend" vs "server") | Always show LLM top-3 nearest categories; weekly consolidation pass merges dupes |
| **Category explosion** (500 micro-cats) | Hard cap + forced deepening; auto-merge cats < 3 facts |
| **Non-determinism** (same fact → different cat on retry) | Temperature 0.1 for categorizer; embedding similarity gates LLM call |
| **Retrieval silence** (agent doesn't know memory has X) | L2-index always in prompt listing all categories; meta-ask hook when confidence low |
| **Summary drift** (closet diverges from drawer) | Closets always link to drawer source; L4 is ground truth |
| **Cost per turn** (LLM calls add up) | Batch extraction every 15 msgs, not per-msg; categorizer = small local model |
| **Stale L1** (critical facts drift from reality) | Nightly refresh pass; access_count weighting |
| **Schema rot** (new kind of fact doesn't fit) | Uniform node type + `kind` tag; no schema change needed |
| **Contradiction pile-up** | Temporal supersession closes old rows; queries filter `valid_to IS NULL` |

---

## 9. Staged Roadmap

### Stage 0 — Graph substrate (ship-first slice, ~1 week)

1. SQLite `nodes` + `edges` tables
2. `core/memory/store.py` wrapper
3. `memory_save` + `memory_recall` neuros (keyword search only, no vectors)
4. L0 + L1 flat files, injected into `context.py`
5. Seed with 6 initial categories (halls)

**Criterion to advance:** 200+ facts saved, retrieval works for "what did I say about X" queries.

### Stage 1 — LLM-maintained taxonomy (~1 week)

6. `memory_extract` neuro wired into turn end-of-batch
7. `memory_categorize` neuro with top-3 nearest gating
8. Vector index on nodes (sqlite-vss)
9. L2 taxonomy always-in-prompt

**Criterion:** 1000+ facts, taxonomy stays sane w/o manual curation.

### Stage 2 — Consolidation & temporal rigor (~3 days)

10. `memory_consolidate` weekly cron
11. `memory_supersede` on contradictions
12. `memory_l1_refresh` nightly cron
13. AAAK compression for L1

**Criterion:** categories stable over time, contradictions handled cleanly.

### Stage 3 — PPR retrieval & hybrid walk (~1 week)

14. NetworkX graph rebuilt from SQLite
15. PPR walk with recency × confidence weights
16. Hybrid retrieval in `context.py`
17. L4 drawer fallback

**Criterion:** multi-hop queries work ("what connects X and Y?").

### Stage 4 — Optional HDC augmentation (~1 week, only if needed)

18. Per-node HDC signature (bundled role-filler)
19. Structural similarity retrieval for "situations like this one"
20. Complements vector, doesn't replace

**Criterion:** structural queries feel qualitatively better than stage 3.

### Stage 5+ — Deferred (may never happen)

- KG embeddings (TransE/ComplEx) — needs 10k+ triples
- GNN learned retrieval — needs feedback labels
- Hypergraph edges beyond n=2 — add when binary feels forced

---

## 10. What to Borrow from MemPalace

Direct inspiration, adapt to our substrate:

| MemPalace thing | Do we copy? | Notes |
|---|---|---|
| 4-layer L0–L3 structure | **yes** | Extended to L4 for drawers |
| ~170 token always-loaded budget | **yes** | Extended to ~370 with L2 index |
| AAAK compression format | **yes** | Port their prompt |
| SQLite temporal KG schema | **inspiration** | We generalize to uniform node/edge |
| Hardcoded wings/rooms/halls | **no** | Replace with LLM-maintained categories |
| Stop-hook every 15 msgs | **yes** | Match cadence |
| PreCompact hook | **yes** | Fire extraction before context compression |
| ChromaDB for vectors | **optional** | sqlite-vss is lighter-weight |
| MCP server + 19 tools | **partial** | Expose via neuros instead; MCP later |
| Method-of-loci spatial metaphor | **soft** | Use as UX framing; underlying graph is flat |

---

## 11. Future: Hypergraph Evolution

The schema above already supports hyperedges (n-ary). We don't *use* them in stages 0–3 — all edges are binary. But when the following pains appear, we switch on hyperedges:

- Binary decomposition feels lossy ("meeting" fact needs 6 binary edges to represent one event)
- Cross-cutting queries get expensive ("find all nodes linked to both X and Y in Z context")
- Role-typed relations emerge (same edge type used with different role semantics)

At that point: no migration needed — just start writing `edges.nodes` with length > 2 and `edges.roles` with multiple role labels. Retrieval code generalizes naturally.

### Hypergraph as tensor (conceptual)

All `(node_i, edge_type_k, node_j, time_t)` occurrences form a sparse 4-way tensor. Embeddings + retrieval *are* low-rank approximations of this tensor. We don't materialize it — but this view is why the graph substrate can evolve to learned retrieval (GNN, HDC, KGE) without schema rewrites.

---

## 12. Relationship to Existing Docs

- Complements `docs/neuro-arch` brainstorming (commit `68edbc3d`) — memory nodes share fractal-uniform principle with neuros
- Future unification: memory nodes and neuros on same graph (neuro invocation = observation edge). Not in v1.
- Does **not** replace existing `core/conversation.py` — it wraps drawers around existing JSON storage, zero migration.

---

## 13. Open Questions

1. Where do episodic observations from `EnvironmentState` fit? (Likely: persist each observation as a fact node on task completion.)
2. Should L1 AAAK be per-project or global? (Lean: global first, per-project as categories grow.)
3. How do we handle ambiguous entity resolution ("Kai" the person vs "kai" the tool)? (Probably: embedding-based entity linking during categorization.)
4. Cron vs on-access trigger for consolidation? (Lean: both — cron nightly, on-access when category > N facts.)
5. Should manifest node (L2-index) list all categories or top-k by access? (Lean: top-k, regenerated nightly.)

---

## 14. TL;DR

- **5 layers** (L0 identity, L1 critical, L2 taxonomy, L3 facts, L4 drawers) — bounded token budget, cheap common case.
- **Graph substrate** (uniform nodes, N-ary typed edges, temporal validity) — future-proof for hypergraph.
- **LLM librarian** (local Gemma4) maintains taxonomy — no hardcoded wings/rooms.
- **Everything is a neuro** — memory capabilities are plugins, not core code.
- **Borrow** MemPalace's structure, AAAK, hook cadence. **Replace** their fixed schema with emergent taxonomy.
- **Start small** (stage 0: graph + keyword + flat L0/L1 files). **Layer on** LLM taxonomy, PPR, HDC only as pain appears.
- **Single-user scoped** — skip multi-tenant complexity but plan for long horizon + many projects + cross-cutting queries.
