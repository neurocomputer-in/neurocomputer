'use client';
import { useState, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { appendMessage } from '@/store/conversationSlice';
import { setLoading } from '@/store/chatSlice';
import {
  startVoiceRecording, stopVoiceRecording, sendVoiceMessage,
  requestTTS, playAudio, stopAudio, isPlaying,
} from '@/services/voice';
import { Message } from '@/types';
import { useEnsureConversation } from './useEnsureConversation';

export function useVoice() {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const selectedAgent = useAppSelector(s => s.agent.selectedAgent);
  const { ensure } = useEnsureConversation();
  const [recording, setRecording] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  const startRecording = useCallback(async () => {
    try {
      await startVoiceRecording();
      setRecording(true);
    } catch (e: any) {
      console.error('Mic access denied:', e?.message);
    }
  }, []);

  const stopAndSend = useCallback(async () => {
    // Auto-create a conversation if the user hit the mic from the welcome
    // screen — no separate "New Session" click needed.
    const resolved = await ensure();
    if (!resolved) return;
    const cid = resolved.cid;

    setRecording(false);
    dispatch(setLoading(true));

    try {
      const blob = await stopVoiceRecording();
      if (blob.size === 0) {
        dispatch(setLoading(false));
        return;
      }

      // Show voice message IMMEDIATELY with local audio blob
      const localAudioUrl = URL.createObjectURL(blob);
      const tempId = `voice-${Date.now()}`;
      const userMsg: Message = {
        id: tempId,
        text: 'Transcribing...',
        isUser: true,
        isVoice: true,
        audioUrl: localAudioUrl,
        timestamp: new Date().toISOString(),
      };
      dispatch(appendMessage({ cid, message: userMsg }));

      // Upload → Whisper transcribes → update message text
      const result = await sendVoiceMessage(blob, cid, selectedAgent.type);

      if (result.transcription) {
        // Update the placeholder message with real transcription
        const updatedMsg: Message = {
          id: tempId,
          text: result.transcription,
          isUser: true,
          isVoice: true,
          audioUrl: result.audio_url || localAudioUrl,
          timestamp: userMsg.timestamp,
        };
        dispatch(appendMessage({ cid, message: updatedMsg }));
      }
      // AI response comes via LiveKit DataChannel — loading clears there
    } catch (e: any) {
      console.error('Voice send failed:', e?.message);
      dispatch(setLoading(false));
    }
  }, [ensure, selectedAgent, dispatch]);

  const speakText = useCallback(async (text: string) => {
    if (!activeTabCid || !text.trim()) return;
    try {
      setSpeaking(true);
      const { audio_url } = await requestTTS(text, activeTabCid);
      playAudio(audio_url, () => setSpeaking(false));
    } catch (e: any) {
      console.error('TTS failed:', e?.message);
      setSpeaking(false);
    }
  }, [activeTabCid]);

  const stopSpeaking = useCallback(() => {
    stopAudio();
    setSpeaking(false);
  }, []);

  return {
    recording, speaking,
    startRecording, stopAndSend,
    speakText, stopSpeaking,
    isAudioPlaying: isPlaying,
  };
}
