async def run(state, **kwargs):
    from core.gui_automator.workflow_recorder import WorkflowRecorder
    name = kwargs.get("name")
    
    if not name:
        return {"success": False, "error": "Workflow name required"}
        
    if "gui_recorder" not in state:
        state["gui_recorder"] = WorkflowRecorder()
        
    state["gui_recorder"].start_recording(name)
    
    return {"success": True}
