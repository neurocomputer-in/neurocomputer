"""
Agency registry — add a few lines here to create a new agency.

Each agency groups agents into a specialized workspace.
"""

from typing import Dict
from core.agency import AgencyConfig


AGENCY_CONFIGS: Dict[str, AgencyConfig] = {
    "default": AgencyConfig(
        name="Neuro HQ",
        description="General AI workspace — chat, code, automate",
        color="#8B5CF6",
        emoji="🧠",
        agents=["neuro", "opencode", "nl_dev"],
        default_agent="neuro",
        default_project="default",
    ),
    "upwork": AgencyConfig(
        name="Upwork Agency",
        description="Job hunting, proposals, and freelance automation",
        color="#14B8A6",
        emoji="💼",
        agents=["neuro", "neuroupwork"],
        default_agent="neuroupwork",
    ),
    "webclaw": AgencyConfig(
        name="Web Agency",
        description="Web automation, scraping, and browser tasks",
        color="#F97316",
        emoji="🦀",
        agents=["neuro", "openclaw"],
        default_agent="openclaw",
    ),
}
