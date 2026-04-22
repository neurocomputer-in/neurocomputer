"""
Shared SSE consumer for opencode's /global/event stream.

One SSEConsumer instance per Python process owns a single persistent
connection, parses v1.4.6 envelopes, and routes events to per-session
SessionBus objects. Delegate turns (run()) coordinate via each bus's
lock + status + queue to serialize POSTs and consume their own events.
"""
from __future__ import annotations

import asyncio
import json
from typing import Literal

import aiohttp


SessionStatus = Literal["idle", "busy", "unknown"]


class SessionBus:
    def __init__(self, sid: str) -> None:
        self.sid = sid
        self.lock = asyncio.Lock()
        self.status: SessionStatus = "unknown"
        self.idle_ev = asyncio.Event()
        self.queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=2048)


class SSEConsumer:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._buses: dict[str, SessionBus] = {}
        self._task: asyncio.Task | None = None
        self._session: aiohttp.ClientSession | None = None
        self._stopping = False

    async def start(self) -> None:
        if self._task is not None:
            return
        self._session = aiohttp.ClientSession()
        self._task = asyncio.create_task(self._run_forever(), name="opencode-sse")

    async def stop(self) -> None:
        self._stopping = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self._session:
            await self._session.close()
            self._session = None

    def bus_for(self, sid: str) -> SessionBus:
        if sid not in self._buses:
            self._buses[sid] = SessionBus(sid)
        return self._buses[sid]

    async def _run_forever(self) -> None:
        """Open /global/event, parse SSE, dispatch. Reconnect with backoff."""
        backoff = 1.0
        assert self._session is not None
        while not self._stopping:
            try:
                async with self._session.get(
                    f"{self._base_url}/global/event",
                    headers={"Accept": "text/event-stream"},
                    timeout=aiohttp.ClientTimeout(total=None, sock_read=None),
                ) as resp:
                    if resp.status != 200:
                        raise RuntimeError(f"/global/event returned {resp.status}")
                    backoff = 1.0
                    async for raw in resp.content:
                        line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                        if not line.startswith("data:"):
                            continue
                        payload_str = line[5:].strip()
                        if not payload_str:
                            continue
                        try:
                            envelope = json.loads(payload_str)
                        except json.JSONDecodeError:
                            continue
                        self._dispatch(envelope)
            except asyncio.CancelledError:
                raise
            except Exception:
                for bus in self._buses.values():
                    bus.status = "unknown"
                    bus.idle_ev.clear()
            if self._stopping:
                break
            await asyncio.sleep(min(backoff, 30.0))
            backoff = min(backoff * 2.0, 30.0)

    def _dispatch(self, envelope: dict) -> None:
        payload = envelope.get("payload") or {}
        etype = payload.get("type", "")
        props = payload.get("properties") or {}
        sid = props.get("sessionID") or payload.get("aggregateID")
        if not sid:
            return
        bus = self.bus_for(sid)
        event = {"type": etype, "properties": props}

        # Track session status before queuing so consumers see consistent state.
        if etype == "session.status":
            status_type = (props.get("status") or {}).get("type", "")
            if status_type == "idle":
                bus.status = "idle"
                bus.idle_ev.set()
            elif status_type == "busy":
                bus.status = "busy"
                bus.idle_ev.clear()

        try:
            bus.queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                bus.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            bus.queue.put_nowait(event)
