'use client';
import { useCallback, useEffect, useRef } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { appendMessage, createConversation, openTab } from '@/store/conversationSlice';
import { setLoading, setInputText } from '@/store/chatSlice';
import { apiSendMessage } from '@/services/api';
import { AgentType, Message } from '@/types';

// Idle window: if no backend activity (stream chunk, opencode.* event,
// heartbeat) arrives within this many ms, treat the turn as stalled and
// stop the "thinking" animation. Resets on every activity bump so long
// multi-step turns keep the UI alive as long as the backend is working.
const LOADING_IDLE_TIMEOUT_MS = 30000;

export function useChat() {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  // Use the active tab's agentId as the source of truth — not the global selectedAgent
  // which is never updated when the user switches agents via the dropdown.
  const activeTabAgentId = openTabs.find(t => t.cid === activeTabCid)?.agentId ?? 'neuro';
  const inputText = useAppSelector(s => s.chat.inputText);
  const isLoading = useAppSelector(s => s.chat.isLoading);
  const activityTick = useAppSelector(s => s.chat.loadingActivityTick);
  const loadingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Arm / re-arm the idle timer on every transition of isLoading → true
  // and on every activity bump while loading. Clear it when loading ends.
  useEffect(() => {
    if (loadingTimer.current) {
      clearTimeout(loadingTimer.current);
      loadingTimer.current = null;
    }
    if (!isLoading) return;
    loadingTimer.current = setTimeout(() => {
      dispatch(setLoading(false));
    }, LOADING_IDLE_TIMEOUT_MS);
    return () => {
      if (loadingTimer.current) {
        clearTimeout(loadingTimer.current);
        loadingTimer.current = null;
      }
    };
  }, [isLoading, activityTick, dispatch]);

  const sendMessage = useCallback(async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed) return;

    // Resolve target conversation. If no tab is active, auto-create one in
    // the currently-selected project/workspace so the user can chat
    // directly from the welcome screen without a separate "New Session"
    // click. The agent is whatever's filtered to (fallback to Neuro).
    let cid = activeTabCid;
    let agent = activeTabAgentId;
    if (!cid) {
      const agentType =
        (agentFilter && agentFilter !== AgentType.ALL) ? agentFilter : AgentType.NEURO;
      const result = await dispatch(createConversation({
        agentId: agentType,
        projectId: selectedProjectId,
      } as any));
      if (!createConversation.fulfilled.match(result)) {
        console.error('Failed to auto-create conversation for new message');
        return;
      }
      const conv = result.payload as any;
      cid = conv.id;
      agent = conv.agentId ?? agentType;
      dispatch(openTab({
        cid: cid as string,
        title: conv.title || 'New Chat',
        agentId: agent,
        isActive: true,
        workdir: conv.workdir,
      } as any));
      // `page.tsx` picks up the activeTabCid change via useEffect and
      // wires up LiveKit + loadMessages. We continue to send below.
    }

    const userMsg: Message = {
      id: `user-${Date.now()}`,
      text: trimmed,
      isUser: true,
      isVoice: false,
      timestamp: new Date().toISOString(),
    };
    dispatch(appendMessage({ cid: cid as string, message: userMsg }));
    dispatch(setInputText(''));
    dispatch(setLoading(true));

    try {
      await apiSendMessage({
        cid: cid as string,
        message: trimmed,
        agentId: agent,
      });
    } catch (e) {
      console.error('Failed to send message', e);
      dispatch(setLoading(false));
    }
  }, [activeTabCid, activeTabAgentId, agentFilter, selectedProjectId, selectedWorkspaceId, dispatch]);

  return { sendMessage, inputText, isLoading };
}
