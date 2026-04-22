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
