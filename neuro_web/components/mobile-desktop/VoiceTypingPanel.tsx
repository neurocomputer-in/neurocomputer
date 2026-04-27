'use client';
import { useState, useEffect, useRef } from 'react';
import { Mic, Square, Loader2, X, CornerDownLeft, Send } from 'lucide-react';
import { startVoiceRecording, stopVoiceRecording } from '@/services/voice';
import { apiVoiceType } from '@/services/api';

interface Props {
  onClose: () => void;
}

const fmtMMSS = (ms: number) => {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60).toString().padStart(2, '0');
  const s = (total % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
};

/**
 * Voice typing — prominent floating panel with pulsing red dot, animated
 * waveform bars, and elapsed timer. Mirrors the Kotlin VoiceRecordingPanel
 * UX so the user always knows the recorder state at a glance.
 *
 * Flow (one-shot, matches Kotlin):
 *   idle → tap mic → recording (red pulse + waveform + timer)
 *        → tap "Send" or mic again → transcribing (spinner)
 *        → typed (green confirmation, panel closes)
 *   "Cancel" or "X" abandons the recording without sending.
 *
 * Press-Enter toggle stays accessible — users in terminals/chat windows on
 * the remote PC usually want auto-Enter; users editing a doc don't.
 */
export default function VoiceTypingPanel({ onClose }: Props) {
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pressEnter, setPressEnter] = useState(false);
  const [lastTranscript, setLastTranscript] = useState<string | null>(null);
  const [startTime, setStartTime] = useState<number>(0);
  const [now, setNow] = useState<number>(0);
  const [bars, setBars] = useState<number[]>([0.3, 0.5, 0.4, 0.6, 0.3]);
  const busyRef = useRef(false);

  // Animate timer + waveform while recording.
  useEffect(() => {
    if (!recording) return;
    setNow(Date.now());
    const id = window.setInterval(() => {
      setNow(Date.now());
      setBars(() => Array.from({ length: 5 }, () => 0.2 + Math.random() * 0.8));
    }, 200);
    return () => window.clearInterval(id);
  }, [recording]);

  const startRec = async () => {
    if (busyRef.current) return;
    busyRef.current = true;
    setError(null);
    setLastTranscript(null);
    try {
      await startVoiceRecording();
      setStartTime(Date.now());
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
      // Auto-close 1.2s after success so the user sees the confirmation.
      setTimeout(() => onClose(), 1200);
    } catch (e: any) {
      setError(e?.message || 'Transcribe failed');
    } finally {
      setTranscribing(false);
      busyRef.current = false;
    }
  };

  const cancel = async () => {
    if (recording) {
      try { await stopVoiceRecording(); } catch {}
    }
    onClose();
  };

  const elapsed = recording ? now - startTime : 0;

  return (
    <div
      onPointerDown={(e) => e.stopPropagation()}
      style={{
        background: 'rgba(18,18,22,0.96)',
        borderRadius: 16,
        padding: 18,
        border: '1px solid rgba(255,255,255,0.12)',
        boxShadow: '0 12px 32px rgba(0,0,0,0.6)',
        width: 280,
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
      }}
    >
      {/* Header — pulsing dot + status text */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        {recording ? (
          <>
            <span style={{
              width: 10, height: 10, borderRadius: '50%',
              background: '#ef4444',
              animation: 'voicePulse 0.6s ease-in-out infinite alternate',
              flexShrink: 0,
            }} />
            <span style={{ color: '#fca5a5', fontSize: 13, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
              Recording {fmtMMSS(elapsed)}
            </span>
          </>
        ) : transcribing ? (
          <>
            <Loader2 size={14} color="#c4b5fd" style={{ animation: 'spin 1s linear infinite' }} />
            <span style={{ color: '#c4b5fd', fontSize: 13, fontWeight: 600 }}>Transcribing…</span>
          </>
        ) : lastTranscript ? (
          <>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#22c55e', flexShrink: 0 }} />
            <span style={{ color: '#86efac', fontSize: 13, fontWeight: 600 }}>Typed</span>
          </>
        ) : error ? (
          <>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#ef4444', flexShrink: 0 }} />
            <span style={{ color: '#fca5a5', fontSize: 13, fontWeight: 600 }}>{error}</span>
          </>
        ) : (
          <>
            <Mic size={14} color="#a5b4fc" />
            <span style={{ color: '#d0d6e0', fontSize: 13, fontWeight: 600 }}>Voice typing</span>
          </>
        )}
        <span style={{ flex: 1 }} />
        <button
          onPointerDown={(e) => { e.stopPropagation(); cancel(); }}
          style={{
            width: 28, height: 28, borderRadius: 8,
            background: 'transparent', border: 'none',
            color: 'rgba(255,255,255,0.5)', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}
          title="Cancel"
        >
          <X size={14} />
        </button>
      </div>

      {/* Waveform — only when recording */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, height: 48 }}>
        {recording ? bars.map((h, i) => (
          <div key={i} style={{
            width: 6,
            height: `${Math.max(8, h * 48)}px`,
            background: 'linear-gradient(180deg, #ef4444, #fca5a5)',
            borderRadius: 3,
            transition: 'height 0.18s ease-out',
          }} />
        )) : lastTranscript ? (
          <div style={{
            color: '#d0d6e0', fontSize: 12, lineHeight: 1.4, padding: '0 4px',
            maxHeight: 48, overflow: 'hidden', textAlign: 'center',
          }}>
            {lastTranscript.slice(0, 120)}{lastTranscript.length > 120 ? '…' : ''}
          </div>
        ) : (
          <div style={{ color: '#62666d', fontSize: 12 }}>
            Tap mic to dictate, tap again to send
          </div>
        )}
      </div>

      {/* Big mic / send / record button */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <button
          onPointerDown={(e) => {
            e.stopPropagation();
            if (transcribing) return;
            if (recording) stopAndType();
            else startRec();
          }}
          disabled={transcribing}
          style={{
            width: 64, height: 64, borderRadius: 32,
            background: recording ? '#ef4444'
              : transcribing ? 'rgba(99,102,241,0.2)'
              : '#6366f1',
            border: 'none',
            color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: transcribing ? 'not-allowed' : 'pointer',
            boxShadow: recording
              ? '0 0 0 6px rgba(239,68,68,0.18), 0 6px 16px rgba(239,68,68,0.4)'
              : '0 6px 16px rgba(99,102,241,0.4)',
            transition: 'background 0.2s, box-shadow 0.2s',
          }}
          title={recording ? 'Stop & send' : 'Start recording'}
        >
          {transcribing ? <Loader2 size={24} style={{ animation: 'spin 1s linear infinite' }} />
            : recording ? <Send size={22} />
            : <Mic size={26} />}
        </button>
      </div>

      {/* Press-Enter toggle */}
      <button
        onPointerDown={(e) => { e.stopPropagation(); setPressEnter(v => !v); }}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          padding: '7px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
          background: pressEnter ? 'rgba(34,197,94,0.2)' : 'rgba(255,255,255,0.05)',
          border: '1px solid ' + (pressEnter ? 'rgba(34,197,94,0.5)' : 'rgba(255,255,255,0.08)'),
          color: pressEnter ? '#86efac' : 'rgba(255,255,255,0.6)',
          cursor: 'pointer',
        }}
      >
        <CornerDownLeft size={11} />
        Press Enter after typing: {pressEnter ? 'ON' : 'OFF'}
      </button>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes voicePulse {
          from { transform: scale(1); opacity: 1; }
          to   { transform: scale(1.4); opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
