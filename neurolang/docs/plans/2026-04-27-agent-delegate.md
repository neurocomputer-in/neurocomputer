# `agent.delegate` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to execute this plan task-by-task.

**Goal:** Ship `neurolang.stdlib.agent.delegate(task, **opts) → Neuro` — a
factory that returns dynamically-built sub-agent neuros that compose into
parent flows and run an inner `propose_plan → compile_source → execute`
loop at runtime.

**Architecture:** Factory pattern returns a fresh `@neuro(register=False)`
closure each call. Catalog filtering via fnmatch globs. Memory inherits
through existing `current_memory()` ContextVar. Depth budget enforced via
new `_delegation_depth` ContextVar. Sub-prompt is just `task`; upstream
`input_value` flows in via `flow.run(input_value)`.

**Tech Stack:** Python 3.10+, `fnmatch` (stdlib), `contextvars` (stdlib).
No new deps.

**Reference:** `docs/specs/2026-04-27-agent-delegate-design.md` for the
design decisions locked during brainstorming.

---

## Task 1: Skeleton + factory + happy path + compose-with-pipe

**Files:**
- Create: `neurolang/stdlib/agent.py`
- Create: `tests/stdlib/test_agent.py`
- Modify: `neurolang/stdlib/__init__.py` (add `agent`)

- [ ] **Step 1: Wire `agent` into the stdlib namespace**

Modify `neurolang/stdlib/__init__.py`:

```python
"""NeuroLang standard library — built-in neuros for common agentic tasks.

These are normal `@neuro`-decorated functions; nothing special about them
except that they ship in the package and serve as exemplars for users
writing their own neuros.

Optional external dependencies (openai, anthropic, requests, elevenlabs,
whisper, etc.) are checked at use time so the base install stays light.
"""
from . import web, reason, memory_neuros, model, voice, agent

__all__ = ["web", "reason", "memory_neuros", "model", "voice", "agent"]
```

- [ ] **Step 2: Write the happy-path test (TDD)**

Create `tests/stdlib/test_agent.py`:

```python
"""Tests for neurolang.stdlib.agent.delegate."""
from __future__ import annotations

import json
import pytest

import neurolang
from neurolang import default_registry, Memory
from neurolang.stdlib import agent, reason


_FAKE_SUMMARY = "fake-summary-output"


def _make_smart_provider(*, plan_neuros: list[str], compose: str, missing=None):
    """Returns a (callable, default_model) tuple shaped like _PROVIDERS values.
    Dispatches on `kind`: planner-shaped JSON for kind='plan', source for kind='compile'."""
    missing = missing or []

    def _provider(prompt, system, *, model, kind, **_):
        if kind == "plan":
            return json.dumps({
                "neuros": plan_neuros,
                "composition": compose,
                "missing": missing,
            })
        if kind == "compile":
            return (
                "from neurolang import neuro\n"
                "from neurolang.stdlib import reason\n"
                f"flow = {compose.split('=', 1)[1].strip()}\n"
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

    # Make summarize deterministic
    def fake_call_llm(prompt, model=None):
        return _FAKE_SUMMARY
    monkeypatch.setattr(reason, "_call_llm", fake_call_llm)

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
```

- [ ] **Step 3: Run tests — verify they fail**

Run: `cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_agent.py -v`
Expected: ImportError/AttributeError — `agent` module doesn't exist yet.

- [ ] **Step 4: Implement the factory**

Create `neurolang/stdlib/agent.py`:

```python
"""agent.delegate — recursive flow composition.

A factory that returns a fresh sub-agent neuro per call. The returned neuro,
when invoked, runs propose_plan → compile_source → flow.run() against its
bound `task` description. See docs/specs/2026-04-27-agent-delegate-design.md.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Optional

from ..neuro import neuro, Neuro


class DelegationBudgetExhausted(Exception):
    """Raised when agent.delegate is called with depth=0 (no recursion budget left)."""


class DelegationFailed(Exception):
    """Wraps a CompileError or planning failure with the originating task description."""

    def __init__(self, task: str, cause: BaseException):
        super().__init__(f"agent.delegate({task!r}) failed: {cause}")
        self.task = task
        self.cause = cause


_delegation_depth: ContextVar[Optional[int]] = ContextVar("_delegation_depth", default=None)


def _short(s: str, n: int = 40) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def delegate(
    task: str,
    *,
    catalog: Optional[list[str]] = None,
    depth: int = 1,
    model: Optional[str] = None,
) -> Neuro:
    """Build a sub-agent neuro that plans → compiles → runs at call time.

    The returned neuro, when called with an upstream value, runs an inner
    `propose_plan(task) → compile_source(task) → flow.run(value)` loop and
    returns the inner flow's result. `task` is bound; only `value` flows
    in at runtime.
    """
    if depth < 0:
        raise ValueError(f"delegate depth must be >= 0, got {depth!r}")

    @neuro(
        effect="llm",
        kind="skill.agent",
        name=f"agent.delegate<{_short(task)}>",
        register=False,
    )
    def _agent(input_value: Any) -> Any:
        # Depth budget: each delegate call consumes one unit. Inherits the
        # parent's residual budget if a sub-agent was itself launched from
        # inside another delegate's sub-flow.
        residual = _delegation_depth.get()
        effective = depth if residual is None else residual
        if effective <= 0:
            raise DelegationBudgetExhausted(
                f"delegate({task!r}) called with no remaining depth budget"
            )

        from ...neurolang import compile_source, propose_plan  # type: ignore  # avoid cycle on import
        # Re-import via the top-level package; stdlib lives one level under it.
        from .. import compile_source, propose_plan  # noqa: F811

        try:
            plan = propose_plan(task, model=model)
            if plan.missing:
                intents = ", ".join(m.intent for m in plan.missing)
                return f"[delegate: cannot satisfy task — missing: {intents}]"

            flow = compile_source(task, model=model)
        except Exception as e:
            raise DelegationFailed(task, e) from e

        token = _delegation_depth.set(effective - 1)
        try:
            return flow.run(input_value)
        finally:
            _delegation_depth.reset(token)

    return _agent
```

- [ ] **Step 5: Run tests — verify they pass**

Run: `cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_agent.py -v`
Expected: 3 passed.

- [ ] **Step 6: Run full suite**

Run: `cd /home/ubuntu/neurolang && python -m pytest tests/ -q`
Expected: 129/129 passing (126 prior + 3 new).

- [ ] **Step 7: Commit**

```bash
git add neurolang/stdlib/agent.py neurolang/stdlib/__init__.py tests/stdlib/test_agent.py
git commit -m "feat(agent): delegate factory — recursive flow composition (Task 1)

Factory returns a fresh @neuro(register=False) per call with task baked
into the closure. At runtime, runs propose_plan → compile_source → flow.run
against the bound task. Composes naturally with | operator.

3 tests: happy path, compose-with-pipe, no registry pollution."
```

---

## Task 2: Catalog filtering + depth budget + DelegationFailed

**Files:**
- Modify: `neurolang/stdlib/agent.py`
- Modify: `tests/stdlib/test_agent.py`

- [ ] **Step 1: Add the failure-mode tests (TDD)**

Append to `tests/stdlib/test_agent.py`:

```python
def test_delegate_catalog_glob_filter(monkeypatch):
    """catalog=['reason.*'] hides web.* from the sub-agent's planner."""
    from neurolang import _providers, default_registry

    captured_catalogs: list[set] = []

    def _provider(prompt, system, *, model, kind, **_):
        # The system prompt embeds the catalog markdown — we sniff it.
        captured_catalogs.append({line for line in system.splitlines() if line.startswith("- **")})
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

    catalog_lines = captured_catalogs[0]  # planner call
    # Only reason.* names should appear; web.* should not.
    assert any("summarize" in line for line in catalog_lines)
    assert not any("web.search" in line or "web.scrape" in line for line in catalog_lines)


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
        # compile step: return invalid Python
        return "this is not valid python <<<"
    monkeypatch.setitem(_providers._PROVIDERS, "opencode-zen", (_raising, "fake-model"))

    sub = agent.delegate("anything")
    with pytest.raises(agent.DelegationFailed) as exc_info:
        sub.run("input")
    assert "anything" in str(exc_info.value)
    assert isinstance(exc_info.value.cause, CompileError)
```

- [ ] **Step 2: Run tests — verify they fail**

Run: `cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_agent.py -v`
Expected: 4 fail (catalog not yet filtered; tests for depth=-1/CompileError need fresh agent.py code paths exercised).

- [ ] **Step 3: Implement catalog filtering**

In `neurolang/stdlib/agent.py`, replace the `_agent` body. Add `import fnmatch` at top and update the file:

```python
"""agent.delegate — recursive flow composition.

A factory that returns a fresh sub-agent neuro per call. The returned neuro,
when invoked, runs propose_plan → compile_source → flow.run() against its
bound `task` description. See docs/specs/2026-04-27-agent-delegate-design.md.
"""
from __future__ import annotations

import fnmatch
from contextvars import ContextVar
from typing import Any, Optional

from ..neuro import neuro, Neuro
from ..registry import Registry, default_registry


class DelegationBudgetExhausted(Exception):
    """Raised when agent.delegate is called with depth=0 (no recursion budget left)."""


class DelegationFailed(Exception):
    """Wraps a CompileError or planning failure with the originating task description."""

    def __init__(self, task: str, cause: BaseException):
        super().__init__(f"agent.delegate({task!r}) failed: {cause}")
        self.task = task
        self.cause = cause


_delegation_depth: ContextVar[Optional[int]] = ContextVar("_delegation_depth", default=None)


def _short(s: str, n: int = 40) -> str:
    return s if len(s) <= n else s[:n - 1] + "…"


def _filtered_registry(patterns: Optional[list[str]]):
    """Return either the default registry (patterns=None) or a fresh
    Registry containing only neuros whose names match any glob pattern."""
    if patterns is None:
        return default_registry
    sub = Registry()
    for n in default_registry:
        if any(fnmatch.fnmatchcase(n.name, p) for p in patterns):
            sub.add(n)
    return sub


def delegate(
    task: str,
    *,
    catalog: Optional[list[str]] = None,
    depth: int = 1,
    model: Optional[str] = None,
) -> Neuro:
    """Build a sub-agent neuro that plans → compiles → runs at call time."""
    if depth < 0:
        raise ValueError(f"delegate depth must be >= 0, got {depth!r}")

    @neuro(
        effect="llm",
        kind="skill.agent",
        name=f"agent.delegate<{_short(task)}>",
        register=False,
    )
    def _agent(input_value: Any) -> Any:
        residual = _delegation_depth.get()
        effective = depth if residual is None else residual
        if effective <= 0:
            raise DelegationBudgetExhausted(
                f"delegate({task!r}) called with no remaining depth budget"
            )

        from .. import compile_source, propose_plan

        sub_registry = _filtered_registry(catalog)

        try:
            plan = propose_plan(task, model=model, registry=sub_registry)
            if plan.missing:
                intents = ", ".join(m.intent for m in plan.missing)
                return f"[delegate: cannot satisfy task — missing: {intents}]"

            flow = compile_source(task, model=model, registry=sub_registry)
        except DelegationBudgetExhausted:
            raise
        except Exception as e:
            raise DelegationFailed(task, e) from e

        token = _delegation_depth.set(effective - 1)
        try:
            return flow.run(input_value)
        finally:
            _delegation_depth.reset(token)

    return _agent
```

- [ ] **Step 4: Run tests — verify they pass**

Run: `cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_agent.py -v`
Expected: 8 passed (3 from Task 1 + 5 new).

- [ ] **Step 5: Run full suite**

Run: `cd /home/ubuntu/neurolang && python -m pytest tests/ -q`
Expected: 134/134.

- [ ] **Step 6: Commit**

```bash
git add neurolang/stdlib/agent.py tests/stdlib/test_agent.py
git commit -m "feat(agent): catalog filter + depth budget + DelegationFailed (Task 2)

catalog=['reason.*'] uses fnmatch glob filter to scope which neuros the
sub-agent sees; planner + compile_source both receive the filtered registry.
depth=0 raises DelegationBudgetExhausted; CompileError inside the sub-flow
wraps as DelegationFailed(task, cause). Negative depth rejected at
construction time.

5 new tests (catalog glob, soft-fail-on-missing, depth=0, depth<0,
compile-error-wrap)."
```

---

## Task 3: Memory inheritance + example + STATUS/CHANGELOG/push

**Files:**
- Modify: `tests/stdlib/test_agent.py` (one new test)
- Create: `examples/agent_delegate.py`
- Modify: `docs/STATUS.md`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Add the memory-inheritance test**

Append to `tests/stdlib/test_agent.py`:

```python
def test_delegate_inherits_parent_memory(monkeypatch):
    """Sub-flow's memory.store is visible to parent's memory.recall via shared ContextVar."""
    from neurolang import _providers, neuro
    from neurolang.stdlib import memory_neuros

    # Sub-agent compiles to: store the input under key 'cached'
    def _provider(prompt, system, *, model, kind, **_):
        if kind == "plan":
            return json.dumps({
                "neuros": ["neurolang.stdlib.memory.store"],
                "composition": "flow = memory_neuros.store",
                "missing": [],
            })
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
```

- [ ] **Step 2: Run tests — verify all pass**

Run: `cd /home/ubuntu/neurolang && python -m pytest tests/stdlib/test_agent.py -v`
Expected: 9 passed.

- [ ] **Step 3: Write the example**

Create `examples/agent_delegate.py`:

```python
"""Demo: a flow whose middle step is a sub-agent that figures out
its own pipeline. Requires a live LLM (default: opencode-zen).

Run: python examples/agent_delegate.py
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/neurolang")

import neurolang  # noqa: F401  — registers stdlib
from neurolang import neuro
from neurolang.stdlib import reason, agent


@neuro(effect="pure", register=False)
def passthrough(text: str) -> str:
    return text


# The middle step decides its own implementation. The outer author only
# specifies WHAT the sub-task is — not WHICH neuros to use.
flow = passthrough | agent.delegate(
    "summarize the input in two sentences",
    catalog=["neurolang.stdlib.reason.*"],
)

ARTICLE = (
    "Recurrent neural networks (RNNs) processed sequences token by token, "
    "which made training slow and limited context length. The 2017 transformer "
    "paper replaced recurrence with self-attention, letting every token attend "
    "to every other token in parallel. This unlocked the modern era of LLMs: "
    "GPT, BERT, and the trillion-parameter scale beyond."
)

print("=== flow ===")
print(flow)
print("\n=== flow.to_mermaid() ===")
print(flow.to_mermaid())
print("\n=== sub-agent figures out its own pipeline now ===\n")
result = flow.run(ARTICLE)
print(result)
```

- [ ] **Step 4: Update STATUS.md**

In `docs/STATUS.md`, move `agent.delegate` from "Next up" to the top of
"Just shipped" with the date 2026-04-27 and a brief description. Decrement
the "Next up" list. Update the test count (134 → 135). Update the "Stdlib"
line in Quick reference to include `agent`.

- [ ] **Step 5: Update CHANGELOG.md**

In `CHANGELOG.md`, add a new section under `[Unreleased]` with
`### Added (Phase 1.8 — agent.delegate, recursive composition)`. Summarize
the design decisions (factory pattern, catalog glob, depth budget,
soft-fail on missing).

- [ ] **Step 6: Verify full suite + push**

```bash
cd /home/ubuntu/neurolang
python -m pytest tests/ -q   # expected: 135/135
python examples/agent_delegate.py   # smoke check (live LLM)
git add -- examples/agent_delegate.py tests/stdlib/test_agent.py docs/STATUS.md CHANGELOG.md
git commit -m "docs(agent): example + STATUS + CHANGELOG (Task 3)

Live demo at examples/agent_delegate.py: outer flow declares only the
sub-task; the middle step (agent.delegate) plans + compiles its own
inner flow at runtime."
git push origin main
```

Expected: clean push, 135/135 green.
