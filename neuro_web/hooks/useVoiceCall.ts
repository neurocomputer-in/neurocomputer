'use client';
import { useState, useCallback, useRef } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setVoiceCallActive, setVoiceCallMuted } from '@/store/chatSlice';
import { apiStartVoiceCall, apiEndVoiceCall } from '@/services/api';
import { useEnsureConversation } from './useEnsureConversation';
import { useActiveCid } from '@/components/os/WindowContext';

export function useVoiceCall() {
  const dispatch = useAppDispatch();
  const paneCid = useActiveCid();
  const globalActiveCid = useAppSelector(s => s.conversations.activeTabCid);
  const activeTabCid = paneCid ?? globalActiveCid;
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const voiceCall = useAppSelector(s => s.chat.voiceCall);
  const interimTranscript = useAppSelector(s => s.chat.interimTranscript);
  const activeTabAgentId = openTabs.find(t => t.cid === activeTabCid)?.agentId ?? 'neuro';
  const { ensure } = useEnsureConversation();

  const [connecting, setConnecting] = useState(false);
  const connectingRef = useRef(false);
  const micStreamRef = useRef<MediaStream | null>(null);
  const agentAudioRef = useRef<HTMLAudioElement | null>(null);

  const startCall = useCallback(async () => {
    // Ref guard catches fast double-clicks and StrictMode re-invocations
    // before React state updates propagate.
    if (connectingRef.current) return;
    if (voiceCall.active) return;
    connectingRef.current = true;
    setConnecting(true);

    // Auto-create a conversation if the user hit Call from the welcome
    // screen — no separate "New Session" click needed.
    const resolved = await ensure();
    if (!resolved) {
      connectingRef.current = false;
      setConnecting(false);
      return;
    }
    const callCid = resolved.cid;
    const callAgentId = resolved.agentId || activeTabAgentId;

    // Show the call panel optimistically so the user sees instant feedback
    // while the backend + LiveKit handshake runs. If setup fails we revert.
    dispatch(setVoiceCallActive({ active: true, cid: callCid }));

    try {
      // Get voice call token from backend (starts AgentSession)
      const result = await apiStartVoiceCall({
        conversationId: callCid,
        agentId: callAgentId,
      });

      // Create a separate LiveKit room for voice (audio tracks)
      // The data-channel room stays connected via livekitService
      const { Room, RoomEvent, Track, createLocalAudioTrack } = await import('livekit-client');
      const voiceRoom = new Room({ adaptiveStream: false, dynacast: false });

      // Handle remote audio (agent TTS)
      voiceRoom.on(RoomEvent.TrackSubscribed, (track: any) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.id = 'voice-call-audio';
          document.body.appendChild(el);
          agentAudioRef.current = el as HTMLAudioElement;
        }
      });
      voiceRoom.on(RoomEvent.TrackUnsubscribed, (track: any) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach().forEach((el: HTMLElement) => el.remove());
        }
      });

      // Forward data messages to the existing handler via CustomEvent
      voiceRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, _p: any, _k: any, topic?: string) => {
        try {
          const text = new TextDecoder().decode(payload);
          const parsed = JSON.parse(text);
          const event = new CustomEvent('voice-data', { detail: { text, topic: topic || parsed.topic } });
          window.dispatchEvent(event);
        } catch {}
      });

      let voiceUrl = result.url;
      if (typeof window !== 'undefined' && window.location.protocol === 'https:' && voiceUrl.startsWith('ws://')) {
        voiceUrl = 'wss://' + voiceUrl.slice(5);
      }

      await voiceRoom.connect(voiceUrl, result.token);

      // Publish local mic audio
      const micTrack = await createLocalAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      });
      await voiceRoom.localParticipant.publishTrack(micTrack);
      micStreamRef.current = micTrack.mediaStream ?? null;

      // Store references for cleanup
      (window as any).__voiceCallRoom = voiceRoom;
      (window as any).__voiceCallMicTrack = micTrack;

      // Redux already flipped to active above; nothing more to do on success.
    } catch (e: any) {
      const name = e?.name || '';
      const raw = e?.message || String(e);
      let friendly = raw;
      if (name === 'NotFoundError' || /not found/i.test(raw)) {
        friendly = 'No microphone found. Plug in a mic (or check your OS audio input) and try again.';
      } else if (name === 'NotAllowedError' || /denied|permission/i.test(raw)) {
        friendly = 'Microphone permission denied. Grant it in your browser/OS settings and retry.';
      } else if (name === 'NotReadableError' || /busy|readable/i.test(raw)) {
        friendly = 'Microphone is busy (another app is using it). Close it and retry.';
      }
      console.error('[VoiceCall] Failed to start:', name, raw, e);
      try { (window as any).__voiceCallLastError = { name, message: raw }; } catch {}
      alert(`Voice call failed: ${friendly}`);
      dispatch(setVoiceCallActive({ active: false }));
    } finally {
      connectingRef.current = false;
      setConnecting(false);
    }
  }, [activeTabAgentId, voiceCall.active, ensure, dispatch]);

  const endCall = useCallback(async () => {
    // Use the cid the call was started on, not the current active tab
    const callCid = voiceCall.cid || activeTabCid;
    if (!callCid) return;

    // Clean up local room
    const voiceRoom = (window as any).__voiceCallRoom;
    const micTrack = (window as any).__voiceCallMicTrack;

    if (micTrack) {
      micTrack.stop();
      (window as any).__voiceCallMicTrack = null;
      micStreamRef.current = null;
      agentAudioRef.current = null;
    }
    if (voiceRoom) {
      await voiceRoom.disconnect();
      (window as any).__voiceCallRoom = null;
    }

    // Remove any lingering audio elements
    document.querySelectorAll('#voice-call-audio').forEach(el => el.remove());

    // Tell backend to end session
    try {
      await apiEndVoiceCall(callCid);
    } catch (e: any) {
      console.error('[VoiceCall] Hangup error:', e?.message);
    }

    dispatch(setVoiceCallActive({ active: false }));
  }, [voiceCall.cid, activeTabCid, dispatch]);

  const toggleMute = useCallback(() => {
    const micTrack = (window as any).__voiceCallMicTrack;
    if (!micTrack) return;

    const newMuted = !voiceCall.muted;
    if (newMuted) {
      micTrack.mute();
    } else {
      micTrack.unmute();
    }
    dispatch(setVoiceCallMuted(newMuted));
  }, [voiceCall.muted, dispatch]);

  return {
    startCall,
    endCall,
    toggleMute,
    connecting,
    isActive: voiceCall.active,
    isMuted: voiceCall.muted,
    startedAt: voiceCall.startedAt,
    interimTranscript,
    micStreamRef,
    agentAudioRef,
  };
}
