# Tablet-Mode Remote Access & Orientation Management

**Date:** 2026-04-21
**Status:** Draft — awaiting user review

## Goal

Remote-access a Linux PC from the Android `neuro_mobile_app` so it feels like a native tablet:
1. PC display auto-rotates to match phone's physical orientation.
2. Input is touch-first (absolute taps/drags, 2-finger scroll, client-side pinch-zoom). PC cursor hidden.
3. Rotation-lock button on mobile freezes the display orientation.

Existing stack reused: LiveKit WebRTC video + data channel already carry desktop screen share and mouse events. This feature piggybacks on the same data channel — no new transport.

## Decisions (Q&A)

| # | Decision |
|---|----------|
| Q1 | Rotation-lock button lives on **Android mobile app** only. |
| Q2 | Touch input = **hybrid**: absolute taps/drags as xdotool clicks; pinch-zoom handled client-side (video scale only, no PC-side action); 2-finger scroll → wheel. |
| Q3 | Orientation transport = **reuse LiveKit data channel** (same channel as mouse events). |
| Q4 | Rotation applies to **all connected outputs** (every HDMI-* rotates together). |
| Q5 | Cursor hide = **`xsetroot -cursor_name blank`** w/ `unclutter -idle 0` fallback; restored on session end. |
| Q6 | Sensor cadence = **quantized 4-state machine** on mobile, 300ms debounce, emit on change only; lock = suppress emission. |
| Q7 | On disconnect, PC **restores pre-session orientation + cursor** (snapshot taken at session start). |

Module structure: new `core/display_controller.py` owning xrandr + cursor + lock + snapshot; `core/mouse_controller.py` extended with absolute-touch methods; new `OrientationService.kt` and `TabletTouchOverlay.kt` on Android with a `RotationLockButton` in `DraggableToolbar`.

## Architecture

```
┌──────────── ANDROID ────────────┐          ┌─────────── PC ───────────┐
│ SensorManager (rot_vec)         │          │ desktop_stream.py        │
│   │                             │          │   └ data-chan dispatch ──┐│
│   ▼                             │          │                          ││
│ OrientationService.kt           │          │         ┌────────────────▼│
│   • quantize→4 states           │          │         │ display_ctrl    │
│   • debounce 300ms              │          │         │  xrandr · lock  │
│   • honor lockFlag              │          │         │  snapshot · cur │
│   │                             │          │         └─────────────────│
│   ▼                             │          │                          │
│ LiveKitService.kt ──data chan───┼─WebRTC──▶│ mouse_controller.py      │
│   type:"orientation"            │          │   + handle_touch(...)    │
│   type:"touch"                  │          │                          │
│   type:"session"                │          │                          │
│                                 │          │                          │
│ TabletTouchOverlay + Lock btn   │          │                          │
└─────────────────────────────────┘          └──────────────────────────┘
```

## Data-channel message schemas

All JSON, published on existing LiveKit data channel:

```json
{"type":"session","event":"mobile_connect|mobile_disconnect"}

{"type":"orientation",
 "state":"landscape-left|landscape-right|portrait|portrait-inverted",
 "locked": false}

{"type":"touch",
 "kind":"tap|long_press|drag_start|drag_move|drag_end|scroll",
 "nx": 0.0, "ny": 0.0,  // normalized to streamed video frame (0..1)
 "dy": 0}               // scroll delta, only for kind=scroll
```

Coords are normalized so they remain valid across rotations / resolution changes — PC denormalizes using current `screen_width/height/monitor_offset`, which `desktop_stream` already refreshes on monitor changes.

## Orientation → xrandr mapping

| phone state          | xrandr rotate |
|----------------------|---------------|
| `landscape-left`     | `normal`      |
| `landscape-right`    | `inverted`    |
| `portrait`           | `left`        |
| `portrait-inverted`  | `right`       |

Landscape-held phone (most ergonomic for desktop content) maps to natural horizontal PC layout.

## Components

### `core/display_controller.py` (new)

Public API:
```python
class DisplayController:
    def __init__(self, dry_run: bool = False): ...

    async def session_start(self) -> None:
        """Snapshot current xrandr rotate per output + cursor theme.
           Apply blank cursor. Idempotent guard via _snapshot flag."""

    async def session_end(self) -> None:
        """Restore snapshot. No-op if no session active."""

    async def handle_orientation(self, state: str, locked: bool) -> None:
        """Update lock flag. If !locked and state changed, rotate all outputs."""

    def set_lock(self, locked: bool) -> None: ...

controller = DisplayController()  # module singleton
```

Internal state:
- `_snapshot: dict[output_name, rotate_value] | None`
- `_cursor_snapshot: str | None`
- `_current_state: str | None` — for dedup
- `_locked: bool`
- `_last_rotate_ts: float` — throttle ≥ 250ms between xrandr calls

Rotation impl:
```python
async def _rotate_all_outputs(self, rot: str) -> None:
    for name in self._connected_outputs():          # parse `xrandr --query`
        await _run("xrandr", "--output", name, "--rotate", rot)
    # Re-query dims, push to mouse controller via existing hook:
    from core.desktop_stream import update_mouse_controller_for_monitor
    w, h, off = self._current_monitor_dims()
    update_mouse_controller_for_monitor(w, h, off)
```

Cursor hide/restore:
- hide: `xsetroot -cursor_name blank` (blank Xcursor shipped in most themes; otherwise create `/tmp/neuro_blank.xbm` empty pixmap once and use `-cursor`).
- fallback: `unclutter -idle 0 -root &` (detach PID, kill on restore).
- restore: run `xsetroot -cursor_name <snapshot_name or default_arrow>`, or kill `unclutter` PID.

### `core/mouse_controller.py` (extend)

Add:
```python
async def handle_touch(self, msg: dict) -> None:
    kind = msg["kind"]
    nx, ny = msg.get("nx", 0.0), msg.get("ny", 0.0)
    ax, ay = self._denorm(nx, ny)
    match kind:
        case "tap":        _xdotool("mousemove", str(ax), str(ay)); _xdotool("click", "1")
        case "long_press": _xdotool("mousemove", str(ax), str(ay)); _xdotool("click", "3")
        case "drag_start": _xdotool("mousemove", str(ax), str(ay)); _xdotool("mousedown", "1")
        case "drag_move":  _xdotool("mousemove", str(ax), str(ay))
        case "drag_end":   _xdotool("mousemove", str(ax), str(ay)); _xdotool("mouseup", "1")
        case "scroll":     self._accumulate_scroll(msg.get("dy", 0))

def _denorm(self, nx, ny) -> tuple[int, int]:
    ox, oy = self.monitor_offset
    return int(ox + nx * self.screen_width), int(oy + ny * self.screen_height)
```

Existing relative-move touchpad path (`type:"mouse"`) unchanged. Tablet mode and touchpad mode coexist; mobile decides which msg types to emit. `drag_move` reuses existing 60Hz throttle; taps bypass throttle.

### `desktop_stream.py` (extend data-chan dispatcher)

In the existing data-channel RX loop, add handlers:
```python
elif t == "orientation":
    await display_controller.handle_orientation(m["state"], m.get("locked", False))
elif t == "session":
    if m["event"] == "mobile_connect":    await display_controller.session_start()
    elif m["event"] == "mobile_disconnect": await display_controller.session_end()
elif t == "touch":
    await mouse_controller.handle_touch(m)
```

Also wire `display_controller.session_end()` into the existing LiveKit participant-disconnected handler and into the `_screen_tasks` cancellation path in `server.py` (line ~1836), so force-kill/close paths still restore state.

### `OrientationService.kt` (new Android)

```kotlin
class OrientationService(
    context: Context,
    private val onState: (OrientationState, locked: Boolean) -> Unit,
) : SensorEventListener {
    enum class OrientationState { PORTRAIT, LANDSCAPE_LEFT, LANDSCAPE_RIGHT, PORTRAIT_INVERTED }

    private var locked = false
    private var lastEmitted: OrientationState? = null
    private var pendingState: OrientationState? = null
    private var debounceJob: Job? = null

    fun start() {  // register TYPE_ROTATION_VECTOR, SENSOR_DELAY_UI (~20Hz)
    }
    fun stop() {   // unregister + cancel job
    }
    fun setLock(on: Boolean) {
        locked = on
        // On lock-on: emit final state so PC records locked=true alongside current state.
        lastEmitted?.let { onState(it, on) }
        // On lock-off: nothing; next sensor change fires naturally.
    }

    override fun onSensorChanged(e: SensorEvent) {
        val next = quantize(e.values)
        if (next == lastEmitted || locked) return
        pendingState = next
        debounceJob?.cancel()
        debounceJob = scope.launch {
            delay(300)
            if (pendingState == next && !locked) {
                lastEmitted = next
                onState(next, false)
            }
        }
    }
}
```

`quantize()` uses pitch/roll from rotation vector with ±15° hysteresis band around each flip threshold to prevent chatter near boundaries.

### `LiveKitService.kt` additions

```kotlin
fun sendOrientation(state: OrientationState, locked: Boolean)
fun sendTouch(kind: String, nx: Float, ny: Float, dy: Float = 0f)
fun sendSession(event: String)   // "mobile_connect" | "mobile_disconnect"
```

`sendSession("mobile_connect")` on LiveKit room-join; `"mobile_disconnect"` on `onDisconnected` + app `onStop` (lifecycle-aware).

### `RotationLockButton.kt` (new Android UI)

- Compose icon button placed inside existing `DraggableToolbar` component.
- State hoisted to a `RotationLockState` holder (single source of truth, DI via `NetworkModule`).
- Toggle handler:
  ```kotlin
  rotationLockState.toggle()
  orientationService.setLock(rotationLockState.locked)
  ```
- Visual: locked = filled padlock icon; unlocked = outline.

### `TabletTouchOverlay.kt` (new Android, sibling of `TouchpadOverlay`)

Full-screen Compose overlay on top of the remote video view, shown when `tabletMode = true` (default ON for this feature):

- `detectTapGestures(onTap = ..., onLongPress = ...)` → `sendTouch("tap"|"long_press", nx, ny)`
- `detectDragGestures(onDragStart/onDrag/onDragEnd)` → `drag_start`/`drag_move`/`drag_end`
- `detectTransformGestures` → 2-finger:
  - If primarily scale change → apply `Modifier.graphicsLayer(scaleX=..., scaleY=...)` to local video view (client-side zoom, no PC msg).
  - If primarily pan w/ 2 fingers → `sendTouch("scroll", nx, ny, dy = pan.y)`.

Coords normalized: `nx = offset.x / size.width`, `ny = offset.y / size.height`.

### Mode switch

New settings flag `tabletMode: Boolean` (default `true`). `MainScreen` picks `TabletTouchOverlay` vs legacy `TouchpadOverlay` based on flag. Preserves backwards compat.

## Error handling

- `xrandr` failure → log warn, return. Next state change re-attempts.
- `xsetroot` + `unclutter` both missing → log once, continue without cursor hide. Non-fatal.
- Malformed data-chan msg → dispatcher logs + drops.
- Sensor unavailable → `OrientationService.start()` returns false; UI auto-locks display; touch still works.
- Packet loss on LiveKit data chan → orientation msgs are idempotent (send latest quantized state); loss self-heals on next sensor change.

## Cleanup paths

All must eventually call `DisplayController.session_end()`:
1. `session:mobile_disconnect` msg (normal exit)
2. LiveKit participant-disconnected event in `desktop_stream.py`
3. `/screen/start` cancellation of old task in `server.py`
4. Server shutdown `atexit` hook on `controller`

`session_end` guards on `_snapshot is None` to be idempotent.

**Lock-state edge cases:**
- Lock ON + disconnect → `session_end` still restores pre-session orientation (lock scope = session).
- Lock toggled during sensor transit → in-flight xrandr finishes; subsequent events suppressed.
- App force-killed mid-session → PC's LiveKit disconnect hook is the safety net.

## Testing

New test files:

- `tests/core/test_display_controller.py` (pytest, stub `subprocess.run` via `monkeypatch`):
  - `session_start` → `session_end` round-trips snapshot (xrandr argv asserted)
  - `handle_orientation` w/ `locked=True` → no xrandr call
  - same-state dedup: two `handle_orientation("portrait", False)` → one xrandr invocation
  - all-outputs: two connected outputs → two xrandr calls per rotation
  - `session_end` without prior `session_start` is no-op
  - 250ms throttle suppresses back-to-back rotates within window

- `tests/core/test_mouse_controller_touch.py`:
  - `handle_touch` for each `kind` emits expected xdotool argv
  - `_denorm` correct on multi-monitor offsets (`(1920, 0)` and `(0, 0)`)
  - tap bypasses 60Hz throttle; `drag_move` honors it

- `neuro_mobile_app/.../OrientationServiceTest.kt` (JVM unit test):
  - `quantize()` hysteresis: angle crossing ±15° band doesn't oscillate
  - `setLock(true)` suppresses subsequent `onState` calls
  - debounce: 3 quick transitions within 300ms → 1 emission

Manual E2E checklist (documented in spec):
1. Connect mobile → all PC outputs rotate to match physical orientation.
2. Rotate phone portrait↔landscape → PC follows within 500ms.
3. Toggle lock → rotation freezes; physical rotation does not change PC.
4. Disconnect → PC restores pre-session orientation and cursor.
5. Tap anywhere on streamed video → click lands at matching PC pixel.

## YAGNI — explicitly out of scope

- Per-monitor selective rotation (Q4 = all outputs).
- Server-side sensor smoothing (mobile handles via quantize + debounce).
- Pinch-zoom propagated to PC (client-side video scale only).
- Persistent lock state across sessions.
- Windows/Mac targets (xrandr is Linux-only).
- Forward/back edge gestures.

## Open questions

None at spec-write time. All Q1–Q7 resolved above.
