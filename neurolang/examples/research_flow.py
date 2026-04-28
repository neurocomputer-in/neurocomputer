"""End-to-end example: research flow.

Demonstrates the Phase 1 surface — a real composable agentic flow built
from NeuroLang primitives + the standard library, with no NL compiler,
no IDE, no differentiability. Just the library.

Run:
    python examples/research_flow.py "best books on category theory"

Optional deps used: openai, requests, beautifulsoup4
    pip install openai requests beautifulsoup4
"""
from __future__ import annotations

import sys

from neurolang import neuro, Flow, Memory, Budget
from neurolang.stdlib import web, reason, memory_neuros


# -- A custom neuro the user defines for this app -----------------------------

@neuro(effect="tool", kind="skill.web", budget=Budget(latency_ms=15000))
def extract_first_result(results: list[dict]) -> str:
    """Pick the first search result and return its scraped text."""
    if not results:
        return ""
    url = results[0]["url"]
    return web.scrape(url)


@neuro(effect="memory")
def remember(value: str) -> str:
    """Save into the active memory under 'last_summary'."""
    memory_neuros.store(value, key="last_summary")
    return value


# -- The flow -----------------------------------------------------------------

research_flow: Flow = (
    web.search                  # query string -> list of results
    | extract_first_result      # results -> scraped text
    | reason.summarize          # text -> short summary
    | remember                  # summary -> store, return summary
)


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else "best books on category theory"

    # Inspect before running
    print("Flow:", research_flow)
    print("Effects:", research_flow.effect_signature())
    cost = research_flow.cost_estimate()
    print(f"Cost estimate: latency_ms={cost.latency_ms} cost_usd={cost.cost_usd}")

    # Build a plan
    plan = research_flow.plan(query)
    print("Plan hash:", plan.hash())
    print("Plan steps:", [s.name.split(".")[-1] for s in plan.steps])

    print("\nMermaid diagram:")
    print(research_flow.to_mermaid())

    # Execute
    print(f"\nRunning research_flow({query!r})...\n")
    mem = Memory.discrete()
    try:
        summary = plan.run(memory=mem)
        print("=" * 60)
        print(summary)
        print("=" * 60)
        print("\nMemory snapshot:", list(mem.keys()))
    except ImportError as e:
        print(f"[Skipped execution — missing optional dep: {e}]")
        print("Install with: pip install openai requests beautifulsoup4")


if __name__ == "__main__":
    main()
