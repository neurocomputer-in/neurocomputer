"""
Deduplicate OCR frames and extract structured job data.
Uses LLM to parse raw text into structured fields.
"""
import json
import os
import re
from datetime import datetime

UPWORK_DIR = os.path.join(os.getcwd(), "upwork", "projects")

def simple_deduplicate(frames):
    """Remove duplicate lines across frames using simple string similarity."""
    unique_lines = set()
    deduplicated = []

    for frame in frames:
        text = frame.get("text", "")
        lines = text.split("\n")
        new_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Simple dedup: skip exact duplicates and very short lines
            if len(line) < 5:
                continue
            if line not in unique_lines:
                unique_lines.add(line)
                new_lines.append(line)

        if new_lines:
            deduplicated.append("\n".join(new_lines))

    return "\n---\n".join(deduplicated), len(unique_lines)

async def run(state, **kwargs):
    job_slug = kwargs.get("job_slug", "").strip()

    if not job_slug:
        return {"ok": False, "error": "job_slug is required"}

    job_dir = os.path.join(UPWORK_DIR, job_slug)
    frames_file = os.path.join(job_dir, "frames.json")

    if not os.path.exists(frames_file):
        return {"ok": False, "error": f"No frames found for {job_slug}"}

    # Load frames
    with open(frames_file, "r") as f:
        frames = json.load(f)

    if not frames:
        return {"ok": False, "error": "No frames to process"}

    # Deduplicate
    combined_text, unique_lines = simple_deduplicate(frames)

    # Extract structured data using LLM
    llm = state.get("__llm")
    if not llm:
        # Fallback: just save combined text
        meta = {
            "job_slug": job_slug,
            "raw_text": combined_text[:5000],
            "url": frames[0].get("url", ""),
            "captured_at": datetime.now().isoformat(),
            "frame_count": len(frames),
            "unique_lines": unique_lines
        }
    else:
        system_prompt = """You are a job posting analyzer. Extract structured data from Upwork job descriptions.

Return JSON with these fields:
- title: Job title
- company: Client/company name (or "Not specified")
- budget: Budget range (e.g., "$500-$1000" or "Fixed price" or "Hourly: $15-25/hr")
- posted_date: When posted (or "Not specified")
- skills: Array of key skills
- description: Full job description (keep important details)
- verdict: "worth_applying" or "skip" with brief reason
- red_flags: Array of concerns (empty if none)

If fields are not found in the text, use null or "Not specified"."""

        user_msg = f"Extract job data from:\n\n{combined_text[:8000]}"

        try:
            raw_output = llm.generate_json(user_msg, system_prompt=system_prompt)
            # Parse JSON
            if raw_output.startswith("```json"):
                raw_output = raw_output[7:]
            if raw_output.startswith("```"):
                raw_output = raw_output[3:]
            if raw_output.endswith("```"):
                raw_output = raw_output[:-3]

            job_data = json.loads(raw_output.strip())
        except Exception as e:
            job_data = {"error": str(e), "raw_text": combined_text[:5000]}

    # Save meta.json
    meta = {
        "job_slug": job_slug,
        "title": job_data.get("title", "Unknown"),
        "company": job_data.get("company", "Not specified"),
        "budget": job_data.get("budget", "Not specified"),
        "posted_date": job_data.get("posted_date", "Not specified"),
        "skills": job_data.get("skills", []),
        "description": job_data.get("description", combined_text[:3000]),
        "url": frames[0].get("url", ""),
        "verdict": job_data.get("verdict", "unknown"),
        "red_flags": job_data.get("red_flags", []),
        "captured_at": datetime.now().isoformat(),
        "frame_count": len(frames),
        "unique_lines": unique_lines
    }

    meta_file = os.path.join(job_dir, "meta.json")
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    # Clean up frames file (optional - keep for reference)
    # Save combined raw text
    raw_file = os.path.join(job_dir, "raw_combined.txt")
    with open(raw_file, "w") as f:
        f.write(combined_text)

    return {
        "ok": True,
        "job_data": {k: v for k, v in meta.items() if k != "raw_text"},
        "frame_count": len(frames),
        "unique_lines": unique_lines,
        "job_slug": job_slug
    }
