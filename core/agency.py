"""
Agency — Top-level grouping of agents and projects.

Usage:
    from core.agency import Agency, AgencyConfig

    config = AgencyConfig(
        name="My Agency",
        agents=["neuro", "openclaw"],
        default_agent="neuro",
    )
    agency = Agency("my_agency", config)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from core.agent import Agent, AgentConfig
from core.agent_configs import AGENT_CONFIGS


@dataclass
class AgencyConfig:
    """Minimal config to define an agency. Add a few lines → new agency."""
    name: str
    description: str = ""
    color: str = "#8B5CF6"
    emoji: str = "🏢"
    agents: List[str] = field(default_factory=lambda: ["neuro"])
    default_agent: str = "neuro"


class Agency:
    """A workspace grouping agents and projects."""

    def __init__(self, agency_id: str, config: AgencyConfig):
        self.agency_id = agency_id
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
        """Get the default agent for this agency."""
        return self.get_agent(self.config.default_agent) or self.get_agent(self.config.agents[0])

    def list_agents(self) -> List[dict]:
        """List agent info for this agency."""
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
            "id": self.agency_id,
            "name": self.config.name,
            "description": self.config.description,
            "color": self.config.color,
            "emoji": self.config.emoji,
            "agents": self.config.agents,
            "defaultAgent": self.config.default_agent,
        }
