import mss
import mss.tools
import subprocess
from PIL import Image
from typing import Optional, Tuple

def get_monitors():
    """Get all monitor geometries from mss."""
    with mss.MSS() as sct:
        return sct.monitors  # index 0 = combined, 1+ = individual

def get_active_window_geometry() -> Optional[dict]:
    """Get the geometry of the currently active window via xdotool."""
    try:
        wid = subprocess.check_output(["xdotool", "getactivewindow"], text=True).strip()
        geo = subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", wid], text=True)
        info = {}
        for line in geo.strip().split("\n"):
            k, v = line.split("=")
            info[k] = int(v) if v.isdigit() else v
        return info  # WINDOW, X, Y, WIDTH, HEIGHT, SCREEN
    except Exception:
        return None

def get_window_geometry_by_name(name: str) -> Optional[dict]:
    """Find a window by partial title and return its geometry."""
    try:
        wids = subprocess.check_output(
            ["xdotool", "search", "--name", name], text=True
        ).strip().split("\n")
        if not wids or not wids[0]:
            return None
        wid = wids[0]
        geo = subprocess.check_output(["xdotool", "getwindowgeometry", "--shell", wid], text=True)
        info = {}
        for line in geo.strip().split("\n"):
            k, v = line.split("=")
            info[k] = int(v) if v.isdigit() else v
        return info
    except Exception:
        return None

def find_monitor_for_window(window_x: int, window_y: int) -> Tuple[int, dict]:
    """
    Given absolute window coordinates, find which monitor it's on.
    Returns (monitor_index, monitor_dict).
    """
    monitors = get_monitors()
    for i in range(1, len(monitors)):  # skip combined (index 0)
        m = monitors[i]
        if (m["left"] <= window_x < m["left"] + m["width"] and
            m["top"] <= window_y < m["top"] + m["height"]):
            return i, m
    # Fallback to primary
    return 1, monitors[1]

def capture_full(monitor_index=1):
    """
    Capture the full screen of a specific monitor.
    monitor_index=1 is usually the primary monitor.
    monitor_index=0 captures all monitors combined.
    Returns a PIL Image.
    """
    with mss.MSS() as sct:
        try:
            monitor = sct.monitors[monitor_index]
            sct_img = sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
        except IndexError:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

def capture_active_window_monitor() -> Tuple[Image.Image, dict]:
    """
    Capture the monitor where the active window is located.
    Returns (image, monitor_dict) so callers can compute absolute offsets.
    """
    win = get_active_window_geometry()
    if win:
        idx, mon = find_monitor_for_window(win.get("X", 0), win.get("Y", 0))
    else:
        monitors = get_monitors()
        idx, mon = 1, monitors[1]
    
    img = capture_full(monitor_index=idx)
    return img, mon

def capture_window_monitor(window_name: str) -> Tuple[Image.Image, dict]:
    """
    Capture the monitor where a specific named window is located.
    Returns (image, monitor_dict) so callers can compute absolute offsets.
    """
    win = get_window_geometry_by_name(window_name)
    if win:
        idx, mon = find_monitor_for_window(win.get("X", 0), win.get("Y", 0))
    else:
        monitors = get_monitors()
        idx, mon = 1, monitors[1]
    
    img = capture_full(monitor_index=idx)
    return img, mon

def capture_region(left, top, width, height):
    """
    Capture a specific region of the screen (absolute coordinates).
    Returns a PIL Image.
    """
    with mss.MSS() as sct:
        region = {'top': int(top), 'left': int(left), 'width': int(width), 'height': int(height)}
        sct_img = sct.grab(region)
        return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
