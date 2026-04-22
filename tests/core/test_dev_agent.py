"""Tests for core.dev_agent — validate + atomic save + rollback."""
import json
import pytest
from pathlib import Path
from core import dev_agent


@pytest.fixture
def temp_repo(tmp_path, monkeypatch):
    """Redirect dev_agent's NEUROS_DIR + SNAPSHOTS_DIR at tmp_path."""
    neuros = tmp_path / "neuros"
    snaps = tmp_path / ".neuros_history"
    neuros.mkdir()
    monkeypatch.setattr(dev_agent, "NEUROS_DIR", neuros)
    monkeypatch.setattr(dev_agent, "SNAPSHOTS_DIR", snaps)
    return tmp_path


# ── conf validation ────────────────────────────────────────────────

def test_validate_conf_happy(temp_repo):
    conf = {"name": "demo", "description": "x"}
    out = dev_agent.validate_conf_json(conf)
    assert out["ok"] is True


def test_validate_conf_missing_fields(temp_repo):
    out = dev_agent.validate_conf_json({})
    assert out["ok"] is False
    assert any("name" in e for e in out["errors"])
    assert any("description" in e for e in out["errors"])


def test_validate_conf_invalid_name(temp_repo):
    out = dev_agent.validate_conf_json({"name": "Bad-Name!", "description": "x"})
    assert out["ok"] is False
    assert any("snake_case" in e for e in out["errors"])


def test_validate_conf_json_string(temp_repo):
    out = dev_agent.validate_conf_json('{"name":"ok","description":"x"}')
    assert out["ok"] is True


def test_validate_conf_bad_json(temp_repo):
    out = dev_agent.validate_conf_json("{ not json }")
    assert out["ok"] is False
    assert "invalid JSON" in out["errors"][0]


# ── code validation ────────────────────────────────────────────────

def test_validate_code_async_fn_ok(temp_repo):
    src = "async def run(state, **kw):\n    return {}\n"
    assert dev_agent.validate_code_py(src)["ok"]


def test_validate_code_class_method_ok(temp_repo):
    src = ("from core.base_neuro import BaseNeuro\n"
           "class X(BaseNeuro):\n"
           "    async def run(self, state, **kw):\n        return {}\n")
    assert dev_agent.validate_code_py(src)["ok"]


def test_validate_code_missing_run(temp_repo):
    src = "def hello():\n    return 42\n"
    out = dev_agent.validate_code_py(src)
    assert out["ok"] is False
    assert any("run" in e.lower() for e in out["errors"])


def test_validate_code_syntax_error(temp_repo):
    out = dev_agent.validate_code_py("def oops( :\n")
    assert out["ok"] is False
    assert any("SyntaxError" in e for e in out["errors"])


def test_validate_code_forbidden_shell_call_ai(temp_repo):
    src = ("import os\n"
           "async def run(state, **kw):\n"
           "    os.system('rm -rf /')\n"
           "    return {}\n")
    out = dev_agent.validate_code_py(src, author="ai")
    assert out["ok"] is False
    assert any("os.system" in e for e in out["errors"])


def test_validate_code_forbidden_allowed_for_humans(temp_repo):
    src = ("import os\n"
           "async def run(state, **kw):\n"
           "    os.system('ls')\n"
           "    return {}\n")
    out = dev_agent.validate_code_py(src, author="human")
    assert out["ok"] is True


# ── atomic save + snapshot + rollback ──────────────────────────────

def _valid_code():
    return ("async def run(state, *, text='', **kw):\n"
            "    return {'reply': f'echo: {text}'}\n")


def test_atomic_save_fresh_neuron(temp_repo):
    conf = {"name": "echo_demo", "description": "demo"}
    out = dev_agent.atomic_save_neuro("echo_demo", conf, _valid_code())
    assert out["ok"] is True
    assert out["stage"] == "saved"
    assert out["snapshot"] is None   # no prior version

    target = temp_repo / "neuros" / "echo_demo"
    assert (target / "conf.json").exists()
    assert (target / "code.py").exists()
    # valid JSON written
    loaded = json.loads((target / "conf.json").read_text())
    assert loaded["name"] == "echo_demo"


def test_atomic_save_snapshot_on_overwrite(temp_repo):
    conf = {"name": "demo_a", "description": "v1"}
    dev_agent.atomic_save_neuro("demo_a", conf, _valid_code())

    # Second save w/ different content — should snapshot v1
    conf2 = {"name": "demo_a", "description": "v2"}
    code2 = _valid_code().replace("echo:", "v2:")
    out = dev_agent.atomic_save_neuro("demo_a", conf2, code2)
    assert out["ok"] is True
    assert out["snapshot"] is not None
    assert Path(out["snapshot"]).exists()
    assert (Path(out["snapshot"]) / "conf.json").exists()


def test_atomic_save_fails_schema_before_write(temp_repo):
    """Schema errors must fail before ANY file touched."""
    target = temp_repo / "neuros" / "bad"
    out = dev_agent.atomic_save_neuro("bad", {"name": "bad"},
                                       _valid_code())
    assert out["ok"] is False
    assert out["stage"] == "schema"
    assert not target.exists() or not (target / "conf.json").exists()


def test_atomic_save_fails_syntax_before_write(temp_repo):
    conf = {"name": "broken", "description": "x"}
    out = dev_agent.atomic_save_neuro("broken", conf, "def run(:\n")
    assert out["ok"] is False
    assert out["stage"] == "syntax"
    target = temp_repo / "neuros" / "broken"
    assert not target.exists() or not (target / "code.py").exists()


def test_atomic_save_rejects_name_mismatch(temp_repo):
    """conf.name must match folder name."""
    conf = {"name": "alpha", "description": "x"}
    out = dev_agent.atomic_save_neuro("beta", conf, _valid_code())
    assert out["ok"] is False
    assert out["stage"] == "schema"
    assert any("beta" in e or "alpha" in e for e in out["errors"])


def test_rollback_restores_prior_version(temp_repo):
    # v1
    dev_agent.atomic_save_neuro("roll_me",
                                 {"name": "roll_me", "description": "v1"},
                                 _valid_code())
    # v2
    dev_agent.atomic_save_neuro("roll_me",
                                 {"name": "roll_me", "description": "v2"},
                                 _valid_code().replace("echo:", "v2:"))

    target = temp_repo / "neuros" / "roll_me"
    assert "v2" in (target / "conf.json").read_text()

    # Rollback
    out = dev_agent.rollback_neuro("roll_me")
    assert out["ok"] is True
    assert "conf.json" in out["restored_files"]
    # Now v1 should be live
    assert "v1" in (target / "conf.json").read_text()


def test_rollback_no_snapshots_errors(temp_repo):
    out = dev_agent.rollback_neuro("never_saved")
    assert out["ok"] is False


def test_list_snapshots(temp_repo):
    for v in ("a", "b", "c"):
        dev_agent.atomic_save_neuro("ls_demo",
                                     {"name": "ls_demo", "description": v},
                                     _valid_code())
    snaps = dev_agent.list_snapshots("ls_demo")
    # 3 saves = 2 prior versions snapshotted (the very first had nothing to snap)
    assert len(snaps) == 2


def test_snapshot_rotation(temp_repo, monkeypatch):
    """Older snapshots auto-pruned beyond the cap."""
    monkeypatch.setattr(dev_agent, "MAX_SNAPSHOTS_PER_NEURON", 3)
    for i in range(6):
        dev_agent.atomic_save_neuro(
            "rot_demo",
            {"name": "rot_demo", "description": f"v{i}"},
            _valid_code(),
        )
    snaps = dev_agent.list_snapshots("rot_demo")
    assert len(snaps) <= 3
