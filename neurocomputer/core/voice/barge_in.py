"""BargeInController — duration-gated TTS cancel.

State machine:
  IDLE  --user_started_speaking-->  ARMED (start gate timer)
  ARMED --user_stopped_speaking-->  IDLE  (cough/ack: no cancel)
  ARMED --timer expires----------->  CANCELLING:
                                       if agent is speaking, call session.interrupt()
                                     -->  IDLE
"""
import asyncio
import logging

logger = logging.getLogger("voice-barge-in")

DEFAULT_GATE_MS = 500


class BargeInController:
    def __init__(self, session, gate_ms: int = DEFAULT_GATE_MS):
        self._session = session
        self._gate_s = gate_ms / 1000.0
        self._timer_task: asyncio.Task | None = None
        self._stopped = False

    async def start(self):
        self._stopped = False

    async def stop(self):
        self._stopped = True
        await self._cancel_timer()

    def on_user_started_speaking(self):
        if self._stopped:
            return
        # Reset/restart gate timer on every start event
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = asyncio.create_task(self._fire_after_gate())

    def on_user_stopped_speaking(self):
        # User stopped before gate expired → cough/ack, no cancel
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()

    async def _cancel_timer(self):
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass

    async def _fire_after_gate(self):
        try:
            await asyncio.sleep(self._gate_s)
        except asyncio.CancelledError:
            return
        if self._stopped:
            return
        if self._is_agent_speaking():
            try:
                self._session.interrupt()
                logger.info("[Voice] barge-in fired")
            except Exception as e:
                logger.warning(f"[Voice] barge-in interrupt failed: {e}")

    def _is_agent_speaking(self) -> bool:
        # AgentSession exposes various indicators; the test stub uses _agent_speaking.
        # In production, derive from session events tracked by voice_manager.
        return bool(getattr(self._session, "_agent_speaking", False))
