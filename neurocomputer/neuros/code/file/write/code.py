"""
Code File Write — writes or appends content to a file.
Supports 'write' (overwrite) and 'append' modes.
"""
from pathlib import Path


async def run(state, *, filepath: str | None = None,
                     path: str | None = None,
                     filename: str | None = None,
                     content: str,
                     mode: str = "write"):
    """
    mode: "write" (default, overwrite) or "append" (add to existing file)
    """
    root = state.get("__project_root") \
           or state.get("__dev", {}).get("project_root")
    if not root:
        return {"reply": "No active project -- create or open one first."}

    # Alias resolution
    if filepath is None:
        filepath = path or filename
    if filepath is None:
        return {"reply": "No file path provided."}

    abs_path = Path(root) / filepath
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "append" and abs_path.exists():
        existing = abs_path.read_text(encoding="utf-8")
        body = existing + "\n" + content + "\n"
    else:
        body = content + "\n"

    abs_path.write_text(body, encoding="utf-8")

    action = "Appended to" if mode == "append" else "Wrote"
    return {
        "reply": f"{action} `{filepath}` ({len(body.splitlines())} lines).",
        "file_path": str(abs_path),
    }
