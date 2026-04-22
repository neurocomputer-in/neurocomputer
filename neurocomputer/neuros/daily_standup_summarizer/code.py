from neuro_sdk import BaseNeuro

class DailyStandupSummarizer(BaseNeuro):
    """
    Input state keys:
        - messages (list[dict]):  Each dict has keys 'author' (str) and 'text' (str).

    Output state keys:
        - summary (dict): Keys 'yesterday', 'today', 'blockers',
                          each mapping to a list of {'author': str, 'point': str}.
        - summary_text (str): A human-readable markdown version of the summary.
    """

    async def run(self, state, **kw):
        messages = state.get("messages", [])

        summary = {
            "yesterday": [],
            "today": [],
            "blockers": [],
        }

        YESTERDAY_KEYWORDS = ("yesterday", "completed", "finished", "done", "shipped", "merged")
        TODAY_KEYWORDS     = ("today", "will", "plan", "going to", "working on", "next")
        BLOCKER_KEYWORDS   = ("blocked", "blocker", "issue", "problem", "stuck", "waiting on")

        for msg in messages:
            author = msg.get("author", "Unknown")
            text   = msg.get("text", "")

            # Split into sentences for finer-grained bucketing
            sentences = [s.strip() for s in text.replace("\n", ".").split(".") if s.strip()]

            for sentence in sentences:
                lower = sentence.lower()
                if any(kw in lower for kw in BLOCKER_KEYWORDS):
                    summary["blockers"].append({"author": author, "point": sentence})
                elif any(kw in lower for kw in YESTERDAY_KEYWORDS):
                    summary["yesterday"].append({"author": author, "point": sentence})
                elif any(kw in lower for kw in TODAY_KEYWORDS):
                    summary["today"].append({"author": author, "point": sentence})
                else:
                    # Default bucket: treat as 'today' if unclassified
                    summary["today"].append({"author": author, "point": sentence})

        # Build a readable markdown summary
        lines = ["## Daily Standup Summary\n"]
        for section, emoji in (("yesterday", "✅"), ("today", "🔨"), ("blockers", "🚧")):
            lines.append(f"### {emoji} {section.capitalize()}")
            if summary[section]:
                for entry in summary[section]:
                    lines.append(f"- **{entry['author']}**: {entry['point']}")
            else:
                lines.append("- _Nothing reported_")
            lines.append("")

        state["summary"]      = summary
        state["summary_text"] = "\n".join(lines)
        return state
