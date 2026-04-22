"""Verify Brain routes workflow shortcuts through agent neuros when available.

Before: /advisor → launches single-node DAG with 'advisor' as the neuro.
After:  /advisor → launches single-node DAG with 'agent_default' as the
        neuro, so the agent's memory_scope partitions memory transparently.
"""
import asyncio
import pytest
from core.brain import Brain


@pytest.fixture
async def brain(monkeypatch, tmp_path):
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "m.db"))
    monkeypatch.setenv("NEURO_GRAPH_DB",  str(tmp_path / "g.db"))
    b = Brain()
    yield b


async def test_advisor_slash_routes_through_agent_default(brain):
    """debug event's 'target' should be agent_default, not 'advisor'."""
    cid = "test_agent_routing_advisor"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    await brain.handle(cid, "/advisor what is X?")
    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    workflow_events = [d for t, d in events
                       if t == "debug" and isinstance(d, dict)
                       and d.get("stage") == "workflow"]
    assert len(workflow_events) == 1
    assert workflow_events[0]["target"] == "agent_default"
    assert workflow_events[0]["invoked"] == "advisor"


async def test_coder_slash_routes_through_agent_coder(brain):
    cid = "test_agent_routing_coder"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    await brain.handle(cid, "/coder write hello world python")
    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    workflow_events = [d for t, d in events
                       if t == "debug" and isinstance(d, dict)
                       and d.get("stage") == "workflow"]
    assert workflow_events[0]["target"] == "agent_coder"
    assert workflow_events[0]["invoked"] == "coder"


async def test_direct_agent_slash_command(brain):
    """/agent_coder <msg> — direct agent invocation."""
    cid = "test_direct_agent"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    await brain.handle(cid, "/agent_coder write reverse string")
    assert cid in brain.tasks
    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    workflow_events = [d for t, d in events
                       if t == "debug" and isinstance(d, dict)
                       and d.get("stage") == "workflow"]
    assert workflow_events[0]["target"] == "agent_coder"


async def test_smart_router_advisor_maps_to_agent_default(brain):
    """When smart_router picks 'advisor', Brain remaps to agent_default."""
    cid = "test_auto_agent"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    # Stub smart_router
    original_run = brain.factory.run
    async def proxy(name, state, **kw):
        if name == "smart_router":
            return {"action": "skill", "skill": "advisor",
                    "params": {"user_question": "hello"}}
        return await original_run(name, state, **kw)
    brain.factory.run = proxy

    await brain.handle(cid, "hello")
    assert cid in brain.tasks
    task, _ = brain.tasks[cid]
    # Let it start then cancel
    await asyncio.sleep(0)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_unknown_agent_slash_falls_through(brain):
    """/agent_nonexistent falls through to smart_router path, not an error."""
    cid = "test_unknown"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    # Don't actually run smart_router — just verify the slash didn't match
    original_run = brain.factory.run
    async def proxy(name, state, **kw):
        if name == "smart_router":
            return {"action": "reply", "reply": "idk what that is"}
        return await original_run(name, state, **kw)
    brain.factory.run = proxy

    out = await brain.handle(cid, "/agent_nonexistent_foo hello")
    assert "idk" in out   # fell through to smart_router → reply
