'use client';
import { useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  fetchConversations, createConversation, deleteConversation,
  renameConversation, openTab, closeTab, setActiveTab,
  loadMessages,
} from '@/store/conversationSlice';
import { Tab } from '@/types';

export function useConversations() {
  const dispatch = useAppDispatch();
  const selectedWorkspaceId = useAppSelector(s => s.workspace.selectedWorkspaceId);
  const conversations = useAppSelector(s => s.conversations.conversations);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const tabMessages = useAppSelector(s => s.conversations.tabMessages);
  const loading = useAppSelector(s => s.conversations.loading);

  const refresh = useCallback(
    (projectId: string | null) => dispatch(fetchConversations({ projectId, agencyId: selectedWorkspaceId })),
    [dispatch, selectedWorkspaceId]
  );

  const create = useCallback(
    (agentId: string, projectId: string | null, title?: string) =>
      dispatch(createConversation({ title, agentId, projectId })),
    [dispatch]
  );

  const remove = useCallback(
    (cid: string) => dispatch(deleteConversation(cid)),
    [dispatch]
  );

  const rename = useCallback(
    (cid: string, title: string) => dispatch(renameConversation({ cid, title })),
    [dispatch]
  );

  const openConversation = useCallback(
    async (tab: Tab) => {
      dispatch(openTab(tab));
      if (!tabMessages[tab.cid] || tabMessages[tab.cid].length === 0) {
        await dispatch(loadMessages(tab.cid));
      }
    },
    [dispatch, tabMessages]
  );

  const switchTab = useCallback(
    (cid: string) => dispatch(setActiveTab(cid)),
    [dispatch]
  );

  const closeTabById = useCallback(
    (cid: string) => dispatch(closeTab(cid)),
    [dispatch]
  );

  return {
    conversations, openTabs, activeTabCid, tabMessages, loading,
    refresh, create, remove, rename, openConversation, switchTab, closeTabById,
  };
}
