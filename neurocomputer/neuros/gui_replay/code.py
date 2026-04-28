import json
import os

async def run(state, **kwargs):
    workflow_name = kwargs.get("workflow_name")
    if not workflow_name:
        return {"success": False, "error": "workflow_name required"}
        
    filepath = os.path.join("workflows", f"{workflow_name}.json")
    if not os.path.exists(filepath):
        return {"success": False, "error": f"Workflow {workflow_name} not found"}
        
    with open(filepath, "r") as f:
        workflow = json.load(f)
        
    factory = state.get("__factory")
    if not factory:
        return {"success": False, "error": "Factory required for replay"}
        
    steps_completed = 0
    for step in workflow.get("steps", []):
        action = step.get("action")
        target = step.get("target")
        coords = step.get("coords")
        
        if action == "click":
            # Using gui_click neuro
            args = {}
            if coords:
                args["x"] = coords[0]
                args["y"] = coords[1]
            elif target:
                args["description"] = target
            
            res = await factory.run("gui_click", state, **args)
            if not res.get("success"):
                return {"success": False, "error": f"Failed step: {step}", "steps_completed": steps_completed}
        elif action == "type":
            text = step.get("text")
            res = await factory.run("gui_type", state, text=text, description=target)
            if not res.get("success"):
                return {"success": False, "error": f"Failed step: {step}", "steps_completed": steps_completed}
                
        steps_completed += 1
        
    return {"success": True, "steps_completed": steps_completed}
