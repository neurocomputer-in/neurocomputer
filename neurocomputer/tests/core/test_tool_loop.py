"""Tests for tool_loop — multi-round tool-calling."""
import json
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "m.db"))
    monkeypatch.setenv("NEURO_GRAPH_DB",  str(tmp_path / "g.db"))
    return NeuroFactory(dir="neuros")


async def test_tool_loop_returns_content_when_no_tools_invoked(factory):
    """LLM decides no tool needed — loop returns content immediately."""
    class FakeInf:
        async def run(self, state, **kw):
            return {"content": "direct answer, no tools",
                    "provider_used": "fake", "model_used": "fake"}

    entry = factory.reg["tool_loop"]
    inst = await factory.pool.get(entry, {"__cid": "t"})
    inst.inference = FakeInf()

    out = await factory.run("tool_loop", {"__cid": "t", "__factory": factory},
                            messages=[{"role": "user", "content": "hi"}],
                            tools=[])
    assert out["content"] == "direct answer, no tools"
    assert out["rounds"] == 0
    assert out["tool_calls_made"] == []


async def test_tool_loop_executes_single_tool_call_then_finals(factory):
    """Round 1: LLM asks for memory_graph search. Round 2: LLM returns final answer."""
    call_idx = {"n": 0}
    captured_messages_second_round = []

    class FakeInf:
        async def run(self, state, **kw):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                # First: request a tool
                return {"tool_calls": [
                    {"id": "c_0", "name": "memory_graph",
                     "arguments": {"op": "search", "query": "python"}}
                ]}
            # Second: final answer w/ the tool result in context
            captured_messages_second_round.extend(kw["messages"])
            return {"content": "found 1 fact about python."}

    state = {"__cid": "t", "__factory": factory}
    entry = factory.reg["tool_loop"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    # Seed the memory graph with a fact the tool will find
    await factory.run("memory_graph", state, op="add_node",
                      kind="fact", content="Python is an interpreted language.")

    out = await factory.run("tool_loop", state,
                            messages=[{"role": "user", "content": "search python"}],
                            tools=[{"type": "function",
                                    "function": {"name": "memory_graph",
                                                 "description": "graph ops"}}])

    assert out["rounds"] == 1
    assert out["content"] == "found 1 fact about python."
    assert len(out["tool_calls_made"]) == 1
    assert out["tool_calls_made"][0]["name"] == "memory_graph"

    # Round 2 saw messages with: user, assistant-tool-call, tool-result
    roles = [m["role"] for m in captured_messages_second_round]
    assert roles == ["user", "assistant", "tool"]
    tool_msg = captured_messages_second_round[2]
    # The tool message carries the graph search result as JSON
    result = json.loads(tool_msg["content"])
    assert "items" in result
    assert any("Python" in it["content"] for it in result["items"])


async def test_tool_loop_handles_multi_round(factory):
    """LLM calls two tools across two rounds, then returns final content."""
    call_idx = {"n": 0}

    class FakeInf:
        async def run(self, state, **kw):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return {"tool_calls": [
                    {"name": "memory_graph",
                     "arguments": {"op": "search", "query": "X"}}
                ]}
            if call_idx["n"] == 2:
                return {"tool_calls": [
                    {"name": "memory_graph",
                     "arguments": {"op": "stats"}}
                ]}
            return {"content": "done after 2 rounds"}

    state = {"__cid": "t", "__factory": factory}
    entry = factory.reg["tool_loop"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("tool_loop", state,
                            messages=[{"role": "user", "content": "multi"}],
                            tools=[{"type": "function",
                                    "function": {"name": "memory_graph"}}])
    assert out["content"] == "done after 2 rounds"
    assert out["rounds"] == 2
    assert len(out["tool_calls_made"]) == 2


async def test_tool_loop_max_rounds_cap(factory):
    """If LLM never stops requesting tools, loop caps at max_rounds."""
    class NeverStops:
        async def run(self, state, **kw):
            return {"tool_calls": [
                {"name": "memory_graph",
                 "arguments": {"op": "stats"}}
            ]}

    state = {"__cid": "t", "__factory": factory}
    entry = factory.reg["tool_loop"]
    inst = await factory.pool.get(entry, state)
    inst.inference = NeverStops()
    inst.max_rounds = 3   # lower to make test fast

    out = await factory.run("tool_loop", state,
                            messages=[{"role": "user", "content": "never ending"}],
                            tools=[])
    assert out["rounds"] == 3
    assert out["content"] == ""
    assert "max_rounds" in out["error"]
    assert len(out["tool_calls_made"]) == 3


async def test_tool_loop_tool_handler_override(factory):
    """When tool_handlers maps tool_name → a different neuro, that neuro runs."""
    dispatched = []

    async def fake_handler_run(state, **kw):
        dispatched.append(("aliased", kw))
        return {"ok": True}

    class Aliased:
        async def run(self, state, **kw):
            return await fake_handler_run(state, **kw)

    # We'll pass tool_handlers={'my_search': 'memory_graph'} — so when LLM
    # requests tool 'my_search', loop calls factory.run('memory_graph', ...).
    call_idx = {"n": 0}
    class FakeInf:
        async def run(self, state, **kw):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return {"tool_calls": [
                    {"name": "my_search",
                     "arguments": {"op": "stats"}}
                ]}
            return {"content": "routed via alias"}

    state = {"__cid": "t", "__factory": factory}
    entry = factory.reg["tool_loop"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("tool_loop", state,
                            messages=[{"role": "user", "content": "go"}],
                            tools=[{"type": "function",
                                    "function": {"name": "my_search"}}],
                            tool_handlers={"my_search": "memory_graph"})
    assert out["content"] == "routed via alias"
    assert out["rounds"] == 1
    # memory_graph was actually invoked via alias (stats op succeeded)
    assert out["tool_calls_made"][0]["name"] == "my_search"


async def test_tool_loop_unknown_tool_returns_error_to_llm(factory):
    """When LLM requests a tool the factory doesn't know, tool result
    reports the error; loop continues to give the LLM a chance to recover."""
    call_idx = {"n": 0}
    errors_seen = []

    class FakeInf:
        async def run(self, state, **kw):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return {"tool_calls": [
                    {"name": "fake_tool_that_doesnt_exist", "arguments": {}}
                ]}
            # Inspect what the tool message contained
            for msg in kw["messages"]:
                if msg.get("role") == "tool":
                    errors_seen.append(json.loads(msg["content"]))
            return {"content": "recovered"}

    state = {"__cid": "t", "__factory": factory}
    entry = factory.reg["tool_loop"]
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeInf()

    out = await factory.run("tool_loop", state,
                            messages=[{"role": "user", "content": "go"}],
                            tools=[])
    assert out["content"] == "recovered"
    assert len(errors_seen) == 1
    assert "not in factory" in errors_seen[0]["error"]


async def test_tool_loop_describe(factory):
    rich = {e["name"]: e for e in factory.describe()}
    tl = rich["tool_loop"]
    assert tl["kind"] == "skill.tool_loop"
    assert tl["kind_namespace"] == "skill"
    assert tl["uses"] == ["inference"]
