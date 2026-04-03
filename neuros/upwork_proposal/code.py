"""
Generate a proposal draft for a saved job.
"""
import json
import os

UPWORK_DIR = os.path.join(os.getcwd(), "upwork", "projects")

async def run(state, **kwargs):
    job_slug = kwargs.get("job_slug", "").strip()
    custom_intro = kwargs.get("custom_intro", "").strip()

    if not job_slug:
        return {"proposal": "Job slug required", "word_count": 0}

    job_dir = os.path.join(UPWORK_DIR, job_slug)
    meta_file = os.path.join(job_dir, "meta.json")

    if not os.path.exists(meta_file):
        return {"proposal": f"No job found: {job_slug}", "word_count": 0}

    with open(meta_file, "r") as f:
        meta = json.load(f)

    # Save proposal
    proposal_file = os.path.join(job_dir, "proposal.md")

    title = meta.get("title", "Unknown")
    company = meta.get("company", "Not specified")
    budget = meta.get("budget", "Not specified")
    skills = meta.get("skills", [])
    description = meta.get("description", "")[:3000]

    user_msg = f"""Write a compelling Upwork proposal for this job:

**Title:** {title}
**Client:** {company}
**Budget:** {budget}
**Key Skills:** {', '.join(skills[:8])}
**Job Details:** {description}

{custom_intro if custom_intro else "Write a professional proposal highlighting relevant experience and how you'll approach the work."}

Keep it concise (150-300 words), conversational but professional. Focus on the client's needs, not yourself. End with a question to start conversation."""

    llm = state.get("__llm")

    if llm:
        try:
            proposal = llm.generate_text(user_msg, system_prompt="You are an expert Upwork freelancer writing persuasive proposals.")
            word_count = len(proposal.split())
        except Exception as e:
            proposal = f"Error generating proposal: {e}"
            word_count = 0
    else:
        proposal = f"# Proposal for {title}\n\n**Budget:** {budget}\n**Skills:** {', '.join(skills)}\n\nPlease provide a custom_intro to generate a full proposal."
        word_count = len(proposal.split())

    # Save proposal
    with open(proposal_file, "w") as f:
        f.write(f"# Proposal: {title}\n\n{proposal}\n\n---\n*Generated at: {__import__('datetime').datetime.now().isoformat()}*")

    return {
        "proposal": proposal,
        "word_count": word_count,
        "job_slug": job_slug,
        "saved_to": proposal_file
    }
