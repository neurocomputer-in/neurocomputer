"""Tests for memory_categorize + memory_consolidate (Stage 2)."""
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_GRAPH_DB", str(tmp_path / "g.db"))
    return NeuroFactory(dir="neuros")


async def test_categorize_creates_new_when_empty(factory):
    """Empty taxonomy → LLM proposes new category → category node created."""
    class FakeInf:
        async def run(self, state, **kw):
            return {"content":
                '{"use_existing": false, "new_category_name":'
                ' "ml_optimization", "new_category_definition":'
                ' "decisions about optimizers and learning rates"}'}

    state = {"__cid": "t"}
    entry = factory.reg["memory_categorize"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("memory_categorize", state,
                            fact_content="Adam with lr=1e-3 works for small CNNs.")
    assert out["new"] is True
    assert out["category_name"] == "ml_optimization"
    assert out["category_id"].startswith("node-")

    # Category exists in graph
    listed = await factory.run("memory_graph", state,
                               op="list_nodes", kind="category")
    assert len(listed["items"]) == 1
    assert listed["items"][0]["content"] == "ml_optimization"


async def test_categorize_reuses_existing(factory):
    """When a fitting category exists, LLM says use_existing=true."""
    state = {"__cid": "t"}
    # Seed a category
    await factory.run("memory_graph", state, op="add_node",
                      kind="category", content="ml_optimization",
                      props={"def": "optimizer + lr choices"})

    class FakeInf:
        async def run(self, state, **kw):
            return {"content":
                '{"use_existing": true, "category_name": "ml_optimization"}'}

    entry = factory.reg["memory_categorize"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("memory_categorize", state,
                            fact_content="SGD momentum=0.9 for final accuracy.")
    assert out["new"] is False
    assert out["category_name"] == "ml_optimization"

    # No duplicate category created
    listed = await factory.run("memory_graph", state,
                               op="list_nodes", kind="category")
    assert len(listed["items"]) == 1


async def test_categorize_links_fact_via_edge(factory):
    """When fact_id provided, part_of edge is created between fact + category."""
    class FakeInf:
        async def run(self, state, **kw):
            return {"content":
                '{"use_existing": false, "new_category_name":'
                ' "architecture", "new_category_definition": "model shapes"}'}

    state = {"__cid": "t"}
    # Create a fact first
    add = await factory.run("memory_graph", state, op="add_node",
                            kind="fact", content="User prefers ResNet50 for images.")
    fact_id = add["id"]

    entry = factory.reg["memory_categorize"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("memory_categorize", state,
                            fact_content="User prefers ResNet50 for images.",
                            fact_id=fact_id)
    cat_id = out["category_id"]

    # Neighbor walk from fact should reach the category
    nbrs = await factory.run("memory_graph", state,
                             op="neighbors", node_id=fact_id,
                             edge_type="part_of")
    assert len(nbrs["items"]) == 1
    assert nbrs["items"][0]["node"]["id"] == cat_id


async def test_categorize_batch_mode(factory):
    class FakeInf:
        def __init__(self):
            self.calls = 0
        async def run(self, state, **kw):
            self.calls += 1
            return {"content":
                '{"use_existing": false, "new_category_name":'
                ' "cat_' + str(self.calls) + '", "new_category_definition": "..."}'}

    state = {"__cid": "t"}
    entry = factory.reg["memory_categorize"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    # seed two facts
    f1 = (await factory.run("memory_graph", state, op="add_node",
                            kind="fact", content="fact A"))["id"]
    f2 = (await factory.run("memory_graph", state, op="add_node",
                            kind="fact", content="fact B"))["id"]

    out = await factory.run("memory_categorize", state, facts=[
        {"content": "fact A", "id": f1},
        {"content": "fact B", "id": f2},
    ])
    assert out["count"] == 2
    assert len(out["results"]) == 2
    assert all(r["new"] for r in out["results"])


async def test_consolidate_dry_run_returns_suggestions(factory):
    state = {"__cid": "t"}
    # Seed 3 categories, two obvious dupes
    await factory.run("memory_graph", state, op="add_node",
                      kind="category", content="optimizer")
    await factory.run("memory_graph", state, op="add_node",
                      kind="category", content="optimizers")
    await factory.run("memory_graph", state, op="add_node",
                      kind="category", content="architecture")

    class FakeInf:
        async def run(self, state, **kw):
            return {"content":
                '{"merges": [{"from_name": "optimizers",'
                ' "to_name": "optimizer", "reason": "plural duplicate"}]}'}

    entry = factory.reg["memory_consolidate"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("memory_consolidate", state, dry_run=True)
    assert out["dry_run"] is True
    assert out["applied"] == 0
    assert len(out["merges"]) == 1
    assert out["merges"][0]["from_name"] == "optimizers"
    assert out["merges"][0]["to_name"] == "optimizer"

    # All 3 categories still valid
    listed = await factory.run("memory_graph", state,
                               op="list_nodes", kind="category")
    assert len(listed["items"]) == 3


async def test_consolidate_applies_merges_and_invalidates(factory):
    state = {"__cid": "t"}
    # Seed dupe + a fact linked to the loser
    await factory.run("memory_graph", state, op="add_node",
                      kind="category", content="optimizer")
    await factory.run("memory_graph", state, op="add_node",
                      kind="category", content="optimizers")

    class FakeInf:
        async def run(self, state, **kw):
            return {"content":
                '{"merges": [{"from_name": "optimizers",'
                ' "to_name": "optimizer", "reason": "dupe"}]}'}

    entry = factory.reg["memory_consolidate"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("memory_consolidate", state, dry_run=False)
    assert out["dry_run"] is False
    assert out["applied"] == 1

    # Only 1 valid category remains
    listed = await factory.run("memory_graph", state,
                               op="list_nodes", kind="category")
    assert len(listed["items"]) == 1
    assert listed["items"][0]["content"] == "optimizer"


async def test_consolidate_empty_taxonomy_no_op(factory):
    state = {"__cid": "t"}
    out = await factory.run("memory_consolidate", state, dry_run=True)
    assert out["merges"] == []
    assert out["applied"] == 0


async def test_stage2_describe_kinds(factory):
    rich = {e["name"]: e for e in factory.describe()}
    assert rich["memory_categorize"]["kind"] == "memory.categorize"
    assert rich["memory_categorize"]["kind_namespace"] == "memory"
    assert rich["memory_consolidate"]["kind"] == "memory.consolidate"
    assert rich["memory_consolidate"]["kind_namespace"] == "memory"
