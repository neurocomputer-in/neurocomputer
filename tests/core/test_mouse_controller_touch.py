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
    assert calls[0] == ["xdotool", "mousemove", "100", "100"]
    assert calls[1] == ["xdotool", "mousedown", "1"]
    assert ["xdotool", "mouseup", "1"] in calls
    assert ["xdotool", "mousemove", "900", "900"] in calls


@pytest.mark.asyncio
async def test_touch_tap_respects_monitor_offset():
    mc = MouseController(screen_width=1920, screen_height=1080, monitor_offset=(1920, 0))
    calls, run = _collect_xdotool_calls()
    with patch("core.mouse_controller.subprocess.run", side_effect=run):
        await mc.handle_event({"type": "touch_tap", "nx": 0.0, "ny": 0.0})
    assert calls[0] == ["xdotool", "mousemove", "1920", "0"]
