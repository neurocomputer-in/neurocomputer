import { configureStore } from '@reduxjs/toolkit';
import workspaceReducer from './workspaceSlice';
import projectReducer from './projectSlice';
import conversationReducer from './conversationSlice';
import agentReducer from './agentSlice';
import chatReducer from './chatSlice';
import uiReducer from './uiSlice';

export const store = configureStore({
  reducer: {
    workspace: workspaceReducer,
    projects: projectReducer,
    conversations: conversationReducer,
    agent: agentReducer,
    chat: chatReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
