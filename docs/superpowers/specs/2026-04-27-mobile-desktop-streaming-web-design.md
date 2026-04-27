# Mobile Desktop Streaming — neuro_web (Android Chrome)

**Date**: 2026-04-27  
**Target**: Android Chrome only  
**Scope**: Full parity with Kotlin neuro_mobile remote desktop experience

---

## Overview

Add a full-screen remote desktop view to the neuro_web PWA at `/mobile/desktop`. The user taps "Desktop" in the mobile dock, the route auto-connects to the running desktop stream via LiveKit, and presents the full Kotlin app feature set: live video, touchpad/tablet pointer modes, custom overlay keyboard, voice typing, floating toolbar, server cursor, and rotation lock.

No backend changes required — all server-side infrastructure (LiveKit room, `mouse_control` DataChannel topic, `cursor_position` topic, `/screen/start`, `/voice/token`) is already operational.

---

## Route

- **Path**: `/mobile/desktop`
- **Entry point**: `neuro_web/app/mobile/desktop/page.tsx`
- **Fullscreen**: calls `document.documentElement.requestFullscreen()` on first user interaction — hides Chrome address bar
- **Orientation**: default portrait; rotation lock toggle via Screen Orientation API (`screen.orientation.lock('landscape')`/`'portrait'`)
- **Viewport**: `user-scalable=no, viewport-fit=cover` in meta (Android Chrome only — no iOS concerns)
- **Wake Lock**: `navigator.wakeLock.request('screen')` on connect — prevents sleep during session

---

## Architecture

### Component Tree

```
app/mobile/desktop/page.tsx
└── MobileDesktopScreen          # connection lifecycle, mode state, DataChannel bridge
    ├── DesktopVideoView          # <video> el, FitInside letterbox, zoom/pan
    ├── ServerCursorOverlay       # absolute-positioned cursor dot, subscribes cursor_position
    ├── TouchpadOverlay           # default: relative pointer + acceleration (hidden when tablet mode)
    ├── TabletTouchOverlay        # absolute normalized coords (hidden when touchpad mode)
    ├── FullKeyboardOverlay       # 6-row custom keyboard, modifier toggles (shown/hidden via toolbar)
    ├── FloatingToolbar           # draggable, mode cycle, kb toggle, voice btn, rotation lock
    └── VoiceRecordingPanel       # reuses useVoiceCall hook + /voice/token endpoint
```

All files under `neuro_web/components/mobile-desktop/`.

### State — `store/mobileDesktop.ts` (Zustand)

```ts
{
  connected: boolean
  roomName: string | null
  serverScreenW: number       // from cursor_position topic
  serverScreenH: number
  mode: 'touchpad' | 'tablet'
  keyboardOpen: boolean
  scrollMode: boolean         // scroll gesture vs pointer gesture in touchpad mode
  focusMode: boolean          // hides toolbar temporarily
  rotationLocked: boolean
  modifiers: { ctrl: boolean; alt: boolean; shift: boolean }  // auto-clear after non-modifier key
}
```

---

## Video Display — `DesktopVideoView`

- Subscribes to first `VideoTrack` in LiveKit room (published by desktop agent on `/screen/start`)
- Attaches track to `<video>` element via `track.attach(videoEl)`
- **FitInside letterbox**: same math as Kotlin `TabletTouchOverlay` — computes `offsetX/Y, scaleX/Y` from video intrinsic size vs container size. Exposes these as context for overlay coordinate mapping.
- Pinch-to-zoom via `@use-gesture/react` `usePinch` → `POST /screen/view` with `{zoom, pan_x, pan_y}`
- Black letterbox bars fill remaining space (same as Kotlin)

---

## Pointer Input — Touchpad Mode (`TouchpadOverlay`)

Default mode. Full-screen transparent div captures pointer events.

**Constants (ported from Kotlin):**
```ts
BASE_SENSITIVITY = 1.0
ACCEL_FACTOR = 0.18
ACCEL_POWER = 0.65
MAX_SENSITIVITY = 12.0
PC_SENS = 2.5
LONG_PRESS_MS = 500
DOUBLE_TAP_MS = 350
TAP_CONFIRM_MS = 180
MOVE_THRESHOLD_PX = 3
```

**Gesture mapping:**
| Gesture | Message sent |
|---|---|
| Tap (< MOVE_THRESHOLD) | `{type:"direct_click", button:"left", count:1}` after TAP_CONFIRM_MS |
| Double-tap | `{type:"direct_click", button:"left", count:2}` |
| Long-press (no move) | `{type:"direct_click", button:"right", count:1}` |
| Drag | `{type:"direct_move", x, y}` with accel applied to deltas |
| Double-tap-then-drag | mousedown → move → mouseup sequence |
| Two-finger drag (scrollMode) | `{type:"scroll", dx, dy}` |

All events: JSON over LiveKit DataChannel topic `mouse_control`, RELIABLE.

---

## Pointer Input — Tablet Mode (`TabletTouchOverlay`)

Absolute coordinate mapping. Tap position → normalized (0..1) desktop coord using FitInside letterbox math from `DesktopVideoView`.

**Gesture mapping:**
| Gesture | Message sent |
|---|---|
| Single tap | `{type:"touch_tap", nx, ny, count:1}` |
| Double-tap | `{type:"touch_tap", nx, ny, count:2}` |
| Long-press | `{type:"touch_long_press", nx, ny}` |
| Drag start/move/end | `{type:"touch_drag_start/move/end", nx, ny}` |
| Two-finger scroll | `{type:"scroll", nx, ny, dy}` |

---

## Keyboard — `FullKeyboardOverlay`

Custom 6-row layout — avoids Android IME entirely (no soft keyboard = no viewport reflow).

**Rows:**
1. F1–F12
2. ` 1 2 3 4 5 6 7 8 9 0 - = Backspace
3. Tab Q W E R T Y U I O P [ ] \
4. CapsLock A S D F G H J K L ; ' Enter
5. Shift Z X C V B N M , . / Shift
6. Ctrl | Alt | Space | ← ↑ ↓ → | Esc

**Modifier logic:**
- Ctrl/Alt/Shift are toggle buttons — highlight when active
- After any non-modifier key press, all modifiers auto-clear
- Combo string: `{type:"key", key:"c", modifiers:["ctrl"]}` 

**Wire format:**
```json
{"type":"key", "key":"Return", "modifiers":[]}
{"type":"key", "key":"c", "modifiers":["ctrl"]}
```

Shown/hidden via `keyboardOpen` state, toggled from FloatingToolbar.

---

## Floating Toolbar — `FloatingToolbar`

Draggable via `useDrag` from `@use-gesture/react`. Persists position in component state.

**Buttons:**
| Button | Action |
|---|---|
| Mode toggle | cycles touchpad → tablet → touchpad |
| Scroll mode | toggles two-finger scroll in touchpad mode |
| Keyboard | toggles `keyboardOpen` |
| Voice | opens VoiceRecordingPanel |
| Focus | hides toolbar (tap edge to restore) |
| Rotation lock | calls Screen Orientation API |
| Disconnect | closes LiveKit room, navigates back to dock |

Collapses to a drag handle when in focus mode.

---

## Voice Typing — `VoiceRecordingPanel`

Reuses existing `hooks/useVoiceCall.ts` (already wired to `/voice/token` endpoint + LiveKit voice room). No new implementation needed — just render panel UI from FloatingToolbar voice button.

---

## Server Cursor — `ServerCursorOverlay`

Subscribes to `cursor_position` DataChannel topic:
```json
{"x": 0.5, "y": 0.3, "sw": 1920, "sh": 1080}
```
Converts normalized coords through FitInside letterbox math → CSS `left/top` on a 12px dot overlay above the video.

---

## Connection Lifecycle

1. Mount → `POST /screen/start` → receive `{cid, url, token, room_name}`
2. `room.connect(url, token)` with `{adaptiveStream: true, dynacast: true}`
3. Subscribe video track → attach to `<video>`
4. Open DataChannel for `mouse_control` (send) + `cursor_position` (receive)
5. Request Wake Lock + Fullscreen on first user gesture
6. On disconnect/back → `room.disconnect()`, release Wake Lock, release orientation lock

---

## Files

**New files:**
```
neuro_web/app/mobile/desktop/page.tsx
neuro_web/components/mobile-desktop/MobileDesktopScreen.tsx
neuro_web/components/mobile-desktop/DesktopVideoView.tsx
neuro_web/components/mobile-desktop/ServerCursorOverlay.tsx
neuro_web/components/mobile-desktop/TouchpadOverlay.tsx
neuro_web/components/mobile-desktop/TabletTouchOverlay.tsx
neuro_web/components/mobile-desktop/FullKeyboardOverlay.tsx
neuro_web/components/mobile-desktop/FloatingToolbar.tsx
neuro_web/components/mobile-desktop/VoiceRecordingPanel.tsx
neuro_web/store/mobileDesktop.ts
```

**Modified files:**
```
neuro_web/components/os/MobileDock.tsx   — add "Desktop" launcher icon
```

**Backend changes: none.**

---

## Non-Goals

- iOS Safari support
- Clipboard sync / file transfer (not in Kotlin app either)
- Multi-display switching UI (server supports it; can add later)
- Latency / bandwidth indicator UI

---

## Success Criteria

- Video streams and fills screen on Android Chrome
- Touchpad mode moves cursor with natural acceleration matching Kotlin feel
- Tablet mode tap lands within ~5px of intended target
- Custom keyboard sends all keys including F-keys, modifiers, combos
- Voice recording opens, transcription appears in desktop
- Toolbar drags, modes cycle, rotation locks
- Session survives 5+ minutes without memory leak or connection drop
