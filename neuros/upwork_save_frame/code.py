"""
Save a raw OCR frame to a job's frames.json.
"""
import json
import os
from datetime import datetime

UPWORK_DIR = os.path.join(os.getcwd(), "upwork", "projects")

async def run(state, **kwargs):
    job_slug = kwargs.get("job_slug", "").strip().replace(" ", "_").lower()
    frame_text = kwargs.get("frame_text", "").strip()
    url = kwargs.get("url", "")

    if not job_slug:
        return {"saved": False, "error": "job_slug is required"}
    if not frame_text:
        return {"saved": False, "error": "frame_text is required"}

    # Create job directory
    job_dir = os.path.join(UPWORK_DIR, job_slug)
    os.makedirs(job_dir, exist_ok=True)

    # Load existing frames
    frames_file = os.path.join(job_dir, "frames.json")
    if os.path.exists(frames_file):
        with open(frames_file, "r") as f:
            frames = json.load(f)
    else:
        frames = []

    # Add new frame
    frame_entry = {
        "text": frame_text,
        "url": url,
        "timestamp": datetime.now().isoformat()
    }
    frames.append(frame_entry)

    # Save frames
    with open(frames_file, "w") as f:
        json.dump(frames, f, indent=2, ensure_ascii=False)

    return {
        "saved": True,
        "frame_count": len(frames),
        "job_slug": job_slug
    }
