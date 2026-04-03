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

async def start_desktop_stream(room: rtc.Room, room_name: str = "default"):
    """
    Captures the desktop screen and publishes it as a video track.
    
    Args:
        room: Connected LiveKit room instance.
    """
    logger.info("[Screen] Starting desktop stream...")
    
    # 1. Probe monitor dimensions first to create a correctly-sized VideoSource
    sct = mss.mss()
    initial_monitor = sct.monitors[_current_monitor_index] if _current_monitor_index < len(sct.monitors) else sct.monitors[1]
    mon_w = initial_monitor['width']
    mon_h = initial_monitor['height']
    
    # Target output height is fixed at 720p; scale width to preserve aspect ratio.
    # This avoids stretching/cropping when the backend resizes frames.
    target_h = 720
    target_w = int(mon_w / mon_h * target_h)
    # Ensure both dimensions are even numbers (required for I420 / YUV420)
    target_w = target_w if target_w % 2 == 0 else target_w + 1
    target_h = target_h if target_h % 2 == 0 else target_h + 1
    
    logger.info(f"[Screen] Monitor: {mon_w}x{mon_h} → Stream: {target_w}x{target_h}")

    # 2. Create Video Source sized to the actual aspect ratio
    source = rtc.VideoSource(target_w, target_h)
    
    # 2. Create Track
    # We use "desktop" name, and let LiveKit infer or default the source type 
    # (usually CAMERA by default if not specified, which works fine here)
    track = rtc.LocalVideoTrack.create_video_track("desktop", source)

    # 3. Publish Track with ScreenShare source type so clients can subscribe properly
    options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_SCREENSHARE)
    publication = await room.local_participant.publish_track(track, options)


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

    # 5. Set up mouse controller for touchpad events from mobile
    # Pass monitor offset so mouse movements are correct
    mouse_controller = MouseController(mon_w, mon_h, monitor_offset=(mon_left, mon_top))
    global _active_mouse_controller
    _active_mouse_controller = mouse_controller

    @room.on("data_received")
    def _on_data_received(data_packet):
        """Handle incoming data packets — dispatch mouse_control events."""
        if data_packet.topic == "mouse_control":
            try:
                msg = json.loads(data_packet.data.decode("utf-8"))
                asyncio.create_task(mouse_controller.handle_event(msg))
            except Exception as e:
                logger.error(f"[Screen] Failed to parse mouse event: {e}")

    logger.info("[Screen] Mouse controller ready, listening for touchpad events")

    try:
        while True:
            # Check connection
            if room.connection_state != rtc.ConnectionState.CONN_CONNECTED:
                logger.info("[Screen] Room disconnected, stopping stream.")
                break

            # Dynamically get current monitor in case it changed
            current_monitor[0] = get_current_monitor_info()
            mon_w = current_monitor[0]['width']
            mon_h = current_monitor[0]['height']
            mon_left = current_monitor[0].get('left', 0)
            mon_top = current_monitor[0].get('top', 0)


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
                
            # Capture cropped frame
            sct_img = sct.grab(crop_region)
            
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

                    # Map absolute cursor pos to crop-relative coords
                    # cx/cy are absolute (across all monitors), crop_region starts at mon_left+left
                    crop_abs_left = mon_left + left
                    crop_abs_top = mon_top + top
                    rel_x = cx - crop_abs_left
                    rel_y = cy - crop_abs_top

                    crop_w = right - left
                    crop_h = bottom - top
                    in_bounds = 0 <= rel_x < crop_w and 0 <= rel_y < crop_h

                    # Debug: draw a always-visible test cursor at center if cursor is out of bounds
                    draw = ImageDraw.Draw(pil_img)
                    if in_bounds:
                        r = 6  # Larger cursor
                        # Bright red outline for visibility
                        draw.ellipse(
                            [rel_x - r - 2, rel_y - r - 2, rel_x + r + 2, rel_y + r + 2],
                            fill=None, outline=(255, 0, 0), width=3
                        )
                        # White filled center
                        draw.ellipse(
                            [rel_x - r, rel_y - r, rel_x + r, rel_y + r],
                            fill=(255, 255, 255), outline=(255, 255, 255)
                        )
                        # Crosshair lines
                        line_len = 15
                        draw.line([rel_x - line_len, rel_y, rel_x - r - 3, rel_y], fill=(255, 255, 255), width=2)
                        draw.line([rel_x + r + 3, rel_y, rel_x + line_len, rel_y], fill=(255, 255, 255), width=2)
                        draw.line([rel_x, rel_y - line_len, rel_x, rel_y - r - 3], fill=(255, 255, 255), width=2)
                        draw.line([rel_x, rel_y + r + 3, rel_x, rel_y + line_len], fill=(255, 255, 255), width=2)

                    else:
                        # Debug: draw test dot at center when cursor is out of bounds
                        center_x = crop_w // 2
                        center_y = crop_h // 2
                        r = 10
                        draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r],
                            fill=(0, 255, 0), outline=(0, 255, 0))


                    # Debug: Always draw a visible marker in top-left to verify rendering
                    draw = ImageDraw.Draw(pil_img)
                    draw.rectangle([10, 10, 30, 30], fill=(0, 255, 255), outline=(0, 255, 255))
                    draw.text((35, 15), f"M{_current_monitor_index}", fill=(0, 255, 255))
            except Exception as e:
                pass
            
            # Resize to output resolution (preserving aspect ratio)
            rot = view_state.rotation
            if rot != 0:
                pil_img = pil_img.rotate(-rot, expand=True)
                
            # If 90 or 270 deg, swap the target dimensions
            if rot == 90 or rot == 270:
                frame_w, frame_h = target_h, target_w  # Swap
            else:
                frame_w, frame_h = target_w, target_h  # Normal

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
