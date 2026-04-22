from pathlib import Path

async def run(state, *, neuro):
    # Access the __dev context in state, create it if it doesn’t exist
    ctx = state.setdefault("__dev", {})
    # Access or create the drafts buffer
    drafts = ctx.setdefault("drafts", {})
    # Define the neuro’s directory path
    root = Path("neuros") / neuro

    # Check if the neuro exists
    if not root.exists():
        return {"reply": f"neuro '{neuro}' not found."}

    # Load each file into the drafts buffer
    for filename in ["neuro.json", "prompt.txt", "code.py"]:
        file_path = root / filename
        if file_path.exists():
            drafts[str(file_path)] = file_path.read_text()
        else:
            drafts[str(file_path)] = ""  # Use empty string if file doesn’t exist

    # Track the current neuro being edited
    ctx["neuro"] = neuro
    return {"reply": f"Loaded '{neuro}' into the buffer. You can now modify it."}