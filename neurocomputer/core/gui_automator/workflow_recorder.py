import json
import os
import time

class WorkflowRecorder:
    """Records sequence of GUI actions into replayable workflows."""
    
    def __init__(self, workflows_dir="workflows"):
        self.workflows_dir = workflows_dir
        os.makedirs(self.workflows_dir, exist_ok=True)
        self.current_workflow = None
        self.steps = []
        
    def start_recording(self, name: str):
        self.current_workflow = name
        self.steps = []
        
    def record_step(self, action: str, target: str, coords: list, method: str, **kwargs):
        if not self.current_workflow:
            return
            
        step = {
            "action": action,
            "target": target,
            "coords": coords,
            "method": method,
            "timestamp": time.time(),
            **kwargs
        }
        self.steps.append(step)
        
    def save_workflow(self, name: str = None) -> str:
        name = name or self.current_workflow
        if not name:
            raise ValueError("No workflow name specified")
            
        workflow = {
            "name": name,
            "recorded_at": time.time(),
            "steps": self.steps
        }
        
        filepath = os.path.join(self.workflows_dir, f"{name}.json")
        with open(filepath, "w") as f:
            json.dump(workflow, f, indent=2)
            
        self.current_workflow = None
        self.steps = []
        return filepath
