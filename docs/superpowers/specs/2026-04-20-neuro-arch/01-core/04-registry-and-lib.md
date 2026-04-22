# 01-core · 04 · Registry and library

**Status**: drafted. Awaiting user approval.

---

## 1 · One global registry

A single in-process registry holds every loaded neuro. This is today's `NeuroFactory.reg` — unchanged in role, lightly extended in shape.

```
registry: dict[str, NeuroEntry]
```

- Keys are neuro names (string, unique).
- Values wrap either a fn-neuro or a class-neuro, uniformly (see `01-primitive-class-vs-fn.md` §8).
- Population: filesystem scan (`neuros/**/conf.json`) + hot-reload watcher.
- One process = one registry. Multiple agents running in the same process share it. Filtering gives each agent its own view.

## 2 · Agent view = filtered slice

An agent never sees the whole registry. It sees a **profile** — a list of glob patterns applied against neuro names:

```json
// profiles/neuro.json
{
  "name": "neuro",
  "description": "Default conversational agent.",
  "neuros": ["reply", "planner", "smart_router", "code_*", "memory", "*flow"],
  "planner": "planner",
  "replier": "reply"
}
```

Resolution:

- `*` matches any single name segment.
- `code_*` matches `code_reply`, `code_planner`, etc.
- A name matches the profile if it matches *any* pattern (OR semantics).
- `["*"]` = all neuros visible (current `general` profile semantics).
- Empty list = no neuros visible (useful for locked-down agents).

The factory's `catalogue(cid)` and `describe(cid)` already implement this (see `core/neuro_factory.py:167`). Keep as-is; generalize naming from "pattern" to "profile".

## 3 · Agent → profile binding

Today: `Brain` maps `cid → active_profile`. In the new arch:

- An **agent** has a default profile (declared in the agent's own config).
- A **session** can override the profile mid-run (`/profile <name>`, already supported).
- Profile changes apply immediately; the factory rebuilds the visible set for the session.

No change in user-visible behavior. Cleanup: profile resolution moves out of `Brain._profile_cfg` into a small `ProfileResolver` helper so agents other than the default `neuro` can reuse it.

## 4 · Naming conventions

- `snake_case`, ASCII, no leading digit.
- Optional prefix groups for discoverability:

  | prefix     | purpose                                  |
  |------------|------------------------------------------|
  | `code_*`   | code-related dev neuros                  |
  | `dev_*`    | dev agent internals (planner, diff, etc) |
  | `upwork_*` | upwork workflow neuros                   |
  | `memory_*` | memory backends / helpers                |
  | `flow_*`   | reusable composite flows                 |

  Prefixes are convention, not enforced. Profiles use them for glob patterns.

- Reserved names (shipped built-ins): `memory`, `dag_flow`, `sequential_flow`, `parallel_flow`, `retry_flow`. User neuros must not shadow.

## 5 · Categories (IDE metadata)

For the future 3D IDE to render a sensible library tree, each neuro may declare a category:

```json
{
  "name": "summarize",
  "description": "...",
  "category": "text.nlp",
  "icon":     "sparkles",
  "color":    "#7c3aed"
}
```

- `category` is a dotted path. IDE groups the library by the first segment (top-level folder).
- Uncategorized neuros fall under `misc`.
- No runtime behavior — pure metadata. Factory reads and exposes on `describe()`.

## 6 · `describe()` output (IDE contract)

`factory.describe(cid)` returns the canonical shape the IDE consumes:

```json
[
  {
    "name": "summarize",
    "description": "...",
    "category": "text.nlp",
    "icon": "sparkles",
    "color": "#7c3aed",
    "kind":  "leaf",
    "inputs":  [{"name":"text","type":"str"}],
    "outputs": [{"name":"summary","type":"str"}],
    "uses":  [],
    "scope": "call",
    "summary_md": "Condenses text to N sentences..."
  },
  ...
]
```

- `kind`: `"leaf"` | `"flow"` (derived: `FlowNeuro` subclass → `"flow"`, else `"leaf"`).
- `summary_md`: human-readable description for the IDE's english-summary mode.
- Unknown optional fields default to `null`.

## 7 · Versioning

v1 shipping plan: **no versions**. One name → one loaded neuro.

Design seam for v2 without code change:

- `conf.json` may carry `"version": "0.3.0"` (semver). Ignored at runtime in v1; indexed in v2.
- Registry key may become `"name@version"` in v2, with `"name"` resolving to the latest.
- Migration from v1 → v2 is additive.

Don't implement v2 until at least two neuros in the same deployment need divergent versions simultaneously. Until then, git history is the version record.

## 8 · Library composition (deferred)

YAGNI for v1. When a compelling use case appears (e.g., a marketplace of plug-and-play neuro packs), add:

- A `lib/` directory mirroring `neuros/` but treated as read-only dependencies.
- A `pack.json` at the root of a lib listing exported neuros.
- Profile patterns can then reference `<pack>:<name>`.

Open this up only when it's demanded.

## 9 · Per-agency / per-agent overrides

Also YAGNI v1. The current architecture supports it via profiles — two agents can have two profiles pointing at two disjoint neuro sets. That covers 99% of override needs.

A deeper override (same name, different impl per agent) adds complexity disproportionate to the need. Defer until concrete.

## 10 · Discovery and browsing

For the IDE + CLI, the factory exposes:

- `factory.catalogue(cid)` → `list[str]` (names visible to this session)
- `factory.describe(cid)` → list of rich metadata (see §6)
- `factory.find(pattern)` → filter by glob (IDE search)
- `factory.get_meta(name)` → full conf for one neuro
- `factory.categories()` → `{"text.nlp": [...], "code.io": [...], ...}` grouped tree

All read-only. Writes (create/edit/delete neuros) go through dev-agent neuros (`dev_new`, `dev_edit`, etc), not through direct factory calls. This keeps lifecycle (syntax check, rollback, events) centralized — see `02-dev-agent/`.

## 11 · Decisions locked

1. **One global registry.** Single source of truth. Agents filter, never fork.
2. **Profile = glob pattern list**. Existing `core/neuro_factory.set_pattern` becomes the mechanism; naming upgraded from "pattern" to "profile" in public API.
3. **Agent → profile binding**: default profile in agent config; session can switch mid-run (current `/profile` behavior).
4. **Category + icon + color** in `conf.json` — optional IDE metadata, zero runtime cost.
5. **Reserved names**: `memory`, `dag_flow`, `sequential_flow`, `parallel_flow`, `retry_flow`. User neuros must not shadow.
6. **No versioning in v1**; seam reserved in `conf.json`.
7. **Library composition deferred** (no `lib/` tree yet).
8. **Per-agency overrides deferred**; use disjoint profiles instead.
9. **Factory discovery API** (`catalogue`, `describe`, `find`, `get_meta`, `categories`) is the IDE's read surface. Writes go through dev neuros.
10. **Profile resolution helper** extracted from `Brain` so any agent can reuse it.

## 12 · Deferred

- Semver-aware registry (name@version keys).
- `lib/` external packs + `pack.json`.
- Per-agency neuro overrides (same-name different-impl).
- Remote registry sync (pull neuros from a central store).
- ACLs on neuros (this agent cannot see/invoke neuro X).
