<p align="center">
  <img src="assets/neuro.png" width="80" height="80" alt="Neurocomputer Logo">
</p>

<h1 align="center">Neurocomputer</h1>
<p align="center"><strong>Your desktop, your agents, your pocket.</strong></p>
<p align="center">An open-source AI-native ecosystem that lets you see, control, and automate any desktop — entirely from a mobile application.</p>

<p align="center">
  <a href="https://github.com/neurocomputer-in/neurocomputer">GitHub</a> · <a href="#quick-start">Quick Start</a> · <a href="#the-agents">Agents</a> · <a href="#neuro-framework">Framework</a>
</p>

---

## What Is Neurocomputer?

Neurocomputer is a complete ecosystem that bridges the gap between a powerful desktop machine and the device you always have with you — your phone.

It works at **two layers simultaneously**:

1. **Application Layer** — A mobile app that gives you a live view of your desktop screen, lets you control the mouse and keyboard with precision gestures, and chat with specialized AI agents that can execute tasks on your behalf.

2. **Framework Layer** — A modular agentic engine called **Neuro** where any workflow can be captured as a reusable skill, chained into multi-step plans, and executed autonomously. The system reasons about what to do, acts, observes the result, and iterates — just like a human operator.

The result: you can issue a command from your couch, your commute, or across the world, and watch your desktop respond in real time.

---

## Core Capabilities

### 📺 Remote Desktop — See & Control

Stream your full desktop to your Android device over WebRTC with ultra-low latency.

| Feature | How It Works |
|---|---|
| **Live Screen** | MSS captures frames → LiveKit publishes a VideoTrack → phone renders natively |
| **Mouse Control** | Glassmorphic touchpad overlay: drag to move, tap to click, two-finger scroll |
| **Keyboard** | Full on-screen keyboard with special keys, Ctrl/Alt combos, and macro hotkeys |
| **Multi-Monitor** | Switch between displays with a single tap |
| **Zoom & Pan** | Pinch to zoom up to 10x on any area of the screen |

### 🎙 Voice — Speak & Listen

Talk to the agent hands-free. The voice pipeline is optimized for low latency:

**Mic → Silero VAD → Sarvam Streaming STT → Brain → ElevenLabs TTS → Speaker**

All audio travels through LiveKit, the same transport used for the desktop stream.

### 🤖 Automation — Command & Execute

Tell the agent what you want done. It will plan the steps, operate the mouse and keyboard, read the screen, and complete the task.

- *"Lock my PC"* — executes instantly
- *"Open the file explorer and find my project folder"* — plans two steps, runs them in sequence
- *"Analyze this Upwork job and draft a proposal"* — chains multiple specialized skills together

Every action can be saved as a **skill** and reused later, building a personal library of automations.

---

## The Agents

Neurocomputer ships with four specialized agents. Each one shares the same Brain engine but is tuned for a different domain.

| Agent | Logo | What It Does |
|---|---|---|
| **Neuro** | <img src="assets/neuro.png" width="20"> | General-purpose assistant. Routes intents, plans tasks, and orchestrates skills. |
| **OpenClaw** | <img src="assets/openclaw.png" width="20"> | Browser automation. Connects to a local WebSocket gateway to physically browse the web, click elements, and extract data. |
| **OpenCode** | <img src="assets/opencode.png" width="20"> | Coding agent. Reads, writes, diffs, and patches code across entire repositories. |
| **NeuroUpwork** | <img src="assets/upwork.png" width="20"> | Freelance workflow. Captures job listings, scores them for fit, and drafts tailored proposals and POCs. |

Switch agents instantly from the mobile app — either through the header bar or the floating toolbar during remote desktop sessions.

---

## Neuro Framework

At the core of every agent is the **Neuro** agentic framework. It is designed around three principles:

1. **Skills are modular.** Each skill ("neuro") lives in its own folder with a `conf.json` and a `code.py`. Drop a new folder in, and the Brain picks it up at runtime — no restart needed.

2. **Planning is automatic.** Complex requests are broken into a DAG (Directed Acyclic Graph) of skill calls. The Planner generates the graph; the Executor runs it node by node, passing outputs forward.

3. **Reasoning is built-in.** The Smart Router classifies every request in a single LLM call: is this a direct reply, or does it need a skill? If a skill, which one? This keeps simple conversations fast and complex tasks structured.

### Architecture

```
User Input (text or voice)
     │
     ▼
 Smart Router ──── reply? ──── Direct Answer
     │
     ▼ skill
  Planner ──── generates DAG
     │
     ▼
  Executor ──── runs nodes ──── Neuro A → Neuro B → Neuro C
     │
     ▼
  Reply Neuro ──── final answer back to user
```

### 50+ Built-In Skills

| Category | Examples |
|---|---|
| **Desktop** | Lock screen, unlock, take screenshot, open file explorer, move mouse to position |
| **Code** | Read/write/diff files, scan projects, plan code changes, generate patches |
| **Upwork** | List jobs, analyze fit, finalize scoring, draft proposals, capture screenshots |
| **Browser** | Delegate tasks to OpenClaw gateway for web interaction |
| **Meta** | List available skills, create new skills, edit existing skills at runtime |
| **Utilities** | TTS playback, LinkedIn post drafts, video generation, prime checker (demo) |

### Profiles

Profiles control which skills are visible to the Brain:

| Profile | Use Case |
|---|---|
| `general` | Default. All general-purpose skills available. |
| `code_dev` | Code editing and project management focus. |
| `neuro_dev` | Full meta-programming — build and edit skills themselves. |

Switch with `/profile code_dev` or `/dev on` in chat.

---

## The Mobile App

A Jetpack Compose Android application that serves as the unified interface for the entire ecosystem.

### Key UI Elements

- **Agent Selector** — Tap the agent pill in the header to switch between Neuro, OpenClaw, OpenCode, and NeuroUpwork.
- **Chat Interface** — Full conversation history with text, voice waveforms, and TTS playback per message.
- **Voice Typing** — Hold the mic button to dictate; transcription populates the input field.
- **Tab Bar** — Multiple conversations per agent, each tracked independently.
- **Side Drawer** — Access remote desktop, settings, and overlay controls.

### Remote Desktop Mode

Tap "Remote Desktop" in the side drawer to enter fullscreen landscape mode:

- **Right Sidebar**: Mic, mouse toggle, monitor switch, exit fullscreen
- **Left Toolbar**: Draggable floating panel with voice typing, keyboard, scroll/click/focus modes, and agent switcher
- **Touchpad Overlay**: Single-finger drag (move), tap (click), double-tap (double click), two-finger drag (scroll), two-finger tap (right click)

---

## The Secure Sandbox Approach

Neurocomputer is designed to run inside a **private, isolated machine** — a dedicated workstation, a VM, or a containerized environment that is separate from your personal host OS.

Why? Because autonomous agents need access to your screen, your files, and your inputs. By isolating this to a dedicated environment, you control exactly what the agents can see and touch. You drop in only the files you want to work with, and keep everything else safely walled off.

This is not just a feature — it is the recommended deployment model.

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/neurocomputer-in/neurocomputer.git
cd neurocomputer
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

Create a `.env` file with your API keys:

```dotenv
OPENAI_API_KEY=sk-...
ELEVENLABS_API_KEY=...
SARVAM_API_KEY=...
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

Set up LiveKit:

```bash
cp livekit.yaml.example livekit.yaml   # edit with your public IP
livekit-server --config livekit.yaml &
```

### 3. Run

```bash
python server.py
# Server starts at http://0.0.0.0:8000
```

### 4. Connect the Mobile App

```bash
cd neuro_mobile_app
./gradlew assembleDebug
# Install the APK, then set your server URL in Settings
```

---

## API Overview

| Endpoint | Purpose |
|---|---|
| `POST /chat` | Send a message to the active agent |
| `GET /agents` | List running agents |
| `POST /agents/{type}` | Switch to a specific agent |
| `POST /stream/start` | Begin desktop screen streaming |
| `POST /mouse/move`, `/click`, `/scroll` | Remote input controls |
| `POST /keyboard/send` | Send keystrokes and combos |
| `GET /voice/token` | Get LiveKit token for voice sessions |
| `POST /conversation` | Create a new conversation |
| `GET /conversations?agent_id=` | List conversations filtered by agent |

Full endpoint documentation is available in `server.py`.

---

## Roadmap

- [ ] **Vision-Action Loop** — Integrate vision-language models so agents can autonomously read the screen and decide what to click next, driven purely by a high-level prompt.
- [ ] **Cross-Platform Inputs** — Extend remote control to Windows and macOS hosts.
- [ ] **Custom Hotkey Macros** — Let users define their own mobile toolbar buttons mapped to complex desktop actions.
- [ ] **Local LLM Offloading** — Run reasoning on efficient local models (Gemma, Llama) to reduce cloud API dependency.
- [ ] **File Drop Sandbox** — Seamless mechanism to push files from mobile into the isolated agent environment.

---

<p align="center"><sub>Built for a new generation of workflows.</sub></p>
