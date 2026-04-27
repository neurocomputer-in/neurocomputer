# S2 — Main Agency / Main Project / Main Agent (Defaults Contract)

**Master plan:** [`2026-04-28-MASTER-neurolang-integration-plan.md`](./2026-04-28-MASTER-neurolang-integration-plan.md)
**Status:** DRAFT
**Depends on:** none (foundational)
**Blocks:** S1, S6
**ETA:** 30 minutes

---

## Goal

Make the concepts of "the default agency", "the default project", and "the default agent" first-class and explicit, so every downstream feature (NeuroLang profile, schedules, multi-agent talk, IDE) can name them without ambiguity. Today the system has implicit defaults (the `default` agency in `AGENCY_CONFIGS`, the `neuro` agent); we're not creating new agencies — we're naming the fall-through contract so the rest of the codebase can rely on it.

---

## Background — what exists today

`neurocomputer/core/agency_configs.py`:

```python
AGENCY_CONFIGS = {
    "default": AgencyConfig(name="Neuro HQ", agents=["neuro", "opencode"], default_agent="neuro", ...),
    "upwork":  AgencyConfig(...),
    "webclaw": AgencyConfig(...),
}
```

`neurocomputer/core/agent_configs.py`:

```python
AGENT_CONFIGS = {
    "neuro":    AgentConfig(name="Neuro", profile="general", ...),
    "upwork":   AgentConfig(...),
    "openclaw": AgentConfig(...),
    "opencode": AgentConfig(...),
}
```

The `default` agency and `neuro` agent are de-facto "Main" but the constants are not exposed. There is no "Project" concept yet — the closest thing is the `cid` (conversation id) used by `Brain.handle()`. We will add a thin `Project` concept here so the term has a definition.

---

## What "Main" means (the contract)

Three named singletons used as fall-throughs:

| Symbol | What it is | Default value |
|---|---|---|
| `MAIN_AGENCY_ID` | The agency used when none specified | `"default"` |
| `MAIN_AGENT_ID` | The agent used when none specified | `"neuro"` |
| `MAIN_PROJECT_ID` | The project used when none specified | `"default"` |

Plus a tiny `Project` dataclass so the concept is real:

```python
@dataclass
class ProjectConfig:
    name: str
    description: str = ""
    color: str = "#6366F1"
    emoji: str = "📁"
    agency_id: str = "default"      # which agency owns it
    default_agent: str = "neuro"
    profile: str = "general"        # which profile is active in this project
    blackboard_path: str = "default" # subpath under shared blackboard

PROJECT_CONFIGS: Dict[str, ProjectConfig] = {
    "default": ProjectConfig(name="Main", agency_id="default", default_agent="neuro", profile="general"),
}
```

Projects sit *between* agency and conversation: an agency hosts multiple projects, a project hosts multiple conversations, a conversation runs on the project's agent.

---

## Files to add / edit

### New

- `neurocomputer/core/project.py` — `Project` class + `ProjectConfig` dataclass.
- `neurocomputer/core/project_configs.py` — `PROJECT_CONFIGS` dict (one entry, `"default"`).
- `neurocomputer/core/defaults.py` — exports `MAIN_AGENCY_ID`, `MAIN_AGENT_ID`, `MAIN_PROJECT_ID` constants.

### Edit

- `neurocomputer/core/agency.py` — add `default_project: str = "default"` to `AgencyConfig`.
- `neurocomputer/core/agency_configs.py` — set `default_project="default"` on the `default` agency.
- `neurocomputer/core/agent_manager.py` — when looking up an agent without an `agent_id`, fall back to `MAIN_AGENT_ID`. (Audit: any place that does `agent_id or "neuro"` is replaced with `agent_id or MAIN_AGENT_ID`.)

---

## Implementation Checklist

- [ ] **2.1** Create `core/defaults.py` with three constants.
- [ ] **2.2** Create `core/project.py` with `ProjectConfig` dataclass + `Project` class (mirror `agency.py` shape).
- [ ] **2.3** Create `core/project_configs.py` with `PROJECT_CONFIGS = {"default": ProjectConfig(name="Main", ...)}`.
- [ ] **2.4** Add `default_project: str = "default"` field to `AgencyConfig` in `core/agency.py`.
- [ ] **2.5** Set `default_project="default"` on the `default` entry in `core/agency_configs.py`.
- [ ] **2.6** Grep for hardcoded `"neuro"` as an agent fall-through and replace with `from core.defaults import MAIN_AGENT_ID`. Common sites: `agent_manager.py`, `chat_handler.py`, `server.py`. Don't change places where `"neuro"` is the literal name (display strings).
- [ ] **2.7** Add a one-page section to `core/README.md` (create if missing) documenting the contract and the four-tier hierarchy: **Agency → Project → Agent → Neuro**.
- [ ] **2.8** Smoke test: `python -c "from core.defaults import MAIN_AGENCY_ID, MAIN_AGENT_ID, MAIN_PROJECT_ID; print(MAIN_AGENCY_ID, MAIN_AGENT_ID, MAIN_PROJECT_ID)"` prints `default neuro default`.
- [ ] **2.9** Mark this spec `Status: SHIPPED` and add a one-line entry to `STATUS.md`.

---

## Acceptance criteria

1. **`from core.defaults import MAIN_AGENCY_ID, MAIN_AGENT_ID, MAIN_PROJECT_ID`** works from anywhere.
2. **The `default` agency has `default_project="default"`** in its config.
3. **`PROJECT_CONFIGS["default"]`** is a `ProjectConfig` with `name="Main"`.
4. **No regressions** — `pytest` (existing tests) still passes.
5. **Doc update** — `core/README.md` has a paragraph explaining the **Agency → Project → Agent → Neuro** hierarchy.

---

## Out of scope

- Multi-project UI (project picker in IDE) — defer.
- Per-project memory namespacing — defer (use blackboard subpaths later).
- Migration of existing conversations to projects — defer; conversations without a `project_id` default to `MAIN_PROJECT_ID` at read time.
- Permissions / per-project ACL — defer.

---

## Open questions

- *(none — defaults are deliberate and small)*

---

## Notes for the executing agent

- This spec is a renaming + tiny additive change. **Do not** restructure `Agency` / `Agent` classes.
- If you find more than ~10 call sites that need editing in step 2.6, **stop and add a feature flag** (`USE_DEFAULTS_CONSTANTS = True`) instead of doing a big-bang replace. Better to ship a small win.
- Keep the `Project` class minimal in this round — just enough to satisfy `PROJECT_CONFIGS["default"]` lookups.
