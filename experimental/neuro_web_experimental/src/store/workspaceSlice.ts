import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Workspace } from '@/types';
import { apiGetWorkspaces, apiCreateWorkspace, apiUpdateWorkspace } from '@/services/api';

interface WorkspaceState {
  workspaces: Workspace[];
  selectedWorkspaceId: string | null;
  loading: boolean;
}

const initialState: WorkspaceState = {
  workspaces: [],
  selectedWorkspaceId: null,
  loading: false,
};

export const fetchWorkspaces = createAsyncThunk('workspaces/fetch', async () => {
  return await apiGetWorkspaces();
});

export const createWorkspace = createAsyncThunk(
  'workspaces/create',
  async (data: Partial<Workspace> & { name: string }) => {
    return await apiCreateWorkspace(data);
  },
);

export const updateWorkspace = createAsyncThunk(
  'workspaces/update',
  async ({ id, patch }: { id: string; patch: Partial<Workspace> }) => {
    return await apiUpdateWorkspace(id, patch);
  },
);

const workspaceSlice = createSlice({
  name: 'workspace',
  initialState,
  reducers: {
    setSelectedWorkspace(state, action: PayloadAction<string | null>) {
      state.selectedWorkspaceId = action.payload;
      try { localStorage.setItem('neuro_selected_workspace', action.payload ?? ''); } catch {}
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchWorkspaces.pending, (state) => { state.loading = true; })
      .addCase(fetchWorkspaces.fulfilled, (state, action) => {
        state.loading = false;
        state.workspaces = action.payload;
      })
      .addCase(fetchWorkspaces.rejected, (state) => { state.loading = false; })
      .addCase(createWorkspace.fulfilled, (state, action) => {
        state.workspaces.push(action.payload);
      })
      .addCase(updateWorkspace.fulfilled, (state, action) => {
        const idx = state.workspaces.findIndex(w => w.id === action.payload.id);
        if (idx >= 0) state.workspaces[idx] = action.payload;
      });
  },
});

export const { setSelectedWorkspace } = workspaceSlice.actions;
export default workspaceSlice.reducer;
