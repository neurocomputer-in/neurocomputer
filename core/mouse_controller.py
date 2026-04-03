"""
Mouse Controller - Receives mouse events from LiveKit data channel and executes via xdotool.

Uses xdotool (subprocess) instead of pyautogui to avoid NumPy/cv2 dependency issues.
Handles: move, click, double-click, right-click, scroll.

Scroll smoothing: accumulates scroll deltas over a short window and fires
a single batched scroll to prevent bombardment and lag.
"""

import asyncio
import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger("mouse-controller")


def _xdotool(*args: str) -> None:
    """Run an xdotool command silently."""
    subprocess.run(["xdotool", *args], check=False, capture_output=True)


class MouseController:
    """Handles mouse control events from the mobile touchpad."""

    def __init__(self, screen_width: int = 1920, screen_height: int = 1080,
                 dry_run: bool = False, monitor_offset: tuple = (0, 0)):
        self.dry_run = dry_run
        self.monitor_offset = monitor_offset  # (left, top) offset of current monitor
        self._update_screen_dimensions(screen_width, screen_height)

        # Sensitivity multipliers
        self.move_sensitivity = 2.5   # Higher = faster cursor
        self.scroll_sensitivity = 1.0  # Reduced — batching handles amplification

        # Rate limiting for mouse moves
        self._last_move_time = 0.0
        self._move_throttle_s = 1.0 / 60  # Max 60 moves/sec

        # ── Scroll accumulator / debouncer ──
        self._scroll_accum = 0.0         # Accumulated scroll delta
        self._scroll_task: Optional[asyncio.Task] = None  # Pending flush task
        self._scroll_flush_delay = 0.08  # 80ms window — collect scrolls, then fire once
        self._scroll_max_per_flush = 5   # Cap scroll clicks per flush to prevent runaway

        logger.info(f"[Mouse] Controller initialized: {screen_width}x{screen_height}, offset={monitor_offset}, dry_run={dry_run}")

    def _update_screen_dimensions(self, width: int, height: int):
        """Update screen dimensions."""
        self.screen_width = width
        self.screen_height = height

    def _update_monitor_offset(self, offset: tuple):
        """Update monitor offset for multi-monitor support."""
        self.monitor_offset = offset

    async def handle_event(self, event: dict):
        """Dispatch a mouse event to the appropriate handler."""
        event_type = event.get("type")
        if not event_type:
            return

        try:
            if event_type == "mouse_move":
                await self._handle_move(event)
            elif event_type == "click":
                await self._handle_click(event)
            elif event_type == "double_click":
                await self._handle_click(event, count=2)
            elif event_type == "right_click":
                await self._handle_click(event, button="right")
            elif event_type == "scroll":
                self._accumulate_scroll(event)
            elif event_type == "key":
                await self._handle_key(event)
            elif event_type == "mousedown":
                await self._handle_mousedown(event)
            elif event_type == "mouseup":
                await self._handle_mouseup(event)
            elif event_type == "direct_click":
                await self._handle_direct_click(event)
            elif event_type == "direct_double_click":
                await self._handle_direct_click(event, count=2)
            elif event_type == "direct_right_click":
                await self._handle_direct_click(event, button="right")
            elif event_type == "window_focus":
                await self._handle_window_focus(event)
            else:
                logger.warning(f"[Mouse] Unknown event type: {event_type}")
        except Exception as e:
            logger.error(f"[Mouse] Error handling {event_type}: {e}")

    async def _handle_mousedown(self, event: dict):
        """Hold mouse button down (for drag)."""
        button = event.get("button", "left")
        btn_num = "3" if button == "right" else "1"
        if self.dry_run:
            logger.info(f"[Mouse][DRY] mousedown({btn_num})")
            return
        await asyncio.to_thread(_xdotool, "mousedown", btn_num)

    async def _handle_mouseup(self, event: dict):
        """Release mouse button (end drag)."""
        button = event.get("button", "left")
        btn_num = "3" if button == "right" else "1"
        if self.dry_run:
            logger.info(f"[Mouse][DRY] mouseup({btn_num})")
            return
        await asyncio.to_thread(_xdotool, "mouseup", btn_num)

    async def _handle_key(self, event: dict):
        """Handle keyboard key press."""
        key = event.get("key")
        if not key:
            return



        # Map common key names to xdotool key names
        key_mapping = {
            "BackSpace": "BackSpace",
            "Backspace": "BackSpace",
            "Enter": "Return",
            "Return": "Return",
            "Escape": "Escape",
            "Tab": "Tab",
            "Space": "space",
            "Ctrl": "ctrl",
            "Alt": "alt",
            "Shift": "shift",
            "Meta": "super",
            "CapsLock": "Caps_Lock",
            "Left": "Left",
            "Right": "Right",
            "Up": "Up",
            "Down": "Down",
            "Home": "Home",
            "End": "End",
            "PageUp": "Page_Up",
            "PageDown": "Page_Down",
            "Insert": "Insert",
            "Delete": "Delete",
            "PrintScreen": "Print",
            "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
            "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
            "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",
            # Symbols
            "+": "plus", "-": "minus", "=": "equal",
            "[": "bracketleft", "]": "bracketright",
            "\\": "backslash", ";": "semicolon",
            "'": "apostrophe", ",": "comma", ".": "period",
            "/": "slash", "`": "grave",
            "(": "parenleft", ")": "parenright",
            "*": "asterisk", ":": "colon",
            "!": "exclam", "?": "question",
            "#": "numbersign", "$": "dollar",
            "%": "percent", "^": "asciicircum",
            "&": "ampersand", "_": "underscore",
            "+": "plus", "|": "bar",
            "{": "braceleft", "}": "braceright",
            "<": "less", ">": "greater",
            '"': "quotedbl",
        }
        key = key_mapping.get(key, key)

        if self.dry_run:
            logger.info(f"[Mouse][DRY] key({key})")
            return

        await asyncio.to_thread(_xdotool, "key", key)


    async def _handle_move(self, event: dict):
        """Handle relative mouse movement."""
        now = time.monotonic()
        if now - self._last_move_time < self._move_throttle_s:
            return  # Rate limit
        self._last_move_time = now

        dx = float(event.get("dx", 0))
        dy = float(event.get("dy", 0))

        desktop_dx = int(dx * self.move_sensitivity)
        desktop_dy = int(dy * self.move_sensitivity)

        if desktop_dx == 0 and desktop_dy == 0:
            return



        if self.dry_run:
            logger.info(f"[Mouse][DRY] mousemove_relative({desktop_dx}, {desktop_dy})")
            return

        # Use simple relative movement - works across monitors
        await asyncio.to_thread(_xdotool, "mousemove_relative", "--", str(desktop_dx), str(desktop_dy))


    async def _handle_click(self, event: dict, button: str = "left", count: int = 1):
        """Handle mouse click."""
        button = event.get("button", button)
        count = event.get("count", count)

        btn_num = "3" if button == "right" else "2" if button == "middle" else "1"

        if self.dry_run:
            logger.info(f"[Mouse][DRY] click(button={btn_num}, repeat={count})")
            return

        args = ["click"]
        if count > 1:
            args += ["--repeat", str(count)]
        args.append(btn_num)

        await asyncio.to_thread(_xdotool, *args)

    async def _handle_direct_click(self, event: dict, button: str = "left", count: int = 1):
        """Handle direct click at absolute coordinates (normalized 0-1)."""
        # Get normalized coordinates from event
        x = float(event.get("x", 0.5))
        y = float(event.get("y", 0.5))
        button = event.get("button", button)
        count = event.get("count", count)

        # Convert normalized coordinates to absolute screen coordinates
        abs_x = int(x * self.screen_width)
        abs_y = int(y * self.screen_height)

        # Add monitor offset for multi-monitor
        abs_x += self.monitor_offset[0]
        abs_y += self.monitor_offset[1]

        btn_num = "3" if button == "right" else "2" if button == "middle" else "1"



        if self.dry_run:
            logger.info(f"[Mouse][DRY] mousemove({abs_x}, {abs_y}) + click({btn_num}, repeat={count})")
            return

        # Move mouse to absolute position, then click
        await asyncio.to_thread(_xdotool, "mousemove", str(abs_x), str(abs_y))

        # Small delay to ensure mouse move completes
        await asyncio.sleep(0.02)

        # Perform click
        args = ["click"]
        if count > 1:
            args += ["--repeat", str(count)]
        args.append(btn_num)

        await asyncio.to_thread(_xdotool, *args)


    async def _handle_window_focus(self, event: dict):
        """Click at tap position to focus the window. Cursor stays at tap position."""
        x = float(event.get("x", 0.5))
        y = float(event.get("y", 0.5))

        abs_x = int(x * self.screen_width) + self.monitor_offset[0]
        abs_y = int(y * self.screen_height) + self.monitor_offset[1]



        if self.dry_run:
            logger.info(f"[Mouse][DRY] mousemove({abs_x},{abs_y}) click")
            return

        # Move cursor to tap position and click to focus
        subprocess.run(
            ["xdotool",
             "mousemove", str(abs_x), str(abs_y),
             "click", "1"],
            capture_output=True, text=True
        )

    # ── Scroll debouncing ────────────────────────────────────────────────

    def _accumulate_scroll(self, event: dict):
        """Accumulate scroll delta and schedule a batched flush."""
        dy = float(event.get("dy", 0))
        self._scroll_accum += dy * self.scroll_sensitivity

        # Schedule flush if not already pending
        if self._scroll_task is None or self._scroll_task.done():
            self._scroll_task = asyncio.ensure_future(self._flush_scroll())

    async def _flush_scroll(self):
        """Wait for the debounce window, then fire one batched scroll."""
        await asyncio.sleep(self._scroll_flush_delay)

        # Grab accumulated value and reset
        raw = self._scroll_accum
        self._scroll_accum = 0.0

        amount = int(raw)
        if amount == 0:
            return

        # Cap to prevent runaway scrolling
        amount = max(-self._scroll_max_per_flush, min(self._scroll_max_per_flush, amount))

        if self.dry_run:
            logger.info(f"[Mouse][DRY] scroll({amount})")
            return

        # xdotool: button 4 = scroll up, button 5 = scroll down
        if amount > 0:
            await asyncio.to_thread(_xdotool, "click", "--repeat", str(abs(amount)), "4")
        else:
            await asyncio.to_thread(_xdotool, "click", "--repeat", str(abs(amount)), "5")

    def update_sensitivity(self, move: Optional[float] = None, scroll: Optional[float] = None):
        """Update sensitivity settings."""
        if move is not None:
            self.move_sensitivity = max(0.1, min(10.0, move))
        if scroll is not None:
            self.scroll_sensitivity = max(0.1, min(10.0, scroll))
        logger.info(f"[Mouse] Sensitivity updated: move={self.move_sensitivity}, scroll={self.scroll_sensitivity}")
