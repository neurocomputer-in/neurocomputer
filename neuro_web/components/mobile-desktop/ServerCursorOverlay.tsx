'use client';
import { useEffect, useState } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useLetterbox } from './LetterboxContext';
import { RoomEvent } from 'livekit-client';

export default function ServerCursorOverlay() {
  const { room } = useDesktopRoom();
  const lb = useLetterbox();
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);

  useEffect(() => {
    if (!room) return;

    function onData(payload: Uint8Array, _p: any, _k: any, topic?: string) {
      if (topic !== 'cursor_position') return;
      try {
        const msg = JSON.parse(new TextDecoder().decode(payload));
        const left = lb.offsetX + (msg.x ?? 0.5) * lb.drawW;
        const top = lb.offsetY + (msg.y ?? 0.5) * lb.drawH;
        setPos({ left, top });
      } catch {}
    }

    room.on(RoomEvent.DataReceived, onData);
    return () => { room.off(RoomEvent.DataReceived, onData); };
  }, [room, lb]);

  if (!pos) return null;

  return (
    <div
      style={{
        position: 'absolute',
        left: pos.left - 6,
        top: pos.top - 6,
        width: 12,
        height: 12,
        borderRadius: '50%',
        background: 'rgba(255,255,255,0.85)',
        border: '1.5px solid rgba(0,0,0,0.5)',
        pointerEvents: 'none',
        zIndex: 20,
        boxShadow: '0 0 4px rgba(0,0,0,0.4)',
      }}
    />
  );
}
