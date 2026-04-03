# Neurocomputer

**An AI agent framework with modular "neuros" (hot-swappable skills) orchestrated by LLM planners.**

## Architecture

```
User Message → Smart Router (intent) → Planner (DAG) → Executor (runs neuros) → Reply
```

## Agents

| Agent | Purpose |
|-------|---------|
| **Neuro** | General-purpose task execution |
| **Upwork** | Job capture, analysis, and proposal generation |
| **OpenClaw** | Browser automation delegation |
| **Windsurf** | IDE-integrated coding workflows |

## Neuros (50+ hot-swappable skills)

Organized under `neuros/` as self-contained folders with `conf.json` + `code.py`.

### Task Execution
- `planner` - Converts user goals into DAG execution plans
- `smart_router` - Routes to neuro or direct reply
- `executor` - Runs the DAG of neuros

### Code Development
- `code_planner`, `code_project_manager`, `code_file_read`, `code_file_write`, `code_file_diff`, `code_file_list`, `code_scan`
- `dev_planner`, `dev_new`, `dev_edit`, `dev_save`, `dev_diff`, `dev_patch`, `dev_show`, `dev_reset`

### Upwork Workflow
- `upwork_list`, `upwork_analyze`, `upwork_finalize`, `upwork_proposal`, `upwork_save_frame`

### Desktop & System
- `screen_lock_ubuntu`, `unlock_pc`, `screenshot_shortcut`, `open_file_explorer`, `move_mouse_to_center`, `move_mouse_top_right`
- `desktop_stream`, `mouse_controller`, `voice_manager`

### Integrations
- `openclaw_delegate` - Delegates to OpenClaw browser agent
- `windsurf_controller` - Bridges to Windsurf IDE via Playwright

## Profiles

| Profile | Planner | Replier |
|---------|---------|---------|
| `general` | planner | reply |
| `code_dev` | code_planner | code_reply |
| `neuro_dev` | dev_planner | dev_reply |

Switch via `/profile <name>` or `/dev on|off`.

## Server Endpoints

- `POST /chat` - Send message to agent
- `POST /chat/token` - Get LiveKit token for chat
- `GET /agents` - List running agents
- `POST /agents/{type}` - Create/switch to agent type
- `POST /upwork/capture` - Capture job frame
- `POST /upwork/finalize/{slug}` - Process captured job
- `GET /upwork/jobs` - List saved jobs
- `POST /tts` - Text-to-speech

## Quick Start

```bash
pip install -r requirements.txt
python server.py
```

Requires: `OPENAI_API_KEY` in `.env`

## Neuro Structure

```
neuros/<name>/
  conf.json   # manifest (name, description, inputs, outputs)
  code.py     # async run() function
```

Neuros hot-reload on file change—no restarts needed.
