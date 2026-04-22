"""memory_graph — bridge from the neuro protocol to core.memory_graph.MemoryGraph."""
import os
from core.memory_graph import MemoryGraph


# Path-keyed cache — lets NEURO_GRAPH_DB env override for tests / deploys.
_graphs: dict = {}


def _get_graph():
    path = os.environ.get("NEURO_GRAPH_DB", "agent_graph.db")
    if path not in _graphs:
        _graphs[path] = MemoryGraph(path=path)
    return _graphs[path]


async def run(state, *, op, node_id=None, edge_id=None, kind=None,
              content=None, props=None, nodes=None, roles=None,
              edge_type=None, weight=1.0, query=None, content_like=None,
              top_k=10, limit=50, **_):
    g = _get_graph()

    if op == "add_node":
        nid = g.add_node(kind=kind or "fact", content=content, props=props)
        return {"id": nid, "ok": True}

    if op == "get_node":
        node = g.get_node(node_id)
        return {"node": node, "ok": node is not None}

    if op == "list_nodes":
        items = g.list_nodes(kind=kind, content_like=content_like, limit=limit)
        return {"items": items, "ok": True}

    if op == "add_edge":
        if not nodes or not roles or not edge_type:
            return {"ok": False, "error": "add_edge requires nodes, roles, edge_type"}
        eid = g.add_edge(nodes=nodes, roles=roles, edge_type=edge_type, weight=weight, props=props)
        return {"id": eid, "ok": True}

    if op == "neighbors":
        items = g.neighbors(node_id, edge_type=edge_type, limit=limit)
        return {"items": items, "ok": True}

    if op == "search":
        items = g.search_keyword(query or "", kind=kind, top_k=top_k)
        return {"items": items, "ok": True}

    if op == "invalidate_node":
        g.invalidate_node(node_id)
        return {"ok": True}

    if op == "invalidate_edge":
        g.invalidate_edge(edge_id)
        return {"ok": True}

    if op == "stats":
        return {"stats": g.stats(), "ok": True}

    return {"ok": False, "error": f"unknown op {op!r}"}
