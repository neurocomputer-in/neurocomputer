async def run(state):
    """List all available neuros and return a formatted reply."""
    cid = state.get("__cid")
    neuros = state["__factory"].describe(cid)

    if not neuros:
        return {"reply": "No skills available at the moment."}

    lines = []
    for n in neuros:
        lines.append(f"- **{n['name']}**: {n['desc']}")

    reply = "Here are my available skills:\n\n" + "\n".join(lines)
    return {"reply": reply}
