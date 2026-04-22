"""Tests for the memory-librarian pipeline (memory_extract + memory_store_facts)."""
import pytest
from core.neuro_factory import NeuroFactory


@pytest.fixture
def factory(tmp_path, monkeypatch):
    monkeypatch.setenv("NEURO_GRAPH_DB", str(tmp_path / "g.db"))
    return NeuroFactory(dir="neuros")


async def test_memory_extract_parses_llm_json(factory):
    """Extractor returns structured facts when the LLM emits valid JSON."""
    class FakeModel:
        async def run(self, state, *, messages, **_):
            return {"content": '{"facts": [{"content":"User prefers Adam over SGD.", "confidence":0.9}, {"content":"Learning rate 1e-3 worked well.", "confidence":0.8}]}'}

    entry = factory.reg["memory_extract"]
    state = {"__cid": "t"}
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeModel()

    out = await factory.run("memory_extract", state, messages=[
        {"sender": "user",      "text": "I'm using Adam with lr=1e-3 and it's working well."},
        {"sender": "assistant", "text": "Good choice for most problems."},
    ])
    assert out["count"] == 2
    assert "Adam" in out["facts"][0]["content"]
    assert 0 < out["facts"][0]["confidence"] <= 1.0


async def test_memory_extract_handles_markdown_fenced_json(factory):
    class FakeModel:
        async def run(self, state, *, messages, **_):
            return {"content": '```json\n{"facts": [{"content":"x"}]}\n```'}

    entry = factory.reg["memory_extract"]
    state = {"__cid": "t"}
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeModel()

    out = await factory.run("memory_extract", state, messages=[
        {"sender": "user", "text": "something"}
    ])
    assert out["count"] == 1


async def test_memory_extract_empty_when_chitchat(factory):
    class FakeModel:
        async def run(self, state, *, messages, **_):
            return {"content": '{"facts": []}'}

    entry = factory.reg["memory_extract"]
    state = {"__cid": "t"}
    inst = await factory.pool.get(entry, state)
    inst.inference = FakeModel()

    out = await factory.run("memory_extract", state, messages=[
        {"sender": "user", "text": "hi"}, {"sender": "assistant", "text": "hello"}
    ])
    assert out["count"] == 0
    assert out["facts"] == []


async def test_memory_store_facts_writes_to_graph(factory):
    state = {"__cid": "t"}
    facts = [
        {"content": "User name is Gopal.", "confidence": 1.0},
        {"content": "Prefers markdown output.", "confidence": 0.9},
    ]
    out = await factory.run("memory_store_facts", state, facts=facts)
    assert out["count"] == 2

    # Verify they're in the graph
    q = await factory.run("memory_graph", state, op="list_nodes", kind="fact")
    contents = [n["content"] for n in q["items"]]
    assert "User name is Gopal." in contents
    assert "Prefers markdown output." in contents


async def test_memory_store_facts_dedup(factory):
    state = {"__cid": "t"}
    await factory.run("memory_store_facts", state, facts=[
        {"content": "The same fact.", "confidence": 1.0}
    ])
    out = await factory.run("memory_store_facts", state, facts=[
        {"content": "the same fact.", "confidence": 0.8},  # case-differ — still dedup
        {"content": "New fact here.", "confidence": 0.7},
    ])
    assert out["count"] == 1   # only the new one written

    q = await factory.run("memory_graph", state, op="list_nodes", kind="fact")
    assert len(q["items"]) == 2  # dedup kept original + added new


async def test_memory_ingest_pipeline(factory):
    """Sequential flow: extract → store. End-to-end pipeline test."""
    class FakeModel:
        async def run(self, state, *, messages, **_):
            return {"content": '{"facts": [{"content":"User prefers TypeScript.", "confidence":0.9}]}'}

    # Stub the model via the extract instance (session-scoped, shared).
    state = {"__cid": "t"}
    extract_entry = factory.reg["memory_extract"]
    extract_inst = await factory.pool.get(extract_entry, state)
    extract_inst.inference = FakeModel()

    out = await factory.run("memory_ingest", state, messages=[
        {"sender": "user",      "text": "I'm migrating from Python to TypeScript."},
        {"sender": "assistant", "text": "That's a big shift — types should feel nicer."},
    ])
    # Sequential accumulates both children's outputs
    assert out["count"] == 1
    assert len(out["ids"]) == 1

    # Fact is in the graph
    q = await factory.run("memory_graph", state, op="search", query="TypeScript")
    assert len(q["items"]) == 1
    assert "TypeScript" in q["items"][0]["content"]


async def test_memory_ingest_describe_kind(factory):
    rich = {e["name"]: e for e in factory.describe()}
    assert rich["memory_extract"]["kind"] == "memory.extract"
    assert rich["memory_extract"]["kind_namespace"] == "memory"
    assert rich["memory_store_facts"]["kind"] == "memory.store"
    assert rich["memory_ingest"]["kind"] == "skill.flow.sequential"
