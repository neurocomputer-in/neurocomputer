# Infinity Multi-Agency Architecture

**Status**: Draft — In Progress
**Last Updated**: 2026-03-22

---

## Overview

Infinity is evolving from a single AI agent into an **AI Operating System** — a platform for running multiple specialized agencies, each staffed by purpose-built agents that coordinate through shared memory and a hyperdimensional workflow engine.

The system has four layers:

```
┌─────────────────────────────────────────┐
│           AGENCY LAYER                  │  ← Upwork Agency, CC Manager, Docs, etc.
│   (Specialized teams, own dashboards)    │
├─────────────────────────────────────────┤
│            AGENT LAYER                  │  ← Named agents, owned by agencies
│   (Composed of neuros in workflows)     │
├─────────────────────────────────────────┤
│         WORKFLOW ENGINE                 │  ← Hyperdimensional execution graphs
│   (Multi-path, conditional, parallel)    │
├─────────────────────────────────────────┤
│            NEURO LAYER                  │  ← Atomic hot-swappable skills
│   (conf.json + code.py + prompt.txt)    │
└─────────────────────────────────────────┘
         ↕ Shared via
┌─────────────────────────────────────────┐
│          BLACKBOARD                     │  ← Shared memory & data layer
│   (Folders + metadata, all agencies)     │
└─────────────────────────────────────────┘
```

---

## Layer 1: Neuro Layer (Foundation)

**What it is**: The atomic unit of capability. A neuro is a hot-swappable Python skill defined by:

```
neuros/<neuro_name>/
├── conf.json     # Name, description, inputs, outputs, model, temperature
├── code.py       # async def run(state, **kwargs) → dict
└── prompt.txt    # Optional system prompt for LLM-based neuros
```

**Existing examples** (45+ built-in):
- `reply` — conversational response
- `planner` — goal → DAG planner
- `smart_router` — intent classification
- `screenshot_shortcut` — desktop action
- `openclaw_delegate` — external agent delegation
- `video_generator` — async media generation

**How neuros work**:
- `NeuroFactory` hot-reloads all `conf.json` files from `neuros/` recursively
- Each run gets `state["__llm"]` (BaseBrain), `state["__prompt"]`, and a streaming callback
- Stdout is captured and forwarded as `node.log` events
- Execution by `Executor` walks a DAG, one neuro at a time

---

## Layer 2: Agent Layer

**What it is**: An agent is a **named role** within an agency, composed of multiple neuros connected in a workflow. Agents have:
- A **name** and **personality** (system prompt / persona)
- A **workflow graph** defining how neuros are orchestrated
- **Blackboard read/write permissions** (what data it can access)
- **Triggers** (events that activate the agent)
- **Memory** (conversation context within the agent)

**Agents vs Neuros**:
| Aspect | Neuro | Agent |
|--------|-------|-------|
| Scope | Atomic skill | Composed of multiple neuros |
| Workflow | Single function | Multi-step graph |
| Memory | Stateless (uses global state) | Own conversation context |
| Identity | Generic | Has a persona, role, name |
| Triggers | Called by planner | Responds to events |

**Example Agent: `proposal_writer` (Upwork Agency)**

```
Agent: proposal_writer
Persona: "Expert Upwork freelancer who crafts compelling, human-sounding proposals"
Owned Neuros:
  - upwork_writer (core drafting)
  - upwork_reviewer (QA pass)
  - template_matcher (finds best template for job type)
  - tone_calibrator (adjusts voice to match job posting)
Workflow: template_matcher → upwork_writer → tone_calibrator → upwork_reviewer
Blackboard: reads jobs.json, profile.json, templates/; writes proposals/drafts/
Triggers: user request "write a proposal", or analyst scores job > threshold
```

---

## Layer 3: Workflow Engine (Hyperdimensional)

**Why "Hyperdimensional"**: Unlike Infinity's current linear DAG executor, agency workflows are **multi-path, conditional, and parallel**. Think of it as a directed graph where:

- Multiple branches can execute **in parallel**
- Nodes have **conditions** (only run if X is true)
- Nodes can **loop** (retry, iterate over a list)
- A node can **spawn** a sub-workflow and continue
- Nodes can **call other agents** as sub-agents
- The graph can **dynamically rewire** based on intermediate results

**Workflow Graph Schema**:
```json
{
  "name": "proposal_writer_flow",
  "start": ["template_matcher"],
  "nodes": {
    "template_matcher": {
      "neuro": "template_matcher",
      "params": {"job_id": "var:job_id"},
      "next": ["upwork_writer"],
      "parallel": false
    },
    "upwork_writer": {
      "neuro": "upwork_writer",
      "params": {"job_id": "var:job_id", "template": "var:template"},
      "next": ["tone_calibrator", "upwork_reviewer"],
      "parallel": true
    },
    "tone_calibrator": {
      "neuro": "tone_calibrator",
      "params": {"draft": "ref:upwork_writer.draft"},
      "next": null
    },
    "upwork_reviewer": {
      "neuro": "upwork_reviewer",
      "params": {"draft": "ref:upwork_writer.draft"},
      "next": ["approval_gate"]
    },
    "approval_gate": {
      "type": "human_gate",
      "input": "ref:upwork_reviewer.issues",
      "condition": "issues.length < 3",
      "on_pass": "mark_approved",
      "on_fail": "return_for_revision"
    }
  }
}
```

**Workflow Node Types**:

| Node Type | Description |
|-----------|-------------|
| `neuro` | Execute a single neuro |
| `agent` | Call another agent as sub-agent |
| `condition` | Branch based on a boolean expression |
| `parallel` | Execute multiple nodes simultaneously |
| `loop` | Iterate over a list (for each job in jobs) |
| `human_gate` | Pause for human approval/rejection |
| `subgraph` | Execute a named sub-workflow |
| `code` | Inline Python snippet for data transformation |
| `blackboard_write` | Write result to blackboard path |
| `notify` | Send notification (in-app, email, WhatsApp) |

**Workflow Executor** (new `core/hworkflow.py`):
- Replaces/extends `core/executor.py` for agency workflows
- Supports parallel node execution (via asyncio.gather)
- Condition evaluation with access to workflow state
- Loop unrolling for list inputs
- Human gate handling (pause, resume, reject paths)
- Real-time progress publishing to WebSocket
- Max depth / timeout limits for safety

---

## Layer 4: Agency Layer

**What it is**: An agency is a **team of agents** working toward a shared mission, with its own dashboard tab, data space, and workflow orchestration.

**Agency Schema**:
```json
{
  "name": "upwork_agency",
  "display_name": "Upwork Agency",
  "description": "Autonomous Upwork job hunter and proposal machine",
  "icon": "💼",
  "color": "#14F195",
  "agents": [
    {"name": "job_crawler", "role": "researcher"},
    {"name": "job_analyst", "role": "analyst"},
    {"name": "proposal_writer", "role": "writer"},
    {"name": "proposal_reviewer", "role": "qa"},
    {"name": "tracker", "role": "operations"},
    {"name": "poc_builder", "role": "builder"}
  ],
  "blackboard_paths": {
    "read": ["upwork/jobs.json", "shared/*"],
    "write": ["upwork/proposals/*", "projects/*"]
  },
  "triggers": [
    {"event": "scheduled", "cron": "*/30 * * * *", "agent": "job_crawler"},
    {"event": "job.new", "agent": "job_analyst"},
    {"event": "proposal.approved", "agent": "poc_builder"}
  ],
  "dashboard": {
    "tabs": ["jobs", "proposals", "clients", "analytics", "settings"]
  }
}
```

**Agency Dashboard** (UI):
Each agency gets a tab in the Infinity frontend:

```
┌─────────────┬──────────────┬──────────────┬────────────┬──────────────┐
│  Infinity   │  Upwork      │ Claude Code  │   Docs     │ Presentations │
│             │  Agency      │  Manager     │            │              │
├─────────────┼──────────────┼──────────────┼────────────┼──────────────┤
│  [Chat]     │  Jobs Feed   │  Terminal    │  Doc List  │  Slide Deck  │
│  [Voice]    │  Kanban      │  File Tree   │  Editor    │  Preview     │
│  [Screen]   │  Analytics   │  Artifacts   │  Templates │  Export      │
└─────────────┴──────────────┴──────────────┴────────────┴──────────────┘
```

### Planned Agencies

#### 1. Upwork Agency 💼
**Mission**: Find, analyze, bid on, and win Upwork projects.

```
Agents:
  job_crawler      → Browses Upwork, extracts jobs via browser automation
  job_analyst      → Scores jobs vs profile, ranks by fit
  proposal_writer  → Drafts human-sounding proposals with POC support
  proposal_reviewer→ QA pass before human approval
  tracker          → Monitors proposals, follow-ups, outcomes, feedback
  poc_builder      → Builds proof-of-concept prototypes for complex bids
  client_memoir    → Remembers every client interaction, preferences

Workflow (full pipeline):
  job_crawler (scheduled/ondemand)
      → job_analyst (scores each job)
          → [IF score > threshold] → proposal_writer
                                        → proposal_reviewer
                                            → [IF issues < 3] → human_gate
                                                → [ON APPROVE] → tracker.submit
                                                → [IF poc_needed] → poc_builder → attach
                                            → [ON REJECT] → proposal_writer (revise)
```

#### 2. Claude Code Manager Agency 🤖
**Mission**: Give Neo full control over Claude Code as a managed build engine.

```
Agents:
  cc_session_mgr   → Spawns/manages Claude Code subprocess lifecycle
  cc_context_loader→ Pre-loads project context from blackboard before tasks
  cc_output_parser → Parses terminal output, extracts files, errors, artifacts
  cc_watcher       → Monitors Claude Code for completion, errors, hangs

Workflow:
  User task request
      → cc_context_loader (reads blackboard specs, project context)
          → cc_session_mgr (spawns `claude` CLI subprocess)
              → cc_output_parser (streams + parses output in real-time)
                  → [ON COMPLETE] → cc_watcher → write artifacts to blackboard
                  → [ON ERROR] → retry / escalate to user
              → [ON USER INTERRUPT] → cc_session_mgr (SIGTERM)

Key capability: Real-time terminal streaming to dashboard (xterm.js)
```

#### 3. Documentation Agency 📝
**Mission**: Auto-generate and maintain documentation for all project deliverables.

```
Agents:
  doc_writer        → Generates README, API docs, user guides from code
  doc_formatter     → Applies consistent formatting, style, structure
  doc_reviewer      → Checks accuracy, completeness, readability
  doc_publisher     → Formats for different outputs (MD, PDF, HTML)

Workflow:
  POC completed on blackboard
      → doc_writer (reads code, generates structured docs)
          → doc_formatter (apply house style)
              → doc_reviewer (accuracy check)
                  → doc_publisher (export in requested format)
                      → write to blackboard/docs/{project_id}/
```

#### 4. Client Presentation Agency 🎨
**Mission**: Turn project deliverables into polished client-facing presentations.

```
Agents:
  slide_creator     → Generates slide content from project specs/deliverables
  asset_builder     → Creates diagrams, screenshots, demo clips
  demo_builder      → Builds interactive demos / GIFs from POC code
  deck_assembler    → Assembles slides + assets into final deck

Workflow:
  Project marked "ready for client"
      → slide_creator (generates slide content)
          → asset_builder (creates supporting visuals)
              → demo_builder (if POC exists, build demo reel)
                  → deck_assembler (combine all into deck)
                      → write to blackboard/presentations/{project_id}/
```

#### 5. (Future) Infinity AI Claude Code Manager ⚡
**Mission**: Neo uses Claude Code with complete I/O control, managed by Infinity.

```
Agents:
  claude_orchestrator → Sends commands to Claude Code, captures I/O
  claude_context_mgr  → Maintains context window across Claude Code sessions
  claude_artificer    → Extracts and organizes code artifacts from sessions
  claude_memory       → Remembers Claude Code session history for Neo

This is meta — it's the agency that manages Claude Code the tool itself,
so Neo can say "build me a working React auth system" and watch it happen,
interrupt it mid-way, redirect it, and have artifacts auto-organized.
```

---

## Blackboard (Shared Data Layer)

**Purpose**: Single source of truth. All agencies read/write here. Any agent (including Claude Code) can access it.

### Structure

```
blackboard/
├── .manifest.json               # Global index: all items, their locations, versions
├── .shared/                    # Cross-agency data
│   ├── memory.json             # Global learnings, context, preferences
│   ├── contacts.json           # Shared client/contact list
│   └── activity_log.json       # Audit trail of all agent actions
├── upwork/
│   ├── .meta.json              # Agency metadata
│   ├── profile.json            # User's skills, rates, preferences, tone
│   ├── jobs.json               # Cached + ranked job listings
│   ├── templates/              # Proposal templates, custom phrases
│   │   ├── default.md
│   │   ├── tech_stack.md
│   │   └── phrases.json
│   ├── proposals/
│   │   ├── drafts/{id}.json
│   │   ├── approved/{id}.json
│   │   ├── submitted/{id}.json
│   │   ├── won/{id}.json
│   │   └── lost/{id}.json
│   ├── clients.json
│   └── feedback.json           # Win/loss analysis, what worked
├── projects/
│   └── {project_id}/
│       ├── .meta.json          # Project metadata, client, status
│       ├── .spec.json          # Requirements / SOW
│       ├── poc/                # Proof-of-concept code
│       ├── deliverables/       # Final outputs
│       ├── timeline.json       # Milestones, deadlines
│       └── client_notes.json   # Client communication log
├── code/
│   ├── artifacts/              # Extracted code from CC Manager sessions
│   ├── snippets/               # Reusable code snippets
│   └── sandboxes/             # Isolated test directories
├── docs/
│   └── {project_id}/
│       ├── README.md
│       ├── api.md
│       ├── user_guide.md
│       └── changelog.md
├── presentations/
│   └── {project_id}/
│       ├── slides.md
│       ├── assets/
│       └── demo.mp4
```

### Metadata Schema (`.meta.json)

Every item on the blackboard carries metadata:

```json
{
  "id": "proposal_001",
  "type": "proposal",
  "agency": "upwork",
  "created_by": "proposal_writer",
  "created_at": "2026-03-22T10:00:00Z",
  "updated_at": "2026-03-22T11:30:00Z",
  "version": 3,
  "status": "approved",
  "tags": ["react", "frontend", "high-budget"],
  "links": [
    {"to": "job_upwork_123", "type": "for_job"},
    {"to": "proj_client_alpha", "type": "potential_project"}
  ],
  "size_kb": 12
}
```

### Blackboard Neuro

The `blackboard` neuro provides read/write/search capabilities to all agents:

```
neuros/blackboard/
├── conf.json
├── code.py   (read, write, search, link, diff, list)
└── prompt.txt
```

**Actions**:
- `read(path, metadata)` — Read file + metadata from blackboard
- `write(path, content, metadata)` — Write with auto-stamped metadata
- `search(query)` — Search by tag, agency, type, date, status
- `link(from, to, type)` — Create cross-reference between items
- `list(path)` — List directory contents with metadata
- `diff(path, since)` — Show changes since timestamp
- `manifest()` — Return full blackboard index

---

## Agent Communication Patterns

Agents within an agency don't call each other directly. They communicate via:

1. **Blackboard** — Write output to blackboard path, other agents read it
2. **Workflow triggers** — When agent A finishes, workflow engine activates agent B
3. **Event bus** — Pub/sub events (agent.action.completed, agent.action.failed)
4. **Shared state** — Workflow engine maintains shared state dict across all nodes

**Example: proposal_writer communicating with tracker**:
```
proposal_writer finishes draft
  → writes to blackboard/upwork/proposals/drafts/{id}.json
  → emits event: proposal.drafted
  → workflow engine receives event
  → activates proposal_reviewer
  → reviewer finishes
  → emits proposal.reviewed
  → workflow engine activates tracker
  → tracker logs to blackboard/upwork/feedback.json
```

---

## Inter-Agency Communication

Agencies are loosely coupled. They communicate through the blackboard and a shared event bus.

**Example: CC Manager → Documentation Agency**:
```
CC Manager completes POC
  → writes artifacts to blackboard/projects/{id}/poc/
  → emits event: project.poc.completed
  → global event bus broadcasts
  → Documentation Agency receives event
  → doc_writer activated
  → reads poc/ → generates docs
  → writes to blackboard/docs/{id}/
  → emits event: docs.generated
```

---

## Frontend Architecture

### Web/Desktop (Next.js in `infinity_desktop/`)

```
Tab bar at top:
  [∞ Infinity] [💼 Upwork] [🤖 Claude Code] [📝 Docs] [🎨 Presentations]

Each tab renders agency-specific view:
  - Upwork: Job feed, Kanban board, Analytics, Settings
  - Claude Code: Terminal emulator (xterm.js), file tree, artifact viewer
  - Docs: Document list, editor, preview
  - Presentations: Slide editor, deck preview

Shared components:
  - BlackboardDrawer: Browse blackboard from any tab
  - AgentStatusBar: Show active agents, recent actions
  - NotificationBell: Alerts across all agencies
  - AgencyChat: Chat interface per agency (or shared with Infinity)
```

### Mobile (React Native in `infinity_mobile/`)

```
Bottom tab bar:
  [Infinity] [Upwork] [CC] [Docs] [More]

Each tab:
  - Scrollable card list of agency items
  - Tap → detail view
  - Swipe actions (approve/reject proposals)
  - Pull to refresh
```

---

## Implementation Roadmap

### Phase 0: Foundation (do first)
- [ ] **Blackboard directory** — Create `blackboard/` with `.manifest.json`
- [ ] **Blackboard neuro** — read/write/search/link/diff
- [ ] **Workflow Engine** — `core/hworkflow.py` (extends Executor with parallel + conditionals)

### Phase 1: Agency Core (do second)
- [ ] **Agency registry** — `core/agency.py` — loads and manages agency configs
- [ ] **Agency routing** — Brain detects which agency based on message prefix or active tab
- [ ] **Profile per agency** — `profiles/<agency>.json` (planner, neuros, blackboard paths)
- [ ] **Agency API routes** — REST endpoints for each agency

### Phase 2: Upwork Agency
- [ ] Create 7 upwork agents (neuros + workflows)
- [ ] Upwork dashboard UI tab
- [ ] Proposal Kanban board
- [ ] Human-in-the-loop approval flow
- [ ] Browser automation for job crawling
- [ ] POC builder (creates simple code samples)

### Phase 3: Claude Code Manager
- [ ] `cc_session_mgr` agent — subprocess spawning, I/O streaming
- [ ] Terminal emulator in browser (xterm.js)
- [ ] `cc_output_parser` — extract artifacts, files, errors
- [ ] Artifact → blackboard write
- [ ] CC dashboard tab

### Phase 4: Documentation + Presentations
- [ ] Documentation agency agents
- [ ] Doc generator (reads code → MD)
- [ ] Slide creator from project specs
- [ ] Integration: CC Manager → Docs → Presentations pipeline

### Phase 5: Meta & Polish
- [ ] Infinity AI Claude Code Manager (control Claude Code itself)
- [ ] Mobile agency tabs
- [ ] Real-time notifications across agencies
- [ ] Analytics dashboard per agency
- [ ] Agency templates (clone an agency as base for new one)

---

## Key Design Principles

1. **Blackboard is the only shared contract** — Agencies don't import each other's code
2. **Agents are ephemeral, data is persistent** — Workflows run, complete, fail. The blackboard remembers
3. **Loose coupling via events** — Agents react to events, not direct calls
4. **Human-in-the-loop at key gates** — Proposals, commits, payments — all have human approval
5. **Claude Code is a managed tool** — Not an API, a subprocess Neo commands directly
6. **Agencies are composable** — Copy an agency config, swap the agents, you have a new agency
7. **Everything is gitignored** — blackboard/ contains sensitive client/proposal data

---

## File Structure (Target)

```
/home/ubuntu/infinity_dev/
├── blackboard/                      # Shared data layer (gitignored)
│   ├── .manifest.json
│   ├── .shared/
│   ├── upwork/
│   ├── projects/
│   ├── code/
│   ├── docs/
│   └── presentations/
├── core/
│   ├── brain.py                    # (existing)
│   ├── executor.py                 # (existing, linear DAG)
│   ├── neuro_factory.py            # (existing)
│   ├── hworkflow.py                # NEW: hyperdimensional workflow engine
│   ├── agency.py                   # NEW: agency registry + lifecycle
│   ├── blackboard.py               # NEW: blackboard read/write/search
│   └── pubsub.py                   # (existing)
├── neuros/
│   ├── blackboard/                 # (new) read/write/search neuro
│   ├── upwork/                     # NEW Upwork agency neuros
│   │   ├── job_crawler/
│   │   ├── job_analyst/
│   │   ├── proposal_writer/
│   │   ├── proposal_reviewer/
│   │   ├── tracker/
│   │   ├── poc_builder/
│   │   └── client_memoir/
│   ├── cc_manager/                 # NEW Claude Code agency neuros
│   │   ├── cc_session_mgr/
│   │   ├── cc_context_loader/
│   │   └── cc_output_parser/
│   ├── docs/                       # NEW Documentation agency neuros
│   │   ├── doc_writer/
│   │   ├── doc_formatter/
│   │   └── doc_publisher/
│   └── presentations/             # NEW Presentation agency neuros
│       ├── slide_creator/
│       ├── asset_builder/
│       └── deck_assembler/
├── agencies/                       # NEW: agency configs (not neuros)
│   ├── upwork_agency.json
│   ├── cc_manager_agency.json
│   ├── docs_agency.json
│   └── presentations_agency.json
├── profiles/
│   ├── general.json               # (existing)
│   ├── upwork.json               # NEW
│   ├── cc_manager.json           # NEW
│   └── docs.json                 # NEW
├── server.py                      # (existing + agency routes)
├── infinity_desktop/web/         # (existing + agency tabs)
├── infinity_mobile/             # (existing + agency tabs)
└── docs/
    ├── MULTI_AGENCY_ARCHITECTURE.md   # This document
    └── AGENCY_TEMPLATES.md             # How to build a new agency
```
