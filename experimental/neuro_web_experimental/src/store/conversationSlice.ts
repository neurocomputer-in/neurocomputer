import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { ConversationSummary, Message, Tab, OpenCodeToolCall, OpenCodeStep } from '@/types';
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
  async ({ projectId, agencyId }: { projectId: string | null; agencyId?: string | null }) => {
    return await apiGetConversations(projectId, agencyId); // agencyId param name kept for backward compat in callers
  }
);

export const createConversation = createAsyncThunk(
  'conversations/create',
  async (data: {
    title?: string; agentId?: string;
    projectId?: string | null; workdir?: string | null;
    llmProvider?: string; llmModel?: string;
  }) => {
    return await apiCreateConversation(data);
  }
);

export const loadMessages = createAsyncThunk(
  'conversations/loadMessages',
  async (cid: string) => {
    const conv = await apiGetConversation(cid);
    // Backend returns {role, content}, frontend expects {isUser, text}
    const messages: Message[] = (conv.messages ?? []).map((raw: any) => ({
      id: raw.id ?? `msg-${Date.now()}-${Math.random()}`,
      text: raw.content ?? raw.text ?? '',
      isUser: raw.role ? raw.role === 'user' : (raw.isUser ?? false),
      isVoice: raw.isVoice ?? false,
      audioUrl: raw.audioUrl,
      timestamp: raw.timestamp,
    }));
    return { cid, messages };
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

function _persistTabs(state: ConversationState) {
  try {
    const workspaceId = typeof window !== 'undefined'
      ? (localStorage.getItem('neuro_selected_workspace') || 'global')
      : 'global';
    const projectId = typeof window !== 'undefined'
      ? (localStorage.getItem('neuro_selected_project') || 'global')
      : 'global';
    localStorage.setItem(`neuro_tabs_${workspaceId}_${projectId}`, JSON.stringify({
      openTabs: state.openTabs,
      activeTabCid: state.activeTabCid,
    }));
  } catch {}
}

const conversationSlice = createSlice({
  name: 'conversations',
  initialState,
  reducers: {
    openTab(state, action: PayloadAction<Tab>) {
      const exists = state.openTabs.find(t => t.cid === action.payload.cid);
      if (!exists) state.openTabs.push(action.payload);
      state.activeTabCid = action.payload.cid;
      _persistTabs(state);
    },
    closeTab(state, action: PayloadAction<string>) {
      state.openTabs = state.openTabs.filter(t => t.cid !== action.payload);
      if (state.activeTabCid === action.payload) {
        state.activeTabCid = state.openTabs.length > 0
          ? state.openTabs[state.openTabs.length - 1].cid
          : null;
      }
      _persistTabs(state);
    },
    setActiveTab(state, action: PayloadAction<string>) {
      state.activeTabCid = action.payload;
      _persistTabs(state);
    },
    appendMessage(state, action: PayloadAction<{ cid: string; message: Message }>) {
      const { cid, message } = action.payload;
      if (!state.tabMessages[cid]) state.tabMessages[cid] = [];
      const idx = state.tabMessages[cid].findIndex(m => m.id === message.id);
      if (idx >= 0) {
        // Update existing message (e.g., voice transcription update)
        state.tabMessages[cid][idx] = message;
      } else {
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
    updateTabAgent(state, action: PayloadAction<{ cid: string; agentId: string }>) {
      const tab = state.openTabs.find(t => t.cid === action.payload.cid);
      if (tab) tab.agentId = action.payload.agentId;
      _persistTabs(state);
    },
    /** Append a streaming chunk to a message (creates if needed) */
    appendStreamChunk(state, action: PayloadAction<{ cid: string; streamId: string; chunk: string; neuro?: string }>) {
      const { cid, streamId, chunk, neuro } = action.payload;
      if (!state.tabMessages[cid]) state.tabMessages[cid] = [];
      const msgs = state.tabMessages[cid];
      const existing = msgs.find(m => m.streamId === streamId);
      if (existing) {
        existing.text += chunk;
      } else {
        msgs.push({
          id: streamId,
          text: chunk,
          isUser: false,
          isVoice: false,
          isStreaming: true,
          streamId,
          messageType: 'assistant',
          timestamp: new Date().toISOString(),
        });
      }
    },
    /** Mark a streaming message as complete */
    finalizeStream(state, action: PayloadAction<{ cid: string; streamId: string }>) {
      const { cid, streamId } = action.payload;
      const msgs = state.tabMessages[cid];
      if (!msgs) return;
      const msg = msgs.find(m => m.streamId === streamId);
      if (msg) msg.isStreaming = false;
    },
    /** Add or update a tool call on a streaming message */
    appendToolCall(state, action: PayloadAction<{ cid: string; streamId: string; toolCall: OpenCodeToolCall }>) {
      const { cid, streamId, toolCall } = action.payload;
      if (!state.tabMessages[cid]) state.tabMessages[cid] = [];
      const msgs = state.tabMessages[cid];
      let msg = msgs.find(m => m.streamId === streamId);
      if (!msg) {
        msg = {
          id: streamId,
          text: '',
          isUser: false,
          isVoice: false,
          isStreaming: true,
          streamId,
          messageType: 'assistant',
          timestamp: new Date().toISOString(),
        };
        msgs.push(msg);
      }
      if (!msg.toolCalls) msg.toolCalls = [];
      const existing = msg.toolCalls.find(tc => tc.callId === toolCall.callId);
      if (existing) {
        Object.assign(existing, toolCall);
      } else {
        msg.toolCalls.push(toolCall);
      }
    },
    /** Add or update a step on a streaming message */
    appendStep(state, action: PayloadAction<{ cid: string; streamId: string; step: OpenCodeStep }>) {
      const { cid, streamId, step } = action.payload;
      if (!state.tabMessages[cid]) state.tabMessages[cid] = [];
      const msgs = state.tabMessages[cid];
      let msg = msgs.find(m => m.streamId === streamId);
      if (!msg) {
        msg = {
          id: streamId,
          text: '',
          isUser: false,
          isVoice: false,
          isStreaming: true,
          streamId,
          messageType: 'assistant',
          timestamp: new Date().toISOString(),
        };
        msgs.push(msg);
      }
      if (!msg.openCodeSteps) msg.openCodeSteps = [];
      const existing = msg.openCodeSteps.find(s => s.step === step.step);
      if (existing) {
        Object.assign(existing, step);
      } else {
        msg.openCodeSteps.push(step);
      }
    },
    /** Restore tabs from localStorage for current workspace+project on page load */
    restoreTabs(state) {
      try {
        const workspaceId = localStorage.getItem('neuro_selected_workspace') || 'global';
        const projectId = localStorage.getItem('neuro_selected_project') || 'global';
        const saved = localStorage.getItem(`neuro_tabs_${workspaceId}_${projectId}`);
        if (saved) {
          const parsed = JSON.parse(saved);
          state.openTabs = parsed.openTabs ?? [];
          state.activeTabCid = parsed.activeTabCid ?? null;
        }
      } catch {}
    },
    /** Save current tabs to localStorage for workspace+project, then restore another's tabs */
    switchProjectTabs(state, action: PayloadAction<{
      fromProjectId: string | null;
      toProjectId: string | null;
      fromAgencyId?: string | null;
      toAgencyId?: string | null;
    }>) {
      const { fromProjectId, toProjectId, fromAgencyId, toAgencyId } = action.payload;
      const fromWorkspace = fromAgencyId ?? 'global';
      const toWorkspace = toAgencyId ?? fromWorkspace;
      // Save current tabs for the workspace+project we're leaving
      const key = `neuro_tabs_${fromWorkspace}_${fromProjectId ?? 'global'}`;
      try {
        localStorage.setItem(key, JSON.stringify({
          openTabs: state.openTabs,
          activeTabCid: state.activeTabCid,
        }));
      } catch {}
      // Restore tabs for the workspace+project we're switching to
      const restoreKey = `neuro_tabs_${toWorkspace}_${toProjectId ?? 'global'}`;
      try {
        const saved = localStorage.getItem(restoreKey);
        if (saved) {
          const parsed = JSON.parse(saved);
          state.openTabs = parsed.openTabs ?? [];
          state.activeTabCid = parsed.activeTabCid ?? null;
        } else {
          state.openTabs = [];
          state.activeTabCid = null;
        }
      } catch {
        state.openTabs = [];
        state.activeTabCid = null;
      }
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
  replaceTabCid, clearTabMessages, updateTabAgent, switchProjectTabs, restoreTabs,
  appendStreamChunk, finalizeStream, appendToolCall, appendStep,
} = conversationSlice.actions;
export default conversationSlice.reducer;
