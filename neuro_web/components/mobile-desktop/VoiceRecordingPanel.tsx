'use client';
import { Mic, MicOff, PhoneOff } from 'lucide-react';
import { useVoiceCall } from '@/hooks/useVoiceCall';

export default function VoiceRecordingPanel() {
  const { startCall, endCall, toggleMute, isActive, isMuted, connecting } = useVoiceCall();

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      background: 'rgba(18,18,22,0.92)',
      borderRadius: 10, padding: '6px 10px',
      border: '1px solid rgba(255,255,255,0.08)',
    }}>
      {!isActive ? (
        <button
          onPointerDown={e => { e.stopPropagation(); startCall(); }}
          disabled={connecting}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            background: '#6366f1', border: 'none', borderRadius: 7,
            color: '#fff', padding: '5px 10px', fontSize: 12,
            cursor: connecting ? 'not-allowed' : 'pointer',
            opacity: connecting ? 0.6 : 1,
          }}
        >
          <Mic size={13} />
          {connecting ? 'Connecting…' : 'Voice'}
        </button>
      ) : (
        <>
          <button
            onPointerDown={e => { e.stopPropagation(); toggleMute(); }}
            style={{
              background: isMuted ? 'rgba(239,68,68,0.2)' : 'rgba(99,102,241,0.2)',
              border: 'none', borderRadius: 7, padding: '5px 8px', cursor: 'pointer',
              color: isMuted ? '#ef4444' : '#6366f1',
            }}
          >
            {isMuted ? <MicOff size={13} /> : <Mic size={13} />}
          </button>
          <button
            onPointerDown={e => { e.stopPropagation(); endCall(); }}
            style={{
              background: 'rgba(239,68,68,0.15)', border: 'none', borderRadius: 7,
              padding: '5px 8px', cursor: 'pointer', color: '#ef4444',
            }}
          >
            <PhoneOff size={13} />
          </button>
        </>
      )}
    </div>
  );
}
