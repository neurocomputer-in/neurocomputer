"""MemoryStore — SQLite-backed persistent memory for agents.

Key shape: (scope, agent_id, caller, key). TTL optional per-row.
Spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/03-state-and-memory.md
"""
import json
import os
import sqlite3
import time


SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    scope       TEXT NOT NULL,
    agent_id    TEXT NOT NULL,
    caller      TEXT NOT NULL,
    key         TEXT NOT NULL,
    value_json  TEXT NOT NULL,
    ts          REAL NOT NULL,
    ttl_ts      REAL,
    PRIMARY KEY (scope, agent_id, caller, key)
);
CREATE INDEX IF NOT EXISTS idx_kv_prefix
    ON kv(scope, agent_id, caller, key);
"""


class MemoryStore:
    def __init__(self, path: str = "agent_memory.db"):
        self.path = path
        d = os.path.dirname(path) or "."
        os.makedirs(d, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self):
        return sqlite3.connect(self.path, isolation_level=None)

    @staticmethod
    def _now() -> float:
        return time.time()

    def write(self, scope, agent_id, caller, key, value, ttl_seconds=None):
        now = self._now()
        ttl = (now + ttl_seconds) if ttl_seconds is not None else None
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO kv VALUES (?, ?, ?, ?, ?, ?, ?)",
                (scope, agent_id, caller, key, json.dumps(value), now, ttl),
            )
        return {"ok": True, "ts": now}

    def read(self, scope, agent_id, caller, key):
        now = self._now()
        with self._conn() as c:
            cur = c.execute(
                "SELECT value_json, ts, ttl_ts FROM kv "
                "WHERE scope=? AND agent_id=? AND caller=? AND key=?",
                (scope, agent_id, caller, key),
            )
            row = cur.fetchone()
        if row is None:
            return None
        value_json, ts, ttl_ts = row
        if ttl_ts is not None and ttl_ts <= now:
            self.delete(scope, agent_id, caller, key)
            return None
        return {"value": json.loads(value_json), "meta": {"ts": ts, "ttl": ttl_ts}}

    def delete(self, scope, agent_id, caller, key):
        with self._conn() as c:
            c.execute(
                "DELETE FROM kv "
                "WHERE scope=? AND agent_id=? AND caller=? AND key=?",
                (scope, agent_id, caller, key),
            )
        return {"ok": True}

    def list(self, scope, agent_id, caller, prefix=""):
        now = self._now()
        with self._conn() as c:
            cur = c.execute(
                "SELECT key, value_json, ts, ttl_ts FROM kv "
                "WHERE scope=? AND agent_id=? AND caller=? AND key LIKE ?",
                (scope, agent_id, caller, prefix + "%"),
            )
            items = [
                {"key": k, "value": json.loads(v), "meta": {"ts": ts, "ttl": ttl_ts}}
                for k, v, ts, ttl_ts in cur.fetchall()
                if ttl_ts is None or ttl_ts > now
            ]
        return items

    def search(self, scope, agent_id, caller, query, top_k=5):
        """Naive substring match in key + serialized value. Vector search v2."""
        items = self.list(scope, agent_id, caller, prefix="")
        q = query.lower()
        scored = []
        for it in items:
            hay = (it["key"] + " " + json.dumps(it["value"])).lower()
            if q in hay:
                scored.append(it)
        return scored[:top_k]
