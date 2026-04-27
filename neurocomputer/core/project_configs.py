from typing import Dict
from core.project import ProjectConfig

PROJECT_CONFIGS: Dict[str, ProjectConfig] = {
    "default": ProjectConfig(
        name="Main",
        description="Default project",
    ),
}
