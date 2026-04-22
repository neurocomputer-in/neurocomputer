# Agent Meeting Rooms — Architecture Plan

**Status**: Draft
**Last Updated**: 2026-03-23

---

## Overview

This document covers the **Meeting Rooms** system — isolated collaboration spaces where multiple AI agents (Claude Code Infinity, Upwork Agent, custom agents) work together via text and voice — and the **Claude Code Infinity wrapper** that lets Claude Code CLI be managed from Infinity's mobile/desktop apps.

This is complementary to `MULTI_AGENCY_ARCHITECTURE.md` which covers the agency/agent framework. Meeting Rooms are the **real-time collaboration substrate** that any agency agent can participate in.

---

## Decisions (Confirmed)

- **Task Queue**: Hybrid — Celery+Redis for persistent Upwork polling, asyncio for real-time meeting rooms
- **Priority**: Upwork Agent first; Meeting Room infrastructure built alongside as collaboration substrate
- **Claude Code**: Local subprocess (simpler, lower latency; managed mode later)

---

## Part 1: Agent Meeting Rooms

### Concept

A **Meeting Room** is an isolated real-time collaboration space with:
- Multiple AI agents participating simultaneously
- Text chat (shared with existing Infinity chat)
- Voice channel (LiveKit room, multiple participants)
- Shared room state (context, files, task queue)
- Per-agent message routing (agents only see relevant messages)

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  MEETING ROOM (room_id)                                     │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │  Claude    │  │  Upwork    │  │  Infinity  │          │
│  │  Code      │  │  Agent     │  │  Brain     │          │
│  │  Infinity  │  │            │  │  (mediator)│          │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘          │
│        │                │                │                  │
│        └────────────────┼────────────────┘                  │
│                         │                                    │
│              ┌───────────▼───────────┐                      │
│              │  ROOM BRAIN           │                      │
│              │  (mediator neuro)      │                      │
│              │  • Routes messages     │                      │
│              │  • Merges responses    │                      │
│              │  • Manages turn-taking │                      │
│              └───────────────────────┘                      │
│                         │                                    │
│              ┌───────────▼───────────┐                      │
│              │  ROOM STATE            │                      │
│              │  • Per-room PubSub     │                      │
│              │  • Shared KV store     │                      │
│              │  • File context       │                      │
│              │  • Task queue         │                      │
│              └───────────────────────┘                      │
└──────────────────────────────────────────────────────────────┘
```

### Room Types

| Room Type | Purpose | Participants |
|-----------|---------|--------------|
| `text` | Text-only chat | Multiple text agents |
| `voice` | LiveKit voice room | Multiple voice agents |
| `hybrid` | Text + voice combined | Mixed |
| `board` | Whiteboard + agents | Visual collaboration |

### Relationship to Existing Architecture

- **Existing**: `ConversationScreen.tsx` already supports multiple agents via `AgentDropdown`
- **New**: Generalize Conversation → MeetingRoom with proper room isolation, per-agent state, shared context
- **Reuse**: WebSocket (`websocket.ts`), LiveKit voice, ChatBubble, VoiceMicButton, AudioMessageBubble
- **Per-conversation PubSub**: Existing `hub.queue(cid)` already provides room-scoped events — just extend for multi-agent routing

### Room State Management

```python
# core/room_state.py
class RoomState:
    """Per-room shared state, lives in memory (not persisted)"""

    def __init__(self, room_id: str):
        self.room_id = room_id
        self.agents = {}           # agent_id → AgentInfo
        self.context = {}          # shared KV store
        self.message_history = []   # recent messages (last 100)
        self.task_queue = []       # pending tasks
        self.hub = Hub()           # room-scoped event bus

    async def broadcast(self, topic: str, data: dict):
        """Send event to all agents in room"""
        await self.hub.queue(self.room_id).put({"topic": topic, "data": data})
```

### Agent Registry

```python
# core/agent_registry.py
class AgentRegistry:
    """Tracks all available agents and their capabilities"""

    def __init__(self):
        self.agents = {}  # agent_id → AgentInfo

    def register(self, agent_id, agent_type, capabilities, endpoint):
        """Register a new agent"""
        # agent_type: "claude_code", "upwork", "infinity", "custom"
        # capabilities: ["text", "voice", "code_write", "job_scrape"]

    def list_agents(self, capability_filter=None):
        """List agents, optionally filtered by capability"""

    async def send_message(self, agent_id, message, room_id):
        """Send message to specific agent"""

    async def get_status(self, agent_id):
        """Get agent availability/status"""
```

### API Endpoints (server.py additions)

```
GET  /api/rooms                    → list rooms
POST /api/rooms                    → create room {type, name, agents[]}
GET  /api/rooms/{room_id}          → get room details + participants
DELETE /api/rooms/{room_id}         → close room

POST /api/rooms/{room_id}/join     → join room {agent_id}
POST /api/rooms/{room_id}/leave     → leave room {agent_id}
POST /api/rooms/{room_id}/message   → send message {agent_id, text, type}

GET  /api/agents                   → list registered agents
POST /api/agents/register          → register agent {type, capabilities, endpoint}
GET  /api/agents/{id}/status       → check agent availability

WebSocket /ws/room/{room_id}       → real-time room events
```

### WebSocket Room Events

```json
// Topic: "room.message" — new message in room
{"topic": "room.message", "data": {"agent_id": "claude", "text": "...", "ts": "..."}}

// Topic: "room.agent_joined" — agent entered room
{"topic": "room.agent_joined", "data": {"agent_id": "upwork", "agent_type": "upwork"}}

// Topic: "room.agent_left"
{"topic": "room.agent_left", "data": {"agent_id": "claude"}}

// Topic: "room.task" — room task assigned/completed
{"topic": "room.task", "data": {"task_id": "...", "status": "done", "result": "..."}}
```

---

## Part 2: Claude Code Infinity Wrapper

### Concept

Wrap the Claude Code CLI as an agent that can be managed from Infinity's mobile/desktop app. The user should be able to:
- See Claude Code's terminal output in real-time
- Send commands / context to Claude Code
- Pause/resume/terminate sessions
- Have Claude Code participate in Meeting Rooms

### Architecture

```
┌─────────────────────────────────────────────┐
│  Claude Code Infinity Agent                  │
│  • Wraps claude code CLI                     │
│  • CLI client: automated_cli_client.py       │
│  • Managed via REST API                      │
│  • Runs in sandboxed environment            │
└─────────────────────┬───────────────────────┘
                      │ subprocess / WebSocket streaming
         ┌────────────▼───────────────────────┐
         │  CLAUDE CODE PROCESS MANAGER       │
         │  server.py: /claude-code/*         │
         │  • spawn(session_id, task)         │
         │  • send_message(session_id, msg)   │
         │  • get_status(session_id)          │
         │  • terminate(session_id)            │
         │  • stream_output(session_id)       │
         └─────────────────────────────────────┘
```

### CLI Integration

Existing `automated_cli_client.py` already provides:
- `ScenarioRunner(NeoClient)` — headless test driver
- Loads JSON scenarios with test steps
- Waits for DAG completion events

**Enhance to support:**
- Interactive mode (not just scripted scenarios)
- Real-time stdout/stderr streaming
- Bidirectional communication (send msg mid-session)
- Session management (pause, resume, terminate)

### API Endpoints

```
POST /api/claude-code/spawn         → start session {task?, cwd?}
POST /api/claude-code/{id}/chat     → send message to Claude Code
GET  /api/claude-code/{id}/status   → session status (running/paused/done)
POST /api/claude-code/{id}/pause    → pause session
POST /api/claude-code/{id}/resume   → resume session
POST /api/claude-code/{id}/terminate → end session
GET  /api/claude-code/{id}/history  → conversation history
WebSocket /ws/claude-code/{id}      → real-time stdout/stderr streaming
```

### Claude Code in Meeting Rooms

When Claude Code Infinity is in a Meeting Room:
1. It appears as an agent in `AgentRoster`
2. Messages directed to "Claude" are sent via `/api/claude-code/{id}/chat`
3. Output streams back via WebSocket → broadcast to room
4. User can interrupt via room controls → `terminate` or `pause`

---

## Part 3: Shared Component Architecture

### Shared Core (reuse across mobile + desktop)

```
infinity_core/                    # NEW: shared library
  components/
    ChatBubble.tsx                # Base message bubble
    AgentChatBubble.tsx           # Bubble with agent identity + avatar
    VoiceMicButton.tsx            # Mic control (exists in mobile)
    AudioMessageBubble.tsx       # Audio message (exists)
    AgentRoster.tsx              # Room participants list
    RoomToolbar.tsx              # Leave room, toggle voice/text
    TurnIndicator.tsx            # Show whose turn / responding agent
    ThinkingIndicator.tsx        # AI processing state
  services/
    websocket.ts                 # Unified WebSocket client
    agentRegistry.ts             # Agent discovery + messaging
    roomManager.ts               # Meeting room CRUD
  hooks/
    useAgent.ts                  # Connect to specific agent
    useRoom.ts                   # Meeting room state
    useVoiceRoom.ts              # LiveKit voice room
```

### Mobile Reuse

```
infinity_mobile/
  src/
    screens/
      MeetingRoomScreen.tsx      # Generalized from ConversationScreen
      AgentChatScreen.tsx        # Single agent chat (1:1)
    components/                 # Imports from infinity_core
    services/                    # Imports from infinity_core
```

### Desktop Reuse

```
infinity_desktop/
  web/src/
    app/
      room/[roomId]/page.tsx     # Meeting room page
      agents/page.tsx            # Agent management
    components/                  # Imports from infinity_core
    hooks/                       # Imports from infinity_core
```

---

## File Structure (Meeting Rooms + Claude Code)

```
/home/ubuntu/infinity_dev/
├── core/
│   ├── room_state.py            # NEW: per-room state + room-scoped Hub
│   ├── agent_registry.py        # NEW: agent registration + discovery
│   └── ...
├── server.py                     # + room/agent/claude-code endpoints
├── infinity_core/               # NEW: shared TS components
│   ├── components/
│   ├── services/
│   └── hooks/
├── neuros/
│   ├── room_mediator/           # NEW: mediates multi-agent conversations
│   └── ...
└── docs/
    ├── AGENT_MEETING_ROOMS.md   # This document
    └── MULTI_AGENCY_ARCHITECTURE.md  # Existing
```

---

## Implementation Order

1. **Agent Registry** (`core/agent_registry.py`) — register/list agents
2. **Room State** (`core/room_state.py`) — per-room Hub + state
3. **Room API endpoints** — CRUD + join/leave/message
4. **WebSocket room events** — broadcast to room participants
5. **Claude Code process manager** — spawn/chat/terminate via subprocess
6. **Claude Code WebSocket streaming** — real-time output
7. **Claude Code in Meeting Rooms** — agent joins room, streams output
8. **Shared TS components** (`infinity_core/`) — reuse in mobile + desktop
9. **MeetingRoomScreen** — mobile, generalized from ConversationScreen
10. **Room page** — desktop web

---

## Verification

1. **Room creation**: POST `/api/rooms` → room created, agents can join via WebSocket
2. **Multi-agent message**: Send message to room → all agents receive via WebSocket
3. **Claude Code spawn**: POST `/api/claude-code/spawn` → subprocess starts, stdout streams via WS
4. **Claude Code in room**: Add Claude Code agent to room → its output appears in room chat
5. **Mobile room**: Infinity app → create room → see agent roster → toggle voice → send messages
