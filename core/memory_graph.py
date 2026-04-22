"""MemoryGraph — typed property hypergraph with temporal validity.

Per `docs/MEMORY_ARCHITECTURE.md` §2 (Storage Substrate). This is the
Stage 0 slice: SQLite-backed, schema supports n-ary edges and time
travel from day one, but v1 uses only binary edges + keyword retrieval.
Vector indexing, PPR walks, and emergent taxonomy live in later stages.

Tables:
  nodes   — every memory item (fact, entity, category, turn, neuro, index)
  edges   — typed relationships; `nodes` is a JSON array of ids so an
            edge can link 2..N nodes (hyperedge), `roles` parallel.

Temporal discipline: nothing is destructively deleted. `invalidate()`
closes `valid_to = now`. Queries default to "currently valid" slice.

Keyword retrieval (Stage 0): simple SQL LIKE on nodes.content, with
optional `kind` filter + recency boost via `access_count`.
"""
import json
import os
import sqlite3
import time
import uuid
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
    id             TEXT PRIMARY KEY,
    kind           TEXT NOT NULL,
    content        TEXT,
    props          TEXT NOT NULL,
    valid_from     REAL NOT NULL,
    valid_to       REAL,
    created_at     REAL NOT NULL,
    access_count   INTEGER DEFAULT 0,
    last_accessed  REAL
);
CREATE INDEX IF NOT EXISTS idx_nodes_kind     ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_valid    ON nodes(valid_to);
CREATE INDEX IF NOT EXISTS idx_nodes_content  ON nodes(content);

CREATE TABLE IF NOT EXISTS edges (
    id          TEXT PRIMARY KEY,
    nodes       TEXT NOT NULL,
    roles       TEXT NOT NULL,
    type        TEXT NOT NULL,
    weight      REAL DEFAULT 1.0,
    props       TEXT,
    valid_from  REAL NOT NULL,
    valid_to    REAL,
    created_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_edges_type  ON edges(type);
CREATE INDEX IF NOT EXISTS idx_edges_valid ON edges(valid_to);
"""


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


class MemoryGraph:
    def __init__(self, path: str = "agent_graph.db"):
        self.path = path
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self):
        return sqlite3.connect(self.path, isolation_level=None)

    # ── nodes ──────────────────────────────────────────────────────

    def add_node(self, kind: str, content: Optional[str] = None,
                 props: Optional[dict] = None,
                 valid_from: Optional[float] = None,
                 node_id: Optional[str] = None) -> str:
        nid = node_id or _new_id("node")
        now = _now()
        vf = valid_from if valid_from is not None else now
        with self._conn() as c:
            c.execute(
                "INSERT INTO nodes (id, kind, content, props, valid_from, valid_to, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (nid, kind, content, json.dumps(props or {}), vf, None, now),
            )
        return nid

    def get_node(self, node_id: str) -> Optional[dict]:
        now = _now()
        with self._conn() as c:
            cur = c.execute(
                "SELECT id, kind, content, props, valid_from, valid_to, "
                "created_at, access_count, last_accessed "
                "FROM nodes WHERE id = ?", (node_id,)
            )
            row = cur.fetchone()
        if row is None:
            return None
        node = _row_to_node(row)
        if node["valid_to"] is not None and node["valid_to"] <= now:
            return None
        self._bump_access(node_id, now)
        node["access_count"] += 1
        node["last_accessed"] = now
        return node

    def list_nodes(self, kind: Optional[str] = None,
                   content_like: Optional[str] = None,
                   limit: int = 50) -> list:
        now = _now()
        q = ["SELECT id, kind, content, props, valid_from, valid_to, "
             "created_at, access_count, last_accessed FROM nodes",
             "WHERE (valid_to IS NULL OR valid_to > ?)"]
        args = [now]
        if kind is not None:
            q.append("AND kind = ?")
            args.append(kind)
        if content_like is not None:
            q.append("AND content LIKE ?")
            args.append(f"%{content_like}%")
        q.append("ORDER BY access_count DESC, created_at DESC LIMIT ?")
        args.append(limit)
        with self._conn() as c:
            cur = c.execute(" ".join(q), args)
            return [_row_to_node(r) for r in cur.fetchall()]

    def invalidate_node(self, node_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE nodes SET valid_to = ? WHERE id = ? AND valid_to IS NULL",
                      (_now(), node_id))

    def _bump_access(self, node_id: str, now: float) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE nodes SET access_count = access_count + 1, "
                "last_accessed = ? WHERE id = ?", (now, node_id)
            )

    # ── edges ──────────────────────────────────────────────────────

    def add_edge(self, nodes: list, roles: list, edge_type: str,
                 weight: float = 1.0, props: Optional[dict] = None,
                 valid_from: Optional[float] = None,
                 edge_id: Optional[str] = None) -> str:
        if len(nodes) != len(roles):
            raise ValueError("nodes and roles must be same length (n-ary edge)")
        eid = edge_id or _new_id("edge")
        now = _now()
        vf = valid_from if valid_from is not None else now
        with self._conn() as c:
            c.execute(
                "INSERT INTO edges (id, nodes, roles, type, weight, props, "
                "valid_from, valid_to, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (eid, json.dumps(nodes), json.dumps(roles), edge_type,
                 weight, json.dumps(props or {}), vf, None, now),
            )
        return eid

    def neighbors(self, node_id: str, edge_type: Optional[str] = None,
                  limit: int = 50) -> list:
        now = _now()
        q = ["SELECT id, nodes, roles, type, weight, props, valid_from, "
             "valid_to, created_at FROM edges",
             "WHERE (valid_to IS NULL OR valid_to > ?)"]
        args = [now]
        if edge_type is not None:
            q.append("AND type = ?")
            args.append(edge_type)
        q.append("LIMIT ?")
        args.append(limit)
        with self._conn() as c:
            cur = c.execute(" ".join(q), args)
            rows = cur.fetchall()

        out = []
        for row in rows:
            edge = _row_to_edge(row)
            if node_id in edge["nodes"]:
                for other in edge["nodes"]:
                    if other != node_id:
                        n = self.get_node(other)
                        if n is not None:
                            out.append({"node": n, "edge": edge})
        return out

    def invalidate_edge(self, edge_id: str) -> None:
        with self._conn() as c:
            c.execute("UPDATE edges SET valid_to = ? WHERE id = ? AND valid_to IS NULL",
                      (_now(), edge_id))

    # ── keyword retrieval (Stage 0) ────────────────────────────────

    def search_keyword(self, query: str,
                       kind: Optional[str] = None,
                       top_k: int = 10) -> list:
        """Simple case-insensitive substring match ranked by access_count desc."""
        now = _now()
        q = ["SELECT id, kind, content, props, valid_from, valid_to, "
             "created_at, access_count, last_accessed FROM nodes",
             "WHERE (valid_to IS NULL OR valid_to > ?)",
             "AND content IS NOT NULL",
             "AND LOWER(content) LIKE LOWER(?)"]
        args = [now, f"%{query}%"]
        if kind is not None:
            q.append("AND kind = ?")
            args.append(kind)
        q.append("ORDER BY access_count DESC, last_accessed DESC LIMIT ?")
        args.append(top_k)
        with self._conn() as c:
            cur = c.execute(" ".join(q), args)
            return [_row_to_node(r) for r in cur.fetchall()]

    # ── introspection ──────────────────────────────────────────────

    def stats(self) -> dict:
        with self._conn() as c:
            n = c.execute("SELECT COUNT(*) FROM nodes WHERE valid_to IS NULL").fetchone()[0]
            e = c.execute("SELECT COUNT(*) FROM edges WHERE valid_to IS NULL").fetchone()[0]
            per_kind = dict(c.execute(
                "SELECT kind, COUNT(*) FROM nodes WHERE valid_to IS NULL GROUP BY kind"
            ).fetchall())
        return {"nodes": n, "edges": e, "nodes_by_kind": per_kind}


def _row_to_node(row) -> dict:
    (nid, kind, content, props, valid_from, valid_to,
     created_at, access_count, last_accessed) = row
    return {
        "id":            nid,
        "kind":          kind,
        "content":       content,
        "props":         json.loads(props) if props else {},
        "valid_from":    valid_from,
        "valid_to":      valid_to,
        "created_at":    created_at,
        "access_count":  access_count or 0,
        "last_accessed": last_accessed,
    }


def _row_to_edge(row) -> dict:
    (eid, nodes_json, roles_json, etype, weight, props,
     valid_from, valid_to, created_at) = row
    return {
        "id":         eid,
        "nodes":      json.loads(nodes_json),
        "roles":      json.loads(roles_json),
        "type":       etype,
        "weight":     weight,
        "props":      json.loads(props) if props else {},
        "valid_from": valid_from,
        "valid_to":   valid_to,
        "created_at": created_at,
    }
