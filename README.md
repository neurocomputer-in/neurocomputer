# Neurocomputer

Neurocomputer is an agentic software ecosystem built around a modular unit called a **neuro**.
A neuro can represent model logic, memory logic, context shaping, prompt composition, skills, workflows, tools, and agents.

The goal is to treat AI system design like composable engineering, not one giant prompt.

## Ecosystem

This repository is organized as a multi-interface ecosystem:

- **`neurocomputer/`**: core runtime, neuro framework, backend API, tests, scripts
- **`neuro_web/`**: desktop web interface (Next.js)
- **`neuro_mobile/`**: Android remote interface (Kotlin/Compose)
- **`experimental/`**: experimental interfaces and prototypes
- **`docs/`**: architecture and product docs (includes `docs/website/`)

## Interfaces

The same neuro runtime can be operated from multiple surfaces:

- **Backend API runtime**: `python neurocomputer/server.py` (default port `7000`)
- **Web app**: `neuro_web/` desktop client for conversations, projects, and agent orchestration
- **Mobile app**: `neuro_mobile/` Android remote client
- **Neurogramming IDE**: a graph-first coding interface where neuros are inspected, composed, and edited as reusable blocks

## Neurogramming IDE (LEGO for coding)

Neurogramming is the coding model in this repo: build software from composable neuros, connect them into workflows, then iterate safely.

The IDE direction is:

- **3D/graph-native neuro visualization** (node-and-edge mental model)
- **Source-aware editing** for each neuro (`conf.json`, `code.py`, `prompt.txt`)
- **Kind-based modularity** (skill, memory, model, context, prompt, agent, code, etc.)
- **Safe save pipeline** through validation + snapshots

Quick IDE backend:

```bash
python3 neurocomputer/scripts/ide_server.py
```

Then in web UI:

```bash
cd neuro_web
NEXT_PUBLIC_IDE_URL=http://127.0.0.1:8000 npm run dev
```

Open `http://localhost:3000/graph`.

## The Neuro Framework

### What is a neuro?

A neuro is a modular runtime unit. At minimum, a neuro is declared by config and executable logic:

- `conf.json`: contract, description, metadata
- `code.py`: implementation
- `prompt.txt`: optional prompt layer for LLM-driven neuros

Most neuros live in `neurocomputer/neuros/` using a taxonomy.

### Core primitives

The framework is intentionally split into orthogonal primitives:

- **Model neuro**: provider/model abstraction and model invocation
  - `neurocomputer/core/model_neuro.py`
- **Memory neuro**: memory storage, retrieval, and consolidation flows
  - `neurocomputer/core/memory.py`
  - `neurocomputer/core/memory_graph.py`
- **Context neuro**: context packaging and I/O contracts
  - `neurocomputer/core/context_neuro.py`
- **Prompt neuro**: prompt blocks and composition patterns
  - `neurocomputer/core/prompt_neuro.py`
- **Skill neuro**: discrete actionable capabilities under `neurocomputer/neuros/skill/`
- **Workflow neuro**: DAG/sequential/parallel orchestration
  - `neurocomputer/core/flows/dag_flow.py`
  - `neurocomputer/core/flows/sequential_flow.py`
  - `neurocomputer/core/flows/parallel_flow.py`
- **Tool-loop neuro**: in-reply tool calling and continuation
  - `neurocomputer/core/tool_loop_neuro.py`
- **Agent neuro**: role-specialized orchestration as composable agents
  - `neurocomputer/core/agent_neuro.py`

### Runtime orchestration

The orchestration path is centered around:

- `neurocomputer/core/brain.py`: routing, profile application, session orchestration
- `neurocomputer/core/neuro_factory.py`: neuro discovery, registry, execution
- `neurocomputer/server.py`: API surface + runtime glue

## Repository layout

Top-level layout (intentionally kept to 5 main folders):

```text
.
├── neurocomputer/   # core runtime + framework
├── neuro_web/       # web interface
├── neuro_mobile/    # android interface
├── experimental/    # experiments
└── docs/            # architecture + product docs
```

## Quick start

### 1) Setup Python runtime

```bash
git clone git@github.com:neurocomputer-in/neurocomputer.git
cd neurocomputer
python3 -m venv .venv
source .venv/bin/activate
pip install -r neurocomputer/requirements.txt
```

### 2) Configure environment

Create `.env` in repo root:

```dotenv
OPENAI_API_KEY=...
ELEVENLABS_API_KEY=...
SARVAM_API_KEY=...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

Optional local LiveKit:

```bash
cp neurocomputer/livekit.yaml.example livekit.yaml
livekit-server --config livekit.yaml
```

### 3) Run backend

```bash
python neurocomputer/server.py
```

Backend default: `http://127.0.0.1:7000`

### 4) Run web interface

```bash
cd neuro_web
npm install
npm run dev
```

### 5) Build mobile interface

```bash
cd neuro_mobile
./gradlew assembleDebug
```

## Neuro authoring workflow

Create a new neuro by adding a folder under `neurocomputer/neuros/` and defining:

1. `conf.json`
2. `code.py`
3. optional `prompt.txt`

Then validate and test through:

- IDE API endpoints in `neurocomputer/scripts/ide_server.py`
- runtime execution through `neurocomputer/core/neuro_factory.py`
- test suite in `neurocomputer/tests/`

## Key docs

- `docs/MULTI_AGENCY_ARCHITECTURE.md`
- `docs/MEMORY_ARCHITECTURE.md`
- `docs/AGENT_MEETING_ROOMS.md`
- `neurocomputer/scripts/README_ide.md`

