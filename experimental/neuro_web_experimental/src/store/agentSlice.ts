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
