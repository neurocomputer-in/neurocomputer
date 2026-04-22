"""Dev-agent robustness pipeline.

The functions here are the safety net for self-modification. Any neuro
(or script, or human) wanting to write a new neuro to disk should go
through `atomic_save_neuro` so we always have: schema validation,
syntax gate, snapshot of the previous version, atomic file swap,
structured error envelopes.

Spec: docs/superpowers/specs/2026-04-20-neuro-arch/02-dev-agent/
      01-robustness-patterns.md + 02-self-mod-safety.md
"""
import ast
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
NEUROS_DIR = REPO_ROOT / "neuros"
SNAPSHOTS_DIR = REPO_ROOT / ".neuros_history"
MAX_SNAPSHOTS_PER_NEURON = 10


# Fields the validator knows about. Anything else gets a warning but
# isn't a hard fail (forward-compat for new kinds adding new conf fields).
SCHEMA_REQUIRED = ["name", "description"]

# Forbidden calls in AI-authored code. AST-level check; catches obvious
# shell escape attempts. Human-authored code (marked by author=human on
# the event envelope) can opt out of this check in the caller.
FORBIDDEN_CALLS = {
    "os.system", "subprocess.call", "subprocess.run", "subprocess.Popen",
    "os.popen", "os.execv", "os.execvp",
}

NEURO_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


# ────────────────────────────────────────────────────────────────────
#  validators
# ────────────────────────────────────────────────────────────────────

def validate_conf_json(conf) -> dict:
    """conf may be a str (to be parsed) or a dict. Returns:
        {'ok': bool, 'errors': [str], 'conf': dict | None}
    """
    errors = []
    if isinstance(conf, str):
        try:
            conf = json.loads(conf)
        except json.JSONDecodeError as e:
            return {"ok": False,
                    "errors": [f"invalid JSON: {e.msg} (line {e.lineno})"],
                    "conf": None}
    if not isinstance(conf, dict):
        return {"ok": False,
                "errors": ["conf must be a JSON object"],
                "conf": None}
    for req in SCHEMA_REQUIRED:
        if req not in conf:
            errors.append(f"missing required field: {req!r}")
    name = conf.get("name")
    if name is not None and not NEURO_NAME_RE.match(str(name)):
        errors.append(
            f"name must be snake_case (a-z, 0-9, _), starting w/ a letter: {name!r}"
        )
    for listy in ("inputs", "outputs", "uses", "children"):
        if listy in conf and not isinstance(conf[listy], list):
            errors.append(f"{listy!r} must be a list")

    return {"ok": not errors, "errors": errors,
            "conf": conf if not errors else None}


def validate_code_py(src: str, *, author: str = "ai") -> dict:
    """AST-parses + checks for run + forbidden calls.
    Human-authored code can skip forbidden-call scan via author='human'.
    """
    errors = []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {"ok": False,
                "errors": [f"SyntaxError line {e.lineno}: {e.msg}"]}

    if not _has_run_signature(tree):
        errors.append(
            "code.py must define either `async def run(state, **kw)` or "
            "a class with `async def run(self, state, **kw)`"
        )

    if author == "ai":
        for call_name, lineno in _forbidden_calls(tree):
            errors.append(
                f"forbidden call {call_name!r} on line {lineno} "
                "(AI-authored code is not allowed to shell-out)"
            )

    return {"ok": not errors, "errors": errors}


# ────────────────────────────────────────────────────────────────────
#  atomic save + snapshot
# ────────────────────────────────────────────────────────────────────

def atomic_save_neuro(name: str,
                       conf,
                       code: str,
                       prompt: Optional[str] = None,
                       *,
                       author: str = "ai",
                       snapshot: bool = True) -> dict:
    """Full save pipeline:
      1. schema-validate conf
      2. syntax-validate code
      3. snapshot existing neuro dir
      4. write new files atomically (tempfile + rename)
      5. emit structured result

    Returns: {'ok': bool, 'errors'?: [str], 'stage'?: str,
              'snapshot'?: str, 'paths'?: {...}}
    """
    # Stage 1: schema
    vc = validate_conf_json(conf)
    if not vc["ok"]:
        return {"ok": False, "stage": "schema", "errors": vc["errors"]}
    conf_obj = vc["conf"]
    if conf_obj.get("name") and conf_obj["name"] != name:
        return {"ok": False, "stage": "schema",
                "errors": [f"conf.name {conf_obj['name']!r} != folder name {name!r}"]}

    # Stage 2: syntax
    vcode = validate_code_py(code, author=author)
    if not vcode["ok"]:
        return {"ok": False, "stage": "syntax", "errors": vcode["errors"]}

    target = NEUROS_DIR / name
    existed = (target / "conf.json").exists() or (target / "code.py").exists()
    target.mkdir(parents=True, exist_ok=True)

    # Stage 3: snapshot prior version
    snapshot_path = None
    if snapshot and existed:
        snapshot_path = _snapshot_dir(name)
        snapshot_path.mkdir(parents=True, exist_ok=True)
        for fname in ("conf.json", "code.py", "prompt.txt", "layout.json"):
            src = target / fname
            if src.exists():
                shutil.copy2(src, snapshot_path / fname)
        _prune_snapshots(name, MAX_SNAPSHOTS_PER_NEURON)

    # Stage 4: atomic write
    conf_text = (conf if isinstance(conf, str)
                 else json.dumps(conf_obj, indent=2) + "\n")
    try:
        _atomic_write(target / "conf.json", conf_text)
        _atomic_write(target / "code.py", code if code.endswith("\n") else code + "\n")
        if prompt is not None:
            _atomic_write(target / "prompt.txt",
                          prompt if prompt.endswith("\n") else prompt + "\n")
    except OSError as e:
        return {"ok": False, "stage": "write",
                "errors": [f"filesystem error: {e}"]}

    return {"ok": True,
            "stage": "saved",
            "snapshot": str(snapshot_path) if snapshot_path else None,
            "paths": {
                "conf":   str(target / "conf.json"),
                "code":   str(target / "code.py"),
                "prompt": str(target / "prompt.txt") if prompt is not None else None,
            }}


def rollback_neuro(name: str,
                    snapshot_ts: Optional[str] = None) -> dict:
    """Restore a neuro to a previous snapshot. Default: most recent."""
    hist = SNAPSHOTS_DIR / name
    if not hist.exists():
        return {"ok": False, "errors": [f"no snapshots for {name!r}"]}
    snaps = sorted([p for p in hist.iterdir() if p.is_dir()])
    if not snaps:
        return {"ok": False, "errors": ["snapshot directory is empty"]}

    pick = None
    if snapshot_ts:
        for s in snaps:
            if s.name == snapshot_ts:
                pick = s
                break
        if pick is None:
            return {"ok": False, "errors": [f"snapshot {snapshot_ts!r} not found"]}
    else:
        pick = snaps[-1]

    target = NEUROS_DIR / name
    target.mkdir(parents=True, exist_ok=True)
    restored = []
    for fname in ("conf.json", "code.py", "prompt.txt", "layout.json"):
        src = pick / fname
        if src.exists():
            shutil.copy2(src, target / fname)
            restored.append(fname)

    return {"ok": True,
            "restored_from": pick.name,
            "restored_files": restored}


def delete_neuro(name: str, folder: Optional[Path] = None) -> dict:
    """Remove a neuro's folder. Snapshots it first so it's recoverable
    via rollback_neuro(name, snapshot_ts=<ts>).

    `folder` should be the real on-disk folder (from factory.reg[name].folder
    for taxonomized neuros). Falls back to NEUROS_DIR/name for flat layouts.
    """
    target = Path(folder) if folder else (NEUROS_DIR / name)
    if not target.exists():
        return {"ok": False, "errors": [f"neuro folder not found: {target}"]}
    if not target.is_dir():
        return {"ok": False, "errors": [f"not a directory: {target}"]}

    # Snapshot first so delete is recoverable
    snapshot_path = _snapshot_dir(name)
    snapshot_path.mkdir(parents=True, exist_ok=True)
    for fname in ("conf.json", "code.py", "prompt.txt", "layout.json"):
        src = target / fname
        if src.exists():
            shutil.copy2(src, snapshot_path / fname)
    _prune_snapshots(name, MAX_SNAPSHOTS_PER_NEURON)

    try:
        shutil.rmtree(target)
    except OSError as e:
        return {"ok": False, "stage": "rmtree",
                "errors": [f"filesystem error: {e}"]}

    # Clean up empty parent dirs inside neuros/ (taxonomy housekeeping)
    parent = target.parent
    while parent != NEUROS_DIR and parent.is_relative_to(NEUROS_DIR):
        try:
            parent.rmdir()   # only succeeds if empty
        except OSError:
            break
        parent = parent.parent

    return {"ok": True,
            "stage": "deleted",
            "snapshot": str(snapshot_path),
            "deleted": str(target)}


def list_snapshots(name: str) -> list:
    hist = SNAPSHOTS_DIR / name
    if not hist.exists():
        return []
    return sorted([p.name for p in hist.iterdir() if p.is_dir()])


# ────────────────────────────────────────────────────────────────────
#  internal helpers
# ────────────────────────────────────────────────────────────────────

def _has_run_signature(tree) -> bool:
    # top-level async def run(...)
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "run":
            return True
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.AsyncFunctionDef) and item.name == "run":
                    return True
    return False


def _forbidden_calls(tree) -> list:
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _qualified_call_name(node)
            if name in FORBIDDEN_CALLS:
                out.append((name, getattr(node, "lineno", 0)))
    return out


def _qualified_call_name(node) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        parts = []
        cur = node.func
        while isinstance(cur, ast.Attribute):
            parts.insert(0, cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.insert(0, cur.id)
        return ".".join(parts)
    return ""


def _snapshot_dir(name: str) -> Path:
    ts = time.strftime("%Y-%m-%dT%H-%M-%SZ", time.gmtime())
    # On the off-chance two snapshots happen in the same second, append a tick.
    base = SNAPSHOTS_DIR / name / ts
    if base.exists():
        i = 1
        while (SNAPSHOTS_DIR / name / f"{ts}_{i}").exists():
            i += 1
        return SNAPSHOTS_DIR / name / f"{ts}_{i}"
    return base


def _prune_snapshots(name: str, keep: int) -> None:
    hist = SNAPSHOTS_DIR / name
    if not hist.exists():
        return
    snaps = sorted([p for p in hist.iterdir() if p.is_dir()])
    excess = len(snaps) - keep
    for p in snaps[:max(0, excess)]:
        try:
            shutil.rmtree(p)
        except OSError:
            pass


def _atomic_write(path: Path, content: str) -> None:
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    try:
        tmp.replace(path)    # atomic on POSIX
    except OSError:
        if tmp.exists():
            tmp.unlink()
        raise
