'use client';
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { createConversation, openTab } from '@/store/conversationSlice';
import { AgentType } from '@/types';

/**
 * Returns an ``ensure()`` helper that guarantees an active conversation.
 * If a tab is already active it returns its cid; otherwise it creates a
 * new conversation in the currently-selected project/workspace using the
 * filtered agent (fallback: Neuro), opens a tab, and returns the new cid.
 *
 * Used by any hook that needs to act on a conversation from the welcome
 * screen (chat send, voice message, voice call) without forcing the user
 * to click a separate "New Session" button.
 */
export function useEnsureConversation() {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const agentFilter = useAppSelector(s => s.agent.agentFilter);
  const selectedProjectId = useAppSelector(s => s.projects.selectedProjectId);

  const ensure = useCallback(async (): Promise<{ cid: string; agentId: string } | null> => {
    if (activeTabCid) {
      return { cid: activeTabCid, agentId: 'neuro' };
    }
    const agentType =
      (agentFilter && agentFilter !== AgentType.ALL) ? agentFilter : AgentType.NEURO;

    // If the user picked a provider/model via LlmSelector before any
    // conversation existed, carry that selection into the new conversation.
    let pendingLlm: { provider?: string; model?: string } = {};
    try {
      const raw = localStorage.getItem('neuro_pending_llm');
      if (raw) pendingLlm = JSON.parse(raw) || {};
    } catch {}

    const result = await dispatch(createConversation({
      agentId: agentType,
      projectId: selectedProjectId,
      llmProvider: pendingLlm.provider,
      llmModel: pendingLlm.model,
    } as any));
    if (!createConversation.fulfilled.match(result)) return null;
    const conv = result.payload as any;
    dispatch(openTab({
      cid: conv.id,
      title: conv.title || 'New Chat',
      agentId: conv.agentId ?? agentType,
      isActive: true,
      workdir: conv.workdir,
    } as any));
    return { cid: conv.id as string, agentId: conv.agentId ?? agentType };
  }, [activeTabCid, agentFilter, selectedProjectId, dispatch]);

  return { ensure };
}
