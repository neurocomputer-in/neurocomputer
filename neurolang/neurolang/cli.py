"""NeuroLang CLI — `neurolang compile`, `neurolang summarize`, `neurolang run`.

Entry point: registered as `neurolang` in pyproject.toml.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Optional


# Stashed by main() after discover_neuros() runs, so _cmd_repl can pass
# the DiscoveryReport into start_repl()'s banner without rewiring every
# subcommand handler. Read by _cmd_repl only.
_LAST_DISCOVERY_REPORT = None


# Exit codes:
#   0 — success or user-cancelled at TTY prompt (no error)
#   1 — compile error (matches _cmd_compile)
#   2 — propose error or usage error (matches argparse convention)
def _cmd_plan(args) -> int:
    """Handle `neurolang plan "<prompt>"`.

    Flow:
      1. propose_plan(prompt) → ProposedPlan as JSON to stdout
      2. If --dry-run: stop here.
      3. Decide proceed: --yes OR non-TTY stdin → auto-yes;
         otherwise prompt [y/N/e].
      4. On proceed: compile_source(prompt) → optionally write to -o, optionally --execute.
    """
    from . import compile as compile_mod
    from . import propose as propose_mod
    from .stdlib import web, reason, memory_neuros, model, voice  # noqa: F401

    # Reject incompatible flag combos before any LLM call
    if args.dry_run and args.yes:
        print("[plan error] --dry-run and --yes are incompatible", file=sys.stderr)
        return 2

    try:
        plan = propose_mod.propose_plan(args.prompt, model=args.model,
                                         use_cache=not args.no_cache)
    except propose_mod.ProposeError as e:
        err = {"error": "propose_failed", "stage": "propose", "message": str(e)}
        print(json.dumps(err, indent=2), file=sys.stderr)
        return 2

    # Pretty-print as JSON to stdout
    print(json.dumps(dataclasses.asdict(plan), indent=2, default=str))

    if args.dry_run:
        return 0

    # Decide whether to proceed to compile
    proceed = args.yes or not sys.stdin.isatty()
    if not proceed:
        try:
            ans = input("\nCompile this plan? [y/N/e] ").strip().lower()
        except EOFError:
            ans = "n"
        if ans == "y":
            proceed = True
        elif ans == "e":
            print("[hint] Re-run with edited prompt: "
                  f"neurolang plan \"<your edited intent>\"", file=sys.stderr)
            return 0
        else:
            return 0

    # Compile
    try:
        flow, source = compile_mod.compile_source(
            args.prompt, model=args.model, output="both",
            use_cache=not args.no_cache,
        )
    except compile_mod.CompileError as e:
        print(f"[compile error] {e}", file=sys.stderr)
        return 1

    if args.output_file:
        Path(args.output_file).write_text(source)
        print(f"Wrote {args.output_file} ({len(source)} chars)", file=sys.stderr)
    else:
        print("\n=== Compiled source ===", file=sys.stderr)
        print(source)

    if args.execute:
        print("=== Running ===", file=sys.stderr)
        result = flow.run()
        print("=== Result ===", file=sys.stderr)
        print(result)
    return 0


def _cmd_compile(args) -> int:
    from . import compile as compile_mod
    from . import default_registry
    from .stdlib import web, reason, memory_neuros, model, voice  # populate registry  # noqa: F401

    try:
        if args.execute:
            flow, source = compile_mod.compile_source(args.prompt, model=args.model, output="both",
                                                       use_cache=not args.no_cache)
            print("=== Generated source ===")
            print(source)
            print("=== Running ===")
            result = flow.run()
            print("=== Result ===")
            print(result)
        else:
            source = compile_mod.compile_source(args.prompt, model=args.model, output="source",
                                                 use_cache=not args.no_cache)
            if args.output_file:
                Path(args.output_file).write_text(source)
                print(f"Wrote {args.output_file} ({len(source)} chars)")
            else:
                print(source)
        return 0
    except Exception as e:
        print(f"[compile error] {e}", file=sys.stderr)
        return 1


def _cmd_summarize(args) -> int:
    from .compile import decompile_summary
    try:
        source = Path(args.path).read_text()
        summary = decompile_summary(source, model=args.model, use_cache=not args.no_cache)
        print(summary)
        return 0
    except Exception as e:
        print(f"[summarize error] {e}", file=sys.stderr)
        return 1


def _cmd_catalog(args) -> int:
    from ._providers import _render_catalog
    from . import default_registry
    from .stdlib import web, reason, memory_neuros, model, voice  # noqa: F401
    print(_render_catalog(default_registry))
    return 0


def _cmd_cache(args) -> int:
    from .cache import CompilerCache
    cache = CompilerCache()
    if args.action == "list":
        for entry in cache.list():
            short_prompt = entry.get("prompt", "")[:60]
            print(f"{entry['key']}  {entry['model']:<10}  {short_prompt}")
        return 0
    if args.action == "clear":
        cache.clear()
        print("cache cleared")
        return 0
    return 1


def _cmd_repl(args) -> int:
    """Handle `neurolang repl` — start the interactive shell."""
    from . import repl
    from .stdlib import web, reason, memory_neuros, model, voice  # noqa: F401  (populate registry)
    return repl.start_repl(_LAST_DISCOVERY_REPORT)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="neurolang", description="NeuroLang CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # compile
    pc = sub.add_parser("compile", help="Compile a natural-language prompt to NeuroLang Python")
    pc.add_argument("prompt", help="Natural-language description of the flow")
    pc.add_argument("--model", default=None)
    pc.add_argument("-o", "--output-file", help="Write source to this file instead of stdout")
    pc.add_argument("--execute", action="store_true", help="After compiling, also run the flow")
    pc.add_argument("--no-cache", action="store_true", help="Skip cache lookup; force fresh compile")
    pc.set_defaults(func=_cmd_compile)

    # summarize
    ps = sub.add_parser("summarize", help="Summarize a NeuroLang source file in natural language")
    ps.add_argument("path", help="Path to a .py file containing a NeuroLang flow")
    ps.add_argument("--model", default=None)
    ps.add_argument("--no-cache", action="store_true")
    ps.set_defaults(func=_cmd_summarize)

    # catalog
    pcat = sub.add_parser("catalog", help="List all registered neuros in markdown")
    pcat.set_defaults(func=_cmd_catalog)

    # cache
    pca = sub.add_parser("cache", help="Manage the compilation cache")
    pca.add_argument("action", choices=["list", "clear"])
    pca.set_defaults(func=_cmd_cache)

    # repl
    pr = sub.add_parser("repl", help="Interactive REPL with discovered neuros pre-loaded")
    pr.add_argument("--show-discovery", action="store_true",
                    help="Print the DiscoveryReport before starting (debug)")
    pr.set_defaults(func=_cmd_repl)

    # plan
    pp = sub.add_parser("plan", help="Propose a flow for a natural-language prompt as JSON")
    pp.add_argument("prompt", help="Natural-language description of the flow")
    pp.add_argument("--model", default=None)
    pp.add_argument("--yes", "--no-confirm", dest="yes", action="store_true",
                    help="Skip the TTY confirmation; compile after proposing")
    pp.add_argument("--dry-run", action="store_true",
                    help="Print proposal as JSON; do not compile")
    pp.add_argument("--execute", action="store_true",
                    help="After compile, also run the flow")
    pp.add_argument("-o", "--output-file",
                    help="Write compiled source to this file")
    pp.add_argument("--show-discovery", action="store_true",
                    help="Print the DiscoveryReport before dispatching")
    pp.add_argument("--no-cache", action="store_true",
                    help="Skip cache lookup; force fresh LLM calls for both propose and compile")
    pp.set_defaults(func=_cmd_plan)

    args = parser.parse_args(argv)

    # Auto-run filesystem discovery before dispatch (idempotent).
    # Stash the report so _cmd_repl can pass it to start_repl()'s banner
    # without rewiring every subcommand handler.
    from . import discover as discover_mod
    global _LAST_DISCOVERY_REPORT
    _LAST_DISCOVERY_REPORT = discover_mod.discover_neuros()
    if getattr(args, "show_discovery", False):
        print(json.dumps({"discovery": dataclasses.asdict(_LAST_DISCOVERY_REPORT)},
                         indent=2, default=str),
              file=sys.stderr)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
