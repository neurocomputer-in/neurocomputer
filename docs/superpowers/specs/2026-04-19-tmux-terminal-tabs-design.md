# Tmux Terminal Tabs — Design Spec

**Status:** Approved design. Awaiting implementation plan.
**Date:** 2026-04-19
**Owner:** Gopal

## Goal

Extend the existing tab system so users can open **terminal tabs** alongside chat tabs. Each terminal tab binds to a persistent `tmux` session on the backend host, rendering live pty I/O in the browser (desktop, mobile, Electron) via `xterm.js`. Sessions survive disconnects, device switches, and FastAPI restarts — just like running `tmux` locally.

**First cut (this spec): human-driven terminal only.** Agent-driven / shared sessions ("AI and human both type") are an explicit follow-up.

## Background and constraints

- Neuro already models `conversations/<id>.json` with `agent_id`, `project_id`, `workspace_id`. Tabs are backed by these files.
- Workspaces → Projects hierarchy exists; the "Main Project" concept is already in place per workspace.
- Frontend uses React + Redux; tabs live in Redux `conversations` slice; UI decides render mode from tab metadata.
- Backend is single-user, runs as `ubuntu`. The shell session will inherit that user's privileges — explicit v1 assumption.
- `tmux` is assumed available on the host. If absent, the feature is disabled (gated at runtime).

## Decisions (locked during brainstorming)

1. **Terminal engine:** Real `tmux` on the server host, rendered in browser via `xterm.js` over a WebSocket.
2. **Mode:** Human-driven only for v1. Agent integration (shared session) deferred.
3. **Session organization:** Hybrid — each terminal tab defaults to its own tmux session (1:1), but any tab can switch/attach to any existing session via a switcher in the tab header. Multiple tabs attaching the same session is allowed (tmux multi-client).
4. **Scope:** Per-project. Sessions belong to `(workspace_id, project_id)` like conversations do. New terminals default to Main Project of the selected workspace.
5. **Transport split:** Metadata (CRUD) over REST reusing the existing conversation store. Live I/O over a dedicated raw-binary WebSocket endpoint (`/terminal/ws/{cid}`). No LiveKit on the hot path.

## Architecture

```
┌─────────────────────┐   WebSocket binary   ┌──────────────────────┐
│  xterm.js (tab)     │ ◄──────────────────► │ FastAPI /terminal/ws │
│  terminal frontend  │                      │       │              │
└─────────────────────┘                      │       ▼              │
         │                                   │  pty master/slave    │
         │ HTTP (CRUD)                       │       │              │
         │  list / create / rename / delete  │       ▼              │
         ▼                                   │  `tmux attach -t foo`│
┌─────────────────────┐                      └──────────────────────┘
│  /terminal REST     │                          ▲ ▲
│  metadata endpoints │                          │ │ same name multi-attach
└─────────────────────┘                          │ │
         │                                       │ │
         ▼                           (tmux daemon, shared across sessions,
 conversations/<id>.json              survives FastAPI restarts)
 { type: "terminal",
   tmux_session: "neuro-<ws>-<proj>-<8>",
   workspace_id, project_id, title, workdir }
```

## Data model

`conversations/<id>.json` gains three optional fields. All other fields keep existing semantics:

| Field | Type | Meaning |
|---|---|---|
| `type` | `"chat"` (default, implied) \| `"terminal"` | Discriminator. Absent ⇒ `"chat"` so existing convs load unchanged. |
| `tmux_session` | string | Backend-managed tmux session name. Pattern: `neuro-<workspace_id>-<project_id>-<8hex>`. |
| `workdir` | string (absolute path) | Initial cwd for `tmux new-session -c …`. Optional. Defaults to the server process cwd. |

`messages[]` stays empty for terminals. Scrollback lives in tmux (`history-limit 10000`, tunable later). There is no per-message persistence in Neuro's store — reattach replays from tmux's own buffer.

Other existing fields (`agent_id`, `llm_settings`, `session_role`, `selection_type`, `history_summary`) are unused for terminals; they stay present but defaulted/null so the file shape is uniform.

### Session name convention

`neuro-<workspace_id>-<project_id>-<8-char-hex>`

- Slugify `workspace_id` and `project_id` if they contain unsafe chars for tmux names (`tmux` accepts most but let's be safe: `[a-zA-Z0-9_-]` only, lowercase).
- 8-char random suffix avoids collisions on repeated "new terminal" in the same project.
- Listing sessions for a project = `tmux list-sessions -F '#{session_name}'` filtered by prefix `neuro-<ws>-<proj>-`.

## API

### REST (metadata)

```
POST   /terminal                                 Create tab + tmux session
GET    /terminal?project_id=&agency_id=          List tabs for (project, workspace)
GET    /terminal/{cid}                           One tab
PATCH  /terminal/{cid}                           Rename title / rebind tmux_session
DELETE /terminal/{cid}?kill_session=0|1          Close tab (optional kill tmux)
GET    /terminal/sessions?project_id=&agency_id= List LIVE tmux sessions for a project
```

**`POST /terminal` body:**
```json
{
  "title": "build",
  "workspace_id": "default",
  "project_id": "main-default",
  "workdir": "/home/ubuntu/neuro",
  "tmux_session": null
}
```

- `title`: optional. If absent/empty, backend sets `"terminal"`.
- `workspace_id`, `project_id`: required. Enforced like existing `POST /conversation`.
- `workdir`: optional. If absent, pty inherits the FastAPI process cwd.
- `tmux_session: null` ⇒ backend generates `neuro-default-main-default-a1b2c3d4` and runs `tmux new-session -A -d -s <name> -c <workdir>`.
- `tmux_session: "<existing-name>"` ⇒ tab binds to an already-running session (this is how "attach existing" works from the switcher).

Response: the tab JSON on disk (same fields as in **Data model** above), plus a convenience `"available": true` so the client can distinguish "created" from "bound-to-existing" if it cares.

**`PATCH /terminal/{cid}` body:**
```json
{ "title": "new-name", "tmux_session": "neuro-default-main-default-b4e5f6a7" }
```
- Either field optional. Changing `tmux_session` is the mechanism for switching which session a tab is attached to. The frontend must tear down the current WS and open a new one after the PATCH.

**`DELETE /terminal/{cid}?kill_session=1`:** deletes the conv JSON AND runs `tmux kill-session -t <name>`. With `kill_session=0` (default), only the tab is forgotten; the tmux session keeps running and can be reattached via a new tab.

**`GET /terminal/sessions?project_id=…&agency_id=…`:** calls `tmux list-sessions -F '#{session_name} #{session_created} #{session_attached} #{session_windows}'`, filters to sessions whose name starts with `neuro-<ws>-<proj>-`, returns:
```json
[
  { "name": "neuro-default-main-default-a1b2c3d4",
    "created_at": 1713312000, "attached_clients": 0, "windows": 1 }
]
```

### WebSocket (live I/O)

```
ws://<host>:7001/terminal/ws/{cid}?token=<jwt>
```

- Auth token: same as existing `/chat/token` flow. Reject connection if the token's cid doesn't match the URL cid.
- Subprotocol: none. Binary frames = pty bytes; text frames = JSON control messages.

**Frame definitions:**

```
Client → Server
  binary       raw stdin bytes (keystrokes)
  text JSON    { "type": "resize", "cols": 120, "rows": 30 }
             | { "type": "ping" }

Server → Client
  binary       raw stdout bytes (direct pty.read())
  text JSON    { "type": "ready" }                    // sent once after attach
             | { "type": "exit", "code": 0 }          // pty EOF / tmux died
             | { "type": "error", "msg": "..." }      // fatal; client should show + allow retry
             | { "type": "pong" }                     // for ping
```

**Server flow on WS connect:**
1. Validate token; load `conversations/{cid}.json`; confirm `type == "terminal"`; read `tmux_session`.
2. `tmux has-session -t <name>`:
   - Present ⇒ continue.
   - Missing ⇒ `tmux new-session -A -d -s <name> -c <workdir>` (auto-recreate).
3. Spawn a `ptyprocess.PtyProcess` running `["tmux", "attach", "-t", <name>]` with `TERM=xterm-256color`.
4. Send `{"type":"ready"}` text frame.
5. Concurrently:
   - Read pty master → send binary frame to ws.
   - Receive ws binary → write to pty.
   - Receive ws text `resize` → `pty.setwinsize(rows, cols)`.
   - Receive ws text `ping` → reply `pong`.
6. On ws close: `pty.close()` (detach from tmux — does NOT kill the tmux session).
7. On pty EOF while ws open: send `{"type":"exit","code":<N>}`, close ws.

**Multi-attach:** Allowed. Two ws connections for same cid each get their own pty → each attaches to the same tmux session. Tmux handles the rest (both clients see identical output, both can type — same as `tmux attach` from two real terminals).

## Backend implementation

**Python deps (add to `requirements.txt`):**
- `ptyprocess` — for pty master/slave + `setwinsize`.

(`tmux` itself is a system binary; detect with `shutil.which("tmux")` at startup. If absent, feature is gated off — REST returns 501, UI hides creation entry.)

**New module: `core/tmux_manager.py`**

Responsibilities:
- `new_session(name, workdir)` — shell-out to `tmux new-session -A -d -s <name> -c <workdir>`. Idempotent.
- `session_exists(name)` — `tmux has-session -t <name>`, return bool.
- `list_sessions(prefix)` — parse `tmux list-sessions -F '…'`, filter by prefix, return list of dicts.
- `kill_session(name)` — `tmux kill-session -t <name>`.
- Helper: `make_session_name(ws_id, proj_id)` returns `neuro-<slug-ws>-<slug-proj>-<8hex>`.

All functions synchronous shell-outs (tmux CLI is fast, microseconds per call). Called from FastAPI async handlers via `asyncio.to_thread` or directly (they're quick).

**New module: `core/terminal_ws.py`**

Holds the async pty bridge. One instance per live WS connection:
- Opens pty → exec tmux attach
- Two tasks: `_pump_pty_to_ws` (uses `loop.add_reader` on pty master fd, non-blocking `os.read` chunks of ≤ 4 KB, ws.send_bytes), `_pump_ws_to_pty` (`async for msg in ws`, dispatch binary/text).
- `asyncio.gather` them; first to exit cancels the other; `finally` closes pty.
- If `add_reader` ever misbehaves on the pty master (has happened historically with certain tmux/kernel combos), fall back to a thread reader + `asyncio.Queue`. Code-ready as a toggle.

**FastAPI routes in `server.py` (new file `server_terminal.py` included from `server.py`):**
- The six REST endpoints above.
- `@app.websocket("/terminal/ws/{cid}")`.

**Feature gate:**
- On startup, check `shutil.which("tmux")`. If missing, register a middleware / route guard that returns 501 for `/terminal/*` with a message: `"tmux not installed on host. apt install tmux / brew install tmux."`.
- Expose `GET /terminal/capabilities` → `{"available": true/false, "reason": "..."}` so frontend can hide UI entries cleanly.

**Concurrency invariants:**
- WS connection holds references: `conv_json`, `tmux_session`, `pty`. Nothing global except the tmux daemon itself.
- No in-memory registry of pts needed — each ws owns its lifecycle.
- Multi-attach correctness relies entirely on tmux's own multi-client support; Neuro doesn't coordinate.

## Frontend

**New deps (`package.json`):**
- `xterm`
- `xterm-addon-fit`
- `xterm-addon-webgl`
- `xterm-addon-web-links`

**Component tree:**

```
TabBar (existing)
 └─ "+" → dropdown: [ "New Chat", "New Terminal" ]

Active tab renderer (existing logic switches on tab.type):
 ├─ type === "chat"      → ChatPanel + ChatInput  (existing)
 └─ type === "terminal"  → TerminalPanel
                            ├─ TerminalHeader (title, session switcher, reconnect button)
                            ├─ XTermContainer (mounts xterm, binds WS)
                            └─ MobileKeyBar  (viewport ≤ 640px)
```

**`TerminalPanel.tsx`:**
- On mount: reads `tab.cid`, calls `useTerminalWs(cid)` hook.
- Renders xterm via ref; applies FitAddon, WebGL addon (skip WebGL on mobile), WebLinks addon.
- Emits `{type:"resize", ...}` whenever container resizes (debounced 50 ms).
- Forwards all user input → `ws.send(bytes)`.
- Receives binary → `term.write(data)`.

**`useTerminalWs(cid)` hook:**
- Opens ws to `/terminal/ws/{cid}?token=<…>` (token fetched from existing chat token endpoint).
- Exponential-backoff reconnect: 1s, 2s, 4s, 8s, cap 10s. Reset on clean success.
- Exposes `{ status: "connecting"|"ready"|"reconnecting"|"error", send: (bytes)=>void }`.

**Tab creation:**
- `TabBar` "+" becomes a dropdown: `New Chat`, `New Terminal`. On "New Terminal":
  1. `POST /terminal` body: `{ title: "terminal", workspace_id, project_id }` (uses currently selected workspace + project, defaulting to Main Project like existing conv creation).
  2. On success: `dispatch(openTab({ cid, title, type: "terminal", isActive: true }))`.
  3. `TerminalPanel` mounts, hook connects, user sees prompt within ~1 second.

**Session switcher (hybrid attach):**
- `TerminalHeader` has a dropdown showing live sessions from `GET /terminal/sessions?project_id=…`.
- Current session highlighted; other sessions pickable.
- Picking: `PATCH /terminal/{cid}` with `{tmux_session}` → WS closes → reopens → attaches to new session.
- Dropdown also has "+ new session" entry → `POST /terminal` with `tmux_session: null` (new tab) OR rebind current tab (still TBD via UX; default: always new tab for clarity).

**Tab pill differentiation:**
- Terminal tab pill shows `>_` icon (lucide `Terminal`) instead of agent avatar.
- Same tab close behavior as chat tabs.
- Deleting a tab prompts: "Also kill the tmux session?" — default No.

**Mobile virtual key bar:**
- Shown when `viewport width ≤ 640px`.
- Rows: `Ctrl` `Esc` `Tab` `↑` `↓` `←` `→` with a `…` overflow for F-keys and modifier combos.
- `Ctrl` acts as sticky modifier: tap → next keystroke is prefixed with `\x03` for C, or whatever `Ctrl-<x>` maps to (`String.fromCharCode(k & 0x1f)`).

**Redux:**
- New slice `terminalSlice`:
  - `sessionsByProject: Record<projectId, SessionInfo[]>` — cached list from `/terminal/sessions`.
  - `wsStatusByCid: Record<cid, "connecting"|"ready"|"reconnecting"|"error">`.
  - Async thunks: `fetchTerminalSessions(projectId)`, `createTerminal({title, workspaceId, projectId})`, `deleteTerminal({cid, killSession})`.
- Terminal tabs still live in the existing `conversations` slice via `openTab` — they're conversations with `type: "terminal"`.

## Failure handling

| Scenario | Detection | Response |
|---|---|---|
| `tmux` not installed | startup probe / `GET /terminal/capabilities` returns `available:false` | UI hides "New Terminal" entry; REST routes return 501. |
| `tmux new-session` fails (bad cwd, permission) | nonzero exit from shell-out | `POST /terminal` returns 500 with stderr; UI toast. |
| Session killed externally while tab is open | pty EOF on the ws server side | WS sends `{"type":"exit","code":N}`; UI shows banner `"Session ended. [Recreate]"`; Recreate re-posts with same name to `tmux new-session -A -d`. |
| Session-name collision | `tmux new-session -A` (attach-if-exists flag) | No-op; tab binds to existing session. |
| WS disconnects mid-stream | `onclose` event | Backoff reconnect loop. Tmux scrollback reattaches on success — user sees recent output preserved. |
| Runaway output flood | — | Starlette `ws.send_bytes` back-pressures; xterm.js queues writes. If ws send-buffer passes ~4 MB, drop non-critical chunks + log warning (rare; most terminal programs self-throttle on TTY). |
| FastAPI restart while tab open | ws closes from server side | Reconnect loop handles it. tmux daemon survives independently → session state intact. |
| Host reboot | tmux daemon dies | Saved `tmux_session` name won't resolve. On next WS connect, server detects miss and auto-recreates with `tmux new-session -A -d` (empty session). UI optionally notifies "previous session was lost on host restart". |
| Binary doesn't honor `TERM` | — | Set `TERM=xterm-256color` when spawning pty. Covers vim/htop/top/nano/less. |

## Security

Explicit v1 assumption: the web UI is trusted. Anyone who can reach the Neuro backend can open a terminal and run commands as the `ubuntu` user. This is fine for localhost / single-user deployments (current model). Before exposing Neuro over a network:

- Bind cid ↔ owning user (requires user identity model, which Neuro doesn't have yet).
- Add allow-list of commands, or run shells in a sandbox (bubblewrap, podman).
- Audit log of terminal sessions.

These are explicitly out of scope for v1 but noted so they're not forgotten.

## Testing plan

**Unit (backend, `tests/test_tmux_manager.py`):**
- `make_session_name("default","main-default")` produces `neuro-default-main-default-<8hex>` with a fresh suffix each call.
- `new_session(name, workdir)` is idempotent — calling twice doesn't create two sessions.
- `session_exists` correct for present, absent, and just-killed sessions.
- `list_sessions(prefix)` filters correctly when multiple unrelated tmux sessions exist on the host.

**Integration (backend, `tests/test_terminal_api.py`):**
- `POST /terminal` → response JSON has `type:"terminal"`, `tmux_session` matches naming pattern; `tmux has-session` passes.
- `DELETE /terminal/{cid}?kill_session=1` → session gone.
- `DELETE /terminal/{cid}?kill_session=0` → session still running, conv JSON deleted.
- `GET /terminal/sessions?project_id=X&agency_id=Y` returns only sessions with the correct prefix.
- WS round-trip (using `websockets` client in test): connect, send `b"echo hi\n"`, within 500 ms receive binary containing both the echo and the output.
- WS resize: send resize text frame, then `b"stty size\n"`, parse received output, assert dimensions match.
- Reconnect continuity: connect, send `b"echo marker\n"`, disconnect, reconnect same cid — within 2 s receive scrollback containing `"marker"` (tmux replays on attach).
- Capability gate: simulate `which("tmux")==None` (monkeypatch), assert `/terminal/*` returns 501.

**E2E (Playwright, `neuro_web/e2e/terminal.spec.ts`):**
- Click "+" → "New Terminal" → xterm shows shell prompt within 3 s.
- Type `ls\n` → output area contains a real directory listing.
- Close tab, confirm prompt "Kill session?" defaults No, tab disappears.
- Reopen same session from session switcher → scrollback shows earlier `ls` output.
- On viewport 375 × 812 (iPhone-sized), virtual key bar is visible; tap `Ctrl` then `C` sends `\x03` and cancels a running `sleep 10`.

**Manual smoke:**
- `vim /tmp/foo` → resize browser → vim redraws correctly.
- `htop` for 10 s → no garbage, smooth cursor movement.
- `ssh localhost` from inside the terminal → escapes pass through untouched.
- `cat` a 1 MB file → output arrives without browser lockup.
- System-clipboard copy/paste works both ways.

## Out of scope for v1

- Agent-driven / shared-session mode (option "c" from brainstorming). Deferred — requires a protocol for agent to inject keystrokes and scrape output while a human is also typing. Design will build on this spec.
- Per-user identity binding and multi-tenant isolation.
- Command audit log.
- Configurable scrollback size via UI.
- SSH profile manager (user can still just type `ssh host` inside a terminal).
- Terminal themes / color customization.

## Open questions (none blocking)

- Where exactly does "+ new session" inside the switcher dropdown land — rebind current tab, or open a new tab? Current spec defaults to "new tab" for clarity; revisit during UX review.
- Should we add a keyboard shortcut (e.g. `Ctrl+Shift+`` ` `) for "New Terminal" once users have the feature? Not in v1 plan.
