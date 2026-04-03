import uuid
import asyncio
from typing import Dict, List, Optional

from core.agent import Agent, AgentConfig
from core.agent_configs import AGENT_CONFIGS


class AgentManager:
    """Singleton managing all running agents."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.agents: Dict[str, Agent] = {}
        self.active_agent_id: Optional[str] = None
        self._event_queue = asyncio.Queue()
        self._subscribers: Dict[str, asyncio.Queue] = {}

    def create_agent(self, agent_type: str, agent_id: str = None) -> Agent:
        """Create a new agent by type, or return existing if already created."""
        # Check if we already have an agent of this type
        existing = self.get_agent_by_type(agent_type)
        if existing:
            return existing

        config = AGENT_CONFIGS.get(agent_type)
        if not config:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_CONFIGS.keys())}")

        agent_id = agent_id or f"{agent_type}_{uuid.uuid4().hex[:8]}"
        agent = Agent(agent_id, config)
        self.agents[agent_id] = agent

        # If this is the first agent, make it active
        if self.active_agent_id is None:
            self.active_agent_id = agent_id

        return agent

    def get_agent_by_type(self, agent_type: str) -> Optional[Agent]:
        """Get an existing agent by type.

        Matches by:
        1. Config key (neuro, upwork, windsurf, openclaw)
        2. Config name (Neuro, Upwork, Windsurf, OpenClaw)
        3. Partial substring match (wind -> windsurf, open -> openclaw)
        """
        agent_type_lower = agent_type.lower().strip()

        for agent in self.agents.values():
            config_name_lower = agent.config.name.lower()

            # Exact match by config key (e.g., "neuro", "upwork")
            for key, config in AGENT_CONFIGS.items():
                if key.lower() == agent_type_lower and agent.config.name == config.name:
                    return agent

            # Exact match by config name (e.g., "Neuro", "Upwork")
            if config_name_lower == agent_type_lower:
                return agent

            # Partial substring match (e.g., "wind" matches "Windsurf")
            if agent_type_lower in config_name_lower or config_name_lower in agent_type_lower:
                return agent

        return None

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        return self.agents.get(agent_id)

    def switch_active_agent(self, agent_id: str) -> bool:
        """Switch the active agent for frontend."""
        if agent_id in self.agents:
            self.active_agent_id = agent_id
            return True
        return False

    def switch_to_agent_type(self, agent_type: str) -> Agent:
        """Switch to an agent of the specified type, creating if necessary."""
        # First check if we already have one
        existing = self.get_agent_by_type(agent_type)
        if existing:
            self.active_agent_id = existing.agent_id
            return existing

        # Create new agent of this type
        return self.create_agent(agent_type)

    def get_active_agent(self) -> Optional[Agent]:
        """Get the currently active agent."""
        if self.active_agent_id:
            return self.agents.get(self.active_agent_id)
        return None

    def ensure_default_agent(self) -> Agent:
        """Ensure a default agent exists and is active."""
        if not self.active_agent_id or self.active_agent_id not in self.agents:
            agent = self.create_agent("neuro")
            self.active_agent_id = agent.agent_id
            return agent
        return self.get_active_agent()

    def list_agents(self) -> List[dict]:
        """List all running agents."""
        return [
            {
                "agent_id": a.agent_id,
                "name": a.config.name,
                "description": a.config.description,
                "is_active": a.agent_id == self.active_agent_id
            }
            for a in self.agents.values()
        ]

    def list_agent_types(self) -> List[dict]:
        """List available agent types."""
        return [
            {"type": t, "name": c.name, "description": c.description}
            for t, c in AGENT_CONFIGS.items()
        ]

    async def publish_event(self, topic: str, data: dict):
        """Publish an event to all subscribers."""
        event = {"topic": topic, "data": data}
        await self._event_queue.put(event)
        for q in self._subscribers.values():
            await q.put(event)

    def subscribe(self, subscriber_id: str) -> asyncio.Queue:
        """Subscribe to agent events."""
        q = asyncio.Queue()
        self._subscribers[subscriber_id] = q
        return q

    def unsubscribe(self, subscriber_id: str):
        """Unsubscribe from agent events."""
        self._subscribers.pop(subscriber_id, None)


# Global singleton instance
agent_manager = AgentManager()
