from typing import Optional, Tuple
from PIL import Image
from .vision_engine import QwenVLEngine, OCREngine, TemplateMatchEngine
from .pattern_store import PatternStore

class ElementDetector:
    """Unified detector using PatternStore -> TemplateMatch -> OCR -> VLM cascade."""
    
    def __init__(self, vlm_engine: "QwenVLEngine | None" = None):
        self.pattern_store = PatternStore()
        self.template_engine = TemplateMatchEngine()
        self.ocr_engine = OCREngine()
        # Share a single VLM instance across the system to avoid CUDA OOM
        self.vlm_engine = vlm_engine or QwenVLEngine()
        
    async def find_element(self, image: Image.Image, description: str, force_method: Optional[str] = None) -> Optional[dict]:
        """
        Find an element by description.
        Returns dict with keys: x, y, w, h, method, confidence
        """
        # 1. Force Method (if specified)
        if force_method == "vlm":
            coords = await self.vlm_engine.find_element(image, description)
            if coords:
                return self._build_result(coords, "vlm", image, description)
            return None
        elif force_method == "ocr":
            boxes = self.ocr_engine.find_text(image, description)
            if boxes:
                return self._build_result(boxes[0], "ocr", image, description)
            return None
            
        # 2. Check Pattern Store (Fastest)
        pattern = self.pattern_store.get_pattern(description)
        if pattern and pattern['template_path']:
            try:
                template = Image.open(pattern['template_path'])
                coords = self.template_engine.match(image, template)
                if coords:
                    self.pattern_store.record_success(description)
                    return self._build_result(coords, "pattern", image, description)
            except Exception:
                pass
            self.pattern_store.record_failure(description)
            
        # 3. OCR (Medium speed)
        boxes = self.ocr_engine.find_text(image, description)
        if boxes:
            return self._build_result(boxes[0], "ocr", image, description)
            
        # 4. VLM (Slowest but smartest)
        coords = await self.vlm_engine.find_element(image, description)
        if coords:
            return self._build_result(coords, "vlm", image, description)
            
        return None
        
    def _build_result(self, coords: Tuple[int, int, int, int], method: str, image: Image.Image, description: str) -> dict:
        x, y, w, h = coords
        # Save crop as template for future pattern matching
        crop = image.crop((x, y, x+w, y+h))
        self.pattern_store.save_pattern(description, crop, method, coords)
        
        return {
            "x": x, "y": y, "w": w, "h": h,
            "method": method,
            "confidence": 0.9 if method in ("pattern", "template") else 0.8
        }
