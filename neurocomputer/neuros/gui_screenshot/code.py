import os
import time

async def run(state, **kwargs):
    from core.gui_automator.screen_capture import capture_full, capture_region
    
    region = kwargs.get("region")
    
    if region and len(region) == 4:
        x, y, w, h = region
        img = capture_region(x, y, w, h)
    else:
        img = capture_full()
        
    os.makedirs("gui_screenshots", exist_ok=True)
    filepath = os.path.join("gui_screenshots", f"capture_{int(time.time())}.png")
    img.save(filepath)
    
    return {"image_path": filepath}
