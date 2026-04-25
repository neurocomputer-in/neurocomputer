"""tmux session manager — thin wrapper around the tmux CLI.

All functions are synchronous shell-outs; tmux CLI is fast
(microseconds) so callers can invoke directly from async handlers
without threading.
"""
from __future__ import annotations

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
    """Pattern: ``neuro-<ws>-<proj>-<8hex>``. Slugs are lowercase,
    ``[a-z0-9-]`` only, collapsed hyphens."""
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
    """Idempotent: if the session already exists, this is a no-op.

    We use explicit ``has-session`` rather than tmux's ``-A`` flag because
    ``new-session -A`` still tries to attach to the existing session, which
    fails with ``open terminal failed: not a terminal`` when invoked from a
    non-tty parent (FastAPI worker, pytest, subprocess)."""
    if session_exists(name):
        return
    cmd = ["tmux", "new-session", "-d", "-s", name]
    if workdir:
        cmd += ["-c", workdir]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"tmux new-session failed: {r.stderr.strip()}")
    # Bump history and enable mouse so desktop wheel-scroll works natively and
    # the frontend can drive copy-mode scroll via `send-keys -X` (mobile bar).
    for opt, val in (("history-limit", "10000"), ("mouse", "on")):
        subprocess.run(
            ["tmux", "set-option", "-t", name, opt, val],
            capture_output=True,
        )


def send_keys(name: str, text: str, submit: bool = True) -> bool:
    """Push ``text`` into the given tmux session as if the user typed it.
    If ``submit`` is true, an Enter is appended so the line executes.
    Uses ``-l`` (literal) so special shell characters aren't reinterpreted
    by tmux's key-binding parser."""
    if not name or not text:
        return False
    r = subprocess.run(
        ["tmux", "send-keys", "-t", name, "-l", text],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return False
    if submit:
        r2 = subprocess.run(
            ["tmux", "send-keys", "-t", name, "Enter"],
            capture_output=True, text=True,
        )
        return r2.returncode == 0
    return True


# short name → copy-mode command understood by `tmux send-keys -X`
_COPYMODE_ACTIONS = {
    "up":           "scroll-up",
    "down":         "scroll-down",
    "page-up":      "page-up",
    "page-down":    "page-down",
    "halfpage-up":  "halfpage-up",
    "halfpage-down":"halfpage-down",
    "top":          "history-top",
    "cancel":       "cancel",
}

# short name → literal key name that `tmux send-keys` sends to the app.
# Used when the pane is in alternate-screen mode (TUI running — tmux has
# no scrollback for this pane; the app owns its own viewport and must be
# driven via its own key bindings).
_TUI_KEYS = {
    "up":           "Up",
    "down":         "Down",
    "page-up":      "PPage",
    "page-down":    "NPage",
    "halfpage-up":  "PPage",
    "halfpage-down":"NPage",
    "top":          "Home",
    "cancel":       "Escape",
}


def _is_alt_screen(name: str) -> bool:
    r = subprocess.run(
        ["tmux", "display-message", "-p", "-t", name, "#{alternate_on}"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() == "1"


def _has_mouse_any(name: str) -> bool:
    """True when the pane's app has mouse reporting enabled (DECSET 1000/1002/1003)."""
    r = subprocess.run(
        ["tmux", "display-message", "-p", "-t", name, "#{mouse_any_flag}"],
        capture_output=True, text=True,
    )
    return r.stdout.strip() == "1"


def scroll(name: str, action: str, count: int = 1) -> bool:
    """Scroll the tmux pane in response to a frontend request.

    * ``count`` repeats the action in a SINGLE tmux invocation via
      ``send-keys -N <count>``. This lets the frontend batch rapid
      taps / touch-drag deltas into one round trip — big latency win.
    * Routes by pane mode & app capability:
        - Alt-screen TUI with mouse reporting on (vim, opencode, less):
          send mouse-wheel events via tmux's proper forwarding mechanism
          — ``send-keys -M`` with a synthesized WheelUp/WheelDown mouse
          event. This is exactly what tmux does internally when a real
          mouse-wheel event arrives from the terminal.
        - Alt-screen TUI WITHOUT mouse reporting: fall back to PPage /
          NPage which most TUIs interpret as "scroll main content".
        - Normal screen (shell): enter copy-mode and dispatch
          ``send-keys -X <cmd>`` to navigate tmux's scrollback.
    """
    count = max(1, min(200, count))
    n_flag = ["-N", str(count)] if count > 1 else []

    if _is_alt_screen(name):
        if action in ("up", "down") and _has_mouse_any(name):
            # Synthesize a mouse-wheel event at (1,1) and let tmux forward
            # it to the pane's app using its own send-keys -M mechanism.
            # WheelUpPane / WheelDownPane are tmux's built-in mouse keys.
            mouse_key = "WheelUpPane" if action == "up" else "WheelDownPane"
            r = subprocess.run(
                ["tmux", "send-keys", "-t", name, *n_flag, "-M", mouse_key],
                capture_output=True,
            )
            return r.returncode == 0

        # Plain key forward (works for page-up/page-down across most TUIs,
        # and for up/down in apps that don't have mouse reporting).
        key = _TUI_KEYS.get(action)
        if not key:
            return False
        r = subprocess.run(
            ["tmux", "send-keys", "-t", name, *n_flag, key],
            capture_output=True,
        )
        return r.returncode == 0

    cmd_name = _COPYMODE_ACTIONS.get(action)
    if not cmd_name:
        return False
    if cmd_name == "cancel":
        r = subprocess.run(
            ["tmux", "send-keys", "-t", name, "-X", "cancel"],
            capture_output=True,
        )
    else:
        r = subprocess.run(
            ["tmux",
             "copy-mode", "-t", name,
             ";",
             "send-keys", "-t", name, *n_flag, "-X", cmd_name],
            capture_output=True,
        )
    return r.returncode == 0


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
    out: list[dict] = []
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
