"""Model Library — named model aliases + roles.

Stores a user-editable two-layer library:
  * ModelAlias : named pointer to (provider, model_id) with description
  * Role       : named intent slot with ordered candidate aliases + one pinned

Persisted as a single JSON file next to the SQLite db. Hot-reloaded via
mtime check on every read. No schema migrations — extending the shape
later is a matter of adding optional keys.
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from core.llm_registry import get_default_llm_settings, normalize_provider


_DB_PATH = os.getenv("DB_PATH", "/home/ubuntu/neurocomputer/data/neuro.db")
LIBRARY_PATH = os.getenv(
    "MODEL_LIBRARY_PATH",
    os.path.join(os.path.dirname(_DB_PATH), "model_library.json"),
)

_lock = threading.RLock()
_cache: Dict[str, Any] = {}
_cache_mtime: float = 0.0


# ---------------------------------------------------------------- seeding
def _default_library() -> Dict[str, Any]:
    """First-boot bundle: one "default" alias + five starter roles all pinned to it."""
    defaults = get_default_llm_settings()
    provider = defaults["provider"]
    model_id = defaults["model"]
    default_slug = "default"
    aliases = {
        default_slug: {
            "display_name": "Default",
            "description": f"Default model ({provider} / {model_id})",
            "provider": provider,
            "model_id": model_id,
        }
    }
    seed_roles = [
        ("router", "Router", "Fast routing and classification"),
        ("planner", "Planner", "Multi-step task planning"),
        ("replier", "Replier", "Conversational reply"),
        ("philosopher", "Philosopher", "Reflection and analysis"),
        ("coder", "Coder", "Code generation and editing"),
    ]
    roles = {
        slug: {
            "display_name": name,
            "description": desc,
            "candidates": [default_slug],
            "pinned": default_slug,
        }
        for slug, name, desc in seed_roles
    }
    return {"aliases": aliases, "roles": roles}


# ---------------------------------------------------------------- io
def _write(data: Dict[str, Any]) -> None:
    Path(LIBRARY_PATH).parent.mkdir(parents=True, exist_ok=True)
    tmp = LIBRARY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, LIBRARY_PATH)


def _read_from_disk() -> Dict[str, Any]:
    with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _deep_copy(data: Dict[str, Any]) -> Dict[str, Any]:
    return json.loads(json.dumps(data))


def load_library() -> Dict[str, Any]:
    """Return current library. Seeds defaults on first call, hot-reloads on mtime change."""
    global _cache, _cache_mtime
    with _lock:
        if not os.path.exists(LIBRARY_PATH):
            seeded = _default_library()
            _write(seeded)
            _cache = seeded
            _cache_mtime = os.path.getmtime(LIBRARY_PATH)
            return _deep_copy(seeded)
        mtime = os.path.getmtime(LIBRARY_PATH)
        if mtime != _cache_mtime or not _cache:
            _cache = _read_from_disk()
            _cache_mtime = mtime
        return _deep_copy(_cache)


def save_library(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the whole library and write atomically. Returns the saved shape."""
    validated = _validate(data)
    with _lock:
        _write(validated)
        global _cache, _cache_mtime
        _cache = validated
        _cache_mtime = os.path.getmtime(LIBRARY_PATH)
    return _deep_copy(validated)


# ---------------------------------------------------------------- validation
def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("library must be a dict")
    aliases_in = data.get("aliases") or {}
    roles_in = data.get("roles") or {}
    if not isinstance(aliases_in, dict):
        raise ValueError("'aliases' must be a dict keyed by slug")
    if not isinstance(roles_in, dict):
        raise ValueError("'roles' must be a dict keyed by slug")

    clean_aliases: Dict[str, Any] = {}
    for slug, a in aliases_in.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError(f"alias slug must be a non-empty string: {slug!r}")
        if not isinstance(a, dict):
            raise ValueError(f"alias {slug!r} must be a dict")
        provider = a.get("provider")
        model_id = a.get("model_id")
        if not provider or not isinstance(provider, str):
            raise ValueError(f"alias {slug!r}: 'provider' is required")
        if not model_id or not isinstance(model_id, str):
            raise ValueError(f"alias {slug!r}: 'model_id' is required")
        clean_aliases[slug] = {
            "display_name": str(a.get("display_name") or slug),
            "description": str(a.get("description") or ""),
            "provider": normalize_provider(provider),
            "model_id": model_id.strip(),
        }

    clean_roles: Dict[str, Any] = {}
    for slug, r in roles_in.items():
        if not isinstance(slug, str) or not slug.strip():
            raise ValueError(f"role slug must be a non-empty string: {slug!r}")
        if not isinstance(r, dict):
            raise ValueError(f"role {slug!r} must be a dict")
        candidates = r.get("candidates") or []
        if not isinstance(candidates, list) or not all(isinstance(c, str) for c in candidates):
            raise ValueError(f"role {slug!r}: 'candidates' must be a list of alias slugs")
        if not candidates:
            raise ValueError(f"role {slug!r}: needs at least one candidate")
        for c in candidates:
            if c not in clean_aliases:
                raise ValueError(f"role {slug!r}: unknown alias {c!r} in candidates")
        pinned = r.get("pinned") or candidates[0]
        if pinned not in candidates:
            raise ValueError(f"role {slug!r}: pinned {pinned!r} must be one of candidates")
        clean_roles[slug] = {
            "display_name": str(r.get("display_name") or slug),
            "description": str(r.get("description") or ""),
            "candidates": list(candidates),
            "pinned": pinned,
        }

    return {"aliases": clean_aliases, "roles": clean_roles}


# ---------------------------------------------------------------- resolvers
def resolve_alias(slug: str) -> Optional[Dict[str, str]]:
    """Alias slug → ``{"provider", "model"}`` (shape matches brain llm_settings)."""
    if not slug:
        return None
    a = load_library()["aliases"].get(slug)
    if not a:
        return None
    return {"provider": a["provider"], "model": a["model_id"]}


def resolve_role(slug: str) -> Optional[Dict[str, str]]:
    """Role slug → pinned alias's ``{"provider", "model"}``, or None if unknown."""
    if not slug:
        return None
    r = load_library()["roles"].get(slug)
    if not r:
        return None
    return resolve_alias(r["pinned"])


def list_aliases() -> Dict[str, Any]:
    return load_library()["aliases"]


def list_roles() -> Dict[str, Any]:
    return load_library()["roles"]
