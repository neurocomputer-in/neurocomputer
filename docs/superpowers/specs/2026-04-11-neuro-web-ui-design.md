# Neuro Desktop Web UI — Design Spec

## Overview

Desktop web application for Neurocomputer — a multi-agent AI workspace. Mirrors the existing Android mobile app's functionality (minus screen sharing/remote desktop) with a VS Code-inspired multi-panel layout optimized for desktop.

**Goal**: Full feature parity with the mobile app so both clients share the same backend, same conversations, and stay in sync.

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Framework | Next.js (App Router) | SSR-ready, file-based routing, future 3D support (Three.js/R3F) |
| Styling | Tailwind CSS | Utility-first, fast iteration |
| Components | Chakra UI | Accessible, dark-theme friendly, simple API |
| State | Redux Toolkit | Structured global store, excellent devtools |
| Real-time | LiveKit (DataChannel + Audio) | Same as mobile — chat responses via DataChannel, voice via audio tracks |
| Language | TypeScript | Type safety across the frontend |

## Architecture

```
┌─────────────────────┐         ┌──────────────────────┐
│  neuro_web/ (:3000) │──HTTP──▶│ FastAPI backend (:7000)│
│  Next.js App        │         │  Brain → Executor     │
│                     │◀─DC────│  LiveKit agent rooms   │
└────────┬────────────┘         └──────────┬───────────┘
         │                                 │
         └───────── LiveKit Server (:7880) ┘
                   DataChannel + Audio
```

- **Sending messages**: HTTP POST to `/chat/send` (reliable)
- **Receiving responses**: LiveKit DataChannel subscription (real-time)
- **CRUD operations**: REST calls to existing endpoints (`/projects`, `/conversations`, `/agents`)
- **Voice**: LiveKit audio tracks (same flow as mobile)
- **Sync**: Both mobile and desktop talk to the same DB and LiveKit rooms. Conversation list polls every 10s.

No new backend endpoints required — the existing API covers all needs.

## Project Structure

```
neuro_web/
├── app/
│   ├── layout.tsx            # Root layout (Redux provider, Chakra provider, sidebar shell)
│   ├── page.tsx              # Main workspace (single-page app)
│   └── globals.css           # Tailwind base + theme variables
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx       # Projects + agent filter + conversations list
│   │   ├── TopBar.tsx        # Agent dropdown, voice toggles, connection status
│   │   └── TabBar.tsx        # Open conversation tabs
│   ├── chat/
│   │   ├── ChatPanel.tsx     # Message list container with auto-scroll
│   │   ├── MessageBubble.tsx # Single message (text, voice, markdown, code blocks)
│   │   ├── ChatInput.tsx     # Text input + voice record + send button
│   │   └── VoicePlayer.tsx   # Audio playback for voice messages
│   ├── project/
│   │   ├── ProjectList.tsx   # Sidebar project list with color dots + counts
│   │   ├── ProjectCreate.tsx # Create project modal (name, color picker)
│   │   └── ProjectMenu.tsx   # Context menu: rename, delete, manage agents
│   ├── agent/
│   │   ├── AgentDropdown.tsx # Agent selector with icons (Neuro, OpenClaw, OpenCode, NeuroUpwork)
│   │   └── AgentBadge.tsx    # Small agent icon + name chip
│   └── common/
│       ├── MarkdownRenderer.tsx  # Markdown + syntax-highlighted code blocks
│       └── LoadingIndicator.tsx  # Typing dots animation
├── store/
│   ├── index.ts              # configureStore with all slices
│   ├── projectSlice.ts       # projects[], selectedProject, CRUD thunks
│   ├── conversationSlice.ts  # conversations[], messages[], CRUD + polling thunks
│   ├── agentSlice.ts         # selectedAgent, availableAgents, filter state
│   ├── chatSlice.ts          # isLoading, inputText, activeTabCid
│   └── uiSlice.ts            # sidebarOpen, modals, dropdowns
├── services/
│   ├── api.ts                # Axios instance with baseURL, headers (ngrok-skip-browser-warning)
│   ├── livekit.ts            # LiveKit room connect/disconnect, DataChannel listener
│   └── voice.ts              # MediaRecorder for voice, TTS endpoint calls
├── hooks/
│   ├── useChat.ts            # Dispatch send, subscribe to LiveKit responses
│   ├── useProjects.ts        # Fetch/create/update/delete projects
│   ├── useConversations.ts   # Fetch/create/rename/delete/move conversations
│   └── useLiveKit.ts         # Room lifecycle, connection state
├── types/
│   └── index.ts              # Project, Agent, AgentType, Message, ConversationSummary, Tab
├── theme/
│   └── index.ts              # Chakra UI extendTheme with NeuroColors
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

## Layout

Fixed sidebar (260px) + main area. Single-page workspace — no multi-page routing for V1.

### Top Bar (48px)
- Logo ("N")
- Agent dropdown (icon + name + chevron)
- Spacer
- Voice toggles (Speak on/off, Voice record)
- Connection status indicator (green dot + "Connected")

### Sidebar (260px, left)
- **Projects section**: List with color dot, name, conversation count. "+" to create. Click to switch. Right-click for rename/delete/color.
- **Agent filter chips**: Horizontal row of pills — "All", "Neuro", "OpenClaw", "OpenCode", "NeuroUpwork". Filters the conversation list below.
- **Conversations list**: Filtered by selected project + agent. Shows title, agent icon, relative timestamp. Click opens as tab. Scrollable.
- Sidebar is resizable (drag handle) and collapsible (keyboard shortcut).

### Tab Bar (36px)
- Open conversation tabs with close (×) buttons
- Active tab has bottom border accent (#8B5CF6)
- "+" button creates new conversation
- Tabs persist per project (sessionState saved to backend)

### Chat Panel (center, flex)
- Messages with agent avatar on left (agent messages) or right-aligned (user messages)
- Agent name + timestamp above each message
- Markdown rendering with syntax-highlighted code blocks
- Typing indicator (three animated dots) when loading
- Auto-scroll to bottom on new message

### Chat Input (bottom)
- Text field with placeholder "Ask anything..."
- Attachment button (📎) — future use
- Voice record button (🎤)
- Send button (primary color)
- Enter to send, Shift+Enter for newline

## State Management (Redux Toolkit)

### Slices

**projectSlice**
```typescript
{
  projects: Project[],
  selectedProjectId: string | null,  // null = NoProject
  loading: boolean
}
// Thunks: fetchProjects, createProject, updateProject, deleteProject
```

**conversationSlice**
```typescript
{
  conversations: ConversationSummary[],  // for sidebar list
  openTabs: Tab[],
  activeTabCid: string | null,
  tabMessages: Record<string, Message[]>,  // cid → messages
  loading: boolean
}
// Thunks: fetchConversations, createConversation, renameConversation,
//         deleteConversation, moveConversation, loadMessages, persistSession
```

**agentSlice**
```typescript
{
  selectedAgent: AgentInfo,      // current filter / default for new chats
  availableAgents: AgentInfo[],  // from project.agents
}
```

**chatSlice**
```typescript
{
  isLoading: boolean,          // waiting for agent response
  inputText: string,
}
```

**uiSlice**
```typescript
{
  sidebarOpen: boolean,
  sidebarWidth: number,        // resizable
  showProjectCreate: boolean,
  showAgentDropdown: boolean,
}
```

### Data Flow

1. **App load**: `fetchProjects()` → set selectedProject (from localStorage or NoProject) → `fetchConversations(projectId)` → restore session (open tabs from project.sessionState) → `loadMessages(activeTabCid)` → connect LiveKit for active cid
2. **Send message**: user types + Enter → dispatch `sendMessage(text)` → optimistic add to tabMessages → HTTP POST `/chat/send` → set isLoading → LiveKit DataChannel fires with response → append to tabMessages → clear isLoading
3. **Switch project**: `persistSession()` → set selectedProject → `fetchConversations(newProjectId)` → restore session from project.sessionState
4. **Switch tab**: set activeTabCid → `loadMessages(cid)` → connect LiveKit for new cid
5. **New conversation**: POST `/conversation` → add tab → set active → wait for first message to send

## Real-time Communication

### LiveKit Integration
- On tab switch or new conversation: call `/chat/token` → connect to LiveKit room → subscribe to DataChannel events
- Topics listened to: `agent_response` (chat messages), `system_event` (task.done, etc.)
- On disconnect/reconnect: automatic via LiveKit SDK reconnection
- Connection state exposed via Redux `uiSlice` or dedicated hook

### Polling
- Conversation list: poll `GET /conversations?project_id=X` every 10 seconds
- Project list: poll `GET /projects` every 30 seconds
- Catches changes made from mobile or other clients

## TypeScript Types

```typescript
interface Project {
  id: string | null;        // null = NoProject
  name: string;
  description: string;
  color: string;            // hex
  updatedAt: string;
  conversationCount: number;
  sessionState: { openTabs: string[]; activeTab: string | null };
  agents: string[];         // ["neuro", "openclaw", ...]
}

enum AgentType { ALL, NEURO, OPENCLAW, OPENCODE, NEUROUPWORK }

interface AgentInfo {
  type: AgentType;
  name: string;
  description: string;
}

interface Message {
  id: string;
  text: string;
  isUser: boolean;
  isVoice: boolean;
  audioUrl?: string;
  timestamp?: string;
}

interface ConversationSummary {
  id: string;
  title: string;
  lastMessage: string;
  updatedAt: string;
  agentId?: string;
  projectId?: string;
}

interface Tab {
  cid: string;
  title: string;
  agentId: string;
  isActive: boolean;
}
```

## Theme

Dark theme matching the mobile app's NeuroColors:

| Token | Value | Usage |
|-------|-------|-------|
| `bg.deep` | `#060612` | Code blocks, input fields |
| `bg.base` | `#0a0a1a` | Sidebar, panels |
| `bg.surface` | `#0f0f20` | Chat area, main content |
| `bg.elevated` | `#1a1a2e` | Cards, tabs, hover states |
| `primary` | `#8B5CF6` | Accent, active states, buttons |
| `text.primary` | `#e0e0e0` | Main text |
| `text.secondary` | `#888888` | Timestamps, labels |
| `text.muted` | `#555555` | Placeholders, dividers |
| `success` | `#4ade80` | Connected status |
| `warning` | `#f59e0b` | Warnings |
| `error` | `#ef4444` | Errors, disconnect |

Chakra UI `extendTheme` with these tokens. Tailwind `tailwind.config.ts` extends colors with same values.

## Features NOT in V1

- Screen sharing / remote desktop / touchpad control (user is already on desktop)
- 3D features (future — Three.js/R3F ready via Next.js)
- Multi-user collaboration (single-user for now)
- Notification system
- File upload / attachment sending (attachment button is placeholder)

## API Endpoints Used

All existing — no backend changes needed:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/health` | Connection check |
| GET | `/projects` | List projects |
| POST | `/projects` | Create project |
| PATCH | `/projects/{pid}` | Update project (name, color, session, agents) |
| DELETE | `/projects/{pid}` | Delete project |
| POST | `/projects/{pid}/agents` | Add agent to project |
| DELETE | `/projects/{pid}/agents/{aid}` | Remove agent from project |
| GET | `/conversations?project_id=X` | List conversations |
| POST | `/conversation` | Create conversation |
| GET | `/conversation/{cid}` | Get conversation with messages |
| PATCH | `/conversation/{cid}` | Rename, change agent |
| DELETE | `/conversation/{cid}` | Delete conversation |
| PATCH | `/conversation/{cid}/project` | Move to another project |
| POST | `/chat/send` | Send chat message (HTTP) |
| POST | `/chat/token` | Get LiveKit token for chat room |
| POST | `/voice/token` | Get LiveKit token for voice |
| POST | `/tts` | Generate TTS audio |
| GET | `/agents` | List running agents |
| GET | `/agents/types` | List available agent types |
