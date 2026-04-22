"""
Workspace registry — add a few lines here to create a new workspace.

Each workspace groups agents into a specialized environment.
"""

from typing import Dict
from core.workspace import WorkspaceConfig


WORKSPACE_CONFIGS: Dict[str, WorkspaceConfig] = {
    "default": WorkspaceConfig(
        name="Main Workspace",
        description="General AI workspace — chat, code, automate",
        color="#8B5CF6",
        emoji="🧠",
        agents=["neuro", "opencode"],
        default_agent="neuro",
        theme="cosmic",
    ),
    "upwork": WorkspaceConfig(
        name="Upwork Workspace",
        description="Job hunting, proposals, and freelance automation",
        color="#14B8A6",
        emoji="💼",
        agents=["neuro", "neuroupwork"],
        default_agent="neuroupwork",
        theme="ocean",
    ),
    "webclaw": WorkspaceConfig(
        name="Web Workspace",
        description="Web automation, scraping, and browser tasks",
        color="#F97316",
        emoji="🦀",
        agents=["neuro", "openclaw"],
        default_agent="openclaw",
        theme="sunset",
    ),
}
