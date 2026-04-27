from typing import Any, Dict
from core.agent_manager import agent_manager
from core.agent_configs import AGENT_CONFIGS
from core.agency_configs import AGENCY_CONFIGS
from core.defaults import MAIN_AGENCY_ID


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    agency_id = kwargs.get("agency_id") or MAIN_AGENCY_ID
    agency_cfg = AGENCY_CONFIGS.get(agency_id)
    agent_ids = agency_cfg.agents if agency_cfg else list(AGENT_CONFIGS.keys())
    agents = []
    for aid in agent_ids:
        cfg = AGENT_CONFIGS.get(aid)
        agents.append({
            "id": aid,
            "name": cfg.name if cfg else aid,
            "agency_id": agency_id,
        })
    return {"agents": agents}
