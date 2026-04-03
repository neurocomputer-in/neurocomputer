from pathlib import Path
import json
async def run(state, *, text):
    llm = state["__llm"]
    system = state["__prompt"]
    conv = state.get("__conv")
    hist = "\n".join(f"{e['sender']}: {e['text']}" for e in conv.history()) if conv else ""
    ctx = state.setdefault("__dev", {})
    drafts = ctx.get("drafts", {})
    neuro = ctx.get("neuro")

    if not neuro:
        return {"reply": "Please load or create a neuro first (e.g., `/load <neuro>` or `/dev_new <neuro>`)."}

    # Check if drafts are empty (new neuro) or have content (modification)
    if not any(drafts.values()):  # New neuro
        prompt = (
            f"User is creating a new neuro '{neuro}'.\n"
            f"User says: {text}\n\n"
            "Generate initial content for the neuro files. Respond with a JSON object: "
            "{\"neuro.json\": \"initial JSON\", \"prompt.txt\": \"initial prompt\", \"code.py\": \"initial code\"}"
        )
    else:  # Modify existing drafts
        prompt = (
            f"User wants to modify the neuro '{neuro}'.\n"
            f"Current drafts:\n"
            f"neuro.json: {drafts.get(str(Path('neuros') / neuro / 'neuro.json'), '')}\n"
            f"prompt.txt: {drafts.get(str(Path('neuros') / neuro / 'prompt.txt'), '')}\n"
            f"code.py: {drafts.get(str(Path('neuros') / neuro / 'code.py'), '')}\n\n"
            f"User says: {text}\n\n"
            "Suggest updates to the files. Respond with a JSON object: "
            "{\"neuro.json\": \"new content\", \"prompt.txt\": \"new content\", \"code.py\": \"new content\"}"
        )

    updates = json.loads(llm.generate_json(prompt, system))
    for file, content in updates.items():
        if content:
            drafts[str(Path("neuros") / neuro / file)] = content

    draft_text = "\n\n".join(
        f"**{k.split('/')[-1]}**:\n```\n{v}\n```"
        for k, v in drafts.items()
        if k.startswith(str(Path("neuros") / neuro))
    )
    return {"reply": f"Updated draft for '{neuro}':\n{draft_text}\nSay `/save` when ready."}