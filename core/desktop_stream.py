import asyncio
import json
import subprocess
import numpy as np
import mss
import logging
from livekit import rtc, api
from dataclasses import dataclass
from typing import Optional
from PIL import Image, ImageDraw

from core.mouse_controller import MouseController

logger = logging.getLogger("desktop-streamer")

@dataclass
class ViewState:
    """Tracks the current zoom and pan state for screen capture."""
    zoom: float = 1.0  # 1.0 = full screen, 2.0 = 2x zoom, etc.
    pan_x: float = 0.5  # 0.0 = left edge, 1.0 = right edge, 0.5 = center
    pan_x: float = 0.5  # 0.0 = left edge, 1.0 = right edge, 0.5 = center
    pan_y: float = 0.5  # 0.0 = top edge, 1.0 = bottom edge, 0.5 = center
    rotation: int = 0   # 0, 90, 180, 270
    
    def reset(self):
        self.zoom = 1.0
        self.pan_x = 0.5
        self.pan_y = 0.5
        self.rotation = 0
    
    def clamp(self):
        """Ensure values stay within valid bounds."""
        self.zoom = max(1.0, min(10.0, self.zoom))  # 1x to 10x zoom
        # Pan bounds depend on zoom level - can't pan outside visible area
        max_pan = 1.0 - (0.5 / self.zoom)
        min_pan = 0.5 / self.zoom
        self.pan_x = max(min_pan, min(max_pan, self.pan_x))
        self.pan_y = max(min_pan, min(max_pan, self.pan_y))

# Global view state - can be updated via API
_active_streams: dict[str, ViewState] = {}

# Global mouse controller for multi-monitor offset updates
_active_mouse_controller: Optional[MouseController] = None

# Current monitor index for screen capture (1 = first monitor, 2 = second, etc.)
_current_monitor_index = 1  # Start with primary monitor (index 1)

# Dirty flag: set by DisplayController after xrandr rotate so the capture
# loop knows to re-init its mss handle and recompute frame dimensions.
_display_dirty: bool = False

def mark_display_dirty():
    """Mark the display geometry as changed (e.g. after an xrandr rotate)."""
    global _display_dirty
    _display_dirty = True

def set_current_monitor(index: int):
    """Set the current monitor index for screen capture."""
    global _current_monitor_index
    _current_monitor_index = index


def get_current_monitor() -> int:
    """Get the current monitor index."""
    return _current_monitor_index

def update_mouse_controller_for_monitor(width: int, height: int, offset: tuple):
    """Update the active mouse controller's screen dimensions and monitor offset."""
    global _active_mouse_controller
    if _active_mouse_controller is not None:
        _active_mouse_controller._update_screen_dimensions(width, height)
        _active_mouse_controller._update_monitor_offset(offset)


def get_view_state(room_name: str) -> ViewState:
    """Get or create view state for a room."""
    if room_name not in _active_streams:
        _active_streams[room_name] = ViewState()
    return _active_streams[room_name]

def update_view(room_name: str, zoom: Optional[float] = None, 
                pan_x: Optional[float] = None, pan_y: Optional[float] = None,
                rotation: Optional[int] = None,
                reset: bool = False):
    """Update the view state for a room."""
    state = get_view_state(room_name)
    if reset:
        state.reset()
    else:
        if zoom is not None:
            state.zoom = zoom
        if pan_x is not None:
            state.pan_x = pan_x
        if pan_y is not None:
            state.pan_y = pan_y
        if rotation is not None:
            state.rotation = rotation
        state.clamp()

    return state

async def _handle_switch_display(room: rtc.Room):
    """Switch to next display via data channel — no HTTP round-trip."""
    global _current_monitor_index, _active_mouse_controller
    try:
        sct = mss.mss()
        num_monitors = len(sct.monitors) - 1
        if num_monitors <= 1:
            return
        _current_monitor_index = (_current_monitor_index % num_monitors) + 1
        monitor = sct.monitors[_current_monitor_index]
        offset = (monitor.get('left', 0), monitor.get('top', 0))
        if _active_mouse_controller:
            _active_mouse_controller._update_screen_dimensions(monitor['width'], monitor['height'])
            _active_mouse_controller._update_monitor_offset(offset)
        # Move mouse to center + click to focus
        cx = monitor['left'] + monitor['width'] // 2
        cy = monitor['top'] + monitor['height'] // 2
        await asyncio.to_thread(
            lambda: (
                subprocess.run(["xdotool", "mousemove", str(cx), str(cy)], check=False, capture_output=True),
                subprocess.run(["xdotool", "click", "1"], check=False, capture_output=True)
            )
        )
        sct.close()
        logger.info(f"[Display] Switched to monitor {_current_monitor_index} via data channel")
    except Exception as e:
        logger.error(f"[Display] Switch error: {e}")


async def start_desktop_stream(room: rtc.Room, room_name: str = "default"):
    """
    Captures the desktop screen and publishes it as a video track.
    
    Args:
        room: Connected LiveKit room instance.
    """
    logger.info("[Screen] Starting desktop stream...")
    
    def _target_dims_for(w: int, h: int) -> tuple[int, int]:
        """Pick stream dims matching monitor aspect.
        Landscape: 1280-wide. Portrait: 720-wide (a.k.a. rotated 720x1280)."""
        if h > w:
            # Portrait
            tw = 720
            th = int(h / w * tw)
        else:
            # Landscape (or square)
            th = 720
            tw = int(w / h * th)
        # Round up to multiple of 4 (YUV420 half-dims must be even)
        tw = (tw + 3) & ~3
        th = (th + 3) & ~3
        return tw, th

    # 1. Probe monitor dimensions first to create a correctly-sized VideoSource
    sct = mss.mss()
    initial_monitor = sct.monitors[_current_monitor_index] if _current_monitor_index < len(sct.monitors) else sct.monitors[1]
    mon_w = initial_monitor['width']
    mon_h = initial_monitor['height']
    target_w, target_h = _target_dims_for(mon_w, mon_h)

    logger.info(f"[Screen] Monitor: {mon_w}x{mon_h} → Stream: {target_w}x{target_h}")

    options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_SCREENSHARE)

    async def _publish_track(w: int, h: int):
        """Create a VideoSource+track at dims (w,h) and publish it."""
        src = rtc.VideoSource(w, h)
        tr = rtc.LocalVideoTrack.create_video_track("desktop", src)
        pub = await room.local_participant.publish_track(tr, options)
        return src, tr, pub

    # Create the mouse controller + register the data-channel handler BEFORE
    # calling publish_track. publish_track is async and slow; if the handler
    # isn't attached yet when the mobile client sends its first orientation
    # event (right after room connect), that event is dropped.
    mouse_controller = MouseController(
        initial_monitor['width'],
        initial_monitor['height'],
        monitor_offset=(initial_monitor.get('left', 0), initial_monitor.get('top', 0)),
    )
    global _active_mouse_controller
    _active_mouse_controller = mouse_controller

    @room.on("data_received")
    def _on_data_received(data_packet):
        """Handle incoming data packets — dispatch mouse + tablet-mode events."""
        topic = getattr(data_packet, "topic", None)
        logger.info(f"[Screen] data_received topic={topic} bytes={len(getattr(data_packet, 'data', b''))}")
        if topic != "mouse_control":
            return
        try:
            msg = json.loads(data_packet.data.decode("utf-8"))
        except Exception as e:
            logger.error(f"[Screen] Failed to decode data packet: {e}")
            return
        logger.info(f"[Screen] data msg type={msg.get('type')} full={msg}")

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

    source, track, publication = await _publish_track(target_w, target_h)


    # 4. Capture Loop
    sct = mss.mss()

    # Keep track of current monitor for dynamic switching
    current_monitor = [sct.monitors[1]]  # Use list to allow modification in nested function

    def get_current_monitor_info():
        """Get current monitor info based on global index - called dynamically."""
        global _current_monitor_index
        try:
            # Ensure index is valid
            max_idx = len(sct.monitors) - 1
            if _current_monitor_index > max_idx:
                _current_monitor_index = 1
            if _current_monitor_index < 1:
                _current_monitor_index = 1
            return sct.monitors[_current_monitor_index]
        except (IndexError, KeyError):
            return sct.monitors[1]  # Fallback to first monitor

    # Initialize monitor
    current_monitor[0] = get_current_monitor_info()


    # Get view state for this room
    view_state = get_view_state(room_name)

    # Initial monitor dimensions - will be updated dynamically
    mon_w = current_monitor[0]['width']
    mon_h = current_monitor[0]['height']
    mon_left = current_monitor[0].get('left', 0)
    mon_top = current_monitor[0].get('top', 0)

    # Sync current monitor dims into the already-created mouse controller
    # (it was constructed earlier with initial dims before data handler
    # registration).
    mouse_controller._update_screen_dimensions(mon_w, mon_h)
    mouse_controller._update_monitor_offset((mon_left, mon_top))

    logger.info("[Screen] Mouse controller ready, listening for touchpad events")

    # Kick off a display-controller session here so the pre-session snapshot
    # is taken and per-session state (like _current_state) is fresh. The
    # mobile client also sends {"type":"session","event":"mobile_connect"},
    # but there's a small window where that message can race the stream
    # start — doing it server-side as well makes the handshake reliable.
    try:
        from core.display_controller import controller as _disp
        await _disp.session_start()
    except Exception as e:
        logger.warning(f"[Screen] auto session_start failed: {e}")

    # Cursor position feedback to mobile
    _cursor_frame_count = 0
    _last_pub_x = -1.0
    _last_pub_y = -1.0

    try:
        while True:
            # Check connection
            if room.connection_state != rtc.ConnectionState.CONN_CONNECTED:
                logger.info("[Screen] Room disconnected, stopping stream.")
                break

            # If display geometry changed (e.g. xrandr rotate), refresh mss.
            # mss caches the monitor list at creation; without this, we'd read
            # stale width/height for one or more frames after a rotation,
            # producing blank or distorted captures.
            global _display_dirty
            if _display_dirty:
                try:
                    sct.close()
                except Exception:
                    pass
                sct = mss.mss()
                _display_dirty = False
                logger.info("[Screen] Refreshed mss after display rotation")

            # Dynamically get current monitor in case it changed
            current_monitor[0] = get_current_monitor_info()
            mon_w = current_monitor[0]['width']
            mon_h = current_monitor[0]['height']
            mon_left = current_monitor[0].get('left', 0)
            mon_top = current_monitor[0].get('top', 0)

            # Let frame dims follow current aspect per-frame. LiveKit's
            # VideoSource dims at track-publish time are only a starting hint;
            # each VideoFrame carries its own width/height which subscribers
            # use. Unpublish/republish on rotation caused the phone to
            # permanently stall, so we DON'T do that — we just push frames of
            # the correct size and rely on adaptive stream to renegotiate.
            target_w, target_h = _target_dims_for(mon_w, mon_h)

            # Update mouse controller with new monitor dimensions and offset
            mouse_controller._update_screen_dimensions(mon_w, mon_h)
            mouse_controller._update_monitor_offset((mon_left, mon_top))

            # Get current view state (may be updated by API)
            zoom = view_state.zoom
            pan_x = view_state.pan_x
            pan_y = view_state.pan_y

            # Calculate crop region based on zoom and pan
            # Visible width/height at current zoom level
            vis_w = int(mon_w / zoom)
            vis_h = int(mon_h / zoom)

            # Center point based on pan (pan is 0-1 normalized)
            center_x = int(pan_x * mon_w)
            center_y = int(pan_y * mon_h)

            # Calculate crop bounds
            left = max(0, center_x - vis_w // 2)
            top = max(0, center_y - vis_h // 2)
            right = min(mon_w, left + vis_w)
            bottom = min(mon_h, top + vis_h)

            # Adjust if we hit edges
            if right - left < vis_w:
                left = max(0, right - vis_w)
            if bottom - top < vis_h:
                top = max(0, bottom - vis_h)

            # Create crop region dict for mss
            crop_region = {
                'left': mon_left + left,
                'top': mon_top + top,
                'width': right - left,
                'height': bottom - top
            }
                
            # Capture cropped frame. mss / the underlying XGetImage call can
            # transiently fail right after an xrandr rotation — the X server
            # has new geometry but the existing mss handle still holds a
            # stale reference. Refresh and retry once; on second failure
            # skip this frame rather than tearing down the whole stream.
            try:
                sct_img = sct.grab(crop_region)
            except Exception as e:
                logger.warning(f"[Screen] grab failed ({e}); refreshing mss and retrying")
                try:
                    sct.close()
                except Exception:
                    pass
                sct = mss.mss()
                try:
                    current_monitor[0] = get_current_monitor_info()
                    mon_w = current_monitor[0]['width']
                    mon_h = current_monitor[0]['height']
                    mon_left = current_monitor[0].get('left', 0)
                    mon_top = current_monitor[0].get('top', 0)
                    crop_region = {
                        'left': mon_left, 'top': mon_top,
                        'width': mon_w, 'height': mon_h,
                    }
                    sct_img = sct.grab(crop_region)
                except Exception as e2:
                    logger.warning(f"[Screen] grab retry also failed ({e2}); skipping frame")
                    await asyncio.sleep(0.1)
                    continue

            # Convert to PIL Image for resizing.
            pil_img = Image.frombytes('RGB', (sct_img.width, sct_img.height), sct_img.rgb)
            
            # Draw cursor overlay onto the frame
            try:
                result = subprocess.run(
                    ['xdotool', 'getmouselocation'],
                    capture_output=True, text=True, timeout=0.1
                )
                if result.returncode == 0:
                    parts = result.stdout.strip().split()
                    cx = int(parts[0].split(':')[1])  # x:1234
                    cy = int(parts[1].split(':')[1])  # y:5678

                    # Publish cursor position back to mobile every frame
                    _cursor_frame_count += 1
                    norm_x = round((cx - mon_left) / mon_w, 4) if mon_w > 0 else 0.5
                    norm_y = round((cy - mon_top) / mon_h, 4) if mon_h > 0 else 0.5
                    heartbeat = (_cursor_frame_count % 60 == 0)  # force every 2s
                    if heartbeat or abs(norm_x - _last_pub_x) + abs(norm_y - _last_pub_y) > 0.001:
                        cursor_msg = json.dumps({
                            "x": norm_x, "y": norm_y,
                            "sw": mon_w, "sh": mon_h,
                            "ox": mon_left, "oy": mon_top
                        }).encode()
                        asyncio.create_task(
                            room.local_participant.publish_data(
                                cursor_msg,
                                reliable=False,
                                topic="cursor_position"
                            )
                        )
                        _last_pub_x, _last_pub_y = norm_x, norm_y

                    # Map absolute cursor pos to crop-relative coords
                    # cx/cy are absolute (across all monitors), crop_region starts at mon_left+left
                    crop_abs_left = mon_left + left
                    crop_abs_top = mon_top + top
                    rel_x = cx - crop_abs_left
                    rel_y = cy - crop_abs_top

                    crop_w = right - left
                    crop_h = bottom - top
                    in_bounds = 0 <= rel_x < crop_w and 0 <= rel_y < crop_h

                    # Cursor overlay removed — mobile app renders its own cursor
            except Exception as e:
                pass
            
            # Resize to output resolution (preserving aspect ratio)
            rot = view_state.rotation
            if rot != 0:
                pil_img = pil_img.rotate(-rot, expand=True)
                
            # Track dims always match current capture aspect (republished on
            # rotation), so direct resize fills the frame — no letterbox.
            frame_w, frame_h = target_w, target_h
            resized = pil_img.resize((frame_w, frame_h), Image.Resampling.LANCZOS)
            
            # Convert to YUV420P (I420) for maximum encoder compatibility
            yuv_img = resized.convert('YCbCr')
            y, cb, cr = yuv_img.split()
            
            # LiveKit I420 expects Y, U, V planes concatenated
            y_data = np.array(y).tobytes()
            u_data = np.array(cb.resize((frame_w // 2, frame_h // 2), Image.Resampling.LANCZOS)).tobytes()
            v_data = np.array(cr.resize((frame_w // 2, frame_h // 2), Image.Resampling.LANCZOS)).tobytes()

            frame = rtc.VideoFrame(
                width=frame_w,
                height=frame_h,
                type=rtc.VideoBufferType.I420,
                data=y_data + u_data + v_data
            )

            source.capture_frame(frame)
            await asyncio.sleep(1 / 30)  # 30 FPS target
            
    except Exception as e:
        logger.error(f"[Screen] Stream error: {e}")
    finally:
        logger.info("[Screen] Stream ended.")
        try:
            from core.display_controller import controller as _disp
            await _disp.session_end()
        except Exception as e:
            logger.warning(f"[Screen] session_end failed on stream finish: {e}")
