'use client';
import { createContext, useContext, useEffect, useCallback, useRef, ReactNode } from 'react';
import { ConnectionState } from 'livekit-client';
import { livekitService } from '@/services/livekit';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setConnectionStatus } from '@/store/uiSlice';
import { appendMessage, appendStreamChunk, finalizeStream, appendToolCall, appendStep } from '@/store/conversationSlice';
import { store } from '@/store';
import { setLoading, setThinkingContent, setCurrentStep, setVoiceCallActive, setInterimTranscript, setVoiceActivity, bumpLoadingActivity } from '@/store/chatSlice';
import { requestTTS, playAudio } from '@/services/voice';
import { Message } from '@/types';

interface LiveKitContextValue {
  connectToConversation: (cid: string) => Promise<void>;
}

const LiveKitContext = createContext<LiveKitContextValue>({
  connectToConversation: async () => {},
});

export function useLiveKitContext() {
  return useContext(LiveKitContext);
}

export function LiveKitProvider({ children }: { children: ReactNode }) {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const ttsAutoPlay = useAppSelector(s => s.ui.ttsAutoPlay);
  const activeTabCidRef = useRef(activeTabCid);
  const ttsAutoPlayRef = useRef(ttsAutoPlay);

  useEffect(() => { activeTabCidRef.current = activeTabCid; }, [activeTabCid]);
  useEffect(() => { ttsAutoPlayRef.current = ttsAutoPlay; }, [ttsAutoPlay]);

  // Register handlers ONCE on the singleton service
  useEffect(() => {
    livekitService.onMessage((raw: string, topic: string) => {
      const cid = activeTabCidRef.current;
      if (!cid) return;

      let parsed: any;
      try {
        parsed = JSON.parse(raw);
      } catch {
        // Not JSON — treat as plain text agent response
        if (raw.trim()) {
          const message: Message = {
            id: `agent-${Date.now()}-${Math.random()}`,
            text: raw,
            isUser: false,
            isVoice: false,
            timestamp: new Date().toISOString(),
          };
          dispatch(appendMessage({ cid, message }));
          dispatch(setLoading(false));
        }
        return;
      }

      // ── Handle system events (thinking, steps, streaming) ──────
      if (topic === 'system_event' || parsed.sender === 'system' || parsed.type === 'system') {
        const eventTopic = parsed.text || parsed.content || '';
        const metadata = parsed.metadata || {};
        const data = metadata.data || metadata;

        // Any backend activity resets the idle safety timer in useChat.
        // Specifically include long-running signals (opencode.* + streaming)
        // so multi-step turns don't hit the client-side stall timeout.
        if (
          eventTopic === 'stream_chunk' ||
          eventTopic === 'node.start' ||
          eventTopic === 'node.done' ||
          eventTopic === 'thinking' ||
          (typeof eventTopic === 'string' && eventTopic.startsWith('opencode.'))
        ) {
          dispatch(bumpLoadingActivity());
        }

        if (eventTopic === 'thinking' && data.content) {
          dispatch(setThinkingContent(data.content));
          return;
        }

        if (eventTopic === 'node.start' && data.id) {
          dispatch(setCurrentStep({
            nodeId: data.id,
            neuro: data.neuro || 'processing',
            status: 'running',
          }));
          return;
        }

        if (eventTopic === 'node.done' && data.id) {
          dispatch(setCurrentStep({
            nodeId: data.id,
            neuro: data.neuro || 'processing',
            status: 'done',
          }));
          return;
        }

        if (eventTopic === 'stream_chunk' && data.stream_id) {
          dispatch(appendStreamChunk({
            cid,
            streamId: data.stream_id,
            chunk: data.chunk || '',
            neuro: data.neuro,
          }));
          return;
        }

        if (eventTopic === 'stream_end' && data.stream_id) {
          dispatch(finalizeStream({ cid, streamId: data.stream_id }));
          dispatch(setLoading(false));
          return;
        }

        if (eventTopic === 'opencode.tool' && data.call_id) {
          const msgs = store.getState().conversations.tabMessages[cid] || [];
          const streaming = msgs.find(m => m.isStreaming && m.streamId);
          const streamId = streaming?.streamId || data.stream_id || `opencode-${Date.now()}`;
          dispatch(appendToolCall({
            cid,
            streamId,
            toolCall: {
              callId: data.call_id,
              tool: data.tool || '',
              status: data.status || 'running',
              input: data.input || {},
              output: data.output || '',
              title: data.title || '',
              time: data.time,
            },
          }));
          return;
        }

        if (eventTopic === 'opencode.step') {
          const msgs = store.getState().conversations.tabMessages[cid] || [];
          const streaming = msgs.find(m => m.isStreaming && m.streamId);
          const streamId = streaming?.streamId || data.stream_id || `opencode-${Date.now()}`;
          dispatch(appendStep({
            cid,
            streamId,
            step: {
              step: data.stepID ?? data.step ?? 0,
              status: data.type === 'step-start' ? 'running' : 'done',
              reason: data.reason,
              tokens: data.tokens,
            },
          }));
          return;
        }

        if (eventTopic === 'opencode.reasoning') {
          // Reasoning preview from the delegate — surfaces "what the model
          // is thinking about" during long multi-step turns so the UI
          // doesn't look dead during reasoning-only stretches.
          const text = typeof data.text === 'string' ? data.text : '';
          if (text) dispatch(setThinkingContent(text));
          return;
        }

        if (eventTopic === 'opencode.heartbeat') {
          // Keep-alive tick from the delegate. Ensure loading stays on so
          // the thinking animation doesn't give up while a long turn runs.
          dispatch(setLoading(true));
          return;
        }

        if (eventTopic === 'task.done' || eventTopic === 'task.cancelled') {
          dispatch(setLoading(false));
          dispatch(setThinkingContent(null));
          dispatch(setCurrentStep(null));
          return;
        }

        // Other system events — ignore silently
        return;
      }

      // ── Handle agent_response (regular chat messages) ──────────
      const msgText = parsed.text ?? parsed.content ?? '';
      if (!msgText || !msgText.trim()) return;

      const msgId = parsed.message_id || `agent-${Date.now()}-${Math.random()}`;
      const isVoice = parsed.isVoice ?? false;
      const audioUrl: string | undefined = parsed.audio_url;

      const message: Message = {
        id: msgId,
        text: msgText,
        isUser: false,
        isVoice,
        audioUrl,
        timestamp: new Date().toISOString(),
      };
      dispatch(appendMessage({ cid, message }));
      dispatch(setLoading(false));

      // Auto-play TTS if toggle is on
      if (ttsAutoPlayRef.current && msgText.trim()) {
        if (audioUrl) {
          playAudio(audioUrl);
        } else {
          requestTTS(msgText, cid).then(({ audio_url }) => {
            playAudio(audio_url);
            dispatch(appendMessage({
              cid,
              message: { ...message, audioUrl: audio_url },
            }));
          }).catch(() => {});
        }
      }
    });

    livekitService.onStateChange((state: ConnectionState) => {
      if (state === ConnectionState.Connected) dispatch(setConnectionStatus('connected'));
      else if (state === ConnectionState.Connecting || state === ConnectionState.Reconnecting)
        dispatch(setConnectionStatus('connecting'));
      else dispatch(setConnectionStatus('disconnected'));
    });
  }, [dispatch]);

  // Forward voice call DataChannel events (from separate voice room) into Redux
  useEffect(() => {
    const handleVoiceData = (e: Event) => {
      const { text, topic } = (e as CustomEvent).detail;
      const cid = activeTabCidRef.current;
      if (!cid) return;

      let parsed: any;
      try {
        parsed = JSON.parse(text);
      } catch {
        return;
      }

      if (topic === 'voice.state') {
        const state = parsed.state;
        if (state === 'connected') dispatch(setVoiceCallActive({ active: true, cid }));
        else if (state === 'ended') dispatch(setVoiceCallActive({ active: false }));
        return;
      }

      if (topic === 'voice.activity') {
        dispatch(setVoiceActivity(parsed.state));
        return;
      }

      if (topic === 'voice.user_transcript') {
        if (parsed.is_final && parsed.text) {
          dispatch(setInterimTranscript(null));
          const message: Message = {
            id: parsed.message_id || `voice-user-${Date.now()}`,
            text: parsed.text,
            isUser: true,
            isVoice: true,
            timestamp: new Date().toISOString(),
          };
          dispatch(appendMessage({ cid, message }));
        } else if (parsed.text) {
          dispatch(setInterimTranscript(parsed.text));
        }
        return;
      }

      if (topic === 'voice.agent_transcript') {
        if (parsed.done && parsed.text) {
          const message: Message = {
            id: parsed.message_id || `voice-agent-${Date.now()}`,
            text: parsed.text,
            isUser: false,
            isVoice: true,
            timestamp: new Date().toISOString(),
          };
          dispatch(appendMessage({ cid, message }));
          dispatch(setLoading(false));
        }
        return;
      }

      if (topic === 'voice.interrupted') {
        console.log('[Voice] Agent interrupted by user');
        return;
      }
    };
    window.addEventListener('voice-data', handleVoiceData);
    return () => window.removeEventListener('voice-data', handleVoiceData);
  }, [dispatch]);

  const connectToConversation = useCallback(async (cid: string) => {
    dispatch(setConnectionStatus('connecting'));
    try {
      await livekitService.connect(cid);
    } catch (e: any) {
      console.error('[LiveKit] connect error:', e?.message || e);
      dispatch(setConnectionStatus('disconnected'));
    }
  }, [dispatch]);

  return (
    <LiveKitContext.Provider value={{ connectToConversation }}>
      {children}
    </LiveKitContext.Provider>
  );
}
