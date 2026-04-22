import inspect
import pytest
from core.base_neuro import BaseNeuro, FnEntry


class LeafNeuro(BaseNeuro):
    async def run(self, state, **kw):
        return {"leaf": True}


async def test_baseneuro_subclass_runs():
    out = await LeafNeuro().run({})
    assert out == {"leaf": True}


async def test_baseneuro_abstract_default_raises():
    """Plain BaseNeuro() with no override and no legacy fn must raise on run."""
    b = BaseNeuro.__new__(BaseNeuro)   # bypass legacy ctor
    b.name = ""
    b._legacy_fn = None
    b._accepted = set()
    b._accepts_var_kw = False
    with pytest.raises(NotImplementedError):
        await b.run({})


async def test_fn_entry_wraps_async_fn():
    async def raw(state, *, text):
        return {"reply": f"x {text}"}
    fe = FnEntry(fn=raw, conf={"name": "t", "inputs": ["text"], "outputs": ["reply"]})
    inst = fe.build_instance()
    out = await inst.run({}, text="hi")
    assert out == {"reply": "x hi"}


async def test_legacy_ctor_still_works():
    """Factory's current shape: BaseNeuro(name, fn, inputs, outputs, desc)."""
    async def fn(state, *, text):
        return {"echo": text}
    n = BaseNeuro("echo", fn, ["text"], ["echo"], "desc")
    out = await n.run({}, text="hi", extra="ignored")
    assert out == {"echo": "hi"}
    assert n.name == "echo"
    assert n.desc == "desc"
