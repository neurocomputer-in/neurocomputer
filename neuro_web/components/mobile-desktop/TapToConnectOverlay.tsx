'use client';
import { useState } from 'react';
import { Monitor, Maximize } from 'lucide-react';
import { useIsMobile } from '@/hooks/useIsMobile';
import { useAppSelector } from '@/store/hooks';

interface Props {
  /** True once the LiveKit room is connected — switches the button to "Tap to enter". */
  connected: boolean;
  /** Called after the user gesture; do fullscreen-/orientation-API work here. */
  onEnter: () => Promise<void> | void;
}

/**
 * First-mount overlay shown on mobile before the desktop view becomes
 * interactive. Required because requestFullscreen() and screen.orientation.lock()
 * MUST be called from a user-gesture handler — auto-fullscreen on `useEffect`
 * is rejected by every browser. Tapping this overlay provides that gesture.
 *
 * Dismissal is driven by Redux (`kioskActive`) rather than local state because
 * entering kiosk swaps DesktopApp's render path (inline → portal), which
 * unmounts/remounts this component and would wipe a local dismissed flag.
 */
export default function TapToConnectOverlay({ connected, onEnter }: Props) {
  const isMobile = useIsMobile();
  const kioskActive = useAppSelector(s => s.mobileDesktop.kioskActive);
  const [entering, setEntering] = useState(false);

  if (!isMobile || kioskActive) return null;

  const handleTap = async () => {
    if (entering) return;
    setEntering(true);
    // onEnter dispatches setKioskActive(true) — Redux state updates trigger
    // re-render and `kioskActive ? return null` hides this overlay. No need
    // to also track dismissed locally.
    await onEnter();
  };

  return (
    <div
      onPointerDown={(e) => { e.stopPropagation(); handleTap(); }}
      style={{
        position: 'absolute',
        inset: 0,
        zIndex: 100,
        background: 'rgba(8, 9, 10, 0.95)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 18,
        cursor: 'pointer',
        textAlign: 'center',
        padding: 20,
      }}
    >
      <div style={{
        width: 72, height: 72, borderRadius: 18,
        background: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: '1px solid rgba(99,102,241,0.3)',
      }}>
        <Monitor size={32} color="#a5b4fc" />
      </div>
      <div style={{ color: '#f7f8f8', fontSize: 18, fontWeight: 600 }}>
        Remote Desktop
      </div>
      <div style={{ color: '#8a8f98', fontSize: 13, maxWidth: 280, lineHeight: 1.5 }}>
        {connected
          ? 'Tap anywhere to enter fullscreen and start controlling your desktop.'
          : 'Connecting to your desktop…'}
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        background: connected ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
        border: '1px solid ' + (connected ? 'rgba(99,102,241,0.4)' : 'rgba(255,255,255,0.08)'),
        borderRadius: 10, padding: '10px 18px',
        color: connected ? '#c4b5fd' : '#62666d',
        fontSize: 13, fontWeight: 500,
        marginTop: 8,
      }}>
        <Maximize size={14} />
        {entering ? 'Entering fullscreen…' : connected ? 'Tap to start' : 'Connecting…'}
      </div>
    </div>
  );
}
