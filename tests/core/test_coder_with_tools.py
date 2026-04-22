"""Tests for the coder_with_tools workflow — LLM reads files / queries memory mid-reply."""
import json
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "m.db"))
    monkeypatch.setenv("NEURO_GRAPH_DB",  str(tmp_path / "g.db"))
    return NeuroFactory(dir="neuros")


async def test_tool_loop_coder_declares_tools(factory):
    """The tooled-coder should expose the 4 expected tool schemas."""
    import pathlib
    # Discover the code.py wherever it lives under neuros/ (taxonomy-safe)
    repo_neuros = pathlib.Path(__file__).resolve().parent.parent.parent / "neuros"
    matches = list(repo_neuros.rglob("tool_loop_coder/code.py"))
    assert matches, "tool_loop_coder/code.py not found anywhere under neuros/"
    src = matches[0].read_text()
    for tool_name in ("code_file_read", "code_file_list",
                      "memory_recall_keyword", "memory_graph"):
        assert tool_name in src


async def test_tooled_coder_turn_no_tool_call_path(factory):
    """When LLM answers directly (no tool_calls), reply flows through."""
    class FakeInf:
        async def run(self, state, **kw):
            return {"content": "```python\nprint('hi')\n```", "provider_used": "fake"}

    state = {"__cid": "t"}
    # tool_loop is session-scoped → set its inference
    tl_inst = await factory.pool.get(factory.reg["tool_loop"], state)
    tl_inst.inference = FakeInf()

    out = await factory.run("tool_loop_coder", state,
                            user_question="print hi in python")
    assert "```python" in out["reply"]
    assert out["rounds"] == 0
    assert out["tool_calls_made"] == []


async def test_tooled_coder_calls_memory_tool_then_finals(factory):
    """Round 1: LLM calls memory_graph search. Round 2: LLM finalizes."""
    call_idx = {"n": 0}

    class FakeInf:
        async def run(self, state, **kw):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return {"tool_calls": [
                    {"name": "memory_graph",
                     "arguments": {"op": "search", "query": "factory"}}
                ]}
            return {"content": "Based on memory: factory handles neuro loading."}

    state = {"__cid": "t"}
    tl_inst = await factory.pool.get(factory.reg["tool_loop"], state)
    tl_inst.inference = FakeInf()

    # Seed a fact for the tool to find
    await factory.run("memory_graph", state, op="add_node",
                      kind="fact",
                      content="The factory handles neuro loading + hot reload.")

    out = await factory.run("tool_loop_coder", state,
                            user_question="what does the factory do?")
    assert "factory handles" in out["reply"]
    assert out["rounds"] == 1
    assert len(out["tool_calls_made"]) == 1
    assert out["tool_calls_made"][0]["name"] == "memory_graph"


async def test_coder_with_tools_full_workflow(factory):
    """End-to-end: memory.read → system prompt → tool_loop_coder → memory.write → librarian."""
    replies = iter([
        # Turn 1: LLM directly answers
        {"content": "```python\ndef fib(n):\n    return n if n < 2 else fib(n-1) + fib(n-2)\n```\nRecursion is clearest."},
    ])

    class FakeInf:
        async def run(self, state, **kw):
            return next(replies)

    class NoFacts:
        async def run(self, state, *, messages, **_):
            return {"content": '{"facts": []}'}

    state = {"__cid": "tooled_session", "__agent_id": "neuro"}
    # Stub tool_loop's inference (used by tool_loop_coder)
    (await factory.pool.get(factory.reg["tool_loop"], state)).inference = FakeInf()
    # Stub memory_extract's inference
    (await factory.pool.get(factory.reg["memory_extract"], state)).inference = NoFacts()

    state_t1 = {**state, "user_question": "fibonacci in python?"}
    await factory.run("coder_with_tools", state_t1, user_question="fibonacci in python?")
    assert "def fib" in state_t1["reply"]


async def test_coder_with_tools_describe_rich(factory):
    rich = {e["name"]: e for e in factory.describe()}
    wf = rich["coder_with_tools"]
    assert wf["kind"] == "skill.flow.dag"
    assert set(wf["uses"]) == {"memory", "coder_system_prompt",
                                "tool_loop_coder", "memory_ingest"}

    bridge = rich["tool_loop_coder"]
    assert bridge["kind"] == "skill.leaf"
    assert bridge["uses"] == ["tool_loop"]
