'use client';
import { useEffect, useRef, useState } from 'react';
import { PhoneOff, MicOff, Mic, Maximize2 } from 'lucide-react';
import { useVoiceCall } from '@/hooks/useVoiceCall';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setLiveMode } from '@/store/uiSlice';
import { AudioAnalyser } from '@/services/audioAnalyser';
import dynamic from 'next/dynamic';
import FrequencyBars from './FrequencyBars';
import { LiveSession } from './LiveSession';

const VoiceOrb = dynamic(() => import('@/components/three/VoiceOrb'), { ssr: false });

function formatDuration(startedAt: string | null): string {
  if (!startedAt) return '0:00';
  const seconds = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const ACTIVITY_LABELS: Record<string, string> = {
  idle: 'Voice Call Active',
  listening: 'Listening...',
  thinking: 'Thinking...',
  speaking: 'Speaking...',
};

const ACTIVITY_COLORS: Record<string, string> = {
  idle: '#27a644',
  listening: 'var(--accent)',
  thinking: '#f59e0b',
  speaking: 'var(--accent)',
};

export default function VoiceCallPanel() {
  const {
    isActive, isMuted, startedAt, interimTranscript,
    endCall, toggleMute, micStreamRef, agentAudioRef,
  } = useVoiceCall();
  const activity = useAppSelector(s => s.chat.voiceCall.activity);
  const dispatch = useAppDispatch();
  const [duration, setDuration] = useState('0:00');
  const analyserRef = useRef<AudioAnalyser | null>(null);
  const [analyser, setAnalyser] = useState<AudioAnalyser | null>(null);
  const [advancedMode, setAdvancedMode] = useState(false);

  useEffect(() => {
    if (!isActive || !startedAt) return;
    const interval = setInterval(() => setDuration(formatDuration(startedAt)), 1000);
    return () => clearInterval(interval);
  }, [isActive, startedAt]);

  useEffect(() => {
    // If the call ends while live mode was on, clear the flag so page.tsx
    // doesn't keep reserving a narrow column.
    if (!isActive) {
      setAdvancedMode(false);
      dispatch(setLiveMode(false));
    }
  }, [isActive, dispatch]);

  useEffect(() => {
    if (!isActive) {
      analyserRef.current?.dispose();
      analyserRef.current = null;
      setAnalyser(null);
      return;
    }
    if (!analyserRef.current) {
      analyserRef.current = new AudioAnalyser(64);
      setAnalyser(analyserRef.current);
    }
    return () => {
      analyserRef.current?.dispose();
      analyserRef.current = null;
      setAnalyser(null);
    };
  }, [isActive]);

  useEffect(() => {
    const a = analyserRef.current;
    if (!a) return;
    if (activity === 'listening' && micStreamRef.current) {
      a.connectStream(micStreamRef.current);
    } else if (activity === 'speaking' && agentAudioRef.current) {
      a.connectElement(agentAudioRef.current);
    } else {
      a.disconnect();
    }
  }, [activity, micStreamRef, agentAudioRef]);

  if (!isActive) return null;

  const color = ACTIVITY_COLORS[activity] || ACTIVITY_COLORS.idle;
  const label = ACTIVITY_LABELS[activity] || ACTIVITY_LABELS.idle;

  return (
    <div
      style={{
        padding: '6px 24px 0',
        flexShrink: 0,
        display: 'flex',
        justifyContent: 'center',
        animation: 'voicePanelSlideDown 0.25s ease forwards',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '8px 14px',
          width: '100%',
          maxWidth: '1024px',
          boxSizing: 'border-box',
          height: '48px',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: '8px',
        }}
      >
        <VoiceOrb activity={activity} analyser={analyser} size={28} />

        <span style={{
          fontSize: '12px', fontWeight: 510, color,
          transition: 'color 0.3s', flexShrink: 0,
        }}>
          {label}
        </span>
        <span style={{
          fontSize: '11px', color: '#62666d',
          fontFamily: "'Berkeley Mono', ui-monospace, monospace",
          flexShrink: 0,
        }}>
          {duration}
        </span>

        <div style={{ flex: 1, minWidth: 0, height: '14px', display: 'flex', alignItems: 'center' }}>
          <FrequencyBars activity={activity} analyser={analyser} height={14} />
        </div>

        {interimTranscript && (
          <span style={{
            fontSize: '11px', color: '#8a8f98', fontStyle: 'italic',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            maxWidth: '200px', flexShrink: 1,
          }}>
            {interimTranscript}
          </span>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '4px', flexShrink: 0 }}>
          <button
            onClick={() => { setAdvancedMode(true); dispatch(setLiveMode(true)); }}
            style={{
              width: '26px', height: '26px', borderRadius: '50%',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.08)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', transition: 'all 0.15s', padding: 0,
            }}
            title="Advanced Live Mode"
          >
            <Maximize2 size={12} color="#d0d6e0" />
          </button>
          <button
            onClick={toggleMute}
            style={{
              width: '26px', height: '26px', borderRadius: '50%',
              background: isMuted ? 'rgba(239,68,68,0.1)' : 'rgba(255,255,255,0.04)',
              border: isMuted ? '1px solid rgba(239,68,68,0.2)' : '1px solid rgba(255,255,255,0.08)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', transition: 'all 0.15s', padding: 0,
            }}
            title={isMuted ? 'Unmute' : 'Mute'}
          >
            {isMuted ? <MicOff size={12} color="#ef4444" /> : <Mic size={12} color="#d0d6e0" />}
          </button>
          <button
            onClick={endCall}
            style={{
              width: '26px', height: '26px', borderRadius: '50%',
              background: 'rgba(239,68,68,0.15)',
              border: '1px solid rgba(239,68,68,0.25)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', transition: 'all 0.15s', padding: 0,
            }}
            onMouseEnter={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.25)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(239,68,68,0.15)')}
            title="End call"
          >
            <PhoneOff size={12} color="#ef4444" />
          </button>
        </div>
      </div>

      <style>{`
        @keyframes voicePanelSlideDown {
          from { max-height: 0; opacity: 0; }
          to { max-height: 60px; opacity: 1; }
        }
      `}</style>
      
      {advancedMode && (
        <LiveSession
          onClose={() => { setAdvancedMode(false); dispatch(setLiveMode(false)); }}
          onEndCall={() => { setAdvancedMode(false); dispatch(setLiveMode(false)); endCall(); }}
        />
      )}
    </div>
  );
}
