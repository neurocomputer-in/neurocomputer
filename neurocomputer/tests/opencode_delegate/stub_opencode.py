"""
Minimal aiohttp server that impersonates enough of `opencode serve` 1.4.6
for delegate tests. Scriptable: tests push event dicts into a per-session
event script; the stub's SSE endpoint flushes them when a POST arrives.

Usage (in a test):
    stub = StubOpenCode()
    await stub.start()
    stub.script_turn("ses_A", [...event dicts...])
    # ...post to stub.url, drive delegate...
    await stub.stop()
"""
import asyncio
import json
import socket
import uuid
from typing import Any

from aiohttp import web


class StubOpenCode:
    def __init__(self):
        self._app = web.Application()
        self._app.router.add_get("/global/health", self._health)
        self._app.router.add_get("/global/event", self._event_stream)
        self._app.router.add_post("/session", self._create_session)
        self._app.router.add_get("/session/{sid}", self._get_session)
        self._app.router.add_post("/session/{sid}/message", self._post_message)
        self._runner: web.AppRunner | None = None
        self._site: web.TCPSite | None = None
        self._port: int = 0
        self._sessions: dict[str, dict] = {}
        self._scripts: dict[str, list[list[dict]]] = {}
        self._active_subscribers: list[asyncio.Queue] = []
        self._post_behavior: dict[str, str] = {}
        self.post_log: list[dict] = []
        self.fail_next_event_connections: int = 0
        self.stall_event_stream: bool = False

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._port}"

    async def start(self) -> None:
        # Bind to an ephemeral port we pick ourselves — avoids aiohttp-internal
        # socket-lookup gymnastics and is stable across versions.
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        self._port = s.getsockname()[1]
        s.close()

        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()
        self._site = web.TCPSite(self._runner, "127.0.0.1", self._port,
                                 reuse_address=True)
        await self._site.start()

    async def stop(self) -> None:
        # Close any open SSE streams so their handlers exit.
        for q in list(self._active_subscribers):
            try:
                q.put_nowait({"__stub_shutdown__": True})
            except asyncio.QueueFull:
                pass
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    def script_turn(self, sid: str, events: list[dict]) -> None:
        """Queue one turn's worth of events to be flushed on the NEXT POST
        to /session/{sid}/message (or to any session when no specific
        pending script is set for the target sid)."""
        self._scripts.setdefault(sid, []).append(list(events))

    def set_post_behavior(self, sid: str, behavior: str) -> None:
        self._post_behavior[sid] = behavior

    def drop_next_sse_connection(self) -> None:
        self.fail_next_event_connections += 1

    # ── HTTP handlers ────────────────────────────────────────────────

    async def _health(self, _req: web.Request) -> web.Response:
        return web.json_response({"healthy": True, "version": "1.4.6-stub"})

    async def _create_session(self, req: web.Request) -> web.Response:
        body = await req.json() if req.can_read_body else {}
        sid = f"ses_{uuid.uuid4().hex[:18]}"
        self._sessions[sid] = {"id": sid, "title": body.get("title", ""),
                               "time": {"created": 1, "updated": 1}}
        return web.json_response(self._sessions[sid])

    async def _get_session(self, req: web.Request) -> web.Response:
        sid = req.match_info["sid"]
        if sid not in self._sessions:
            # Treat as existing (tests often pass arbitrary sids via script).
            self._sessions[sid] = {"id": sid, "title": "", "time": {"created": 1, "updated": 1}}
        return web.json_response(self._sessions[sid])

    async def _post_message(self, req: web.Request) -> web.Response:
        sid = req.match_info["sid"]
        body = await req.json()
        self.post_log.append({"sid": sid, "body": body,
                              "at": asyncio.get_event_loop().time()})

        behavior = self._post_behavior.get(sid, "normal")
        if behavior == "404":
            return web.Response(status=404, text="not found")
        if behavior == "stall":
            await asyncio.sleep(3600)

        pending = self._scripts.get(sid, [])
        if pending:
            events = pending.pop(0)
            for q in list(self._active_subscribers):
                for evt in events:
                    wrapped = {"directory": "/stub", "project": "stub-proj",
                               "payload": evt}
                    try:
                        q.put_nowait(wrapped)
                    except asyncio.QueueFull:
                        pass
        return web.json_response({"ok": True})

    async def _event_stream(self, req: web.Request) -> web.StreamResponse:
        if self.fail_next_event_connections > 0:
            self.fail_next_event_connections -= 1
            return web.Response(status=500, text="stub forcing failure")

        resp = web.StreamResponse(
            status=200,
            headers={"Content-Type": "text/event-stream",
                     "Cache-Control": "no-cache"},
        )
        await resp.prepare(req)
        queue: asyncio.Queue = asyncio.Queue(maxsize=4096)
        self._active_subscribers.append(queue)
        await queue.put({"payload": {"type": "server.connected", "properties": {}}})
        try:
            while True:
                if self.stall_event_stream:
                    await asyncio.sleep(0.1)
                    continue
                evt = await queue.get()
                if isinstance(evt, dict) and evt.get("__stub_shutdown__"):
                    break
                line = f"data: {json.dumps(evt)}\n\n".encode("utf-8")
                try:
                    await resp.write(line)
                except (ConnectionResetError, asyncio.CancelledError):
                    break
        except asyncio.CancelledError:
            pass
        finally:
            if queue in self._active_subscribers:
                self._active_subscribers.remove(queue)
        return resp
