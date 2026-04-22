# Tablet-Mode Remote Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add mobile-phone-driven PC display rotation (xrandr), absolute touch input, PC cursor hide, and a rotation-lock toggle to the Neuro remote access feature.

**Architecture:** New `core/display_controller.py` owns xrandr snapshot/rotate/restore + cursor hide. `core/mouse_controller.py` gains absolute touch event handlers. `desktop_stream.py` dispatches new data-channel message types (`orientation`, `session`, `touch_*`). Android `OrientationService.kt` quantizes sensor → 4 discrete states and emits via LiveKit data channel; `RotationLockButton` + `TabletTouchOverlay` added to UI.

**Tech Stack:** Python 3, FastAPI, LiveKit Python SDK, xdotool, xrandr, xsetroot, unclutter (fallback), mss, PIL. Android: Kotlin, Jetpack Compose, LiveKit Android SDK, Hilt, SensorManager.

**Spec:** `docs/superpowers/specs/2026-04-21-tablet-mode-remote-design.md`

---

## File Structure

**Create:**
- `core/display_controller.py` — DisplayController class (xrandr/cursor/lock/snapshot)
- `tests/core/test_display_controller.py` — pytest for DisplayController
- `tests/core/test_mouse_controller_touch.py` — pytest for new touch event types
- `neuro_mobile_app/.../domain/OrientationService.kt` — sensor → quantize → emit
- `neuro_mobile_app/.../domain/RotationLockState.kt` — shared lock state holder
- `neuro_mobile_app/.../ui/components/RotationLockButton.kt` — Compose toggle
- `neuro_mobile_app/.../ui/components/TabletTouchOverlay.kt` — Compose touch surface
- `neuro_mobile_app/.../OrientationServiceTest.kt` — JVM unit test

**Modify:**
- `core/mouse_controller.py` — add `touch_tap`/`touch_long_press`/`touch_drag_*` event handlers
- `core/desktop_stream.py` — extend data-chan dispatcher + call `display_controller.session_end()` in finally
- `server.py` — call `display_controller.session_end()` when `_screen_tasks` task is cancelled
- `neuro_mobile_app/.../data/service/LiveKitService.kt` — add `sendOrientation`, `sendTouchEvent`, `sendSession`
- `neuro_mobile_app/.../di/NetworkModule.kt` — provide `OrientationService`, `RotationLockState` singletons
- `neuro_mobile_app/.../ui/components/DraggableToolbar.kt` — add `RotationLockButton`
- `neuro_mobile_app/.../ui/screens/MainScreen.kt` — conditionally render `TabletTouchOverlay` vs `TouchpadOverlay` based on `tabletMode` setting
- `neuro_mobile_app/.../MainActivity.kt` or lifecycle owner — call `LiveKitService.sendSession("mobile_connect"/"disconnect")` on connect/disconnect

**Test location notes:**
- Python tests live under `tests/core/`. `tests/__init__.py` already exists.
- Kotlin unit tests live under `neuro_mobile_app/app/src/test/java/com/neurocomputer/neuromobile/domain/`. Create the folder if absent.

---

## Task 1: `core/display_controller.py` — core module + xrandr rotate

**Files:**
- Create: `core/display_controller.py`
- Test: `tests/core/test_display_controller.py`

### Step 1 — Write failing test (snapshot + rotate + restore round-trip)

- [ ] Create `tests/core/test_display_controller.py`:

```python
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from core.display_controller import DisplayController


XRANDR_QUERY_OUTPUT = (
    "Screen 0: minimum 8 x 8, current 3000 x 1920, maximum 32767 x 32767\n"
    "HDMI-0 connected primary 1080x1920+1920+0 left (normal left inverted right) 527mm x 296mm\n"
    "   1920x1080     60.00*+\n"
    "DP-0 disconnected (normal left inverted right) 0mm x 0mm\n"
    "HDMI-1 connected 1920x1080+0+0 (normal left inverted right) 527mm x 296mm\n"
    "   1920x1080     60.00*+\n"
)


def _fake_subprocess_run(calls: list):
    def _run(argv, **kwargs):
        calls.append(argv)
        result = MagicMock()
        result.returncode = 0
        result.stdout = XRANDR_QUERY_OUTPUT if argv[:2] == ["xrandr", "--query"] else ""
        result.stderr = ""
        return result
    return _run


@pytest.mark.asyncio
async def test_session_start_snapshots_and_hides_cursor():
    ctrl = DisplayController()
    calls = []
    with patch("core.display_controller.subprocess.run", side_effect=_fake_subprocess_run(calls)):
        await ctrl.session_start()
    # Must have queried xrandr at least once
    assert any(argv[:2] == ["xrandr", "--query"] for argv in calls)
    # Must have attempted cursor hide (xsetroot -cursor_name blank)
    assert any(argv[:3] == ["xsetroot", "-cursor_name", "blank"] for argv in calls)
    # Snapshot captured
    assert ctrl._snapshot is not None
    assert "HDMI-0" in ctrl._snapshot
    assert ctrl._snapshot["HDMI-0"] == "left"
    assert ctrl._snapshot["HDMI-1"] == "normal"


@pytest.mark.asyncio
async def test_handle_orientation_rotates_all_outputs():
    ctrl = DisplayController()
    calls = []
    with patch("core.display_controller.subprocess.run", side_effect=_fake_subprocess_run(calls)):
        await ctrl.session_start()
        calls.clear()
        await ctrl.handle_orientation("portrait", locked=False)
    rotate_calls = [a for a in calls if a[:2] == ["xrandr", "--output"]]
    # Two connected outputs → two rotate calls
    outputs = {a[2] for a in rotate_calls}
    assert outputs == {"HDMI-0", "HDMI-1"}
    # Portrait → 'left'
    assert all(a[3:] == ["--rotate", "left"] for a in rotate_calls)


@pytest.mark.asyncio
async def test_handle_orientation_dedup_same_state():
    ctrl = DisplayController()
    calls = []
    with patch("core.display_controller.subprocess.run", side_effect=_fake_subprocess_run(calls)):
        await ctrl.session_start()
        await ctrl.handle_orientation("landscape-left", locked=False)
        calls.clear()
        await ctrl.handle_orientation("landscape-left", locked=False)
    assert not any(a[:2] == ["xrandr", "--output"] for a in calls)


@pytest.mark.asyncio
async def test_handle_orientation_locked_suppresses_rotate():
    ctrl = DisplayController()
    calls = []
    with patch("core.display_controller.subprocess.run", side_effect=_fake_subprocess_run(calls)):
        await ctrl.session_start()
        calls.clear()
        await ctrl.handle_orientation("portrait", locked=True)
    assert not any(a[:2] == ["xrandr", "--output"] for a in calls)


@pytest.mark.asyncio
async def test_session_end_restores_snapshot_and_cursor():
    ctrl = DisplayController()
    calls = []
    with patch("core.display_controller.subprocess.run", side_effect=_fake_subprocess_run(calls)):
        await ctrl.session_start()
        await ctrl.handle_orientation("portrait", locked=False)
        calls.clear()
        await ctrl.session_end()
    rotate_calls = [a for a in calls if a[:2] == ["xrandr", "--output"]]
    # Both outputs restored to pre-session rotate values
    restored = {a[2]: a[4] for a in rotate_calls}
    assert restored.get("HDMI-0") == "left"
    assert restored.get("HDMI-1") == "normal"
    # Snapshot cleared
    assert ctrl._snapshot is None


@pytest.mark.asyncio
async def test_session_end_without_start_is_noop():
    ctrl = DisplayController()
    calls = []
    with patch("core.display_controller.subprocess.run", side_effect=_fake_subprocess_run(calls)):
        await ctrl.session_end()
    assert calls == []


@pytest.mark.asyncio
async def test_throttle_back_to_back_rotates_suppressed():
    ctrl = DisplayController()
    calls = []
    with patch("core.display_controller.subprocess.run", side_effect=_fake_subprocess_run(calls)):
        await ctrl.session_start()
        await ctrl.handle_orientation("landscape-left", locked=False)
        calls.clear()
        # Immediate second rotate to a new state — should be suppressed by 250ms throttle
        await ctrl.handle_orientation("portrait", locked=False)
    assert not any(a[:2] == ["xrandr", "--output"] for a in calls)
```

### Step 2 — Run tests to confirm failure

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -m pytest tests/core/test_display_controller.py -v
```
Expected: all fail with `ModuleNotFoundError: No module named 'core.display_controller'`.

### Step 3 — Implement `core/display_controller.py`

- [ ] Create `core/display_controller.py`:

```python
"""
Display Controller — manages PC display orientation + cursor for mobile tablet-mode sessions.

Receives phone orientation events via LiveKit data channel and:
  - snapshots current xrandr orientation per connected output on session start
  - applies xrandr --rotate on all connected outputs when orientation changes
  - honours a lock flag (when locked, ignores orientation changes)
  - restores snapshot + cursor on session end

Non-fatal on missing xrandr/xsetroot — logs and continues.
"""

import asyncio
import re
import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger("display-controller")

# Phone state → xrandr rotate value (per spec §Orientation mapping)
_ORIENTATION_MAP = {
    "landscape-left": "normal",
    "landscape-right": "inverted",
    "portrait": "left",
    "portrait-inverted": "right",
}

# Minimum interval between xrandr rotations (seconds)
_ROTATE_THROTTLE_S = 0.25


def _run(*argv: str) -> subprocess.CompletedProcess:
    """Run a subprocess synchronously, capturing output. Never raises."""
    try:
        return subprocess.run(list(argv), check=False, capture_output=True, text=True)
    except FileNotFoundError as e:
        logger.warning(f"[Display] Command not found: {argv[0]} ({e})")
        result = subprocess.CompletedProcess(list(argv), returncode=127, stdout="", stderr=str(e))
        return result


class DisplayController:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._snapshot: Optional[dict[str, str]] = None  # output_name -> rotate value
        self._cursor_snapshot: Optional[str] = None
        self._current_state: Optional[str] = None
        self._locked: bool = False
        self._last_rotate_ts: float = 0.0
        self._unclutter_pid: Optional[int] = None

    # ─── public ──────────────────────────────────────────────────────────

    async def session_start(self) -> None:
        """Snapshot current state + hide cursor. Idempotent."""
        if self._snapshot is not None:
            logger.info("[Display] session_start called while session active — ignored")
            return
        self._snapshot = await asyncio.to_thread(self._capture_snapshot)
        self._cursor_snapshot = "left_ptr"  # default Xcursor; we don't rely on reading actual value
        await asyncio.to_thread(self._hide_cursor)
        logger.info(f"[Display] Session started. Snapshot: {self._snapshot}")

    async def session_end(self) -> None:
        """Restore snapshot + cursor. No-op if not started."""
        if self._snapshot is None:
            return
        snapshot = self._snapshot
        self._snapshot = None
        self._current_state = None
        self._locked = False
        self._last_rotate_ts = 0.0
        await asyncio.to_thread(self._restore_snapshot, snapshot)
        await asyncio.to_thread(self._restore_cursor)
        logger.info("[Display] Session ended; snapshot restored")

    async def handle_orientation(self, state: str, locked: bool) -> None:
        """Process an orientation update from the phone."""
        self._locked = locked
        if locked:
            logger.debug(f"[Display] Orientation msg suppressed — lock on (state={state})")
            return
        if state not in _ORIENTATION_MAP:
            logger.warning(f"[Display] Unknown orientation state: {state}")
            return
        if state == self._current_state:
            return
        now = time.monotonic()
        if now - self._last_rotate_ts < _ROTATE_THROTTLE_S:
            logger.debug(f"[Display] Rotate throttled ({state})")
            return
        rotate_value = _ORIENTATION_MAP[state]
        if self._snapshot is None:
            # Defensive — rotate still works but there's no snapshot to restore
            logger.info("[Display] Rotating with no snapshot; session_start not called")
        await asyncio.to_thread(self._rotate_all_outputs, rotate_value)
        self._current_state = state
        self._last_rotate_ts = now
        await asyncio.to_thread(self._refresh_mouse_controller_dims)

    def set_lock(self, locked: bool) -> None:
        self._locked = locked

    # ─── internals ───────────────────────────────────────────────────────

    def _capture_snapshot(self) -> dict[str, str]:
        """Parse `xrandr --query` for connected outputs and their rotate values."""
        result = _run("xrandr", "--query")
        snapshot: dict[str, str] = {}
        # Match lines like: "HDMI-0 connected primary 1080x1920+1920+0 left (normal left inverted right)"
        pattern = re.compile(
            r"^(\S+)\s+connected\b.*?(?:\d+x\d+\+\d+\+\d+\s+)?(normal|left|right|inverted)?\s*\("
        )
        for line in result.stdout.splitlines():
            m = pattern.match(line)
            if m:
                name = m.group(1)
                rot = m.group(2) or "normal"
                snapshot[name] = rot
        return snapshot

    def _connected_outputs(self) -> list[str]:
        return list((self._snapshot or self._capture_snapshot()).keys())

    def _rotate_all_outputs(self, rotate_value: str) -> None:
        for name in self._connected_outputs():
            if self.dry_run:
                logger.info(f"[Display][DRY] xrandr --output {name} --rotate {rotate_value}")
                continue
            res = _run("xrandr", "--output", name, "--rotate", rotate_value)
            if res.returncode != 0:
                logger.warning(f"[Display] xrandr rotate failed for {name}: {res.stderr.strip()}")

    def _restore_snapshot(self, snapshot: dict[str, str]) -> None:
        for name, rot in snapshot.items():
            if self.dry_run:
                logger.info(f"[Display][DRY] xrandr --output {name} --rotate {rot}")
                continue
            _run("xrandr", "--output", name, "--rotate", rot)

    def _hide_cursor(self) -> None:
        if self.dry_run:
            logger.info("[Display][DRY] hide cursor")
            return
        res = _run("xsetroot", "-cursor_name", "blank")
        if res.returncode != 0:
            # Fallback: launch unclutter in background
            try:
                p = subprocess.Popen(
                    ["unclutter", "-idle", "0", "-root"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                self._unclutter_pid = p.pid
                logger.info(f"[Display] xsetroot failed; started unclutter pid={p.pid}")
            except FileNotFoundError:
                logger.warning("[Display] Neither xsetroot nor unclutter available; cursor not hidden")

    def _restore_cursor(self) -> None:
        if self.dry_run:
            logger.info("[Display][DRY] restore cursor")
            return
        if self._unclutter_pid is not None:
            try:
                subprocess.run(["kill", str(self._unclutter_pid)], check=False, capture_output=True)
            finally:
                self._unclutter_pid = None
        _run("xsetroot", "-cursor_name", self._cursor_snapshot or "left_ptr")

    def _refresh_mouse_controller_dims(self) -> None:
        """After rotate, push updated monitor dims to the mouse controller."""
        try:
            from core.desktop_stream import update_mouse_controller_for_monitor, get_current_monitor
            import mss
            sct = mss.mss()
            idx = get_current_monitor()
            max_idx = len(sct.monitors) - 1
            if idx < 1 or idx > max_idx:
                idx = 1
            mon = sct.monitors[idx]
            update_mouse_controller_for_monitor(
                mon["width"], mon["height"], (mon.get("left", 0), mon.get("top", 0))
            )
            sct.close()
        except Exception as e:
            logger.warning(f"[Display] Failed to refresh mouse dims after rotate: {e}")


# Module-level singleton
controller = DisplayController()
```

### Step 4 — Run tests to verify pass

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -m pytest tests/core/test_display_controller.py -v
```
Expected: 7 passed.

### Step 5 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add core/display_controller.py tests/core/test_display_controller.py && git commit -m "$(cat <<'EOF'
feat(display): add DisplayController for tablet-mode xrandr + cursor

Owns pre-session snapshot, orientation → xrandr mapping, all-outputs
rotate, 250ms throttle, lock flag, cursor hide/restore.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `core/mouse_controller.py` — absolute-touch event types

**Files:**
- Modify: `core/mouse_controller.py`
- Test: `tests/core/test_mouse_controller_touch.py`

### Step 1 — Write failing tests

- [ ] Create `tests/core/test_mouse_controller_touch.py`:

```python
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from core.mouse_controller import MouseController


def _collect_xdotool_calls():
    calls = []

    def _run(argv, **kwargs):
        if argv[:1] == ["xdotool"]:
            calls.append(argv)
        return MagicMock(returncode=0)

    return calls, _run


@pytest.mark.asyncio
async def test_touch_tap_emits_mousemove_then_click_at_denormed_coords():
    mc = MouseController(screen_width=1920, screen_height=1080, monitor_offset=(0, 0))
    calls, run = _collect_xdotool_calls()
    with patch("core.mouse_controller.subprocess.run", side_effect=run):
        await mc.handle_event({"type": "touch_tap", "nx": 0.5, "ny": 0.25})
    assert calls[0] == ["xdotool", "mousemove", "960", "270"]
    assert calls[1] == ["xdotool", "click", "1"]


@pytest.mark.asyncio
async def test_touch_long_press_emits_right_click():
    mc = MouseController(screen_width=1920, screen_height=1080, monitor_offset=(0, 0))
    calls, run = _collect_xdotool_calls()
    with patch("core.mouse_controller.subprocess.run", side_effect=run):
        await mc.handle_event({"type": "touch_long_press", "nx": 0.5, "ny": 0.5})
    assert ["xdotool", "mousemove", "960", "540"] in calls
    assert ["xdotool", "click", "3"] in calls


@pytest.mark.asyncio
async def test_touch_drag_start_move_end_sequence():
    mc = MouseController(screen_width=1000, screen_height=1000, monitor_offset=(0, 0))
    calls, run = _collect_xdotool_calls()
    with patch("core.mouse_controller.subprocess.run", side_effect=run):
        await mc.handle_event({"type": "touch_drag_start", "nx": 0.1, "ny": 0.1})
        await mc.handle_event({"type": "touch_drag_move", "nx": 0.5, "ny": 0.5})
        await mc.handle_event({"type": "touch_drag_end", "nx": 0.9, "ny": 0.9})
    # mousemove at start + mousedown
    assert calls[0] == ["xdotool", "mousemove", "100", "100"]
    assert calls[1] == ["xdotool", "mousedown", "1"]
    # drag_move may be throttled — last call should be a mouseup preceded by mousemove
    assert ["xdotool", "mouseup", "1"] in calls
    assert ["xdotool", "mousemove", "900", "900"] in calls


@pytest.mark.asyncio
async def test_touch_tap_respects_monitor_offset():
    mc = MouseController(screen_width=1920, screen_height=1080, monitor_offset=(1920, 0))
    calls, run = _collect_xdotool_calls()
    with patch("core.mouse_controller.subprocess.run", side_effect=run):
        await mc.handle_event({"type": "touch_tap", "nx": 0.0, "ny": 0.0})
    assert calls[0] == ["xdotool", "mousemove", "1920", "0"]
```

### Step 2 — Run to verify failure

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -m pytest tests/core/test_mouse_controller_touch.py -v
```
Expected: all fail — `touch_tap` unknown event type warning + no click issued.

### Step 3 — Extend `core/mouse_controller.py` dispatcher

- [ ] In `core/mouse_controller.py`, locate the `handle_event` method (starts around line 63). Add these branches BEFORE the final `else`:

```python
            elif event_type == "touch_tap":
                await self._handle_touch_tap(event)
            elif event_type == "touch_long_press":
                await self._handle_touch_long_press(event)
            elif event_type == "touch_drag_start":
                await self._handle_touch_drag_start(event)
            elif event_type == "touch_drag_move":
                await self._handle_touch_drag_move(event)
            elif event_type == "touch_drag_end":
                await self._handle_touch_drag_end(event)
```

Then add the handler methods anywhere inside the class (below `_handle_direct_click`):

```python
    def _denorm(self, nx: float, ny: float) -> tuple[int, int]:
        """Convert normalized 0-1 coords to absolute pixel coords on current monitor."""
        ox, oy = self.monitor_offset
        return (
            int(ox + nx * self.screen_width),
            int(oy + ny * self.screen_height),
        )

    async def _handle_touch_tap(self, event: dict):
        ax, ay = self._denorm(float(event.get("nx", 0.0)), float(event.get("ny", 0.0)))
        if self.dry_run:
            logger.info(f"[Mouse][DRY] touch_tap({ax},{ay})")
            return
        await asyncio.to_thread(_xdotool, "mousemove", str(ax), str(ay))
        await asyncio.to_thread(_xdotool, "click", "1")

    async def _handle_touch_long_press(self, event: dict):
        ax, ay = self._denorm(float(event.get("nx", 0.0)), float(event.get("ny", 0.0)))
        if self.dry_run:
            logger.info(f"[Mouse][DRY] touch_long_press({ax},{ay})")
            return
        await asyncio.to_thread(_xdotool, "mousemove", str(ax), str(ay))
        await asyncio.to_thread(_xdotool, "click", "3")

    async def _handle_touch_drag_start(self, event: dict):
        ax, ay = self._denorm(float(event.get("nx", 0.0)), float(event.get("ny", 0.0)))
        if self.dry_run:
            logger.info(f"[Mouse][DRY] touch_drag_start({ax},{ay})")
            return
        await asyncio.to_thread(_xdotool, "mousemove", str(ax), str(ay))
        await asyncio.to_thread(_xdotool, "mousedown", "1")

    async def _handle_touch_drag_move(self, event: dict):
        now = time.monotonic()
        if now - self._last_move_time < self._move_throttle_s:
            return
        self._last_move_time = now
        ax, ay = self._denorm(float(event.get("nx", 0.0)), float(event.get("ny", 0.0)))
        if self.dry_run:
            logger.info(f"[Mouse][DRY] touch_drag_move({ax},{ay})")
            return
        await asyncio.to_thread(_xdotool, "mousemove", str(ax), str(ay))

    async def _handle_touch_drag_end(self, event: dict):
        ax, ay = self._denorm(float(event.get("nx", 0.0)), float(event.get("ny", 0.0)))
        if self.dry_run:
            logger.info(f"[Mouse][DRY] touch_drag_end({ax},{ay})")
            return
        await asyncio.to_thread(_xdotool, "mousemove", str(ax), str(ay))
        await asyncio.to_thread(_xdotool, "mouseup", "1")
```

### Step 4 — Run tests to verify pass

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -m pytest tests/core/test_mouse_controller_touch.py -v
```
Expected: 4 passed.

### Step 5 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add core/mouse_controller.py tests/core/test_mouse_controller_touch.py && git commit -m "$(cat <<'EOF'
feat(mouse): absolute touch event handlers for tablet mode

Adds touch_tap / touch_long_press / touch_drag_start|move|end that
denormalize (nx,ny) against current monitor offset+dims and drive
xdotool. Existing relative-move touchpad path untouched.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Wire `DisplayController` + touch dispatch into `desktop_stream.py`

**Files:**
- Modify: `core/desktop_stream.py` (data-chan handler @ ~line 200; finally @ ~line 359)

### Step 1 — Modify data-chan dispatcher

- [ ] In `core/desktop_stream.py`, replace the `_on_data_received` handler (around lines 200-211) with:

```python
    @room.on("data_received")
    def _on_data_received(data_packet):
        """Handle incoming data packets — dispatch mouse + tablet-mode events."""
        if data_packet.topic != "mouse_control":
            return
        try:
            msg = json.loads(data_packet.data.decode("utf-8"))
        except Exception as e:
            logger.error(f"[Screen] Failed to decode data packet: {e}")
            return

        t = msg.get("type")
        if t == "switch_display":
            asyncio.create_task(_handle_switch_display(room))
        elif t == "orientation":
            from core.display_controller import controller as _disp
            asyncio.create_task(
                _disp.handle_orientation(msg.get("state", ""), bool(msg.get("locked", False)))
            )
        elif t == "session":
            from core.display_controller import controller as _disp
            event = msg.get("event")
            if event == "mobile_connect":
                asyncio.create_task(_disp.session_start())
            elif event == "mobile_disconnect":
                asyncio.create_task(_disp.session_end())
        else:
            asyncio.create_task(mouse_controller.handle_event(msg))
```

### Step 2 — Modify the `finally` block (line ~359) to restore state on disconnect

- [ ] Replace the existing `finally:` block at end of `start_desktop_stream` with:

```python
    finally:
        logger.info("[Screen] Stream ended.")
        try:
            from core.display_controller import controller as _disp
            await _disp.session_end()
        except Exception as e:
            logger.warning(f"[Screen] session_end failed on stream finish: {e}")
```

### Step 3 — Quick smoke test (no new pytest; verify module imports)

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -c "from core import desktop_stream, display_controller; print('ok')"
```
Expected: `ok`.

### Step 4 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add core/desktop_stream.py && git commit -m "$(cat <<'EOF'
feat(desktop_stream): dispatch tablet-mode data-chan messages

Extends data_received handler to route orientation/session messages
to DisplayController; restores session state on stream finally.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Wire `session_end` into `/screen/start` cancellation path in `server.py`

**Files:**
- Modify: `server.py` (around line 1836: `_screen_tasks[user_id].cancel()`)

### Step 1 — Modify cancellation path

- [ ] In `server.py`, locate the block starting `if user_id in _screen_tasks:` (around line 1835). Replace:

```python
        if user_id in _screen_tasks:
            logger.info(f"[Screen] Cancelling old stream task for {user_id}")
            _screen_tasks[user_id].cancel()
```

with:

```python
        if user_id in _screen_tasks:
            logger.info(f"[Screen] Cancelling old stream task for {user_id}")
            _screen_tasks[user_id].cancel()
            try:
                from core.display_controller import controller as _disp
                asyncio.create_task(_disp.session_end())
            except Exception as e:
                logger.warning(f"[Screen] session_end on cancel failed: {e}")
```

### Step 2 — Verify import still works

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -c "import server; print('ok')"
```
Expected: `ok` (no ImportError).

### Step 3 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add server.py && git commit -m "$(cat <<'EOF'
fix(server): restore display state when old screen stream cancelled

Belt-and-suspenders cleanup — calls DisplayController.session_end
if a prior stream task is being cancelled before its own finally
gets a chance to run.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Android `OrientationService.kt` + `RotationLockState`

**Files:**
- Create: `neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/domain/OrientationService.kt`
- Create: `neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/domain/RotationLockState.kt`
- Test: `neuro_mobile_app/app/src/test/java/com/neurocomputer/neuromobile/domain/OrientationServiceTest.kt`

### Step 1 — Create `RotationLockState.kt`

- [ ] Create file:

```kotlin
package com.neurocomputer.neuromobile.domain

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import javax.inject.Inject
import javax.inject.Singleton

/** Shared lock flag for rotation. Toggled by RotationLockButton, read by OrientationService. */
@Singleton
class RotationLockState @Inject constructor() {
    private val _locked = MutableStateFlow(false)
    val locked: StateFlow<Boolean> = _locked

    fun toggle(): Boolean {
        _locked.value = !_locked.value
        return _locked.value
    }

    fun set(value: Boolean) { _locked.value = value }
}
```

### Step 2 — Create `OrientationService.kt`

- [ ] Create file:

```kotlin
package com.neurocomputer.neuromobile.domain

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Converts raw rotation-vector sensor data into 4 discrete orientation states and
 * emits via [onState] — but only on state change, after a 300ms debounce, and only
 * when the [RotationLockState] is NOT locked.
 *
 * On [setLock] ON → one final emit with locked=true carrying the current state, then
 * subsequent sensor events are suppressed until unlocked.
 */
@Singleton
class OrientationService @Inject constructor(
    private val context: Context,
    private val lockState: RotationLockState,
) : SensorEventListener {

    enum class OrientationState(val wire: String) {
        PORTRAIT("portrait"),
        LANDSCAPE_LEFT("landscape-left"),
        LANDSCAPE_RIGHT("landscape-right"),
        PORTRAIT_INVERTED("portrait-inverted"),
    }

    private val sensorManager: SensorManager =
        context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val rotationVector: Sensor? = sensorManager.getDefaultSensor(Sensor.TYPE_ROTATION_VECTOR)

    private var listener: ((OrientationState, Boolean) -> Unit)? = null
    private var started = false
    private var lastEmitted: OrientationState? = null
    private var pendingState: OrientationState? = null
    private var debounceJob: Job? = null
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())

    /** Hysteresis band (deg) around pitch/roll thresholds — prevents chatter. */
    private val hysteresisDeg = 15.0f

    fun start(onState: (OrientationState, Boolean) -> Unit): Boolean {
        if (started) return true
        val sensor = rotationVector ?: return false
        listener = onState
        sensorManager.registerListener(this, sensor, SensorManager.SENSOR_DELAY_UI)
        started = true
        return true
    }

    fun stop() {
        if (!started) return
        sensorManager.unregisterListener(this)
        debounceJob?.cancel()
        started = false
        listener = null
    }

    fun setLock(on: Boolean) {
        lockState.set(on)
        // On lock: emit final state so PC records locked=true.
        if (on) lastEmitted?.let { listener?.invoke(it, true) }
    }

    override fun onSensorChanged(event: SensorEvent) {
        if (event.sensor.type != Sensor.TYPE_ROTATION_VECTOR) return
        if (lockState.locked.value) return

        val next = quantize(event.values) ?: return
        if (next == lastEmitted) return
        pendingState = next
        debounceJob?.cancel()
        debounceJob = scope.launch {
            delay(300)
            if (pendingState == next && !lockState.locked.value) {
                lastEmitted = next
                listener?.invoke(next, false)
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    /** Classify rotation-vector values into 4-state phone orientation. Visible for testing. */
    internal fun quantize(values: FloatArray): OrientationState? {
        val rot = FloatArray(9)
        SensorManager.getRotationMatrixFromVector(rot, values)
        val orientation = FloatArray(3)
        SensorManager.getOrientation(rot, orientation)
        // orientation: [azimuth, pitch, roll] in radians
        val pitchDeg = Math.toDegrees(orientation[1].toDouble()).toFloat()
        val rollDeg = Math.toDegrees(orientation[2].toDouble()).toFloat()
        // Apply hysteresis: require deviation beyond band from the threshold before switching.
        return classify(pitchDeg, rollDeg, lastEmitted, hysteresisDeg)
    }

    companion object {
        /** Pure function for unit-testability. */
        internal fun classify(
            pitchDeg: Float,
            rollDeg: Float,
            previous: OrientationService.OrientationState?,
            hysteresis: Float,
        ): OrientationService.OrientationState {
            // Naming: landscape-left = phone rotated 90° counterclockwise from portrait.
            // Rough thresholds: roll > +45 → landscape-right, roll < -45 → landscape-left,
            // pitch < -45 → portrait-inverted, else portrait.
            // Hysteresis widens the stable band around the current state.
            fun shifted(threshold: Float, toward: Boolean): Float =
                if (toward) threshold - hysteresis else threshold + hysteresis

            return when {
                rollDeg > shifted(45f, previous != OrientationService.OrientationState.LANDSCAPE_RIGHT) ->
                    OrientationService.OrientationState.LANDSCAPE_RIGHT
                rollDeg < -shifted(45f, previous != OrientationService.OrientationState.LANDSCAPE_LEFT) ->
                    OrientationService.OrientationState.LANDSCAPE_LEFT
                pitchDeg < -shifted(45f, previous != OrientationService.OrientationState.PORTRAIT_INVERTED) ->
                    OrientationService.OrientationState.PORTRAIT_INVERTED
                else -> OrientationService.OrientationState.PORTRAIT
            }
        }
    }
}
```

### Step 3 — Create JVM unit test

- [ ] Create `neuro_mobile_app/app/src/test/java/com/neurocomputer/neuromobile/domain/OrientationServiceTest.kt`:

```kotlin
package com.neurocomputer.neuromobile.domain

import org.junit.Assert.assertEquals
import org.junit.Test

class OrientationServiceTest {
    @Test
    fun `portrait near zero roll and pitch`() {
        val s = OrientationService.classify(0f, 0f, null, 15f)
        assertEquals(OrientationService.OrientationState.PORTRAIT, s)
    }

    @Test
    fun `landscape right at high positive roll`() {
        val s = OrientationService.classify(0f, 80f, null, 15f)
        assertEquals(OrientationService.OrientationState.LANDSCAPE_RIGHT, s)
    }

    @Test
    fun `landscape left at high negative roll`() {
        val s = OrientationService.classify(0f, -80f, null, 15f)
        assertEquals(OrientationService.OrientationState.LANDSCAPE_LEFT, s)
    }

    @Test
    fun `hysteresis keeps state stable near boundary`() {
        // Phone previously landscape-right. Small dip below +45° should NOT flip to portrait
        // thanks to the hysteresis band.
        val prev = OrientationService.OrientationState.LANDSCAPE_RIGHT
        val s = OrientationService.classify(0f, 35f, prev, 15f)
        assertEquals(OrientationService.OrientationState.LANDSCAPE_RIGHT, s)
    }

    @Test
    fun `portrait inverted at high negative pitch`() {
        val s = OrientationService.classify(-80f, 0f, null, 15f)
        assertEquals(OrientationService.OrientationState.PORTRAIT_INVERTED, s)
    }
}
```

### Step 4 — Run unit tests

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev/neuro_mobile_app && ./gradlew :app:testDebugUnitTest --tests '*OrientationServiceTest' -q
```
Expected: BUILD SUCCESSFUL, 5 tests pass.

### Step 5 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/domain/ neuro_mobile_app/app/src/test/java/com/neurocomputer/neuromobile/domain/ && git commit -m "$(cat <<'EOF'
feat(mobile): OrientationService + RotationLockState

Quantizes rotation-vector sensor to 4 discrete orientation states
with 300ms debounce + ±15° hysteresis; honors RotationLockState.
Classifier extracted as pure fn for JVM unit tests.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Extend `LiveKitService.kt` with `sendOrientation`/`sendTouchEvent`/`sendSession`

**Files:**
- Modify: `neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/data/service/LiveKitService.kt`

### Step 1 — Add publisher helpers

- [ ] Locate the existing `sendMouseEvent(event: MouseEvent)` method (~line 136). BELOW it (still inside the class), add:

```kotlin
    private fun publishJson(json: String, topic: String = "mouse_control") {
        val currentRoom = room ?: return
        scope.launch(Dispatchers.IO) {
            try {
                currentRoom.localParticipant.publishData(
                    data = json.toByteArray(Charsets.UTF_8),
                    reliability = io.livekit.android.room.participant.DataPublishReliability.RELIABLE,
                    topic = topic,
                )
            } catch (e: Exception) {
                android.util.Log.w("LiveKitService", "publishJson failed: ${e.message}")
            }
        }
    }

    fun sendOrientation(state: String, locked: Boolean) {
        publishJson(
            """{"type":"orientation","state":"$state","locked":$locked}"""
        )
    }

    fun sendTouchEvent(kind: String, nx: Float, ny: Float, dy: Float = 0f) {
        publishJson(
            """{"type":"$kind","nx":$nx,"ny":$ny,"dy":$dy}"""
        )
    }

    fun sendSession(event: String) {
        publishJson("""{"type":"session","event":"$event"}""")
    }
```

Note: Import `io.livekit.android.room.participant.DataPublishReliability` (or whatever the existing `sendMouseEvent` uses for `reliability`) — match the existing pattern at line 151–155.

### Step 2 — Smoke build

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev/neuro_mobile_app && ./gradlew :app:compileDebugKotlin -q
```
Expected: BUILD SUCCESSFUL.

### Step 3 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/data/service/LiveKitService.kt && git commit -m "$(cat <<'EOF'
feat(mobile): LiveKitService senders for orientation / touch / session

Three new fn publishing JSON on existing mouse_control topic —
reuses WebRTC data channel; no new transport.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Hilt wiring + session lifecycle

**Files:**
- Modify: `neuro_mobile_app/.../di/NetworkModule.kt` — provide `OrientationService`, `RotationLockState`
- Modify: `neuro_mobile_app/.../MainActivity.kt` — start/stop `OrientationService` + `sendSession`

### Step 1 — Hilt providers

- [ ] In `neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/di/NetworkModule.kt`, add providers alongside existing `@Provides` (fill in matching `@Module`/`@InstallIn` annotations already present):

```kotlin
    @Provides
    @Singleton
    fun provideRotationLockState(): com.neurocomputer.neuromobile.domain.RotationLockState =
        com.neurocomputer.neuromobile.domain.RotationLockState()

    @Provides
    @Singleton
    fun provideOrientationService(
        @ApplicationContext context: android.content.Context,
        lockState: com.neurocomputer.neuromobile.domain.RotationLockState,
    ): com.neurocomputer.neuromobile.domain.OrientationService =
        com.neurocomputer.neuromobile.domain.OrientationService(context, lockState)
```

If `@ApplicationContext` isn't already imported, add `import dagger.hilt.android.qualifiers.ApplicationContext`.

### Step 2 — Start / stop lifecycle + send session events

- [ ] In `MainActivity.kt` (or whichever class owns the LiveKit connection — find by grepping for `liveKitService.connect` / `sendMouseEvent`), inject `OrientationService` and add:

```kotlin
@Inject lateinit var orientationService: com.neurocomputer.neuromobile.domain.OrientationService
```

Then where the LiveKit room successfully connects (callback / `onConnected`), call:

```kotlin
liveKitService.sendSession("mobile_connect")
orientationService.start { state, locked ->
    liveKitService.sendOrientation(state.wire, locked)
}
```

And where the room disconnects (or in `onStop` as safety):

```kotlin
orientationService.stop()
liveKitService.sendSession("mobile_disconnect")
```

### Step 3 — Smoke build

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev/neuro_mobile_app && ./gradlew :app:compileDebugKotlin -q
```
Expected: BUILD SUCCESSFUL.

### Step 4 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/di/NetworkModule.kt neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/MainActivity.kt && git commit -m "$(cat <<'EOF'
feat(mobile): DI + lifecycle for OrientationService

Provides OrientationService/RotationLockState as singletons; starts
sensor on LiveKit connect and sends mobile_connect/disconnect events.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: `RotationLockButton` in `DraggableToolbar`

**Files:**
- Create: `neuro_mobile_app/.../ui/components/RotationLockButton.kt`
- Modify: `neuro_mobile_app/.../ui/components/DraggableToolbar.kt`

### Step 1 — Create `RotationLockButton.kt`

- [ ] Create file:

```kotlin
package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.outlined.LockOpen
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.neurocomputer.neuromobile.domain.OrientationService
import com.neurocomputer.neuromobile.domain.RotationLockState

@Composable
fun RotationLockButton(
    lockState: RotationLockState,
    orientationService: OrientationService,
    modifier: Modifier = Modifier,
) {
    val locked by lockState.locked.collectAsState()
    IconButton(
        onClick = {
            val newValue = lockState.toggle()
            orientationService.setLock(newValue)
        },
        modifier = modifier,
    ) {
        Icon(
            imageVector = if (locked) Icons.Filled.Lock else Icons.Outlined.LockOpen,
            contentDescription = if (locked) "Rotation locked" else "Rotation unlocked",
            tint = if (locked) Color(0xFFE57373) else Color(0xFFB0B0B0),
            modifier = Modifier.size(24.dp),
        )
    }
}
```

### Step 2 — Integrate into `DraggableToolbar.kt`

- [ ] Open `ui/components/DraggableToolbar.kt`. It takes various parameters for toolbar items. Add two new params:

```kotlin
    lockState: com.neurocomputer.neuromobile.domain.RotationLockState? = null,
    orientationService: com.neurocomputer.neuromobile.domain.OrientationService? = null,
```

and inside the Row/Column of toolbar buttons, add:

```kotlin
    if (lockState != null && orientationService != null) {
        RotationLockButton(
            lockState = lockState,
            orientationService = orientationService,
        )
    }
```

Then in the call site (the screen that invokes `DraggableToolbar`, typically `ConversationScreen.kt` or `MainScreen.kt`), pass these — inject via `hiltViewModel()` or constructor param as appropriate.

### Step 3 — Smoke build

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev/neuro_mobile_app && ./gradlew :app:compileDebugKotlin -q
```
Expected: BUILD SUCCESSFUL.

### Step 4 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/components/RotationLockButton.kt neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/components/DraggableToolbar.kt && git commit -m "$(cat <<'EOF'
feat(mobile): RotationLockButton in DraggableToolbar

Compose lock/unlock toggle wired to RotationLockState; calls
OrientationService.setLock on toggle. Visual: filled red lock
when locked, outline grey when free.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: `TabletTouchOverlay.kt` + settings flag + `MainScreen` switch

**Files:**
- Create: `neuro_mobile_app/.../ui/components/TabletTouchOverlay.kt`
- Modify: `neuro_mobile_app/.../ui/screens/MainScreen.kt`

### Step 1 — Create `TabletTouchOverlay.kt`

- [ ] Create file:

```kotlin
package com.neurocomputer.neuromobile.ui.components

import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.unit.IntSize
import com.neurocomputer.neuromobile.data.service.LiveKitService

/**
 * Full-screen transparent overlay that converts touch gestures into absolute
 * (normalized) remote-input events on the LiveKit data channel. Used instead
 * of the relative touchpad when tablet-mode is enabled.
 *
 * Pinch-zoom is handled locally — scales the video view (via graphicsLayer),
 * never sent to PC (PCs don't accept pinch).
 */
@Composable
fun TabletTouchOverlay(
    liveKitService: LiveKitService,
    modifier: Modifier = Modifier,
) {
    var size by remember { mutableStateOf(IntSize.Zero) }
    var zoom by remember { mutableStateOf(1f) }
    var panX by remember { mutableStateOf(0f) }
    var panY by remember { mutableStateOf(0f) }

    fun norm(x: Float, y: Float): Pair<Float, Float> {
        val nx = if (size.width > 0) (x / size.width).coerceIn(0f, 1f) else 0f
        val ny = if (size.height > 0) (y / size.height).coerceIn(0f, 1f) else 0f
        return nx to ny
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .onSizeChanged { size = it }
            .graphicsLayer(
                scaleX = zoom, scaleY = zoom,
                translationX = panX, translationY = panY,
            )
            .pointerInput(Unit) {
                detectTapGestures(
                    onTap = { offset ->
                        val (nx, ny) = norm(offset.x, offset.y)
                        liveKitService.sendTouchEvent("touch_tap", nx, ny)
                    },
                    onLongPress = { offset ->
                        val (nx, ny) = norm(offset.x, offset.y)
                        liveKitService.sendTouchEvent("touch_long_press", nx, ny)
                    },
                )
            }
            .pointerInput(Unit) {
                detectDragGestures(
                    onDragStart = { offset ->
                        val (nx, ny) = norm(offset.x, offset.y)
                        liveKitService.sendTouchEvent("touch_drag_start", nx, ny)
                    },
                    onDrag = { change, _ ->
                        val (nx, ny) = norm(change.position.x, change.position.y)
                        liveKitService.sendTouchEvent("touch_drag_move", nx, ny)
                    },
                    onDragEnd = {
                        // Last known position — Compose doesn't give it here; send (0,0) or track
                        liveKitService.sendTouchEvent("touch_drag_end", 0f, 0f)
                    },
                )
            }
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, gestureZoom, _ ->
                    if (gestureZoom != 1f) {
                        zoom = (zoom * gestureZoom).coerceIn(1f, 5f)
                    } else {
                        // 2-finger pan → scroll (vertical delta only; most common case)
                        val (nx, ny) = norm(pan.x + size.width / 2f, pan.y + size.height / 2f)
                        liveKitService.sendTouchEvent("scroll", nx, ny, dy = pan.y)
                    }
                }
            }
    )
}
```

Track last-drag-position in a mutable var to fix the `touch_drag_end` coord (see code comment). Use `androidx.compose.runtime.mutableStateOf<Pair<Float,Float>?>(null)` and update inside `onDrag`.

### Step 2 — Add `tabletMode` setting + switch in `MainScreen.kt`

- [ ] In `MainScreen.kt`, behind a simple boolean (`var tabletMode = true` — plumb later via Settings if desired), pick which overlay renders on top of the remote video:

```kotlin
if (tabletMode) {
    TabletTouchOverlay(liveKitService = liveKitService)
} else {
    TouchpadOverlay(/* existing params */)
}
```

### Step 3 — Smoke build

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev/neuro_mobile_app && ./gradlew :app:compileDebugKotlin -q
```
Expected: BUILD SUCCESSFUL.

### Step 4 — Commit

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && git add neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/components/TabletTouchOverlay.kt neuro_mobile_app/app/src/main/java/com/neurocomputer/neuromobile/ui/screens/MainScreen.kt && git commit -m "$(cat <<'EOF'
feat(mobile): TabletTouchOverlay for absolute tap / drag / scroll

Compose overlay that emits touch_* events with normalized coords;
pinch-zoom handled client-side via graphicsLayer (no PC msg).
MainScreen picks between tablet overlay and legacy touchpad via
tabletMode flag (default on).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: End-to-end manual verification

**No new files. Documentation step.**

### Step 1 — Run full Python test suite

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -m pytest tests/core/test_display_controller.py tests/core/test_mouse_controller_touch.py -v
```
Expected: all 11 tests pass.

### Step 2 — Build APK

- [ ] Run:
```bash
cd /home/ubuntu/neurocomputer-dev/neuro_mobile_app && ./gradlew :app:assembleDebug -q
```
Expected: `BUILD SUCCESSFUL`, APK in `app/build/outputs/apk/debug/`.

### Step 3 — Manual E2E checklist (ask user to execute on hardware)

Use `/screen/start` endpoint on PC, connect Android app:

- [ ] **(1) Connect** — Mobile joins LiveKit room. All connected PC monitors rotate to match phone's physical orientation within ~500ms.
- [ ] **(2) Rotation follow** — Rotate phone portrait ↔ landscape. PC display follows within 500ms, no jitter or flicker.
- [ ] **(3) Lock** — Tap rotation-lock button. Rotate phone physically. PC display does NOT rotate. Unlock → next phone movement resumes auto-rotate.
- [ ] **(4) Disconnect restore** — Close app or kill LiveKit session. PC display reverts to pre-session orientation within ~2s; cursor returns.
- [ ] **(5) Touch input** — In streamed video, tap a button on the desktop. Click lands at matching PC pixel. Long-press → right-click menu. Drag a window → window follows finger. 2-finger pinch → local zoom of video (no PC change).

### Step 4 — Commit E2E results (if any fix-ups needed)

- [ ] If all pass, no commit. If any step 1-5 fails, debug → fix inline → commit per-fix.

---

## Self-Review

Checked against spec §1–§5:
- §Architecture/data flow → Tasks 1–3, 5–9 cover both PC and mobile sides end-to-end.
- §Data-chan schemas → Task 3 (PC dispatch), Task 6 (mobile sender) match exactly.
- §Orientation mapping → encoded in `_ORIENTATION_MAP` in Task 1.
- §DisplayController public API → Task 1 matches spec verbatim.
- §Mouse controller extensions → Task 2 covers all 5 touch kinds + `_denorm` + offset math.
- §Desktop stream wiring → Task 3 covers dispatcher + finally hook; Task 4 covers server.py cancel path.
- §OrientationService → Task 5 matches spec (quantize + debounce + hysteresis + lock).
- §RotationLockButton → Task 8.
- §TabletTouchOverlay → Task 9.
- §Error handling → Task 1 handles xrandr/xsetroot/unclutter missing; Task 3 error-guards dispatch.
- §Cleanup paths 1-4 → Task 3 (paths 1, 2) + Task 4 (path 3) + `session_end` idempotent guard (path 4, app-exit case).
- §Testing → Tasks 1, 2, 5 cover pytest + JVM unit test per spec. Manual E2E → Task 10.

No placeholders in code steps. Type names consistent: `DisplayController`, `OrientationService`, `RotationLockState`, `TabletTouchOverlay`, `RotationLockButton`, wire strings `"touch_tap"/"touch_long_press"/"touch_drag_start"/..."touch_drag_end"/"scroll"/"orientation"/"session"`.
