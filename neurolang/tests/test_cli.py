"""Tests for the NeuroLang CLI — exercised via `cli.main([...])`."""
from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from io import StringIO
from unittest.mock import patch

import pytest

from neurolang import cli


# ---- Helpers --------------------------------------------------------------

@contextmanager
def captured_stdout():
    buf = StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        yield buf
    finally:
        sys.stdout = old


def _set_dummy_llm_fn(monkeypatch, tmp_path):
    """Patch the shared _PROVIDERS dict with one smart fake that dispatches
    on the `kind=` kwarg passed by the canonical provider plumbing. Also
    redirect the cache to a tmp dir so tests don't touch the user's real
    ~/.neurolang/cache/.

    `_PROVIDERS` lives in the `_providers` module — both `compile.py` and
    `propose.py` import it from there, so all callers reference THE SAME
    dict object. We patch the canonical location and both callers see it.
    """
    monkeypatch.setenv("NEUROLANG_CACHE", str(tmp_path / "cache"))

    plan_payload = {
        "neuros": [],
        "composition": "",
        "missing": [{"intent": "demo"}],
    }
    compile_payload_src = (
        "from neurolang import Flow\n"
        "from tests.test_compile import _t_double, _t_add_one\n"
        "flow = _t_double | _t_add_one\n"
    )

    def smart_provider(prompt, system, *, model, kind):
        if kind == "plan":
            return json.dumps(plan_payload)
        if kind in ("compile", "decompile"):
            return compile_payload_src
        raise AssertionError(f"smart_provider got unexpected kind={kind!r}")

    from neurolang import _providers
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (smart_provider, "opencode/minimax-m2.5-free"))


# ---- Tests ----------------------------------------------------------------

def test_cli_plan_outputs_json(monkeypatch, tmp_path):
    """plan should emit pretty-printed JSON on stdout containing the
    expected top-level keys."""
    _set_dummy_llm_fn(monkeypatch, tmp_path)
    # Force --dry-run so the test never tries to compile
    with captured_stdout() as buf:
        rc = cli.main(["plan", "x", "--dry-run"])
    assert rc == 0
    output = buf.getvalue().strip()
    # Must be parseable JSON
    parsed = json.loads(output)
    assert "prompt" in parsed
    assert "composition_source" in parsed
    assert "neuros" in parsed
    assert "missing" in parsed
    assert "cost_estimate_usd" in parsed


def test_cli_plan_dry_run_does_not_compile(monkeypatch, tmp_path):
    """--dry-run must not invoke compile_source()."""
    _set_dummy_llm_fn(monkeypatch, tmp_path)
    # Direct submodule import works after the function rename eliminated the package-attribute shadow.
    from neurolang import compile as compile_mod
    with patch.object(compile_mod, "compile_source", side_effect=AssertionError("compile called")) as mocked:
        with captured_stdout():
            rc = cli.main(["plan", "x", "--dry-run"])
    assert rc == 0
    mocked.assert_not_called()


def test_cli_plan_yes_triggers_compile(monkeypatch, tmp_path):
    """--yes must invoke compile_source() after the proposal."""
    _set_dummy_llm_fn(monkeypatch, tmp_path)
    # Direct submodule import works after the function rename eliminated the package-attribute shadow.
    from neurolang import compile as compile_mod
    called = {"n": 0}
    real_compile = compile_mod.compile_source

    def spy(prompt, **kw):
        called["n"] += 1
        return real_compile(prompt, **kw)

    monkeypatch.setattr(compile_mod, "compile_source", spy)
    # cli._cmd_plan does `from . import compile as compile_mod`, which returns
    # the cached sys.modules["neurolang.compile"] — the same module object
    # monkeypatch.setattr(compile_mod, "compile_source", spy) patches.
    # So the spy intercepts the CLI's call.

    with captured_stdout():
        rc = cli.main(["plan", "x", "--yes"])
    assert rc == 0
    assert called["n"] >= 1


def test_cli_plan_dry_run_and_yes_rejected(monkeypatch, tmp_path, capsys):
    """--dry-run + --yes is contradictory; CLI must reject before any LLM call."""
    _set_dummy_llm_fn(monkeypatch, tmp_path)
    rc = cli.main(["plan", "x", "--dry-run", "--yes"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "incompatible" in err.lower() or "incompatible" in err  # message clarity


def test_cli_plan_show_discovery_emits_to_stderr(monkeypatch, tmp_path, capsys):
    """--show-discovery prints DiscoveryReport JSON to stderr (not stdout)."""
    _set_dummy_llm_fn(monkeypatch, tmp_path)
    # Redirect home so discovery has a clean sandbox
    monkeypatch.setenv("HOME", str(tmp_path))
    cli.main(["plan", "x", "--dry-run", "--show-discovery"])
    captured = capsys.readouterr()
    assert "discovery" in captured.err.lower()  # appears in stderr
    # stdout should still contain the proposed plan JSON
    assert '"prompt"' in captured.out


def test_cli_plan_eof_during_prompt_treated_as_no(monkeypatch, tmp_path, capsys):
    """Closed stdin during the [y/N/e] prompt → treat as 'n' (cancel)."""
    _set_dummy_llm_fn(monkeypatch, tmp_path)
    # Force interactive path: TTY stdin + no --yes
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    # input() will raise EOFError because there's no actual input
    monkeypatch.setattr("builtins.input", lambda *a, **k: (_ for _ in ()).throw(EOFError()))
    # Direct submodule import works after the function rename eliminated the package-attribute shadow.
    from neurolang import compile as compile_mod
    called = {"n": 0}
    def spy(*a, **kw):
        called["n"] += 1
        return None
    monkeypatch.setattr(compile_mod, "compile_source", spy)

    rc = cli.main(["plan", "x"])
    assert rc == 0
    assert called["n"] == 0, "compile must not be called on EOF/cancel"


def test_cli_plan_edit_branch_prints_hint(monkeypatch, tmp_path, capsys):
    """Choosing 'e' at the prompt prints a re-run hint and exits 0."""
    _set_dummy_llm_fn(monkeypatch, tmp_path)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *a, **k: "e")
    # Direct submodule import works after the function rename eliminated the package-attribute shadow.
    from neurolang import compile as compile_mod
    called = {"n": 0}
    def spy(*a, **kw):
        called["n"] += 1
        return None
    monkeypatch.setattr(compile_mod, "compile_source", spy)

    rc = cli.main(["plan", "x"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "neurolang plan" in err.lower() or "re-run" in err.lower()
    assert called["n"] == 0


# ---- repl subcommand tests --------------------------------------------------


def test_cli_repl_subcommand_calls_start_repl(monkeypatch, tmp_path):
    """`neurolang repl` should run discover_neuros() then call start_repl
    with the resulting DiscoveryReport."""
    monkeypatch.setenv("NEUROLANG_CACHE", str(tmp_path / "cache"))
    captured: dict = {"reports": []}

    def fake_start_repl(report=None):
        captured["reports"].append(report)
        return 0

    from neurolang import repl as repl_mod
    monkeypatch.setattr(repl_mod, "start_repl", fake_start_repl)

    rc = cli.main(["repl"])
    assert rc == 0
    assert len(captured["reports"]) == 1
    # The report should be a DiscoveryReport (or at least have the expected attrs)
    report = captured["reports"][0]
    assert report is not None
    assert hasattr(report, "user_dir_neuros")
    assert hasattr(report, "project_dir_neuros")


def test_cli_repl_show_discovery_emits_to_stderr(monkeypatch, tmp_path, capsys):
    """`neurolang repl --show-discovery` should print the report JSON to stderr
    before invoking start_repl."""
    monkeypatch.setenv("NEUROLANG_CACHE", str(tmp_path / "cache"))
    monkeypatch.setenv("HOME", str(tmp_path))  # clean discovery sandbox

    from neurolang import repl as repl_mod
    monkeypatch.setattr(repl_mod, "start_repl", lambda report=None: 0)

    rc = cli.main(["repl", "--show-discovery"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "discovery" in err.lower()
