'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Loader2 } from 'lucide-react';
import { Room, RoomEvent, ConnectionState } from 'livekit-client';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  setDesktopConnected, setServerScreenSize,
  clearDesktopModifiers, toggleDesktopModifier, setKioskActive,
} from '@/store/mobileDesktopSlice';
import { apiStartDesktopStream, apiGetScreenToken, apiStopDesktopStream } from '@/services/api';
import { useIsMobile } from '@/hooks/useIsMobile';
import { DesktopRoomContext } from './DesktopRoomContext';
import { LetterboxContext, LetterboxCtx } from './LetterboxContext';
import { LocalCursorProvider } from './LocalCursorContext';
import DesktopVideoView from './DesktopVideoView';
import ServerCursorOverlay from './ServerCursorOverlay';
import LocalCursorOverlay from './LocalCursorOverlay';
import TouchpadOverlay from './TouchpadOverlay';
import TabletTouchOverlay from './TabletTouchOverlay';
import FloatingToolbar from './FloatingToolbar';
import GlowingBorder from './GlowingBorder';
import TapToConnectOverlay from './TapToConnectOverlay';
import CustomKeyboardSheet from '@/components/keyboard/CustomKeyboardSheet';

const USER_ID = 'desktop-web';

export default function DesktopApp() {
  const dispatch = useAppDispatch();
  const isMobile = useIsMobile();
  const { mode, keyboardOpen, modifiers, displaySwitching, connected, kioskActive } =
    useAppSelector(s => s.mobileDesktop);
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
      // Drop kiosk so the OS chrome (MobileTabStrip etc.) reappears for the
      // next tab/screen the user lands on.
      dispatch(setKioskActive(false));
    };
  }, [dispatch]);

  const handleKeyboardKey = useCallback((combo: string) => {
    sendControl({ type: 'key', key: combo });
  }, [sendControl]);

  // Triggered by TapToConnectOverlay — must run inside a user gesture so the
  // browser allows requestFullscreen() and screen.orientation.lock(). The
  // overlay handles the gesture; we do the privileged work here. Kiosk mode
  // is set BEFORE awaiting fullscreen so the chrome hides instantly even on
  // slow devices / when fullscreen is denied.
  const handleEnterFullscreen = useCallback(async () => {
    dispatch(setKioskActive(true));
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen({ navigationUI: 'hide' } as any);
      }
    } catch {
      // Some browsers (Safari, certain PWA modes) deny fullscreen — kiosk
      // mode still works as a CSS-level full-viewport cover; user can use the
      // toolbar's fullscreen button later if needed.
    }
    try {
      if ('screen' in window && screen.orientation) {
        await (screen.orientation as any).lock?.('landscape');
      }
    } catch {
      // Orientation lock typically requires fullscreen; if fullscreen failed
      // above this will too. Portrait still works, just less optimally.
    }
  }, [dispatch]);

  // Belt-and-braces against Android PWA dropping fullscreen mid-session
  // (status/nav bars sneak back in on some devices when the user taps near
  // the edges or the OS auto-reveals them). While kiosk is active we:
  //   1) Tag <body> with a class so global CSS can hide chrome even if a
  //      Redux race lets a stale render leak through.
  //   2) Re-request fullscreen whenever the browser exits unexpectedly.
  //      This re-request needs a user gesture on most browsers, so we only
  //      do it from a `pointerdown` listener, not eagerly.
  useEffect(() => {
    if (!kioskActive) return;
    document.body.classList.add('desktop-kiosk');

    const reEnterFromGesture = () => {
      if (document.fullscreenElement || !kioskActive) return;
      document.documentElement
        .requestFullscreen({ navigationUI: 'hide' } as any)
        .catch(() => {});
    };
    document.addEventListener('pointerdown', reEnterFromGesture, { capture: true });

    return () => {
      document.body.classList.remove('desktop-kiosk');
      document.removeEventListener('pointerdown', reEnterFromGesture, { capture: true });
    };
  }, [kioskActive]);

  // Outer container — when in kiosk mode we render this through a Portal so
  // it escapes the framer-motion `transform` on the parent Window (which
  // would otherwise trap our `position: fixed` and confine kiosk to the
  // window's bounds). Out of kiosk we stay inline so the desktop tab on
  // wide-screen layouts behaves like any other window.
  const content = (
    <div
      style={{
        position: kioskActive ? 'fixed' : 'absolute',
        inset: 0,
        zIndex: kioskActive ? 9999 : undefined,
        background: '#000',
        touchAction: 'none',
        userSelect: 'none',
        overflow: 'hidden',
      }}
    >
            <DesktopVideoView room={room} onLetterboxChange={setLetterbox} />
            <ServerCursorOverlay />
            {/* Local cursor — fast, immediate response. Hidden in 'none' mode
                because there's nothing for the user to drive. */}
            {mode !== 'none' && <LocalCursorOverlay />}
            {/* Touch overlays — only one is mounted at a time. 'none' mounts
                neither; the user can still scroll the video etc. but no
                input is captured. */}
            {mode === 'touchpad' && <TouchpadOverlay />}
            {mode === 'tablet' && <TabletTouchOverlay />}
            <FloatingToolbar />
            {connected && <GlowingBorder />}
            <CustomKeyboardSheet
              open={keyboardOpen}
              onKey={handleKeyboardKey}
              modifiers={modifiers}
              onToggleModifier={(m) => dispatch(toggleDesktopModifier(m))}
              onClearModifiers={() => dispatch(clearDesktopModifiers())}
            />

            {displaySwitching && (
              <div style={{
                position: 'absolute',
                inset: 0,
                zIndex: 90,
                background: 'rgba(0,0,0,0.55)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                color: '#fff',
                fontSize: 14,
                fontWeight: 500,
                pointerEvents: 'none',
              }}>
                <Loader2 size={18} style={{ animation: 'spin 1s linear infinite' }} />
                Switching display…
                <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
              </div>
            )}

            {isMobile && (
              <TapToConnectOverlay connected={connected} onEnter={handleEnterFullscreen} />
            )}
          </div>
  );

  return (
    <DesktopRoomContext.Provider value={{ room, sendControl }}>
      <LetterboxContext.Provider value={letterbox}>
        <LocalCursorProvider>
          {kioskActive && typeof document !== 'undefined'
            ? createPortal(content, document.body)
            : content}
        </LocalCursorProvider>
      </LetterboxContext.Provider>
    </DesktopRoomContext.Provider>
  );
}
