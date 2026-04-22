import pathlib
import pytest
from core.memory import MemoryStore


def test_sqlite_backend_roundtrip(tmp_path):
    db = tmp_path / "mem.db"
    s = MemoryStore(path=str(db))

    s.write(scope="agent", agent_id="neuro", caller="user", key="x", value={"v": 1})
    r = s.read(scope="agent", agent_id="neuro", caller="user", key="x")
    assert r["value"] == {"v": 1}
    assert "ts" in r["meta"]


def test_list_with_prefix(tmp_path):
    s = MemoryStore(path=str(tmp_path / "mem.db"))
    s.write("agent", "neuro", "user", "pref.theme", "dark")
    s.write("agent", "neuro", "user", "pref.lang", "en")
    s.write("agent", "neuro", "user", "other", "x")
    items = s.list("agent", "neuro", "user", prefix="pref.")
    assert {i["key"] for i in items} == {"pref.theme", "pref.lang"}


def test_delete_removes(tmp_path):
    s = MemoryStore(path=str(tmp_path / "mem.db"))
    s.write("agent", "neuro", "user", "k", 1)
    assert s.read("agent", "neuro", "user", "k")["value"] == 1
    s.delete("agent", "neuro", "user", "k")
    assert s.read("agent", "neuro", "user", "k") is None


def test_ttl_expires(tmp_path):
    import time
    s = MemoryStore(path=str(tmp_path / "mem.db"))
    s.write("agent", "neuro", "user", "k", 1, ttl_seconds=0)
    time.sleep(0.01)
    assert s.read("agent", "neuro", "user", "k") is None


def test_search_keyword_match(tmp_path):
    s = MemoryStore(path=str(tmp_path / "mem.db"))
    s.write("agent", "neuro", "user", "note.1", "eat spaghetti")
    s.write("agent", "neuro", "user", "note.2", "wash car")
    s.write("agent", "neuro", "user", "note.3", "buy spaghetti sauce")
    hits = s.search("agent", "neuro", "user", "spaghetti", top_k=5)
    assert len(hits) == 2
    assert {h["key"] for h in hits} == {"note.1", "note.3"}
