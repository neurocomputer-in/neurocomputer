# Neurocomputer

**An agentic AI framework where hot-swappable skills ("neuros") are orchestrated by a Brain that plans, routes, and executes tasks — all over a real-time voice + data channel.**

---

## Table of Contents

1. [Core Neuro Framework](#1-core-neuro-framework)
2. [Desktop Server Setup](#2-desktop-server-setup)
3. [Mobile Application](#3-mobile-application)
4. [Agents](#4-agents)
5. [Neuros — 50+ Skills](#5-neuros--50-skills)
6. [API Reference](#6-api-reference)
7. [Configuration](#7-configuration)
8. [Quick Start](#8-quick-start)

---

## 1. Core Neuro Framework

The heart of the system is the **Brain**, which implements a ReAct-style (Reason + Act) loop to handle any user request.

### Architecture

```
User Message
    │
    ▼
Smart Router ─────────────────────────────────┐
  • Is this a simple reply?                    │
  • Which skill (neuro) is needed?             │
    │                                          │
    ▼ reply                    ▼ skill         │
Direct Reply             Planner (DAG)         │
  → answer                → nodes             │
                            → executor        │
                              → neuros run    │
                              → reply neuro   │
                              → final answer ←┘
```

### Key Components

| Module | Role |
|--------|------|
| `core/brain.py` | Main orchestrator — Smart Router → Planner → Executor loop |
| `core/agent.py` | Agent instance wrapping a Brain with identity and config |
| `core/agent_manager.py` | Singleton that manages all live Agent instances |
| `core/agent_configs.py` | Defines the Neuro, OpenClaw, OpenCode, Upwork agent configs |
| `core/neuro_factory.py` | Loads, caches, and runs individual neuros |
| `core/executor.py` | Runs a DAG (Directed Acyclic Graph) of neuro nodes |
| `core/conversation.py` | Maintains per-session message history |
| `core/environment_state.py` | Tracks goal, recent observations, and ReAct context |
| `core/pubsub.py` | Lightweight in-process event hub for Brain → UI communication |

### How the Brain Works

1. **Smart Router**: A single LLM call classifies the request into `reply` (direct answer) or `skill` (run a neuro).
2. **Direct Reply**: If no skill is needed, the reply is served immediately.
3. **Planner**: For skills requiring multiple steps, the Planner produces a DAG of neuro calls.
4. **Executor**: Executes each node in the DAG, passing outputs from one neuro as inputs to the next.
5. **Publish**: After each step, events are published to both the WebSocket pubsub hub and the LiveKit DataChannel for real-time UI updates.

### Profiles

Profiles control which neuros are visible and how the Brain behaves.

| Profile | Description |
|---------|-------------|
| `general` | Default mode — all general-purpose neuros available |
| `code_dev` | Code editing and project management neuros |
| `neuro_dev` | Full neuro-building and meta-programming mode |

Switch profiles in chat: `/profile code_dev` or `/dev on`.

### Voice Pipeline

```
Microphone → Silero VAD → Sarvam STT (Streaming WebSocket) → Brain → ElevenLabs TTS → Speaker
                                                                   ↓
                                                          LiveKit DataChannel → Mobile UI
```

- **VAD**: Silero VAD tuned for low-latency speech start detection (25ms silence threshold)
- **STT**: Sarvam `saaras:v3` model, streaming over WebSocket for real-time transcription
- **LLM**: Custom `InfinityBrainLLM` adapter routes through the Brain instead of a raw model
- **TTS**: ElevenLabs streaming TTS with `eleven_flash_v2_5` and sentence-level chunking
- **Transport**: All audio and events go through a LiveKit room → Android app via WebRTC

---

## 2. Desktop Server Setup

The server (`server.py`) is a **FastAPI** application that exposes the Brain over HTTP and WebSocket, manages agents, handles voice sessions, and streams the desktop screen.

### Requirements

- Python 3.11+
- LiveKit server running locally (see `livekit.yaml.example`)
- TURN server for WebRTC NAT traversal (see `turnserver.conf.example`)

### Starting the Server

```bash
# 1. Copy and fill in environment
cp .env.example .env   # fill in your API keys

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start LiveKit (in a separate terminal)
livekit-server --config livekit.yaml

# 4. Start the main server
python server.py
```

### Desktop Streaming

The `core/desktop_stream.py` module captures the screen and publishes it as a LiveKit video track.

- Uses **MSS** for fast screen capture on Linux
- Supports **multi-monitor switching** via the `/stream/switch-monitor` API
- Supports zoom (1x–10x) and pan control via the `/stream/view` API
- The Android app receives the stream as a native WebRTC `VideoTrack`

### Mouse Controller

`core/mouse_controller.py` receives mouse events from the Android app and applies them via system-level input injection:

- Relative mouse movement (touchpad mode)
- Left / right / middle click
- Scroll wheel
- Keyboard input and combos (e.g. Ctrl+C, Alt+Tab)
- Multi-monitor offset awareness

### TURN Server (for remote access over the internet)

Use `coturn` with the template in `turnserver.conf.example`. The LiveKit server must reference the same external IP.

```bash
turnserver -c /etc/turnserver.conf
```

---

## 3. Mobile Application

The Android app is a Jetpack Compose application in `neuro_mobile_app/`. It connects to the backend over LiveKit (WebRTC) for real-time messaging, voice, and remote desktop streaming.

### Screens & Navigation

| Screen | Description |
|--------|-------------|
| **ConversationScreen** | Main screen with chat, agent switching, remote desktop, voice |
| **SettingsModal** | Backend URL configuration, connection settings |

### ConversationScreen Breakdown

#### Header Bar
- **Agent Selector Button**: Shows the active agent's logo and name. Tap to open the agent dropdown.
- **History Button**: Opens the Chat History drawer with per-agent conversation list.
- **New Chat (+) Button**: Creates a new conversation tab for the active agent.
- **TTS Toggle**: Speaker icon to enable/disable text-to-speech for agent replies.
- **Menu (☰) Button**: Opens the side drawer for remote desktop and settings.

#### Tab Bar
- Horizontal scrollable tabs, one per open conversation.
- Tap a tab to switch context; long-press to rename; swipe or tap × to close.
- Each agent maintains its own tab set independently.

#### Chat Area
- Full conversation history (user + agent messages).
- Separate display for text, voice (waveform player), and TTS-generated audio.
- Auto-scrolls to the latest message in real time.

#### Input Bar
- Text input with send button.
- **Voice Typing Button** (Mic 🎤): Hold to dictate; message populates the input field after release.
- **Attachment Menu**: Expandable menu for future file sharing.

### Remote Desktop Mode

Activated via the Side Drawer → "Remote Desktop". The screen transitions to a fullscreen landscape view.

#### Fullscreen UI Controls

| Location | Control | Function |
|----------|---------|----------|
| Right sidebar | 🎤 Mic | Toggle voice recording |
| Right sidebar | 🖱 Mouse | Toggle touchpad/cursor mode |
| Right sidebar | 📺 Monitor | Switch desktop display (multi-monitor) |
| Right sidebar | ⛶ Exit | Exit fullscreen mode |
| Top-right | Agent Pill | Open agent dropdown even in fullscreen |
| Left side | Draggable Toolbar | Floating multi-function panel (see below) |

#### Draggable Floating Toolbar
The left-side toolbar is a draggable panel that floats over the remote desktop. It contains:

- **Agent Button**: Tap to switch the active agent mid-session
- **Voice Typing**: Dictate to the agent without leaving the remote view
- **Keyboard 🎹 Button**: Opens the full on-screen keyboard overlay (with special keys, Ctrl/Alt combos)
- **Scroll Mode**: Switches touchpad to scroll-wheel mode
- **Click Mode**: Switches touchpad to precise click mode
- **Focus Mode**: Sends a tab/focus key to the remote desktop

#### Touchpad Overlay
When mouse mode is active, a transparent gesture layer covers the video:

- **Single finger drag** → relative cursor movement
- **Single tap** → left click
- **Double tap** → double click
- **Two-finger drag** → scroll
- **Two-finger tap** → right click

---

## 4. Agents

All agents use the same Brain and neuro system but have different identities, descriptions, and behavioral contexts.

| Agent | ID | Logo | Description |
|-------|----|------|-------------|
| **Neuro** | `neuro` | 🧠 Round cyan logo | General-purpose — handles any task |
| **OpenClaw** | `openclaw` | Purple claw logo | Browser automation via the OpenClaw WS gateway |
| **OpenCode** | `opencode` | `[]` brackets logo | Coding and development specialization |
| **NeuroUpwork** | `neuroupwork` | Orange Upwork logo | Freelance job analysis and proposal generation |

### Switching Agents

- **In Chat**: Tap the agent pill in the header bar to open the dropdown.
- **In Remote Desktop**: Tap the agent pill at top-right or the Agent Button in the draggable toolbar.
- Switching agents clears the active tab and loads conversation history for the new agent.

### OpenClaw Integration

The OpenClaw agent connects to a local WebSocket gateway that controls a browser automation service. It uses a device identity keypair for auth and the `openclaw_delegate` neuro to proxy tasks to the browser agent.

### Per-Agent Conversations

Each agent has an independent list of conversations. The Chat History drawer shows only the conversations for the currently selected agent.

---

## 5. Neuros — 50+ Skills

Neuros live in `neuros/<name>/` and each contains:
- `conf.json` — name, description, inputs, outputs
- `code.py` — `async run(inputs, state)` function

Neuros hot-reload at runtime — no server restart needed.

### Task Execution
| Neuro | Description |
|-------|-------------|
| `smart_router` | Unified routing — direct reply or skill selection |
| `planner` | Converts goal into a multi-step DAG |
| `executor` | Runs the DAG of neuros |
| `reply` | Generates a final natural-language answer |
| `reflector` | Self-evaluates and improves responses |

### Code Development
| Neuro | Description |
|-------|-------------|
| `code_planner` | Plans code tasks into file operations |
| `code_file_read` | Read file contents |
| `code_file_write` | Write or overwrite files |
| `code_file_diff` | Show diff between file versions |
| `code_file_list` | List project files |
| `code_scan` | Scan for code patterns or issues |
| `code_project_manager` | Manage multi-file project state |
| `dev_planner` | Planner for neuro development tasks |
| `dev_new` | Create a new neuro from scratch |
| `dev_edit` | Edit an existing neuro |
| `dev_save` | Save neuro changes |
| `dev_diff` | Show diff in a neuro |
| `dev_patch` | Apply patch to a neuro |
| `dev_show` | Display current neuro source |
| `dev_reset` | Reset neuro to last saved state |
| `dev_codegen` | AI code generation inside a neuro |

### Upwork Workflow
| Neuro | Description |
|-------|-------------|
| `upwork_list` | List captured Upwork job postings |
| `upwork_analyze` | Analyze a job for fit and effort |
| `upwork_finalize` | Finalize analysis and score |
| `upwork_proposal` | Draft a tailored proposal |
| `upwork_save_frame` | Save a screenshot of a job listing |

### Desktop & System
| Neuro | Description |
|-------|-------------|
| `screenshot_shortcut` | Take a screenshot (Linux shortcut) |
| `screen_lock_ubuntu` | Lock the desktop |
| `unlock_pc` | Unlock the desktop |
| `open_file_explorer` | Open Files application |
| `move_mouse_to_center` | Move cursor to screen center |
| `move_mouse_top_right` | Move cursor to screen top-right |

### Browser & Integrations
| Neuro | Description |
|-------|-------------|
| `openclaw_delegate` | Proxy task to OpenClaw browser agent |
| `intent_classifier` | Intent classification helper |
| `load_skill` | Hot-load a skill from file |
| `install_python_library` | Install a Python package at runtime |

### Utilities
| Neuro | Description |
|-------|-------------|
| `neuro_list` | List all available neuros |
| `neuro_crafter` | Help design new neuros |
| `echo` | Echo input for debugging |
| `wait` | Sleep for N seconds |
| `write_file` | Write content to a file |
| `delete_file` | Delete a file |
| `play_text_audio` | Play text via TTS |
| `linkedin_post_creator` | Draft LinkedIn posts |
| `video_generator` | Generate video content |
| `prime_checker` | Check if a number is prime (example) |

---

## 6. API Reference

### Agent Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/agents` | List all running agent instances |
| `GET` | `/agents/types` | List configured agent types |
| `POST` | `/agents/{type}` | Create or switch to an agent type |
| `POST` | `/chat` | Send a chat message to the active agent |
| `POST` | `/chat/token` | Get a LiveKit token for a conversation's chat room |

### Conversation Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/conversation` | Create a new conversation |
| `GET` | `/conversations` | List conversations (filter by `?agent_id=`) |
| `GET` | `/conversation/{cid}` | Get conversation + messages |
| `PATCH` | `/conversation/{cid}` | Rename a conversation |
| `DELETE` | `/conversation/{cid}` | Delete a conversation |

### Voice Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/voice/token` | Get LiveKit token for voice session |
| `POST` | `/voice_message` | Submit a voice transcription to the brain |
| `POST` | `/tts` | Generate TTS audio for a message |

### Desktop Stream Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/stream/start` | Start desktop screen capture and publishing |
| `POST` | `/stream/stop` | Stop desktop stream |
| `POST` | `/stream/switch-monitor` | Switch capture to another monitor |
| `POST` | `/stream/view` | Update zoom/pan/rotation |
| `POST` | `/mouse/move` | Send relative mouse movement |
| `POST` | `/mouse/click` | Send mouse click |
| `POST` | `/mouse/scroll` | Send scroll event |
| `POST` | `/keyboard/send` | Send keyboard key or combo |

### Upwork Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/upwork/capture` | Save a captured job frame |
| `POST` | `/upwork/finalize/{slug}` | Process and finalize a job |
| `GET` | `/upwork/jobs` | List all captured jobs |

### OpenClaw Endpoints
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/openclaw/connect` | Connect to OpenClaw gateway |
| `POST` | `/openclaw/disconnect` | Disconnect from gateway |
| `GET` | `/openclaw/state` | Get connection state |
| `POST` | `/openclaw/send` | Send a task to OpenClaw |

### WebSocket Endpoints
| Path | Description |
|------|-------------|
| `WS /ws/{cid}` | Real-time event stream for a conversation |
| `WS /ws/claude` | Bridge to Claude CLI server (port 9593) |

---

## 7. Configuration

All sensitive keys go in `.env` (never committed to git):

```dotenv
# OpenAI (for Planner, Router, Reply neuros)
OPENAI_API_KEY=sk-...

# ElevenLabs (TTS)
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=JBFqnCBsd6RMkjzDR9eL

# Sarvam (STT)
SARVAM_API_KEY=...

# LiveKit
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...

# OpenClaw
OPENCLAW_WS_URL=ws://127.0.0.1:18789
OPENCLAW_GATEWAY_TOKEN=...
OPENCLAW_IDENTITY_PATH=~/.openclaw/identity/device.json
```

### LiveKit Server (`livekit.yaml.example`)

```yaml
port: 7880
rtc:
  port_udp: 50000-60000
  use_external_ip:
    - "YOUR_PUBLIC_IP"
  turn:
    enabled: true
    host: "YOUR_PUBLIC_IP"
    port: 3478
    username: "your_turn_user"
    password: "your_turn_password"
```

Copy to `livekit.yaml` and fill in your server's public IP. **Never commit `livekit.yaml` or `turnserver.conf` — they are `.gitignore`d.**

---

## 8. Quick Start

```bash
# 1. Clone
git clone https://github.com/neurocomputer-in/neurocomputer.git
cd neurocomputer

# 2. Python setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Configure
cp livekit.yaml.example livekit.yaml  # edit with your details
# Create .env with your API keys (see section 7)

# 4. Start LiveKit
livekit-server --config livekit.yaml &

# 5. Start the server
python server.py
# → Server running at http://0.0.0.0:8000

# 6. Build the Android app
cd neuro_mobile_app
./gradlew assembleDebug
# Or run deploy_android.sh to build + install on device
```

### Setting Up the Mobile App

1. Open the app → tap **Settings (⚙)** → set your backend URL (e.g. `http://192.168.1.100:8000`).
2. Select an agent from the **Agent Selector** in the header.
3. Start chatting. Use the **🎤 mic** button for voice input.
4. For remote desktop, tap **≡ (Menu) → Remote Desktop** — the screen streams directly from your PC to your phone over WebRTC.
