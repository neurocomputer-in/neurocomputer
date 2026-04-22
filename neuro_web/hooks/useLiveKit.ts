'use client';
import { useEffect, useCallback } from 'react';
import { ConnectionState } from 'livekit-client';
import { livekitService } from '@/services/livekit';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setConnectionStatus } from '@/store/uiSlice';
import { appendMessage } from '@/store/conversationSlice';
import { setLoading } from '@/store/chatSlice';
import { Message } from '@/types';

export function useLiveKit() {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);

  const handleData = useCallback((text: string, _topic: string) => {
    if (!activeTabCid) return;
    const message: Message = {
      id: `agent-${Date.now()}-${Math.random()}`,
      text,
      isUser: false,
      isVoice: false,
      timestamp: new Date().toISOString(),
    };
    dispatch(appendMessage({ cid: activeTabCid, message }));
    dispatch(setLoading(false));
  }, [activeTabCid, dispatch]);

  const handleStateChange = useCallback((state: ConnectionState) => {
    if (state === ConnectionState.Connected) dispatch(setConnectionStatus('connected'));
    else if (state === ConnectionState.Connecting || state === ConnectionState.Reconnecting)
      dispatch(setConnectionStatus('connecting'));
    else dispatch(setConnectionStatus('disconnected'));
  }, [dispatch]);

  useEffect(() => {
    livekitService.onMessage(handleData);
    livekitService.onStateChange(handleStateChange);
  }, [handleData, handleStateChange]);

  const connectToConversation = useCallback(async (cid: string) => {
    dispatch(setConnectionStatus('connecting'));
    try {
      console.log('[LiveKit] connecting to conversation', cid);
      await livekitService.connect(cid);
      console.log('[LiveKit] connect() resolved, state:', livekitService.getState());
    } catch (e: any) {
      console.error('[LiveKit] connect error:', e?.message || e);
      dispatch(setConnectionStatus('disconnected'));
    }
  }, [dispatch]);

  return { connectToConversation };
}
