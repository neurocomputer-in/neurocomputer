import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import {
  apiTerminalCreate,
  apiTerminalDelete,
  apiTerminalSessions,
  apiTerminalCapabilities,
  apiTerminalList,
} from '@/services/api';
import type { TmuxSessionInfo, TerminalTab } from '@/types';

export type WsStatus = 'idle' | 'connecting' | 'ready' | 'reconnecting' | 'error';

interface TerminalState {
  available: boolean | null;
  sessionsByProject: Record<string, TmuxSessionInfo[]>;
  tabsByProject: Record<string, TerminalTab[]>;
  wsStatus: Record<string, WsStatus>;
}

const initialState: TerminalState = {
  available: null,
  sessionsByProject: {},
  tabsByProject: {},
  wsStatus: {},
};

function scopeKey(workspaceId: string | null | undefined,
                  projectId: string | null | undefined): string {
  return `${workspaceId || 'default'}:${projectId || 'main-default'}`;
}

export const fetchCapabilities = createAsyncThunk(
  'terminal/capabilities',
  async () => (await apiTerminalCapabilities()).available,
);

export const createTerminal = createAsyncThunk(
  'terminal/create',
  async (args: {
    title?: string;
    workspace_id: string;
    project_id: string | null;
    workdir?: string | null;
    tmux_session?: string | null;
  }) => apiTerminalCreate(args),
);

export const deleteTerminal = createAsyncThunk(
  'terminal/delete',
  async (args: { cid: string; killSession: boolean }) =>
    apiTerminalDelete(args.cid, args.killSession),
);

export const fetchTerminalSessions = createAsyncThunk(
  'terminal/sessions',
  async (args: { project_id?: string | null; agency_id?: string | null }) => {
    const rows = await apiTerminalSessions(args);
    return { key: scopeKey(args.agency_id, args.project_id), rows };
  },
);

export const fetchTerminalTabs = createAsyncThunk(
  'terminal/list',
  async (args: { project_id?: string | null; agency_id?: string | null }) => {
    const rows = await apiTerminalList(args);
    return { key: scopeKey(args.agency_id, args.project_id), rows };
  },
);

const slice = createSlice({
  name: 'terminal',
  initialState,
  reducers: {
    setWsStatus(state, a: PayloadAction<{ cid: string; status: WsStatus }>) {
      state.wsStatus[a.payload.cid] = a.payload.status;
    },
  },
  extraReducers: b => {
    b.addCase(fetchCapabilities.fulfilled, (s, a) => { s.available = a.payload; });
    b.addCase(fetchTerminalSessions.fulfilled, (s, a) => {
      s.sessionsByProject[a.payload.key] = a.payload.rows;
    });
    b.addCase(fetchTerminalTabs.fulfilled, (s, a) => {
      s.tabsByProject[a.payload.key] = a.payload.rows;
    });
  },
});

export const { setWsStatus } = slice.actions;
export default slice.reducer;
