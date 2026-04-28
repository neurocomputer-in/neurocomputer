async def run(state, **kwargs):
    from core.gui_automator.action_executor import ActionExecutor
    
    text = kwargs.get("text")
    description = kwargs.get("description")
    
    if not text:
        return {"success": False, "error": "Text is required"}
        
    if "gui_executor" not in state:
        state["gui_executor"] = ActionExecutor()
    executor = state["gui_executor"]
    
    if description:
        # Click element first
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
        if result:
            x = result["x"] + result["w"] // 2
            y = result["y"] + result["h"] // 2
            await executor.click(x, y)
        else:
            return {"success": False, "error": f"Element '{description}' not found"}
            
    await executor.type_text(text)
    return {"success": True}
