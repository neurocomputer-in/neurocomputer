export interface Project {
  id: string | null;
  name: string;
  description: string;
  color: string;
  workspaceId?: string | null;
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
  icon: string;
  color: string;
}

export interface Message {
  id: string;
  text: string;
  isUser: boolean;
  isVoice: boolean;
  audioUrl?: string;
  timestamp?: string;
  messageType?: 'assistant' | 'thinking' | 'step_progress' | 'error';
  thinking?: string;
  isStreaming?: boolean;
  streamId?: string;
  stepInfo?: { nodeId: string; neuroName: string; status: 'running' | 'done' | 'error' };
  toolCalls?: OpenCodeToolCall[];
  openCodeSteps?: OpenCodeStep[];
}

export interface OpenCodeToolCall {
  callId: string;
  tool: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  input: Record<string, unknown>;
  output: string;
  title: string;
  time?: { start?: number; end?: number };
}

export interface OpenCodeStep {
  step: number;
  status: 'running' | 'done';
  reason?: string;
  tokens?: { input: number; output: number; reasoning: number };
}

export interface ConversationSummary {
  id: string;
  title: string;
  lastMessage: string;
  updatedAt: string;
  agentId?: string;
  projectId?: string | null;
  workdir?: string | null;
}

export type TabKind = 'chat' | 'terminal' | 'neuroide';

export interface Tab {
  cid: string;
  title: string;
  agentId: string;
  isActive: boolean;
  workdir?: string | null;
  type?: TabKind;
  tmuxSession?: string | null;
}

export interface WindowTab {
  id: string;        // window-local uuid for this tab slot
  cid: string;       // conversation/terminal/ide session id
  appId: string;     // key into APP_MAP for icon + color
  title: string;
  type: TabKind;
}

export interface TerminalTab {
  id: string;
  cid: string;
  type: 'terminal';
  title: string;
  workspace_id: string;
  project_id: string | null;
  tmux_session: string;
  workdir: string | null;
  created_at: number | null;
  created_new?: boolean;
}

export interface TmuxSessionInfo {
  name: string;
  created_at: number;
  attached_clients: number;
  windows: number;
}

export interface Workspace {
  id: string;
  name: string;
  description: string;
  color: string;
  emoji: string;
  agents: string[];
  defaultAgent: string;
  /** Theme id (see neuro_web/theme/presets.ts). Defaults to "cosmic". */
  theme?: string;
}

/** @deprecated Use Workspace instead */
export type Agency = Workspace;

export interface LlmProviderInfo {
  id: string;
  name: string;
  envKey: string;
  available: boolean;
  defaultModel: string;
  models: string[];
}

export interface LlmSettings {
  provider: string;
  model: string;
}

export interface ModelAlias {
  display_name: string;
  description: string;
  provider: string;
  model_id: string;
}

export interface ModelRole {
  display_name: string;
  description: string;
  candidates: string[];
  pinned: string;
}

export interface ModelLibrary {
  aliases: Record<string, ModelAlias>;
  roles: Record<string, ModelRole>;
}

export const AGENT_LIST: AgentInfo[] = [
  { type: AgentType.ALL, name: 'All Agents', description: 'Show all', icon: 'globe', color: '#8B5CF6' },
  { type: AgentType.NEURO, name: 'Neuro', description: 'General AI assistant', icon: 'brain', color: '#8B5CF6' },
  { type: AgentType.OPENCLAW, name: 'OpenClaw', description: 'Web automation & scraping', icon: 'globe', color: '#f97316' },
  { type: AgentType.OPENCODE, name: 'OpenCode', description: 'Code assistant', icon: 'code', color: '#3b82f6' },
  { type: AgentType.NEUROUPWORK, name: 'NeuroUpwork', description: 'Upwork automation', icon: 'briefcase', color: '#14b8a6' },
];
