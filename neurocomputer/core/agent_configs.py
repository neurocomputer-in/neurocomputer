from typing import Dict
from core.agent import AgentConfig


AGENT_CONFIGS: Dict[str, AgentConfig] = {
    "neuro": AgentConfig(
        name="Neuro",
        description="Main general-purpose agent for all tasks",
        router_neuro="smart_router",
        planner_neuro="planner",
        replier_neuro="reply",
        neuro_dirs=[],  # Uses default neuros/
        profile="general"
    ),
    "upwork": AgentConfig(
        name="Upwork",
        description="Specialized agent for Upwork-related tasks",
        router_neuro="smart_router",
        planner_neuro="planner",
        replier_neuro="reply",
        neuro_dirs=[],  # Can add upwork_neuros/ later
        profile="general"
    ),
    "openclaw": AgentConfig(
        name="OpenClaw",
        description="Browser automation and web tasks agent",
        router_neuro="smart_router",
        planner_neuro="planner",
        replier_neuro="reply",
        neuro_dirs=[],
        profile="general"
    ),
    "opencode": AgentConfig(
        name="OpenCode",
        description="Code assistant agent powered by OpenCode",
        router_neuro="smart_router",
        planner_neuro="planner",
        replier_neuro="reply",
        neuro_dirs=[],
        profile="general"
    ),
    "nl_dev": AgentConfig(
        name="NL Dev",
        description="NeuroLang authoring agent — compile NL descriptions into runnable flows",
        router_neuro="smart_router",
        planner_neuro="nl_planner",
        replier_neuro="nl_reply",
        neuro_dirs=[],
        profile="neurolang_dev"
    ),
}
