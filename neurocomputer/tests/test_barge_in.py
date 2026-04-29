"""Tests for BargeInController — 500ms-gated TTS cancel."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from core.voice.barge_in import BargeInController


@pytest.fixture
def fake_session():
    s = MagicMock()
    s.interrupt = MagicMock()
    s._agent_speaking = False  # mutable flag the test controls
    return s


async def test_cough_below_500ms_does_not_cancel(fake_session):
    """User speech for <500ms should NOT trigger cancel."""
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=100)  # short gate for tests
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.05)  # half the gate
    ctrl.on_user_stopped_speaking()
    await asyncio.sleep(0.2)   # let any deferred fire

    assert fake_session.interrupt.call_count == 0
    await ctrl.stop()


async def test_real_interrupt_above_gate_cancels(fake_session):
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=100)
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.2)  # past the gate
    # User still speaking when timer fires → cancel
    assert fake_session.interrupt.call_count == 1
    ctrl.on_user_stopped_speaking()
    await ctrl.stop()


async def test_no_cancel_when_agent_silent(fake_session):
    """If agent isn't currently speaking, no cancel needed."""
    fake_session._agent_speaking = False
    ctrl = BargeInController(fake_session, gate_ms=100)
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.2)
    ctrl.on_user_stopped_speaking()
    assert fake_session.interrupt.call_count == 0
    await ctrl.stop()


async def test_rapid_stop_start_resets_timer(fake_session):
    """Multiple coughs in succession should each reset; none should cancel."""
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=200)
    await ctrl.start()

    for _ in range(3):
        ctrl.on_user_started_speaking()
        await asyncio.sleep(0.05)  # well under 200ms
        ctrl.on_user_stopped_speaking()
        await asyncio.sleep(0.01)

    await asyncio.sleep(0.3)  # let any leftover timer fire
    assert fake_session.interrupt.call_count == 0
    await ctrl.stop()


async def test_stop_cancels_pending_timer(fake_session):
    """Calling stop() must cancel any pending cancellation timer."""
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=500)
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.1)
    await ctrl.stop()
    await asyncio.sleep(0.6)  # past the gate
    assert fake_session.interrupt.call_count == 0
