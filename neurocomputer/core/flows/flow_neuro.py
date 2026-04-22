"""FlowNeuro — a composite neuro that orchestrates children.

Per spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/02-flow-as-neuro.md

Abstract base. Concrete flows (SequentialFlow, ParallelFlow, DagFlow,
user subclasses) implement `run`.
"""
from core.base_neuro import BaseNeuro


class FlowNeuro(BaseNeuro):
    uses: list = []
    children: list = []
    replan_policy: str = "inherit"

    # Phase A override: BaseNeuro still carries the legacy fn-wrapper ctor;
    # until Phase C.1 makes it abstract, give FlowNeuro its own no-arg init.
    def __init__(self, name: str = "", desc: str = "",
                 inputs=None, outputs=None):
        self.name = name
        self.desc = desc
        self.inputs = inputs or []
        self.outputs = outputs or []

    async def run(self, state, **kw):
        raise NotImplementedError

    async def before_child(self, name, params, state):
        return None

    async def after_child(self, name, out, state):
        return None

    async def on_child_error(self, name, exc, state):
        return "replan"
