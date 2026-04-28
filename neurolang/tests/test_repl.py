"""Tests for the NeuroLang REPL — namespace + banner + console push."""
from __future__ import annotations

from io import StringIO
import sys
from pathlib import Path

import pytest

from neurolang import Flow, neuro, register, default_registry
from neurolang.registry import Registry
from neurolang.discover import DiscoveryReport


# ---- _build_namespace tests --------------------------------------------------

def test_namespace_includes_core_types():
    from neurolang.repl import _build_namespace
    ns = _build_namespace()
    assert ns["Flow"] is Flow
    assert ns["neuro"] is neuro
    assert ns["register"] is register
    # Top-level fns from Phase 1.5/1.6 rename
    from neurolang import (
        compile_source, decompile_summary, propose_plan, discover_neuros,
    )
    assert ns["compile_source"] is compile_source
    assert ns["decompile_summary"] is decompile_summary
    assert ns["propose_plan"] is propose_plan
    assert ns["discover_neuros"] is discover_neuros
    assert ns["default_registry"] is default_registry


def test_namespace_includes_stdlib_namespaces():
    from neurolang.repl import _build_namespace
    from neurolang.stdlib import web, reason, model, voice, memory_neuros
    ns = _build_namespace()
    assert ns["web"] is web
    assert ns["reason"] is reason
    assert ns["model"] is model
    assert ns["voice"] is voice
    assert ns["memory_neuros"] is memory_neuros


def test_namespace_binds_dotless_user_neuros():
    """A registered neuro whose name contains no dot lands in the REPL namespace
    by that name. Dotted names (like `web.search`) are accessed via their stdlib
    namespace and NOT bound at the top level."""
    from neurolang.repl import _build_namespace

    custom_reg = Registry()

    @neuro(name="my_thing", register=False)
    def _my_thing(x):
        """A test neuro."""
        return x

    @neuro(name="myns.deep_thing", register=False)
    def _deep_thing(x):
        """A test neuro under a namespace."""
        return x

    custom_reg.add(_my_thing)
    custom_reg.add(_deep_thing)

    ns = _build_namespace(registry=custom_reg)
    assert ns["my_thing"] is _my_thing
    # Dotted names should NOT appear at top level
    assert "myns.deep_thing" not in ns
    assert "deep_thing" not in ns


def test_namespace_collision_safety_does_not_clobber_core():
    """A user neuro accidentally named `Flow` must NOT replace the Flow type
    at the top of the REPL namespace."""
    from neurolang.repl import _build_namespace

    custom_reg = Registry()

    @neuro(name="Flow", register=False)
    def _evil(x):
        """A neuro named Flow."""
        return x

    custom_reg.add(_evil)

    ns = _build_namespace(registry=custom_reg)
    assert ns["Flow"] is Flow  # NOT the user neuro


def test_namespace_defaults_to_default_registry():
    """When `registry` is omitted, _build_namespace falls back to the package's
    default_registry. We assert this by registering a neuro globally and
    verifying it appears in the resulting namespace."""
    from neurolang.repl import _build_namespace
    from neurolang import default_registry

    @neuro(name="_repl_default_marker")
    def _marker(x):
        """Probe neuro for default-registry test."""
        return x

    try:
        ns = _build_namespace()
        assert ns.get("_repl_default_marker") is _marker
    finally:
        # Clean up: remove the test neuro from the global registry so it
        # doesn't leak into other tests' default-registry scans.
        default_registry._by_name.pop("_repl_default_marker", None)


# ---- _format_banner tests ----------------------------------------------------

def test_banner_renders_with_report():
    from neurolang.repl import _format_banner
    fake_report = DiscoveryReport(
        user_dir_neuros=[Path("/home/u/.neurolang/neuros/a.py")],
        project_dir_neuros=[],
        extra_neuros=[],
        project_root=None,
    )
    banner = _format_banner(fake_report)
    assert "NeuroLang REPL" in banner
    # Should mention the user-neuros count
    assert "1 user neuros" in banner
    # Should mention the user neuros path
    assert ".neurolang/neuros" in banner


def test_banner_renders_with_none_report():
    """Sanity: passing report=None still produces a usable banner."""
    from neurolang.repl import _format_banner
    banner = _format_banner(None)
    assert "NeuroLang REPL" in banner
    assert "0 user neuros" in banner


def test_banner_includes_project_root_when_detected():
    from neurolang.repl import _format_banner
    fake_report = DiscoveryReport(
        user_dir_neuros=[],
        project_dir_neuros=[Path("/proj/neuros/p.py")],
        extra_neuros=[],
        project_root=Path("/proj"),
    )
    banner = _format_banner(fake_report)
    assert "/proj/neuros" in banner


def test_banner_counts_actual_stdlib():
    """Regression: banner used to show '0 stdlib neuros' because the heuristic
    split on the first dot segment ('neurolang') instead of checking the full
    'neurolang.stdlib.*' prefix."""
    from neurolang.repl import _format_banner
    from neurolang.stdlib import web, reason, model, voice, memory_neuros  # noqa: F401
    banner = _format_banner(None)
    # There are 12 stdlib neuros in the default registry; confirm non-zero.
    import re
    match = re.search(r"(\d+) stdlib neuros", banner)
    assert match is not None, "banner should contain '<N> stdlib neuros'"
    assert int(match.group(1)) > 0, "stdlib_count must be > 0 after imports"


# ---- Meta-command tests ------------------------------------------------------

def _capture_handle_meta(line, ns):
    """Helper: call _handle_meta and return (stdout, stderr) captured."""
    from neurolang.repl import _handle_meta
    out, err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        _handle_meta(line, ns)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return out.getvalue(), err.getvalue()


def test_meta_help_lists_commands():
    ns: dict = {}
    out, err = _capture_handle_meta(":help", ns)
    assert ":catalog" in out
    assert ":plan" in out
    assert ":compile" in out
    assert ":exit" in out or ":quit" in out


def test_meta_catalog_prints_markdown():
    ns: dict = {}
    out, err = _capture_handle_meta(":catalog", ns)
    # _render_catalog markdown starts with this header
    assert "Available NeuroLang neuros" in out


def test_meta_unknown_does_not_kill_session():
    ns: dict = {}
    out, err = _capture_handle_meta(":nosuch_command", ns)
    # Error goes to stderr; no exception raised
    assert "[repl error]" in err
    assert ":nosuch_command" in err.lower() or "nosuch_command" in err.lower()
    # Session-continuity proof: a follow-up meta-command must still work.
    out2, err2 = _capture_handle_meta(":help", ns)
    assert ":catalog" in out2
    assert err2 == ""


def test_meta_empty_does_not_kill_session():
    ns: dict = {}
    out, err = _capture_handle_meta(":", ns)
    assert "[repl error]" in err


def test_meta_exit_raises_systemexit():
    from neurolang.repl import _handle_meta
    ns: dict = {}
    with pytest.raises(SystemExit):
        _handle_meta(":exit", ns)


def test_meta_quit_raises_systemexit():
    from neurolang.repl import _handle_meta
    ns: dict = {}
    with pytest.raises(SystemExit):
        _handle_meta(":quit", ns)


def test_meta_plan_calls_propose_and_binds_last_plan(monkeypatch, tmp_path):
    """`:plan "<NL>"` should call propose_plan() and bind the result to
    ns['last_plan']. Use the smart-provider pattern from test_cli.py."""
    import json as _json
    from neurolang import _providers

    monkeypatch.setenv("NEUROLANG_CACHE", str(tmp_path / "cache"))
    plan_payload = {
        "neuros": [], "composition": "",
        "missing": [{"intent": "demo"}],
    }

    def smart(prompt, system, *, model, kind, **kwargs):
        if kind == "plan":
            return _json.dumps(plan_payload)
        raise AssertionError(f"unexpected kind={kind!r}")

    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (smart, "opencode/minimax-m2.5-free"))

    ns: dict = {}
    out, err = _capture_handle_meta(':plan "demo"', ns)

    from neurolang.propose import ProposedPlan
    assert isinstance(ns.get("last_plan"), ProposedPlan)
    # Output should mention the prompt + "Bound to `last_plan`"
    assert "demo" in out
    assert "last_plan" in out


def test_meta_plan_missing_argument_errors():
    ns: dict = {}
    out, err = _capture_handle_meta(":plan", ns)
    assert "[repl error]" in err
    assert "needs an NL prompt" in err.lower() or "prompt" in err.lower()


def test_meta_compile_calls_compile_and_binds_flow(monkeypatch, tmp_path):
    """`:compile "<NL>"` should call compile_source() and bind the resulting
    Flow to ns['flow']."""
    from neurolang import _providers

    monkeypatch.setenv("NEUROLANG_CACHE", str(tmp_path / "cache"))
    compile_src = (
        "from neurolang import Flow\n"
        "from tests.test_compile import _t_double, _t_add_one\n"
        "flow = _t_double | _t_add_one\n"
    )

    def smart(prompt, system, *, model, kind, **kwargs):
        if kind == "compile":
            return compile_src
        raise AssertionError(f"unexpected kind={kind!r}")

    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (smart, "opencode/minimax-m2.5-free"))

    ns: dict = {}
    out, err = _capture_handle_meta(':compile "double then add one"', ns)

    assert isinstance(ns.get("flow"), Flow)
    assert "Bound to `flow`" in out
    assert "_t_double" in out  # source printed


def test_console_push_intercepts_meta(monkeypatch):
    """NeuroLangConsole.push() should call _handle_meta for `:` lines and
    return False (no continuation), without invoking Python parsing."""
    from neurolang.repl import NeuroLangConsole
    ns: dict = {}
    console = NeuroLangConsole(locals=ns)
    # `:help` is a known meta-command; should not raise; should return False
    out, err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        result = console.push(":help")
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    assert result is False  # no continuation expected
    assert ":catalog" in out.getvalue()  # _handle_meta did run


def test_console_namespace_aliases_locals_when_locals_none():
    """When NeuroLangConsole(locals=None), self._namespace must alias self.locals
    (NOT a separate empty dict) so meta-command mutations are visible to user code."""
    from neurolang.repl import NeuroLangConsole
    console = NeuroLangConsole(locals=None)
    assert console._namespace is console.locals
    # Concrete check: a meta-command that binds `last_plan` should be visible
    # via console.locals (the dict Python eval would see).
    console._namespace["sentinel"] = 42
    assert console.locals["sentinel"] == 42


# ---- Async displayhook tests ------------------------------------------------

def test_async_displayhook_resolves_coroutine():
    """The wrapped displayhook should auto-run a coroutine and display the
    awaited value instead of the coroutine object."""
    from neurolang.repl import _async_aware_displayhook

    async def _say_hi():
        return 42

    captured: list = []

    def fake_orig(value):
        captured.append(value)

    # Patch the original displayhook the wrapper delegates to
    import neurolang.repl as repl_mod
    saved = repl_mod._orig_displayhook
    repl_mod._orig_displayhook = fake_orig
    try:
        coro = _say_hi()
        _async_aware_displayhook(coro)
    finally:
        repl_mod._orig_displayhook = saved

    assert captured == [42]


def test_async_displayhook_passes_through_non_coroutine():
    from neurolang.repl import _async_aware_displayhook
    captured: list = []
    import neurolang.repl as repl_mod
    saved = repl_mod._orig_displayhook
    repl_mod._orig_displayhook = captured.append
    try:
        _async_aware_displayhook("hello")
        _async_aware_displayhook(123)
    finally:
        repl_mod._orig_displayhook = saved
    assert captured == ["hello", 123]


def test_async_displayhook_skips_none():
    """Standard sys.displayhook silently ignores None — preserve that behavior."""
    from neurolang.repl import _async_aware_displayhook
    captured: list = []
    import neurolang.repl as repl_mod
    saved = repl_mod._orig_displayhook
    repl_mod._orig_displayhook = captured.append
    try:
        _async_aware_displayhook(None)
    finally:
        repl_mod._orig_displayhook = saved
    assert captured == []  # None was filtered before delegation


def test_async_displayhook_error_path_when_coroutine_raises():
    """If the awaited coroutine raises, _async_aware_displayhook prints
    [repl error] to stderr and does NOT call _orig_displayhook."""
    from neurolang.repl import _async_aware_displayhook

    async def boom():
        raise ValueError("x")

    captured: list = []
    err_buf = StringIO()
    import neurolang.repl as repl_mod
    saved = repl_mod._orig_displayhook
    saved_err = sys.stderr
    repl_mod._orig_displayhook = captured.append
    sys.stderr = err_buf
    try:
        _async_aware_displayhook(boom())
    finally:
        repl_mod._orig_displayhook = saved
        sys.stderr = saved_err
    assert captured == []  # display NOT called on error
    err = err_buf.getvalue()
    assert "[repl error]" in err
    assert "auto-await failed" in err
    assert "ValueError" in err
    assert "x" in err


def test_start_repl_restores_displayhook(monkeypatch):
    """start_repl() must restore sys.displayhook to its pre-call value, even
    if the console raises SystemExit. Otherwise the wrapper bleeds into
    Jupyter / parent processes / subsequent test runs."""
    from neurolang import repl as repl_mod

    sentinel_hook = lambda v: None  # noqa: E731
    saved = sys.displayhook
    try:
        sys.displayhook = sentinel_hook
        # Patch NeuroLangConsole.interact to raise SystemExit immediately
        monkeypatch.setattr(
            repl_mod.NeuroLangConsole, "interact",
            lambda self, banner=None: (_ for _ in ()).throw(SystemExit(0)),
        )
        # Avoid touching the real ~/.neurolang/ paths during banner formatting
        monkeypatch.setattr(repl_mod, "REPL_HISTORY", Path("/tmp/neurolang_test_repl_history"))

        rc = repl_mod.start_repl(None)
        assert rc == 0
        assert sys.displayhook is sentinel_hook  # restored
    finally:
        sys.displayhook = saved


# ---- readline setup tests ---------------------------------------------------

def test_try_setup_readline_returns_false_when_readline_missing(monkeypatch):
    """If `import readline` fails, the function returns False and the REPL
    still works without completion or history."""
    import builtins
    real_import = builtins.__import__

    def hide_readline(name, *args, **kwargs):
        if name == "readline":
            raise ImportError("simulated: no readline on this platform")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", hide_readline)

    from neurolang.repl import _try_setup_readline
    assert _try_setup_readline({}) is False


def test_try_setup_readline_returns_true_when_readline_available(monkeypatch, tmp_path):
    """On a normal Unix host, the function wires completion + history and
    returns True. We redirect the history file to tmp_path."""
    pytest.importorskip("readline")  # skip on Windows / hosts without readline
    monkeypatch.setattr(
        "neurolang.repl.REPL_HISTORY",
        tmp_path / "repl_history",
    )
    from neurolang.repl import _try_setup_readline
    assert _try_setup_readline({"x": 1}) is True
    # The history dir should now exist
    assert (tmp_path / "repl_history").parent.exists()
