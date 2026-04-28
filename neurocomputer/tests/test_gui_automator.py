import os
import pytest
from PIL import Image
import numpy as np

from core.gui_automator.screen_capture import capture_full, capture_region
from core.gui_automator.vision_engine import OCREngine, TemplateMatchEngine
from core.gui_automator.pattern_store import PatternStore
from core.gui_automator.workflow_recorder import WorkflowRecorder

def create_test_image(text="Hello World"):
    # Create white image
    img = Image.new('RGB', (400, 200), color='white')
    return img

def test_screen_capture():
    # Only test if a display is available
    if 'DISPLAY' in os.environ:
        img = capture_full()
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0
        
        region = capture_region(0, 0, 100, 100)
        assert isinstance(region, Image.Image)
        assert region.width == 100
        assert region.height == 100

def test_pattern_store(tmp_path):
    db_path = tmp_path / "test.db"
    template_dir = tmp_path / "templates"
    
    store = PatternStore(db_path=str(db_path), template_dir=str(template_dir))
    
    # Empty get
    assert store.get_pattern("Submit Button") is None
    
    # Save pattern
    img = create_test_image()
    store.save_pattern("Submit Button", img, "ocr", (10, 10, 100, 50))
    
    # Get pattern
    pattern = store.get_pattern("Submit Button")
    assert pattern is not None
    assert pattern["method"] == "ocr"
    assert "last_coords" in pattern
    
    # Record success
    store.record_success("Submit Button")
    pattern = store.get_pattern("Submit Button")
    assert pattern["success_count"] == 2 # 1 from insert + 1 from success
    
def test_workflow_recorder(tmp_path):
    dir_path = tmp_path / "workflows"
    recorder = WorkflowRecorder(workflows_dir=str(dir_path))
    
    recorder.start_recording("test_flow")
    recorder.record_step("click", "Submit", [10, 20], "ocr")
    recorder.record_step("type", "Test", [], "vlm", text="Hello")
    
    path = recorder.save_workflow()
    assert os.path.exists(path)
    
    import json
    with open(path, "r") as f:
        data = json.load(f)
        
    assert data["name"] == "test_flow"
    assert len(data["steps"]) == 2
    assert data["steps"][0]["action"] == "click"
    assert data["steps"][1]["text"] == "Hello"
