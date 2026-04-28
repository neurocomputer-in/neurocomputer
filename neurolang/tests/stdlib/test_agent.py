"""Tests for neurolang.stdlib.agent.delegate."""
from __future__ import annotations

import json

import pytest

import neurolang  # noqa: F401  — registers stdlib
from neurolang import default_registry, Memory
from neurolang.stdlib import agent, reason


_FAKE_SUMMARY = "fake-summary-output"


def _make_smart_provider(*, plan_neuros: list[str], compose: str, missing=None):
    """Returns a (callable, default_model) tuple shaped like _PROVIDERS values.

    Dispatches on `kind`: planner JSON for kind='plan', source for kind='compile'.
    The compile branch echoes the upstream plan's composition so a single fake
    can drive both halves of the inner propose→compile loop.
    """
    missing = missing or []

    def _provider(prompt, system, *, model, kind, **_):
        if kind == "plan":
            return json.dumps({
                "neuros": plan_neuros,
                "composition": compose,
                "missing": missing,
            })
        if kind == "compile":
            rhs = compose.split("=", 1)[1].strip() if "=" in compose else "reason.summarize"
            return (
                "from neurolang import neuro\n"
                "from neurolang.stdlib import reason\n"
                f"flow = {rhs}\n"
            )
        raise AssertionError(f"unexpected kind: {kind}")
    return _provider, "fake-model"


def test_delegate_returns_neuro_that_runs_inner_flow(monkeypatch):
    """delegate(task) → Neuro; calling it runs propose → compile → run."""
    from neurolang import _providers
    fake = _make_smart_provider(
        plan_neuros=["neurolang.stdlib.reason.summarize"],
        compose="flow = reason.summarize",
    )
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", fake)
    monkeypatch.setattr(reason, "_call_llm", lambda p, m=None: _FAKE_SUMMARY)

    sub = agent.delegate("summarize the input")
    assert sub.name.startswith("agent.delegate<")

    result = sub.run("some long text to summarize")
    assert result == _FAKE_SUMMARY


def test_delegate_composes_with_pipe(monkeypatch):
    """flow = upstream | agent.delegate(...) builds a Flow; delegate appears in neuros()."""
    from neurolang import _providers, neuro
    fake = _make_smart_provider(
        plan_neuros=["neurolang.stdlib.reason.summarize"],
        compose="flow = reason.summarize",
    )
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", fake)
    monkeypatch.setattr(reason, "_call_llm", lambda p, m=None: _FAKE_SUMMARY)

    @neuro(effect="pure", register=False)
    def upstream(s: str) -> str:
        return s.upper()

    flow = upstream | agent.delegate("summarize result")
    names = [n.name for n in flow.neuros()]
    assert names[0] == upstream.name
    assert names[1].startswith("agent.delegate<")

    out = flow.run("hello world")
    assert out == _FAKE_SUMMARY


def test_delegate_does_not_pollute_default_registry():
    """Each delegate(...) call MUST NOT add to default_registry."""
    before = len(list(default_registry))
    agent.delegate("anything")
    agent.delegate("another")
    after = len(list(default_registry))
    assert after == before, "delegate must use register=False"


def test_delegate_catalog_glob_filter(monkeypatch, tmp_path):
    """catalog=['neurolang.stdlib.reason.*'] hides web.* from the sub-agent's planner."""
    from neurolang import _providers

    # Force the propose/compile caches into a fresh tmpdir so we get cache
    # misses and the LLM provider is actually invoked (test relies on that).
    monkeypatch.setenv("NEUROLANG_CACHE", str(tmp_path))

    captured_catalogs: list[str] = []

    def _provider(prompt, system, *, model, kind, **_):
        captured_catalogs.append(system)
        if kind == "plan":
            return json.dumps({
                "neuros": ["neurolang.stdlib.reason.summarize"],
                "composition": "flow = reason.summarize",
                "missing": [],
            })
        return (
            "from neurolang.stdlib import reason\n"
            "flow = reason.summarize\n"
        )
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (_provider, "fake-model"))
    monkeypatch.setattr(reason, "_call_llm", lambda p, m=None: "ok")

    sub = agent.delegate("summarize input", catalog=["neurolang.stdlib.reason.*"])
    sub.run("text")

    # The catalog markdown lists each neuro by full registered name in
    # backticks. Few-shot examples may mention short names like `web.search`,
    # so we check the unambiguous registered names instead.
    plan_system = captured_catalogs[0]
    assert "neurolang.stdlib.reason.summarize" in plan_system
    assert "neurolang.stdlib.web.search" not in plan_system
    assert "neurolang.stdlib.web.scrape" not in plan_system


def test_delegate_unknown_capability_soft_fails(monkeypatch):
    """planner returns missing != [] → delegate returns a soft-fail string."""
    from neurolang import _providers
    fake = _make_smart_provider(
        plan_neuros=[],
        compose="",
        missing=[{"intent": "send a fax"}],
    )
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", fake)

    sub = agent.delegate("send a fax to grandma")
    out = sub.run("any input")
    assert out.startswith("[delegate: cannot satisfy task")
    assert "send a fax" in out


def test_delegate_depth_zero_raises():
    """depth=0 → DelegationBudgetExhausted on call."""
    sub = agent.delegate("anything", depth=0)
    with pytest.raises(agent.DelegationBudgetExhausted):
        sub.run("input")


def test_delegate_negative_depth_rejected():
    """depth < 0 is a programming error — reject at construction time."""
    with pytest.raises(ValueError, match="depth must be >= 0"):
        agent.delegate("x", depth=-1)


def test_delegate_inherits_parent_memory(monkeypatch, tmp_path):
    """Sub-flow's memory.store is visible to parent's memory.recall — same ContextVar."""
    from neurolang import _providers, neuro
    monkeypatch.setenv("NEUROLANG_CACHE", str(tmp_path))

    def _provider(prompt, system, *, model, kind, **_):
        if kind == "plan":
            return json.dumps({
                "neuros": ["neurolang.stdlib.memory.store"],
                "composition": "flow = _store_cached",
                "missing": [],
            })
        # Sub-flow that stores its input under key 'cached' in active memory.
        return (
            "from neurolang import neuro\n"
            "from neurolang.stdlib import memory_neuros\n"
            "@neuro(effect='memory', register=False)\n"
            "def _store_cached(value):\n"
            "    return memory_neuros.store(value, key='cached')\n"
            "flow = _store_cached\n"
        )
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (_provider, "fake-model"))

    @neuro(effect="pure", register=False)
    def passthrough(s: str) -> str:
        return s

    flow = passthrough | agent.delegate("cache the input")
    mem = Memory.discrete()
    flow.run("the cached value", memory=mem)

    assert mem.get("cached") == "the cached value"


def test_delegate_compile_failure_wraps_as_delegation_failed(monkeypatch):
    """A CompileError inside the sub-agent surfaces as DelegationFailed."""
    from neurolang import _providers
    from neurolang.compile import CompileError

    def _raising(prompt, system, *, model, kind, **_):
        if kind == "plan":
            return json.dumps({
                "neuros": ["neurolang.stdlib.reason.summarize"],
                "composition": "flow = reason.summarize",
                "missing": [],
            })
        # compile step: invalid Python
        return "this is not valid python <<<"
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (_raising, "fake-model"))

    sub = agent.delegate("anything")
    with pytest.raises(agent.DelegationFailed) as exc_info:
        sub.run("input")
    assert "anything" in str(exc_info.value)
    assert isinstance(exc_info.value.cause, CompileError)
