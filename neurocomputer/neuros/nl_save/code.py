import re
from pathlib import Path
from typing import Any, Dict

NL_NEURO_DIR = Path.home() / ".neurolang" / "neuros"


def _slug(s: str, fallback: str = "flow") -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", s.lower()).strip("_")
    return s[:60] or fallback


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    source = kwargs.get("source") or state.get("source") or ""
    if not source:
        return {"error": "nl_save: no source to save"}
    name = kwargs.get("name") or _slug(state.get("prompt", "") or state.get("__prompt", "") or "flow")
    NL_NEURO_DIR.mkdir(parents=True, exist_ok=True)
    path = NL_NEURO_DIR / f"{name}.py"
    path.write_text(source, encoding="utf-8")
    return {"path": str(path), "name": name}
