from pathlib import Path
from datetime import datetime, timezone

async def run(state, *, filepath: str | None = None,
                     path: str | None = None,
                     filename: str | None = None,
                     content: str):
    # fall back to the project path cached by code_project_manager
    root = state.get("__project_root") \
           or state.get("__dev", {}).get("project_root")
    if not root:
        return {"reply": "⚠️  No active project – create or open one first."}

    # Alias resolution: accept 'path' or 'filename' if 'filepath' is not provided
    if filepath is None:
        filepath = path or filename
    if filepath is None:
        return {"reply": "⚠️  No file path provided."}

    abs_path = Path(root) / filepath
    abs_path.parent.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    body = f"[{ts}]\n{content}\n"
    abs_path.write_text(body, encoding="utf-8")

    return {
        "reply": f"📝 Wrote `{filepath}` ({len(body.splitlines())} lines).",
        "file_path": str(abs_path)
    }
