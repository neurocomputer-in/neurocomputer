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
    assert any(argv[:2] == ["xrandr", "--query"] for argv in calls)
    assert any(argv[:3] == ["xsetroot", "-cursor_name", "blank"] for argv in calls)
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
    # Rotation is now a single atomic xrandr call with multiple --output args.
    rotate_calls = [a for a in calls if a[:1] == ["xrandr"] and "--output" in a]
    assert len(rotate_calls) == 1
    argv = rotate_calls[0]
    # Both connected outputs must appear, each paired with --rotate left.
    assert argv.count("--output") == 2
    assert argv.count("--rotate") == 2
    for name in ("HDMI-0", "HDMI-1"):
        i = argv.index(name)
        assert argv[i + 1] == "--rotate"
        assert argv[i + 2] == "left"


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
    rotate_calls = [a for a in calls if a[:1] == ["xrandr"] and "--output" in a]
    assert len(rotate_calls) == 1
    argv = rotate_calls[0]
    # Snapshot restore runs all outputs atomically, each at its pre-session value.
    for name, expected_rot in (("HDMI-0", "left"), ("HDMI-1", "normal")):
        i = argv.index(name)
        assert argv[i + 1] == "--rotate"
        assert argv[i + 2] == expected_rot
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
        await ctrl.handle_orientation("portrait", locked=False)
    assert not any(a[:2] == ["xrandr", "--output"] for a in calls)
