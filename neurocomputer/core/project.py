from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ProjectConfig:
    name: str
    description: str = ""
    color: str = "#6366f1"
    emoji: str = "📁"
    neuro_dir: Optional[str] = None  # project-local neuros path; None = use global


@dataclass
class Project:
    project_id: str
    config: ProjectConfig

    @property
    def name(self) -> str:
        return self.config.name

    def to_dict(self) -> dict:
        return {
            "id": self.project_id,
            "name": self.config.name,
            "description": self.config.description,
            "color": self.config.color,
            "emoji": self.config.emoji,
        }
