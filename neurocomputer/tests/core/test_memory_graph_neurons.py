"""Tests for memory_graph + memory_recall_keyword + memory_layer_identity neuros."""
import os
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_GRAPH_DB", str(tmp_path / "g.db"))
    return NeuroFactory(dir="neuros")


async def test_memory_graph_add_and_list(factory):
    state = {"__cid": "t"}
    out = await factory.run("memory_graph", state, op="add_node",
                            kind="fact", content="Pluto reclassified 2006.")
    assert out["ok"] is True
    nid = out["id"]

    out = await factory.run("memory_graph", state, op="get_node", node_id=nid)
    assert out["ok"] is True
    assert "Pluto" in out["node"]["content"]

    out = await factory.run("memory_graph", state, op="list_nodes", kind="fact")
    assert len(out["items"]) == 1


async def test_memory_graph_search(factory):
    state = {"__cid": "t"}
    for content in ("Gradient descent is optimization.",
                    "Newton uses second-order information.",
                    "Learning rate scales the gradient."):
        await factory.run("memory_graph", state, op="add_node",
                          kind="fact", content=content)

    out = await factory.run("memory_graph", state, op="search", query="gradient")
    assert len(out["items"]) == 2


async def test_memory_graph_hyperedge(factory):
    state = {"__cid": "t"}
    alice = (await factory.run("memory_graph", state, op="add_node",
                               kind="entity", content="Alice"))["id"]
    bob = (await factory.run("memory_graph", state, op="add_node",
                             kind="entity", content="Bob"))["id"]
    project = (await factory.run("memory_graph", state, op="add_node",
                                 kind="project", content="Neuro"))["id"]
    out = await factory.run("memory_graph", state, op="add_edge",
                            nodes=[alice, bob, project],
                            roles=["attendee", "attendee", "context"],
                            edge_type="meeting")
    assert out["ok"] is True

    out = await factory.run("memory_graph", state, op="neighbors",
                            node_id=alice, edge_type="meeting")
    contents = {n["node"]["content"] for n in out["items"]}
    assert contents == {"Bob", "Neuro"}


async def test_memory_recall_keyword(factory):
    state = {"__cid": "t"}
    # Seed graph
    await factory.run("memory_graph", state, op="add_node",
                      kind="fact", content="Gradient descent is an optimizer.")
    await factory.run("memory_graph", state, op="add_node",
                      kind="fact", content="Learning rate is a scalar.")

    out = await factory.run("memory_recall_keyword", state,
                            query="gradient", top_k=5)
    assert "Relevant notes from memory:" in out["text"]
    assert "gradient" in out["text"].lower()
    assert out["tokens"] > 0


async def test_memory_layer_identity_flat_file(tmp_path, monkeypatch):
    # Create a fake L0 file
    mem_dir = tmp_path / "mem"
    mem_dir.mkdir()
    (mem_dir / "l0.md").write_text("I am Neuro. User is Gopal.\n")
    monkeypatch.chdir(tmp_path)  # so default path mem/l0.md resolves here

    f = NeuroFactory(dir=os.path.join(os.path.dirname(__file__), "..", "..", "neuros"))
    out = await f.run("memory_layer_identity", {"__cid": "t"})
    assert out["ok"] is True
    assert "Neuro" in out["text"]


async def test_memory_layer_identity_missing_file_graceful(factory):
    out = await factory.run("memory_layer_identity", {"__cid": "t"},
                            path="/nonexistent/file.md")
    assert out["ok"] is False
    assert out["text"] == ""


async def test_memory_graph_kinds_in_describe(factory):
    rich = {e["name"]: e for e in factory.describe()}
    assert rich["memory_graph"]["kind"] == "memory.store"
    assert rich["memory_graph"]["kind_namespace"] == "memory"
    assert rich["memory_recall_keyword"]["kind"] == "memory.recall"
    assert rich["memory_layer_identity"]["kind"] == "memory.layer"
