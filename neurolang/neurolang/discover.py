"""Filesystem auto-discovery of user neuros.

Eager scan triggered at CLI startup (or via explicit `discover_neuros()` call).
Imports each `.py` from:
  1. `~/.neurolang/neuros/` (user-global)
  2. `<project_root>/neuros/` (where project_root = nearest ancestor of cwd
     containing `.neurolang`, `pyproject.toml`, `setup.py`, or `.git`)
  3. Any directories passed via `extra_paths=`

The `@neuro` decorator side-effect-registers each neuro into the default
registry as its file is imported. This module is *only* responsible for
finding and importing those files.

Idempotency: a module-level `_imported` set tracks absolute paths so
repeated `discover_neuros()` calls in the same process don't re-import.
"""
from __future__ import annotations

import importlib.util
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Project-root marker files / dirs, in priority order.
# `.neurolang` first because it's the explicit "this IS a NeuroLang project" signal.
_PROJECT_MARKERS = (".neurolang", "pyproject.toml", "setup.py", ".git")


# Module-level state for idempotency. Holds absolute Path objects already imported.
_imported: set[Path] = set()


@dataclass
class DiscoveryReport:
    """Summary of one discovery pass."""
    user_dir_neuros: list[Path] = field(default_factory=list)
    project_dir_neuros: list[Path] = field(default_factory=list)
    extra_neuros: list[Path] = field(default_factory=list)
    project_root: Optional[Path] = None
    errors: list[tuple[Path, str]] = field(default_factory=list)


def find_project_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from `start` (default cwd) looking for a project marker.
    Returns the first ancestor directory containing a marker, or None.
    """
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        for marker in _PROJECT_MARKERS:
            if (d / marker).exists():
                return d
    return None


def _user_neuros_dir() -> Path:
    return Path.home() / ".neurolang" / "neuros"


def _import_file(path: Path) -> None:
    """Import a .py file as a module. Raises on import error."""
    abs_path = path.resolve()
    # Use a unique module name so repeated paths-in-different-tmpdirs
    # never collide in sys.modules.
    mod_name = f"_neurolang_discovered_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(mod_name, abs_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not build module spec for {abs_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        # Don't leave a broken module in sys.modules
        sys.modules.pop(mod_name, None)
        raise


def _scan_dir(directory: Path) -> list[Path]:
    """Return sorted list of .py files (non-recursive, skip __init__/dunders)."""
    if not directory.exists() or not directory.is_dir():
        return []
    return sorted(
        p for p in directory.glob("*.py")
        if not p.name.startswith("_")
    )


# Note on the broad `except Exception` blocks below (one per phase):
# discovered files are user code from the filesystem. We catch Exception
# (not BaseException) so KeyboardInterrupt and SystemExit still propagate,
# but every other failure is contained — one bad neuro must not break the CLI.
def discover_neuros(extra_paths: Optional[list[Path]] = None) -> DiscoveryReport:
    """Scan the standard discovery directories and import each .py file.

    Idempotent: files already imported in this process are skipped.
    Errors loading individual files do not abort the scan; they are
    collected into `report.errors`.
    """
    report = DiscoveryReport()
    extra_paths = list(extra_paths or [])

    # 1. User-global dir
    user_dir = _user_neuros_dir()
    for f in _scan_dir(user_dir):
        if f.resolve() in _imported:
            continue
        try:
            _import_file(f)
            _imported.add(f.resolve())
            report.user_dir_neuros.append(f)
        except Exception as e:
            report.errors.append((f, f"{type(e).__name__}: {e}"))

    # 2. Project dir
    project_root = find_project_root()
    report.project_root = project_root
    if project_root is not None:
        for f in _scan_dir(project_root / "neuros"):
            if f.resolve() in _imported:
                continue
            try:
                _import_file(f)
                _imported.add(f.resolve())
                report.project_dir_neuros.append(f)
            except Exception as e:
                report.errors.append((f, f"{type(e).__name__}: {e}"))

    # 3. Extra paths
    for d in extra_paths:
        for f in _scan_dir(Path(d)):
            if f.resolve() in _imported:
                continue
            try:
                _import_file(f)
                _imported.add(f.resolve())
                report.extra_neuros.append(f)
            except Exception as e:
                report.errors.append((f, f"{type(e).__name__}: {e}"))

    return report


def reset() -> None:
    """Clear discovery state.

    Empties the idempotency set AND removes every previously-imported
    discovered module from `sys.modules`. Call between discovery passes
    when you need a clean slate (test fixtures, REPL workflows).
    """
    _imported.clear()
    for name in list(sys.modules):
        if name.startswith("_neurolang_discovered_"):
            sys.modules.pop(name, None)
