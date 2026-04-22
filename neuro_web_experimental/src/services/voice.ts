import { api } from './api';

let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

export async function startVoiceRecording(): Promise<void> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
  mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
  mediaRecorder.start();
}

export async function stopVoiceRecording(): Promise<Blob> {
  return new Promise((resolve) => {
    if (!mediaRecorder) { resolve(new Blob()); return; }
    mediaRecorder.onstop = () => {
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      mediaRecorder?.stream.getTracks().forEach(t => t.stop());
      mediaRecorder = null;
      audioChunks = [];
      resolve(blob);
    };
    mediaRecorder.stop();
  });
}

export function isRecording(): boolean {
  return mediaRecorder?.state === 'recording';
}

/** Upload voice message → backend transcribes via Whisper, returns transcription + audio_url */
export async function sendVoiceMessage(
  blob: Blob,
  cid: string,
  agentId?: string,
): Promise<{ message_id: string; transcription: string; audio_url: string }> {
  const form = new FormData();
  form.append('file', blob, 'voice.webm');
  form.append('cid', cid);
  if (agentId) form.append('agent_id', agentId);
  const res = await api.post('/voice-message', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return res.data;
}

/** Request TTS audio for a text, returns {audio_url} */
export async function requestTTS(
  text: string,
  cid: string,
  voice = 'alloy',
): Promise<{ audio_url: string }> {
  const res = await api.post('/tts', { text, cid, voice });
  return res.data;
}

// ---- Playback ----

let currentAudio: HTMLAudioElement | null = null;
let onEndCallback: (() => void) | null = null;

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:7001';

export function playAudio(url: string, onEnd?: () => void): HTMLAudioElement {
  stopAudio();
  const fullUrl = url.startsWith('http') || url.startsWith('blob:') ? url : `${API_BASE}${url}`;
  currentAudio = new Audio(fullUrl);
  onEndCallback = onEnd ?? null;
  currentAudio.onended = () => {
    currentAudio = null;
    onEndCallback?.();
  };
  currentAudio.play().catch(e => console.error('Audio play error:', e));
  return currentAudio;
}

export function stopAudio(): void {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
    currentAudio = null;
  }
}

export function isPlaying(): boolean {
  return currentAudio !== null && !currentAudio.paused;
}
