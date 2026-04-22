"""Agent-kind base class — a named configuration bundle + session dispatcher.

An agent is a neuro whose `run` dispatches a user message to a
configured default workflow (skill.flow.dag), with:

  - its own `memory_scope` (partitioning `__agent_id` → each agent has
    its own slice of memory graph + flat KV)
  - its own `profile` list (visible neuros, glob-style — future tie-in
    to NeuroFactory profile filter)
  - its own `default_workflow` (advisor, coder, …)
  - its own `policy_override` (optional — a specific
    instruction.policy neuro to pass into the workflow's prompt)

Multi-agent = just have multiple agent-kind neuros in the registry.
Pick one by name when dispatching: `factory.run('agent_coder', ...)`.

Spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/09-kind-formats.md §8
"""
from core.base_neuro import BaseNeuro


class AgentNeuro(BaseNeuro):
    # Overridable from conf.json
    profile: list = ["*"]              # glob names visible to this agent
    default_workflow: str = "advisor"  # which skill.flow.dag to hit
    memory_scope: str = "default"      # sets state["__agent_id"]
    policy_override: str = ""          # optional instruction.policy neuro name
    scope: str = "session"             # one AgentNeuro instance per cid

    async def run(self, state, *,
                  user_text: str = None,
                  user_question: str = None,
                  workflow: str = None,
                  **kw):
        text = user_text or user_question or kw.get("text")
        if not text:
            return {"reply": "", "error": "no user_text/user_question provided"}

        # Memory partitioning — all memory writes/reads under this agent
        # bucket. Overrides whatever was in state previously.
        state["__agent_id"] = self.memory_scope or self.name

        # Workflow selection — kwarg override beats class default.
        chosen_workflow = workflow or self.default_workflow
        if not chosen_workflow:
            return {"reply": "", "error": "no workflow configured on agent"}

        factory = state.get("__factory")
        if factory is None:
            return {"reply": "", "error": "state['__factory'] not set — cannot dispatch"}

        if chosen_workflow not in factory.reg:
            return {"reply": "", "error": f"workflow {chosen_workflow!r} not registered"}

        # Dispatch. The workflow (advisor/coder) takes user_question.
        out = await factory.run(chosen_workflow, state, user_question=text)
        if not isinstance(out, dict):
            out = {}

        result = {
            "reply":         state.get("reply", out.get("reply", "")),
            "agent":         self.name,
            "workflow":      chosen_workflow,
            "memory_scope":  state["__agent_id"],
        }
        for carry in ("provider_used", "model_used", "fallback_from", "error"):
            v = state.get(carry) or out.get(carry)
            if v is not None:
                result[carry] = v
        return result
