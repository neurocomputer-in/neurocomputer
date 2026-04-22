"""Tests for the dev_pipeline neuro — bridge to core.dev_agent."""
import pytest
from pathlib import Path
from core.neuro_factory import NeuroFactory
from core import dev_agent


@pytest.fixture
def factory(tmp_path, monkeypatch):
    neuros_src = tmp_path / "neuros"
    snaps = tmp_path / ".neuros_history"
    neuros_src.mkdir()
    monkeypatch.setattr(dev_agent, "NEUROS_DIR", neuros_src)
    monkeypatch.setattr(dev_agent, "SNAPSHOTS_DIR", snaps)
    # Load the REAL repo so dev_pipeline neuro is registered
    return NeuroFactory(dir="neuros")


async def test_pipeline_validate_ok(factory):
    out = await factory.run("dev_pipeline", {"__cid": "t"},
                            op="validate",
                            conf={"name": "d", "description": "x"},
                            code="async def run(state, **kw):\n    return {}\n")
    assert out["ok"] is True
    assert out["stage"] == "validated"


async def test_pipeline_validate_schema_fail(factory):
    out = await factory.run("dev_pipeline", {"__cid": "t"},
                            op="validate",
                            conf={"description": "missing name"})
    assert out["ok"] is False
    assert out["stage"] == "schema"


async def test_pipeline_validate_syntax_fail(factory):
    out = await factory.run("dev_pipeline", {"__cid": "t"},
                            op="validate",
                            conf={"name": "d", "description": "x"},
                            code="def run(:")
    assert out["ok"] is False
    assert out["stage"] == "syntax"


async def test_pipeline_save_and_rollback_cycle(factory, tmp_path):
    code_v1 = "async def run(state, **kw):\n    return {'v': 1}\n"
    code_v2 = "async def run(state, **kw):\n    return {'v': 2}\n"

    r1 = await factory.run("dev_pipeline", {"__cid": "t"},
                           op="save", neuro_name="cycle_demo",
                           conf={"name": "cycle_demo", "description": "v1"},
                           code=code_v1)
    assert r1["ok"] is True

    r2 = await factory.run("dev_pipeline", {"__cid": "t"},
                           op="save", neuro_name="cycle_demo",
                           conf={"name": "cycle_demo", "description": "v2"},
                           code=code_v2)
    assert r2["ok"] is True
    assert r2["snapshot"] is not None

    # Listing shows 1 snapshot (v1 preserved before v2 write)
    r3 = await factory.run("dev_pipeline", {"__cid": "t"},
                           op="list_snapshots", neuro_name="cycle_demo")
    assert r3["ok"] is True
    assert len(r3["snapshots"]) == 1

    # Rollback
    r4 = await factory.run("dev_pipeline", {"__cid": "t"},
                           op="rollback", neuro_name="cycle_demo")
    assert r4["ok"] is True
    assert "conf.json" in r4["restored_files"]

    # Live conf is now v1 again
    target = dev_agent.NEUROS_DIR / "cycle_demo"
    conf_text = (target / "conf.json").read_text()
    assert "v1" in conf_text and "v2" not in conf_text


async def test_pipeline_save_rejects_dangerous_code_by_default(factory):
    bad = ("import os\nasync def run(state, **kw):\n"
           "    os.system('rm -rf /')\n"
           "    return {}\n")
    out = await factory.run("dev_pipeline", {"__cid": "t"},
                            op="save", neuro_name="dangerous",
                            conf={"name": "dangerous", "description": "x"},
                            code=bad)
    assert out["ok"] is False
    assert out["stage"] == "syntax"
    assert any("os.system" in e for e in out["errors"])


async def test_pipeline_unknown_op(factory):
    out = await factory.run("dev_pipeline", {"__cid": "t"}, op="nonsense")
    assert out["ok"] is False
    assert any("unknown op" in e for e in out["errors"])
