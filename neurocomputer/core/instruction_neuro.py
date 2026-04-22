"""Instruction-kind base classes.

An `instruction.rule` is a single named behavior constraint (e.g.
"always use markdown", "be concise", "never reveal credentials").
Structured — carries category + priority, not just text — so planners
and tools can enforce / filter / merge.

An `instruction.policy` is a composite bundle of rules, optionally
filtered by category + ordered by priority.

Rules and policies are often consumed by `prompt.*` neuros (injected
as text into system prompts) but can also be consulted programmatically
by planners, critics, and the dev-agent.

Spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/09-kind-formats.md §7
"""
from core.base_neuro import BaseNeuro


class InstructionRule(BaseNeuro):
    """Leaf policy text. Subclass and set `template`, `category`, `priority`.

    Output shape: {text, category, priority}
    """
    template: str = ""
    category: str = "general"
    priority: int = 50  # higher = applied first / weighted more

    async def run(self, state, **kw):
        # Allow template vars just like prompt.block.
        import re

        def replace(match):
            key = match.group(1).strip()
            if key in kw:
                return str(kw[key])
            if key in state:
                return str(state[key])
            return match.group(0)

        text = re.sub(r"\{\{([^}]+)\}\}", replace, self.template) if self.template else ""
        return {
            "text":     text,
            "category": self.category,
            "priority": self.priority,
        }


class InstructionTone(InstructionRule):
    """Sub-kind emphasizing voice / personality vs a hard rule."""
    voice: str = "neutral"

    async def run(self, state, **kw):
        out = await super().run(state, **kw)
        out["voice"] = self.voice
        return out


class InstructionPolicy(BaseNeuro):
    """Composite: gathers child rules, optionally filters + orders.

    `children`: list of rule-neuro names (dep-injected as `self.<name>`)
    `filter_category`: if set, only emit rules matching this category
    `min_priority`: drop rules below this priority (default: 0 = keep all)
    """
    children: list = []
    filter_category: str = ""
    min_priority: int = 0

    async def run(self, state, **kw):
        rules = []
        for name in self.children:
            child = getattr(self, name, None)
            if child is None:
                continue
            out = await child.run(state, **kw)
            if not isinstance(out, dict):
                continue
            if self.filter_category and out.get("category") != self.filter_category:
                continue
            if out.get("priority", 0) < self.min_priority:
                continue
            rules.append(out)

        # Sort by priority desc; stable for same-priority rules.
        rules.sort(key=lambda r: -r.get("priority", 0))
        return {
            "rules": rules,
            "text":  "\n".join(r.get("text", "") for r in rules if r.get("text")),
            "count": len(rules),
        }
