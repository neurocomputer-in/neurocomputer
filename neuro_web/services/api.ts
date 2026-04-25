import axios from 'axios';
import { Project, ConversationSummary, Message, Workspace, LlmProviderInfo, LlmSettings, ModelLibrary, TerminalTab, TmuxSessionInfo } from '@/types';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7000';

export const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',
  },
});

// ---- Projects ----

export async function apiGetProjects(workspaceId?: string | null): Promise<Project[]> {
  const params = workspaceId ? { agency_id: workspaceId } : {};
  const res = await api.get('/projects', { params });
  return res.data;
}

export async function apiCreateProject(data: {
  name: string;
  color: string;
  description?: string;
  workspaceId?: string | null;
}): Promise<Project> {
  const payload: Record<string, unknown> = {
    name: data.name,
    color: data.color,
  };
  if (data.description) payload.description = data.description;
  if (data.workspaceId) payload.agency_id = data.workspaceId;
  const res = await api.post('/projects', payload);
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
  projectId: string | null,
  workspaceId?: string | null
): Promise<ConversationSummary[]> {
  const params: Record<string, string> = {};
  if (projectId) params.project_id = projectId;
  if (workspaceId) params.agency_id = workspaceId;
  const res = await api.get('/conversations', { params });
  return res.data;
}

export async function apiCreateConversation(data: {
  title?: string;
  agentId?: string;
  projectId?: string | null;
  workdir?: string | null;
  llmProvider?: string;
  llmModel?: string;
}): Promise<ConversationSummary> {
  const payload: Record<string, unknown> = {};
  if (data.title) payload.title = data.title;
  if (data.agentId) payload.agent_id = data.agentId;
  if (data.projectId) payload.project_id = data.projectId;
  if (data.workdir) payload.workdir = data.workdir;
  if (data.llmProvider) payload.llm_provider = data.llmProvider;
  if (data.llmModel) payload.llm_model = data.llmModel;
  const res = await api.post('/conversation', payload);
  return res.data;
}

export async function apiGetConversation(cid: string): Promise<{
  id: string;
  title: string;
  messages: any[];
  llmSettings?: LlmSettings;
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

export async function apiUpdateConversationAgent(
  cid: string,
  agentId: string
): Promise<ConversationSummary> {
  const res = await api.patch(`/conversation/${cid}`, { agent_id: agentId });
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

export async function apiCancelChat(cid: string): Promise<{ status: string }> {
  const res = await api.post(`/chat/${cid}/cancel`);
  return res.data;
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

// ---- Workspaces ----

export async function apiGetWorkspaces(): Promise<Workspace[]> {
  const res = await api.get('/workspaces');
  return res.data;
}

export async function apiCreateWorkspace(data: Partial<Workspace>): Promise<Workspace> {
  const res = await api.post('/workspaces', data);
  return res.data;
}

export async function apiUpdateWorkspace(id: string, data: Partial<Workspace>): Promise<Workspace> {
  const res = await api.patch(`/workspaces/${id}`, data);
  return res.data;
}

/** @deprecated Use apiGetWorkspaces */ export const apiGetAgencies = apiGetWorkspaces;
/** @deprecated Use apiCreateWorkspace */ export const apiCreateAgency = apiCreateWorkspace;
/** @deprecated Use apiUpdateWorkspace */ export const apiUpdateAgency = apiUpdateWorkspace;

// ---- LLM Settings ----

export async function apiGetLlmProviders(): Promise<{
  providers: LlmProviderInfo[];
  default: LlmSettings;
}> {
  const res = await api.get('/llm/providers');
  return res.data;
}

export async function apiSetOpenCodeModel(provider: string, model: string): Promise<void> {
  await api.post('/opencode/model', { provider, model });
}

export async function apiGetOpenCodeProviders(): Promise<{
  providers: LlmProviderInfo[];
  default: LlmSettings;
}> {
  const res = await api.get('/opencode/providers');
  return res.data;
}

export async function apiGetConversationLlm(cid: string): Promise<LlmSettings> {
  const res = await api.get(`/conversation/${cid}/llm`);
  return res.data;
}

export async function apiUpdateConversationLlm(
  cid: string,
  data: Partial<LlmSettings>
): Promise<LlmSettings> {
  const res = await api.patch(`/conversation/${cid}/llm`, data);
  return res.data;
}

// ---- Model Library ----

export async function apiGetModelLibrary(): Promise<ModelLibrary> {
  const res = await api.get('/model-library');
  return res.data;
}

export async function apiPutModelLibrary(lib: ModelLibrary): Promise<ModelLibrary> {
  const res = await api.put('/model-library', lib);
  return res.data;
}

export async function apiGetConversationRole(cid: string): Promise<{ session_role: string | null }> {
  const res = await api.get(`/conversation/${cid}/role`);
  return res.data;
}

export async function apiUpdateConversationRole(
  cid: string,
  session_role: string | null,
): Promise<{ session_role: string | null; resolved: LlmSettings | null }> {
  const res = await api.patch(`/conversation/${cid}/role`, { session_role });
  return res.data;
}

// ---- Voice Call ----

export async function apiStartVoiceCall(data: {
  conversationId: string;
  agentId?: string;
}): Promise<{ token: string; url: string; room_name: string; conversation_id: string }> {
  const res = await api.post('/voice/call', {
    conversation_id: data.conversationId,
    agent_id: data.agentId || 'neuro',
  });
  return res.data;
}

export async function apiEndVoiceCall(conversationId: string): Promise<void> {
  await api.post('/voice/hangup', { conversation_id: conversationId });
}

export async function apiVoiceCallStatus(conversationId: string): Promise<{ active: boolean }> {
  const res = await api.get(`/voice/status/${conversationId}`);
  return res.data;
}

// ---- Terminal tabs ----

export async function apiTerminalCapabilities(): Promise<{ available: boolean; reason: string | null }> {
  const res = await api.get('/terminal/capabilities');
  return res.data;
}

export async function apiTerminalCreate(body: {
  title?: string;
  workspace_id: string;
  project_id: string | null;
  workdir?: string | null;
  tmux_session?: string | null;
}): Promise<TerminalTab> {
  const res = await api.post('/terminal', body);
  return res.data;
}

export async function apiTerminalGet(cid: string): Promise<TerminalTab> {
  const res = await api.get(`/terminal/${cid}`);
  return res.data;
}

export async function apiTerminalList(params: {
  project_id?: string | null;
  agency_id?: string | null;
}): Promise<TerminalTab[]> {
  const res = await api.get('/terminal', { params });
  return res.data;
}

export async function apiTerminalPatch(
  cid: string,
  body: { title?: string; tmux_session?: string },
): Promise<TerminalTab> {
  const res = await api.patch(`/terminal/${cid}`, body);
  return res.data;
}

export async function apiTerminalDelete(
  cid: string,
  killSession = false,
): Promise<{ ok: boolean; killed: boolean; tmux_session: string | null }> {
  const res = await api.delete(`/terminal/${cid}`, {
    params: { kill_session: killSession ? 1 : 0 },
  });
  return res.data;
}

export async function apiTerminalSessions(params: {
  project_id?: string | null;
  agency_id?: string | null;
}): Promise<TmuxSessionInfo[]> {
  const res = await api.get('/terminal/sessions', { params });
  return res.data;
}

export function terminalWsUrl(cid: string): string {
  let base = BASE_URL;
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    base = base.replace(/^http:\/\/|^https:\/\//, 'https://');
  }
  return base.replace(/^http/, 'ws') + `/terminal/ws/${cid}`;
}
