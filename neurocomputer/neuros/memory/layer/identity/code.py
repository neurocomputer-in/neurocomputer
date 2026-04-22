"""memory_layer_identity — reads L0 identity from a flat file.

Per MEMORY_ARCHITECTURE.md §1: L0 is the always-loaded agent+user identity
core, hand-authored. Default path: mem/l0.md at repo root.

If the file doesn't exist, returns empty — downstream composers skip
empty blocks so this degrades gracefully.
"""
import os


async def run(state, *, path="mem/l0.md", **_):
    # Resolve relative paths from the repo root.
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    if not os.path.exists(path):
        return {"text": "", "tokens": 0, "ok": False}
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        return {
            "text":   text.strip(),
            "tokens": max(1, len(text) // 4),
            "ok":     True,
        }
    except OSError as e:
        return {"text": "", "tokens": 0, "ok": False, "error": str(e)}
