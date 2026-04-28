"""Memory backend and Neuro registry."""
from neurolang import neuro, Memory, default_registry, register
from neurolang.stdlib import memory_neuros


def test_local_memory_basic():
    mem = Memory.discrete()
    mem.set("foo", 42)
    assert mem.get("foo") == 42
    assert mem.has("foo")
    mem.delete("foo")
    assert not mem.has("foo")


def test_memory_neuros_in_flow():
    @neuro(effect="memory")
    def store_double(value: int) -> int:
        return memory_neuros.store(value * 2, key="result")

    mem = Memory.discrete()
    flow = store_double
    flow.run(7, memory=mem)
    assert mem.get("result") == 14


def test_neuro_decorator_registers_by_default():
    @neuro
    def some_unique_neuro_name_xyz(x):
        return x

    assert any(
        n.name.endswith("some_unique_neuro_name_xyz") for n in default_registry
    )


def test_registry_search():
    @neuro
    def findable_unique_marker_abc(x):
        """A test neuro with a distinctive description."""
        return x

    hits = default_registry.search("findable_unique_marker_abc")
    assert len(hits) >= 1


def test_registry_catalog_shape():
    catalog = default_registry.catalog()
    assert isinstance(catalog, list)
    if catalog:
        sample = catalog[0]
        for key in ("name", "kind", "effects", "description"):
            assert key in sample
