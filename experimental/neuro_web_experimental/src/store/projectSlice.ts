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
  selectedProjectId: null,
  loading: false,
};

export const fetchProjects = createAsyncThunk('projects/fetch', async (workspaceId?: string | null) => {
  return await apiGetProjects(workspaceId);
});

export const createProject = createAsyncThunk(
  'projects/create',
  async (data: { name: string; color: string; description?: string; workspaceId?: string | null }) => {
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
      try { localStorage.setItem('neuro_selected_project', action.payload ?? ''); } catch {}
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
