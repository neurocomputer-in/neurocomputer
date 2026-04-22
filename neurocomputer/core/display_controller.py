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

# Simplified two-way mapping: any portrait state → 'left', any landscape → 'normal'.
# The four-way version (with 'inverted' and 'right') produced upside-down PC layouts
# that were confusing; the phone side only meaningfully distinguishes long-axis
# vertical vs long-axis horizontal.
_ORIENTATION_MAP = {
    "landscape-left": "normal",
    "landscape-right": "normal",
    "portrait": "left",
    "portrait-inverted": "left",
}

_ROTATE_THROTTLE_S = 0.25


def _run(*argv: str) -> subprocess.CompletedProcess:
    """Run a subprocess synchronously, capturing output. Never raises."""
    try:
        return subprocess.run(list(argv), check=False, capture_output=True, text=True)
    except FileNotFoundError as e:
        logger.warning(f"[Display] Command not found: {argv[0]} ({e})")
        return subprocess.CompletedProcess(list(argv), returncode=127, stdout="", stderr=str(e))


class DisplayController:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._snapshot: Optional[dict[str, str]] = None
        self._cursor_snapshot: Optional[str] = None
        self._current_state: Optional[str] = None
        self._locked: bool = False
        self._last_rotate_ts: float = 0.0
        self._unclutter_pid: Optional[int] = None

    async def session_start(self) -> None:
        """Snapshot current state + hide cursor. Idempotent."""
        if self._snapshot is not None:
            logger.info("[Display] session_start called while session active — ignored")
            return
        self._snapshot = await asyncio.to_thread(self._capture_snapshot)
        self._cursor_snapshot = "left_ptr"
        # Reset per-session tracking so a new session doesn't dedup against
        # stale state left over from the previous one.
        self._current_state = None
        self._last_rotate_ts = 0.0
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
            logger.info("[Display] Rotating with no snapshot; session_start not called")
        logger.info(f"[Display] handle_orientation state={state} → xrandr rotate {rotate_value}")
        await asyncio.to_thread(self._rotate_all_outputs, rotate_value)
        self._current_state = state
        self._last_rotate_ts = now
        await asyncio.to_thread(self._refresh_mouse_controller_dims)

    def set_lock(self, locked: bool) -> None:
        self._locked = locked

    async def normalise(self) -> None:
        """Reset every connected output back to xrandr rotate 'normal'.
        Idempotent; used by the Normalise Desktop Displays settings action
        so the user can recover from any stuck rotation without restarting."""
        await asyncio.to_thread(self._rotate_all_outputs, "normal")
        self._current_state = "landscape-left"  # matches 'normal' in map
        self._last_rotate_ts = time.monotonic()
        await asyncio.to_thread(self._refresh_mouse_controller_dims)
        logger.info("[Display] normalise() reset all outputs to 'normal'")

    def _capture_snapshot(self) -> dict[str, str]:
        """Parse `xrandr --query` for connected outputs and their rotate values."""
        result = _run("xrandr", "--query")
        snapshot: dict[str, str] = {}
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
        outputs = self._connected_outputs()
        if not outputs:
            logger.warning("[Display] _rotate_all_outputs: no outputs detected")
            return
        args: list[str] = []
        for name in outputs:
            args += ["--output", name, "--rotate", rotate_value]
        if self.dry_run:
            logger.info(f"[Display][DRY] xrandr {' '.join(args)}")
            return
        logger.info(f"[Display] running: xrandr {' '.join(args)}")
        res = _run("xrandr", *args)
        if res.returncode == 0:
            logger.info(f"[Display] xrandr rotate ok ({rotate_value})")
        else:
            logger.warning(f"[Display] atomic xrandr rotate failed rc={res.returncode}: {res.stderr.strip()}; falling back to per-output")
            for name in outputs:
                r = _run("xrandr", "--output", name, "--rotate", rotate_value)
                if r.returncode != 0:
                    logger.warning(f"[Display] xrandr rotate failed for {name}: {r.stderr.strip()}")
                else:
                    logger.info(f"[Display] per-output xrandr {name} rotate {rotate_value} ok")

    def _restore_snapshot(self, snapshot: dict[str, str]) -> None:
        if not snapshot:
            return
        args: list[str] = []
        for name, rot in snapshot.items():
            args += ["--output", name, "--rotate", rot]
        if self.dry_run:
            logger.info(f"[Display][DRY] xrandr {' '.join(args)}")
            return
        res = _run("xrandr", *args)
        if res.returncode != 0:
            logger.warning(f"[Display] atomic xrandr restore failed: {res.stderr.strip()}; falling back to per-output")
            for name, rot in snapshot.items():
                _run("xrandr", "--output", name, "--rotate", rot)

    def _hide_cursor(self) -> None:
        if self.dry_run:
            logger.info("[Display][DRY] hide cursor")
            return
        res = _run("xsetroot", "-cursor_name", "blank")
        if res.returncode != 0:
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
        """After rotate, push updated monitor dims to the mouse controller
        and tell the capture loop to re-init its (stale) mss handle."""
        try:
            from core.desktop_stream import (
                update_mouse_controller_for_monitor,
                get_current_monitor,
                mark_display_dirty,
            )
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
            mark_display_dirty()
        except Exception as e:
            logger.warning(f"[Display] Failed to refresh mouse dims after rotate: {e}")


controller = DisplayController()
