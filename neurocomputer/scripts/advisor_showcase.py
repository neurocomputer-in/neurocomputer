#!/usr/bin/env python3
"""advisor_showcase — REAL end-to-end run of the everything-as-neuro prototype.

Hits a live model provider (OpenCode Zen by default, falls back to OpenRouter
→ Ollama → OpenAI via the inference neuro). No mocks. Persistent memory
across runs (./demo/advisor_memory.db + ./demo/advisor_graph.db).

Exit codes:
    0 — ok
    2 — no provider auth found
    3 — API error on all providers

Usage:
    python3 scripts/advisor_showcase.py                  # default 3-turn demo
    python3 scripts/advisor_showcase.py --reset          # wipe memory, start fresh
    python3 scripts/advisor_showcase.py --interactive    # u ask the questions
    python3 scripts/advisor_showcase.py --question "..."  # one-shot question
"""
import argparse
import asyncio
import os
import pathlib
import sys
import time


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
KV_PATH = DEMO_DIR / "advisor_memory.db"
GRAPH_PATH = DEMO_DIR / "advisor_graph.db"


WORKFLOWS = {
    "advisor": [
        "I'm deciding between Adam and SGD for a small CNN. What's your take?",
        "I went with Adam. What learning rate should I start with?",
        "Any regularization tips for overfitting on a small dataset?",
    ],
    "coder": [
        "write a recursive fibonacci in python",
        "make it faster",
        "now convert that to typescript",
    ],
    # coder_with_tools — LLM can actually read the repo + search memory mid-reply
    "coder_with_tools": [
        "what does core/neuro_factory.py do? read the file first.",
        "list the files in neuros/advisor",
        "search memory for anything about 'fibonacci'",
    ],
}


def _check_auth() -> str | None:
    """Check at least one provider has auth. Returns provider name, or None."""
    # Tell llm_registry to look at everything
    from core.llm_registry import PROVIDER_CONFIGS, get_api_key
    for name in ("opencode-zen", "openrouter", "openai", "ollama"):
        if name == "ollama":
            # Ollama doesn't need auth — assume it's set up if server is up.
            continue
        if get_api_key(name):
            return name
    return None


def _banner(title: str):
    print()
    print("╔" + "═" * 74 + "╗")
    print(f"║  {title:<70}  ║")
    print("╚" + "═" * 74 + "╝")


def _section(label: str):
    print()
    print("─" * 78)
    print(f"  {label}")
    print("─" * 78)


async def _run_one_turn(factory, state, question: str, turn_idx: int, workflow: str):
    print()
    print("=" * 78)
    print(f"  TURN {turn_idx}  ─  USER: {question}")
    print("=" * 78)

    t0 = time.time()
    try:
        out = await factory.run(workflow, state, user_question=question)
    except Exception as e:
        print(f"  ❌ {workflow} failed: {e}")
        return False

    elapsed = time.time() - t0
    reply = state.get("reply", "")
    provider = state.get("provider_used", "?")
    model = state.get("model_used", "?")
    fallback = state.get("fallback_from")

    _section(f"MODEL REPLY  ({elapsed:.1f}s via {provider}"
             + (f" — fell back from {fallback}" if fallback else "")
             + f" / {model})")
    print()
    print(reply.strip() if reply else "(empty)")

    # Stats
    stats_out = await factory.run("memory_graph", state, op="stats")
    stats = stats_out.get("stats", {})
    new_facts = state.get("facts", []) or []
    _section("LIBRARIAN")
    print(f"  new facts this turn: {len(new_facts)}")
    for f in new_facts:
        content = f.get("content", "")
        conf = f.get("confidence", 0)
        print(f"    • ({conf:.2f}) {content}")
    print(f"  memory_graph total: {stats.get('nodes', 0)} nodes, "
          f"{stats.get('edges', 0)} edges")

    return True


async def main_async(args):
    workflow = args.workflow
    if workflow not in WORKFLOWS:
        print(f"  ❌ unknown workflow {workflow!r}. known: {', '.join(WORKFLOWS)}")
        return 3

    # Reset memory if requested
    if args.reset:
        for p in (KV_PATH, GRAPH_PATH):
            if p.exists():
                p.unlink()
                print(f"  wiped {p}")

    os.environ["NEURO_MEMORY_DB"] = str(KV_PATH)
    os.environ["NEURO_GRAPH_DB"] = str(GRAPH_PATH)

    # Preflight
    provider = _check_auth()
    if provider is None:
        print("  ⚠️  No provider auth found.")
        print("  set OPENCODE_API_KEY / OPENROUTER_API_KEY / OPENAI_API_KEY,")
        print("  or run `opencode auth login`, then retry.")
        return 2

    _banner(f"advisor_showcase — workflow={workflow}, REAL-LLM")
    print(f"  primary auth detected: {provider}")
    print(f"  memory: {KV_PATH}")
    print(f"  graph:  {GRAPH_PATH}")

    # Build factory
    from core.neuro_factory import NeuroFactory
    factory = NeuroFactory(dir=str(REPO_ROOT / "neuros"))
    print(f"  loaded {len(factory.reg)} neuros")

    if "inference" not in factory.reg or workflow not in factory.reg:
        print(f"  ❌ required neuros not loaded (inference / {workflow}). Abort.")
        return 3

    cid = f"showcase_{workflow}_session"
    agent_id = "neuro"

    # Collect questions
    if args.question:
        questions = [args.question]
    elif args.interactive:
        questions = None   # ask per-turn
    else:
        questions = args.questions or WORKFLOWS[workflow]

    turn_idx = 1
    any_success = False

    if questions is not None:
        for q in questions:
            state = {"__cid": cid, "__agent_id": agent_id, "user_question": q}
            ok = await _run_one_turn(factory, state, q, turn_idx, workflow)
            any_success = any_success or ok
            turn_idx += 1
    else:
        print()
        print("  interactive mode — ctrl+D or empty line to quit")
        while True:
            try:
                q = input("\n  you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not q:
                break
            state = {"__cid": cid, "__agent_id": agent_id, "user_question": q}
            ok = await _run_one_turn(factory, state, q, turn_idx, workflow)
            any_success = any_success or ok
            turn_idx += 1

    _banner("done")
    stats_out = await factory.run("memory_graph",
                                  {"__cid": cid}, op="stats")
    stats = stats_out.get("stats", {})
    print(f"  final memory_graph: {stats.get('nodes', 0)} nodes, "
          f"{stats.get('edges', 0)} edges by kind: "
          f"{stats.get('nodes_by_kind', {})}")
    print(f"  memory persists at {KV_PATH} and {GRAPH_PATH}")
    print(f"  re-run without --reset and next turn will recall from this session.")
    print()

    return 0 if any_success else 3


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workflow", type=str, default="advisor",
                    choices=list(WORKFLOWS.keys()),
                    help="which workflow to run (advisor|coder)")
    ap.add_argument("--reset", action="store_true",
                    help="wipe the demo memory files before running")
    ap.add_argument("--interactive", action="store_true",
                    help="ask questions interactively instead of scripted ones")
    ap.add_argument("--question", type=str, default=None,
                    help="single-turn: just run this one question")
    ap.add_argument("--questions", type=str, nargs="+", default=None,
                    help="explicit scripted questions (space-separated)")
    args = ap.parse_args()

    # Make repo imports work regardless of cwd
    sys.path.insert(0, str(REPO_ROOT))

    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
