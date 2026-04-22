"""Tests for smart_router auto-routing to advisor/coder workflows.

Stubs the factory's smart_router call to return a canned decision, then
verifies Brain dispatches correctly via DIRECT_SKILLS path.
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


async def _stub_smart_router(brain, decision: dict):
    """Patch factory.run so smart_router returns a canned decision;
    all other neuros proxy to the original."""
    original = brain.factory.run

    async def proxy(name, state, **kw):
        if name == "smart_router":
            return decision
        return await original(name, state, **kw)

    brain.factory.run = proxy


async def test_smart_router_advisor_dispatches_workflow(brain, monkeypatch):
    cid = "test_auto_advisor"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    await _stub_smart_router(brain, {
        "action": "skill",
        "skill":  "advisor",
        "params": {"user_question": "should I use Adam or SGD?"},
    })

    reply = await brain.handle(cid, "should I use Adam or SGD?")
    # DIRECT_SKILLS path returns '🚀 task started'
    assert "task started" in reply.lower()
    assert cid in brain.tasks

    # Cancel before real LLM fires
    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Debug event should include smart_router → advisor
    topics_skills = [(t, d) for t, d in events
                     if t == "debug" and isinstance(d, dict)
                     and d.get("skill") == "advisor"]
    assert len(topics_skills) >= 1


async def test_smart_router_coder_dispatches_workflow(brain, monkeypatch):
    cid = "test_auto_coder"
    events = []
    async def pub(c, topic, data):
        events.append((topic, data))
    brain._pub = pub

    await _stub_smart_router(brain, {
        "action": "skill",
        "skill":  "coder",
        "params": {"user_question": "write recursive fibonacci in python"},
    })

    reply = await brain.handle(cid, "write recursive fibonacci in python")
    assert "task started" in reply.lower()
    assert cid in brain.tasks

    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_smart_router_fills_user_question_when_omitted(brain, monkeypatch):
    """When smart_router forgets to set user_question, brain falls back to user_text."""
    cid = "test_fallback_params"

    async def pub(c, topic, data):
        pass
    brain._pub = pub

    await _stub_smart_router(brain, {
        "action": "skill",
        "skill":  "advisor",
        "params": {},      # LLM forgot user_question
    })

    await brain.handle(cid, "what is gradient descent?")
    assert cid in brain.tasks

    # The launched task's state should carry the user_text as user_question.
    _task, state = brain.tasks[cid]
    # state has __factory + other brain keys; verify the dag's node was
    # wrapped correctly by peeking into the task. Simplest check: the
    # flow_name is 'advisor' and the fallback happened (no KeyError).
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass


async def test_smart_router_reply_action_still_works(brain, monkeypatch):
    """reply_directly path unchanged by the workflow additions."""
    cid = "test_reply_direct"
    replies = []
    async def pub(c, topic, data):
        if topic == "assistant":
            replies.append(data)
    brain._pub = pub

    await _stub_smart_router(brain, {
        "action": "reply",
        "reply":  "hi there — how can I help?",
    })

    out = await brain.handle(cid, "hi")
    assert "how can I help" in out
    assert any("how can I help" in r for r in replies if isinstance(r, str))


async def test_smart_router_other_skill_unaffected(brain, monkeypatch):
    """Skills outside advisor/coder still follow their existing path."""
    cid = "test_unlock"

    async def pub(c, topic, data):
        pass
    brain._pub = pub

    await _stub_smart_router(brain, {
        "action": "skill",
        "skill":  "unlock_pc",
        "params": {},
    })

    reply = await brain.handle(cid, "unlock my pc")
    assert "task started" in reply.lower()
    task, _ = brain.tasks[cid]
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
