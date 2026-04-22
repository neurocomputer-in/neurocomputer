"""Tests for context.* kind — slice + assembler + profile end-to-end."""
import pytest
from core.neuro_factory import NeuroFactory


async def test_context_slice_history_compact_via_state():
    f = NeuroFactory(dir="neuros")
    state = {
        "__cid": "t",
        "messages": [
            {"sender": "user",      "text": "hi there"},
            {"sender": "assistant", "text": "hello, what's up?"},
            {"sender": "user",      "text": "can u help"},
        ],
    }
    out = await f.run("context_slice_history_compact", state, limit=5)
    assert "user: hi there" in out["text"]
    assert "assistant: hello" in out["text"]
    assert out["tokens"] > 0


async def test_context_slice_skills_compact_via_state():
    f = NeuroFactory(dir="neuros")
    state = {
        "__cid": "t",
        "__neuros": [
            {"name": "echo",  "desc": "echo input"},
            {"name": "reply", "desc": "reply to user"},
        ],
    }
    out = await f.run("context_slice_skills_compact", state)
    assert "- echo: echo input" in out["text"]
    assert "- reply: reply to user" in out["text"]


async def test_context_profile_router_assembles():
    f = NeuroFactory(dir="neuros")
    state = {
        "__cid": "t",
        "messages": [
            {"sender": "user", "text": "plan my week"},
        ],
        "__neuros": [
            {"name": "planner", "desc": "plan things"},
        ],
    }
    out = await f.run("context_profile_router", state)
    assert "plan my week" in out["history"]
    assert "- planner: plan things" in out["skills"]
    assert out["tokens"] > 0
    assert isinstance(out["within_budget"], bool)


async def test_context_profile_describe_rich():
    f = NeuroFactory(dir="neuros")
    rich = {e["name"]: e for e in f.describe()}

    prof = rich["context_profile_router"]
    assert prof["kind"] == "context.profile"
    assert prof["kind_namespace"] == "context"
    assert prof["category"] == "context.profile"
    assert set(prof["uses"]) == {"context_slice_history_compact", "context_slice_skills_compact"}

    slice_hist = rich["context_slice_history_compact"]
    assert slice_hist["kind"] == "context.slice"
    assert slice_hist["kind_namespace"] == "context"
