# Mobile Desktop Streaming — neuro_web (Android Chrome) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-screen remote desktop view at `/mobile/desktop` in neuro_web that mirrors all features of the Kotlin neuro_mobile app: live video, touchpad/tablet pointer modes, custom overlay keyboard, voice typing, floating toolbar, and server cursor.

**Architecture:** Desktop streaming is a regular **app** (like Terminal/IDE) — opens as a tab in the existing window manager. On mobile, windows are already fullscreen-by-default (existing `maximized: isMobile` behavior). A new tabKind `'desktop'` is added; `WindowManager.WindowContent` switch routes it to `<DesktopApp />`. The `CustomKeyboard` component is **shared** between the desktop streaming app and the terminal app — on Android, tapping the terminal input shows the custom keyboard instead of the native Android keyboard (set `inputMode="none"`). All mouse/keyboard events are JSON over LiveKit DataChannel topic `mouse_control` (identical to Kotlin wire format). One new backend endpoint: `/screen/client-token`.

**REVISED 2026-04-27:** Originally planned as `/mobile/desktop` route. Refactored to "app inside window" pattern so it behaves like every other app, supports browser-fullscreen toggle, and integrates with the existing tab/window UX. Custom keyboard moved to shared `components/keyboard/` and reused in Terminal app.

**Tech Stack:** Next.js App Router, `livekit-client@^2.5.7`, `@use-gesture/react@^10.3.1`, `framer-motion@^11.1.7`, Redux Toolkit (existing store), TypeScript.

---

## File Map

**New files:**
```
neurocomputer/server.py                                     — add /screen/client-token endpoint
neuro_web/components/mobile-desktop/DesktopRoomContext.tsx  — room + sendControl context
neuro_web/components/mobile-desktop/LetterboxContext.tsx    — coordinate math context
neuro_web/components/mobile-desktop/DesktopApp.tsx          — connection lifecycle + layout (window content)
neuro_web/components/mobile-desktop/DesktopVideoView.tsx    — <video> + letterbox + zoom
neuro_web/components/mobile-desktop/ServerCursorOverlay.tsx — server cursor dot
neuro_web/components/mobile-desktop/TouchpadOverlay.tsx     — relative pointer + gestures
neuro_web/components/mobile-desktop/TabletTouchOverlay.tsx  — absolute touch mapping
neuro_web/components/mobile-desktop/FloatingToolbar.tsx     — draggable control toolbar (with fullscreen)
neuro_web/components/mobile-desktop/VoiceRecordingPanel.tsx — voice toggle UI
neuro_web/components/keyboard/CustomKeyboard.tsx            — SHARED 6-row custom keyboard
neuro_web/components/keyboard/CustomKeyboardSheet.tsx       — bottom-sheet wrapper (open/close + slide-in)
neuro_web/store/mobileDesktopSlice.ts                       — RTK slice for desktop state
```

**Modified files:**
```
neuro_web/store/index.ts                              — register mobileDesktop reducer
neuro_web/services/api.ts                             — add apiStartDesktopStream, apiGetScreenToken, apiStopDesktopStream
neuro_web/types/index.ts                              — add 'desktop' to TabKind union
neuro_web/components/os/WindowManager.tsx             — add 'desktop' case to WindowContent switch
neuro_web/lib/appRegistry.ts                          — add 'neurodesktop' app entry
neuro_web/app/page.tsx                                — handle 'desktop' tabKind in handleLaunchApp (no cid needed)
neuro_web/store/iconsSlice.ts                         — include 'neurodesktop' in default mobileDock
neuro_web/components/terminal/TerminalInputBar.tsx    — use CustomKeyboardSheet on mobile (suppress native kb)
```

---

## Task 1: Backend — `/screen/client-token` endpoint

**Files:**
- Modify: `neurocomputer/server.py` (near line 1888, after `/screen/start`)

- [ ] **Step 1: Add the endpoint after the `/screen/start` block in server.py**

Find the closing brace of `start_screen_share` (around line 1892) and add immediately after:

```python
@app.post("/screen/client-token")
async def screen_client_token(body: dict):
    """Return a LiveKit client token for the screen room (no voice agent started)."""
    user_id = body.get("user_id", "desktop-web")
    conversation_id = f"voice_{user_id}"
    room_name = f"voice-{conversation_id}"
    identity = f"web-client-{uuid.uuid4().hex[:6]}"
    from core.voice_manager import voice_manager
    token = voice_manager._generate_token(room_name, identity, is_agent=False)
    url = voice_manager._url
    if not url or not token:
        raise HTTPException(status_code=500, detail="LiveKit not configured")
    return {"url": url, "token": token, "room_name": room_name}
```

- [ ] **Step 2: Verify endpoint responds**

```bash
cd /home/ubuntu/neurocomputer
curl -s -X POST http://localhost:7000/screen/client-token \
  -H "Content-Type: application/json" \
  -d '{"user_id":"desktop-web"}' | python3 -m json.tool
```

Expected: JSON with `url`, `token`, `room_name` fields (token is a JWT string).

- [ ] **Step 3: Commit**

```bash
git add neurocomputer/server.py
git commit -m "feat(backend): add /screen/client-token endpoint for web desktop client"
```

---

## Task 2: Redux slice + API helpers

**Files:**
- Create: `neuro_web/store/mobileDesktopSlice.ts`
- Modify: `neuro_web/store/index.ts`
- Modify: `neuro_web/services/api.ts`

- [ ] **Step 1: Create `neuro_web/store/mobileDesktopSlice.ts`**

```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface MobileDesktopState {
  connected: boolean;
  serverScreenW: number;
  serverScreenH: number;
  mode: 'touchpad' | 'tablet';
  keyboardOpen: boolean;
  scrollMode: boolean;
  rotationLocked: boolean;
  modifiers: { ctrl: boolean; alt: boolean; shift: boolean };
}

const initialState: MobileDesktopState = {
  connected: false,
  serverScreenW: 1920,
  serverScreenH: 1080,
  mode: 'touchpad',
  keyboardOpen: false,
  scrollMode: false,
  rotationLocked: false,
  modifiers: { ctrl: false, alt: false, shift: false },
};

const mobileDesktopSlice = createSlice({
  name: 'mobileDesktop',
  initialState,
  reducers: {
    setDesktopConnected(state, action: PayloadAction<boolean>) {
      state.connected = action.payload;
    },
    setServerScreenSize(state, action: PayloadAction<{ w: number; h: number }>) {
      state.serverScreenW = action.payload.w;
      state.serverScreenH = action.payload.h;
    },
    cycleDesktopMode(state) {
      state.mode = state.mode === 'touchpad' ? 'tablet' : 'touchpad';
    },
    setDesktopKeyboardOpen(state, action: PayloadAction<boolean>) {
      state.keyboardOpen = action.payload;
    },
    setScrollMode(state, action: PayloadAction<boolean>) {
      state.scrollMode = action.payload;
    },
    setRotationLocked(state, action: PayloadAction<boolean>) {
      state.rotationLocked = action.payload;
    },
    toggleDesktopModifier(state, action: PayloadAction<'ctrl' | 'alt' | 'shift'>) {
      state.modifiers[action.payload] = !state.modifiers[action.payload];
    },
    clearDesktopModifiers(state) {
      state.modifiers = { ctrl: false, alt: false, shift: false };
    },
  },
});

export const {
  setDesktopConnected, setServerScreenSize, cycleDesktopMode,
  setDesktopKeyboardOpen, setScrollMode, setRotationLocked,
  toggleDesktopModifier, clearDesktopModifiers,
} = mobileDesktopSlice.actions;

export default mobileDesktopSlice.reducer;
```

- [ ] **Step 2: Register reducer in `neuro_web/store/index.ts`**

Add import:
```typescript
import mobileDesktopReducer from './mobileDesktopSlice';
```

Add to `reducer` object in `configureStore`:
```typescript
mobileDesktop: mobileDesktopReducer,
```

- [ ] **Step 3: Add API helpers to `neuro_web/services/api.ts`** (append before last export)

```typescript
// ---- Desktop Streaming ----

export async function apiStartDesktopStream(userId: string = 'desktop-web'): Promise<void> {
  await api.post('/screen/start', { user_id: userId });
}

export async function apiGetScreenToken(userId: string = 'desktop-web'): Promise<{
  url: string; token: string; room_name: string;
}> {
  const res = await api.post('/screen/client-token', { user_id: userId });
  return res.data;
}

export async function apiStopDesktopStream(userId: string = 'desktop-web'): Promise<void> {
  await api.post('/voice/end', { user_id: userId });
}
```

- [ ] **Step 4: Verify TypeScript compiles**

```bash
cd /home/ubuntu/neurocomputer/neuro_web
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors (or only pre-existing errors unrelated to these files).

- [ ] **Step 5: Commit**

```bash
git add neuro_web/store/mobileDesktopSlice.ts neuro_web/store/index.ts neuro_web/services/api.ts
git commit -m "feat(web): RTK slice + API helpers for mobile desktop streaming"
```

---

## Task 3: DesktopRoomContext + LetterboxContext

**Files:**
- Create: `neuro_web/components/mobile-desktop/DesktopRoomContext.tsx`
- Create: `neuro_web/components/mobile-desktop/LetterboxContext.tsx`

- [ ] **Step 1: Create `DesktopRoomContext.tsx`**

```typescript
'use client';
import { createContext, useContext } from 'react';
import type { Room } from 'livekit-client';

export interface DesktopRoomCtx {
  room: Room | null;
  sendControl: (payload: object) => void;
}

export const DesktopRoomContext = createContext<DesktopRoomCtx>({
  room: null,
  sendControl: () => {},
});

export function useDesktopRoom() {
  return useContext(DesktopRoomContext);
}
```

- [ ] **Step 2: Create `LetterboxContext.tsx`**

```typescript
'use client';
import { createContext, useContext } from 'react';

export interface LetterboxCtx {
  offsetX: number;   // px from left edge to video area start
  offsetY: number;   // px from top edge to video area start
  drawW: number;     // rendered video width in px
  drawH: number;     // rendered video height in px
  containerW: number;
  containerH: number;
}

export const LetterboxContext = createContext<LetterboxCtx>({
  offsetX: 0, offsetY: 0, drawW: 1, drawH: 1, containerW: 1, containerH: 1,
});

export function useLetterbox() {
  return useContext(LetterboxContext);
}

/** Compute FitInside letterbox dimensions. */
export function computeLetterbox(
  containerW: number, containerH: number,
  videoW: number, videoH: number
): { offsetX: number; offsetY: number; drawW: number; drawH: number } {
  if (!videoW || !videoH) return { offsetX: 0, offsetY: 0, drawW: containerW, drawH: containerH };
  const containerAR = containerW / containerH;
  const videoAR = videoW / videoH;
  let drawW: number, drawH: number;
  if (videoAR > containerAR) {
    drawW = containerW;
    drawH = containerW / videoAR;
  } else {
    drawH = containerH;
    drawW = containerH * videoAR;
  }
  return {
    offsetX: (containerW - drawW) / 2,
    offsetY: (containerH - drawH) / 2,
    drawW,
    drawH,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/mobile-desktop/
git commit -m "feat(web): DesktopRoomContext + LetterboxContext for mobile desktop"
```

---

## Task 4: Page route + MobileDesktopScreen

**Files:**
- Create: `neuro_web/app/mobile/desktop/page.tsx`
- Create: `neuro_web/components/mobile-desktop/MobileDesktopScreen.tsx`

- [ ] **Step 1: Create `neuro_web/app/mobile/desktop/page.tsx`**

```typescript
import dynamic from 'next/dynamic';

const MobileDesktopScreen = dynamic(
  () => import('@/components/mobile-desktop/MobileDesktopScreen'),
  { ssr: false }
);

export default function MobileDesktopPage() {
  return <MobileDesktopScreen />;
}
```

- [ ] **Step 2: Create `neuro_web/components/mobile-desktop/MobileDesktopScreen.tsx`**

```typescript
'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { Room, RoomEvent, DataPacket_Kind, ConnectionState } from 'livekit-client';
import { useRouter } from 'next/navigation';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  setDesktopConnected, setServerScreenSize, cycleDesktopMode,
  setDesktopKeyboardOpen, setScrollMode, setRotationLocked, clearDesktopModifiers,
} from '@/store/mobileDesktopSlice';
import { apiStartDesktopStream, apiGetScreenToken, apiStopDesktopStream } from '@/services/api';
import { DesktopRoomContext } from './DesktopRoomContext';
import { LetterboxContext, computeLetterbox } from './LetterboxContext';
import DesktopVideoView from './DesktopVideoView';
import ServerCursorOverlay from './ServerCursorOverlay';
import TouchpadOverlay from './TouchpadOverlay';
import TabletTouchOverlay from './TabletTouchOverlay';
import FullKeyboardOverlay from './FullKeyboardOverlay';
import FloatingToolbar from './FloatingToolbar';

const USER_ID = 'desktop-web';

export default function MobileDesktopScreen() {
  const dispatch = useAppDispatch();
  const router = useRouter();
  const { mode, keyboardOpen } = useAppSelector(s => s.mobileDesktop);
  const roomRef = useRef<Room | null>(null);
  const wakeLockRef = useRef<WakeLockSentinel | null>(null);
  const [letterbox, setLetterbox] = useState({
    offsetX: 0, offsetY: 0, drawW: 1, drawH: 1, containerW: 1, containerH: 1,
  });

  const sendControl = useCallback((payload: object) => {
    const room = roomRef.current;
    if (!room || room.state !== ConnectionState.Connected) return;
    const data = new TextEncoder().encode(JSON.stringify(payload));
    room.localParticipant.publishData(data, { topic: 'mouse_control', reliable: true });
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function connect() {
      try {
        await apiStartDesktopStream(USER_ID);
        const { url, token } = await apiGetScreenToken(USER_ID);

        let lkUrl = url;
        if (window.location.protocol === 'https:' && url.startsWith('ws://')) {
          lkUrl = 'wss://' + url.slice(5);
        }

        const room = new Room({ adaptiveStream: true, dynacast: true });
        roomRef.current = room;

        room.on(RoomEvent.DataReceived, (payload: Uint8Array, _p: any, _k: any, topic?: string) => {
          if (topic === 'cursor_position') {
            try {
              const msg = JSON.parse(new TextDecoder().decode(payload));
              if (msg.sw && msg.sh) {
                dispatch(setServerScreenSize({ w: msg.sw, h: msg.sh }));
              }
            } catch {}
          }
        });

        room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
          dispatch(setDesktopConnected(state === ConnectionState.Connected));
        });

        await room.connect(lkUrl, token);
        if (cancelled) { await room.disconnect(); return; }

        dispatch(setDesktopConnected(true));

        // Request wake lock
        if ('wakeLock' in navigator) {
          try {
            wakeLockRef.current = await (navigator as any).wakeLock.request('screen');
          } catch {}
        }
      } catch (e) {
        console.error('[Desktop] Connection failed:', e);
      }
    }

    connect();

    return () => {
      cancelled = true;
      wakeLockRef.current?.release().catch(() => {});
      roomRef.current?.disconnect();
      roomRef.current = null;
      apiStopDesktopStream(USER_ID).catch(() => {});
      dispatch(setDesktopConnected(false));
      dispatch(clearDesktopModifiers());
    };
  }, [dispatch]);

  // Request fullscreen on first tap
  const requestFullscreen = useCallback(() => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(() => {});
    }
  }, []);

  return (
    <DesktopRoomContext.Provider value={{ room: roomRef.current, sendControl }}>
      <LetterboxContext.Provider value={letterbox}>
        <div
          style={{
            position: 'fixed', inset: 0,
            background: '#000',
            touchAction: 'none',
            userSelect: 'none',
            overflow: 'hidden',
          }}
          onClick={requestFullscreen}
        >
          <DesktopVideoView room={roomRef.current} onLetterboxChange={setLetterbox} />
          <ServerCursorOverlay />
          {mode === 'touchpad'
            ? <TouchpadOverlay />
            : <TabletTouchOverlay />
          }
          {keyboardOpen && <FullKeyboardOverlay />}
          <FloatingToolbar onDisconnect={() => router.push('/')} />
        </div>
      </LetterboxContext.Provider>
    </DesktopRoomContext.Provider>
  );
}
```

- [ ] **Step 3: Verify the page route resolves (dev server must be running)**

```bash
cd /home/ubuntu/neurocomputer/neuro_web
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/mobile/desktop
```

Expected: `200` (or `307` redirect to login if auth is required).

- [ ] **Step 4: Commit**

```bash
git add neuro_web/app/mobile/desktop/ neuro_web/components/mobile-desktop/MobileDesktopScreen.tsx
git commit -m "feat(web): /mobile/desktop route + MobileDesktopScreen connection lifecycle"
```

---

## Task 5: DesktopVideoView + ServerCursorOverlay

**Files:**
- Create: `neuro_web/components/mobile-desktop/DesktopVideoView.tsx`
- Create: `neuro_web/components/mobile-desktop/ServerCursorOverlay.tsx`

- [ ] **Step 1: Create `DesktopVideoView.tsx`**

```typescript
'use client';
import { useEffect, useRef } from 'react';
import { Room, RoomEvent, Track, RemoteTrack, RemoteTrackPublication, RemoteParticipant } from 'livekit-client';
import { computeLetterbox, LetterboxCtx } from './LetterboxContext';
import { useAppSelector } from '@/store/hooks';
import { usePinch } from '@use-gesture/react';
import { api } from '@/services/api';

interface Props {
  room: Room | null;
  onLetterboxChange: (lb: LetterboxCtx) => void;
}

const USER_ID = 'desktop-web';

export default function DesktopVideoView({ room, onLetterboxChange }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { serverScreenW, serverScreenH } = useAppSelector(s => s.mobileDesktop);
  const videoSizeRef = useRef({ w: serverScreenW, h: serverScreenH });

  function updateLetterbox() {
    const el = containerRef.current;
    if (!el) return;
    const { offsetWidth: cw, offsetHeight: ch } = el;
    const { w, h } = videoSizeRef.current;
    const lb = computeLetterbox(cw, ch, w, h);
    onLetterboxChange({ ...lb, containerW: cw, containerH: ch });
  }

  useEffect(() => {
    videoSizeRef.current = { w: serverScreenW, h: serverScreenH };
    updateLetterbox();
  }, [serverScreenW, serverScreenH]);

  useEffect(() => {
    if (!room) return;

    function attachTrack(track: RemoteTrack) {
      if (track.kind !== Track.Kind.Video) return;
      if (!videoRef.current) return;
      track.attach(videoRef.current);
      videoRef.current.onloadedmetadata = () => {
        videoSizeRef.current = {
          w: videoRef.current!.videoWidth,
          h: videoRef.current!.videoHeight,
        };
        updateLetterbox();
      };
    }

    room.on(RoomEvent.TrackSubscribed,
      (track: RemoteTrack, _pub: RemoteTrackPublication, _p: RemoteParticipant) => attachTrack(track));

    room.remoteParticipants.forEach(p => {
      p.trackPublications.forEach(pub => {
        if (pub.track) attachTrack(pub.track as RemoteTrack);
      });
    });

    return () => { room.removeAllListeners(RoomEvent.TrackSubscribed); };
  }, [room]);

  useEffect(() => {
    const obs = new ResizeObserver(updateLetterbox);
    if (containerRef.current) obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  const zoomRef = useRef(1);

  usePinch(({ offset: [scale] }) => {
    const zoom = Math.max(1, Math.min(10, scale));
    zoomRef.current = zoom;
    api.post('/screen/view', { user_id: USER_ID, zoom, pan_x: 0.5, pan_y: 0.5 }).catch(() => {});
  }, { target: containerRef });

  return (
    <div
      ref={containerRef}
      style={{ position: 'absolute', inset: 0, background: '#000', touchAction: 'none' }}
    >
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{
          position: 'absolute', inset: 0,
          width: '100%', height: '100%',
          objectFit: 'contain',
        }}
      />
    </div>
  );
}
```

- [ ] **Step 2: Create `ServerCursorOverlay.tsx`**

```typescript
'use client';
import { useEffect, useState } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useLetterbox } from './LetterboxContext';
import { RoomEvent, DataPacket_Kind } from 'livekit-client';

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
        background: 'rgba(255,255,255,0.8)',
        border: '1.5px solid rgba(0,0,0,0.5)',
        pointerEvents: 'none',
        zIndex: 20,
        boxShadow: '0 0 4px rgba(0,0,0,0.4)',
      }}
    />
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/mobile-desktop/DesktopVideoView.tsx \
        neuro_web/components/mobile-desktop/ServerCursorOverlay.tsx
git commit -m "feat(web): DesktopVideoView + ServerCursorOverlay components"
```

---

## Task 6: TouchpadOverlay

**Files:**
- Create: `neuro_web/components/mobile-desktop/TouchpadOverlay.tsx`

- [ ] **Step 1: Create `TouchpadOverlay.tsx`**

```typescript
'use client';
import { useRef, useCallback } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useAppSelector } from '@/store/hooks';

const BASE_SENSITIVITY = 1.0;
const ACCEL_FACTOR = 0.18;
const ACCEL_POWER = 0.65;
const MAX_SENSITIVITY = 12.0;
const PC_SENS = 2.5;
const LONG_PRESS_MS = 500;
const DOUBLE_TAP_MS = 350;
const TAP_CONFIRM_MS = 180;
const MOVE_THRESHOLD_PX = 3;

function applyAccel(delta: number): number {
  const abs = Math.abs(delta);
  const accel = 1 + ACCEL_FACTOR * Math.pow(abs, ACCEL_POWER);
  return Math.sign(delta) * Math.min(abs * accel, abs * MAX_SENSITIVITY) * PC_SENS * BASE_SENSITIVITY;
}

type GestureState = 'idle' | 'potential-tap' | 'dragging' | 'scrolling' | 'dt-drag';

export default function TouchpadOverlay() {
  const { sendControl } = useDesktopRoom();
  const { scrollMode } = useAppSelector(s => s.mobileDesktop);

  const stateRef = useRef<GestureState>('idle');
  const lastPosRef = useRef<{ x: number; y: number } | null>(null);
  const pointerDownPosRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const pointerDownTimeRef = useRef(0);
  const lastTapTimeRef = useRef(0);
  const tapTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pointerIdRef = useRef<number | null>(null);

  const clearTimers = () => {
    if (tapTimerRef.current) { clearTimeout(tapTimerRef.current); tapTimerRef.current = null; }
    if (longPressTimerRef.current) { clearTimeout(longPressTimerRef.current); longPressTimerRef.current = null; }
  };

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (pointerIdRef.current !== null) return; // single-touch only in touchpad mode
    pointerIdRef.current = e.pointerId;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    clearTimers();
    pointerDownPosRef.current = { x: e.clientX, y: e.clientY };
    pointerDownTimeRef.current = Date.now();
    lastPosRef.current = { x: e.clientX, y: e.clientY };

    const isDoubleTap = Date.now() - lastTapTimeRef.current < DOUBLE_TAP_MS;

    if (isDoubleTap) {
      stateRef.current = 'dt-drag';
      sendControl({ type: 'mousedown', button: 'left' });
    } else {
      stateRef.current = 'potential-tap';
      longPressTimerRef.current = setTimeout(() => {
        if (stateRef.current === 'potential-tap') {
          stateRef.current = 'idle';
          sendControl({ type: 'click', button: 'right', count: 1 });
        }
      }, LONG_PRESS_MS);
    }
  }, [sendControl]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    if (!lastPosRef.current) return;

    const dx = e.clientX - lastPosRef.current.x;
    const dy = e.clientY - lastPosRef.current.y;
    const startDist = Math.hypot(
      e.clientX - pointerDownPosRef.current.x,
      e.clientY - pointerDownPosRef.current.y
    );
    lastPosRef.current = { x: e.clientX, y: e.clientY };

    if (stateRef.current === 'potential-tap' && startDist > MOVE_THRESHOLD_PX) {
      clearTimers();
      stateRef.current = scrollMode ? 'scrolling' : 'dragging';
    }

    if (stateRef.current === 'dragging' || stateRef.current === 'dt-drag') {
      if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
      sendControl({ type: 'mouse_move', dx: applyAccel(dx), dy: applyAccel(dy) });
    }

    if (stateRef.current === 'scrolling') {
      sendControl({ type: 'scroll', dy: -dy * 0.08 });
    }
  }, [sendControl, scrollMode]);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    pointerIdRef.current = null;
    clearTimers();

    if (stateRef.current === 'dt-drag') {
      sendControl({ type: 'mouseup', button: 'left' });
      stateRef.current = 'idle';
      return;
    }

    if (stateRef.current === 'potential-tap') {
      const now = Date.now();
      lastTapTimeRef.current = now;
      tapTimerRef.current = setTimeout(() => {
        sendControl({ type: 'click', button: 'left', count: 1 });
      }, TAP_CONFIRM_MS);
    }

    stateRef.current = 'idle';
    lastPosRef.current = null;
  }, [sendControl]);

  return (
    <div
      style={{
        position: 'absolute', inset: 0,
        zIndex: 10,
        touchAction: 'none',
        WebkitUserSelect: 'none',
      }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    />
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/mobile-desktop/TouchpadOverlay.tsx
git commit -m "feat(web): TouchpadOverlay — relative pointer mode with acceleration + gestures"
```

---

## Task 7: TabletTouchOverlay

**Files:**
- Create: `neuro_web/components/mobile-desktop/TabletTouchOverlay.tsx`

- [ ] **Step 1: Create `TabletTouchOverlay.tsx`**

```typescript
'use client';
import { useRef, useCallback } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useLetterbox } from './LetterboxContext';

const LONG_PRESS_MS = 500;
const DOUBLE_TAP_MS = 350;
const MOVE_THRESHOLD_NX = 0.01;

export default function TabletTouchOverlay() {
  const { sendControl } = useDesktopRoom();
  const lb = useLetterbox();
  const lbRef = useRef(lb);
  lbRef.current = lb;

  const lastTapTimeRef = useRef(0);
  const lastTapPosRef = useRef({ nx: 0.5, ny: 0.5 });
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isDraggingRef = useRef(false);
  const pointerDownPosRef = useRef({ nx: 0, ny: 0 });
  const pointerIdRef = useRef<number | null>(null);

  function toNorm(clientX: number, clientY: number) {
    const { offsetX, offsetY, drawW, drawH } = lbRef.current;
    const nx = Math.max(0, Math.min(1, (clientX - offsetX) / drawW));
    const ny = Math.max(0, Math.min(1, (clientY - offsetY) / drawH));
    return { nx, ny };
  }

  const onPointerDown = useCallback((e: React.PointerEvent) => {
    if (pointerIdRef.current !== null) return;
    pointerIdRef.current = e.pointerId;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);

    const { nx, ny } = toNorm(e.clientX, e.clientY);
    pointerDownPosRef.current = { nx, ny };
    isDraggingRef.current = false;

    longPressTimerRef.current = setTimeout(() => {
      sendControl({ type: 'touch_long_press', nx, ny });
    }, LONG_PRESS_MS);
  }, [sendControl]);

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    const { nx, ny } = toNorm(e.clientX, e.clientY);
    const dist = Math.hypot(nx - pointerDownPosRef.current.nx, ny - pointerDownPosRef.current.ny);

    if (!isDraggingRef.current && dist > MOVE_THRESHOLD_NX) {
      if (longPressTimerRef.current) { clearTimeout(longPressTimerRef.current); longPressTimerRef.current = null; }
      isDraggingRef.current = true;
      sendControl({ type: 'touch_drag_start', nx: pointerDownPosRef.current.nx, ny: pointerDownPosRef.current.ny });
    }

    if (isDraggingRef.current) {
      sendControl({ type: 'touch_drag_move', nx, ny });
    }
  }, [sendControl]);

  const onPointerUp = useCallback((e: React.PointerEvent) => {
    if (e.pointerId !== pointerIdRef.current) return;
    pointerIdRef.current = null;
    if (longPressTimerRef.current) { clearTimeout(longPressTimerRef.current); longPressTimerRef.current = null; }

    const { nx, ny } = toNorm(e.clientX, e.clientY);

    if (isDraggingRef.current) {
      sendControl({ type: 'touch_drag_end', nx, ny });
      isDraggingRef.current = false;
      return;
    }

    const now = Date.now();
    const isDouble = now - lastTapTimeRef.current < DOUBLE_TAP_MS;
    lastTapTimeRef.current = now;
    lastTapPosRef.current = { nx, ny };
    sendControl({ type: 'touch_tap', nx, ny, count: isDouble ? 2 : 1 });
  }, [sendControl]);

  return (
    <div
      style={{ position: 'absolute', inset: 0, zIndex: 10, touchAction: 'none', WebkitUserSelect: 'none' }}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
    />
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/mobile-desktop/TabletTouchOverlay.tsx
git commit -m "feat(web): TabletTouchOverlay — absolute touch mapping to desktop coords"
```

---

## Task 8: FullKeyboardOverlay

**Files:**
- Create: `neuro_web/components/mobile-desktop/FullKeyboardOverlay.tsx`

Key naming note: use xdotool-compatible names. Server maps `Enter→Return, Backspace→BackSpace`; sending those directly also works (identity mapping). For modifier combos, join with `+` and send as single key string: `"ctrl+c"`. xdotool parses these as chords.

- [ ] **Step 1: Create `FullKeyboardOverlay.tsx`**

```typescript
'use client';
import { useCallback } from 'react';
import { useDesktopRoom } from './DesktopRoomContext';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { toggleDesktopModifier, clearDesktopModifiers } from '@/store/mobileDesktopSlice';

// xdotool-compatible key names
const ROWS: string[][] = [
  ['F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12'],
  ['grave','1','2','3','4','5','6','7','8','9','0','minus','equal','BackSpace'],
  ['Tab','q','w','e','r','t','y','u','i','o','p','bracketleft','bracketright','backslash'],
  ['Caps_Lock','a','s','d','f','g','h','j','k','l','semicolon','apostrophe','Return'],
  ['shift','z','x','c','v','b','n','m','comma','period','slash','shift'],
  ['ctrl','alt','space','Left','Up','Down','Right','Escape'],
];

const DISPLAY: Record<string, string> = {
  BackSpace: '⌫', Tab: 'Tab', Caps_Lock: 'Caps', Return: '↵',
  shift: 'Shift', ctrl: 'Ctrl', alt: 'Alt', space: 'Space',
  Escape: 'Esc', Left: '←', Right: '→', Up: '↑', Down: '↓',
  grave: '`', minus: '-', equal: '=', bracketleft: '[', bracketright: ']',
  backslash: '\\', semicolon: ';', apostrophe: "'", comma: ',', period: '.', slash: '/',
};

const MODIFIERS = new Set(['ctrl', 'alt', 'shift']);
const WIDE_KEYS = new Set(['BackSpace','Tab','Caps_Lock','Return','space','shift','ctrl','alt','Escape']);

function keyLabel(k: string) { return DISPLAY[k] ?? k.toUpperCase(); }

export default function FullKeyboardOverlay() {
  const { sendControl } = useDesktopRoom();
  const dispatch = useAppDispatch();
  const { modifiers } = useAppSelector(s => s.mobileDesktop);

  const handleKey = useCallback((key: string) => {
    if (MODIFIERS.has(key)) {
      dispatch(toggleDesktopModifier(key as 'ctrl' | 'alt' | 'shift'));
      return;
    }

    const activeMods = (Object.entries(modifiers) as [string, boolean][])
      .filter(([, v]) => v)
      .map(([k]) => k);

    const combo = activeMods.length > 0
      ? [...activeMods, key].join('+')
      : key;

    sendControl({ type: 'key', key: combo });
    dispatch(clearDesktopModifiers());
  }, [sendControl, dispatch, modifiers]);

  return (
    <div style={{
      position: 'absolute', bottom: 0, left: 0, right: 0, zIndex: 30,
      background: 'rgba(18,18,22,0.96)',
      backdropFilter: 'blur(12px)',
      borderTop: '1px solid rgba(255,255,255,0.08)',
      padding: '6px 4px',
      paddingBottom: 'max(env(safe-area-inset-bottom), 6px)',
    }}>
      {/* Modifier pills */}
      <div style={{ display: 'flex', gap: 6, padding: '0 4px 4px', flexWrap: 'wrap' }}>
        {(['ctrl', 'alt', 'shift'] as const).map(mod => (
          <button
            key={mod}
            onPointerDown={e => { e.preventDefault(); handleKey(mod); }}
            style={{
              padding: '3px 10px', borderRadius: 6, fontSize: 11, fontWeight: 600,
              background: modifiers[mod] ? '#6366f1' : 'rgba(255,255,255,0.08)',
              color: modifiers[mod] ? '#fff' : 'rgba(255,255,255,0.7)',
              border: 'none', cursor: 'pointer',
            }}
          >
            {mod.toUpperCase()}
          </button>
        ))}
      </div>

      {ROWS.map((row, ri) => (
        <div key={ri} style={{ display: 'flex', gap: 3, marginBottom: 3, justifyContent: 'center' }}>
          {row.map((key, ki) => (
            <button
              key={ki}
              onPointerDown={e => { e.preventDefault(); handleKey(key); }}
              style={{
                flex: WIDE_KEYS.has(key) ? 2 : 1,
                minWidth: 0,
                height: 34,
                borderRadius: 5,
                background: MODIFIERS.has(key) && modifiers[key as keyof typeof modifiers]
                  ? '#6366f1'
                  : 'rgba(255,255,255,0.1)',
                color: 'rgba(255,255,255,0.9)',
                border: '1px solid rgba(255,255,255,0.06)',
                fontSize: 11,
                fontWeight: 500,
                cursor: 'pointer',
                padding: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              {keyLabel(key)}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/mobile-desktop/FullKeyboardOverlay.tsx
git commit -m "feat(web): FullKeyboardOverlay — 6-row custom keyboard with modifier toggles"
```

---

## Task 9: FloatingToolbar + VoiceRecordingPanel

**Files:**
- Create: `neuro_web/components/mobile-desktop/FloatingToolbar.tsx`
- Create: `neuro_web/components/mobile-desktop/VoiceRecordingPanel.tsx`

- [ ] **Step 1: Create `VoiceRecordingPanel.tsx`**

Voice reuses the existing `useVoiceCall` hook — the hook already opens a separate LiveKit voice room. In the desktop context, it uses the active conversation CID from Redux. Since there may be no open conversation, the hook creates one via `ensure()`.

```typescript
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
```

- [ ] **Step 2: Create `FloatingToolbar.tsx`**

```typescript
'use client';
import { useState, useRef, useCallback } from 'react';
import { useDrag } from '@use-gesture/react';
import { Monitor, TouchpadIcon, Keyboard, Volume2, Minimize2, RotateCw, X } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import {
  cycleDesktopMode, setDesktopKeyboardOpen, setScrollMode, setRotationLocked,
} from '@/store/mobileDesktopSlice';
import VoiceRecordingPanel from './VoiceRecordingPanel';

interface Props {
  onDisconnect: () => void;
}

export default function FloatingToolbar({ onDisconnect }: Props) {
  const dispatch = useAppDispatch();
  const { mode, keyboardOpen, scrollMode, rotationLocked } = useAppSelector(s => s.mobileDesktop);
  const [pos, setPos] = useState({ x: 16, y: 200 });
  const [collapsed, setCollapsed] = useState(false);
  const [showVoice, setShowVoice] = useState(false);
  const toolbarRef = useRef<HTMLDivElement>(null);

  const bind = useDrag(({ offset: [ox, oy] }) => {
    setPos({ x: ox, y: oy });
  }, {
    from: () => [pos.x, pos.y],
    filterTaps: true,
  });

  const btnStyle = (active?: boolean): React.CSSProperties => ({
    width: 36, height: 36, borderRadius: 8,
    background: active ? '#6366f1' : 'rgba(255,255,255,0.1)',
    border: '1px solid rgba(255,255,255,0.08)',
    color: active ? '#fff' : 'rgba(255,255,255,0.8)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    cursor: 'pointer', padding: 0,
  });

  const handleRotationLock = useCallback(async () => {
    const locked = !rotationLocked;
    dispatch(setRotationLocked(locked));
    if ('screen' in window && 'orientation' in (window as any).screen) {
      try {
        if (locked) {
          await (screen.orientation as any).lock('landscape');
        } else {
          screen.orientation.unlock();
        }
      } catch {}
    }
  }, [rotationLocked, dispatch]);

  return (
    <div
      ref={toolbarRef}
      {...bind()}
      style={{
        position: 'absolute',
        left: pos.x,
        top: pos.y,
        zIndex: 40,
        touchAction: 'none',
        userSelect: 'none',
      }}
    >
      <div style={{
        background: 'rgba(14,14,18,0.92)',
        backdropFilter: 'blur(16px)',
        borderRadius: 12,
        border: '1px solid rgba(255,255,255,0.1)',
        padding: 6,
        display: 'flex',
        flexDirection: 'column',
        gap: 5,
        boxShadow: '0 4px 20px rgba(0,0,0,0.5)',
      }}>
        {/* Drag handle */}
        <div style={{
          width: 28, height: 4, borderRadius: 2,
          background: 'rgba(255,255,255,0.2)',
          margin: '0 auto 2px',
          cursor: 'grab',
        }} />

        {!collapsed ? (
          <>
            <button style={btnStyle()} title="Mode" onPointerDown={e => { e.stopPropagation(); dispatch(cycleDesktopMode()); }}>
              {mode === 'touchpad' ? <TouchpadIcon size={16} /> : <Monitor size={16} />}
            </button>
            <button style={btnStyle(scrollMode)} onPointerDown={e => { e.stopPropagation(); dispatch(setScrollMode(!scrollMode)); }}>
              <span style={{ fontSize: 11, fontWeight: 700 }}>SCR</span>
            </button>
            <button style={btnStyle(keyboardOpen)} onPointerDown={e => { e.stopPropagation(); dispatch(setDesktopKeyboardOpen(!keyboardOpen)); }}>
              <Keyboard size={16} />
            </button>
            <button style={btnStyle(showVoice)} onPointerDown={e => { e.stopPropagation(); setShowVoice(v => !v); }}>
              <Volume2 size={16} />
            </button>
            <button style={btnStyle(rotationLocked)} onPointerDown={e => { e.stopPropagation(); handleRotationLock(); }}>
              <RotateCw size={16} />
            </button>
            <button style={btnStyle()} onPointerDown={e => { e.stopPropagation(); onDisconnect(); }}>
              <X size={16} />
            </button>
          </>
        ) : null}

        <button
          style={{ ...btnStyle(), opacity: 0.5 }}
          onPointerDown={e => { e.stopPropagation(); setCollapsed(v => !v); }}
        >
          <Minimize2 size={14} />
        </button>
      </div>

      {showVoice && !collapsed && (
        <div style={{ marginTop: 6 }}>
          <VoiceRecordingPanel />
        </div>
      )}
    </div>
  );
}
```

Note: `TouchpadIcon` may not exist in lucide-react — use `Hand` instead if `TouchpadIcon` is unavailable. Check with:

```bash
node -e "require('lucide-react').TouchpadIcon ? console.log('ok') : console.log('use Hand')"
```

If `TouchpadIcon` is not available, replace `TouchpadIcon` import with `Hand` and update the import line and usage.

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/mobile-desktop/FloatingToolbar.tsx \
        neuro_web/components/mobile-desktop/VoiceRecordingPanel.tsx
git commit -m "feat(web): FloatingToolbar + VoiceRecordingPanel for mobile desktop"
```

---

## Task 10: Wire up — MobileDock + appRegistry

**Files:**
- Modify: `neuro_web/components/os/MobileDock.tsx`

The Desktop launcher bypasses the normal `handleLaunchApp` flow and navigates directly to `/mobile/desktop`. Add it as a special button inside MobileDock.

- [ ] **Step 1: Add Desktop launcher icon to `MobileDock.tsx`**

Add import at top:
```typescript
import { useRouter } from 'next/navigation';
import { Tv2 } from 'lucide-react';
```

Add `const router = useRouter();` inside the `MobileDock` component body (after the existing hooks).

Add the Desktop icon between the left dock icons and the Windows launcher button. In the icon row `<div>`, insert after `{left.map(...)}`:

```tsx
{/* Desktop streaming launcher */}
<div
  onPointerDown={() => {}}
  onPointerUp={() => router.push('/mobile/desktop')}
  style={{
    width: 38, height: 38, borderRadius: 11,
    background: 'linear-gradient(145deg, #1d4ed8ee 0%, #2563eb88 100%)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 2px 6px #1d4ed844',
    cursor: 'pointer',
    flexShrink: 0,
  }}
>
  <Tv2 size={18} color="#fff" strokeWidth={1.8} />
</div>
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd /home/ubuntu/neurocomputer/neuro_web && npx tsc --noEmit 2>&1 | head -30
```

Fix any type errors before proceeding.

- [ ] **Step 3: Check dev server renders the dock icon**

Open `http://localhost:3000` on Android Chrome (or Chrome DevTools mobile emulation). The dock should show a blue TV icon. Tapping it should navigate to `/mobile/desktop`.

- [ ] **Step 4: Commit**

```bash
git add neuro_web/components/os/MobileDock.tsx
git commit -m "feat(web): add Desktop launcher to MobileDock → /mobile/desktop"
```

---

## Task 11: End-to-end smoke test

- [ ] **Step 1: Ensure dev server + neurocomputer backend running**

```bash
# Check backend
curl -s http://localhost:7000/health 2>/dev/null || curl -s http://localhost:7000/ | head -5

# Check frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/mobile/desktop
```

Expected: backend responding, frontend returns 200.

- [ ] **Step 2: Manual test checklist on Android Chrome**

Open `http://<server-ip>:3000` on Android Chrome (same network).

1. **Dock icon** — blue TV icon visible in dock
2. **Navigate** — tap → `/mobile/desktop` loads, black screen with toolbar
3. **Video** — desktop video appears within 3s of page load
4. **Touchpad** — drag finger → desktop cursor moves with acceleration
5. **Tap** — single tap → left click at cursor position
6. **Long press** — hold 500ms without moving → right-click context menu on desktop
7. **Toolbar** — visible, draggable
8. **Mode toggle** — tap mode button → switches touchpad/tablet
9. **Tablet mode** — tap anywhere → click lands at tapped position on desktop
10. **Keyboard** — tap keyboard icon → overlay appears; type 'hello' → appears on desktop
11. **Modifier** — tap Ctrl + tap C → Ctrl+C sent (copies selection if any)
12. **Scroll mode** — toggle scroll → two-finger drag scrolls desktop page
13. **Voice** — tap voice button → request mic permission → speak → transcription to desktop
14. **Server cursor** — cursor dot follows desktop mouse position
15. **Disconnect** — tap X → returns to home screen, stream stops

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat(web): mobile desktop streaming — full Kotlin parity on Android Chrome"
```

---

## Appendix: Lucide icon fallback

If `TouchpadIcon` is missing from installed lucide-react version, replace:
```typescript
import { ..., TouchpadIcon, ... } from 'lucide-react';
// usage: <TouchpadIcon size={16} />
```
with:
```typescript
import { ..., Hand, ... } from 'lucide-react';
// usage: <Hand size={16} />
```
