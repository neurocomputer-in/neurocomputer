"""NeuroLang interactive REPL.

Wraps `code.InteractiveConsole` with:
  - a pre-populated namespace (core types + stdlib namespaces + discovered neuros)
  - a meta-command preprocessor for `:catalog` / `:plan` / `:compile` / `:help`
  - async-aware displayhook so coroutine results are auto-resolved
  - readline + persistent history on Unix (graceful no-op on Windows)

Public entry: `start_repl(report=None)`. Called from `cli._cmd_repl()`.
"""
from __future__ import annotations

import asyncio
import atexit
import code
import inspect
import sys
from pathlib import Path
from typing import Optional

from . import (
    Flow, Plan, Memory, Budget, Effect, neuro, register,
    compile_source, decompile_summary, propose_plan, discover_neuros,
    default_registry,
)
from .stdlib import web, reason, model, voice, memory_neuros, email_neuros
from .discover import DiscoveryReport


REPL_HISTORY = Path.home() / ".neurolang" / "repl_history"

REPL_BANNER_TEMPLATE = r"""
  _   _                      _
 | \ | | ___ _   _ _ __ ___ | |    __ _ _ __   __ _
 |  \| |/ _ \ | | | '__/ _ \| |   / _` | '_ \ / _` |
 | |\  |  __/ |_| | | | (_) | |__| (_| | | | | (_| |
 |_| \_|\___|\__,_|_|  \___/|_____\__,_|_| |_|\__, |
                                              |___/
          NeuroLang REPL — compose AI agents — v{version}

Loaded: {stdlib_count} stdlib neuros + {user_count} user neuros + {project_count} project neuros
Discovery: {user_path_summary}, {project_summary}
Type :help for meta-commands, :exit to quit.
"""

# Stdlib namespaces pre-loaded into the REPL. Single source of truth shared
# by _build_namespace (binds the modules into the namespace) and
# _format_banner (counts how many stdlib neuros are registered).
STDLIB_NAMESPACES = (
    ("web", web),
    ("reason", reason),
    ("model", model),
    ("voice", voice),
    ("memory_neuros", memory_neuros),
    ("email", email_neuros),
)
def _is_stdlib_neuro(name: str) -> bool:
    """True for neuros whose canonical name lives under neurolang.stdlib.*."""
    parts = name.split(".")
    return len(parts) >= 3 and parts[0] == "neurolang" and parts[1] == "stdlib"


def _build_namespace(*, registry=None) -> dict:
    """Assemble the initial REPL namespace.

    Includes:
      - Core types: Flow, Plan, Memory, Budget, Effect, neuro, register
      - Top-level fns: compile_source, decompile_summary, propose_plan,
        discover_neuros, default_registry
      - Stdlib namespaces: web, reason, model, voice, memory_neuros
      - Discovered user neuros: each registered neuro whose .name does NOT
        contain a dot is bound at the top level by its name. Dotted names
        like `web.search` are reachable via their stdlib namespace already.
        Names that would shadow existing namespace entries (core types,
        stdlib modules) are SKIPPED — explicit safety so a user-registered
        `Flow` neuro doesn't replace the `Flow` type.
    """
    ns: dict = {
        # Core types
        "Flow": Flow, "Plan": Plan, "Memory": Memory,
        "Budget": Budget, "Effect": Effect,
        "neuro": neuro, "register": register,
        # Top-level fns
        "compile_source": compile_source,
        "decompile_summary": decompile_summary,
        "propose_plan": propose_plan,
        "discover_neuros": discover_neuros,
        "default_registry": default_registry,
    }
    # Stdlib namespaces — driven by the module-level tuple
    for name, module in STDLIB_NAMESPACES:
        ns[name] = module
    reg = registry if registry is not None else default_registry
    for n in reg:
        if "." not in n.name and n.name not in ns:
            ns[n.name] = n
    return ns


def _format_banner(report: Optional[DiscoveryReport]) -> str:
    """Compose the startup banner from a DiscoveryReport. report=None means
    discovery wasn't run (or hasn't been wired up yet)."""
    from . import __version__

    stdlib_count = sum(1 for n in default_registry if _is_stdlib_neuro(n.name))
    user_count = len(report.user_dir_neuros) if report else 0
    project_count = len(report.project_dir_neuros) if report else 0
    user_path = str(Path.home() / ".neurolang" / "neuros")
    if user_count:
        user_summary = f"{user_path} ({user_count} files)"
    else:
        user_summary = f"{user_path} (empty)"
    if report and report.project_root:
        project_summary = f"{report.project_root}/neuros ({project_count} files)"
    else:
        project_summary = "<project> not detected"
    return REPL_BANNER_TEMPLATE.format(
        version=__version__,
        stdlib_count=stdlib_count,
        user_count=user_count,
        project_count=project_count,
        user_path_summary=user_summary,
        project_summary=project_summary,
    )


# ---------------------------------------------------------------------------
# Meta-command preprocessor + dispatcher
# ---------------------------------------------------------------------------


def _is_meta(line: str) -> bool:
    return line.lstrip().startswith(":")


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _handle_meta(line: str, ns: dict) -> None:
    """Execute a meta-command. Print errors to stderr; never raise out
    (SystemExit excluded — `:exit`/`:quit` must propagate)."""
    parts = line.lstrip()[1:].strip()  # drop the leading ':'
    if not parts:
        print("[repl error] empty meta-command; try :help", file=sys.stderr)
        return
    cmd, _, rest = parts.partition(" ")
    cmd = cmd.lower()
    rest = rest.strip()
    try:
        if cmd == "help":
            _meta_help()
        elif cmd == "catalog":
            _meta_catalog()
        elif cmd == "plan":
            _meta_plan(rest, ns)
        elif cmd == "compile":
            _meta_compile(rest, ns)
        elif cmd in ("exit", "quit"):
            sys.exit(0)
        else:
            print(f"[repl error] unknown meta-command :{cmd} (try :help)",
                  file=sys.stderr)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[repl error] :{cmd} failed: {type(e).__name__}: {e}",
              file=sys.stderr)


def _meta_help() -> None:
    print("Meta-commands:")
    print("  :help                — this list")
    print("  :catalog             — show the registered-neuro catalog as markdown")
    print("  :plan \"<NL>\"         — propose a flow for an NL prompt; binds `last_plan`")
    print("  :compile \"<NL>\"      — NL → Flow; binds `flow` in this session")
    print("  :exit | :quit        — leave the REPL (Ctrl+D also works)")


def _meta_catalog() -> None:
    from ._providers import _render_catalog
    print(_render_catalog(default_registry))


def _meta_plan(rest: str, ns: dict) -> None:
    if not rest:
        print('[repl error] :plan needs an NL prompt, e.g. :plan "fetch emails"',
              file=sys.stderr)
        return
    prompt = _strip_quotes(rest)
    plan = propose_plan(prompt)
    ns["last_plan"] = plan
    print(f"Prompt:      {plan.prompt}")
    print(f"Composition: {plan.composition_source}")
    if plan.neuros:
        print("Neuros:")
        for n in plan.neuros:
            eff = ",".join(n.effects) or "pure"
            print(f"  - {n.name}  effects=[{eff}]  ~${n.cost_estimate_usd:.4f}  ~{n.latency_estimate_ms}ms")
    if plan.missing:
        print("Missing capabilities:")
        for m in plan.missing:
            sug = ", ".join(m.suggestions) if m.suggestions else "(none)"
            print(f"  - {m.intent}  suggested: {sug}")
    print(f"Total est:   ${plan.cost_estimate_usd:.4f}, ~{plan.latency_estimate_ms}ms")
    print('Bound to `last_plan`. Use `:compile "<prompt>"` to build the Flow.')


def _meta_compile(rest: str, ns: dict) -> None:
    if not rest:
        print('[repl error] :compile needs an NL prompt, e.g. :compile "fetch emails"',
              file=sys.stderr)
        return
    prompt = _strip_quotes(rest)
    flow, source = compile_source(prompt, output="both")
    ns["flow"] = flow
    print("Bound to `flow` — run via flow.run(...)")
    print("--- Source ---")
    print(source)


# ---------------------------------------------------------------------------
# Console subclass — intercept meta-commands before Python parsing
# ---------------------------------------------------------------------------


class NeuroLangConsole(code.InteractiveConsole):
    """code.InteractiveConsole + meta-command preprocessor."""

    def __init__(self, locals=None, filename: str = "<neurolang-repl>"):
        super().__init__(locals=locals, filename=filename)
        # `code.InteractiveConsole.__init__` guarantees self.locals is a dict
        # (it creates one when locals=None). Bind to the SAME object so meta-
        # command mutations (e.g., `:plan` setting last_plan) are visible to
        # subsequent Python expressions in this session.
        self._namespace = self.locals

    def push(self, line: str) -> bool:
        if _is_meta(line):
            _handle_meta(line, self._namespace)
            self.resetbuffer()
            return False
        return super().push(line)


# ---------------------------------------------------------------------------
# Async coroutine auto-await
# ---------------------------------------------------------------------------

# Captured at import time so we can delegate to whatever was set BEFORE we
# install our wrapper. (Tests monkeypatch this when exercising the wrapper.)
_orig_displayhook = sys.displayhook


def _async_aware_displayhook(value) -> None:
    """If `value` is a coroutine/awaitable, run it via asyncio.run() and
    display the resolved result. Otherwise delegate to the original displayhook.

    Standard sys.displayhook ignores None — preserve that.
    """
    if value is None:
        return
    try:
        if inspect.iscoroutine(value):
            value = asyncio.run(value)
        elif inspect.isawaitable(value):
            value = asyncio.run(_to_coroutine(value))
    except Exception as e:
        print(f"[repl error] auto-await failed: {type(e).__name__}: {e}",
              file=sys.stderr)
        return
    # Module-attr lookup (NOT a closure over the import-time value) so tests
    # can monkeypatch repl._orig_displayhook to inject a recorder.
    _orig_displayhook(value)


async def _to_coroutine(awaitable):
    """Adapter: lift any awaitable into a coroutine that awaits it."""
    return await awaitable


# ---------------------------------------------------------------------------
# readline + persistent history (best-effort, Unix-only)
# ---------------------------------------------------------------------------


def _try_setup_readline(ns: dict) -> bool:
    """Wire up tab-completion against `ns` and persistent history at
    REPL_HISTORY. Returns True on success, False if readline is unavailable
    or any setup step fails. The REPL works either way."""
    try:
        import readline
        import rlcompleter
    except ImportError:
        return False
    try:
        completer = rlcompleter.Completer(ns)
        readline.set_completer(completer.complete)
        readline.parse_and_bind("tab: complete")
        REPL_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        if REPL_HISTORY.exists():
            try:
                readline.read_history_file(str(REPL_HISTORY))
            except Exception:
                pass  # corrupted history shouldn't kill the REPL
        atexit.register(_save_history)
        return True
    except Exception:
        return False


def _save_history() -> None:
    try:
        import readline
        readline.write_history_file(str(REPL_HISTORY))
    except Exception:
        pass


def start_repl(report: Optional[DiscoveryReport] = None) -> int:
    """Build the namespace, install async-aware displayhook, set up readline,
    run the console."""
    ns = _build_namespace()
    saved_displayhook = sys.displayhook
    sys.displayhook = _async_aware_displayhook
    _try_setup_readline(ns)
    banner = _format_banner(report)
    console = NeuroLangConsole(locals=ns)
    try:
        console.interact(banner=banner)
    except SystemExit as e:
        if e.code is None:
            return 0
        if isinstance(e.code, int):
            return e.code
        # String/other code: print message and exit with status 1 (Python convention)
        print(e.code, file=sys.stderr)
        return 1
    finally:
        sys.displayhook = saved_displayhook
    return 0
