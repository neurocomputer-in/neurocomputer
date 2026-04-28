async def run(state, **kwargs):
    from core.gui_automator.screen_capture import capture_full
    from core.gui_automator.vision_engine import QwenVLEngine, OCREngine
    
    question = kwargs.get("question")
    img = capture_full()
    
    # Run OCR (fast)
    ocr = OCREngine()
    text_content = ocr.extract_text(img)
    
    # Run VLM
    if "gui_vlm" not in state:
        state["gui_vlm"] = QwenVLEngine()
    vlm = state["gui_vlm"]
    
    prompt = question if question else "Describe the current screen and its main interactive elements in detail."
    description = await vlm.describe_screen(img, prompt=prompt)
    
    return {
        "description": description,
        "text_content": text_content.strip()
    }
