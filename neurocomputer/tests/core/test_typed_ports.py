import pathlib
import textwrap
import pytest
from core.neuro_factory import NeuroFactory


async def test_string_form_ports_normalized(tmp_path):
    root = tmp_path / "neuros"
    d = root / "echo_old"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(
        '{"name":"echo_old","description":"","inputs":["text"],"outputs":["reply"]}'
    )
    (d / "code.py").write_text(
        "async def run(state, *, text):\n    return {'reply': text}\n"
    )

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    assert rich["echo_old"]["inputs"] == [
        {"name": "text", "type": "any", "description": "", "optional": False}
    ]
    assert rich["echo_old"]["outputs"] == [
        {"name": "reply", "type": "any", "description": "", "optional": False}
    ]


async def test_object_form_ports_passthrough(tmp_path):
    root = tmp_path / "neuros"
    d = root / "summarize"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(textwrap.dedent("""
        {
          "name": "summarize",
          "description": "",
          "inputs":  [{"name":"text","type":"str","description":"body"}],
          "outputs": [{"name":"summary","type":"str"}],
          "category": "text.nlp",
          "icon":     "sparkles",
          "color":    "#7c3aed",
          "summary_md": "Condenses text."
        }
    """))
    (d / "code.py").write_text(
        "async def run(state, *, text):\n    return {'summary': text[:10]}\n"
    )

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    e = rich["summarize"]
    assert e["inputs"][0]["type"] == "str"
    assert e["category"] == "text.nlp"
    assert e["summary_md"] == "Condenses text."
    assert e["kind_namespace"] == "skill"
    assert e["kind"] in ("skill.leaf", "skill.flow")


async def test_layout_sidecar_loaded(tmp_path):
    root = tmp_path / "neuros"
    d = root / "flow_a"
    d.mkdir(parents=True)
    (d / "conf.json").write_text('{"name":"flow_a","description":"","inputs":[],"outputs":[]}')
    (d / "code.py").write_text("async def run(state, **kw):\n    return {}\n")
    (d / "layout.json").write_text('{"nodes":{"n0":{"x":10,"y":20}}}')

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    assert rich["flow_a"].get("layout") == {"nodes": {"n0": {"x": 10, "y": 20}}}


async def test_flow_kind_reflected_in_describe(tmp_path):
    root = tmp_path / "neuros"
    (root / "x").mkdir(parents=True)
    (root / "x" / "conf.json").write_text('{"name":"x","inputs":[],"outputs":[]}')
    (root / "x" / "code.py").write_text("async def run(state, **kw):\n    return {}\n")

    (root / "chain").mkdir(parents=True)
    (root / "chain" / "conf.json").write_text(
        '{"name":"chain","kind":"sequential_flow","children":["x"],"uses":["x"],'
        '"inputs":[],"outputs":[]}'
    )

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    assert rich["chain"]["kind"] == "skill.flow.sequential"
    assert rich["chain"]["kind_namespace"] == "skill"
    assert rich["x"]["kind"] == "skill.leaf"
    assert rich["x"]["kind_namespace"] == "skill"
