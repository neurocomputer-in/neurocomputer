# Tmux Terminal Tabs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add terminal tabs backed by persistent tmux sessions, rendered via xterm.js over a dedicated WebSocket, with metadata reusing the conversation store.

**Architecture:** Backend spawns per-WS `ptyprocess` running `tmux attach -t <name>`; tmux daemon persists sessions across FastAPI restarts. Metadata stored in `conversations/<id>.json` with `type:"terminal"`, `tmux_session`, `workdir` fields. Frontend has a `TerminalPanel` sibling to `ChatPanel` chosen by tab `type`. Session name pattern: `neuro-<ws>-<proj>-<8hex>` so we can list per-project.

**Tech Stack:** Python 3.12 + FastAPI + `ptyprocess` (installed) + `tmux` 3.4 (installed) · React + Redux Toolkit + xterm.js + `xterm-addon-fit` / `-webgl` / `-web-links`.

---

## Task 1: tmux capability probe + session manager module

**Files:**
- Create: `core/tmux_manager.py`
- Test: `tests/test_tmux_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_tmux_manager.py
import re, subprocess, time, pytest
from core import tmux_manager as tm


def _cleanup(name):
    subprocess.run(["tmux", "kill-session", "-t", name],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def test_tmux_available():
    assert tm.tmux_available() is True


def test_make_session_name_pattern():
    name = tm.make_session_name("default", "main-default")
    assert re.fullmatch(r"neuro-default-main-default-[0-9a-f]{8}", name)
    # Two calls give different suffixes
    assert name != tm.make_session_name("default", "main-default")


def test_slug_unsafe_chars():
    name = tm.make_session_name("My Space", "Proj/X!")
    assert re.fullmatch(r"neuro-my-space-proj-x-[0-9a-f]{8}", name)


def test_new_session_is_idempotent(tmp_path):
    name = tm.make_session_name("t", "p")
    try:
        tm.new_session(name, str(tmp_path))
        assert tm.session_exists(name)
        tm.new_session(name, str(tmp_path))  # second call must not error
        assert tm.session_exists(name)
    finally:
        _cleanup(name)


def test_list_sessions_filter(tmp_path):
    a = tm.make_session_name("workA", "projA")
    b = tm.make_session_name("workA", "projB")
    try:
        tm.new_session(a, str(tmp_path))
        tm.new_session(b, str(tmp_path))
        rows = tm.list_sessions(prefix="neuro-worka-proja-")
        names = [r["name"] for r in rows]
        assert a in names
        assert b not in names
    finally:
        _cleanup(a)
        _cleanup(b)


def test_kill_session(tmp_path):
    name = tm.make_session_name("t", "p")
    tm.new_session(name, str(tmp_path))
    assert tm.session_exists(name)
    tm.kill_session(name)
    assert not tm.session_exists(name)
```

- [ ] **Step 2: Verify tests fail**

Run: `pytest tests/test_tmux_manager.py -v`
Expected: `ModuleNotFoundError: No module named 'core.tmux_manager'`

- [ ] **Step 3: Implement `core/tmux_manager.py`**

```python
"""tmux session manager — thin wrapper around the tmux CLI.

All functions are synchronous shell-outs; tmux CLI is fast
(microseconds) so callers can invoke directly from async handlers
without threading.
"""
from __future__ import annotations

import os
import re
import secrets
import shutil
import subprocess
from typing import Optional

SESSION_PREFIX = "neuro-"
_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def tmux_available() -> bool:
    """True if the tmux binary is on PATH."""
    return shutil.which("tmux") is not None


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = _SLUG_RE.sub("-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "x"


def make_session_name(workspace_id: str, project_id: str) -> str:
    """Pattern: neuro-<ws>-<proj>-<8hex>. Slugs are lowercase,
    [a-z0-9-] only, collapsed hyphens."""
    return (
        f"{SESSION_PREFIX}{_slug(workspace_id)}-{_slug(project_id)}"
        f"-{secrets.token_hex(4)}"
    )


def session_exists(name: str) -> bool:
    r = subprocess.run(
        ["tmux", "has-session", "-t", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def new_session(name: str, workdir: Optional[str] = None) -> None:
    """Idempotent: `new-session -A -d` attaches if present, else creates."""
    cmd = ["tmux", "new-session", "-A", "-d", "-s", name]
    if workdir:
        cmd += ["-c", workdir]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {r.stderr.strip()}")


def kill_session(name: str) -> bool:
    r = subprocess.run(
        ["tmux", "kill-session", "-t", name],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return r.returncode == 0


def list_sessions(prefix: Optional[str] = None) -> list[dict]:
    """Return sessions as list of dicts. Empty list if daemon not running."""
    r = subprocess.run(
        ["tmux", "list-sessions", "-F",
         "#{session_name}\t#{session_created}\t#{session_attached}\t#{session_windows}"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return []
    out = []
    for line in r.stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) != 4:
            continue
        name, created, attached, windows = parts
        if prefix and not name.startswith(prefix):
            continue
        out.append({
            "name": name,
            "created_at": int(created),
            "attached_clients": int(attached),
            "windows": int(windows),
        })
    return out
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tests/test_tmux_manager.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add core/tmux_manager.py tests/test_tmux_manager.py
git commit -m "feat(terminal): add tmux_manager module + tests"
```

---

## Task 2: Conversation data model — terminal fields

**Files:**
- Modify: `core/conversation.py`

- [ ] **Step 1: Add fields to `__init__` load path**

Open `core/conversation.py`. After the existing `self._selection_type = …` load line, add:

```python
            self._type = data.get("type") or "chat"
            self._tmux_session = data.get("tmux_session") or None
            self._workdir = data.get("workdir") or None
```

And initialize defaults at top of `__init__` alongside the other `self._…` assignments:

```python
        self._type = "chat"
        self._tmux_session = None
        self._workdir = None
```

- [ ] **Step 2: Add getters/setters**

After the existing `set_selection_type` method:

```python
    def get_type(self) -> str:
        return self._type or "chat"

    def set_type(self, t: str) -> str:
        self._type = t if t in ("chat", "terminal") else "chat"
        self._save()
        return self._type

    def get_tmux_session(self) -> str | None:
        return self._tmux_session or None

    def set_tmux_session(self, name: str | None) -> str | None:
        self._tmux_session = (name or "").strip() or None
        self._save()
        return self._tmux_session

    def get_workdir(self) -> str | None:
        return self._workdir or None

    def set_workdir(self, path: str | None) -> str | None:
        self._workdir = (path or "").strip() or None
        self._save()
        return self._workdir
```

- [ ] **Step 3: Persist the fields in `_save`**

In the existing `_save` dict, add alongside the other keys:

```python
            "type": self._type or "chat",
            "tmux_session": self._tmux_session or None,
            "workdir": self._workdir or None,
```

- [ ] **Step 4: Syntax check**

Run: `python3 -c "from core.conversation import Conversation; c = Conversation('__test_cid_del__'); c.set_type('terminal'); c.set_tmux_session('neuro-x-y-00000000'); c.set_workdir('/tmp'); assert c.get_type()=='terminal'; import os; os.remove(c._fp); print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add core/conversation.py
git commit -m "feat(terminal): Conversation supports type/tmux_session/workdir"
```

---

## Task 3: REST endpoints — /terminal CRUD + capabilities + sessions list

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Import tmux_manager near the other `from core.*` imports**

```python
from core import tmux_manager
```

- [ ] **Step 2: Add capability + CRUD endpoints**

Add this block after the existing `/conversation/{cid}/role` routes (around line 1115, just before `@app.delete("/conversation/{cid}")`):

```python
# ── Terminal tabs ─────────────────────────────────────────────────────

def _terminal_tab_to_dict(cid: str, data: dict) -> dict:
    return {
        "id": cid,
        "cid": cid,
        "type": data.get("type") or "chat",
        "title": data.get("title") or "terminal",
        "workspace_id": data.get("workspace_id")
                        or data.get("agency_id")
                        or "default",
        "project_id": data.get("project_id") or None,
        "tmux_session": data.get("tmux_session") or None,
        "workdir": data.get("workdir") or None,
        "created_at": data.get("created_at"),
    }


@app.get("/terminal/capabilities")
async def terminal_capabilities():
    ok = tmux_manager.tmux_available()
    return {
        "available": ok,
        "reason": None if ok else "tmux binary not found on host PATH",
    }


@app.post("/terminal")
async def create_terminal(body: dict):
    if not tmux_manager.tmux_available():
        raise HTTPException(status_code=501, detail="tmux not installed")

    workspace_id = (body.get("workspace_id") or body.get("agency_id")
                    or "default")
    project_id = body.get("project_id") or "main-default"
    title = (body.get("title") or "").strip() or "terminal"
    workdir = (body.get("workdir") or "").strip() or None
    tmux_session = (body.get("tmux_session") or "").strip() or None

    created_new = False
    if not tmux_session:
        tmux_session = tmux_manager.make_session_name(workspace_id, project_id)
        created_new = True

    try:
        tmux_manager.new_session(tmux_session, workdir)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    cid = uuid.uuid4().hex
    now = int(time.time())
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    conv_file.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "agent_id": None,
        "title": title,
        "type": "terminal",
        "workspace_id": workspace_id,
        "project_id": project_id,
        "tmux_session": tmux_session,
        "workdir": workdir,
        "created_at": now,
        "messages": [],
        "llm_settings": {},
        "session_role": None,
        "selection_type": None,
    }
    with open(conv_file, "w") as fp:
        json.dump(data, fp, indent=2)

    out = _terminal_tab_to_dict(cid, data)
    out["created_new"] = created_new
    return out


@app.get("/terminal")
async def list_terminals(project_id: Optional[str] = None,
                         agency_id: Optional[str] = None):
    conv_dir = Path(__file__).parent / "conversations"
    out = []
    for p in conv_dir.glob("*.json"):
        try:
            with open(p) as fp:
                data = json.load(fp)
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        if (data.get("type") or "chat") != "terminal":
            continue
        if project_id and data.get("project_id") != project_id:
            continue
        if agency_id and (data.get("workspace_id")
                          or data.get("agency_id")) != agency_id:
            continue
        out.append(_terminal_tab_to_dict(p.stem, data))
    out.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
    return out


@app.get("/terminal/{cid}")
async def get_terminal(cid: str):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="not found")
    with open(conv_file) as fp:
        data = json.load(fp)
    if (data.get("type") or "chat") != "terminal":
        raise HTTPException(status_code=404, detail="not a terminal tab")
    return _terminal_tab_to_dict(cid, data)


@app.patch("/terminal/{cid}")
async def patch_terminal(cid: str, body: dict):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="not found")
    with open(conv_file) as fp:
        data = json.load(fp)
    if (data.get("type") or "chat") != "terminal":
        raise HTTPException(status_code=404, detail="not a terminal tab")
    if "title" in body:
        t = (body.get("title") or "").strip()
        if t:
            data["title"] = t
    if "tmux_session" in body:
        name = (body.get("tmux_session") or "").strip() or None
        if name:
            if not tmux_manager.session_exists(name):
                workdir = data.get("workdir")
                tmux_manager.new_session(name, workdir)
            data["tmux_session"] = name
    with open(conv_file, "w") as fp:
        json.dump(data, fp, indent=2)
    return _terminal_tab_to_dict(cid, data)


@app.delete("/terminal/{cid}")
async def delete_terminal(cid: str, kill_session: int = 0):
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        raise HTTPException(status_code=404, detail="not found")
    with open(conv_file) as fp:
        data = json.load(fp)
    name = data.get("tmux_session")
    conv_file.unlink()
    killed = False
    if kill_session and name:
        killed = tmux_manager.kill_session(name)
    return {"ok": True, "killed": killed, "tmux_session": name}


@app.get("/terminal/sessions")
async def terminal_sessions(project_id: Optional[str] = None,
                            agency_id: Optional[str] = None):
    ws = agency_id or "default"
    proj = project_id or "main-default"
    prefix = f"neuro-{tmux_manager._slug(ws)}-{tmux_manager._slug(proj)}-"
    return tmux_manager.list_sessions(prefix=prefix)
```

Note: `time` and `uuid` are already imported at top of `server.py`. If not, add them.

- [ ] **Step 3: Smoke-test via curl**

Start server (or if running, it'll pick up changes through uvicorn reload). Then:

```bash
curl -s http://localhost:7001/terminal/capabilities
# → {"available":true,"reason":null}

CID=$(curl -s -X POST http://localhost:7001/terminal \
  -H 'Content-Type: application/json' \
  -d '{"title":"t1","workspace_id":"default","project_id":"main-default"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['cid'])")
echo "cid=$CID"

curl -s http://localhost:7001/terminal/$CID | python3 -m json.tool
curl -s "http://localhost:7001/terminal?project_id=main-default&agency_id=default" \
  | python3 -c "import sys,json; r=json.load(sys.stdin); print(len(r),'tabs')"
curl -s "http://localhost:7001/terminal/sessions?project_id=main-default&agency_id=default" \
  | python3 -m json.tool

curl -s -X DELETE "http://localhost:7001/terminal/$CID?kill_session=1" \
  | python3 -m json.tool
```

Expected: capabilities `true`; POST returns tab JSON with `tmux_session` like `neuro-default-main-default-xxxxxxxx`; GET one/list both return it; sessions list includes it; DELETE with kill=1 returns `killed:true`.

- [ ] **Step 4: Commit**

```bash
git add server.py
git commit -m "feat(terminal): /terminal REST endpoints + capabilities probe"
```

---

## Task 4: WebSocket pty bridge

**Files:**
- Create: `core/terminal_ws.py`
- Modify: `server.py`

- [ ] **Step 1: Implement `core/terminal_ws.py`**

```python
"""WebSocket ↔ pty bridge for tmux terminal tabs.

One PtyBridge per live WebSocket connection.
- Reads pty stdout and forwards as binary ws frames.
- Receives binary ws frames and writes them to pty stdin.
- Receives text JSON control frames: {"type":"resize"|"ping"}.
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

from core import tmux_manager

logger = logging.getLogger(__name__)

READ_CHUNK = 4096


class PtyBridge:
    def __init__(self, ws: WebSocket, tmux_session: str):
        self.ws = ws
        self.session = tmux_session
        self.pty: Optional[ptyprocess.PtyProcess] = None
        self._closed = False

    async def run(self):
        await self._spawn_pty()
        await self.ws.send_text(json.dumps({"type": "ready"}))

        reader_task = asyncio.create_task(self._pump_pty_to_ws())
        writer_task = asyncio.create_task(self._pump_ws_to_pty())
        try:
            done, pending = await asyncio.wait(
                {reader_task, writer_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for t in pending:
                t.cancel()
        finally:
            await self._cleanup()

    async def _spawn_pty(self):
        env = os.environ.copy()
        env["TERM"] = "xterm-256color"
        # spawn in a worker thread — ptyprocess.spawn forks
        self.pty = await asyncio.to_thread(
            ptyprocess.PtyProcess.spawn,
            ["tmux", "attach", "-t", self.session],
            env=env,
            dimensions=(30, 120),
        )

    async def _pump_pty_to_ws(self):
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        def _on_readable():
            try:
                data = os.read(self.pty.fd, READ_CHUNK)
            except OSError:
                data = b""
            if not data:
                loop.call_soon_threadsafe(queue.put_nowait, None)
                try:
                    loop.remove_reader(self.pty.fd)
                except Exception:
                    pass
                return
            loop.call_soon_threadsafe(queue.put_nowait, data)

        loop.add_reader(self.pty.fd, _on_readable)
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
                loop.remove_reader(self.pty.fd)
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

    async def _pump_ws_to_pty(self):
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
            if "bytes" in msg and msg["bytes"] is not None:
                try:
                    os.write(self.pty.fd, msg["bytes"])
                except OSError:
                    break
                continue
            if "text" in msg and msg["text"] is not None:
                try:
                    payload = json.loads(msg["text"])
                except json.JSONDecodeError:
                    continue
                t = payload.get("type")
                if t == "resize":
                    cols = int(payload.get("cols") or 80)
                    rows = int(payload.get("rows") or 24)
                    try:
                        self.pty.setwinsize(rows, cols)
                    except Exception:
                        pass
                elif t == "ping":
                    try:
                        await self.ws.send_text(json.dumps({"type": "pong"}))
                    except Exception:
                        break

    async def _cleanup(self):
        if self._closed:
            return
        self._closed = True
        if self.pty and self.pty.isalive():
            try:
                self.pty.kill(signal.SIGHUP)
            except Exception:
                pass
        try:
            if self.pty:
                self.pty.close(force=True)
        except Exception:
            pass
```

- [ ] **Step 2: Add WS route to `server.py`**

Add near the other route definitions, after the REST `/terminal/sessions` endpoint:

```python
from fastapi import WebSocket, WebSocketDisconnect
from core.terminal_ws import PtyBridge


@app.websocket("/terminal/ws/{cid}")
async def terminal_ws(websocket: WebSocket, cid: str):
    await websocket.accept()
    conv_file = Path(__file__).parent / "conversations" / f"{cid}.json"
    if not conv_file.exists():
        await websocket.send_text(json.dumps({
            "type": "error", "msg": "conversation not found"
        }))
        await websocket.close()
        return
    with open(conv_file) as fp:
        data = json.load(fp)
    if (data.get("type") or "chat") != "terminal":
        await websocket.send_text(json.dumps({
            "type": "error", "msg": "not a terminal tab"
        }))
        await websocket.close()
        return
    name = data.get("tmux_session")
    workdir = data.get("workdir")
    if not name:
        await websocket.send_text(json.dumps({
            "type": "error", "msg": "tab has no tmux_session"
        }))
        await websocket.close()
        return
    # Auto-recreate if the session died (e.g. host reboot)
    if not tmux_manager.session_exists(name):
        try:
            tmux_manager.new_session(name, workdir)
        except RuntimeError as e:
            await websocket.send_text(json.dumps({
                "type": "error", "msg": f"tmux start failed: {e}"
            }))
            await websocket.close()
            return
    bridge = PtyBridge(websocket, name)
    try:
        await bridge.run()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("[terminal_ws] bridge error for %s", cid)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
```

Note: `WebSocket`/`WebSocketDisconnect` may already be imported elsewhere; import only if not. `logger` already exists near top of `server.py`.

- [ ] **Step 3: Smoke test the WS using a Python client**

Run:
```bash
python3 - <<'PY'
import asyncio, json, websockets, requests, time

r = requests.post("http://localhost:7001/terminal", json={
    "title":"wsprobe","workspace_id":"default","project_id":"main-default"}).json()
cid = r["cid"]
print("cid", cid, "session", r["tmux_session"])

async def main():
    async with websockets.connect(f"ws://localhost:7001/terminal/ws/{cid}") as ws:
        # read first few frames
        end = time.time() + 3
        got_ready = False
        got_bytes = False
        await ws.send(b"echo NEURO_PROBE\n")
        while time.time() < end:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=0.5)
            except asyncio.TimeoutError:
                break
            if isinstance(msg, (bytes, bytearray)):
                got_bytes = True
                if b"NEURO_PROBE" in bytes(msg):
                    print("✓ echo seen in stream")
                    break
            else:
                if '"ready"' in msg:
                    got_ready = True
        assert got_ready, "never got ready frame"
        assert got_bytes, "no binary output"

asyncio.run(main())
requests.delete(f"http://localhost:7001/terminal/{cid}?kill_session=1")
print("ok")
PY
```

Expected: prints `✓ echo seen in stream` then `ok`.

- [ ] **Step 4: Commit**

```bash
git add core/terminal_ws.py server.py
git commit -m "feat(terminal): WebSocket pty bridge + /terminal/ws endpoint"
```

---

## Task 5: Frontend deps — xterm.js + addons

**Files:**
- Modify: `neuro_web/package.json`

- [ ] **Step 1: Install packages**

Run in `neuro_web/`:
```bash
pnpm add xterm xterm-addon-fit xterm-addon-webgl xterm-addon-web-links
```

- [ ] **Step 2: Verify**

Run: `grep -E 'xterm' /home/ubuntu/neurocomputer-dev/neuro_web/package.json`
Expected: 4 lines (`xterm`, `xterm-addon-fit`, `xterm-addon-webgl`, `xterm-addon-web-links`).

- [ ] **Step 3: Commit**

```bash
git add neuro_web/package.json neuro_web/package-lock.json
git commit -m "feat(terminal): add xterm.js + addons"
```

---

## Task 6: Frontend — types, Tab discriminator, API service

**Files:**
- Modify: `neuro_web/types/index.ts`
- Modify: `neuro_web/services/api.ts`

- [ ] **Step 1: Extend `Tab` type with `type` + terminal fields**

In `neuro_web/types/index.ts`, change:

```ts
export interface Tab {
  cid: string;
  title: string;
  agentId: string;
  isActive: boolean;
  workdir?: string | null;
}
```

to:

```ts
export type TabKind = 'chat' | 'terminal';

export interface Tab {
  cid: string;
  title: string;
  agentId: string;
  isActive: boolean;
  workdir?: string | null;
  type?: TabKind;              // default "chat"
  tmuxSession?: string | null; // populated when type === "terminal"
}

export interface TerminalTab {
  id: string;
  cid: string;
  type: 'terminal';
  title: string;
  workspace_id: string;
  project_id: string | null;
  tmux_session: string;
  workdir: string | null;
  created_at: number | null;
}

export interface TmuxSessionInfo {
  name: string;
  created_at: number;
  attached_clients: number;
  windows: number;
}
```

- [ ] **Step 2: Add API helpers**

In `neuro_web/services/api.ts`, append:

```ts
import type { TerminalTab, TmuxSessionInfo } from '@/types';

export async function apiTerminalCapabilities(): Promise<{ available: boolean; reason: string | null }> {
  const r = await axios.get(`${API_BASE}/terminal/capabilities`);
  return r.data;
}

export async function apiTerminalCreate(body: {
  title?: string; workspace_id: string; project_id: string | null;
  workdir?: string | null; tmux_session?: string | null;
}): Promise<TerminalTab> {
  const r = await axios.post(`${API_BASE}/terminal`, body);
  return r.data;
}

export async function apiTerminalGet(cid: string): Promise<TerminalTab> {
  const r = await axios.get(`${API_BASE}/terminal/${cid}`);
  return r.data;
}

export async function apiTerminalList(params: { project_id?: string | null; agency_id?: string | null }): Promise<TerminalTab[]> {
  const r = await axios.get(`${API_BASE}/terminal`, { params });
  return r.data;
}

export async function apiTerminalPatch(cid: string, body: { title?: string; tmux_session?: string }): Promise<TerminalTab> {
  const r = await axios.patch(`${API_BASE}/terminal/${cid}`, body);
  return r.data;
}

export async function apiTerminalDelete(cid: string, killSession = false): Promise<{ ok: boolean; killed: boolean; tmux_session: string | null }> {
  const r = await axios.delete(`${API_BASE}/terminal/${cid}`, { params: { kill_session: killSession ? 1 : 0 } });
  return r.data;
}

export async function apiTerminalSessions(params: { project_id?: string | null; agency_id?: string | null }): Promise<TmuxSessionInfo[]> {
  const r = await axios.get(`${API_BASE}/terminal/sessions`, { params });
  return r.data;
}
```

(If `axios` / `API_BASE` imports differ, match the existing convention in that file.)

- [ ] **Step 3: Type-check**

Run: `cd neuro_web && npx tsc --noEmit 2>&1 | head -20`
Expected: no errors from the new code (pre-existing errors may exist; our changes should not introduce new ones).

- [ ] **Step 4: Commit**

```bash
git add neuro_web/types/index.ts neuro_web/services/api.ts
git commit -m "feat(terminal): types + API service helpers"
```

---

## Task 7: Redux — terminalSlice + conversationSlice `type` propagation

**Files:**
- Create: `neuro_web/store/terminalSlice.ts`
- Modify: `neuro_web/store/conversationSlice.ts`
- Modify: `neuro_web/store/index.ts`

- [ ] **Step 1: Create the terminal slice**

```ts
// neuro_web/store/terminalSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { apiTerminalCreate, apiTerminalDelete, apiTerminalSessions, apiTerminalCapabilities } from '@/services/api';
import type { TmuxSessionInfo, TerminalTab } from '@/types';

export type WsStatus = 'idle' | 'connecting' | 'ready' | 'reconnecting' | 'error';

interface TerminalState {
  available: boolean | null;
  sessionsByProject: Record<string, TmuxSessionInfo[]>;
  wsStatus: Record<string, WsStatus>;
}

const initialState: TerminalState = {
  available: null,
  sessionsByProject: {},
  wsStatus: {},
};

export const fetchCapabilities = createAsyncThunk(
  'terminal/capabilities',
  async () => (await apiTerminalCapabilities()).available,
);

export const createTerminal = createAsyncThunk(
  'terminal/create',
  async (args: { title?: string; workspace_id: string; project_id: string | null; workdir?: string | null }) =>
    apiTerminalCreate(args),
);

export const deleteTerminal = createAsyncThunk(
  'terminal/delete',
  async (args: { cid: string; killSession: boolean }) =>
    apiTerminalDelete(args.cid, args.killSession),
);

export const fetchTerminalSessions = createAsyncThunk(
  'terminal/sessions',
  async (args: { project_id?: string | null; agency_id?: string | null }) => {
    const rows = await apiTerminalSessions(args);
    return { key: `${args.agency_id || 'default'}:${args.project_id || 'main-default'}`, rows };
  },
);

const slice = createSlice({
  name: 'terminal',
  initialState,
  reducers: {
    setWsStatus(state, a: PayloadAction<{ cid: string; status: WsStatus }>) {
      state.wsStatus[a.payload.cid] = a.payload.status;
    },
  },
  extraReducers: b => {
    b.addCase(fetchCapabilities.fulfilled, (s, a) => { s.available = a.payload; });
    b.addCase(fetchTerminalSessions.fulfilled, (s, a) => {
      s.sessionsByProject[a.payload.key] = a.payload.rows;
    });
  },
});

export const { setWsStatus } = slice.actions;
export default slice.reducer;
```

- [ ] **Step 2: Register slice in the store**

In `neuro_web/store/index.ts`, add next to the other reducers:

```ts
import terminalReducer from './terminalSlice';
...
reducer: {
  ...existing,
  terminal: terminalReducer,
}
```

- [ ] **Step 3: Extend Tab semantics in conversationSlice**

In `conversationSlice.ts`, wherever `openTab` is typed/handled, ensure the payload allows `type?: 'chat' | 'terminal'` and `tmuxSession?: string | null`, and the reducer copies those through. No behavioral change for existing chat tabs.

Search for `openTab` reducer definition and update its PayloadAction type to accept the new optional fields, then spread them into the pushed tab object.

- [ ] **Step 4: Type-check**

Run: `cd neuro_web && npx tsc --noEmit 2>&1 | grep -E "(error TS|terminal)" | head`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add neuro_web/store/terminalSlice.ts neuro_web/store/index.ts neuro_web/store/conversationSlice.ts
git commit -m "feat(terminal): terminalSlice + Tab.type propagation"
```

---

## Task 8: Frontend — `useTerminalWs` hook

**Files:**
- Create: `neuro_web/hooks/useTerminalWs.ts`

- [ ] **Step 1: Implement**

```ts
// neuro_web/hooks/useTerminalWs.ts
import { useEffect, useRef, useCallback } from 'react';
import { useAppDispatch } from '@/store/hooks';
import { setWsStatus } from '@/store/terminalSlice';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:7001';

export interface TerminalWsHandle {
  send: (data: ArrayBuffer | Uint8Array | string) => void;
  resize: (cols: number, rows: number) => void;
  close: () => void;
}

export function useTerminalWs(
  cid: string | null,
  onBinary: (b: ArrayBuffer) => void,
  onExit?: (code: number) => void,
): TerminalWsHandle {
  const dispatch = useAppDispatch();
  const wsRef = useRef<WebSocket | null>(null);
  const backoffRef = useRef(1000);
  const shouldReconnectRef = useRef(true);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!cid) return;
    const url = `${API_BASE.replace(/^http/, 'ws')}/terminal/ws/${cid}`;
    const ws = new WebSocket(url);
    ws.binaryType = 'arraybuffer';
    wsRef.current = ws;
    dispatch(setWsStatus({ cid, status: 'connecting' }));

    ws.onopen = () => {
      backoffRef.current = 1000;
      dispatch(setWsStatus({ cid, status: 'connecting' }));  // wait for "ready" text
    };
    ws.onmessage = (ev) => {
      if (typeof ev.data === 'string') {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === 'ready') {
            dispatch(setWsStatus({ cid, status: 'ready' }));
          } else if (msg.type === 'exit') {
            onExit?.(msg.code ?? 0);
          } else if (msg.type === 'error') {
            console.warn('[terminal] server error:', msg.msg);
            dispatch(setWsStatus({ cid, status: 'error' }));
          }
        } catch {
          /* ignore */
        }
        return;
      }
      if (ev.data instanceof ArrayBuffer) {
        onBinary(ev.data);
      } else if (ev.data instanceof Blob) {
        ev.data.arrayBuffer().then(onBinary);
      }
    };
    ws.onclose = () => {
      wsRef.current = null;
      if (!shouldReconnectRef.current) return;
      dispatch(setWsStatus({ cid, status: 'reconnecting' }));
      reconnectTimerRef.current = setTimeout(() => {
        backoffRef.current = Math.min(backoffRef.current * 2, 10000);
        connect();
      }, backoffRef.current);
    };
    ws.onerror = () => {
      try { ws.close(); } catch { /* no-op */ }
    };
  }, [cid, dispatch, onBinary, onExit]);

  useEffect(() => {
    shouldReconnectRef.current = true;
    connect();
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      try { wsRef.current?.close(); } catch { /* no-op */ }
      wsRef.current = null;
    };
  }, [connect]);

  const send = useCallback((data: ArrayBuffer | Uint8Array | string) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (typeof data === 'string') {
      ws.send(new TextEncoder().encode(data));
    } else {
      ws.send(data);
    }
  }, []);

  const resize = useCallback((cols: number, rows: number) => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: 'resize', cols, rows }));
  }, []);

  const close = useCallback(() => {
    shouldReconnectRef.current = false;
    try { wsRef.current?.close(); } catch { /* no-op */ }
  }, []);

  return { send, resize, close };
}
```

- [ ] **Step 2: Type-check**

Run: `cd neuro_web && npx tsc --noEmit 2>&1 | grep "hooks/useTerminalWs" | head`
Expected: empty.

- [ ] **Step 3: Commit**

```bash
git add neuro_web/hooks/useTerminalWs.ts
git commit -m "feat(terminal): useTerminalWs hook"
```

---

## Task 9: Frontend — TerminalPanel + subcomponents

**Files:**
- Create: `neuro_web/components/terminal/TerminalPanel.tsx`
- Create: `neuro_web/components/terminal/MobileKeyBar.tsx`

- [ ] **Step 1: Implement `TerminalPanel.tsx`**

```tsx
'use client';
import { useEffect, useRef, useState } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { WebglAddon } from 'xterm-addon-webgl';
import { WebLinksAddon } from 'xterm-addon-web-links';
import 'xterm/css/xterm.css';
import { useAppSelector } from '@/store/hooks';
import { useTerminalWs } from '@/hooks/useTerminalWs';
import MobileKeyBar from './MobileKeyBar';

export default function TerminalPanel() {
  const activeCid = useAppSelector(s => s.conversations.activeTabCid);
  const tab = useAppSelector(s =>
    s.conversations.tabs.find(t => t.cid === activeCid) || null);
  const wsStatus = useAppSelector(s =>
    activeCid ? s.terminal.wsStatus[activeCid] : 'idle');

  const containerRef = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const [mobile, setMobile] = useState(false);

  const sendRef = useRef<((d: ArrayBuffer | string) => void) | null>(null);
  const resizeRef = useRef<((c: number, r: number) => void) | null>(null);

  // 1. Mount xterm once per cid change
  useEffect(() => {
    if (!containerRef.current || !activeCid) return;
    const term = new Terminal({
      cursorBlink: true,
      fontFamily: "'Berkeley Mono', ui-monospace, monospace",
      fontSize: 13,
      theme: { background: '#0a0a0b', foreground: '#d0d6e0' },
      scrollback: 10000,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.loadAddon(new WebLinksAddon());
    try { term.loadAddon(new WebglAddon()); } catch { /* fallback */ }
    term.open(containerRef.current);
    fit.fit();
    termRef.current = term;
    fitRef.current = fit;

    term.onData(d => {
      sendRef.current?.(new TextEncoder().encode(d).buffer);
    });

    const onResize = () => {
      try {
        fit.fit();
        resizeRef.current?.(term.cols, term.rows);
      } catch { /* no-op */ }
    };
    const ro = new ResizeObserver(onResize);
    ro.observe(containerRef.current);
    window.addEventListener('resize', onResize);

    return () => {
      ro.disconnect();
      window.removeEventListener('resize', onResize);
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, [activeCid]);

  // 2. Viewport breakpoint
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 640px)');
    const on = () => setMobile(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);

  // 3. WS wiring
  const { send, resize } = useTerminalWs(
    activeCid,
    (buf) => termRef.current?.write(new Uint8Array(buf)),
    (code) => termRef.current?.writeln(`\r\n\x1b[33m[session ended, code=${code}]\x1b[0m\r\n`),
  );

  // bind stable refs so the effect above doesn't need to depend on these
  sendRef.current = send;
  resizeRef.current = resize;

  // 4. Initial resize push after connect
  useEffect(() => {
    if (wsStatus === 'ready' && termRef.current) {
      resize(termRef.current.cols, termRef.current.rows);
    }
  }, [wsStatus, resize]);

  const sendKey = (seq: string) => {
    send(new TextEncoder().encode(seq).buffer);
  };

  if (!tab || tab.type !== 'terminal') return null;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', flex: 1,
      background: '#0a0a0b', overflow: 'hidden',
    }}>
      <div style={{
        padding: '6px 12px',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
        color: '#62666d', fontSize: '11px',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ fontFamily: 'monospace' }}>
          {tab.tmuxSession || '—'}
        </span>
        <span>{statusLabel(wsStatus)}</span>
      </div>
      <div ref={containerRef} style={{ flex: 1, minHeight: 0 }} />
      {mobile && <MobileKeyBar onKey={sendKey} />}
    </div>
  );
}

function statusLabel(s: string | undefined) {
  switch (s) {
    case 'ready': return 'connected';
    case 'connecting': return 'connecting…';
    case 'reconnecting': return 'reconnecting…';
    case 'error': return 'error';
    default: return '';
  }
}
```

- [ ] **Step 2: Implement `MobileKeyBar.tsx`**

```tsx
'use client';
import { useState } from 'react';

interface Props { onKey: (seq: string) => void }

const KEYS: { label: string; seq: string }[] = [
  { label: 'Esc',  seq: '\x1b' },
  { label: 'Tab',  seq: '\t' },
  { label: '↑',    seq: '\x1b[A' },
  { label: '↓',    seq: '\x1b[B' },
  { label: '←',    seq: '\x1b[D' },
  { label: '→',    seq: '\x1b[C' },
];

export default function MobileKeyBar({ onKey }: Props) {
  const [ctrl, setCtrl] = useState(false);
  const press = (seq: string) => {
    if (ctrl && seq.length === 1 && /[a-zA-Z]/.test(seq)) {
      onKey(String.fromCharCode(seq.charCodeAt(0) & 0x1f));
      setCtrl(false);
      return;
    }
    onKey(seq);
    if (ctrl) setCtrl(false);
  };
  return (
    <div style={{
      display: 'flex', gap: 4, padding: 4,
      borderTop: '1px solid rgba(255,255,255,0.05)',
      overflowX: 'auto', background: '#0f1011',
    }}>
      <button onClick={() => setCtrl(c => !c)} style={btn(ctrl)}>Ctrl</button>
      {KEYS.map(k => (
        <button key={k.label} onClick={() => press(k.seq)} style={btn(false)}>
          {k.label}
        </button>
      ))}
    </div>
  );
}

function btn(active: boolean): React.CSSProperties {
  return {
    padding: '6px 10px', borderRadius: 4,
    background: active ? 'rgba(94,106,210,0.25)' : 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    color: active ? '#c4b5fd' : '#d0d6e0',
    fontSize: 12, minWidth: 38, flexShrink: 0,
  };
}
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/terminal
git commit -m "feat(terminal): TerminalPanel + MobileKeyBar"
```

---

## Task 10: Tab bar split-menu + page router wires TerminalPanel

**Files:**
- Modify: `neuro_web/components/layout/TabBar.tsx`
- Modify: `neuro_web/app/page.tsx`

- [ ] **Step 1: Tab "+" split menu**

In `TabBar.tsx`, locate the current "+" button's onClick (which calls `onNewTab`). Replace it with a small menu:

```tsx
// Add state at top of TabBar component:
const [showMenu, setShowMenu] = useState(false);

// Replace the existing onClick with a menu trigger:
<div style={{ position: 'relative' }}>
  <button onClick={() => setShowMenu(v => !v)} /* existing styles */>
    +
  </button>
  {showMenu && (
    <div style={{
      position: 'absolute', top: '100%', right: 0, marginTop: 4,
      background: '#0f1011', border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 6, minWidth: 160, zIndex: 50,
      boxShadow: '0 8px 30px rgba(0,0,0,0.5)', overflow: 'hidden',
    }}>
      <button
        onClick={() => { setShowMenu(false); onNewTab(); }}
        style={menuItem}>New Chat</button>
      <button
        onClick={() => { setShowMenu(false); onNewTerminal(); }}
        style={menuItem}>New Terminal</button>
    </div>
  )}
</div>
```

Define `menuItem`:
```tsx
const menuItem: React.CSSProperties = {
  display: 'block', width: '100%', padding: '8px 12px', textAlign: 'left',
  background: 'transparent', border: 'none', color: '#d0d6e0',
  fontSize: 13, cursor: 'pointer',
};
```

Add `onNewTerminal: () => void` to TabBar props; accept it from the parent.

- [ ] **Step 2: Wire `onNewTerminal` in `app/page.tsx`**

Inside `Home()`, alongside `handleNewTab`:

```tsx
const handleNewTerminal = useCallback(async () => {
  const result = await dispatch(createTerminal({
    workspace_id: selectedWorkspaceId || 'default',
    project_id: selectedProjectId,
  }));
  if (createTerminal.fulfilled.match(result)) {
    const t = result.payload;
    dispatch(openTab({
      cid: t.cid,
      title: t.title || 'terminal',
      agentId: 'terminal',
      isActive: true,
      type: 'terminal',
      tmuxSession: t.tmux_session,
    }));
  }
}, [dispatch, selectedWorkspaceId, selectedProjectId]);
```

Import `createTerminal` from `@/store/terminalSlice`. Pass `onNewTerminal={handleNewTerminal}` to every `<TabBar>` usage (there are two — tab bar top and bottom).

- [ ] **Step 3: Render TerminalPanel when active tab is terminal**

In `app/page.tsx`, find the `<ChatPanel />` line and swap for:

```tsx
{activeTabKind === 'terminal'
  ? <TerminalPanel />
  : (<><ChatPanel /><ChatInput /></>)}
```

Compute `activeTabKind` via selector:
```tsx
const activeTabKind = useAppSelector(s => {
  const t = s.conversations.tabs.find(x => x.cid === s.conversations.activeTabCid);
  return t?.type === 'terminal' ? 'terminal' : 'chat';
});
```

Import `TerminalPanel` dynamically (SSR-safe since xterm uses `window`):
```tsx
const TerminalPanel = dynamic(() => import('@/components/terminal/TerminalPanel'), { ssr: false });
```

- [ ] **Step 4: Manual smoke**

- Run `pnpm dev`, open http://localhost:3000
- Click "+" → "New Terminal" → a new tab appears
- The tab shows a live shell prompt within ~2 s
- Type `ls` → see output
- Close the tab; verify `curl http://localhost:7001/terminal/sessions?project_id=main-default&agency_id=default` still shows the session (we didn't kill it)

- [ ] **Step 5: Commit**

```bash
git add neuro_web/components/layout/TabBar.tsx neuro_web/app/page.tsx
git commit -m "feat(terminal): TabBar split menu + page.tsx routes to TerminalPanel"
```

---

## Task 11: Capability gating + graceful fallback

**Files:**
- Modify: `neuro_web/app/page.tsx` (or a top-level component)
- Modify: `neuro_web/components/layout/TabBar.tsx`

- [ ] **Step 1: Probe capabilities on app boot**

Near the existing `useEffect` that fetches workspaces in `app/page.tsx`, add:

```tsx
useEffect(() => {
  dispatch(fetchCapabilities());
}, [dispatch]);
```

Import `fetchCapabilities` from `@/store/terminalSlice`.

- [ ] **Step 2: Hide "New Terminal" entry when unavailable**

In `TabBar.tsx`, read the flag:
```tsx
const termAvailable = useAppSelector(s => s.terminal.available);
```
Render the `New Terminal` menu item only when `termAvailable !== false` (keep it enabled while `null` = still-probing, since probe is cheap and usually resolves instantly).

- [ ] **Step 3: Commit**

```bash
git add neuro_web/app/page.tsx neuro_web/components/layout/TabBar.tsx
git commit -m "feat(terminal): capability gating in UI"
```

---

## Task 12: End-to-end smoke checklist (manual)

Run through and confirm each line. Not automated in v1.

- [ ] Backend: `curl http://localhost:7001/terminal/capabilities` returns `available:true`.
- [ ] UI: click "+" → "New Terminal" → xterm shows a shell prompt within 3 s.
- [ ] Type `echo hello-terminal` → see output.
- [ ] Resize the browser window → prompt redraws at new dimensions. `stty size` in terminal matches visible rows/cols.
- [ ] Run `vim /tmp/foo`; type some text; resize; quit without saving. No garbage output.
- [ ] Close the tab. Verify tmux session remains: `tmux list-sessions | grep neuro-default-main-default`.
- [ ] Stop and restart the FastAPI backend. Open a NEW terminal tab bound to the still-running session (via the session switcher later, or just create a new tab — session recreate is auto on WS connect).
- [ ] In Chrome devtools → device emulation → iPhone SE. Confirm mobile key bar appears; tap `Ctrl` then `C` to cancel a `sleep 5` running in the shell.
- [ ] With two browser windows both showing the same terminal tab, typing in one is visible in the other (multi-attach via tmux).
- [ ] `curl -X DELETE 'http://localhost:7001/terminal/<cid>?kill_session=1'` → session disappears from `tmux list-sessions`.

---

## Critical files

| Action | Path |
|---|---|
| Create | `core/tmux_manager.py` |
| Create | `core/terminal_ws.py` |
| Create | `tests/test_tmux_manager.py` |
| Create | `neuro_web/hooks/useTerminalWs.ts` |
| Create | `neuro_web/store/terminalSlice.ts` |
| Create | `neuro_web/components/terminal/TerminalPanel.tsx` |
| Create | `neuro_web/components/terminal/MobileKeyBar.tsx` |
| Modify | `core/conversation.py` |
| Modify | `server.py` |
| Modify | `neuro_web/package.json` |
| Modify | `neuro_web/types/index.ts` |
| Modify | `neuro_web/services/api.ts` |
| Modify | `neuro_web/store/index.ts` |
| Modify | `neuro_web/store/conversationSlice.ts` |
| Modify | `neuro_web/components/layout/TabBar.tsx` |
| Modify | `neuro_web/app/page.tsx` |

No DB migration — new fields live inside `conversations/<id>.json` and are additive.

## Out of scope

- Agent-driven / shared-session mode (v2).
- Playwright E2E — manual smoke only for v1.
- Per-user identity binding — explicit v1 assumption: single-user.
- Command audit log.
- **Session-switcher dropdown UI** (v1.1). The *backend* for hybrid org is
  fully implemented (POST with `tmux_session` binds to an existing session;
  PATCH `tmux_session` rebinds a tab; GET `/terminal/sessions` lists them).
  The *UI switcher* inside `TerminalPanel` header is a small follow-up and
  is not needed to exercise the rest of the feature.
- Tab-pill icon differentiation (`>_` glyph). The tab uses its existing
  rendering; distinguishable by title and by rendering swap in the main panel.
