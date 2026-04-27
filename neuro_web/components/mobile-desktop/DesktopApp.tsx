'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { Room, RoomEvent, ConnectionState } from 'livekit-client';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  setDesktopConnected, setServerScreenSize,
  clearDesktopModifiers, toggleDesktopModifier,
} from '@/store/mobileDesktopSlice';
import { apiStartDesktopStream, apiGetScreenToken, apiStopDesktopStream } from '@/services/api';
import { DesktopRoomContext } from './DesktopRoomContext';
import { LetterboxContext, LetterboxCtx } from './LetterboxContext';
import DesktopVideoView from './DesktopVideoView';
import ServerCursorOverlay from './ServerCursorOverlay';
import TouchpadOverlay from './TouchpadOverlay';
import TabletTouchOverlay from './TabletTouchOverlay';
import FloatingToolbar from './FloatingToolbar';
import CustomKeyboardSheet from '@/components/keyboard/CustomKeyboardSheet';

const USER_ID = 'desktop-web';

export default function DesktopApp() {
  const dispatch = useAppDispatch();
  const { mode, keyboardOpen, modifiers } = useAppSelector(s => s.mobileDesktop);
  const [room, setRoom] = useState<Room | null>(null);
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);
  const [letterbox, setLetterbox] = useState<LetterboxCtx>({
    offsetX: 0, offsetY: 0, drawW: 1, drawH: 1, containerW: 1, containerH: 1,
  });

  const sendControl = useCallback((payload: object) => {
    if (!room || room.state !== ConnectionState.Connected) return;
    const data = new TextEncoder().encode(JSON.stringify(payload));
    room.localParticipant.publishData(data, { topic: 'mouse_control', reliable: true });
  }, [room]);

  useEffect(() => {
    let cancelled = false;
    let localRoom: Room | null = null;

    async function connect() {
      try {
        await apiStartDesktopStream(USER_ID);
        const { url, token } = await apiGetScreenToken(USER_ID);

        let lkUrl = url;
        if (typeof window !== 'undefined' && window.location.protocol === 'https:' && url.startsWith('ws://')) {
          lkUrl = 'wss://' + url.slice(5);
        }

        localRoom = new Room({ adaptiveStream: true, dynacast: true });

        localRoom.on(RoomEvent.DataReceived, (payload, _p, _k, topic) => {
          if (topic === 'cursor_position') {
            try {
              const msg = JSON.parse(new TextDecoder().decode(payload));
              if (msg.sw && msg.sh) {
                dispatch(setServerScreenSize({ w: msg.sw, h: msg.sh }));
              }
            } catch {}
          }
        });

        localRoom.on(RoomEvent.ConnectionStateChanged, (state) => {
          dispatch(setDesktopConnected(state === ConnectionState.Connected));
        });

        await localRoom.connect(lkUrl, token);
        if (cancelled) { await localRoom.disconnect(); return; }

        setRoom(localRoom);
        dispatch(setDesktopConnected(true));

        if ('wakeLock' in navigator) {
          try {
            wakeLockRef.current = await (navigator as any).wakeLock.request('screen');
          } catch {}
        }
      } catch (e) {
        console.error('[DesktopApp] Connection failed:', e);
      }
    }

    connect();

    return () => {
      cancelled = true;
      wakeLockRef.current?.release().catch(() => {});
      wakeLockRef.current = null;
      localRoom?.disconnect();
      apiStopDesktopStream(USER_ID).catch(() => {});
      dispatch(setDesktopConnected(false));
      dispatch(clearDesktopModifiers());
    };
  }, [dispatch]);

  // Convert active modifiers state to a list of strings used by CustomKeyboard combo logic
  const activeMods = (Object.entries(modifiers) as [string, boolean][])
    .filter(([, v]) => v)
    .map(([k]) => k);

  const handleKeyboardKey = useCallback((combo: string) => {
    sendControl({ type: 'key', key: combo });
  }, [sendControl]);

  return (
    <DesktopRoomContext.Provider value={{ room, sendControl }}>
      <LetterboxContext.Provider value={letterbox}>
        <div
          style={{
            position: 'absolute', inset: 0,
            background: '#000',
            touchAction: 'none',
            userSelect: 'none',
            overflow: 'hidden',
          }}
        >
          <DesktopVideoView room={room} onLetterboxChange={setLetterbox} />
          <ServerCursorOverlay />
          {mode === 'touchpad' ? <TouchpadOverlay /> : <TabletTouchOverlay />}
          <FloatingToolbar />
          <CustomKeyboardSheet
            open={keyboardOpen}
            onKey={handleKeyboardKey}
            modifiers={modifiers}
            onToggleModifier={(m) => dispatch(toggleDesktopModifier(m))}
            onClearModifiers={() => dispatch(clearDesktopModifiers())}
          />
        </div>
      </LetterboxContext.Provider>
    </DesktopRoomContext.Provider>
  );
}
