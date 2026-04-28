"""File-based cache for NL ↔ formal compilations.

Keyed by hash(prompt + model + library_version). Stores generated Python
source and (lazily) reverse-compiled NL summaries. Lives at
~/.neurolang/cache/ by default.

This cache is the *unit/counit data* of the NL ↔ formal adjunction made
into storage — not just a perf optimization, but the categorical contract.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


def _default_dir() -> Path:
    return Path(os.environ.get("NEUROLANG_CACHE", str(Path.home() / ".neurolang" / "cache")))


@dataclass
class CacheEntry:
    key: str
    prompt: str
    model: str
    library_version: str
    source_path: str
    summary: Optional[str] = None


class CompilerCache:
    """Persistent cache for NL→source and source→NL round-trips."""

    def __init__(self, root: Optional[Path] = None):
        self.root = Path(root) if root else _default_dir()
        self.flows_dir = self.root / "flows"
        self.flows_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        self._index: dict[str, dict] = self._load_index()

    # --- Key derivation -------------------------------------------------------

    def make_key(
        self,
        prompt: str,
        *,
        model: str,
        library_version: str,
        system_fingerprint: str = "",
    ) -> str:
        h = hashlib.sha256(
            f"{model}|{library_version}|{system_fingerprint}|{prompt.strip()}".encode("utf-8")
        )
        return h.hexdigest()[:16]

    # --- Forward (NL → source) ------------------------------------------------

    def get_forward(self, key: str) -> Optional[CacheEntry]:
        if key not in self._index:
            return None
        rec = self._index[key]
        # Lazy-load source from disk
        src_path = self.flows_dir / f"{key}.py"
        if not src_path.exists():
            return None
        return CacheEntry(
            key=key,
            prompt=rec["prompt"],
            model=rec["model"],
            library_version=rec["library_version"],
            source_path=str(src_path),
            summary=rec.get("summary"),
        )

    def put_forward(self, *, key: str, prompt: str, model: str,
                    library_version: str, source: str) -> CacheEntry:
        src_path = self.flows_dir / f"{key}.py"
        src_path.write_text(source)
        self._index[key] = {
            "prompt": prompt,
            "model": model,
            "library_version": library_version,
        }
        self._save_index()
        return CacheEntry(
            key=key, prompt=prompt, model=model,
            library_version=library_version, source_path=str(src_path),
        )

    # --- Reverse (source → summary) ------------------------------------------

    def put_summary(self, key: str, summary: str) -> None:
        if key in self._index:
            self._index[key]["summary"] = summary
            self._save_index()

    def get_summary(self, key: str) -> Optional[str]:
        return self._index.get(key, {}).get("summary")

    # --- Listing & cleanup ----------------------------------------------------

    def list(self) -> list[dict]:
        return [{"key": k, **v} for k, v in self._index.items()]

    def clear(self) -> None:
        for f in self.flows_dir.glob("*.py"):
            f.unlink()
        self._index = {}
        self._save_index()

    # --- Persistence ----------------------------------------------------------

    def _load_index(self) -> dict:
        if not self.index_path.exists():
            return {}
        try:
            return json.loads(self.index_path.read_text())
        except Exception:
            return {}

    def _save_index(self) -> None:
        self.index_path.write_text(json.dumps(self._index, indent=2, sort_keys=True))
