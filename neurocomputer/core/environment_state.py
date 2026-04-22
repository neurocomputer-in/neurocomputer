"""
Environment state tracker for ReAct-style reasoning.

Maintains:
- Recent command/action outputs (success/failure)
- Observation history for current task
- Context for intelligent replanning
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class Observation:
    """Single observation from an action."""
    action: str
    neuro: str
    result: str
    success: bool
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class EnvironmentState:
    """Tracks environment state for a conversation."""
    observations: List[Observation] = field(default_factory=list)
    current_goal: Optional[str] = None
    working_directory: Optional[str] = None
    active_project: Optional[str] = None
    last_error: Optional[str] = None
    replan_count: int = 0
    
    def add_observation(self, action: str, neuro: str, result: str, success: bool, **metadata):
        """Record an observation from an action."""
        self.observations.append(Observation(
            action=action,
            neuro=neuro,
            result=result[:500] if result else "",  # Truncate long results
            success=success,
            metadata=metadata
        ))
        if not success:
            self.last_error = result[:200] if result else "Unknown error"
    
    def get_recent_observations(self, n: int = 5) -> List[Observation]:
        """Get the n most recent observations."""
        return self.observations[-n:]
    
    def format_for_prompt(self) -> str:
        """Format recent observations for LLM context."""
        if not self.observations:
            return "No previous actions in this session."
        
        lines = ["## Recent Actions:"]
        for obs in self.get_recent_observations():
            status = "✓ SUCCESS" if obs.success else "✗ FAILED"
            result_preview = obs.result[:100] + "..." if len(obs.result) > 100 else obs.result
            lines.append(f"- [{status}] {obs.neuro}: {result_preview}")
        
        if self.active_project:
            lines.append(f"\n**Active Project**: {self.active_project}")
        if self.last_error:
            lines.append(f"\n**Last Error**: {self.last_error}")
            
        return "\n".join(lines)
    
    def needs_replan(self) -> bool:
        """Check if last action failed and might need replanning."""
        if not self.observations:
            return False
        return not self.observations[-1].success
    
    def get_failure_context(self) -> Optional[Dict[str, Any]]:
        """Get context about the last failure for replanning."""
        if not self.observations or self.observations[-1].success:
            return None
        
        last = self.observations[-1]
        return {
            "failed_action": last.action,
            "failed_neuro": last.neuro,
            "error": last.result,
            "timestamp": last.timestamp.isoformat(),
            "replan_count": self.replan_count
        }
    
    def clear_for_new_goal(self, goal: str):
        """Reset state for a new goal while keeping some history."""
        self.current_goal = goal
        self.last_error = None
        self.replan_count = 0
        # Keep last 3 observations for context continuity
        self.observations = self.observations[-3:] if len(self.observations) > 3 else self.observations
