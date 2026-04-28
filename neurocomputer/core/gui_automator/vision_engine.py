import os
import io
import asyncio
from typing import Dict, List, Tuple, Optional
import base64

from PIL import Image

class QwenVLEngine:
    """Uses Qwen2-VL to describe screen and find elements."""
    
    def __init__(self, model_id="Qwen/Qwen2-VL-2B-Instruct"):
        self.model_id = model_id
        self.model = None
        self.processor = None
        
    def _load(self):
        if self.model is None:
            # Lazy import
            from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
            import torch
            
            self.model = Qwen2VLForConditionalGeneration.from_pretrained(
                self.model_id, torch_dtype=torch.float16, device_map="auto"
            )
            self.processor = AutoProcessor.from_pretrained(self.model_id)

    async def describe_screen(self, image: Image.Image, prompt: str = "Describe the UI and main interactive elements.") -> str:
        self._load()
        from qwen_vl_utils import process_vision_info
        
        messages = [
            {"role": "system", "content": "You are an expert GUI automation agent."},
            {"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt}
            ]}
        ]
        
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = self.processor(
            text=[text], images=image_inputs, videos=video_inputs, padding=True, return_tensors="pt"
        ).to(self.model.device)
        
        generated_ids = self.model.generate(**inputs, max_new_tokens=512)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        return self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

    async def find_element(self, image: Image.Image, description: str) -> Optional[Tuple[int, int, int, int]]:
        """
        Ask Qwen2-VL for the bounding box of an element.
        Returns (x, y, w, h) in pixels, or None if not found.
        """
        self._load()
        from qwen_vl_utils import process_vision_info
        import re
        
        # Qwen-VL can output coordinates in format <box>(ymin,xmin),(ymax,xmax)</box>
        prompt = f"Find the bounding box of '{description}'. Output the coordinates in the format <box>(ymin,xmin),(ymax,xmax)</box> where values are normalized from 0 to 1000."
        
        messages = [
            {"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt}
            ]}
        ]
        
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, _ = process_vision_info(messages)
        inputs = self.processor(
            text=[text], images=image_inputs, padding=True, return_tensors="pt"
        ).to(self.model.device)
        
        generated_ids = self.model.generate(**inputs, max_new_tokens=100)
        generated_ids_trimmed = [
            out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        
        output_str = self.processor.batch_decode(generated_ids_trimmed, skip_special_tokens=False, clean_up_tokenization_spaces=False)[0]
        
        # Parse output for bounding box
        box_match = re.search(r'<box>\((\d+),(\d+)\),\((\d+),(\d+)\)</box>', output_str)
        if box_match:
            ymin, xmin, ymax, xmax = map(int, box_match.groups())
            # Convert normalied 0-1000 coordinates back to original pixel dims
            img_w, img_h = image.size
            real_xmin = int((xmin / 1000.0) * img_w)
            real_ymin = int((ymin / 1000.0) * img_h)
            real_xmax = int((xmax / 1000.0) * img_w)
            real_ymax = int((ymax / 1000.0) * img_h)
            
            return (real_xmin, real_ymin, real_xmax - real_xmin, real_ymax - real_ymin)
            
        return None

class OCREngine:
    """Uses Tesseract to find text elements on screen."""
    
    def __init__(self):
        pass

    def extract_text(self, image: Image.Image) -> str:
        import pytesseract
        return pytesseract.image_to_string(image)
        
    def find_text(self, image: Image.Image, target_text: str, case_sensitive: bool = False) -> List[Tuple[int, int, int, int]]:
        """Returns list of boxes (x,y,w,h) where target text is found."""
        import pytesseract
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        
        boxes = []
        target = target_text if case_sensitive else target_text.lower()
        
        for i in range(len(data['text'])):
            word = data['text'][i]
            if not word.strip():
                continue
                
            compare_word = word if case_sensitive else word.lower()
            if target in compare_word:
                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]
                boxes.append((x, y, w, h))
                
        return boxes

class TemplateMatchEngine:
    """Uses OpenCV to find template images."""
    
    def __init__(self):
        pass
        
    def match(self, image: Image.Image, template: Image.Image, threshold: float = 0.8) -> Optional[Tuple[int, int, int, int]]:
        import cv2
        import numpy as np
        
        # Convert PIL to CV2 format (RGB to BGR)
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        template_cv = cv2.cvtColor(np.array(template), cv2.COLOR_RGB2BGR)
        
        result = cv2.matchTemplate(img_cv, template_cv, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= threshold:
            top_left = max_loc
            h, w = template_cv.shape[:2]
            return (top_left[0], top_left[1], w, h)
            
        return None
