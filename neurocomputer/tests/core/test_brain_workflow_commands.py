"""Tests for Brain's /advisor and /coder slash-command routing.

These integration tests validate that Brain.handle() recognizes the
workflow slash commands, builds the correct single-node DAG, and
launches via _launch. LLM calls are not exercised — the task is
created and set aside; we just verify dispatch shape.
"""
import asyncio
import pytest
from core.brain import Brain


async def _collect_events(cid, events, topic, data):
    events.append((topic, data))


@pytest.fixture
async def brain(monkeypatch, tmp_path):
    # Isolate any memory writes a launched task might do.
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "m.db"))
    monkeypatch.setenv("NEURO_GRAPH_DB",  str(tmp_path / "g.db"))
    b = Brain()
    # Give the hot-reload watcher task a moment to settle; we won't run it.
    yield b


async def test_advisor_slash_command_dispatches(brain):
    cid = "test_advisor_cmd"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    reply = await brain.handle(cid, "/advisor what is gradient descent?")
    assert reply.startswith("🧠")
    # Routes via agent_default (memory-partitioned) or falls back to advisor.
    assert "advisor" in reply.lower() or "agent_default" in reply.lower()
    # A task should be stashed for this cid
    assert cid in brain.tasks
    # Cancel the task (we don't want to actually run an LLM round)
    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    topics = [t for t, _ in events]
    assert any(t == "debug" for t in topics)


async def test_coder_slash_command_dispatches(brain):
    cid = "test_coder_cmd"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    reply = await brain.handle(cid, "/coder write python reverse string")
    assert reply.startswith("🧠")
    assert "coder" in reply.lower()
    assert cid in brain.tasks
    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_empty_slash_workflow_returns_usage(brain):
    cid = "test_usage"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    reply = await brain.handle(cid, "/advisor")
    assert "usage" in reply.lower()
    # No task started for empty usage
    assert cid not in brain.tasks or brain.tasks[cid][0].done()


async def test_plain_message_does_not_trigger_workflow(brain):
    """Messages without the slash prefix go through the normal flow,
    not the workflow slash dispatcher."""
    cid = "test_plain"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    # Plain message — should not emit the workflow debug stage.
    # (It will go to smart_router which requires LLM; we don't await that.)
    try:
        await asyncio.wait_for(
            brain.handle(cid, "hello"), timeout=0.1
        )
    except asyncio.TimeoutError:
        pass
    except Exception:
        pass

    # Must NOT have dispatched via the workflow slash path
    for t, d in events:
        if t == "debug" and isinstance(d, dict) and d.get("stage") == "workflow":
            pytest.fail("Plain 'hello' should not go through workflow slash path")
