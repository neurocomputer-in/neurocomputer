"""
Analyze a saved job and provide recommendations.
"""
import json
import os

UPWORK_DIR = os.path.join(os.getcwd(), "upwork", "projects")

async def run(state, **kwargs):
    job_slug = kwargs.get("job_slug", "").strip()

    if not job_slug:
        return {"analysis": "Job slug required", "recommendation": "skip"}

    job_dir = os.path.join(UPWORK_DIR, job_slug)
    meta_file = os.path.join(job_dir, "meta.json")

    if not os.path.exists(meta_file):
        return {"analysis": f"No job found: {job_slug}", "recommendation": "skip"}

    with open(meta_file, "r") as f:
        meta = json.load(f)

    llm = state.get("__llm")

    # Build analysis prompt
    title = meta.get("title", "Unknown")
    company = meta.get("company", "Not specified")
    budget = meta.get("budget", "Not specified")
    skills = ", ".join(meta.get("skills", [])[:10])
    description = meta.get("description", "")[:3000]
    verdict = meta.get("verdict", "unknown")
    red_flags = meta.get("red_flags", [])

    user_msg = f"""Analyze this Upwork job posting:

**Title:** {title}
**Company:** {company}
**Budget:** {budget}
**Skills:** {skills}
**Description:** {description}
**AI Verdict:** {verdict}
**Red Flags:** {', '.join(red_flags) if red_flags else 'None'}

Provide:
1. ANALYSIS: Brief analysis of the job (2-3 sentences)
2. RECOMMENDATION: "apply" or "skip" with clear reason
3. PITCH_POINTS: 3 specific things you could highlight in your proposal

Be specific and actionable. Consider: budget fairness, client history, skill match, competition level."""

    if llm:
        try:
            response = llm.generate_text(user_msg, system_prompt="You are an Upwork proposal expert.")
            return {
                "analysis": response,
                "job_slug": job_slug,
                "title": title
            }
        except Exception as e:
            return {"analysis": f"Error: {e}", "recommendation": "unknown"}
    else:
        return {
            "analysis": f"Title: {title}\nBudget: {budget}\nSkills: {skills}",
            "recommendation": verdict if verdict != "unknown" else "review_manually",
            "job_slug": job_slug
        }
