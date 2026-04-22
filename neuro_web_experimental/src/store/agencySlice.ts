// @ts-nocheck — deprecated, replaced by workspaceSlice
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Agency } from '@/types';
import { apiGetAgencies } from '@/services/api';

interface AgencyState {
  agencies: Agency[];
  selectedAgencyId: string | null;
  loading: boolean;
}

const initialState: AgencyState = {
  agencies: [],
  selectedAgencyId: null,
  loading: false,
};

export const fetchAgencies = createAsyncThunk('agencies/fetch', async () => {
  return await apiGetAgencies();
});

const agencySlice = createSlice({
  name: 'agency',
  initialState,
  reducers: {
    setSelectedAgency(state, action: PayloadAction<string | null>) {
      state.selectedAgencyId = action.payload;
      try { localStorage.setItem('neuro_selected_agency', action.payload ?? ''); } catch {}
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchAgencies.pending, (state) => { state.loading = true; })
      .addCase(fetchAgencies.fulfilled, (state, action) => {
        state.loading = false;
        state.agencies = action.payload;
      })
      .addCase(fetchAgencies.rejected, (state) => { state.loading = false; });
  },
});

export const { setSelectedAgency } = agencySlice.actions;
export default agencySlice.reducer;
