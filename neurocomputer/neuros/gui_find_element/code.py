async def run(state, **kwargs):
    from core.gui_automator.screen_capture import capture_full
    from core.gui_automator.element_detector import ElementDetector
    from core.gui_automator.vision_engine import QwenVLEngine
    
    description = kwargs.get("description")
    force_method = kwargs.get("force_method")
    
    if not description:
        return {"found": False, "error": "Description is required"}
        
    img = capture_full()
    
    # Share a single VLM instance across all GUI neuros to avoid CUDA OOM
    if "gui_vlm" not in state:
        state["gui_vlm"] = QwenVLEngine()
    
    if "gui_detector" not in state:
        state["gui_detector"] = ElementDetector(vlm_engine=state["gui_vlm"])
    detector = state["gui_detector"]
    
    result = await detector.find_element(img, description, force_method=force_method)
    
    if result:
        return {
            "found": True,
            **result
        }
    else:
        return {"found": False}
