'use client';
import { useState, useRef } from 'react';
import { Mic, Square, Loader2, X, CornerDownLeft } from 'lucide-react';
import { startVoiceRecording, stopVoiceRecording } from '@/services/voice';
import { apiVoiceType } from '@/services/api';

interface Props {
  onClose: () => void;
}

/**
 * Voice-typing panel — tap mic to start recording, tap again to stop +
 * transcribe + type at the focused desktop window via /voice-type. Toggle
 * the "↵" pill to also press Enter after the transcription is typed (handy
 * for terminal/chat windows on the desktop side).
 *
 * Different from VoiceRecordingPanel which manages a live LiveKit voice call.
 * This is a one-shot transcribe-and-type, modeled on the Kotlin app's
 * voice-typing flow.
 */
export default function VoiceTypingPanel({ onClose }: Props) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pressEnter, setPressEnter] = useState(false);
  const [lastTranscript, setLastTranscript] = useState<string | null>(null);
  // Guard against rapid double-taps that would start a second recorder over the first.
  const busyRef = useRef(false);

  const startRec = async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setError(null);
    setLastTranscript(null);
    try {
      await startVoiceRecording();
      setRecording(true);
    } catch (e: any) {
      setError(e?.message || 'Mic permission denied');
    } finally {
      busyRef.current = false;
    }
  };

  const stopAndType = async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setRecording(false);
    setTranscribing(true);
    try {
      const blob = await stopVoiceRecording();
      if (!blob || blob.size === 0) {
        setTranscribing(false);
        return;
      }
      const r = await apiVoiceType(blob, pressEnter);
      setLastTranscript(r.transcription || '(empty)');
    } catch (e: any) {
      setError(e?.message || 'Transcribe failed');
    } finally {
      setTranscribing(false);
      busyRef.current = false;
    }
  };

  const onMicTap = (e: React.PointerEvent) => {
    e.stopPropagation();
    if (recording) stopAndType();
    else startRec();
  };

  return (
    <div
      onPointerDown={(e) => e.stopPropagation()}
      style={{
        background: 'rgba(18,18,22,0.95)',
        borderRadius: 12,
        padding: 10,
        border: '1px solid rgba(255,255,255,0.1)',
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
        minWidth: 220,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <button
          onPointerDown={onMicTap}
          disabled={transcribing}
          style={{
            flex: '0 0 auto',
            width: 38, height: 38, borderRadius: 10,
            background: recording ? 'rgba(239,68,68,0.25)'
              : transcribing ? 'rgba(94,106,210,0.15)'
              : 'rgba(99,102,241,0.2)',
            border: '1px solid ' + (recording ? 'rgba(239,68,68,0.5)' : 'rgba(99,102,241,0.4)'),
            color: recording ? '#f87171' : transcribing ? '#c4b5fd' : '#a5b4fc',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: transcribing ? 'not-allowed' : 'pointer',
          }}
        >
          {transcribing ? <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
            : recording ? <Square size={14} />
            : <Mic size={16} />}
        </button>

        <div style={{ flex: 1, fontSize: 12, color: '#d0d6e0', lineHeight: 1.3 }}>
          {recording && <span style={{ color: '#f87171' }}>● Recording — tap to type</span>}
          {transcribing && <span style={{ color: '#c4b5fd' }}>Transcribing…</span>}
          {!recording && !transcribing && !error && (
            lastTranscript
              ? <span style={{ color: '#9ae6b4' }}>Typed: {lastTranscript.slice(0, 60)}{lastTranscript.length > 60 ? '…' : ''}</span>
              : <span>Tap mic to dictate</span>
          )}
          {error && <span style={{ color: '#f87171' }}>{error}</span>}
        </div>

        <button
          onPointerDown={(e) => { e.stopPropagation(); onClose(); }}
          style={{
            width: 28, height: 28, borderRadius: 8,
            background: 'transparent', border: 'none',
            color: 'rgba(255,255,255,0.5)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          title="Close"
        >
          <X size={14} />
        </button>
      </div>

      <button
        onPointerDown={(e) => { e.stopPropagation(); setPressEnter(v => !v); }}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          padding: '5px 10px', borderRadius: 7, fontSize: 11,
          background: pressEnter ? 'rgba(99,102,241,0.25)' : 'rgba(255,255,255,0.05)',
          border: '1px solid ' + (pressEnter ? 'rgba(99,102,241,0.5)' : 'rgba(255,255,255,0.08)'),
          color: pressEnter ? '#c4b5fd' : 'rgba(255,255,255,0.6)',
          cursor: 'pointer',
        }}
      >
        <CornerDownLeft size={11} />
        Press Enter after typing {pressEnter ? 'ON' : 'OFF'}
      </button>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
