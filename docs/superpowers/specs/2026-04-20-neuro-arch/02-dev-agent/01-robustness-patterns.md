# 02-dev-agent · 01 · Robustness patterns

**Status**: drafted.

---

## 1 · Scope

Concrete patterns the dev agent applies to every write. Target: AI-driven self-modification reliable enough that the user rarely needs to intervene.

## 2 · The dev-write pipeline

Every dev-agent mutation flows through these stages. Failure at any stage kicks back to the dev neuro with a structured error; success advances.

```
LLM output
   │
   ▼
(1) parse + schema validate
   │
   ▼
(2) syntax gate (ast.parse on code.py)
   │
   ▼
(3) atomic write (tempfile + rename)
   │
   ▼
(4) dry-run import (synthetic module, throwaway namespace)
   │
   ▼
(5) contract check (has run / subclass, main class resolvable)
   │
   ▼
(6) snapshot previous version
   │
   ▼
(7) move into place → factory hot-reload picks it up
   │
   ▼
(8) emit dev.event
```

If stage 7 succeeds but the factory hot-reload fails (e.g., a dependency in `uses` doesn't resolve), the pipeline triggers rollback (§6).

## 3 · Schema validation (stage 1)

- `conf.json` validates against a JSON Schema (checked in at `core/schemas/neuro_conf.schema.json`).
- Required fields: `name`, `description`, `inputs`, `outputs`.
- Optional with defaults: `scope`, `kind`, `uses`, `category`, `icon`, `color`, `summary_md`.
- Port entries validate against a nested schema (see `01-core/06-typed-io-and-ide-seams.md`).
- A schema fail returns `{error_type: "schema", field, expected, got, suggestion}`.

Parsing LLM output tolerates: markdown fences, leading prose, trailing prose. Same `_extract_json` helper used by `BaseBrain` (see `core/base_brain.py:58`) applies.

## 4 · Retry with repair

On any validation fail (schema, syntax, contract), the dev pipeline asks the same LLM to fix with the error attached:

```
System: You wrote this conf.json:
<original>

It failed validation:
<error as JSON>

Rewrite it to pass validation. Preserve intent. Respond with only the fixed JSON.
```

Bounded: **≤3 repair attempts per write**. After that, the dev neuro surfaces the error to the user with the last attempt + the sequence of errors.

## 5 · Atomic write (stage 3)

- Write to `neuros/<name>/.code.py.tmp` (hidden temp file in same dir for atomic rename).
- `fsync` the tempfile.
- Syntax-gate (stage 2) *on the temp file* before move.
- `os.rename(tmp, target)` — atomic on POSIX.

Effect: a crash or kill between `write` and `rename` leaves the old `code.py` intact. The factory's `_watch()` never sees a half-written file.

## 6 · Snapshot + rollback

Before the final `rename`, copy the current version into a snapshot dir:

```
.neuros_history/
  <neuro_name>/
    2026-04-20T15-33-09Z/
      conf.json
      code.py
      prompt.txt
      dev_event.json        # event that caused this snapshot
```

- Retention: **last 10 snapshots per neuro**. Older ones pruned automatically.
- Also pruned: snapshots older than 30 days, regardless of count.
- Snapshot location is `.gitignore`'d by default (operators can opt in to track via `.gitattributes`).

Rollback operation:
- Trigger: factory reload fails after a write, or user invokes `dev_reset <name>`.
- Action: `mv neuros/<name>/* <back to latest snapshot>`.
- Emits `dev.event {"type": "rollback", ...}`.

## 7 · Structured error envelope

All failures surface as:

```json
{
  "error_type": "schema" | "syntax" | "import" | "contract" | "reload" | "dep_missing" | "protected",
  "file":       "neuros/foo/code.py",
  "line":       17,
  "col":        5,
  "message":    "unexpected EOF while parsing",
  "expected":   "async def run(state, **kw)",
  "got":        "def run(state):",
  "suggestion": "Change the function to an async def and accept **kwargs."
}
```

This envelope is what the dev neuro returns in its `{error: ...}` output. The next LLM turn (retry with repair) reads it and fixes.

## 8 · `dev.event` stream

Every non-trivial dev action publishes a `dev.event` through `state["__pub"]`:

```json
{
  "type":   "create" | "edit" | "patch" | "reload" | "rollback" | "error",
  "neuro":  "research_flow",
  "author": "dev_new" | "dev_edit" | "dev_patch" | ...,
  "ts":     "2026-04-20T15:33:09Z",
  "diff":   "...",            // for edit/patch
  "error":  { ... },           // for error
  "snapshot_path": ".neuros_history/research_flow/2026-04-20T15-33-09Z/"
}
```

- IDE renders this as a changelog panel.
- Also appended to `agent_memory.db` via the memory API (`scope: agent, key: dev.event.<ts>`), so the dev agent can reflect on prior actions.

## 9 · Validation is fast-path

The whole pipeline must complete in ~200ms for a typical small neuro (≤100 LOC). Measured budgets:

| stage                | target (ms) |
|----------------------|-------------|
| schema validate      | < 20        |
| syntax gate          | < 30        |
| atomic write + fsync | < 40        |
| dry-run import       | < 50        |
| contract check       | < 10        |
| snapshot             | < 30        |
| rename + reload      | < 20        |

Over budget → warn but don't fail. Over 2× budget → emit `dev.event {"type":"slow_write",...}` for investigation.

## 10 · Error cases handled explicitly

| case                                     | behavior                                                           |
|------------------------------------------|--------------------------------------------------------------------|
| LLM returned markdown-fenced JSON        | `_extract_json` strips fences, continues.                          |
| `conf.json` missing `inputs`             | schema fail → retry with repair.                                   |
| `code.py` has `SyntaxError`              | syntax gate fails → error envelope, retry with repair.             |
| Module imports fail at load              | dry-run catches → error envelope, retry with repair.               |
| Class neuro: no `BaseNeuro` subclass     | contract fail → error envelope.                                    |
| Class neuro: multiple candidate classes  | contract fail, ask LLM to mark main with `__main_neuro__`.          |
| `uses` references nonexistent neuro      | contract fail, list missing dep, suggest alternatives.              |
| Hot-reload fires while write in progress | factory uses `_reload_lock`; write completes, reload runs once.     |
| Snapshot dir full / disk error           | log + skip snapshot, **allow write anyway** (log loud warning).     |
| Concurrent writes to same neuro          | `write_lock_per_neuro`; second writer waits; no interleaving.       |

## 11 · Decisions locked

1. **Eight-stage pipeline** (§2) runs for every dev-agent mutation.
2. **Schema at `core/schemas/neuro_conf.schema.json`** — single source of truth.
3. **Retry-with-repair ≤3 attempts** — deterministic ceiling.
4. **Atomic write via tempfile + rename** — POSIX atomicity guarantee.
5. **`.neuros_history/` snapshots** — last 10 per neuro, 30-day floor, gitignored by default.
6. **Structured error envelope** — same shape everywhere, consumable by both LLM and humans.
7. **`dev.event` stream** — IDE changelog, memory-backed log.
8. **200ms budget** for a typical small-neuro write — warn above, alert above 2×.
9. **Per-neuro write lock** prevents concurrent mutation.

## 12 · Deferred

- Behavior tests (run the new neuro in a sandbox with synthetic input) — covered lightly in `02-self-mod-safety.md`, not v1.
- Static analysis (type checks, forbidden-import scans) beyond syntax.
- Dev-agent A/B testing (two candidate implementations, pick the passing one).
- Git-integrated history (commit every successful dev write). Possible but adds friction to hot iteration; revisit.
- Multi-file neuros (`code/` dir) — scoped out in `01-core/`; pipeline will extend naturally when added.
