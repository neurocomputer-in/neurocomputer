# Neuro Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Next.js desktop web app at `neuro_web/` that gives full chat/project/agent feature parity with the Android mobile app, sharing the same FastAPI backend and LiveKit server.

**Architecture:** Standalone Next.js 14 (App Router) app on port 3000. Fixed sidebar (260px) + tab bar + chat panel. Redux Toolkit manages all state. HTTP POST sends messages; LiveKit DataChannel receives agent responses. No new backend endpoints required.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, Chakra UI v2, Redux Toolkit, livekit-client, axios, react-markdown, react-syntax-highlighter

---

## File Map

```
neuro_web/
├── package.json
├── next.config.js
├── tailwind.config.ts
├── tsconfig.json
├── app/
│   ├── layout.tsx            # Root: Redux + Chakra providers, font, metadata
│   ├── page.tsx              # Main workspace: sidebar + main panel wired together
│   └── globals.css           # Tailwind directives + CSS variables
├── types/
│   └── index.ts              # All shared TS types (Project, Agent, Message, Tab, etc.)
├── theme/
│   └── index.ts              # Chakra extendTheme with NeuroColors
├── store/
│   ├── index.ts              # configureStore
│   ├── projectSlice.ts       # projects[], selectedProjectId, CRUD thunks
│   ├── conversationSlice.ts  # conversations[], openTabs, tabMessages, CRUD thunks
│   ├── agentSlice.ts         # selectedAgent, availableAgents, agentFilter
│   ├── chatSlice.ts          # isLoading, inputText
│   └── uiSlice.ts            # sidebarOpen, sidebarWidth, showProjectCreate
├── services/
│   ├── api.ts                # Axios instance, all API call functions
│   ├── livekit.ts            # LiveKit room connect/disconnect/DataChannel listener
│   └── voice.ts              # MediaRecorder, TTS calls
├── hooks/
│   ├── useProjects.ts        # fetchProjects, createProject, deleteProject
│   ├── useConversations.ts   # fetchConversations, createConversation, deleteConversation
│   ├── useChat.ts            # sendMessage, subscribe to LiveKit responses
│   └── useLiveKit.ts         # room lifecycle, reconnection
├── components/
│   ├── layout/
│   │   ├── Sidebar.tsx       # Projects section + agent filter + conversations list
│   │   ├── TopBar.tsx        # Logo, agent dropdown, voice toggles, connection status
│   │   └── TabBar.tsx        # Open tabs with × buttons, + new tab
│   ├── chat/
│   │   ├── ChatPanel.tsx     # Message list with auto-scroll
│   │   ├── MessageBubble.tsx # Single message: text/markdown/code, user vs agent
│   │   ├── ChatInput.tsx     # Text input + voice + send button
│   │   └── VoicePlayer.tsx   # Audio playback for voice messages
│   ├── project/
│   │   ├── ProjectList.tsx   # Project items with color dot, name, count
│   │   ├── ProjectCreate.tsx # Create project modal
│   │   └── ProjectMenu.tsx   # Right-click context menu: rename/delete
│   ├── agent/
│   │   ├── AgentDropdown.tsx # Agent selector dropdown (Neuro, OpenClaw, etc.)
│   │   └── AgentBadge.tsx    # Small agent icon + name chip
│   └── common/
│       ├── MarkdownRenderer.tsx  # react-markdown + syntax highlighting
│       └── LoadingIndicator.tsx  # Three animated dots
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `neuro_web/package.json`
- Create: `neuro_web/next.config.js`
- Create: `neuro_web/tailwind.config.ts`
- Create: `neuro_web/tsconfig.json`

- [ ] **Step 1: Create neuro_web/ directory and package.json**

```bash
mkdir -p neuro_web && cd neuro_web
```

Create `neuro_web/package.json`:
```json
{
  "name": "neuro-web",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000"
  },
  "dependencies": {
    "@chakra-ui/react": "^2.8.2",
    "@emotion/react": "^11.11.4",
    "@emotion/styled": "^11.11.5",
    "@reduxjs/toolkit": "^2.2.3",
    "axios": "^1.6.8",
    "framer-motion": "^11.1.7",
    "livekit-client": "^2.5.7",
    "next": "14.2.3",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.1",
    "react-redux": "^9.1.1",
    "react-syntax-highlighter": "^15.5.0",
    "rehype-raw": "^7.0.0",
    "remark-gfm": "^4.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.12.7",
    "@types/react": "^18.3.1",
    "@types/react-dom": "^18.3.0",
    "@types/react-syntax-highlighter": "^15.5.13",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.3",
    "typescript": "^5.4.5"
  }
}
```

- [ ] **Step 2: Create next.config.js**

Create `neuro_web/next.config.js`:
```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false, // false to avoid double-mounting LiveKit connections
};
module.exports = nextConfig;
```

- [ ] **Step 3: Create tailwind.config.ts**

Create `neuro_web/tailwind.config.ts`:
```ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './hooks/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        'bg-deep': '#060612',
        'bg-base': '#0a0a1a',
        'bg-surface': '#0f0f20',
        'bg-elevated': '#1a1a2e',
        primary: '#8B5CF6',
        'text-primary': '#e0e0e0',
        'text-secondary': '#888888',
        'text-muted': '#555555',
        success: '#4ade80',
        warning: '#f59e0b',
        error: '#ef4444',
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 4: Create tsconfig.json**

Create `neuro_web/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 5: Create postcss.config.js**

Create `neuro_web/postcss.config.js`:
```js
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 6: Install dependencies**

```bash
cd /home/ubuntu/neurocomputer/neuro_web && npm install
```

Expected: node_modules/ created, no peer-dep errors.

- [ ] **Step 7: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/package.json neuro_web/package-lock.json neuro_web/next.config.js neuro_web/tailwind.config.ts neuro_web/tsconfig.json neuro_web/postcss.config.js
git commit -m "feat(neuro_web): scaffold Next.js app with deps"
```

---

## Task 2: TypeScript Types + Chakra Theme

**Files:**
- Create: `neuro_web/types/index.ts`
- Create: `neuro_web/theme/index.ts`

- [ ] **Step 1: Create types/index.ts**

Create `neuro_web/types/index.ts`:
```ts
export interface Project {
  id: string | null;
  name: string;
  description: string;
  color: string;
  updatedAt: string;
  conversationCount: number;
  sessionState: { openTabs: string[]; activeTab: string | null };
  agents: string[];
}

export enum AgentType {
  ALL = 'all',
  NEURO = 'neuro',
  OPENCLAW = 'openclaw',
  OPENCODE = 'opencode',
  NEUROUPWORK = 'neuroupwork',
}

export interface AgentInfo {
  type: AgentType;
  name: string;
  description: string;
  emoji: string;
}

export interface Message {
  id: string;
  text: string;
  isUser: boolean;
  isVoice: boolean;
  audioUrl?: string;
  timestamp?: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  lastMessage: string;
  updatedAt: string;
  agentId?: string;
  projectId?: string | null;
}

export interface Tab {
  cid: string;
  title: string;
  agentId: string;
  isActive: boolean;
}

export const AGENT_LIST: AgentInfo[] = [
  { type: AgentType.ALL, name: 'All Agents', description: 'Show all', emoji: '🌐' },
  { type: AgentType.NEURO, name: 'Neuro', description: 'General AI assistant', emoji: '🤖' },
  { type: AgentType.OPENCLAW, name: 'OpenClaw', description: 'Web automation & scraping', emoji: '🦀' },
  { type: AgentType.OPENCODE, name: 'OpenCode', description: 'Code assistant', emoji: '💻' },
  { type: AgentType.NEUROUPWORK, name: 'NeuroUpwork', description: 'Upwork automation', emoji: '💼' },
];
```

- [ ] **Step 2: Create theme/index.ts**

Create `neuro_web/theme/index.ts`:
```ts
import { extendTheme } from '@chakra-ui/react';

export const theme = extendTheme({
  config: {
    initialColorMode: 'dark',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      50: '#ede9fe',
      100: '#ddd6fe',
      200: '#c4b5fd',
      300: '#a78bfa',
      400: '#8B5CF6',
      500: '#7c3aed',
      600: '#6d28d9',
      700: '#5b21b6',
      800: '#4c1d95',
      900: '#2e1065',
    },
    bg: {
      deep: '#060612',
      base: '#0a0a1a',
      surface: '#0f0f20',
      elevated: '#1a1a2e',
    },
    textColor: {
      primary: '#e0e0e0',
      secondary: '#888888',
      muted: '#555555',
    },
  },
  styles: {
    global: {
      body: {
        bg: '#0a0a1a',
        color: '#e0e0e0',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
      },
      '*': { boxSizing: 'border-box' },
      '::-webkit-scrollbar': { width: '4px' },
      '::-webkit-scrollbar-track': { background: 'transparent' },
      '::-webkit-scrollbar-thumb': { background: '#333355', borderRadius: '4px' },
    },
  },
  components: {
    Button: {
      defaultProps: { colorScheme: 'brand' },
    },
  },
});
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/types/index.ts neuro_web/theme/index.ts
git commit -m "feat(neuro_web): add TS types and Chakra theme"
```

---

## Task 3: Redux Store

**Files:**
- Create: `neuro_web/store/projectSlice.ts`
- Create: `neuro_web/store/conversationSlice.ts`
- Create: `neuro_web/store/agentSlice.ts`
- Create: `neuro_web/store/chatSlice.ts`
- Create: `neuro_web/store/uiSlice.ts`
- Create: `neuro_web/store/index.ts`

- [ ] **Step 1: Create projectSlice.ts**

Create `neuro_web/store/projectSlice.ts`:
```ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Project } from '@/types';
import { apiGetProjects, apiCreateProject, apiUpdateProject, apiDeleteProject } from '@/services/api';

interface ProjectState {
  projects: Project[];
  selectedProjectId: string | null;
  loading: boolean;
}

const STORAGE_KEY = 'neuro_selected_project';

const initialState: ProjectState = {
  projects: [],
  selectedProjectId: typeof window !== 'undefined' ? localStorage.getItem(STORAGE_KEY) : null,
  loading: false,
};

export const fetchProjects = createAsyncThunk('projects/fetch', async () => {
  return await apiGetProjects();
});

export const createProject = createAsyncThunk(
  'projects/create',
  async (data: { name: string; color: string; description?: string }) => {
    return await apiCreateProject(data);
  }
);

export const updateProject = createAsyncThunk(
  'projects/update',
  async ({ id, data }: { id: string; data: Partial<Project> }) => {
    return await apiUpdateProject(id, data);
  }
);

export const deleteProject = createAsyncThunk('projects/delete', async (id: string) => {
  await apiDeleteProject(id);
  return id;
});

const projectSlice = createSlice({
  name: 'projects',
  initialState,
  reducers: {
    setSelectedProject(state, action: PayloadAction<string | null>) {
      state.selectedProjectId = action.payload;
      if (typeof window !== 'undefined') {
        if (action.payload) localStorage.setItem(STORAGE_KEY, action.payload);
        else localStorage.removeItem(STORAGE_KEY);
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchProjects.pending, (state) => { state.loading = true; })
      .addCase(fetchProjects.fulfilled, (state, action) => {
        state.loading = false;
        state.projects = action.payload;
      })
      .addCase(fetchProjects.rejected, (state) => { state.loading = false; })
      .addCase(createProject.fulfilled, (state, action) => {
        state.projects.push(action.payload);
      })
      .addCase(updateProject.fulfilled, (state, action) => {
        const idx = state.projects.findIndex(p => p.id === action.payload.id);
        if (idx >= 0) state.projects[idx] = action.payload;
      })
      .addCase(deleteProject.fulfilled, (state, action) => {
        state.projects = state.projects.filter(p => p.id !== action.payload);
        if (state.selectedProjectId === action.payload) state.selectedProjectId = null;
      });
  },
});

export const { setSelectedProject } = projectSlice.actions;
export default projectSlice.reducer;
```

- [ ] **Step 2: Create conversationSlice.ts**

Create `neuro_web/store/conversationSlice.ts`:
```ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ConversationSummary, Message, Tab } from '@/types';
import {
  apiGetConversations, apiCreateConversation, apiGetConversation,
  apiDeleteConversation, apiRenameConversation, apiMoveConversation,
} from '@/services/api';

interface ConversationState {
  conversations: ConversationSummary[];
  openTabs: Tab[];
  activeTabCid: string | null;
  tabMessages: Record<string, Message[]>;
  loading: boolean;
}

const initialState: ConversationState = {
  conversations: [],
  openTabs: [],
  activeTabCid: null,
  tabMessages: {},
  loading: false,
};

export const fetchConversations = createAsyncThunk(
  'conversations/fetch',
  async (projectId: string | null) => {
    return await apiGetConversations(projectId);
  }
);

export const createConversation = createAsyncThunk(
  'conversations/create',
  async (data: { title?: string; agentId?: string; projectId?: string | null }) => {
    return await apiCreateConversation(data);
  }
);

export const loadMessages = createAsyncThunk(
  'conversations/loadMessages',
  async (cid: string) => {
    const conv = await apiGetConversation(cid);
    return { cid, messages: conv.messages as Message[] };
  }
);

export const deleteConversation = createAsyncThunk(
  'conversations/delete',
  async (cid: string) => {
    await apiDeleteConversation(cid);
    return cid;
  }
);

export const renameConversation = createAsyncThunk(
  'conversations/rename',
  async ({ cid, title }: { cid: string; title: string }) => {
    return await apiRenameConversation(cid, title);
  }
);

export const moveConversation = createAsyncThunk(
  'conversations/move',
  async ({ cid, projectId }: { cid: string; projectId: string | null }) => {
    return await apiMoveConversation(cid, projectId);
  }
);

const conversationSlice = createSlice({
  name: 'conversations',
  initialState,
  reducers: {
    openTab(state, action: PayloadAction<Tab>) {
      const exists = state.openTabs.find(t => t.cid === action.payload.cid);
      if (!exists) state.openTabs.push(action.payload);
      state.activeTabCid = action.payload.cid;
    },
    closeTab(state, action: PayloadAction<string>) {
      state.openTabs = state.openTabs.filter(t => t.cid !== action.payload);
      if (state.activeTabCid === action.payload) {
        state.activeTabCid = state.openTabs.length > 0
          ? state.openTabs[state.openTabs.length - 1].cid
          : null;
      }
    },
    setActiveTab(state, action: PayloadAction<string>) {
      state.activeTabCid = action.payload;
    },
    appendMessage(state, action: PayloadAction<{ cid: string; message: Message }>) {
      const { cid, message } = action.payload;
      if (!state.tabMessages[cid]) state.tabMessages[cid] = [];
      // Avoid exact duplicates (same id)
      if (!state.tabMessages[cid].find(m => m.id === message.id)) {
        state.tabMessages[cid].push(message);
      }
    },
    replaceTabCid(state, action: PayloadAction<{ oldCid: string; newCid: string; title: string }>) {
      const { oldCid, newCid, title } = action.payload;
      const tab = state.openTabs.find(t => t.cid === oldCid);
      if (tab) { tab.cid = newCid; tab.title = title; }
      if (state.activeTabCid === oldCid) state.activeTabCid = newCid;
      if (state.tabMessages[oldCid]) {
        state.tabMessages[newCid] = state.tabMessages[oldCid];
        delete state.tabMessages[oldCid];
      }
    },
    clearTabMessages(state, action: PayloadAction<string>) {
      delete state.tabMessages[action.payload];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConversations.pending, (state) => { state.loading = true; })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.loading = false;
        state.conversations = action.payload;
      })
      .addCase(fetchConversations.rejected, (state) => { state.loading = false; })
      .addCase(createConversation.fulfilled, (state, action) => {
        state.conversations.unshift(action.payload);
      })
      .addCase(loadMessages.fulfilled, (state, action) => {
        state.tabMessages[action.payload.cid] = action.payload.messages;
      })
      .addCase(deleteConversation.fulfilled, (state, action) => {
        state.conversations = state.conversations.filter(c => c.id !== action.payload);
        state.openTabs = state.openTabs.filter(t => t.cid !== action.payload);
        if (state.activeTabCid === action.payload) {
          state.activeTabCid = state.openTabs.length > 0
            ? state.openTabs[state.openTabs.length - 1].cid
            : null;
        }
      })
      .addCase(renameConversation.fulfilled, (state, action) => {
        const c = state.conversations.find(c => c.id === action.payload.id);
        if (c) c.title = action.payload.title;
        const t = state.openTabs.find(t => t.cid === action.payload.id);
        if (t) t.title = action.payload.title;
      });
  },
});

export const {
  openTab, closeTab, setActiveTab, appendMessage,
  replaceTabCid, clearTabMessages,
} = conversationSlice.actions;
export default conversationSlice.reducer;
```

- [ ] **Step 3: Create agentSlice.ts**

Create `neuro_web/store/agentSlice.ts`:
```ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { AgentInfo, AgentType, AGENT_LIST } from '@/types';

interface AgentState {
  selectedAgent: AgentInfo;
  agentFilter: AgentType;
}

const initialState: AgentState = {
  selectedAgent: AGENT_LIST.find(a => a.type === AgentType.NEURO)!,
  agentFilter: AgentType.ALL,
};

const agentSlice = createSlice({
  name: 'agent',
  initialState,
  reducers: {
    setSelectedAgent(state, action: PayloadAction<AgentInfo>) {
      state.selectedAgent = action.payload;
    },
    setAgentFilter(state, action: PayloadAction<AgentType>) {
      state.agentFilter = action.payload;
    },
  },
});

export const { setSelectedAgent, setAgentFilter } = agentSlice.actions;
export default agentSlice.reducer;
```

- [ ] **Step 4: Create chatSlice.ts**

Create `neuro_web/store/chatSlice.ts`:
```ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ChatState {
  isLoading: boolean;
  inputText: string;
}

const initialState: ChatState = {
  isLoading: false,
  inputText: '',
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    setInputText(state, action: PayloadAction<string>) {
      state.inputText = action.payload;
    },
  },
});

export const { setLoading, setInputText } = chatSlice.actions;
export default chatSlice.reducer;
```

- [ ] **Step 5: Create uiSlice.ts**

Create `neuro_web/store/uiSlice.ts`:
```ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface UIState {
  sidebarOpen: boolean;
  sidebarWidth: number;
  showProjectCreate: boolean;
  showAgentDropdown: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
}

const initialState: UIState = {
  sidebarOpen: true,
  sidebarWidth: 260,
  showProjectCreate: false,
  showAgentDropdown: false,
  connectionStatus: 'disconnected',
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setSidebarOpen(state, action: PayloadAction<boolean>) {
      state.sidebarOpen = action.payload;
    },
    setSidebarWidth(state, action: PayloadAction<number>) {
      state.sidebarWidth = Math.max(180, Math.min(400, action.payload));
    },
    setShowProjectCreate(state, action: PayloadAction<boolean>) {
      state.showProjectCreate = action.payload;
    },
    setShowAgentDropdown(state, action: PayloadAction<boolean>) {
      state.showAgentDropdown = action.payload;
    },
    setConnectionStatus(state, action: PayloadAction<UIState['connectionStatus']>) {
      state.connectionStatus = action.payload;
    },
  },
});

export const {
  setSidebarOpen, setSidebarWidth, setShowProjectCreate,
  setShowAgentDropdown, setConnectionStatus,
} = uiSlice.actions;
export default uiSlice.reducer;
```

- [ ] **Step 6: Create store/index.ts**

Create `neuro_web/store/index.ts`:
```ts
import { configureStore } from '@reduxjs/toolkit';
import projectReducer from './projectSlice';
import conversationReducer from './conversationSlice';
import agentReducer from './agentSlice';
import chatReducer from './chatSlice';
import uiReducer from './uiSlice';

export const store = configureStore({
  reducer: {
    projects: projectReducer,
    conversations: conversationReducer,
    agent: agentReducer,
    chat: chatReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

- [ ] **Step 7: Create store/hooks.ts (typed Redux hooks)**

Create `neuro_web/store/hooks.ts`:
```ts
import { useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from './index';

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector = <T>(selector: (state: RootState) => T) =>
  useSelector(selector);
```

- [ ] **Step 8: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/store/
git commit -m "feat(neuro_web): add Redux store slices"
```

---

## Task 4: API Service

**Files:**
- Create: `neuro_web/services/api.ts`

- [ ] **Step 1: Create services/api.ts**

Create `neuro_web/services/api.ts`:
```ts
import axios from 'axios';
import { Project, ConversationSummary, Message } from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7000';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
});

// ---- Projects ----

export async function apiGetProjects(): Promise<Project[]> {
  const res = await api.get('/projects');
  return res.data;
}

export async function apiCreateProject(data: {
  name: string;
  color: string;
  description?: string;
}): Promise<Project> {
  const res = await api.post('/projects', data);
  return res.data;
}

export async function apiUpdateProject(id: string, data: Partial<Project>): Promise<Project> {
  const res = await api.patch(`/projects/${id}`, data);
  return res.data;
}

export async function apiDeleteProject(id: string): Promise<void> {
  await api.delete(`/projects/${id}`);
}

// ---- Conversations ----

export async function apiGetConversations(
  projectId: string | null
): Promise<ConversationSummary[]> {
  const params = projectId ? { project_id: projectId } : {};
  const res = await api.get('/conversations', { params });
  return res.data;
}

export async function apiCreateConversation(data: {
  title?: string;
  agentId?: string;
  projectId?: string | null;
}): Promise<ConversationSummary> {
  const payload: Record<string, unknown> = {};
  if (data.title) payload.title = data.title;
  if (data.agentId) payload.agent_id = data.agentId;
  if (data.projectId) payload.project_id = data.projectId;
  const res = await api.post('/conversation', payload);
  return res.data;
}

export async function apiGetConversation(cid: string): Promise<{
  id: string;
  title: string;
  messages: Message[];
}> {
  const res = await api.get(`/conversation/${cid}`);
  return res.data;
}

export async function apiDeleteConversation(cid: string): Promise<void> {
  await api.delete(`/conversation/${cid}`);
}

export async function apiRenameConversation(
  cid: string,
  title: string
): Promise<ConversationSummary> {
  const res = await api.patch(`/conversation/${cid}`, { title });
  return res.data;
}

export async function apiMoveConversation(
  cid: string,
  projectId: string | null
): Promise<ConversationSummary> {
  const res = await api.patch(`/conversation/${cid}/project`, { project_id: projectId });
  return res.data;
}

// ---- Chat ----

export async function apiSendMessage(data: {
  cid: string;
  message: string;
  agentId: string;
}): Promise<void> {
  await api.post('/chat/send', {
    conversation_id: data.cid,
    message: data.message,
    agent_id: data.agentId,
  });
}

export async function apiGetChatToken(cid: string): Promise<{
  token: string;
  url: string;
  room_name: string;
}> {
  const res = await api.post('/chat/token', { conversation_id: cid });
  return res.data;
}

// ---- Agents ----

export async function apiGetAgentTypes(): Promise<string[]> {
  const res = await api.get('/agents/types');
  return res.data;
}
```

- [ ] **Step 2: Create .env.local**

Create `neuro_web/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:7000
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/services/api.ts neuro_web/.env.local
git commit -m "feat(neuro_web): add API service layer"
```

---

## Task 5: LiveKit Service

**Files:**
- Create: `neuro_web/services/livekit.ts`

- [ ] **Step 1: Create services/livekit.ts**

Create `neuro_web/services/livekit.ts`:
```ts
import {
  Room, RoomEvent, DataPacket_Kind, RemoteParticipant,
  ConnectionState, RoomOptions,
} from 'livekit-client';
import { apiGetChatToken } from './api';

export type DataMessageHandler = (text: string, topic: string) => void;

class LiveKitService {
  private room: Room | null = null;
  private currentCid: string | null = null;
  private messageHandler: DataMessageHandler | null = null;
  private stateHandler: ((state: ConnectionState) => void) | null = null;

  onMessage(handler: DataMessageHandler) {
    this.messageHandler = handler;
  }

  onStateChange(handler: (state: ConnectionState) => void) {
    this.stateHandler = handler;
  }

  async connect(cid: string): Promise<void> {
    if (this.currentCid === cid && this.room?.state === ConnectionState.Connected) return;

    await this.disconnect();
    this.currentCid = cid;

    const { token, url } = await apiGetChatToken(cid);

    const options: RoomOptions = {
      adaptiveStream: false,
      dynacast: false,
    };

    this.room = new Room(options);

    this.room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      this.stateHandler?.(state);
    });

    this.room.on(
      RoomEvent.DataReceived,
      (payload: Uint8Array, participant?: RemoteParticipant, _kind?: DataPacket_Kind, topic?: string) => {
        try {
          const text = new TextDecoder().decode(payload);
          this.messageHandler?.(text, topic ?? 'agent_response');
        } catch (e) {
          console.error('Failed to decode DataChannel message', e);
        }
      }
    );

    await this.room.connect(url, token);
  }

  async disconnect(): Promise<void> {
    if (this.room) {
      await this.room.disconnect();
      this.room = null;
    }
    this.currentCid = null;
  }

  getState(): ConnectionState {
    return this.room?.state ?? ConnectionState.Disconnected;
  }
}

// Singleton — one LiveKit room at a time
export const livekitService = new LiveKitService();
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/services/livekit.ts
git commit -m "feat(neuro_web): add LiveKit service singleton"
```

---

## Task 6: Custom Hooks

**Files:**
- Create: `neuro_web/hooks/useLiveKit.ts`
- Create: `neuro_web/hooks/useChat.ts`
- Create: `neuro_web/hooks/useProjects.ts`
- Create: `neuro_web/hooks/useConversations.ts`

- [ ] **Step 1: Create hooks/useLiveKit.ts**

Create `neuro_web/hooks/useLiveKit.ts`:
```ts
import { useEffect, useCallback } from 'react';
import { ConnectionState } from 'livekit-client';
import { livekitService } from '@/services/livekit';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setConnectionStatus } from '@/store/uiSlice';
import { appendMessage } from '@/store/conversationSlice';
import { setLoading } from '@/store/chatSlice';
import { Message } from '@/types';

export function useLiveKit() {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);

  const handleData = useCallback((text: string, topic: string) => {
    if (!activeTabCid) return;

    if (topic === 'agent_response' || topic === 'chat_message') {
      const message: Message = {
        id: `agent-${Date.now()}-${Math.random()}`,
        text,
        isUser: false,
        isVoice: false,
        timestamp: new Date().toISOString(),
      };
      dispatch(appendMessage({ cid: activeTabCid, message }));
      dispatch(setLoading(false));
    }
  }, [activeTabCid, dispatch]);

  const handleStateChange = useCallback((state: ConnectionState) => {
    if (state === ConnectionState.Connected) dispatch(setConnectionStatus('connected'));
    else if (state === ConnectionState.Connecting || state === ConnectionState.Reconnecting)
      dispatch(setConnectionStatus('connecting'));
    else dispatch(setConnectionStatus('disconnected'));
  }, [dispatch]);

  useEffect(() => {
    livekitService.onMessage(handleData);
    livekitService.onStateChange(handleStateChange);
  }, [handleData, handleStateChange]);

  const connectToConversation = useCallback(async (cid: string) => {
    dispatch(setConnectionStatus('connecting'));
    try {
      await livekitService.connect(cid);
    } catch (e) {
      console.error('LiveKit connect error', e);
      dispatch(setConnectionStatus('disconnected'));
    }
  }, [dispatch]);

  return { connectToConversation };
}
```

- [ ] **Step 2: Create hooks/useChat.ts**

Create `neuro_web/hooks/useChat.ts`:
```ts
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { appendMessage } from '@/store/conversationSlice';
import { setLoading, setInputText } from '@/store/chatSlice';
import { apiSendMessage } from '@/services/api';
import { Message } from '@/types';

export function useChat() {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const selectedAgent = useAppSelector(s => s.agent.selectedAgent);
  const inputText = useAppSelector(s => s.chat.inputText);
  const isLoading = useAppSelector(s => s.chat.isLoading);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || !activeTabCid) return;

    // Optimistic user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      text: text.trim(),
      isUser: true,
      isVoice: false,
      timestamp: new Date().toISOString(),
    };
    dispatch(appendMessage({ cid: activeTabCid, message: userMsg }));
    dispatch(setInputText(''));
    dispatch(setLoading(true));

    try {
      await apiSendMessage({
        cid: activeTabCid,
        message: text.trim(),
        agentId: selectedAgent.type,
      });
    } catch (e) {
      console.error('Failed to send message', e);
      dispatch(setLoading(false));
    }
    // Response arrives via LiveKit DataChannel → useLiveKit sets loading=false
  }, [activeTabCid, selectedAgent, dispatch]);

  return { sendMessage, inputText, isLoading };
}
```

- [ ] **Step 3: Create hooks/useProjects.ts**

Create `neuro_web/hooks/useProjects.ts`:
```ts
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchProjects, createProject, deleteProject, setSelectedProject,
} from '@/store/projectSlice';

export function useProjects() {
  const dispatch = useAppDispatch();
  const projects = useAppSelector(s => s.projects.projects);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const loading = useAppSelector(s => s.projects.loading);

  const refresh = useCallback(() => dispatch(fetchProjects()), [dispatch]);

  const create = useCallback(
    (name: string, color: string, description?: string) =>
      dispatch(createProject({ name, color, description })),
    [dispatch]
  );

  const remove = useCallback(
    (id: string) => dispatch(deleteProject(id)),
    [dispatch]
  );

  const select = useCallback(
    (id: string | null) => dispatch(setSelectedProject(id)),
    [dispatch]
  );

  return { projects, selectedProjectId, loading, refresh, create, remove, select };
}
```

- [ ] **Step 4: Create hooks/useConversations.ts**

Create `neuro_web/hooks/useConversations.ts`:
```ts
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchConversations, createConversation, deleteConversation,
  renameConversation, openTab, closeTab, setActiveTab,
  loadMessages,
} from '@/store/conversationSlice';
import { Tab } from '@/types';

export function useConversations() {
  const dispatch = useAppDispatch();
  const conversations = useAppSelector(s => s.conversations.conversations);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const tabMessages = useAppSelector(s => s.conversations.tabMessages);
  const loading = useAppSelector(s => s.conversations.loading);

  const refresh = useCallback(
    (projectId: string | null) => dispatch(fetchConversations(projectId)),
    [dispatch]
  );

  const create = useCallback(
    (agentId: string, projectId: string | null, title?: string) =>
      dispatch(createConversation({ title, agentId, projectId })),
    [dispatch]
  );

  const remove = useCallback(
    (cid: string) => dispatch(deleteConversation(cid)),
    [dispatch]
  );

  const rename = useCallback(
    (cid: string, title: string) => dispatch(renameConversation({ cid, title })),
    [dispatch]
  );

  const openConversation = useCallback(
    async (tab: Tab) => {
      dispatch(openTab(tab));
      if (!tabMessages[tab.cid] || tabMessages[tab.cid].length === 0) {
        await dispatch(loadMessages(tab.cid));
      }
    },
    [dispatch, tabMessages]
  );

  const switchTab = useCallback(
    (cid: string) => dispatch(setActiveTab(cid)),
    [dispatch]
  );

  const closeTabById = useCallback(
    (cid: string) => dispatch(closeTab(cid)),
    [dispatch]
  );

  return {
    conversations, openTabs, activeTabCid, tabMessages, loading,
    refresh, create, remove, rename, openConversation, switchTab, closeTabById,
  };
}
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/hooks/
git commit -m "feat(neuro_web): add custom hooks (livekit, chat, projects, conversations)"
```

---

## Task 7: Common Components

**Files:**
- Create: `neuro_web/components/common/MarkdownRenderer.tsx`
- Create: `neuro_web/components/common/LoadingIndicator.tsx`

- [ ] **Step 1: Create MarkdownRenderer.tsx**

Create `neuro_web/components/common/MarkdownRenderer.tsx`:
```tsx
'use client';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface Props {
  content: string;
}

export default function MarkdownRenderer({ content }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ inline, className, children, ...props }: {
          inline?: boolean;
          className?: string;
          children?: React.ReactNode;
        }) {
          const match = /language-(\w+)/.exec(className || '');
          if (!inline && match) {
            return (
              <SyntaxHighlighter
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                customStyle={{
                  borderRadius: '6px',
                  fontSize: '12px',
                  margin: '8px 0',
                  background: '#060612',
                  border: '1px solid rgba(255,255,255,0.08)',
                }}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            );
          }
          return (
            <code
              style={{
                background: '#060612',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '12px',
                color: '#c4b5fd',
              }}
              {...props}
            >
              {children}
            </code>
          );
        },
        p({ children }) {
          return <p style={{ margin: '4px 0', lineHeight: 1.6 }}>{children}</p>;
        },
        ul({ children }) {
          return <ul style={{ paddingLeft: '20px', margin: '4px 0' }}>{children}</ul>;
        },
        ol({ children }) {
          return <ol style={{ paddingLeft: '20px', margin: '4px 0' }}>{children}</ol>;
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
```

- [ ] **Step 2: Create LoadingIndicator.tsx**

Create `neuro_web/components/common/LoadingIndicator.tsx`:
```tsx
'use client';

export default function LoadingIndicator() {
  return (
    <div style={{ display: 'flex', gap: '4px', alignItems: 'center', padding: '4px 0' }}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: '#8B5CF6',
            animation: 'pulse 1.4s ease-in-out infinite',
            animationDelay: `${i * 0.2}s`,
            opacity: 0.8,
          }}
        />
      ))}
      <style jsx>{`
        @keyframes pulse {
          0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/components/common/
git commit -m "feat(neuro_web): add MarkdownRenderer and LoadingIndicator"
```

---

## Task 8: Chat Components

**Files:**
- Create: `neuro_web/components/chat/MessageBubble.tsx`
- Create: `neuro_web/components/chat/ChatPanel.tsx`
- Create: `neuro_web/components/chat/ChatInput.tsx`
- Create: `neuro_web/components/chat/VoicePlayer.tsx`

- [ ] **Step 1: Create MessageBubble.tsx**

Create `neuro_web/components/chat/MessageBubble.tsx`:
```tsx
'use client';
import { Message } from '@/types';
import MarkdownRenderer from '@/components/common/MarkdownRenderer';

interface Props {
  message: Message;
  agentEmoji?: string;
  agentName?: string;
}

function formatTime(ts?: string): string {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function MessageBubble({ message, agentEmoji = '🤖', agentName = 'Neuro' }: Props) {
  if (message.isUser) {
    return (
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '16px' }}>
        <div style={{ maxWidth: '75%' }}>
          <div style={{ fontSize: '10px', color: '#555', marginBottom: '4px', textAlign: 'right' }}>
            You{message.timestamp ? ` · ${formatTime(message.timestamp)}` : ''}
          </div>
          <div
            style={{
              background: 'rgba(139, 92, 246, 0.15)',
              borderRadius: '12px 4px 12px 12px',
              padding: '10px 14px',
              fontSize: '13px',
              color: '#ddd',
              lineHeight: 1.5,
            }}
          >
            {message.text}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', gap: '10px', marginBottom: '16px', maxWidth: '80%' }}>
      <div
        style={{
          width: '28px',
          height: '28px',
          minWidth: '28px',
          background: 'rgba(139, 92, 246, 0.15)',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '12px',
          marginTop: '2px',
        }}
      >
        {agentEmoji}
      </div>
      <div>
        <div style={{ fontSize: '10px', color: '#555', marginBottom: '4px' }}>
          {agentName}{message.timestamp ? ` · ${formatTime(message.timestamp)}` : ''}
        </div>
        <div
          style={{
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '4px 12px 12px 12px',
            padding: '10px 14px',
            fontSize: '13px',
            color: '#ccc',
            lineHeight: 1.5,
          }}
        >
          {message.isVoice && message.audioUrl ? (
            <audio controls src={message.audioUrl} style={{ height: '32px' }} />
          ) : (
            <MarkdownRenderer content={message.text} />
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create ChatPanel.tsx**

Create `neuro_web/components/chat/ChatPanel.tsx`:
```tsx
'use client';
import { useEffect, useRef } from 'react';
import { useAppSelector } from '@/store/hooks';
import { AGENT_LIST } from '@/types';
import MessageBubble from './MessageBubble';
import LoadingIndicator from '@/components/common/LoadingIndicator';

export default function ChatPanel() {
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const tabMessages = useAppSelector(s => s.conversations.tabMessages);
  const isLoading = useAppSelector(s => s.chat.isLoading);
  const selectedAgent = useAppSelector(s => s.agent.selectedAgent);
  const bottomRef = useRef<HTMLDivElement>(null);

  const messages = activeTabCid ? (tabMessages[activeTabCid] ?? []) : [];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length, isLoading]);

  const agentInfo = AGENT_LIST.find(a => a.type === selectedAgent.type) ?? AGENT_LIST[1];

  if (!activeTabCid) {
    return (
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#444',
          fontSize: '14px',
        }}
      >
        Open a conversation or create a new one
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px 32px',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          agentEmoji={agentInfo.emoji}
          agentName={agentInfo.name}
        />
      ))}
      {isLoading && (
        <div style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              minWidth: '28px',
              background: 'rgba(139, 92, 246, 0.15)',
              borderRadius: '50%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              marginTop: '2px',
            }}
          >
            {agentInfo.emoji}
          </div>
          <div
            style={{
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '4px 12px 12px 12px',
              padding: '12px 16px',
            }}
          >
            <LoadingIndicator />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 3: Create ChatInput.tsx**

Create `neuro_web/components/chat/ChatInput.tsx`:
```tsx
'use client';
import { KeyboardEvent, useRef, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setInputText } from '@/store/chatSlice';
import { useChat } from '@/hooks/useChat';

export default function ChatInput() {
  const dispatch = useAppDispatch();
  const { sendMessage, inputText, isLoading } = useChat();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const [isRecording, setIsRecording] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && inputText.trim()) sendMessage(inputText);
    }
  };

  const disabled = !activeTabCid || isLoading;

  return (
    <div style={{ padding: '12px 32px 16px' }}>
      <div
        style={{
          background: '#0a0a1a',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '12px',
          padding: '10px 14px',
          display: 'flex',
          alignItems: 'flex-end',
          gap: '10px',
        }}
      >
        <span style={{ fontSize: '14px', color: '#555', cursor: 'not-allowed', paddingBottom: '2px' }}>📎</span>
        <textarea
          ref={textareaRef}
          value={inputText}
          onChange={(e) => dispatch(setInputText(e.target.value))}
          onKeyDown={handleKeyDown}
          placeholder={activeTabCid ? 'Ask anything...' : 'Open a conversation first'}
          disabled={disabled}
          rows={1}
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#e0e0e0',
            fontSize: '13px',
            resize: 'none',
            fontFamily: 'inherit',
            lineHeight: 1.5,
            maxHeight: '120px',
            overflow: 'auto',
          }}
          onInput={(e) => {
            const el = e.currentTarget;
            el.style.height = 'auto';
            el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingBottom: '2px' }}>
          <span
            onClick={() => setIsRecording(!isRecording)}
            style={{ fontSize: '14px', color: isRecording ? '#8B5CF6' : '#555', cursor: 'pointer' }}
          >
            🎤
          </span>
          <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.1)' }} />
          <button
            onClick={() => sendMessage(inputText)}
            disabled={disabled || !inputText.trim()}
            style={{
              background: disabled || !inputText.trim() ? '#3a2d6b' : '#8B5CF6',
              border: 'none',
              borderRadius: '6px',
              padding: '4px 12px',
              fontSize: '12px',
              color: disabled || !inputText.trim() ? '#888' : '#fff',
              cursor: disabled || !inputText.trim() ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
            }}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create VoicePlayer.tsx**

Create `neuro_web/components/chat/VoicePlayer.tsx`:
```tsx
'use client';

interface Props {
  audioUrl: string;
}

export default function VoicePlayer({ audioUrl }: Props) {
  return (
    <audio
      controls
      src={audioUrl}
      style={{ height: '32px', width: '200px' }}
    />
  );
}
```

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/components/chat/
git commit -m "feat(neuro_web): add chat components (panel, bubbles, input)"
```

---

## Task 9: Agent Components

**Files:**
- Create: `neuro_web/components/agent/AgentBadge.tsx`
- Create: `neuro_web/components/agent/AgentDropdown.tsx`

- [ ] **Step 1: Create AgentBadge.tsx**

Create `neuro_web/components/agent/AgentBadge.tsx`:
```tsx
'use client';
import { AgentInfo } from '@/types';

interface Props {
  agent: AgentInfo;
  size?: 'sm' | 'md';
}

export default function AgentBadge({ agent, size = 'md' }: Props) {
  const fontSize = size === 'sm' ? '10px' : '12px';
  const padding = size === 'sm' ? '2px 8px' : '4px 10px';

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        background: 'rgba(139,92,246,0.12)',
        border: '1px solid rgba(139,92,246,0.2)',
        borderRadius: '12px',
        padding,
        fontSize,
        color: '#a78bfa',
      }}
    >
      <span>{agent.emoji}</span>
      <span>{agent.name}</span>
    </div>
  );
}
```

- [ ] **Step 2: Create AgentDropdown.tsx**

Create `neuro_web/components/agent/AgentDropdown.tsx`:
```tsx
'use client';
import { useRef, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedAgent } from '@/store/agentSlice';
import { setShowAgentDropdown } from '@/store/uiSlice';
import { AgentInfo, AGENT_LIST, AgentType } from '@/types';

export default function AgentDropdown() {
  const dispatch = useAppDispatch();
  const selectedAgent = useAppSelector(s => s.agent.selectedAgent);
  const showDropdown = useAppSelector(s => s.ui.showAgentDropdown);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        dispatch(setShowAgentDropdown(false));
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [dispatch]);

  const options = AGENT_LIST.filter(a => a.type !== AgentType.ALL);

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <div
        onClick={() => dispatch(setShowAgentDropdown(!showDropdown))}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(255,255,255,0.05)',
          padding: '5px 12px',
          borderRadius: '8px',
          cursor: 'pointer',
          userSelect: 'none',
        }}
      >
        <span style={{ fontSize: '14px' }}>{selectedAgent.emoji}</span>
        <span style={{ fontSize: '12px', color: '#e0e0e0' }}>{selectedAgent.name}</span>
        <span style={{ fontSize: '10px', color: '#666' }}>▾</span>
      </div>

      {showDropdown && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            marginTop: '4px',
            background: '#1a1a2e',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '10px',
            minWidth: '180px',
            zIndex: 100,
            overflow: 'hidden',
          }}
        >
          {options.map((agent: AgentInfo) => (
            <div
              key={agent.type}
              onClick={() => {
                dispatch(setSelectedAgent(agent));
                dispatch(setShowAgentDropdown(false));
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '10px 14px',
                cursor: 'pointer',
                fontSize: '13px',
                color: selectedAgent.type === agent.type ? '#8B5CF6' : '#ddd',
                background: selectedAgent.type === agent.type
                  ? 'rgba(139,92,246,0.1)'
                  : 'transparent',
              }}
              onMouseEnter={e => {
                if (selectedAgent.type !== agent.type)
                  (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)';
              }}
              onMouseLeave={e => {
                if (selectedAgent.type !== agent.type)
                  (e.currentTarget as HTMLElement).style.background = 'transparent';
              }}
            >
              <span>{agent.emoji}</span>
              <div>
                <div style={{ fontWeight: 500 }}>{agent.name}</div>
                <div style={{ fontSize: '11px', color: '#666' }}>{agent.description}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/components/agent/
git commit -m "feat(neuro_web): add AgentDropdown and AgentBadge"
```

---

## Task 10: Project Components

**Files:**
- Create: `neuro_web/components/project/ProjectList.tsx`
- Create: `neuro_web/components/project/ProjectCreate.tsx`
- Create: `neuro_web/components/project/ProjectMenu.tsx`

- [ ] **Step 1: Create ProjectList.tsx**

Create `neuro_web/components/project/ProjectList.tsx`:
```tsx
'use client';
import { useState } from 'react';
import { Project } from '@/types';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setSelectedProject } from '@/store/projectSlice';
import { fetchConversations } from '@/store/conversationSlice';
import ProjectMenu from './ProjectMenu';

interface Props {
  projects: Project[];
}

const PROJECT_COLORS = [
  '#8B5CF6', '#f59e0b', '#4ade80', '#ef4444',
  '#3b82f6', '#ec4899', '#14b8a6', '#f97316',
];

export { PROJECT_COLORS };

export default function ProjectList({ projects }: Props) {
  const dispatch = useAppDispatch();
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const [menuProject, setMenuProject] = useState<Project | null>(null);
  const [menuPos, setMenuPos] = useState({ x: 0, y: 0 });

  const handleSelect = (id: string | null) => {
    dispatch(setSelectedProject(id));
    dispatch(fetchConversations(id));
  };

  const handleContextMenu = (e: React.MouseEvent, p: Project) => {
    e.preventDefault();
    setMenuProject(p);
    setMenuPos({ x: e.clientX, y: e.clientY });
  };

  // NoProject pseudo-entry
  const noProject: Project = {
    id: null,
    name: 'NoProject',
    description: '',
    color: '#555555',
    updatedAt: '',
    conversationCount: 0,
    sessionState: { openTabs: [], activeTab: null },
    agents: [],
  };

  const all = [...projects, noProject];

  return (
    <>
      {all.map((p) => {
        const isSelected = selectedProjectId === p.id;
        return (
          <div
            key={p.id ?? 'noproj'}
            onClick={() => handleSelect(p.id)}
            onContextMenu={(e) => p.id && handleContextMenu(e, p)}
            style={{
              padding: '7px 10px',
              background: isSelected ? `${p.color}15` : 'transparent',
              borderRadius: '8px',
              color: isSelected ? p.color : '#777',
              fontSize: '12px',
              marginBottom: '3px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: p.color,
                flexShrink: 0,
              }}
            />
            <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {p.name}
            </span>
            {(p.conversationCount ?? 0) > 0 && (
              <span style={{ fontSize: '10px', color: isSelected ? `${p.color}90` : '#444' }}>
                {p.conversationCount}
              </span>
            )}
          </div>
        );
      })}
      {menuProject && (
        <ProjectMenu
          project={menuProject}
          position={menuPos}
          onClose={() => setMenuProject(null)}
        />
      )}
    </>
  );
}
```

- [ ] **Step 2: Create ProjectMenu.tsx**

Create `neuro_web/components/project/ProjectMenu.tsx`:
```tsx
'use client';
import { useEffect, useRef, useState } from 'react';
import { Project } from '@/types';
import { useAppDispatch } from '@/store/hooks';
import { deleteProject, updateProject } from '@/store/projectSlice';

interface Props {
  project: Project;
  position: { x: number; y: number };
  onClose: () => void;
}

export default function ProjectMenu({ project, position, onClose }: Props) {
  const dispatch = useAppDispatch();
  const ref = useRef<HTMLDivElement>(null);
  const [renaming, setRenaming] = useState(false);
  const [newName, setNewName] = useState(project.name);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, [onClose]);

  const handleRename = () => {
    if (newName.trim() && newName !== project.name && project.id) {
      dispatch(updateProject({ id: project.id, data: { name: newName.trim() } }));
    }
    onClose();
  };

  const handleDelete = () => {
    if (project.id && confirm(`Delete project "${project.name}"?`)) {
      dispatch(deleteProject(project.id));
    }
    onClose();
  };

  return (
    <div
      ref={ref}
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        background: '#1a1a2e',
        border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: '8px',
        zIndex: 200,
        minWidth: '160px',
        overflow: 'hidden',
      }}
    >
      {renaming ? (
        <div style={{ padding: '10px 12px' }}>
          <input
            autoFocus
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleRename(); if (e.key === 'Escape') onClose(); }}
            style={{
              width: '100%',
              background: '#0a0a1a',
              border: '1px solid #8B5CF6',
              borderRadius: '4px',
              padding: '4px 8px',
              color: '#e0e0e0',
              fontSize: '12px',
              outline: 'none',
            }}
          />
        </div>
      ) : (
        <>
          <div
            onClick={() => setRenaming(true)}
            style={{ padding: '9px 14px', fontSize: '12px', color: '#ddd', cursor: 'pointer' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            ✏️ Rename
          </div>
          <div
            onClick={handleDelete}
            style={{ padding: '9px 14px', fontSize: '12px', color: '#ef4444', cursor: 'pointer' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.08)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            🗑️ Delete
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create ProjectCreate.tsx**

Create `neuro_web/components/project/ProjectCreate.tsx`:
```tsx
'use client';
import { useState } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { createProject } from '@/store/projectSlice';
import { setShowProjectCreate } from '@/store/uiSlice';

const PRESET_COLORS = [
  '#8B5CF6', '#f59e0b', '#4ade80', '#ef4444',
  '#3b82f6', '#ec4899', '#14b8a6', '#f97316',
];

export default function ProjectCreate() {
  const dispatch = useAppDispatch();
  const [name, setName] = useState('');
  const [color, setColor] = useState(PRESET_COLORS[0]);

  const handleCreate = () => {
    if (!name.trim()) return;
    dispatch(createProject({ name: name.trim(), color }));
    dispatch(setShowProjectCreate(false));
  };

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 300,
      }}
      onClick={() => dispatch(setShowProjectCreate(false))}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: '#1a1a2e',
          border: '1px solid rgba(255,255,255,0.1)',
          borderRadius: '12px',
          padding: '24px',
          width: '320px',
        }}
      >
        <h3 style={{ color: '#e0e0e0', fontSize: '14px', marginBottom: '16px', fontWeight: 600 }}>
          New Project
        </h3>
        <input
          autoFocus
          value={name}
          onChange={e => setName(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') dispatch(setShowProjectCreate(false)); }}
          placeholder="Project name"
          style={{
            width: '100%',
            background: '#0a0a1a',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '8px',
            padding: '8px 12px',
            color: '#e0e0e0',
            fontSize: '13px',
            outline: 'none',
            marginBottom: '16px',
            boxSizing: 'border-box',
          }}
        />
        <div style={{ marginBottom: '20px' }}>
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '8px' }}>Color</div>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {PRESET_COLORS.map(c => (
              <div
                key={c}
                onClick={() => setColor(c)}
                style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: c,
                  cursor: 'pointer',
                  border: color === c ? '2px solid #fff' : '2px solid transparent',
                }}
              />
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
          <button
            onClick={() => dispatch(setShowProjectCreate(false))}
            style={{
              padding: '7px 16px', fontSize: '12px', borderRadius: '8px',
              background: 'transparent', border: '1px solid rgba(255,255,255,0.1)',
              color: '#888', cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!name.trim()}
            style={{
              padding: '7px 16px', fontSize: '12px', borderRadius: '8px',
              background: name.trim() ? '#8B5CF6' : '#3a2d6b',
              border: 'none', color: name.trim() ? '#fff' : '#888',
              cursor: name.trim() ? 'pointer' : 'not-allowed',
            }}
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/components/project/
git commit -m "feat(neuro_web): add project list, create modal, context menu"
```

---

## Task 11: Layout Components

**Files:**
- Create: `neuro_web/components/layout/TopBar.tsx`
- Create: `neuro_web/components/layout/TabBar.tsx`
- Create: `neuro_web/components/layout/Sidebar.tsx`

- [ ] **Step 1: Create TopBar.tsx**

Create `neuro_web/components/layout/TopBar.tsx`:
```tsx
'use client';
import { useAppSelector } from '@/store/hooks';
import AgentDropdown from '@/components/agent/AgentDropdown';

export default function TopBar() {
  const connectionStatus = useAppSelector(s => s.ui.connectionStatus);

  const statusColor =
    connectionStatus === 'connected' ? '#4ade80' :
    connectionStatus === 'connecting' ? '#f59e0b' : '#ef4444';
  const statusLabel =
    connectionStatus === 'connected' ? 'Connected' :
    connectionStatus === 'connecting' ? 'Connecting...' : 'Disconnected';

  return (
    <div
      style={{
        height: '48px',
        minHeight: '48px',
        background: '#080816',
        display: 'flex',
        alignItems: 'center',
        padding: '0 16px',
        gap: '12px',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
        flexShrink: 0,
      }}
    >
      {/* Logo */}
      <div style={{ fontSize: '18px', fontWeight: 700, color: '#8B5CF6', letterSpacing: '-0.5px', userSelect: 'none' }}>
        N
      </div>
      <div style={{ width: '1px', height: '24px', background: 'rgba(255,255,255,0.06)' }} />

      {/* Agent dropdown */}
      <AgentDropdown />

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Connection status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
        <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: statusColor }} />
        <span style={{ fontSize: '11px', color: statusColor }}>{statusLabel}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create TabBar.tsx**

Create `neuro_web/components/layout/TabBar.tsx`:
```tsx
'use client';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setActiveTab, closeTab } from '@/store/conversationSlice';
import { useLiveKit } from '@/hooks/useLiveKit';
import { loadMessages } from '@/store/conversationSlice';

export default function TabBar({ onNewTab }: { onNewTab: () => void }) {
  const dispatch = useAppDispatch();
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const { connectToConversation } = useLiveKit();

  const handleSwitchTab = async (cid: string) => {
    dispatch(setActiveTab(cid));
    await connectToConversation(cid);
    await dispatch(loadMessages(cid));
  };

  return (
    <div
      style={{
        height: '36px',
        minHeight: '36px',
        display: 'flex',
        alignItems: 'stretch',
        background: '#080816',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        flexShrink: 0,
        overflowX: 'auto',
      }}
    >
      {openTabs.map((tab) => {
        const isActive = tab.cid === activeTabCid;
        return (
          <div
            key={tab.cid}
            style={{
              display: 'flex',
              alignItems: 'center',
              padding: '0 14px',
              fontSize: '12px',
              color: isActive ? '#e0e0e0' : '#666',
              borderBottom: isActive ? '2px solid #8B5CF6' : '2px solid transparent',
              background: isActive ? '#0f0f20' : 'transparent',
              gap: '6px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              userSelect: 'none',
              flexShrink: 0,
            }}
            onClick={() => handleSwitchTab(tab.cid)}
          >
            <span style={{ maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {tab.title}
            </span>
            <span
              onClick={(e) => { e.stopPropagation(); dispatch(closeTab(tab.cid)); }}
              style={{ fontSize: '10px', color: '#555', padding: '0 2px' }}
            >
              ×
            </span>
          </div>
        );
      })}
      <div
        onClick={onNewTab}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px',
          fontSize: '14px',
          color: '#555',
          cursor: 'pointer',
        }}
      >
        +
      </div>
      <div style={{ flex: 1 }} />
    </div>
  );
}
```

- [ ] **Step 3: Create Sidebar.tsx**

Create `neuro_web/components/layout/Sidebar.tsx`:
```tsx
'use client';
import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setAgentFilter } from '@/store/agentSlice';
import { setShowProjectCreate } from '@/store/uiSlice';
import { AgentType, AGENT_LIST, Tab } from '@/types';
import ProjectList from '@/components/project/ProjectList';
import ProjectCreate from '@/components/project/ProjectCreate';
import { useConversations } from '@/hooks/useConversations';
import { useLiveKit } from '@/hooks/useLiveKit';

export default function Sidebar() {
  const dispatch = useAppDispatch();
  const projects = useAppSelector(s => s.projects.projects);
  const showProjectCreate = useAppSelector(s => s.ui.showProjectCreate);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedAgent = useAppSelector(s => s.agent.selectedAgent);
  const { conversations, openConversation } = useConversations();
  const { connectToConversation } = useLiveKit();

  const filterAgents = AGENT_LIST.filter(a => a.type !== AgentType.ALL);

  const filteredConversations = conversations.filter(c => {
    if (agentFilter === AgentType.ALL) return true;
    return c.agentId === agentFilter;
  });

  const handleOpenConversation = async (cid: string, title: string, agentId: string) => {
    const tab: Tab = { cid, title, agentId, isActive: true };
    await openConversation(tab);
    await connectToConversation(cid);
  };

  function relativeTime(ts: string): string {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  }

  return (
    <div
      style={{
        width: '260px',
        minWidth: '260px',
        background: '#0a0a1a',
        display: 'flex',
        flexDirection: 'column',
        borderRight: '1px solid rgba(255,255,255,0.04)',
        overflow: 'hidden',
      }}
    >
      {/* Projects section */}
      <div style={{ padding: '12px 14px 6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '1.5px', color: '#555', fontWeight: 600 }}>
            Projects
          </span>
          <span
            onClick={() => dispatch(setShowProjectCreate(true))}
            style={{ fontSize: '14px', color: '#555', cursor: 'pointer', padding: '0 4px' }}
          >
            +
          </span>
        </div>
        <ProjectList projects={projects} />
      </div>

      <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '6px 14px' }} />

      {/* Agent filter */}
      <div style={{ padding: '8px 14px' }}>
        <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
          <div
            onClick={() => dispatch(setAgentFilter(AgentType.ALL))}
            style={{
              padding: '3px 10px',
              background: agentFilter === AgentType.ALL ? 'rgba(139,92,246,0.2)' : 'rgba(255,255,255,0.03)',
              border: `1px solid ${agentFilter === AgentType.ALL ? 'rgba(139,92,246,0.4)' : 'rgba(255,255,255,0.08)'}`,
              borderRadius: '12px',
              fontSize: '10px',
              color: agentFilter === AgentType.ALL ? '#8B5CF6' : '#888',
              cursor: 'pointer',
              userSelect: 'none',
            }}
          >
            All
          </div>
          {filterAgents.map(a => (
            <div
              key={a.type}
              onClick={() => dispatch(setAgentFilter(a.type))}
              style={{
                padding: '3px 10px',
                background: agentFilter === a.type ? 'rgba(139,92,246,0.2)' : 'rgba(255,255,255,0.03)',
                border: `1px solid ${agentFilter === a.type ? 'rgba(139,92,246,0.4)' : 'rgba(255,255,255,0.08)'}`,
                borderRadius: '12px',
                fontSize: '10px',
                color: agentFilter === a.type ? '#8B5CF6' : '#888',
                cursor: 'pointer',
                userSelect: 'none',
              }}
            >
              {a.name}
            </div>
          ))}
        </div>
      </div>

      <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '2px 14px' }} />

      {/* Conversations */}
      <div style={{ padding: '8px 14px 6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '10px', textTransform: 'uppercase', letterSpacing: '1.5px', color: '#555', fontWeight: 600 }}>
            Conversations
          </span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '0 14px 14px' }}>
        {filteredConversations.length === 0 ? (
          <div style={{ fontSize: '11px', color: '#444', padding: '8px 4px' }}>
            No conversations yet
          </div>
        ) : (
          filteredConversations.map(c => {
            const agent = AGENT_LIST.find(a => a.type === c.agentId) ?? AGENT_LIST[1];
            return (
              <div
                key={c.id}
                onClick={() => handleOpenConversation(c.id, c.title, c.agentId ?? 'neuro')}
                style={{
                  padding: '8px 10px',
                  background: 'rgba(255,255,255,0.03)',
                  borderRadius: '8px',
                  marginBottom: '4px',
                  cursor: 'pointer',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.06)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
              >
                <div style={{ fontSize: '12px', color: '#ddd', marginBottom: '3px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {c.title}
                </div>
                <div style={{ fontSize: '10px', color: '#555', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>{agent.emoji}</span>
                  <span>{agent.name}</span>
                  <span>·</span>
                  <span>{relativeTime(c.updatedAt)}</span>
                </div>
              </div>
            );
          })
        )}
      </div>

      {showProjectCreate && <ProjectCreate />}
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/components/layout/
git commit -m "feat(neuro_web): add TopBar, TabBar, Sidebar layout components"
```

---

## Task 12: App Shell + Main Page

**Files:**
- Create: `neuro_web/app/globals.css`
- Create: `neuro_web/app/layout.tsx`
- Create: `neuro_web/app/page.tsx`

- [ ] **Step 1: Create globals.css**

Create `neuro_web/app/globals.css`:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-deep: #060612;
  --bg-base: #0a0a1a;
  --bg-surface: #0f0f20;
  --bg-elevated: #1a1a2e;
  --primary: #8B5CF6;
  --text-primary: #e0e0e0;
  --text-secondary: #888888;
  --text-muted: #555555;
  --success: #4ade80;
  --warning: #f59e0b;
  --error: #ef4444;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

html, body {
  height: 100%;
  overflow: hidden;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
}

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #333355; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #4a4a7a; }

button { font-family: inherit; }
textarea, input { font-family: inherit; }
```

- [ ] **Step 2: Create app/layout.tsx**

Create `neuro_web/app/layout.tsx`:
```tsx
import type { Metadata } from 'next';
import './globals.css';
import Providers from './providers';

export const metadata: Metadata = {
  title: 'Neuro',
  description: 'Multi-agent AI workspace',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" style={{ height: '100%' }}>
      <body style={{ height: '100%', overflow: 'hidden' }}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Create app/providers.tsx**

Create `neuro_web/app/providers.tsx`:
```tsx
'use client';
import { Provider } from 'react-redux';
import { ChakraProvider, ColorModeScript } from '@chakra-ui/react';
import { store } from '@/store';
import { theme } from '@/theme';

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Provider store={store}>
      <ColorModeScript initialColorMode="dark" />
      <ChakraProvider theme={theme}>
        {children}
      </ChakraProvider>
    </Provider>
  );
}
```

- [ ] **Step 4: Create app/page.tsx**

Create `neuro_web/app/page.tsx`:
```tsx
'use client';
import { useEffect, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { fetchProjects } from '@/store/projectSlice';
import { fetchConversations, createConversation, openTab } from '@/store/conversationSlice';
import { useLiveKit } from '@/hooks/useLiveKit';
import Sidebar from '@/components/layout/Sidebar';
import TopBar from '@/components/layout/TopBar';
import TabBar from '@/components/layout/TabBar';
import ChatPanel from '@/components/chat/ChatPanel';
import ChatInput from '@/components/chat/ChatInput';

export default function Home() {
  const dispatch = useAppDispatch();
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedAgent = useAppSelector(s => s.agent.selectedAgent);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const { connectToConversation } = useLiveKit();

  // Initial load
  useEffect(() => {
    dispatch(fetchProjects());
  }, [dispatch]);

  // Reload conversations when project changes
  useEffect(() => {
    dispatch(fetchConversations(selectedProjectId));
  }, [selectedProjectId, dispatch]);

  // Poll conversations every 10s
  useEffect(() => {
    const interval = setInterval(() => {
      dispatch(fetchConversations(selectedProjectId));
    }, 10000);
    return () => clearInterval(interval);
  }, [selectedProjectId, dispatch]);

  // Connect LiveKit when active tab changes
  useEffect(() => {
    if (activeTabCid) connectToConversation(activeTabCid);
  }, [activeTabCid, connectToConversation]);

  const handleNewTab = useCallback(async () => {
    const result = await dispatch(createConversation({
      agentId: selectedAgent.type,
      projectId: selectedProjectId,
    }));
    if (createConversation.fulfilled.match(result)) {
      const conv = result.payload;
      dispatch(openTab({
        cid: conv.id,
        title: conv.title || 'New Chat',
        agentId: conv.agentId ?? selectedAgent.type,
        isActive: true,
      }));
    }
  }, [dispatch, selectedAgent, selectedProjectId]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <TopBar />
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <Sidebar />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#0f0f20', overflow: 'hidden' }}>
          <TabBar onNewTab={handleNewTab} />
          <ChatPanel />
          <ChatInput />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify build compiles**

```bash
cd /home/ubuntu/neurocomputer/neuro_web && npm run build 2>&1 | tail -30
```

Expected: `✓ Compiled successfully` or `Route (app) Size`. Fix any TS errors before committing.

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/app/
git commit -m "feat(neuro_web): add app shell, providers, main workspace page"
```

---

## Task 13: Voice Service

**Files:**
- Create: `neuro_web/services/voice.ts`

- [ ] **Step 1: Create services/voice.ts**

Create `neuro_web/services/voice.ts`:
```ts
import { api } from './api';

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

export async function startVoiceRecording(): Promise<void> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
  mediaRecorder.start();
}

export async function stopVoiceRecording(): Promise<Blob> {
  return new Promise((resolve) => {
    if (!mediaRecorder) { resolve(new Blob()); return; }
    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      mediaRecorder?.stream.getTracks().forEach(t => t.stop());
      mediaRecorder = null;
      resolve(blob);
    };
    mediaRecorder.stop();
  });
}

export async function generateTTS(text: string): Promise<string> {
  const res = await api.post('/tts', { text }, { responseType: 'blob' });
  return URL.createObjectURL(res.data);
}
```

- [ ] **Step 2: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neuro_web/services/voice.ts
git commit -m "feat(neuro_web): add voice recording and TTS service"
```

---

## Task 14: Final Verification

- [ ] **Step 1: Start dev server**

```bash
cd /home/ubuntu/neurocomputer/neuro_web && npm run dev
```

Expected: `ready - started server on 0.0.0.0:3000`

- [ ] **Step 2: Smoke test — app loads**

Open `http://localhost:3000`. Expected: Neuro workspace renders — sidebar on left, empty chat area, TopBar with "N" logo.

- [ ] **Step 3: Smoke test — projects load**

With backend running on :7000, the sidebar should show project list after ~1s.

- [ ] **Step 4: Smoke test — send message**

Click "+" in tab bar → new conversation tab created. Type a message → hit Enter. User bubble appears. Agent response arrives via LiveKit DataChannel.

- [ ] **Step 5: Final commit**

```bash
cd /home/ubuntu/neurocomputer
git add -A neuro_web/
git commit -m "feat(neuro_web): complete desktop web UI v1"
```

---

## Self-Review

**Spec coverage:**
- ✅ Fixed Sidebar (260px): ProjectList + AgentFilter + ConversationList
- ✅ TopBar: Logo, AgentDropdown, ConnectionStatus
- ✅ TabBar: Open tabs, close ×, + new tab
- ✅ ChatPanel: Messages with agent/user bubbles, auto-scroll, typing indicator
- ✅ ChatInput: Text, send button, Enter to send, Shift+Enter newline
- ✅ Redux Toolkit: all 5 slices with correct shape
- ✅ HTTP POST for sending, LiveKit DataChannel for receiving
- ✅ Project CRUD (create, delete, rename via context menu)
- ✅ Conversation CRUD (create, load, delete, rename, open as tab)
- ✅ Agent filter chips: All / Neuro / OpenClaw / OpenCode / NeuroUpwork
- ✅ Dark theme tokens matching NeuroColors
- ✅ Polling: conversations every 10s
- ✅ Markdown + syntax highlighting
- ✅ TypeScript types matching spec exactly
- ✅ `ngrok-skip-browser-warning` header in axios instance
- ❌ Sidebar resize (omitted — drag-to-resize adds significant complexity for V1, noted as deferred)
- ❌ Voice record in ChatInput — button present but wired to `isRecording` state toggle; actual MediaRecorder integration deferred to V2 (voice.ts created)

**Type consistency check:** `ConversationSummary.id` used as `Tab.cid` throughout ✅. `AgentType` enum strings match `agentId` field in API calls ✅. `appendMessage` uses `{ cid, message }` consistently ✅.
