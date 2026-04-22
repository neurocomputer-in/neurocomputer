"""Tests for MemoryGraph — Stage 0 of MEMORY_ARCHITECTURE.md."""
import pytest
from core.memory_graph import MemoryGraph


def test_add_and_get_node(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    nid = g.add_node(kind="fact", content="Pluto was reclassified in 2006.",
                     props={"source": "wiki"})
    node = g.get_node(nid)
    assert node["id"] == nid
    assert node["kind"] == "fact"
    assert "Pluto" in node["content"]
    assert node["props"] == {"source": "wiki"}
    assert node["valid_to"] is None
    # access_count increments on get
    assert node["access_count"] == 1


def test_list_nodes_by_kind(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    g.add_node(kind="fact", content="A")
    g.add_node(kind="fact", content="B")
    g.add_node(kind="entity", content="Alice")
    facts = g.list_nodes(kind="fact")
    assert {f["content"] for f in facts} == {"A", "B"}
    entities = g.list_nodes(kind="entity")
    assert entities[0]["content"] == "Alice"


def test_keyword_search(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    g.add_node(kind="fact", content="Gradient descent is an optimization algorithm.")
    g.add_node(kind="fact", content="Newton's method uses second-order information.")
    g.add_node(kind="fact", content="Learning rate scales the gradient step.")

    hits = g.search_keyword("gradient")
    assert len(hits) == 2
    assert all("gradient" in h["content"].lower() for h in hits)


def test_keyword_search_ranks_by_access(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    n1 = g.add_node(kind="fact", content="fact one about topic X")
    n2 = g.add_node(kind="fact", content="fact two about topic X")
    # Bump n2's access count
    for _ in range(3):
        g.get_node(n2)

    hits = g.search_keyword("topic X")
    assert hits[0]["id"] == n2    # higher access_count ranks first


def test_add_binary_edge_and_neighbors(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    alice = g.add_node(kind="entity", content="Alice")
    meeting = g.add_node(kind="event", content="kickoff meeting")
    eid = g.add_edge(nodes=[alice, meeting],
                     roles=["attendee", "event"],
                     edge_type="attended")
    assert eid.startswith("edge-")
    out = g.neighbors(alice, edge_type="attended")
    assert len(out) == 1
    assert out[0]["node"]["content"] == "kickoff meeting"
    assert out[0]["edge"]["type"] == "attended"


def test_add_hyperedge_nary(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    alice   = g.add_node(kind="entity", content="Alice")
    bob     = g.add_node(kind="entity", content="Bob")
    project = g.add_node(kind="project", content="Neuro")
    date    = g.add_node(kind="date", content="2026-04-21")
    eid = g.add_edge(nodes=[alice, bob, project, date],
                     roles=["attendee", "attendee", "context", "when"],
                     edge_type="meeting")

    # alice's neighbor walk should surface bob + project + date
    neighbors = g.neighbors(alice, edge_type="meeting")
    contents = {n["node"]["content"] for n in neighbors}
    assert contents == {"Bob", "Neuro", "2026-04-21"}


def test_invalidate_node_excludes_from_queries(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    n = g.add_node(kind="fact", content="will be superseded")
    assert g.get_node(n) is not None

    g.invalidate_node(n)
    assert g.get_node(n) is None
    # list/search exclude invalid nodes too
    assert g.list_nodes(kind="fact") == []
    assert g.search_keyword("superseded") == []


def test_stats_summary(tmp_path):
    g = MemoryGraph(path=str(tmp_path / "g.db"))
    g.add_node(kind="fact",   content="A")
    g.add_node(kind="fact",   content="B")
    g.add_node(kind="entity", content="X")
    g.add_edge(nodes=[g.list_nodes(kind="entity")[0]["id"]],
               roles=["subject"], edge_type="trivial")

    s = g.stats()
    assert s["nodes"] == 3
    assert s["edges"] == 1
    assert s["nodes_by_kind"] == {"fact": 2, "entity": 1}
