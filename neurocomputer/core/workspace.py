"""
Workspace — Top-level grouping of agents and projects.

Usage:
    from core.workspace import Workspace, WorkspaceConfig

    config = WorkspaceConfig(
        name="My Workspace",
        agents=["neuro", "openclaw"],
        default_agent="neuro",
    )
    workspace = Workspace("my_workspace", config)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.agent import Agent, AgentConfig
from core.agent_configs import AGENT_CONFIGS


@dataclass
class WorkspaceConfig:
    """Minimal config to define a workspace. Add a few lines → new workspace."""
    name: str
    description: str = ""
    color: str = "#8B5CF6"
    emoji: str = "🏢"
    agents: List[str] = field(default_factory=lambda: ["neuro"])
    default_agent: str = "neuro"
    theme: str = "cosmic"


class Workspace:
    """A workspace grouping agents and projects."""

    def __init__(self, workspace_id: str, config: WorkspaceConfig):
        self.workspace_id = workspace_id
        self.config = config
        self._agents: Dict[str, Agent] = {}

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def agent_ids(self) -> List[str]:
        return list(self.config.agents)

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get or create an agent instance (lazy-loaded)."""
        if agent_id not in self.config.agents:
            return None
        if agent_id not in self._agents:
            agent_config = AGENT_CONFIGS.get(agent_id)
            if not agent_config:
                return None
            self._agents[agent_id] = Agent(agent_id, agent_config)
        return self._agents[agent_id]

    def get_default_agent(self) -> Agent:
        """Get the default agent for this workspace."""
        return self.get_agent(self.config.default_agent) or self.get_agent(self.config.agents[0])

    def list_agents(self) -> List[dict]:
        """List agent info for this workspace."""
        result = []
        for aid in self.config.agents:
            ac = AGENT_CONFIGS.get(aid)
            if ac:
                result.append({
                    "id": aid,
                    "name": ac.name,
                    "description": ac.description,
                })
        return result

    def to_dict(self) -> dict:
        return {
            "id": self.workspace_id,
            "name": self.config.name,
            "description": self.config.description,
            "color": self.config.color,
            "emoji": self.config.emoji,
            "agents": self.config.agents,
            "defaultAgent": self.config.default_agent,
        }
