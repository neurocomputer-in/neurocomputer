import pathlib
import textwrap
import pytest
from core.neuro_factory import NeuroFactory


async def test_factory_loads_class_neuro(tmp_path: pathlib.Path):
    root = tmp_path / "neuros"
    d = root / "greet"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(
        '{"name":"greet","description":"","inputs":[],"outputs":[],"scope":"session"}'
    )
    (d / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Greet(BaseNeuro):
            async def run(self, state, **kw):
                return {"hello": True}
    """))

    f = NeuroFactory(dir=str(root))
    out = await f.run("greet", {"__cid": "t"})
    assert out == {"hello": True}


async def test_factory_injects_uses_deps(tmp_path: pathlib.Path):
    root = tmp_path / "neuros"
    (root / "a").mkdir(parents=True)
    (root / "a" / "conf.json").write_text(
        '{"name":"a","description":"","inputs":[],"outputs":[]}'
    )
    (root / "a" / "code.py").write_text(
        "async def run(state, **kw):\n    return {'from_a': 1}\n"
    )

    (root / "parent").mkdir(parents=True)
    (root / "parent" / "conf.json").write_text(
        '{"name":"parent","description":"","inputs":[],"outputs":[],"uses":["a"]}'
    )
    (root / "parent" / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Parent(BaseNeuro):
            uses = ["a"]
            async def run(self, state, **kw):
                out = await self.a.run(state)
                return {"parent_got": out["from_a"]}
    """))

    f = NeuroFactory(dir=str(root))
    out = await f.run("parent", {"__cid": "t"})
    assert out == {"parent_got": 1}


async def test_factory_synthesizes_sequential_flow_from_conf(tmp_path):
    root = tmp_path / "neuros"
    for n in ("x", "y"):
        (root / n).mkdir(parents=True)
        (root / n / "conf.json").write_text(
            f'{{"name":"{n}","description":"","inputs":[],"outputs":[]}}'
        )
        (root / n / "code.py").write_text(
            f"async def run(state, **kw):\n    return {{'{n}': True}}\n"
        )
    (root / "chain").mkdir(parents=True)
    (root / "chain" / "conf.json").write_text(
        '{"name":"chain","description":"","inputs":[],"outputs":[],'
        '"kind":"sequential_flow","children":["x","y"],"uses":["x","y"]}'
    )

    f = NeuroFactory(dir=str(root))
    out = await f.run("chain", {"__cid": "t"})
    assert out == {"x": True, "y": True}


async def test_class_reload_teardown_and_rebuild(tmp_path):
    root = tmp_path / "neuros"
    d = root / "incr"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(
        '{"name":"incr","description":"","inputs":[],"outputs":[],"scope":"singleton"}'
    )
    (d / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Incr(BaseNeuro):
            scope = "singleton"
            async def setup(self):
                self.n = 100
            async def teardown(self):
                self.n = -1
            async def run(self, state, **kw):
                self.n += 1
                return {"n": self.n}
    """))

    f = NeuroFactory(dir=str(root))
    out1 = await f.run("incr", {})
    assert out1 == {"n": 101}
    out2 = await f.run("incr", {})
    assert out2 == {"n": 102}

    # Rewrite the neuro's code — factory should tear down old instance.
    (d / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Incr(BaseNeuro):
            scope = "singleton"
            async def setup(self):
                self.n = 0
            async def run(self, state, **kw):
                self.n += 10
                return {"n": self.n}
    """))
    f._load(d / "conf.json")
    import asyncio as _a; await _a.sleep(0.05)

    out3 = await f.run("incr", {})
    assert out3 == {"n": 10}
