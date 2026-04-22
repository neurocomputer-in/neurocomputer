"""memory — bridge from the neuro protocol to core.memory.MemoryStore."""
import os
from core.memory import MemoryStore


# Path-keyed cache so changing NEURO_MEMORY_DB (per-test, per-deployment)
# picks up the new path without requiring a module reload.
_stores: dict = {}


def _get_store():
    path = os.environ.get("NEURO_MEMORY_DB", "agent_memory.db")
    if path not in _stores:
        _stores[path] = MemoryStore(path=path)
    return _stores[path]


async def run(state, *, op, key=None, value=None, prefix=None, query=None,
              top_k=5, scope="agent", ttl=None, caller=None, **_):
    s = _get_store()
    agent_id = state.get("__agent_id") or "neuro"
    # Caller resolution: explicit kwarg wins (for workflow-level keys),
    # then state["__caller_neuro"] (per-call context), then "shared".
    if caller is None:
        caller = state.get("__caller_neuro") or "shared"

    if op == "read":
        r = s.read(scope, agent_id, caller, key)
        return r or {"value": None}
    if op == "write":
        return s.write(scope, agent_id, caller, key, value, ttl_seconds=ttl)
    if op == "delete":
        return s.delete(scope, agent_id, caller, key)
    if op == "list":
        return {"items": s.list(scope, agent_id, caller, prefix or "")}
    if op == "search":
        return {"items": s.search(scope, agent_id, caller, query, top_k=top_k)}
    return {"ok": False, "error": f"unknown op {op!r}"}
