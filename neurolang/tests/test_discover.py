"""Tests for the filesystem auto-discovery."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from neurolang.registry import default_registry
from neurolang.discover import (
    discover_neuros,
    find_project_root,
    DiscoveryReport,
    reset,
)


# ---- Test helpers ---------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_imported_state():
    """Clear the discovery idempotency cache + remove any test-registered neuros."""
    reset()
    # Snapshot registry; clean up new entries after the test
    before = set(default_registry._by_name)
    yield
    after = set(default_registry._by_name)
    for k in after - before:
        del default_registry._by_name[k]


def _write_neuro_file(path: Path, name: str, body: str = "return 1") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(f"""
        from neurolang import neuro

        @neuro(name="{name}")
        def _fn():
            {body}
    """))
    return path


# ---- find_project_root ----------------------------------------------------

def test_find_project_root_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    sub = tmp_path / "a" / "b" / "c"
    sub.mkdir(parents=True)
    assert find_project_root(sub) == tmp_path


def test_find_project_root_dotneurolang_overrides_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    inner = tmp_path / "inner"
    inner.mkdir()
    (inner / ".neurolang").write_text("")
    deep = inner / "x" / "y"
    deep.mkdir(parents=True)
    assert find_project_root(deep) == inner


def test_find_project_root_returns_none_when_no_marker(tmp_path):
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    # tmp_path is a pristine pytest fixture dir — no markers anywhere
    # at it or below it. The walk goes UP from sub through tmp_path and
    # then beyond. To prevent a marker on a real ancestor (e.g. /home or /)
    # from polluting the result, we assert that find_project_root either
    # returns None OR returns an ancestor *outside* tmp_path. We assert
    # nothing under tmp_path matches.
    result = find_project_root(sub)
    assert result is None or (tmp_path not in result.parents and result != tmp_path)


# ---- discover -------------------------------------------------------------

def test_discover_empty_user_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))
    report = discover_neuros()
    assert isinstance(report, DiscoveryReport)
    assert report.user_dir_neuros == []
    assert report.project_dir_neuros == []
    assert report.errors == []


def test_discover_user_dir_loads_neuros(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))
    user_dir = tmp_path / ".neurolang" / "neuros"
    _write_neuro_file(user_dir / "alpha.py", "user.alpha")

    report = discover_neuros()

    assert len(report.user_dir_neuros) == 1
    assert report.user_dir_neuros[0].name == "alpha.py"
    assert "user.alpha" in default_registry._by_name


def test_discover_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))
    user_dir = tmp_path / ".neurolang" / "neuros"
    _write_neuro_file(user_dir / "beta.py", "user.beta")

    r1 = discover_neuros()
    r2 = discover_neuros()
    assert len(r1.user_dir_neuros) == 1
    assert len(r2.user_dir_neuros) == 0  # second call: nothing newly imported


def test_discover_bad_file_continues(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))
    user_dir = tmp_path / ".neurolang" / "neuros"
    user_dir.mkdir(parents=True)
    (user_dir / "bad.py").write_text("def +oops(:\n    pass\n")
    _write_neuro_file(user_dir / "good.py", "user.good")

    report = discover_neuros()

    assert len(report.errors) == 1
    bad_path, msg = report.errors[0]
    assert bad_path.name == "bad.py"
    assert "SyntaxError" in msg
    # The good neuro still loaded
    assert "user.good" in default_registry._by_name


def test_discover_project_neuros_loaded(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("[project]\nname='p'\n")
    cwd = project_root / "src" / "deep"
    cwd.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: cwd))

    _write_neuro_file(project_root / "neuros" / "tool.py", "proj.tool")

    report = discover_neuros()

    assert report.project_root == project_root
    assert len(report.project_dir_neuros) == 1
    assert "proj.tool" in default_registry._by_name


def test_discover_extra_paths(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: tmp_path))

    extra_dir = tmp_path / "extra"
    _write_neuro_file(extra_dir / "ex.py", "extra.ex")

    report = discover_neuros(extra_paths=[extra_dir])

    assert len(report.extra_neuros) == 1
    assert "extra.ex" in default_registry._by_name


def test_discover_no_project_dir_neuros_directory(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    project_root = tmp_path / "proj"
    project_root.mkdir()
    (project_root / "pyproject.toml").write_text("[project]\nname='p'\n")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home_dir))
    monkeypatch.setattr(Path, "cwd", classmethod(lambda cls: project_root))

    report = discover_neuros()

    # Project found, but no `neuros/` subdir — non-error
    assert report.project_root == project_root
    assert report.project_dir_neuros == []
    assert report.errors == []
