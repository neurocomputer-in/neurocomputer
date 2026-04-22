import pytest
from core.instance_pool import InstancePool
from core.base_neuro import BaseNeuro


class Counter(BaseNeuro):
    async def run(self, state, **kw):
        self.count = getattr(self, "count", 0) + 1
        return {"count": self.count}


class DummyFactory:
    def __init__(self):
        self.reg = {}


def _entry(name, cls, scope):
    from types import SimpleNamespace
    return SimpleNamespace(name=name, cls=cls, scope=scope,
                           conf={"uses": []}, is_class=True)


async def test_session_scope_pools_per_cid():
    pool = InstancePool(DummyFactory())
    entry = _entry("counter", Counter, scope="session")

    i1 = await pool.get(entry, {"__cid": "A"})
    i2 = await pool.get(entry, {"__cid": "A"})
    i3 = await pool.get(entry, {"__cid": "B"})

    assert i1 is i2
    assert i1 is not i3


async def test_singleton_scope_reuses_across_all_state():
    pool = InstancePool(DummyFactory())
    entry = _entry("counter", Counter, scope="singleton")

    i1 = await pool.get(entry, {"__cid": "A"})
    i2 = await pool.get(entry, {"__cid": "B"})
    assert i1 is i2


async def test_call_scope_fresh_every_time():
    pool = InstancePool(DummyFactory())
    entry = _entry("counter", Counter, scope="call")

    i1 = await pool.get(entry, {})
    i2 = await pool.get(entry, {})
    assert i1 is not i2


async def test_invalidate_tears_down_and_drops():
    teardown_called = {"n": 0}

    class WithTeardown(BaseNeuro):
        async def run(self, state, **kw):
            return {}
        async def teardown(self):
            teardown_called["n"] += 1

    pool = InstancePool(DummyFactory())
    entry = _entry("wd", WithTeardown, scope="session")
    i1 = await pool.get(entry, {"__cid": "A"})
    await pool.invalidate("wd")
    i2 = await pool.get(entry, {"__cid": "A"})

    assert teardown_called["n"] == 1
    assert i1 is not i2
