from pathlib import Path

ROOT = Path(r"C:\Users\Adarsh PC\Desktop\emptyWorkspace").expanduser()

# accept either `project_name=` or the alias `name=` so the planner's JSON
# (… "params": {"name": "<proj>"} …) still works.
async def run(state, *,
              project_name: str | None = None,
              **kw):
    """
    • If *project_name* is given → create / switch.
    • Otherwise look for common aliases (`name`, `path`) that
      the planner or a user might have supplied.
    """
    # ---- alias resolution ------------------------------------
    if project_name is None:
        project_name = kw.get("name") or kw.get("path")
    """
    • If project_name is given → create/switch.
    • If project_name is None  → report current selection.
    """

    # Look in the transient state *or* the persistent __dev context
    current = state.get("__project_root") \
             or state.get("__dev", {}).get("project_root")

    # Where am I?
    if project_name is None:
        if current:
            return {
                "reply": f"📂 Current project: **{state['__project_name']}**",
                "project_path": current
            }
        return {"reply": "⚠️  No project selected. Say `create project <name>` or `open project <name>`."}

    # Normalize
    safe = project_name.strip().replace(" ", "_")
    proj_path = ROOT / safe

    # Create if missing
    proj_path.mkdir(parents=True, exist_ok=True)

    # Persist
    # 1️⃣ still expose it for the *current* flow …
    state["__project_root"] = str(proj_path)
    state["__project_name"] = safe
    # 2️⃣ …and also cache it in the per-conversation context
    ctx = state.setdefault("__dev", {})
    ctx["project_root"] = str(proj_path)
    ctx["project_name"] = safe

    return {
        "reply": f"✅ Project **{safe}** ready at `{proj_path}`",
        "project_path": str(proj_path)
    }
