# `neurolang repl` — Design Spec

**Status:** Drafted 2026-04-26. Pending user review, then writing-plans.

**Goal:** Ship `neurolang repl` — an interactive shell where users (humans + AI assistants) compose, inspect, and run NeuroLang flows by typing Python OR natural language. Closes the propose → compile → run loop in one continuous session, replacing today's "edit a `.py` file, run `python ...`" loop.

The killer flow:

```
$ neurolang repl
NeuroLang REPL — 0.0.1
Loaded: 10 stdlib neuros + 2 user neuros (~/.neurolang/neuros/) + 0 project neuros
Type :help for meta-commands, :exit to quit.

>>> :compile "fetch unread emails and summarize them"
Bound to `flow` — run via flow.run(...)

>>> flow.run()
"You have 3 unread: ..."

>>> flow2 = web.search | reason.summarize
>>> flow2.render(format="mermaid")
'graph LR; ...'
```

---

## 1. Locked design decisions (from brainstorming)

| # | Decision | Choice |
|---|---|---|
| 1 | Namespace pre-loading at startup? | **Stdlib + transparency banner** — pre-load core types, top-level fns, all stdlib namespaces, AND every discovered neuro from `default_registry`; print a banner showing exactly what landed and from which paths. |
| 2 | Async coroutine auto-await? | **Yes** — override `sys.displayhook` so top-level expressions returning coroutines are auto-resolved via `asyncio.run()` and the resolved value is displayed. |
| 3 | Tab completion in v1? | **Yes on Unix (readline + rlcompleter), graceful no-op on Windows.** Persistent history at `~/.neurolang/repl_history`. |
| 4 | Meta-command set in v1? | `:help`, `:catalog`, `:plan "<NL>"`, `:compile "<NL>"`, `:exit`/`:quit`. Deferred to v2: `:save`, `:cache`, `:clear`. |

---

## 2. Architecture

One new module + one CLI subcommand. ~200 LOC source, ~12 tests in `test_repl.py` plus 2 added to `test_cli.py`.

```
neurolang/
├── repl.py              [NEW]   — NeuroLangConsole + start_repl()
├── cli.py               [MOD]   — add `repl` subcommand → _cmd_repl()
tests/test_repl.py        [NEW]   — mocked stdin/stdout, meta-commands, async, banner
tests/test_cli.py         [MOD]   — 2 new tests for the `repl` subcommand wiring
```

Module boundaries:

- `repl.py` knows about: `code.InteractiveConsole` extension, namespace assembly, meta-command dispatch, displayhook override for async, readline integration.
- `cli.py` only adds the subparser entry and calls `repl.start_repl()`. Stays thin.

---

## 3. Component contracts

### 3.1 `neurolang/repl.py`

```python
import asyncio
import atexit
import code
import sys
from io import StringIO
from pathlib import Path
from typing import Any, Optional

from . import (
    Flow, Plan, Memory, Budget, Effect, neuro, register,
    compile_source, decompile_summary, propose_plan, discover_neuros,
    default_registry,
)
from .stdlib import web, reason, model, voice, memory_neuros
from ._providers import _render_catalog


REPL_HISTORY = Path.home() / ".neurolang" / "repl_history"
REPL_BANNER_TEMPLATE = """\
NeuroLang REPL — {version}
Loaded: {stdlib_count} stdlib neuros + {user_count} user neuros + {project_count} project neuros
Discovery: {user_path_summary}, {project_summary}
Type :help for meta-commands, :exit to quit.
"""


def _build_namespace(report=None) -> dict:
    """Assemble the initial REPL namespace.

    Includes:
      - Core types: Flow, Plan, Memory, Budget, Effect, neuro, register
      - Top-level fns: compile_source, decompile_summary, propose_plan,
        discover_neuros, default_registry
      - Stdlib namespaces: web, reason, model, voice, memory_neuros
      - Discovered user neuros: each registered neuro whose .name does NOT
        contain a dot is bound at the top level by its name. (Dotted names
        like `web.search` are reachable via their stdlib namespace already.)
    """
    ns: dict = {
        # Core types
        "Flow": Flow, "Plan": Plan, "Memory": Memory,
        "Budget": Budget, "Effect": Effect,
        "neuro": neuro, "register": register,
        # Top-level functions
        "compile_source": compile_source,
        "decompile_summary": decompile_summary,
        "propose_plan": propose_plan,
        "discover_neuros": discover_neuros,
        "default_registry": default_registry,
        # Stdlib namespaces
        "web": web, "reason": reason, "model": model,
        "voice": voice, "memory_neuros": memory_neuros,
    }
    # User neuros (no dot in name — dotted ones live under their namespace).
    # Skip names that would shadow existing namespace entries (core types,
    # stdlib modules) — explicit safety so a user-registered `Flow` neuro
    # doesn't replace the `Flow` type at the top of the REPL.
    for n in default_registry:
        if "." not in n.name and n.name not in ns:
            ns[n.name] = n
    return ns


def _format_banner(report) -> str:
    """Compose the startup banner from a DiscoveryReport."""
    from . import __version__
    # Counts...
    stdlib_count = sum(
        1 for n in default_registry
        if n.name.split(".")[0] in {"web", "reason", "model", "voice"}
        or n.name.startswith("memory.")
    )
    user_count = len(report.user_dir_neuros) if report else 0
    project_count = len(report.project_dir_neuros) if report else 0
    user_path = str(Path.home() / ".neurolang" / "neuros")
    user_summary = f"{user_path} ({user_count} files)" if user_count else f"{user_path} (empty)"
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


# Meta-command preprocessor + dispatcher

def _is_meta(line: str) -> bool:
    return line.lstrip().startswith(":")


def _handle_meta(line: str, ns: dict) -> None:
    """Execute a meta-command. Print errors to stderr; never raise out."""
    parts = line.lstrip()[1:].strip()  # drop the leading ':'
    if not parts:
        print("[repl error] empty meta-command; try :help", file=sys.stderr)
        return
    cmd, _, rest = parts.partition(" ")
    cmd = cmd.lower()
    rest = rest.strip()
    try:
        if cmd in ("help",):
            _meta_help()
        elif cmd in ("catalog",):
            _meta_catalog()
        elif cmd in ("plan",):
            _meta_plan(rest, ns)
        elif cmd in ("compile",):
            _meta_compile(rest, ns)
        elif cmd in ("exit", "quit"):
            sys.exit(0)
        else:
            print(f"[repl error] unknown meta-command :{cmd} (try :help)", file=sys.stderr)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[repl error] :{cmd} failed: {type(e).__name__}: {e}", file=sys.stderr)


def _meta_help() -> None:
    print("Meta-commands:")
    print("  :help                — this list")
    print("  :catalog             — show the registered-neuro catalog as markdown")
    print("  :plan \"<NL>\"         — propose a flow for an NL prompt; binds `last_plan`")
    print("  :compile \"<NL>\"      — NL → Flow; binds `flow` in this session")
    print("  :exit | :quit        — leave the REPL (Ctrl+D also works)")


def _meta_catalog() -> None:
    print(_render_catalog(default_registry))


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _meta_plan(rest: str, ns: dict) -> None:
    if not rest:
        print('[repl error] :plan needs an NL prompt, e.g. :plan "fetch emails"', file=sys.stderr)
        return
    prompt = _strip_quotes(rest)
    plan = propose_plan(prompt)
    ns["last_plan"] = plan
    # Human-friendly summary
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
    print("Bound to `last_plan`. Use `:compile \"<prompt>\"` to build the Flow.")


def _meta_compile(rest: str, ns: dict) -> None:
    if not rest:
        print('[repl error] :compile needs an NL prompt, e.g. :compile "fetch emails"', file=sys.stderr)
        return
    prompt = _strip_quotes(rest)
    flow, source = compile_source(prompt, output="both")
    ns["flow"] = flow
    print("Bound to `flow` — run via flow.run(...)")
    print("--- Source ---")
    print(source)


# Async coroutine auto-await via displayhook

_orig_displayhook = sys.displayhook


def _async_aware_displayhook(value: Any) -> None:
    """If `value` is an awaitable/coroutine, run it and display the result."""
    if value is None:
        return
    try:
        import inspect
        if inspect.iscoroutine(value):
            value = asyncio.run(value)
        elif inspect.isawaitable(value):
            value = asyncio.run(_to_coroutine(value))
    except Exception as e:
        print(f"[repl error] auto-await failed: {type(e).__name__}: {e}", file=sys.stderr)
        return
    _orig_displayhook(value)


async def _to_coroutine(awaitable):
    return await awaitable


# The console subclass

class NeuroLangConsole(code.InteractiveConsole):
    """code.InteractiveConsole + meta-command preprocessor."""

    def __init__(self, locals=None, filename="<neurolang-repl>"):
        super().__init__(locals=locals, filename=filename)
        self._namespace = locals if locals is not None else {}

    def push(self, line: str) -> bool:
        """Override: handle meta-commands BEFORE Python parsing."""
        if _is_meta(line):
            _handle_meta(line, self._namespace)
            self.resetbuffer()
            return False  # not a continuation
        return super().push(line)


# readline + history setup (best-effort)

def _try_setup_readline(ns: dict) -> bool:
    """Returns True iff readline + completion + history were wired up.
    On Windows or any failure, returns False — the REPL still works."""
    try:
        import readline
        import rlcompleter
    except ImportError:
        return False
    completer = rlcompleter.Completer(ns)
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")
    REPL_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    if REPL_HISTORY.exists():
        try:
            readline.read_history_file(str(REPL_HISTORY))
        except Exception:
            pass
    atexit.register(lambda: readline.write_history_file(str(REPL_HISTORY)))
    return True


# Public entry point

def start_repl(report=None) -> int:
    """Build the namespace, install the displayhook, set up readline, run.
    `report` is the DiscoveryReport returned by cli.main()'s discover_neuros();
    used only to render the banner. Tests can pass None or a fake."""
    ns = _build_namespace(report)
    sys.displayhook = _async_aware_displayhook
    _try_setup_readline(ns)
    banner = _format_banner(report)
    console = NeuroLangConsole(locals=ns)
    try:
        console.interact(banner=banner)
    except SystemExit as e:
        return int(e.code or 0)
    return 0
```

### 3.2 `neurolang/cli.py` — `repl` subcommand

In `main()`, add the subparser:

```python
pr = sub.add_parser("repl", help="Interactive REPL with discovered neuros pre-loaded")
pr.add_argument("--show-discovery", action="store_true",
                help="Print the DiscoveryReport before starting (debug)")
pr.set_defaults(func=_cmd_repl)
```

`_cmd_repl(args)`:

```python
def _cmd_repl(args) -> int:
    """Handle `neurolang repl` — start the interactive shell."""
    from . import repl
    # main() already ran discover_neuros() and stored the report in module-state
    # (see Section 3.3). repl gets the report for its banner.
    return repl.start_repl(_LAST_DISCOVERY_REPORT)
```

### 3.3 Discovery-report propagation

`main()` already runs `discover_neuros()` at startup. To pass the report into `start_repl()` for the banner, store it in a module-level variable:

```python
_LAST_DISCOVERY_REPORT = None  # set by main() after discovery

def main(argv=None) -> int:
    # ...existing parsing...
    args = parser.parse_args(argv)
    from . import discover as discover_mod
    global _LAST_DISCOVERY_REPORT
    _LAST_DISCOVERY_REPORT = discover_mod.discover_neuros()
    if getattr(args, "show_discovery", False):
        print(json.dumps({"discovery": dataclasses.asdict(_LAST_DISCOVERY_REPORT)}, ...), file=sys.stderr)
    return args.func(args)
```

This is a small change (one global, one assignment). Beats threading the report through every subcommand handler — only `_cmd_repl` cares about it.

---

## 4. Data flow

```
$ neurolang repl
        │
        ▼
cli.main():
  - parser.parse_args(["repl"])
  - discover_neuros() → DiscoveryReport (stdlib + user + project)
  - _LAST_DISCOVERY_REPORT = report
  - dispatch _cmd_repl(args)
        │
        ▼
_cmd_repl(args):
  - return repl.start_repl(_LAST_DISCOVERY_REPORT)
        │
        ▼
repl.start_repl(report):
  - ns = _build_namespace(report)
      - core types, top-level fns, stdlib namespaces
      - every dot-less neuro from default_registry
  - sys.displayhook = _async_aware_displayhook
  - _try_setup_readline(ns)  → completion + history (Unix only)
  - banner = _format_banner(report)
  - NeuroLangConsole(locals=ns).interact(banner=banner)
        │
        ▼
User types a line:
  - line starts with ":" → _handle_meta(line, ns)
      - dispatch to _meta_help / _meta_catalog / _meta_plan / _meta_compile / exit
      - meta-command failure → print "[repl error] ..." to stderr, continue
  - otherwise → super().push(line) → Python compile + exec
      - sys.displayhook is invoked on the top-level expression value
      - if value is coroutine → asyncio.run(); display the resolved value
        │
        ▼
User exits (Ctrl+D / :exit / :quit):
  - atexit hook writes ~/.neurolang/repl_history (if readline was wired)
  - process exits with code 0
```

---

## 5. Error handling

### 5.1 Meta-command errors (non-fatal)

Every `:...` command is wrapped in a try/except in `_handle_meta`. Failures print `[repl error] :<cmd> failed: <ErrorType>: <msg>` to stderr; the session continues. Only `SystemExit` propagates (so `:exit`/`:quit` work).

### 5.2 Python expression errors (non-fatal)

Inherited from `code.InteractiveConsole`: full traceback printed via `showtraceback`; session continues. Standard Python REPL behavior.

### 5.3 Async auto-await errors

If `asyncio.run()` raises, the displayhook prints `[repl error] auto-await failed: ...` and skips the display step. Session continues.

### 5.4 readline absent (Windows etc.)

`_try_setup_readline` returns False on ImportError. REPL works — no completion, no persistent history. No error message (it's expected behavior on Windows).

### 5.5 Discovery errors (non-fatal)

`discover_neuros()` already collects per-file errors into `DiscoveryReport.errors` without raising. The banner does NOT print errors by default; the user passes `--show-discovery` to see them on stderr.

### 5.6 Ctrl+C / Ctrl+D

- Ctrl+C during input: cancels current line (standard `code.InteractiveConsole` behavior)
- Ctrl+D / EOF: graceful exit; history saved if readline was wired

---

## 6. Testing strategy

All tests offline (no real LLM, no real terminal, no network), matching the project pattern.

### 6.1 `tests/test_repl.py` (new, ~12 tests)

| Test | Asserts |
|---|---|
| `test_namespace_includes_core_types` | After `_build_namespace()`, `ns["Flow"]` is `Flow`, `ns["neuro"]` is the decorator, etc. |
| `test_namespace_includes_stdlib` | `ns["web"]`, `ns["reason"]`, etc. resolve to the stdlib modules |
| `test_namespace_includes_dotless_user_neuros` | Register a fake neuro with name `"my_thing"` and assert `ns["my_thing"]` is it; verify a dotted-name neuro is NOT bound at top level |
| `test_banner_renders` | `_format_banner(fake_report)` includes the version, neuro counts, and discovery paths |
| `test_meta_help_lists_commands` | Capture stdout while calling `_handle_meta(":help", ns)`; assert each command is mentioned |
| `test_meta_catalog_prints_markdown` | Capture stdout while calling `_handle_meta(":catalog", ns)`; assert it starts with the markdown header from `_render_catalog` |
| `test_meta_plan_calls_propose_and_binds_last_plan` | Patch `_providers._PROVIDERS["openai"]` with a smart fake (kind="plan" returns canned JSON); call `_handle_meta(':plan "x"', ns)`; assert `ns["last_plan"]` is a `ProposedPlan` |
| `test_meta_compile_calls_compile_and_binds_flow` | Same fake provider (kind="compile" returns valid Python source); call `_handle_meta(':compile "x"', ns)`; assert `ns["flow"]` is a `Flow` and the source was printed |
| `test_meta_exit_raises_systemexit` | `_handle_meta(":exit", ns)` → `SystemExit` |
| `test_meta_unknown_does_not_kill_session` | `_handle_meta(":nosuch", ns)` → prints to stderr, returns normally (no exception) |
| `test_async_displayhook_resolves_coroutine` | Define a small async fn returning 42; pass the coroutine to `_async_aware_displayhook`; assert `_orig_displayhook` was called with `42` (not a coroutine) |
| `test_console_handles_meta_via_push` | Construct `NeuroLangConsole`, call `.push(":help")`; assert it returns False (no continuation) and the buffer is reset |

Tests use `pytest`'s `capsys` for stdout/stderr capture, `monkeypatch` for env redirection (`NEUROLANG_CACHE` → tmp), and the smart-provider pattern from `test_cli.py` for LLM mocking.

### 6.2 `tests/test_cli.py` (extend, ~2 tests)

| Test | Asserts |
|---|---|
| `test_cli_repl_subcommand_calls_start_repl` | Patch `repl.start_repl` to return 0; call `cli.main(["repl"])`; assert patched fn called once with the discovery report |
| `test_cli_repl_show_discovery_flag` | Same but with `--show-discovery`; assert discovery JSON appeared on stderr |

### 6.3 Running

```bash
cd /home/ubuntu/neurolang && python -m pytest tests/ -q
```

Target: 84 (current) + 14 new = ~98 tests, fully offline, < 1s.

---

## 7. Out of scope (explicit)

- `:save` (export current `flow` to a `.py` file) — defer; `compile_source(prompt, output="source")` + manual write is the workaround
- `:cache` — defer; `neurolang cache list/clear` from another shell works
- `:clear` — defer; `:exit` then re-enter is the workaround
- Custom prompt themes / colors — defer
- IPython-style `?` introspection — `help(x)` works via Python builtin
- Multi-language NL input (Hindi etc.) — handled by `compile_source` / `propose_plan` already; REPL just passes the string through
- Persistent session state across REPL runs — out of scope; user can save scripts manually

---

## 8. Estimated effort

~2-3 hours for a focused, TDD'd implementation:

- `repl.py` skeleton (namespace, banner, `start_repl`): 30 min
- Meta-commands (`:help`/`:catalog`/`:plan`/`:compile`/`:exit`): 45 min
- Async displayhook + `NeuroLangConsole` push override: 30 min
- readline + history wiring: 20 min
- `tests/test_repl.py` (12 tests): 45 min
- `cli.py` integration + `tests/test_cli.py` extension (2 tests): 20 min
- STATUS + CHANGELOG updates: 10 min

After implementation:
- Quick smoke: `python -m neurolang repl` works interactively
- Update `STATUS.md` (REPL → "Just shipped"; pick the new "Next up")
- Append to `CHANGELOG.md`
