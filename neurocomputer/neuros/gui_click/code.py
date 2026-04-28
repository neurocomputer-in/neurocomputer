async def run(state, **kwargs):
    from core.gui_automator.action_executor import ActionExecutor
    
    description = kwargs.get("description")
    x = kwargs.get("x")
    y = kwargs.get("y")
    button_str = kwargs.get("button", "left")
    
    button_map = {"left": 1, "middle": 2, "right": 3}
    button = button_map.get(button_str.lower(), 1)
    
    if "gui_executor" not in state:
        state["gui_executor"] = ActionExecutor()
    executor = state["gui_executor"]
    
    if description and not (x and y):
        # Find element first
        from core.gui_automator.screen_capture import capture_full
        from core.gui_automator.element_detector import ElementDetector
        from core.gui_automator.vision_engine import QwenVLEngine
        
        img = capture_full()
        # Share a single VLM instance to avoid CUDA OOM
        if "gui_vlm" not in state:
            state["gui_vlm"] = QwenVLEngine()
        if "gui_detector" not in state:
            state["gui_detector"] = ElementDetector(vlm_engine=state["gui_vlm"])
        detector = state["gui_detector"]
        
        result = await detector.find_element(img, description)
        if not result:
            return {"success": False, "error": f"Element '{description}' not found"}
            
        # Click center of element
        x = result["x"] + result["w"] // 2
        y = result["y"] + result["h"] // 2
        
    if x is not None and y is not None:
        await executor.click(x, y, button=button)
        return {"success": True, "clicked_at": [x, y]}
        
    return {"success": False, "error": "Must provide description OR both x and y coordinates"}
