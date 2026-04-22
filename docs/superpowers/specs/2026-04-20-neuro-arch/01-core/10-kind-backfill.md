# 01-core · 10 · Kind backfill — assigning kinds to every existing neuro

**Status**: design. Backfill is a **pure metadata addition** — each existing neuro gets a `kind` field in its `conf.json`. No `code.py` changes, no behavior changes. Ship in one commit per group.

---

## 1 · Principles

1. **Non-breaking**: adding a `kind` to conf.json has no runtime effect today. The factory reads `kind` for `describe()` and `kind: prompt.*` / `kind: skill.flow.*` synthesis — unrelated to regular neuros.
2. **Conservative**: when in doubt, use `skill.leaf`. Promoting later is cheap.
3. **Use canonical dotted form**: prefer `skill.leaf` over legacy aliases.
4. **Don't re-classify behavior**: if a neuro today delegates to an external agent, it stays `skill.leaf` (delegate wrapper), not `agent`.
5. **Backfill matches `09-kind-formats.md` contracts**: if today's neuro's I/O doesn't match the new kind contract, keep it `skill.leaf` and flag for a contract-conforming refactor as separate work.

---

## 2 · The full backfill table

Legend: **kind** = what to put in conf.json. **notes** = any concerns / follow-ups.

### 2.1 · `code.*` — code workflow (10 neuros)

| current name               | new kind              | conf shape changes                                   | notes                              |
|----------------------------|-----------------------|------------------------------------------------------|------------------------------------|
| `code_file_read`           | `code.read`           | add `category: code.file_ops`, typed ports           | matches contract                    |
| `code_file_write`          | `code.write`          | add `category`, typed ports                          | matches contract                    |
| `code_file_diff`           | `code.diff`           | add category                                         | matches contract                    |
| `code_file_list`           | `code.scan`           | `"scan_mode": "list"` flag in conf                   | subtype of scan                    |
| `code_scan`                | `code.scan`           | add category                                         | matches                            |
| `code_reader_with_context` | `code.read`           | add `"enriched": true` flag in conf                  | returns more than base contract; flag + keep |
| `code_planner`             | `code.plan`           | add category                                         | matches contract                    |
| `code_project_manager`     | `skill.leaf`          | add `category: code.project`                         | session-level ops, not atomic code |
| `write_file`               | `code.write`          | add category                                         | generalized alias; keep both names |
| `delete_file`              | `code.write`          | add `"mode": "delete"` flag                          | or later split into `code.delete`  |

### 2.2 · `dev.*` / `skill.leaf` — dev agent internals (11 neuros)

Kept as `skill.leaf` for now; a future `dev.*` namespace may formalize.

| current name     | new kind     | notes                                         |
|------------------|--------------|-----------------------------------------------|
| `dev_new`        | `skill.leaf` | creates a neuro folder; dev-agent track     |
| `dev_edit`       | `skill.leaf` | edits an existing neuro; dev-agent track    |
| `dev_save`       | `skill.leaf` |                                               |
| `dev_reset`      | `skill.leaf` |                                               |
| `dev_show`       | `skill.leaf` |                                               |
| `dev_reply`      | `skill.leaf` | reply variant for dev mode                    |
| `dev_diff`       | `code.diff`  | diffs source files; overlaps `code.*`         |
| `dev_patch`      | `code.patch` | applies diff to a file; overlaps `code.*`     |
| `dev_codegen`    | `skill.leaf` | generates code blocks                         |
| `dev_planner`    | `code.plan`  | plans dev work; overlaps `code.*`             |
| `neuro_crafter`  | `skill.leaf` | composes full neuros from spec                |

### 2.3 · `upwork_*` — pipeline neuros (6)

All stay `skill.leaf`. Could be packaged as a `library` in v2.

| current name            | new kind     |
|-------------------------|--------------|
| `upwork_analyze`        | `skill.leaf` |
| `upwork_finalize`       | `skill.leaf` |
| `upwork_list`           | `skill.leaf` |
| `upwork_proposal`       | `skill.leaf` |
| `upwork_save_frame`     | `skill.leaf` |
| `linkedin_post_creator` | `skill.leaf` |

### 2.4 · System / hardware control (8)

| current name            | new kind     | notes                                |
|-------------------------|--------------|--------------------------------------|
| `screen_lock_ubuntu`    | `skill.leaf` | category: `system.control`           |
| `unlock_pc`             | `skill.leaf` |                                      |
| `screenshot_shortcut`   | `skill.leaf` | category: `system.screenshot`        |
| `screenshot_windows`    | `skill.leaf` |                                      |
| `open_file_explorer`    | `skill.leaf` | category: `system.filesystem`        |
| `move_mouse_to_center`  | `skill.leaf` | category: `system.mouse`             |
| `move_mouse_top_right`  | `skill.leaf` |                                      |
| `install_python_library`| `skill.leaf` | category: `system.package`           |

### 2.5 · Utility (6)

| current name         | new kind     | notes                              |
|----------------------|--------------|------------------------------------|
| `echo`               | `skill.leaf` | canonical leaf example             |
| `wait`               | `skill.leaf` |                                    |
| `play_text_audio`    | `skill.leaf` | category: `media.audio`            |
| `video_generator`    | `skill.leaf` | category: `media.video`            |
| `prime_checker`      | `skill.leaf` | trivial example                    |
| `run_command`        | `skill.leaf` | category: `system.shell`           |

### 2.6 · Orchestration (reply / router / planner) (7)

| current name        | new kind     | notes                                                |
|---------------------|--------------|------------------------------------------------------|
| `planner`           | `skill.leaf` | produces DAGs; contract doesn't match `code.plan`    |
| `smart_router`      | `skill.leaf` | routes reply vs skill; doesn't match standard kinds  |
| `intent_classifier` | `skill.leaf` | legacy; may be deprecated                            |
| `reply`             | `skill.leaf` | conversational replier                               |
| `code_reply`        | `skill.leaf` | code-mode replier                                    |
| `result_to_reply`   | `skill.leaf` | post-processes neuro outputs                         |
| `reflector`         | `skill.leaf` | self-reflection; could become `skill.flow.react` later |

### 2.7 · Delegates (3)

| current name          | new kind     | notes                                                  |
|-----------------------|--------------|--------------------------------------------------------|
| `openclaw_delegate`   | `skill.leaf` | wraps external Claude Code agent; not a native agent   |
| `opencode_delegate`   | `skill.leaf` | wraps external OpenCode; not a native agent           |
| `load_skill`          | `skill.leaf` | dynamic loader                                         |

### 2.8 · Discovery (2)

| current name   | new kind     |
|----------------|--------------|
| `neuro_list`   | `skill.leaf` |
| `neuro_crafter`| `skill.leaf` |

### 2.9 · Memory (1, new)

| current name | new kind        | notes                                     |
|--------------|-----------------|-------------------------------------------|
| `memory`     | `memory.store`  | represents the whole API (read/write/...)|

Later split (see `09-kind-formats.md §5.5`) into:
- `memory.store.sqlite` — backend wrapper (same code as today)
- `memory.recall.keyword` — today's `search` op
- `memory.layer.identity` — future, for L0

### 2.10 · Dead / skipped (1)

| current name | action                     |
|--------------|----------------------------|
| `my_skill` (name=my_neuro) | delete folder — empty code.py, already skipped by factory with WARN |

---

## 3 · Summary

- **~60 neuros total**
- **~10** → `code.*`
- **~1** → `memory.store`
- **~45** → `skill.leaf`
- **~4** → `code.*` overlap from dev_* (code.diff, code.patch, code.plan, dev_planner)
- **0** → `prompt.*`, `context.*`, `model.*`, `instruction.*`, `agent` *currently* (those await implementation in future phases)
- **1** → delete

---

## 4 · Implementation — one commit per group

Groups are independent; land in any order. Each touches only `conf.json` files, no code.

### Commit A: `code.*` backfill (9 files)
Adds `"kind": "code.*"` + `"category": "code.file_ops"` etc. to:
`code_file_read`, `code_file_write`, `code_file_diff`, `code_file_list`, `code_scan`, `code_reader_with_context`, `code_planner`, `write_file`, `delete_file`.

### Commit B: `code.*` overlap in dev_*
`dev_diff`, `dev_patch`, `dev_planner` get `kind: code.*` values.

### Commit C: skill.leaf categorization (remaining)
All others get `"kind": "skill.leaf"` + appropriate `"category"` for IDE tree. Cosmetic.

### Commit D: memory.store for the `memory` neuro
One-liner change.

### Commit E: delete dead `my_skill`
Purge empty-code.py neuro.

---

## 5 · Verification

After each commit:

- `pytest tests/core/` — should still pass (no runtime-touching changes).
- `python3 -c "from core.neuro_factory import NeuroFactory; f=NeuroFactory(); print(len(f.reg))"` — count unchanged (except commit E which drops 1).
- `factory.describe()` — each described neuro now has a populated `kind` and `kind_namespace` field.
- `factory.describe(cid)` with a profile → grouping by kind reveals intended shape.

---

## 6 · Why backfill is worth it

Before backfill:
- IDE can't group. 60 neuros in a flat list. Non-devs lost.
- Planner can't hint. "pick a code operation" → has to scan all 60.
- The `kind` feature we shipped in `08-kinds-taxonomy.md` isn't being used.

After backfill:
- IDE groups by `kind_namespace` → clean library sidebar (code, skill, memory, …).
- Planner receives `catalogue(cid, kind_prefix="code.")` → narrow choice set.
- Formal contracts from `09-kind-formats.md` have concrete inhabitants.
- Every subsequent refactor (`code.plan` unification, `code.patch` standardization) has a clear target.

---

## 7 · Open questions

- Should `dev_patch` be **both** `code.patch` AND carry a dev-scope marker (e.g. `"subdomain": "dev"`)? ✅ add `subdomain` field to distinguish dev-agent-only ops from user-code ops.
- `intent_classifier` likely deprecated by `smart_router`. Mark as `"deprecated": true` in conf during backfill.
- `neuro_crafter` — is that actually `kind: skill.leaf` or is it a distinct kind (`meta.author`)? TBD. Leave `skill.leaf` for now.
- `code_reply` — should it be `prompt.composer` (generates reply) instead of `skill.leaf`? It *does* use LLM + prompt. Probably stays `skill.leaf` because it does more than compose prompt.

---

## 8 · Deferred

- **`dev.*` namespace**: when dev-agent hardening track (02-dev-agent/) ships, it may earn its own kind namespace. Backfill again then.
- **`prompt.*` / `context.*` / `model.*` backfill**: only happens after those kinds are *implemented as neurons* (phases 3–5 from `09-kind-formats.md §16`). Today they don't exist as neurons; backfill is vacuous.
- **`agent` kind**: waits for Brain refactor into an agent-neuro (phase 7).
