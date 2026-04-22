"""ide_assistant — natural-language neuro editor.

LLM-driven: takes a plain-English request, optionally with a target
neuro as context, proposes changes, validates via dev_pipeline, saves
atomically. Built-in retry-with-repair: on validation error, the error
envelope is fed back to the LLM for one repair pass.

Not a full tool_loop; just a focused propose-validate-save flow.
Good enough for v1 "change X in neuro Y" style edits.
"""
import json
import pathlib
import re
from core.base_neuro import BaseNeuro


_SYSTEM_PROMPT = """\
You are the neurocomputer IDE editor. The user will ask you to add /
edit / remove neuros — small agent-composable units stored as folders
with conf.json + code.py (+ optional prompt.txt).

Rules you MUST follow:
- Neuro names: lowercase snake_case (e.g. 'my_neuron'), starts with a letter.
- conf.json MUST have {"name": ..., "description": ...}. For pure-conf
  flow neuros (kind=skill.flow.sequential / prompt.composer / etc),
  `children`, `uses`, and kind-specific fields are set there.
- code.py MUST define either `async def run(state, **kw)` at module
  level OR a class subclassing `BaseNeuro` with `async def run(self,
  state, **kw)`.
- NEVER use os.system, subprocess.*, eval, exec. Reject these if
  requested — they're blocked by the save pipeline.
- Prefer composition. If the user wants to add behavior, add/wire a
  neuro rather than stuff Python into an existing one.

Output format: respond with EXACTLY one valid JSON object:

{
  "neuro_name": "<target folder name>",
  "action":      "create" | "modify" | "delete" | "no_op",
  "conf":        <JSON object, required for create/modify>,
  "code":        "<python code string, required for create/modify>",
  "prompt":      "<optional prompt.txt string>",
  "explanation": "<one-paragraph summary of what u did and why>"
}

No prose before/after. If modify, include the FULL new conf + code
(not a diff). If no_op, just explain why.
"""


_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


class IdeAssistant(BaseNeuro):
    uses = ["inference", "dev_pipeline"]

    async def run(self, state, *,
                  user_request: str,
                  target_neuro: str = None,
                  max_retries: int = 2,
                  **_):
        if not user_request or not user_request.strip():
            return {"ok": False, "reply": "no request given",
                    "action": "no_op", "attempts": 0}

        # Build context — fetch target's current state if specified
        context_block = ""
        if target_neuro:
            target_ctx = _read_neuro_source(state, target_neuro)
            if target_ctx:
                context_block = (
                    f"\n\n### current state of `{target_neuro}`:\n\n"
                    f"conf.json:\n```json\n{target_ctx['conf']}\n```\n\n"
                    f"code.py:\n```python\n{target_ctx['code']}\n```"
                )
                if target_ctx.get("prompt"):
                    context_block += (
                        f"\n\nprompt.txt:\n```\n{target_ctx['prompt']}\n```"
                    )
            else:
                context_block = f"\n\n(target neuro `{target_neuro}` does not exist yet — create it)"

        user_msg = f"Request: {user_request}{context_block}"

        attempt = 0
        last_errors = []
        last_parsed = None

        while attempt <= max_retries:
            attempt += 1

            messages = [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ]
            if last_errors:
                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous attempt failed validation:\n"
                        + "\n".join(f"  - {e}" for e in last_errors)
                        + "\n\nFix the errors and respond again with a valid JSON object."
                    ),
                })

            out = await self.inference.run(state, messages=messages)
            raw = out.get("content", "") if isinstance(out, dict) else ""
            parsed = _parse_proposal(raw)

            if not parsed:
                last_errors = ["response was not valid JSON matching the schema"]
                last_parsed = None
                continue

            last_parsed = parsed
            action = parsed.get("action") or "no_op"

            if action == "no_op":
                return {
                    "ok":          True,
                    "reply":       parsed.get("explanation",
                                              "no action needed"),
                    "action":      "no_op",
                    "attempts":    attempt,
                }

            if action == "delete":
                # Deletion isn't implemented in dev_pipeline v1.
                return {
                    "ok":       False,
                    "reply":    "delete not yet supported — create/modify only",
                    "action":   "failed",
                    "attempts": attempt,
                }

            # create / modify path
            name = parsed.get("neuro_name")
            conf = parsed.get("conf")
            code = parsed.get("code")
            prompt_txt = parsed.get("prompt")
            if not name or conf is None or code is None:
                last_errors = [
                    "neuro_name, conf, and code are all required for "
                    "create/modify actions"
                ]
                continue

            # Fall through to dev_pipeline save — it validates +
            # schema/syntax gates + atomic writes + snapshots.
            save_result = await self.dev_pipeline.run(
                state,
                op="save",
                neuro_name=name,
                conf=conf,
                code=code,
                prompt=prompt_txt,
                author="ai",
            )

            if save_result.get("ok"):
                return {
                    "ok":          True,
                    "reply":       parsed.get("explanation",
                                              f"{action}d {name}"),
                    "action":      "created" if action == "create" else "modified",
                    "neuro_name": name,
                    "snapshot":    save_result.get("snapshot"),
                    "attempts":    attempt,
                }

            last_errors = save_result.get("errors", ["unknown save error"])

        # Exhausted retries
        return {
            "ok":          False,
            "reply":       (last_parsed.get("explanation", "")
                           if last_parsed else "")
                           + f"\n\nfailed after {attempt} attempt(s)",
            "action":      "failed",
            "neuro_name": (last_parsed or {}).get("neuro_name"),
            "errors":      last_errors,
            "attempts":    attempt,
        }


# ── helpers ─────────────────────────────────────────────────────────

def _read_neuro_source(state, name: str):
    """Locate the on-disk folder for a registered neuro.

    Prefer the factory entry's tracked `conf_path.parent` so nested
    taxonomy folders (e.g. neuros/agent/advisor/...) work. Fall back
    to flat neuros/<name> for neuros registered without a path.
    """
    factory = state.get("__factory")
    folder = None
    if factory is not None and name in getattr(factory, "reg", {}):
        entry = factory.reg[name]
        path = getattr(entry, "conf_path", None)
        if path is not None:
            folder = path.parent
    if folder is None and factory is not None and hasattr(factory, "dir"):
        folder = pathlib.Path(factory.dir) / name
    if folder is None:
        folder = pathlib.Path("neuros") / name
    if not folder.exists():
        return None
    out = {}
    for fname, key in (("conf.json", "conf"),
                       ("code.py",   "code"),
                       ("prompt.txt","prompt")):
        p = folder / fname
        if p.exists():
            try:
                out[key] = p.read_text(encoding="utf-8")
            except OSError:
                out[key] = ""
    return out if "conf" in out or "code" in out else None


def _parse_proposal(raw: str):
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-z]*\n?", "", s)
        s = re.sub(r"```$", "", s).strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, ValueError):
        pass
    m = _JSON_BLOCK.search(s)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, ValueError):
            pass
    return None
