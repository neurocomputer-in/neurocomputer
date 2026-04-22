"""Tests for ide_assistant — natural-language neuro editor."""
import json
import pytest
from pathlib import Path
from core.neuro_factory import NeuroFactory
from core import dev_agent


@pytest.fixture
def factory(tmp_path, monkeypatch):
    # Seed tmp_path/neuros w/ the infrastructure ide_assistant needs.
    # Discovery by conf.name — folder name may differ from registry name
    # (taxonomic tree: neuros/ide/assistant/conf.json has name=ide_assistant).
    import shutil
    import pathlib
    import json as _json
    neuros = tmp_path / "neuros"
    snaps = tmp_path / ".neuros_history"
    neuros.mkdir()
    repo_neuros = pathlib.Path(__file__).resolve().parent.parent.parent / "neuros"
    needed = {"ide_assistant", "dev_pipeline",
              "inference", "tool_loop",
              "model_llm_opencode_zen", "model_llm_openrouter",
              "model_llm_ollama", "model_llm_openai", "model_vision_openai",
              "memory_graph"}

    # Map conf.name → source folder by scanning every conf.json
    src_by_name = {}
    for conf_path in repo_neuros.rglob("conf.json"):
        try:
            conf = _json.loads(conf_path.read_text(encoding="utf-8"))
            nm = conf.get("name")
            if nm:
                src_by_name[nm] = conf_path.parent
        except (_json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue

    for n in needed:
        src = src_by_name.get(n)
        if src is None:
            continue
        rel = src.relative_to(repo_neuros)
        dst = neuros / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    monkeypatch.setattr(dev_agent, "NEUROS_DIR", neuros)
    monkeypatch.setattr(dev_agent, "SNAPSHOTS_DIR", snaps)
    return NeuroFactory(dir=str(neuros))


async def test_assistant_creates_new_neuron(factory):
    """LLM proposes a valid new neuro → dev_pipeline saves it."""
    class FakeInf:
        async def run(self, state, **kw):
            return {"content": json.dumps({
                "neuro_name": "hello_demo",
                "action":      "create",
                "conf":        {"name": "hello_demo",
                               "description": "greets the user"},
                "code":        "async def run(state, **kw):\n    return {'reply': 'hi'}\n",
                "explanation": "Created a simple hello neuro.",
            })}

    inst = await factory.pool.get(factory.reg["ide_assistant"], {"__cid": "t"})
    inst.inference = FakeInf()

    out = await factory.run("ide_assistant", {"__cid": "t"},
                            user_request="add a neuro that says hi")
    assert out["ok"] is True
    assert out["action"] == "created"
    assert out["neuro_name"] == "hello_demo"
    # File actually landed on disk
    target = dev_agent.NEUROS_DIR / "hello_demo"
    assert (target / "conf.json").exists()
    assert (target / "code.py").exists()


async def test_assistant_modifies_existing_neuron(factory):
    """Given a target neuro, the LLM sees current state + produces new version."""
    # Seed one
    dev_agent.atomic_save_neuro(
        "editable",
        {"name": "editable", "description": "v1"},
        "async def run(state, **kw):\n    return {'v': 1}\n",
    )

    class FakeInf:
        def __init__(self):
            self.seen_user = None
        async def run(self, state, *, messages, **kw):
            self.seen_user = next(m["content"] for m in messages
                                  if m["role"] == "user")
            return {"content": json.dumps({
                "neuro_name": "editable",
                "action":      "modify",
                "conf":        {"name": "editable", "description": "v2-MODIFIED"},
                "code":        "async def run(state, **kw):\n    return {'v': 2}\n",
                "explanation": "Bumped to v2.",
            })}

    fake = FakeInf()
    inst = await factory.pool.get(factory.reg["ide_assistant"], {"__cid": "t"})
    inst.inference = fake

    out = await factory.run("ide_assistant", {"__cid": "t"},
                            user_request="bump to v2",
                            target_neuro="editable")
    assert out["ok"] is True
    assert out["action"] == "modified"
    assert out["snapshot"] is not None

    # LLM saw the current state in its prompt
    assert "v1" in fake.seen_user
    assert "editable" in fake.seen_user

    # New version on disk
    conf = json.loads((dev_agent.NEUROS_DIR / "editable" / "conf.json").read_text())
    assert conf["description"] == "v2-MODIFIED"


async def test_assistant_retries_on_validation_error(factory):
    """First attempt has invalid JSON, second attempt corrects it."""
    call_idx = {"n": 0}

    class FakeInf:
        async def run(self, state, *, messages, **kw):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                # Missing name field → schema fail
                return {"content": json.dumps({
                    "neuro_name": "retry_demo",
                    "action":      "create",
                    "conf":        {"description": "forgot name"},
                    "code":        "async def run(state, **kw):\n    return {}\n",
                })}
            # Second attempt: corrected
            return {"content": json.dumps({
                "neuro_name": "retry_demo",
                "action":      "create",
                "conf":        {"name": "retry_demo", "description": "fixed"},
                "code":        "async def run(state, **kw):\n    return {}\n",
                "explanation": "Added missing name field after retry.",
            })}

    inst = await factory.pool.get(factory.reg["ide_assistant"], {"__cid": "t"})
    inst.inference = FakeInf()

    out = await factory.run("ide_assistant", {"__cid": "t"},
                            user_request="create retry_demo",
                            max_retries=2)
    assert out["ok"] is True
    assert out["attempts"] == 2


async def test_assistant_gives_up_after_max_retries(factory):
    class AlwaysBad:
        async def run(self, state, **kw):
            return {"content": json.dumps({
                "neuro_name": "bad",
                "action":      "create",
                "conf":        {},   # always invalid
                "code":        "async def run(state, **kw):\n    return {}\n",
            })}

    inst = await factory.pool.get(factory.reg["ide_assistant"], {"__cid": "t"})
    inst.inference = AlwaysBad()

    out = await factory.run("ide_assistant", {"__cid": "t"},
                            user_request="hopeless",
                            max_retries=1)
    assert out["ok"] is False
    assert out["action"] == "failed"
    assert out["attempts"] == 2   # initial + 1 retry


async def test_assistant_no_op(factory):
    """LLM decides no change needed → 'no_op' returned."""
    class NoOpModel:
        async def run(self, state, **kw):
            return {"content": json.dumps({
                "action":      "no_op",
                "explanation": "already looks good",
            })}

    inst = await factory.pool.get(factory.reg["ide_assistant"], {"__cid": "t"})
    inst.inference = NoOpModel()

    out = await factory.run("ide_assistant", {"__cid": "t"},
                            user_request="make it better somehow")
    assert out["ok"] is True
    assert out["action"] == "no_op"


async def test_assistant_blocks_shell_escape(factory):
    """LLM tries to write os.system — dev_pipeline rejects; assistant retries."""
    call_idx = {"n": 0}
    class BadThenGood:
        async def run(self, state, **kw):
            call_idx["n"] += 1
            if call_idx["n"] == 1:
                return {"content": json.dumps({
                    "neuro_name": "shell_attempt",
                    "action":      "create",
                    "conf":        {"name": "shell_attempt", "description": "bad"},
                    "code":        ("import os\n"
                                    "async def run(state, **kw):\n"
                                    "    os.system('ls')\n"
                                    "    return {}\n"),
                })}
            return {"content": json.dumps({
                "neuro_name": "shell_attempt",
                "action":      "create",
                "conf":        {"name": "shell_attempt", "description": "safe"},
                "code":        "async def run(state, **kw):\n    return {'ok': True}\n",
                "explanation": "Removed os.system call.",
            })}

    inst = await factory.pool.get(factory.reg["ide_assistant"], {"__cid": "t"})
    inst.inference = BadThenGood()

    out = await factory.run("ide_assistant", {"__cid": "t"},
                            user_request="list files",
                            max_retries=2)
    assert out["ok"] is True
    # The final saved code has NO os.system
    code_text = (dev_agent.NEUROS_DIR / "shell_attempt" / "code.py").read_text()
    assert "os.system" not in code_text
