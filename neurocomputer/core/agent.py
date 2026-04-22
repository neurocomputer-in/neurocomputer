import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.brain import Brain
from core.conversation import Conversation


@dataclass
class AgentConfig:
    """Configuration for an agent instance."""
    name: str = "Agent"
    description: str = "General purpose agent"
    router_neuro: str = "smart_router"
    planner_neuro: str = "planner"
    replier_neuro: str = "reply"
    neuro_dirs: List[str] = field(default_factory=list)  # Additional neuro directories
    profile: str = "general"  # Which profile to use


class Agent:
    """Base Agent class - wraps Brain for multi-agent support."""

    def __init__(self, agent_id: str, config: AgentConfig):
        self.agent_id = agent_id
        self.config = config
        self.brain = Brain()  # Each agent has its own Brain instance
        self.is_running = False

    async def handle_message(self, cid: str, message: str, agent_id: str = None) -> str:
        """Handle message for this agent."""
        self.is_running = True
        try:
            return await self.brain.handle(cid, message, agent_id=agent_id or self.agent_id)
        finally:
            pass  # Keep is_running true while agent is active

    def get_conversation_history(self, cid: str) -> List[dict]:
        """Get conversation history for this agent."""
        conv = self.brain.convs.get(cid)
        if conv:
            return conv.history()
        return Conversation(cid).history()

    def get_status(self) -> dict:
        """Get agent status."""
        return {
            "agent_id": self.agent_id,
            "name": self.config.name,
            "description": self.config.description,
            "is_running": self.is_running,
        }
