"""Prompt-kind base classes.

Part of the kind taxonomy generalization — see
docs/superpowers/specs/2026-04-20-neuro-arch/01-core/08-kinds-taxonomy.md

A `prompt.block` is a reusable fragment of prompt text, optionally
template-substituted with kwargs at call time.

A `prompt.composer` joins multiple prompt blocks into a final prompt,
supporting:
  - declared `children` order
  - custom `separator` (default "\n\n")
  - skipping empty blocks

Both are ordinary `BaseNeuro` subclasses — the runtime doesn't know
they're "prompt" kind. The `kind` field on conf.json is metadata for
tooling / IDE / planner.
"""
from core.base_neuro import BaseNeuro


class PromptBlock(BaseNeuro):
    """Leaf prompt fragment.

    Subclass and set `template` to a mustache-like string (`{{var}}`).
    At call time, kwargs substitute into `{{var}}` positions. If a
    `{{var}}` is not in kwargs, falls back to `state[var]` so earlier
    neuros in a flow can populate vars by writing to state.
    """
    template: str = ""

    async def run(self, state, **vars):
        if not self.template:
            return {"text": ""}
        import re

        def replace(match):
            key = match.group(1).strip()
            if key in vars:
                return str(vars[key])
            if key in state:
                return str(state[key])
            return match.group(0)   # leave unresolved {{var}} untouched

        rendered = re.sub(r"\{\{([^}]+)\}\}", replace, self.template)
        return {"text": rendered}


class PromptComposer(BaseNeuro):
    """Composite prompt — concatenates children's `text` outputs.

    - `children`: list of child neuro names (handles injected by factory via `uses`)
    - `separator`: string placed between non-empty block outputs (default: "\n\n")
    - `**vars` passed through to each child unchanged
    """
    children: list = []
    separator: str = "\n\n"

    async def run(self, state, **vars):
        parts = []
        for name in self.children:
            child = getattr(self, name, None)
            if child is None:
                continue
            out = await child.run(state, **vars)
            if not isinstance(out, dict):
                continue
            text = out.get("text", "")
            if text:
                parts.append(text)
        return {"text": self.separator.join(parts)}
