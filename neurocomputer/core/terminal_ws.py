"""WebSocket ↔ pty bridge for tmux terminal tabs.

One :class:`PtyBridge` per live WebSocket connection:

* reads pty stdout and forwards as binary ws frames,
* receives binary ws frames and writes them to pty stdin,
* receives text JSON control frames:
  ``{"type":"resize","cols":N,"rows":N}`` and ``{"type":"ping"}``.

Uses ``ptyprocess.PtyProcess`` (already in the project venv) to spawn
``tmux attach -t <name>`` with ``TERM=xterm-256color``. Multi-attach to
the same tmux session is safe — tmux handles that natively.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
import ptyprocess

from . import tmux_manager

logger = logging.getLogger(__name__)

READ_CHUNK = 4096


class PtyBridge:
    def __init__(self, ws: WebSocket, tmux_session: str):
        self.ws = ws
        self.session = tmux_session
        self.pty: Optional[ptyprocess.PtyProcess] = None
        self._closed = False

    async def run(self) -> None:
        await self._spawn_pty()
        try:
            await self.ws.send_text(json.dumps({"type": "ready"}))
        except Exception:
            await self._cleanup()
            return

        reader_task = asyncio.create_task(self._pump_pty_to_ws())
        writer_task = asyncio.create_task(self._pump_ws_to_pty())
        try:
            done, pending = await asyncio.wait(
                {reader_task, writer_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        finally:
            await self._cleanup()

    async def _spawn_pty(self) -> None:
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        # Idempotent: apply mouse-on / history-limit to this session so
        # wheel-forwarding works for sessions that pre-date these defaults.
        import subprocess as _sp
        for opt, val in (("mouse", "on"), ("history-limit", "10000")):
            try:
                _sp.run(
                    ["tmux", "set-option", "-t", self.session, opt, val],
                    capture_output=True, timeout=2,
                )
            except Exception:
                pass
        # ``ptyprocess.spawn`` forks; run in a worker thread so the event
        # loop stays responsive.
        self.pty = await asyncio.to_thread(
            ptyprocess.PtyProcess.spawn,
            ["tmux", "attach", "-t", self.session],
            env=env,
            dimensions=(30, 120),
        )

    async def _pump_pty_to_ws(self) -> None:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        fd = self.pty.fd if self.pty else -1

        def _on_readable():
            try:
                data = os.read(fd, READ_CHUNK)
            except OSError:
                data = b""
            if not data:
                loop.call_soon_threadsafe(queue.put_nowait, None)
                try:
                    loop.remove_reader(fd)
                except Exception:
                    pass
                return
            loop.call_soon_threadsafe(queue.put_nowait, data)

        try:
            loop.add_reader(fd, _on_readable)
        except Exception as e:
            logger.exception("[terminal_ws] add_reader failed: %s", e)
            return

        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                try:
                    await self.ws.send_bytes(chunk)
                except Exception:
                    break
        finally:
            try:
                loop.remove_reader(fd)
            except Exception:
                pass
            try:
                code = self.pty.exitstatus if self.pty else 0
                await self.ws.send_text(json.dumps({
                    "type": "exit",
                    "code": code if code is not None else 0,
                }))
            except Exception:
                pass

    async def _pump_ws_to_pty(self) -> None:
        while True:
            try:
                msg = await self.ws.receive()
            except WebSocketDisconnect:
                break
            except Exception:
                break
            mtype = msg.get("type")
            if mtype == "websocket.disconnect":
                break
            # Starlette WebSocket.receive returns a dict with either
            # 'bytes' or 'text' (one of them non-None).
            if msg.get("bytes") is not None and self.pty is not None:
                try:
                    os.write(self.pty.fd, msg["bytes"])
                except OSError:
                    break
                continue
            if msg.get("text") is not None:
                try:
                    payload = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                t = payload.get("type")
                if t == "resize" and self.pty is not None:
                    cols = int(payload.get("cols") or 80)
                    rows = int(payload.get("rows") or 24)
                    try:
                        self.pty.setwinsize(rows, cols)
                    except Exception:
                        pass
                elif t == "tmux-scroll":
                    action = str(payload.get("action") or "")
                    try:
                        count = int(payload.get("count") or 1)
                    except (TypeError, ValueError):
                        count = 1
                    count = max(1, min(200, count))
                    logger.info("[tmux-scroll] action=%s count=%s", action, count)
                    await asyncio.to_thread(
                        tmux_manager.scroll, self.session, action, count
                    )
                elif t == "ping":
                    try:
                        await self.ws.send_text(json.dumps({"type": "pong"}))
                    except Exception:
                        break

    async def _cleanup(self) -> None:
        if self._closed:
            return
        self._closed = True
        pty = self.pty
        self.pty = None
        if pty is not None:
            try:
                if pty.isalive():
                    pty.kill(signal.SIGHUP)
            except Exception:
                pass
            try:
                pty.close(force=True)
            except Exception:
                pass
