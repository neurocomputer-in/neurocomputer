import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface StepInfo {
  nodeId: string;
  neuro: string;
  status: 'running' | 'done' | 'error';
}

type VoiceActivity = 'idle' | 'listening' | 'thinking' | 'speaking';

interface VoiceCallState {
  active: boolean;
  muted: boolean;
  startedAt: string | null;
  cid: string | null;
  activity: VoiceActivity;
}

interface ChatState {
  isLoading: boolean;
  inputText: string;
  thinkingContent: string | null;
  currentStep: StepInfo | null;
  voiceCall: VoiceCallState;
  interimTranscript: string | null;
  /**
   * Monotonic counter bumped on every backend activity event (stream chunks,
   * opencode.* events, heartbeats). useChat's client-side safety timer
   * watches this so it resets whenever the backend is still working, and
   * only fires after the true idle window.
   */
  loadingActivityTick: number;
}

const initialState: ChatState = {
  isLoading: false,
  inputText: '',
  thinkingContent: null,
  currentStep: null,
  voiceCall: { active: false, muted: false, startedAt: null, cid: null, activity: 'idle' as VoiceActivity },
  interimTranscript: null,
  loadingActivityTick: 0,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
      if (!action.payload) {
        state.thinkingContent = null;
        state.currentStep = null;
      }
    },
    setInputText(state, action: PayloadAction<string>) {
      state.inputText = action.payload;
    },
    setThinkingContent(state, action: PayloadAction<string | null>) {
      state.thinkingContent = action.payload;
    },
    setCurrentStep(state, action: PayloadAction<StepInfo | null>) {
      state.currentStep = action.payload;
    },
    clearAgentState(state) {
      state.thinkingContent = null;
      state.currentStep = null;
    },
    setVoiceCallActive(state, action: PayloadAction<{ active: boolean; cid?: string | null }>) {
      state.voiceCall.active = action.payload.active;
      state.voiceCall.startedAt = action.payload.active ? new Date().toISOString() : null;
      state.voiceCall.cid = action.payload.active ? (action.payload.cid ?? state.voiceCall.cid) : null;
      if (!action.payload.active) {
        state.voiceCall.muted = false;
        state.voiceCall.activity = 'idle';
        state.interimTranscript = null;
      }
    },
    setVoiceCallMuted(state, action: PayloadAction<boolean>) {
      state.voiceCall.muted = action.payload;
    },
    setInterimTranscript(state, action: PayloadAction<string | null>) {
      state.interimTranscript = action.payload;
    },
    setVoiceActivity(state, action: PayloadAction<VoiceActivity>) {
      state.voiceCall.activity = action.payload;
    },
    bumpLoadingActivity(state) {
      state.loadingActivityTick += 1;
    },
  },
});

export const {
  setLoading, setInputText, setThinkingContent,
  setCurrentStep, clearAgentState,
  setVoiceCallActive, setVoiceCallMuted, setInterimTranscript, setVoiceActivity,
  bumpLoadingActivity,
} = chatSlice.actions;
export default chatSlice.reducer;
