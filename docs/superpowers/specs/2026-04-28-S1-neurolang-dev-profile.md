# S1 — NeuroLang Dev Profile + `nl_*` Neuros

**Master plan:** [`2026-04-28-MASTER-neurolang-integration-plan.md`](./2026-04-28-MASTER-neurolang-integration-plan.md)
**Status:** DRAFT
**Depends on:** S2 (defaults)
**Blocks:** S4 (IDE mode)
**ETA:** 60–90 minutes

---

## Goal

Add a **`neurolang_dev` profile** that lets the user say (in voice or text) "compile a flow that fetches arxiv papers and emails me a summary" and have the system:

1. Plan it using the **NeuroLang** library's `propose_plan(...)` (catalog-aware, sees stdlib).
2. Compile it via `compile_source(...)` to real Python source.
3. Save the source as a runnable `.py` file under `~/.neurolang/neuros/` (so the NeuroLang discovery layer auto-loads it).
4. Surface the new flow as a node in the existing 3D IDE.
5. Reply with a NL summary via `decompile_summary(...)`.

The agentic loop is unchanged (`smart_router → planner → reply`) — only the **planner**, **replier**, and the active **neuro set** swap out per profile. This proves the user's "same agentic code, different context/instructions per profile" principle.

---

## Background — what NeuroLang gives us

The NeuroLang library at `/home/ubuntu/neurolang/` ships:

- `compile_source(prompt: str, *, model: str = None, registry=None) -> str` — NL → Python source string.
- `decompile_summary(source: str, *, model: str = None) -> str` — Python → NL summary.
- `propose_plan(prompt: str, *, model: str = None, registry=None) -> ProposedPlan` — single-call planner, returns `intents`, `neuros`, `missing`, `rationale`, `cost_estimate`.
- `discover_neuros(extra_paths: list[str] | None = None)` — eager FS scan, loads `~/.neurolang/neuros/` + project-marker-detected `<project>/neuros/`.
- 17 stdlib neuros: `web.{search, scrape}`, `reason.{summarize, classify, brainstorm, deep_research}`, `memory.{store, recall}`, `voice.{transcribe, synthesize}`, `email.{send, read, search, mark}`, plus the `agent.delegate` factory.

Install in neurocomputer's env: `pip install -e /home/ubuntu/neurolang` (one-time).

---

## What changes in neurocomputer

### Profile

`neurocomputer/profiles/neurolang_dev.json`:

```json
{
  "planner":  "nl_planner",
  "replier":  "nl_reply",
  "neuros": ["nl_*", "neuro_list", "load_neuro"]
}
```

### Eight new neuros under `neurocomputer/neuros/`

Each is a directory with `conf.json`, `code.py`, optional `prompt.txt`. All are **thin wrappers** around the NeuroLang library — they exist to give the existing executor a familiar shape.

| Neuro | Purpose | Inputs | Outputs |
|---|---|---|---|
| `nl_planner` | Planning step. Reads user message, calls `propose_plan(prompt)`, returns a DAG with at most three nodes: `nl_propose` → `nl_compile` → `nl_save` | `message: str` | `dag: dict` |
| `nl_reply` | Replier. Calls `decompile_summary(source)` on the saved file or returns the planner's rationale if no save happened | `source: str | None`, `rationale: str` | `text: str` |
| `nl_propose` | Wraps `propose_plan(...)`. Returns the `ProposedPlan` as a dict | `prompt: str` | `proposed: dict` (intents, neuros, missing, rationale, cost) |
| `nl_compile` | Wraps `compile_source(...)`. Returns Python source | `prompt: str` | `source: str` |
| `nl_summary` | Wraps `decompile_summary(...)` | `source: str` | `summary: str` |
| `nl_save` | Writes source to `~/.neurolang/neuros/<slug>.py` (slug derived from prompt or explicit `name`) | `source: str`, `name: str | None` | `path: str` |
| `nl_run` | Imports the saved file, calls its `flow.run(input)` | `path: str`, `input: any` | `result: any` |
| `schedule_run` (optional this round; covered fully in S5) | Schedules an `nl_run` for periodic execution | `path: str`, `every: str (cron or interval)` | `schedule_id: str` |

### Catalog visibility

Existing `neuro_list` already enumerates all neuros and powers the 3D IDE. The new `nl_*` neuros will appear automatically (no IDE changes needed for visibility — only the **highlight** in S4).

---

## Files to add / edit

### New

- `neurocomputer/profiles/neurolang_dev.json`
- `neurocomputer/neuros/nl_planner/{conf.json, code.py, prompt.txt}`
- `neurocomputer/neuros/nl_reply/{conf.json, code.py, prompt.txt}`
- `neurocomputer/neuros/nl_propose/{conf.json, code.py}`
- `neurocomputer/neuros/nl_compile/{conf.json, code.py}`
- `neurocomputer/neuros/nl_summary/{conf.json, code.py}`
- `neurocomputer/neuros/nl_save/{conf.json, code.py}`
- `neurocomputer/neuros/nl_run/{conf.json, code.py}`

### Edit

- `requirements.txt` — add `neurolang @ file:///home/ubuntu/neurolang` (or relative path; document the dev install).
- `neurocomputer/core/agent_configs.py` — add a new agent `"nl_dev"` with `profile="neurolang_dev"`, `planner_neuro="nl_planner"`, `replier_neuro="nl_reply"`. Reuses `smart_router`.
- `neurocomputer/core/agency_configs.py` — add `"nl_dev"` to the `default` agency's `agents` list. The agency stays `MAIN_AGENCY_ID="default"` (per S2); the project stays `MAIN_PROJECT_ID="default"` until per-project profile binding lands.

---

## conf.json shape (mirror existing neuros)

Every existing neuro at `neurocomputer/neuros/<name>/conf.json` follows a stable schema. Example for `nl_compile`:

```json
{
  "name": "nl_compile",
  "description": "Compile a natural-language description into a NeuroLang flow.",
  "kind": "skill",
  "kind_namespace": "nl",
  "category": "neurolang",
  "icon": "📝",
  "color": "#22d3ee",
  "scope": "process",
  "inputs":  [{"name": "prompt",  "type": "string", "description": "What the flow should do"}],
  "outputs": [{"name": "source",  "type": "string", "description": "Python source using NeuroLang primitives"}],
  "uses": [],
  "model": "default",
  "temperature": 0.0
}
```

The kind_namespace `"nl"` is new and gets a color in S4.

---

## code.py shape (one example)

`neurocomputer/neuros/nl_compile/code.py`:

```python
from typing import Any, Dict
from neurolang import compile_source

async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    prompt = kwargs.get("prompt") or state.get("__prompt") or ""
    if not prompt:
        return {"error": "nl_compile: empty prompt"}
    source = compile_source(prompt)
    return {"source": source, "prompt": prompt}
```

`nl_save/code.py`:

```python
import os, re
from pathlib import Path
from typing import Any, Dict

NL_NEURO_DIR = Path.home() / ".neurolang" / "neuros"

def _slug(s: str, fallback: str = "flow") -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_")
    return s[:60] or fallback

async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    source = kwargs.get("source") or state.get("source") or ""
    name = kwargs.get("name") or _slug(state.get("prompt", "flow"))
    NL_NEURO_DIR.mkdir(parents=True, exist_ok=True)
    path = NL_NEURO_DIR / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    return {"path": str(path), "name": name}
```

The other six neuros follow identical patterns — wrap a NeuroLang fn, return a dict.

---

## planner DAG shape

`nl_planner` outputs the DAG that the existing `core/executor.py` already understands. Minimal version:

```json
{
  "start": ["nl_propose"],
  "nodes": {
    "nl_propose": {"neuro": "nl_propose", "params": {"prompt": "var:__prompt"}, "next": ["nl_compile"]},
    "nl_compile": {"neuro": "nl_compile", "params": {"prompt": "var:__prompt"},  "next": ["nl_save"]},
    "nl_save":    {"neuro": "nl_save",    "params": {"source": "ref:nl_compile.source", "name": "var:flow_name"}, "next": []}
  }
}
```

If `propose_plan` returns `missing != []`, the planner short-circuits with a single `nl_reply` node carrying the rationale.

---

## Implementation Checklist

- [ ] **1.1** `pip install -e /home/ubuntu/neurolang` inside neurocomputer's venv. Verify: `python -c "from neurolang import compile_source; print(compile_source.__module__)"`.
- [ ] **1.2** Create `profiles/neurolang_dev.json` with planner=`nl_planner`, replier=`nl_reply`, neuros=`["nl_*", "neuro_list", "load_neuro"]`.
- [ ] **1.3** Add `nl_dev` entry to `core/agent_configs.py` (router=`smart_router`, planner=`nl_planner`, replier=`nl_reply`, profile=`neurolang_dev`).
- [ ] **1.4** Add `"nl_dev"` to the `default` agency's `agents` list in `core/agency_configs.py`.
- [ ] **1.5** Create `neuros/nl_propose/` (conf + code wrapping `propose_plan`).
- [ ] **1.6** Create `neuros/nl_compile/` (conf + code wrapping `compile_source`).
- [ ] **1.7** Create `neuros/nl_summary/` (conf + code wrapping `decompile_summary`).
- [ ] **1.8** Create `neuros/nl_save/` (conf + code writing to `~/.neurolang/neuros/<slug>.py`).
- [ ] **1.9** Create `neuros/nl_run/` (conf + code dynamically importing the saved file and calling `.run()`).
- [ ] **1.10** Create `neuros/nl_planner/` (planner that emits the DAG above; `prompt.txt` describes the planning rules).
- [ ] **1.11** Create `neuros/nl_reply/` (replier that runs `decompile_summary` on the saved source or returns the rationale).
- [ ] **1.12** Smoke test offline: `python -m core.brain` style script that handles a fake message through the `nl_dev` agent. Mock the LLM provider in NeuroLang so no network call is needed.
- [ ] **1.13** Live test via UI: switch agent to `nl_dev`, type "summarise this morning's emails", verify a `.py` lands in `~/.neurolang/neuros/` and the reply contains a one-paragraph summary of the saved source.
- [ ] **1.14** Mark spec `Status: SHIPPED` and update `STATUS.md`.

---

## Acceptance criteria

1. **Profile loads.** `agent_manager.get_agent("nl_dev")` returns an agent with `profile=="neurolang_dev"`.
2. **End-to-end loop.** Sending a message to the `nl_dev` agent produces (a) a saved `.py` under `~/.neurolang/neuros/` containing valid NeuroLang source, AND (b) a NL reply explaining what the flow does.
3. **Discovery integration.** `discover_neuros()` (called from a one-shot Python REPL) sees the saved file and loads it into `default_registry`.
4. **No regressions.** Existing agents (`neuro`, `upwork`, `openclaw`, `opencode`) still answer messages identically.
5. **Catalog endpoint** (`/api/neuros` or whatever serves `neuro_list`) lists the `nl_*` neuros under `kind_namespace="nl"`.

---

## Out of scope

- Visual highlight of `nl_*` neuros in the 3D IDE → **S4**.
- Scheduling / cron → **S5**.
- Multi-agent talk → **S6**.
- Compiling NeuroLang flows that themselves use `agent.delegate` for recursion (works automatically — the saved file is just Python; nothing special needed).
- Custom NeuroLang LLM provider configuration in the UI — for now, NeuroLang uses its own default provider (opencode-zen → openrouter → openai). Configure via env if needed.

---

## Open questions

- **Where to store the user's NeuroLang neuros — `~/.neurolang/neuros/` (per-user, persistent across projects) or `<project>/neuros/` (project-local)?** Default this round: per-user (matches NeuroLang's discovery default). If a `Project` (S2) is active, future-S2.1 can override to project-local.
- **What model does `compile_source` use by default?** Whatever NeuroLang's `DEFAULT_LLM_PROVIDER` resolves to. Document in the `nl_compile` `conf.json`'s description so the user knows.

---

## Notes for the executing agent

- The eight neuros are **mechanically similar**. Generate the first one (`nl_compile`) carefully, then copy-and-edit for the rest. Don't re-think the shape per neuro.
- The `nl_planner` is the only neuro with non-trivial logic — all others are 3–10 lines around a NeuroLang library call.
- Errors from NeuroLang (`CompileError`, `RuntimeError("EMAIL_ADDR not set")`, etc.) bubble up as dict `{"error": str(e)}`; the existing executor handles that gracefully.
- The `prompt.txt` for `nl_planner` should explicitly tell the LLM: "you are NOT writing the flow yourself — you are emitting a 3-node DAG that calls `nl_propose`, `nl_compile`, `nl_save`. The actual flow generation is done by `nl_compile` via the NeuroLang library."
