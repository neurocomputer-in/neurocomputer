"""
List all saved Upwork jobs.
"""
import json
import os
from datetime import datetime

UPWORK_DIR = os.path.join(os.getcwd(), "upwork", "projects")

async def run(state, **kwargs):
    if not os.path.exists(UPWORK_DIR):
        return {"jobs": [], "count": 0, "message": "No jobs saved yet. Capture a job first."}

    jobs = []
    for job_slug in os.listdir(UPWORK_DIR):
        job_dir = os.path.join(UPWORK_DIR, job_slug)
        if not os.path.isdir(job_dir):
            continue

        meta_file = os.path.join(job_dir, "meta.json")
        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                meta = json.load(f)
            jobs.append({
                "slug": job_slug,
                "title": meta.get("title", "Unknown"),
                "company": meta.get("company", "Not specified"),
                "budget": meta.get("budget", "Not specified"),
                "verdict": meta.get("verdict", "unknown"),
                "captured_at": meta.get("captured_at", ""),
                "url": meta.get("url", "")
            })
        else:
            # Job in progress (has frames but not finalized)
            frames_file = os.path.join(job_dir, "frames.json")
            frame_count = 0
            if os.path.exists(frames_file):
                with open(frames_file, "r") as f:
                    frames = json.load(f)
                    frame_count = len(frames)

            jobs.append({
                "slug": job_slug,
                "title": f"[In Progress] {job_slug}",
                "frame_count": frame_count,
                "status": "not_finalized"
            })

    # Sort by captured_at (newest first)
    jobs.sort(key=lambda x: x.get("captured_at", ""), reverse=True)

    return {
        "jobs": jobs,
        "count": len(jobs)
    }
