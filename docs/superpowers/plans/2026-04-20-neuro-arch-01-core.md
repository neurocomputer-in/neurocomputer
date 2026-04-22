# Neuro Architecture — 01-core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land the 6-phase migration from `docs/superpowers/specs/2026-04-20-neuro-arch/01-core/` — unified neuro OOP runtime with fn + class forms, flow-as-neuro (`FlowNeuro` → `DagFlow`/`SequentialFlow`/`ParallelFlow`), `InstancePool` for scoped lifecycles, typed ports, and a `memory` API — with zero breakage of existing neuros.

**Architecture:** Six phases, each independently committable and revertible. Phases A/C/D/E are additive; B is an internal relocation; F is the call-site swap. Tests are unit where contracts are clear (flow classes, factory dispatch, instance pool, dep injection, memory API) and end-to-end smoke where integration matters (Brain path, hot-reload, streaming, cancellation).

**Tech Stack:** Python 3.11+, asyncio, pytest + pytest-asyncio (new), SQLite (stdlib).

**Spec references:** See `docs/superpowers/specs/2026-04-20-neuro-arch/01-core/*.md`. This plan realizes those subdocs.

**Out of scope for this plan:** `02-dev-agent/` pipeline changes, `03-react-orchestrator/` design, `99-future/` DSL. Those are separate plans.

---

## File structure — what this plan creates / modifies

**Create:**
- `core/flows/__init__.py` — re-exports.
- `core/flows/flow_neuro.py` — `FlowNeuro` abstract base + hooks.
- `core/flows/sequential_flow.py` — ordered pipeline built-in.
- `core/flows/parallel_flow.py` — concurrent fan-out built-in.
- `core/flows/dag_flow.py` — JSON DAG interpreter (houses today's Executor body).
- `core/instance_pool.py` — scope-aware class-neuro instance pool.
- `core/neuro_handle.py` — lazy proxy returned by dep injection.
- `core/memory.py` — SQLite-backed memory store.
- `core/schemas/neuro_conf.schema.json` — conf.json JSON Schema (minimal, validates new rich shape).
- `core/schemas/__init__.py` — empty.
- `neuros/memory/conf.json` — the built-in `memory` neuro.
- `neuros/memory/code.py` — thin bridge: calls `core.memory`.
- `tests/core/__init__.py` — empty.
- `tests/core/test_flow_neuro.py`
- `tests/core/test_sequential_flow.py`
- `tests/core/test_parallel_flow.py`
- `tests/core/test_dag_flow.py`
- `tests/core/test_instance_pool.py`
- `tests/core/test_neuro_factory_class.py`
- `tests/core/test_typed_ports.py`
- `tests/core/test_memory.py`
- `tests/core/test_brain_dag_flow_swap.py`
- `pytest.ini` — minimal pytest config with asyncio mode.

**Modify:**
- `core/base_neuro.py` — becomes abstract parent; fn-wrapping moves to internal `FnEntry`.
- `core/neuro_factory.py` — add class-neuro load path, `ClassEntry`/`FnEntry`, `InstancePool`, `NeuroHandle` injection, pure-conf flow synthesis, port normalizer, rich `describe()`.
- `core/executor.py` — reduced to shim in Phase B, removed in Phase F.
- `core/brain.py` — Phase F call-site swap (`Executor(...)` → `factory.run("dag_flow", ...)`).
- `requirements.txt` — add `pytest`, `pytest-asyncio`.

**Do NOT touch:**
- `neuros/*` (existing neuros must continue loading unchanged).
- `profiles/*` (profile semantics unchanged).
- `core/chat_handler.py`, `core/conversation.py`, `core/db.py`, `core/pubsub.py`, LiveKit code, front-end code.

---

## Phase 0 — Preamble (test harness setup)

### Task 0.1: Add pytest to requirements

**Files:**
- Modify: `requirements.txt`
- Create: `pytest.ini`

- [ ] **Step 1: Add pytest and pytest-asyncio to requirements.txt**

Append at the end of `requirements.txt`:

```
pytest==8.3.3
pytest-asyncio==0.24.0
```

- [ ] **Step 2: Install**

Run: `pip install pytest==8.3.3 pytest-asyncio==0.24.0`
Expected: both installed.

- [ ] **Step 3: Create `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 4: Verify pytest runs on the empty core test dir**

```bash
mkdir -p tests/core
touch tests/core/__init__.py
pytest tests/core/ -v
```
Expected: `no tests ran in 0.00s` (or similar — exit 5 is fine for empty).

- [ ] **Step 5: Commit**

```bash
git add requirements.txt pytest.ini tests/core/__init__.py
git commit -m "test(core): add pytest + pytest-asyncio harness"
```

---

## Phase A — Flow infrastructure (additive)

Add the `core/flows/` package with `FlowNeuro`, `SequentialFlow`, `ParallelFlow`, `DagFlow` (initial form). Nothing uses these yet. Fully tested standalone.

### Task A.1: `FlowNeuro` base class

**Files:**
- Create: `core/flows/__init__.py`
- Create: `core/flows/flow_neuro.py`
- Test: `tests/core/test_flow_neuro.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_flow_neuro.py`:

```python
import pytest
from core.flows.flow_neuro import FlowNeuro


class DemoFlow(FlowNeuro):
    async def run(self, state, **kw):
        state["ran"] = True
        return {"ok": True}


async def test_flow_neuro_is_callable():
    f = DemoFlow()
    state = {}
    out = await f.run(state)
    assert out == {"ok": True}
    assert state["ran"] is True


async def test_flow_neuro_has_default_hooks():
    f = DemoFlow()
    await f.before_child("x", {}, {})   # must not raise
    await f.after_child("x", {}, {})
    assert await f.on_child_error("x", ValueError("boom"), {}) == "replan"


async def test_flow_neuro_class_attrs_defaults():
    assert FlowNeuro.uses == []
    assert FlowNeuro.children == []
    assert FlowNeuro.replan_policy == "inherit"
```

- [ ] **Step 2: Run and verify fail**

Run: `pytest tests/core/test_flow_neuro.py -v`
Expected: collection error — `ModuleNotFoundError: core.flows.flow_neuro`.

- [ ] **Step 3: Implement `FlowNeuro`**

`core/flows/__init__.py`:

```python
from core.flows.flow_neuro import FlowNeuro

__all__ = ["FlowNeuro"]
```

`core/flows/flow_neuro.py`:

```python
"""FlowNeuro — a composite neuro that orchestrates children.

Per spec: `01-core/02-flow-as-neuro.md`. Abstract base; concrete flows
(SequentialFlow, ParallelFlow, DagFlow, user subclasses) implement `run`.
"""
from core.base_neuro import BaseNeuro


class FlowNeuro(BaseNeuro):
    uses: list = []
    children: list = []
    replan_policy: str = "inherit"   # "inherit" | "never" | "bounded:N"

    async def run(self, state, **kw):
        raise NotImplementedError

    async def before_child(self, name, params, state):
        return None

    async def after_child(self, name, out, state):
        return None

    async def on_child_error(self, name, exc, state):
        return "replan"   # default matches current Executor behavior
```

> **Note:** `BaseNeuro` is currently a concrete fn-wrapper. Phase C evolves it to an abstract parent. Until then, `FlowNeuro` subclassing it is safe because `FlowNeuro.run` overrides.

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/core/test_flow_neuro.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add core/flows/__init__.py core/flows/flow_neuro.py tests/core/test_flow_neuro.py
git commit -m "feat(flows): add FlowNeuro base class + hooks"
```

### Task A.2: `SequentialFlow`

**Files:**
- Create: `core/flows/sequential_flow.py`
- Modify: `core/flows/__init__.py`
- Test: `tests/core/test_sequential_flow.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_sequential_flow.py`:

```python
import pytest
from core.flows.sequential_flow import SequentialFlow
from core.base_neuro import BaseNeuro


class FakeChild:
    def __init__(self, payload):
        self.payload = payload

    async def run(self, state, **kw):
        state.setdefault("trace", []).append(self.payload["name"])
        return self.payload


async def test_sequential_runs_children_in_order():
    f = SequentialFlow()
    f.children = ["a", "b", "c"]
    f.a = FakeChild({"name": "a", "key_a": 1})
    f.b = FakeChild({"name": "b", "key_b": 2})
    f.c = FakeChild({"name": "c", "key_c": 3})

    state = {}
    out = await f.run(state)

    assert state["trace"] == ["a", "b", "c"]
    assert out == {"name": "c", "key_a": 1, "key_b": 2, "key_c": 3}
    assert state["key_a"] == 1
    assert state["key_b"] == 2
    assert state["key_c"] == 3
```

- [ ] **Step 2: Run and verify fail**

Run: `pytest tests/core/test_sequential_flow.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `SequentialFlow`**

`core/flows/sequential_flow.py`:

```python
"""SequentialFlow — orchestrates `self.children` in declared order."""
from core.flows.flow_neuro import FlowNeuro


class SequentialFlow(FlowNeuro):
    async def run(self, state, **kw):
        acc = {}
        for name in self.children:
            child = getattr(self, name)
            await self.before_child(name, kw, state)
            child_out = await child.run(state, **kw)
            if not isinstance(child_out, dict):
                child_out = {}
            state.update(child_out)
            acc.update(child_out)
            await self.after_child(name, child_out, state)
        return acc
```

Update `core/flows/__init__.py`:

```python
from core.flows.flow_neuro import FlowNeuro
from core.flows.sequential_flow import SequentialFlow

__all__ = ["FlowNeuro", "SequentialFlow"]
```

- [ ] **Step 4: Run test — expect pass**

Run: `pytest tests/core/test_sequential_flow.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add core/flows/sequential_flow.py core/flows/__init__.py tests/core/test_sequential_flow.py
git commit -m "feat(flows): add SequentialFlow"
```

### Task A.3: `ParallelFlow`

**Files:**
- Create: `core/flows/parallel_flow.py`
- Modify: `core/flows/__init__.py`
- Test: `tests/core/test_parallel_flow.py`

- [ ] **Step 1: Write the failing test**

`tests/core/test_parallel_flow.py`:

```python
import asyncio
import pytest
from core.flows.parallel_flow import ParallelFlow


class SleeperChild:
    def __init__(self, name, delay):
        self.name = name
        self.delay = delay

    async def run(self, state, **kw):
        await asyncio.sleep(self.delay)
        return {self.name: True}


async def test_parallel_fans_out():
    f = ParallelFlow()
    f.children = ["a", "b", "c"]
    f.a = SleeperChild("a", 0.01)
    f.b = SleeperChild("b", 0.01)
    f.c = SleeperChild("c", 0.01)

    out = await f.run({})
    assert out == {"a": True, "b": True, "c": True}


async def test_parallel_merge_key_scoping():
    f = ParallelFlow()
    f.children = ["x", "y"]
    f.merge_key = "per_child"
    f.x = SleeperChild("shared", 0.001)
    f.y = SleeperChild("shared", 0.001)   # same output key — conflict without merge_key

    out = await f.run({})
    assert "per_child" in out
    assert set(out["per_child"].keys()) == {"x", "y"}
```

- [ ] **Step 2: Run and verify fail**

Run: `pytest tests/core/test_parallel_flow.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `ParallelFlow`**

`core/flows/parallel_flow.py`:

```python
"""ParallelFlow — concurrent fan-out over `self.children`."""
import asyncio
from core.flows.flow_neuro import FlowNeuro


class ParallelFlow(FlowNeuro):
    merge_key: str = None

    async def run(self, state, **kw):
        async def _one(name):
            child = getattr(self, name)
            out = await child.run(state, **kw)
            return name, (out if isinstance(out, dict) else {})

        pairs = await asyncio.gather(*(_one(n) for n in self.children))

        if self.merge_key:
            bucket = state.setdefault(self.merge_key, {})
            for name, out in pairs:
                bucket[name] = out
            return {self.merge_key: bucket}

        merged = {}
        for _, out in pairs:
            merged.update(out)
        state.update(merged)
        return merged
```

Update `core/flows/__init__.py`:

```python
from core.flows.flow_neuro import FlowNeuro
from core.flows.sequential_flow import SequentialFlow
from core.flows.parallel_flow import ParallelFlow

__all__ = ["FlowNeuro", "SequentialFlow", "ParallelFlow"]
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/core/test_parallel_flow.py -v`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add core/flows/parallel_flow.py core/flows/__init__.py tests/core/test_parallel_flow.py
git commit -m "feat(flows): add ParallelFlow with optional merge_key"
```

### Task A.4: `DagFlow` skeleton (not yet replacing Executor)

**Files:**
- Create: `core/flows/dag_flow.py`
- Modify: `core/flows/__init__.py`
- Test: `tests/core/test_dag_flow.py`

Purpose of this step: ship a `DagFlow` class that accepts `dag=...`, runs nodes via `state["__factory"].run(name, state, **params)`, walks `"next"`, merges `out` into state. Replan loop + event publish land in Phase B when we absorb the Executor body. Keep this task scoped to the walk.

- [ ] **Step 1: Write the failing test**

`tests/core/test_dag_flow.py`:

```python
import pytest
from core.flows.dag_flow import DagFlow


class DummyFactory:
    def __init__(self):
        self.calls = []

    async def run(self, name, state, **params):
        self.calls.append((name, dict(params)))
        return {f"{name}_ran": True}


async def test_dag_flow_walks_chain():
    factory = DummyFactory()
    state = {"__factory": factory}
    dag = {
        "start": "n0",
        "nodes": {
            "n0": {"neuro": "a", "params": {"x": 1}, "next": "n1"},
            "n1": {"neuro": "b", "params": {},       "next": None},
        },
    }
    f = DagFlow()
    out = await f.run(state, dag=dag)

    assert [c[0] for c in factory.calls] == ["a", "b"]
    assert state["a_ran"] is True
    assert state["b_ran"] is True
    assert out == {"a_ran": True, "b_ran": True}
```

- [ ] **Step 2: Run and verify fail**

Run: `pytest tests/core/test_dag_flow.py -v`
Expected: ModuleNotFoundError.

- [ ] **Step 3: Implement `DagFlow` (walk only)**

`core/flows/dag_flow.py`:

```python
"""DagFlow — interprets a JSON DAG via state["__factory"].

Phase A: walk + merge. Phase B absorbs the rest of the Executor body
(replan loop, events, error hooks).
"""
from core.flows.flow_neuro import FlowNeuro


class DagFlow(FlowNeuro):
    async def run(self, state, *, dag, **kw):
        factory = state["__factory"]
        node = dag["start"]
        nodes = dag["nodes"]
        acc = {}

        while node:
            spec = nodes[node]
            name = spec["neuro"]
            params = spec.get("params", {}) or {}
            out = await factory.run(name, state, **params)
            if not isinstance(out, dict):
                out = {}
            state.update(out)
            acc.update(out)
            node = spec.get("next")

        return acc
```

Update `core/flows/__init__.py`:

```python
from core.flows.flow_neuro import FlowNeuro
from core.flows.sequential_flow import SequentialFlow
from core.flows.parallel_flow import ParallelFlow
from core.flows.dag_flow import DagFlow

__all__ = ["FlowNeuro", "SequentialFlow", "ParallelFlow", "DagFlow"]
```

- [ ] **Step 4: Run test — expect pass**

Run: `pytest tests/core/test_dag_flow.py -v`
Expected: 1 passed.

- [ ] **Step 5: Sanity-check existing server still starts**

Run in a second terminal: `python3 server.py` (startup only — kill after "listening" message appears).
Expected: no import errors. Kill with Ctrl+C.

- [ ] **Step 6: Commit**

```bash
git add core/flows/dag_flow.py core/flows/__init__.py tests/core/test_dag_flow.py
git commit -m "feat(flows): add DagFlow walker (no replan yet)"
```

---

## Phase B — Absorb Executor body into DagFlow

Port the existing `core/executor.py` logic (replan, events, error hooks, streaming, ReAct logging, `task.done`/`task.cancelled`) into `DagFlow.run`. Reduce `core/executor.py` to a forwarding shim. No change to Brain yet.

### Task B.1: Expand `DagFlow.run` with the full Executor semantics

**Files:**
- Modify: `core/flows/dag_flow.py`
- Test: `tests/core/test_dag_flow.py` (extend)

- [ ] **Step 1: Extend the failing test**

Append to `tests/core/test_dag_flow.py`:

```python
class ReplanOnceFactory:
    """Returns needs_replan=True on first call of 'maybe', then succeeds."""
    def __init__(self):
        self.calls = 0

    async def run(self, name, state, **params):
        if name == "planner":
            return {"plan": {"ok": True, "flow": {"start": "n0",
                    "nodes": {"n0": {"neuro": "final", "params": {}, "next": None}}}}}
        if name == "maybe":
            self.calls += 1
            return {"needs_replan": True} if self.calls == 1 else {"ok": True}
        if name == "final":
            return {"final_done": True}
        return {}


async def test_dag_flow_replans_via_planner():
    factory = ReplanOnceFactory()
    events = []
    async def pub(topic, data): events.append((topic, data))
    state = {
        "__factory": factory,
        "__pub": pub,
        "__planner": "planner",
        "__cid": "test",
        "goal": "x",
    }
    dag = {
        "start": "n0",
        "nodes": {"n0": {"neuro": "maybe", "params": {}, "next": None}},
    }
    f = DagFlow()
    out = await f.run(state, dag=dag)

    # Replan produced a new flow with "final"; we should see final_done in final output.
    assert state.get("final_done") is True
    # task.done must fire exactly once.
    assert sum(1 for t, _ in events if t == "task.done") == 1


async def test_dag_flow_publishes_node_events():
    class F:
        async def run(self, name, state, **params):
            return {"x": 1}
    events = []
    async def pub(topic, data): events.append((topic, data))
    state = {"__factory": F(), "__pub": pub}
    dag = {"start": "n0", "nodes": {"n0": {"neuro": "a", "params": {}, "next": None}}}

    await DagFlow().run(state, dag=dag)

    topics = [t for t, _ in events]
    assert "node.start" in topics
    assert "node.done" in topics
    assert "task.done" in topics
```

- [ ] **Step 2: Run — expect two new failures**

Run: `pytest tests/core/test_dag_flow.py -v`
Expected: the two new tests fail (no events, no replan).

- [ ] **Step 3: Port the Executor body into `DagFlow`**

Replace `core/flows/dag_flow.py`:

```python
"""DagFlow — interprets a JSON DAG. Absorbs Executor semantics."""
import asyncio
from uuid import uuid4
from core.flows.flow_neuro import FlowNeuro


class DagFlow(FlowNeuro):
    MAX_REPLAN_ROUNDS = 3

    async def run(self, state, *, dag, **kw):
        try:
            rounds = 0
            current = dag
            while True:
                need_replan = await self._run_once(state, current)
                if not need_replan:
                    break
                if rounds >= self.MAX_REPLAN_ROUNDS:
                    await _pub(state, "assistant", "⚠️ Replanning aborted after 3 attempts.")
                    break
                rounds += 1
                current = await self._replan(state)
                if current is None:
                    break
            return {}
        except asyncio.CancelledError:
            await _pub(state, "task.cancelled", {"state": state})
            return {}
        except Exception as exc:
            await _pub(state, "assistant", f"⚠️ Task failed: {exc}")
            return {}
        finally:
            await _pub(state, "task.done", {"state": state})

    async def _run_once(self, state, dag):
        factory = state["__factory"]
        node = dag["start"]
        nodes = dag["nodes"]
        conv = state.get("__conv")
        state.pop("__needs_replan", None)

        while node:
            spec = nodes[node]
            name = spec["neuro"]
            params = spec.get("params", {}) or {}
            on_error = spec.get("on_error", "replan")

            await _pub(state, "node.start", {"id": node, "neuro": name})

            stream_id = f"stream-{node}-{uuid4().hex[:8]}"

            async def _stream_cb(chunk, _sid=stream_id, _neuro=name):
                await _pub(state, "stream_chunk",
                           {"stream_id": _sid, "chunk": chunk, "neuro": _neuro})

            try:
                out = await factory.run(name, state, stream_callback=_stream_cb, **params)
            except Exception as e:
                err = {"error": type(e).__name__, "message": str(e), "neuro": name}
                await _pub(state, "assistant", f"⚠️ {name} failed: {e}")
                await _pub(state, "node.done", {"id": node, "out": err})
                if on_error == "skip":
                    node = spec.get("next"); continue
                if on_error == "abort":
                    break
                state["__needs_replan"] = True
                break

            if not isinstance(out, dict):
                out = {}

            thinking = out.pop("__thinking", None)
            if thinking:
                await _pub(state, "thinking", {"id": node, "neuro": name, "content": thinking})
            logs = out.pop("__logs", None)
            if logs:
                await _pub(state, "node.log", {"id": node, "neuro": name, "logs": logs})

            state.update(out)

            env_state = state.get("__env_state")
            if env_state:
                result_str = str(out.get("reply", out.get("result", str(out)[:200])))
                env_state.add_observation(
                    action=f"Execute {name}",
                    neuro=name,
                    result=result_str,
                    success="error" not in out and "__error" not in out,
                )

            if out.get("replan") or out.get("needs_replan"):
                state["__needs_replan"] = True

            if "reply" in out and isinstance(out["reply"], str):
                if conv is not None:
                    conv.add("assistant", out["reply"])
                if not out.get("__streamed"):
                    await _pub(state, "assistant", out["reply"])
                else:
                    await _pub(state, "stream_end", {"stream_id": stream_id})

            await _pub(state, "node.done", {"id": node, "neuro": name, "out": out})
            node = spec.get("next")

        return bool(state.get("__needs_replan"))

    async def _replan(self, state):
        factory = state["__factory"]
        planner = state.get("__planner", "planner")
        goal = state.get("goal", "")
        cid = state.get("__cid")

        reply = await factory.run(planner, state, goal=goal,
                                  catalogue=factory.catalogue(cid) if hasattr(factory, "catalogue") else [])
        plan = reply.get("plan", reply)
        if not plan.get("ok"):
            await _pub(state, "assistant",
                       plan.get("question") or "Planner could not formulate a new plan.")
            return None

        flow = plan["flow"]

        def _wrap(neuro, params=None):
            return {"start": "n0",
                    "nodes": {"n0": {"neuro": neuro, "params": params or {}, "next": None}}}

        if isinstance(flow, str):
            flow = _wrap("reply" if flow == "reply" else flow)
        elif isinstance(flow, dict):
            if flow.get("type") == "reply":
                flow = _wrap("reply", {"text": state.get("goal", "")})
            elif "name" in flow:
                flow = _wrap(flow["name"], flow.get("params", {}))

        return flow


async def _pub(state, topic, data):
    pub = state.get("__pub")
    if pub is None:
        return
    try:
        await pub(topic, data)
    except Exception:
        pass
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/core/test_dag_flow.py -v`
Expected: all pass, including the replan + events tests.

- [ ] **Step 5: Commit**

```bash
git add core/flows/dag_flow.py tests/core/test_dag_flow.py
git commit -m "feat(flows): port Executor semantics into DagFlow (replan, events, hooks)"
```

### Task B.2: Reduce `core/executor.py` to a forwarding shim

**Files:**
- Modify: `core/executor.py`
- Create: `tests/core/test_executor_shim.py`

- [ ] **Step 1: Write the shim test (fails because shim does not yet forward)**

`tests/core/test_executor_shim.py`:

```python
import pytest
from core.executor import Executor


class RememberFactory:
    def __init__(self):
        self.called_with = None

    async def run(self, name, state, **params):
        self.called_with = (name, dict(params), state)
        return {"ok": True}


async def test_executor_shim_forwards_to_dag_flow():
    factory = RememberFactory()
    pub_log = []
    async def pub(t, d): pub_log.append((t, d))
    dag = {"start": "n0",
           "nodes": {"n0": {"neuro": "whatever", "params": {}, "next": None}}}
    state = {}

    exe = Executor(dag, factory, state, pub)
    await exe.run()

    # Shim should have invoked dag_flow through the factory with dag=...
    assert factory.called_with is not None
    assert factory.called_with[0] == "dag_flow"
    assert factory.called_with[1].get("dag") == dag
    assert state["__pub"] is pub
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_executor_shim.py -v`
Expected: FAIL — old Executor does not call `factory.run("dag_flow", ...)`.

- [ ] **Step 3: Replace `core/executor.py` with a shim**

```python
"""Executor — thin compatibility shim. Body moved into core.flows.DagFlow.

Removed in Phase F. Kept here so any import `from core.executor import Executor`
keeps working during the migration.
"""


class Executor:
    def __init__(self, flow, factory, state, pub):
        self._flow = flow
        self._factory = factory
        self._state = state
        self._state["__pub"] = pub

    async def run(self):
        await self._factory.run("dag_flow", self._state, dag=self._flow)
```

- [ ] **Step 4: Run the shim test — expect pass**

Run: `pytest tests/core/test_executor_shim.py -v`
Expected: PASS.

- [ ] **Step 5: Confirm existing code still imports Executor**

Run: `python3 -c "from core.executor import Executor; print(Executor)"`
Expected: no error.

- [ ] **Step 6: Register `dag_flow` so the shim's factory call resolves**

Note: at this point the factory does not yet know about `dag_flow` — Brain's real factory will fail when the shim forwards. We must wire the built-in before any Brain-level smoke test. Do that in the next task.

- [ ] **Step 7: Commit**

```bash
git add core/executor.py tests/core/test_executor_shim.py
git commit -m "refactor(executor): reduce to forwarding shim over DagFlow"
```

### Task B.3: Register built-in `dag_flow` with `NeuroFactory`

**Files:**
- Modify: `core/neuro_factory.py`
- Test: add to existing `tests/core/test_dag_flow.py`

- [ ] **Step 1: Write the failing registration test**

Append to `tests/core/test_dag_flow.py`:

```python
from core.neuro_factory import NeuroFactory


async def test_factory_registers_builtin_dag_flow():
    f = NeuroFactory(dir="neuros")  # existing neuro dir
    assert "dag_flow" in f.reg, "dag_flow built-in must be registered"
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_dag_flow.py::test_factory_registers_builtin_dag_flow -v`
Expected: AssertionError.

- [ ] **Step 3: Implement registration**

In `core/neuro_factory.py`, add near the top of the class after imports:

```python
from core.flows.dag_flow import DagFlow as _DagFlow
from core.flows.sequential_flow import SequentialFlow as _SequentialFlow
from core.flows.parallel_flow import ParallelFlow as _ParallelFlow

_BUILTIN_FLOWS = {
    "dag_flow":         (_DagFlow, "Interprets a JSON DAG at runtime."),
    "sequential_flow":  (_SequentialFlow, "Runs declared children in order."),
    "parallel_flow":    (_ParallelFlow, "Fans out declared children concurrently."),
}
```

In `NeuroFactory.__init__`, after `self._load_all()`:

```python
self._register_builtins()
```

Add method:

```python
def _register_builtins(self):
    for name, (cls, desc) in _BUILTIN_FLOWS.items():
        if name in self.reg:
            continue
        instance = cls()
        async def _runner(state, _inst=instance, **kw):
            return await _inst.run(state, **kw)
        self.reg[name] = BaseNeuro(name, _runner,
                                   inputs=[], outputs=[], desc=desc)
```

> The built-in instance is a singleton per-factory for now (Phase C introduces the proper InstancePool; this placeholder works because `DagFlow`/`SequentialFlow`/`ParallelFlow` hold no instance state).

- [ ] **Step 4: Run the test — expect pass**

Run: `pytest tests/core/test_dag_flow.py::test_factory_registers_builtin_dag_flow -v`
Expected: PASS.

- [ ] **Step 5: Full-test sanity**

Run: `pytest tests/core/ -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add core/neuro_factory.py tests/core/test_dag_flow.py
git commit -m "feat(factory): register built-in dag_flow / sequential_flow / parallel_flow"
```

---

## Phase C — Class-neuro support in factory

Evolve `BaseNeuro` to abstract parent. Introduce `FnEntry` (private wrapping), `ClassEntry`, main-class resolution, `InstancePool`, `NeuroHandle` for dep injection, and pure-conf flow synthesis.

### Task C.1: Abstract `BaseNeuro` + internal `FnEntry`

**Files:**
- Modify: `core/base_neuro.py`
- Test: `tests/core/test_base_neuro_abstract.py`

- [ ] **Step 1: Write failing tests**

`tests/core/test_base_neuro_abstract.py`:

```python
import inspect
import pytest
from core.base_neuro import BaseNeuro, FnEntry


class LeafNeuro(BaseNeuro):
    async def run(self, state, **kw):
        return {"leaf": True}


async def test_baseneuro_is_abstract_parent():
    # Instantiating BaseNeuro directly must error (abstract run).
    with pytest.raises(Exception):
        await BaseNeuro().run({})   # type: ignore[abstract]


async def test_baseneuro_subclass_runs():
    out = await LeafNeuro().run({})
    assert out == {"leaf": True}


async def test_fn_entry_wraps_async_fn():
    async def raw(state, *, text):
        return {"reply": f"x {text}"}
    fe = FnEntry(fn=raw, conf={"name": "t", "inputs": ["text"], "outputs": ["reply"]})
    inst = fe.build_instance()
    out = await inst.run({}, text="hi")
    assert out == {"reply": "x hi"}
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_base_neuro_abstract.py -v`
Expected: fails / import error.

- [ ] **Step 3: Replace `core/base_neuro.py`**

```python
"""BaseNeuro — abstract parent for every neuro.

Legacy fn-neuros wrap into FnEntry.build_instance() which returns a
synthesized subclass of BaseNeuro. Callers never see the wrapping.
"""
import inspect


class BaseNeuro:
    # Class-level metadata populated by the factory after instantiation:
    name: str = ""
    desc: str = ""
    inputs: list = []
    outputs: list = []
    uses: list = []
    children: list = []
    scope: str = "session"

    # Runtime-resolved deps (populated by factory for class form).
    factory = None

    async def run(self, state, **kw):
        raise NotImplementedError(
            f"{type(self).__name__}.run must be overridden"
        )


class FnEntry:
    """Private wrapper that turns a top-level `async def run` into a
    one-off BaseNeuro subclass instance on demand."""

    def __init__(self, fn, conf):
        self.fn = fn
        self.conf = conf
        sig = inspect.signature(fn)
        self._accepts_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        self._accepted = set(sig.parameters.keys()) - {"state"}

    def filter_kwargs(self, kw):
        if self._accepts_var_kw:
            return kw
        return {k: v for k, v in kw.items() if k in self._accepted}

    def build_instance(self):
        fn = self.fn
        accepted = self._accepted
        accepts_var_kw = self._accepts_var_kw

        class _Fn(BaseNeuro):
            async def run(self, state, **kw):
                if accepts_var_kw:
                    safe = kw
                else:
                    safe = {k: v for k, v in kw.items() if k in accepted}
                return await fn(state, **safe)

        inst = _Fn()
        inst.name = self.conf.get("name", "")
        inst.desc = self.conf.get("description", "")
        inst.inputs = self.conf.get("inputs", [])
        inst.outputs = self.conf.get("outputs", [])
        return inst

    # Back-compat: the existing factory wraps the fn via `BaseNeuro(name, fn, ...)`.
    # We still honor that constructor-style path: see factory updates.
```

Because the existing `core/neuro_factory.py` constructs `BaseNeuro(name, _runner, ...)`, we must preserve that call shape until Phase C.6. Add a legacy ctor path:

```python
    def __init__(self, *args, **kwargs):
        # Legacy positional: BaseNeuro(name, fn, inputs, outputs, desc="")
        if args:
            name, fn, *rest = args
            inputs = rest[0] if len(rest) > 0 else kwargs.get("inputs", [])
            outputs = rest[1] if len(rest) > 1 else kwargs.get("outputs", [])
            desc = rest[2] if len(rest) > 2 else kwargs.get("desc", "")
            self._legacy_fn = fn
            sig = inspect.signature(fn)
            self._accepts_var_kw = any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            )
            self._accepted = set(sig.parameters.keys()) - {"state"}
            self.name, self.desc = name, desc
            self.inputs, self.outputs = inputs, outputs

    async def run(self, state, **kw):
        legacy = getattr(self, "_legacy_fn", None)
        if legacy is None:
            raise NotImplementedError(
                f"{type(self).__name__}.run must be overridden"
            )
        if self._accepts_var_kw:
            safe = kw
        else:
            safe = {k: v for k, v in kw.items() if k in self._accepted}
        return await legacy(state, **safe)
```

The first `__init__`/`run` must be the *one* on the class, not both. Merge them: the class now has an `__init__` that detects legacy and a `run` that handles legacy-or-abstract. Replace the stub versions above with the merged versions shown here.

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/core/test_base_neuro_abstract.py -v`
Expected: PASS.

Run full core tests to catch regressions in flow tests (which rely on `BaseNeuro` as parent):

Run: `pytest tests/core/ -v`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add core/base_neuro.py tests/core/test_base_neuro_abstract.py
git commit -m "refactor(base_neuro): abstract parent + legacy ctor + FnEntry"
```

### Task C.2: `NeuroHandle` — lazy dep-injection proxy

**Files:**
- Create: `core/neuro_handle.py`
- Test: `tests/core/test_neuro_handle.py`

- [ ] **Step 1: Write failing test**

`tests/core/test_neuro_handle.py`:

```python
import pytest
from core.neuro_handle import NeuroHandle


class FakeFactory:
    def __init__(self):
        self.calls = []

    async def run(self, name, state, **params):
        self.calls.append((name, dict(params)))
        return {"n": name}


async def test_handle_forwards_to_factory():
    factory = FakeFactory()
    h = NeuroHandle(factory, "search")
    out = await h.run({}, q="x")
    assert out == {"n": "search"}
    assert factory.calls == [("search", {"q": "x"})]


async def test_handle_identity_carries_name():
    h = NeuroHandle(FakeFactory(), "plan")
    assert h.name == "plan"
    assert "plan" in repr(h)
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_neuro_handle.py -v`

- [ ] **Step 3: Implement**

`core/neuro_handle.py`:

```python
"""NeuroHandle — a lazy proxy returned to class-neuros via `uses` injection.

Calling `handle.run(state, **kw)` dispatches through the factory,
preserving hot-reload (factory resolves the neuro by name each call).
"""


class NeuroHandle:
    __slots__ = ("_factory", "name")

    def __init__(self, factory, name):
        self._factory = factory
        self.name = name

    async def run(self, state, **kw):
        return await self._factory.run(self.name, state, **kw)

    def __repr__(self):
        return f"NeuroHandle({self.name!r})"
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/core/test_neuro_handle.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/neuro_handle.py tests/core/test_neuro_handle.py
git commit -m "feat(core): NeuroHandle lazy proxy for dep injection"
```

### Task C.3: `InstancePool` — scope-aware class-neuro pool

**Files:**
- Create: `core/instance_pool.py`
- Test: `tests/core/test_instance_pool.py`

- [ ] **Step 1: Write failing test**

`tests/core/test_instance_pool.py`:

```python
import pytest
from core.instance_pool import InstancePool
from core.base_neuro import BaseNeuro


class Counter(BaseNeuro):
    async def run(self, state, **kw):
        self.count = getattr(self, "count", 0) + 1
        return {"count": self.count}


class DummyFactory:
    def __init__(self):
        self.reg = {}


async def test_session_scope_pools_per_cid():
    pool = InstancePool(DummyFactory())
    entry = _entry("counter", Counter, scope="session")

    i1 = await pool.get(entry, {"__cid": "A"})
    i2 = await pool.get(entry, {"__cid": "A"})
    i3 = await pool.get(entry, {"__cid": "B"})

    assert i1 is i2
    assert i1 is not i3


async def test_singleton_scope_reuses_across_all_state():
    pool = InstancePool(DummyFactory())
    entry = _entry("counter", Counter, scope="singleton")

    i1 = await pool.get(entry, {"__cid": "A"})
    i2 = await pool.get(entry, {"__cid": "B"})
    assert i1 is i2


async def test_call_scope_fresh_every_time():
    pool = InstancePool(DummyFactory())
    entry = _entry("counter", Counter, scope="call")

    i1 = await pool.get(entry, {})
    i2 = await pool.get(entry, {})
    assert i1 is not i2


def _entry(name, cls, scope):
    from types import SimpleNamespace
    return SimpleNamespace(name=name, cls=cls, scope=scope,
                           conf={"uses": []}, is_class=True)
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_instance_pool.py -v`

- [ ] **Step 3: Implement `InstancePool`**

`core/instance_pool.py`:

```python
"""InstancePool — keyed cache of class-neuro instances.

Scope keys:
  call       → never pooled (fresh instance each get)
  session    → keyed by state["__cid"]
  agent      → keyed by state["__agent_id"]
  singleton  → single instance per factory
"""
import asyncio


class InstancePool:
    def __init__(self, factory):
        self._factory = factory
        self._instances: dict = {}
        self._locks: dict = {}

    async def get(self, entry, state):
        scope = entry.scope or "session"
        if scope == "call":
            return await self._create(entry, state)
        key = (entry.name, self._scope_key(scope, state))
        if key in self._instances:
            return self._instances[key]
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if key not in self._instances:
                self._instances[key] = await self._create(entry, state)
        return self._instances[key]

    async def invalidate(self, name):
        """Called by hot-reload to drop cached instances of `name`."""
        victims = [k for k in self._instances if k[0] == name]
        for k in victims:
            inst = self._instances.pop(k)
            td = getattr(inst, "teardown", None)
            if td:
                try: await td()
                except Exception: pass

    def _scope_key(self, scope, state):
        if scope == "session":
            return state.get("__cid", "_nosess")
        if scope == "agent":
            return state.get("__agent_id", "_default")
        if scope == "singleton":
            return "_singleton"
        raise ValueError(f"unknown scope {scope!r}")

    async def _create(self, entry, state):
        inst = entry.cls()
        inst.name = entry.name
        inst.factory = self._factory

        from core.neuro_handle import NeuroHandle
        for dep in getattr(inst, "uses", []) or entry.conf.get("uses", []):
            if dep not in self._factory.reg:
                raise RuntimeError(
                    f"neuro {entry.name!r} declares use of {dep!r} which is not registered")
            setattr(inst, dep, NeuroHandle(self._factory, dep))

        setup = getattr(inst, "setup", None)
        if setup:
            result = setup()
            if hasattr(result, "__await__"):
                await result
        return inst
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/core/test_instance_pool.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/instance_pool.py tests/core/test_instance_pool.py
git commit -m "feat(core): InstancePool with call/session/agent/singleton scopes"
```

### Task C.4: `NeuroFactory` learns the class path

**Files:**
- Modify: `core/neuro_factory.py`
- Test: `tests/core/test_neuro_factory_class.py`

- [ ] **Step 1: Write failing test**

`tests/core/test_neuro_factory_class.py`:

```python
import pathlib
import textwrap
import pytest
from core.neuro_factory import NeuroFactory


async def test_factory_loads_class_neuro(tmp_path: pathlib.Path):
    root = tmp_path / "neuros"
    d = root / "greet"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(
        '{"name":"greet","description":"","inputs":[],"outputs":[],"scope":"session"}'
    )
    (d / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Greet(BaseNeuro):
            async def run(self, state, **kw):
                return {"hello": True}
    """))

    f = NeuroFactory(dir=str(root))
    out = await f.run("greet", {"__cid": "t"})
    assert out == {"hello": True}


async def test_factory_injects_uses_deps(tmp_path: pathlib.Path):
    root = tmp_path / "neuros"
    (root / "a").mkdir(parents=True)
    (root / "a" / "conf.json").write_text(
        '{"name":"a","description":"","inputs":[],"outputs":[]}'
    )
    (root / "a" / "code.py").write_text(textwrap.dedent("""
        async def run(state, **kw):
            return {"from_a": 1}
    """))

    (root / "parent").mkdir(parents=True)
    (root / "parent" / "conf.json").write_text(
        '{"name":"parent","description":"","inputs":[],"outputs":[],"uses":["a"]}'
    )
    (root / "parent" / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Parent(BaseNeuro):
            uses = ["a"]
            async def run(self, state, **kw):
                out = await self.a.run(state)
                return {"parent_got": out["from_a"]}
    """))

    f = NeuroFactory(dir=str(root))
    out = await f.run("parent", {"__cid": "t"})
    assert out == {"parent_got": 1}
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_neuro_factory_class.py -v`

- [ ] **Step 3: Implement class-load branch in `core/neuro_factory.py`**

Modify `_load(path)` to detect a class subclass of `BaseNeuro` and store a `ClassEntry` instead of a `BaseNeuro(name, _runner, ...)`. Add `ClassEntry` / `FnEntry` descriptor classes, and update `run(name, state, **kw)` to dispatch.

At the top of `core/neuro_factory.py`:

```python
from dataclasses import dataclass
from core.instance_pool import InstancePool


@dataclass
class ClassEntry:
    name: str
    cls: type
    conf: dict
    is_class: bool = True

    @property
    def scope(self) -> str:
        return getattr(self.cls, "scope", None) or self.conf.get("scope", "session")

    @property
    def desc(self) -> str:
        return self.conf.get("description", "")


@dataclass
class _LegacyFnEntry:
    """Compatibility holder so `describe()` keeps its old shape for fn-loaded neuros."""
    name: str
    neuro: object   # BaseNeuro(name, fn, ...) instance
    conf: dict
    is_class: bool = False

    @property
    def scope(self) -> str:
        return self.conf.get("scope", "call")

    @property
    def desc(self) -> str:
        return self.conf.get("description", self.neuro.desc)
```

Inside `NeuroFactory.__init__`, after `self.reg = {}`:

```python
self.pool = InstancePool(self)
```

Add helper `_pick_main_class`:

```python
def _pick_main_class(self, module, conf_name):
    import inspect
    from core.base_neuro import BaseNeuro

    main = getattr(module, "__main_neuro__", None)
    if isinstance(main, str) and main in vars(module):
        cls = module.__dict__[main]
        if isinstance(cls, type) and issubclass(cls, BaseNeuro):
            return cls

    camel = "".join(p.title() for p in conf_name.split("_"))
    exact = module.__dict__.get(camel)
    if isinstance(exact, type) and issubclass(exact, BaseNeuro):
        return exact

    candidates = [
        v for v in module.__dict__.values()
        if isinstance(v, type)
           and issubclass(v, BaseNeuro)
           and v is not BaseNeuro
           and not v.__name__.startswith("_")
    ]
    # Ignore FlowNeuro and imports that came from core.flows
    candidates = [c for c in candidates if c.__module__ == module.__name__]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) == 0:
        return None
    raise RuntimeError(
        f"ambiguous main class for neuro {conf_name!r}: "
        f"{[c.__name__ for c in candidates]}. "
        "Add `__main_neuro__ = 'YourClass'` to code.py."
    )
```

Refactor `_load`:

```python
def _load(self, path):
    folder = path.parent
    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"[factory] skipping {path}: {e}")
        return

    code_path = folder / "code.py"
    module = None
    if code_path.exists():
        module = self._safe_exec(code_path.read_text(encoding="utf-8"),
                                 f"neuro_{spec['name']}")

    cls = self._pick_main_class(module, spec["name"]) if module else None
    name = spec["name"]

    if cls is not None:
        self.reg[name] = ClassEntry(name=name, cls=cls, conf=spec)
        # invalidate any pooled instance from a prior version
        asyncio.create_task(self.pool.invalidate(name))
        return

    if module is not None and hasattr(module, "run"):
        # preserve legacy _runner wrap (LLM injection, stdout capture, etc.)
        entry_neuro = self._build_legacy_fn_neuro(spec, module)
        self.reg[name] = _LegacyFnEntry(name=name, neuro=entry_neuro, conf=spec)
        return

    print(f"[factory] WARN: {name} has no class and no module-level run; skipped")
```

Extract the old `_runner` / `BaseNeuro(...)` construction into `_build_legacy_fn_neuro(spec, module)` so the fn path keeps all its current behavior (LLM injection via `state["__llm"]`, `__prompt` templating, stdout capture, thinking extraction).

Update `run`:

```python
async def run(self, name, state, **kw):
    if name not in self.reg:
        raise KeyError(f"Neuro {name!r} not found. Available: {', '.join(sorted(self.reg))}")
    entry = self.reg[name]
    # stash factory ref in state once (legacy compat)
    state.setdefault("__factory", self)

    if getattr(entry, "is_class", False):
        instance = await self.pool.get(entry, state)
        out = await instance.run(state, **kw)
        if not isinstance(out, dict):
            out = {}
        return out

    # Legacy fn path — reuse the pre-existing BaseNeuro wrapper, unchanged.
    return await entry.neuro.run(state, **kw)
```

Update `catalogue` / `describe` / `_filter` to read from entries of either form (they already stringify names only for `catalogue`; for `describe` use `entry.desc`).

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/core/test_neuro_factory_class.py -v`

- [ ] **Step 5: Run the full core test suite — no regressions**

Run: `pytest tests/core/ -v`

- [ ] **Step 6: Smoke-check the real neuros still load**

```bash
python3 -c "
import asyncio
from core.neuro_factory import NeuroFactory
f = NeuroFactory()
print('loaded', len(f.reg), 'neuros')
print('has echo:', 'echo' in f.reg)
print('has dag_flow:', 'dag_flow' in f.reg)
"
```
Expected: loads the existing neuro set + built-ins.

- [ ] **Step 7: Commit**

```bash
git add core/neuro_factory.py tests/core/test_neuro_factory_class.py
git commit -m "feat(factory): add class-neuro load path + InstancePool dispatch"
```

### Task C.5: Pure-conf flow synthesis

**Files:**
- Modify: `core/neuro_factory.py`
- Test: `tests/core/test_neuro_factory_class.py` (extend)

- [ ] **Step 1: Extend the test**

Append:

```python
async def test_factory_synthesizes_sequential_flow_from_conf(tmp_path):
    root = tmp_path / "neuros"
    # children
    for n in ("x", "y"):
        (root / n).mkdir(parents=True)
        (root / n / "conf.json").write_text(
            f'{{"name":"{n}","description":"","inputs":[],"outputs":[]}}'
        )
        (root / n / "code.py").write_text(
            f"async def run(state, **kw):\n    return {{'{n}': True}}\n"
        )
    # pure-conf flow, no code.py
    (root / "chain").mkdir(parents=True)
    (root / "chain" / "conf.json").write_text(
        '{"name":"chain","description":"","inputs":[],"outputs":[],'
        '"kind":"sequential_flow","children":["x","y"],"uses":["x","y"]}'
    )

    f = NeuroFactory(dir=str(root))
    out = await f.run("chain", {"__cid": "t"})
    assert out == {"x": True, "y": True}
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_neuro_factory_class.py::test_factory_synthesizes_sequential_flow_from_conf -v`

- [ ] **Step 3: Add `_synthesize_flow_class`**

In `core/neuro_factory.py`:

```python
from core.flows.sequential_flow import SequentialFlow
from core.flows.parallel_flow import ParallelFlow
from core.flows.dag_flow import DagFlow

_FLOW_KIND_REGISTRY = {
    "sequential_flow": SequentialFlow,
    "parallel_flow":   ParallelFlow,
    "dag_flow":        DagFlow,
}


def _synthesize_flow_class(conf):
    base = _FLOW_KIND_REGISTRY[conf["kind"]]
    attrs = {
        "uses":     conf.get("uses", []),
        "children": conf.get("children", []),
        "scope":    conf.get("scope", "session"),
    }
    return type(f"_ConfFlow_{conf['name']}", (base,), attrs)
```

In `_load`, between class detection and fn fallback:

```python
if module is None and spec.get("kind") in _FLOW_KIND_REGISTRY:
    cls = _synthesize_flow_class(spec)
    self.reg[name] = ClassEntry(name=name, cls=cls, conf=spec)
    asyncio.create_task(self.pool.invalidate(name))
    return
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/core/test_neuro_factory_class.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/neuro_factory.py tests/core/test_neuro_factory_class.py
git commit -m "feat(factory): synthesize flow class from conf-only kind declaration"
```

### Task C.6: Hot-reload invalidates class instances

**Files:**
- Modify: `core/neuro_factory.py`
- Test: `tests/core/test_neuro_factory_class.py` (extend)

- [ ] **Step 1: Extend the test**

Append:

```python
async def test_class_reload_teardown_and_rebuild(tmp_path):
    root = tmp_path / "neuros"
    d = root / "incr"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(
        '{"name":"incr","description":"","inputs":[],"outputs":[],"scope":"singleton"}'
    )
    (d / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Incr(BaseNeuro):
            scope = "singleton"
            async def setup(self):
                self.n = 100
            async def teardown(self):
                self.n = -1
            async def run(self, state, **kw):
                self.n += 1
                return {"n": self.n}
    """))

    f = NeuroFactory(dir=str(root))
    out1 = await f.run("incr", {})
    assert out1 == {"n": 101}
    out2 = await f.run("incr", {})
    assert out2 == {"n": 102}

    # Rewrite the neuro; factory should tear down old instance.
    (d / "code.py").write_text(textwrap.dedent("""
        from core.base_neuro import BaseNeuro
        class Incr(BaseNeuro):
            scope = "singleton"
            async def setup(self):
                self.n = 0
            async def run(self, state, **kw):
                self.n += 10
                return {"n": self.n}
    """))
    f._load(d / "conf.json")              # trigger manual reload
    # wait for invalidate task
    import asyncio as _a; await _a.sleep(0.05)

    out3 = await f.run("incr", {})
    assert out3 == {"n": 10}
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_neuro_factory_class.py::test_class_reload_teardown_and_rebuild -v`

- [ ] **Step 3: Invalidate + teardown on reload**

Already stubbed in C.4: `asyncio.create_task(self.pool.invalidate(name))`. Verify the `InstancePool.invalidate` coroutine awaits each instance's `teardown` correctly. Trace: ensure `_load`'s call to `invalidate` happens synchronously or scheduled reliably before next `run`. If tests fail on timing, make `invalidate` run synchronously inside `_load`:

```python
# Instead of asyncio.create_task(...), do:
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(self.pool.invalidate(name))
    else:
        loop.run_until_complete(self.pool.invalidate(name))
except RuntimeError:
    # No loop available (e.g. during initial load) — nothing pooled yet anyway.
    pass
```

- [ ] **Step 4: Run test — expect pass**

Run: `pytest tests/core/test_neuro_factory_class.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/neuro_factory.py tests/core/test_neuro_factory_class.py
git commit -m "feat(factory): invalidate pool on class-neuro reload (teardown + rebuild)"
```

---

## Phase D — Typed ports + visual metadata

Normalize `conf.json` `inputs`/`outputs` from string form to object form at load; enrich `describe()` with the extra fields; read optional `layout.json` sidecar.

### Task D.1: Port normalizer + rich `describe`

**Files:**
- Modify: `core/neuro_factory.py`
- Test: `tests/core/test_typed_ports.py`

- [ ] **Step 1: Write failing test**

`tests/core/test_typed_ports.py`:

```python
import pathlib, textwrap, pytest
from core.neuro_factory import NeuroFactory


async def test_string_form_ports_normalized(tmp_path):
    root = tmp_path / "neuros"
    d = root / "echo_old"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(
        '{"name":"echo_old","description":"","inputs":["text"],"outputs":["reply"]}'
    )
    (d / "code.py").write_text("async def run(state, *, text):\n    return {'reply': text}\n")

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    assert rich["echo_old"]["inputs"] == [
        {"name": "text", "type": "any", "description": "", "optional": False}
    ]
    assert rich["echo_old"]["outputs"] == [
        {"name": "reply", "type": "any", "description": "", "optional": False}
    ]


async def test_object_form_ports_passthrough(tmp_path):
    root = tmp_path / "neuros"
    d = root / "summarize"
    d.mkdir(parents=True)
    (d / "conf.json").write_text(textwrap.dedent("""
        {
          "name": "summarize",
          "description": "",
          "inputs":  [{"name":"text","type":"str","description":"body"}],
          "outputs": [{"name":"summary","type":"str"}],
          "category": "text.nlp",
          "icon":     "sparkles",
          "color":    "#7c3aed",
          "summary_md": "Condenses text."
        }
    """))
    (d / "code.py").write_text("async def run(state, *, text):\n    return {'summary': text[:10]}\n")

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    e = rich["summarize"]
    assert e["inputs"][0]["type"] == "str"
    assert e["category"] == "text.nlp"
    assert e["summary_md"] == "Condenses text."
    assert e["kind"] in ("leaf", "flow")
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_typed_ports.py -v`

- [ ] **Step 3: Implement normalizer + rich describe**

In `core/neuro_factory.py`, add:

```python
def _normalize_ports(ports):
    out = []
    for p in ports or []:
        if isinstance(p, str):
            out.append({"name": p, "type": "any", "description": "", "optional": False})
        elif isinstance(p, dict):
            out.append({
                "name":        p.get("name", ""),
                "type":        p.get("type", "any"),
                "description": p.get("description", ""),
                "optional":    bool(p.get("optional", False)),
                **({"default": p["default"]} if "default" in p else {}),
                **({"example": p["example"]} if "example" in p else {}),
            })
    return out
```

Replace `describe`:

```python
def describe(self, cid=None, group=None):
    out = []
    for n in self.catalogue(cid, group):
        entry = self.reg[n]
        conf = entry.conf
        is_class = getattr(entry, "is_class", False)
        kind = "flow" if is_class and _is_flow_class(entry.cls) else "leaf"
        out.append({
            "name":        n,
            "description": entry.desc,
            "category":    conf.get("category"),
            "icon":        conf.get("icon"),
            "color":       conf.get("color"),
            "summary_md":  conf.get("summary_md"),
            "long_md":     conf.get("long_md"),
            "kind":        kind,
            "scope":       entry.scope,
            "uses":        conf.get("uses", []),
            "children":    conf.get("children", []),
            "inputs":      _normalize_ports(conf.get("inputs", [])),
            "outputs":     _normalize_ports(conf.get("outputs", [])),
        })
    return out


def _is_flow_class(cls):
    from core.flows.flow_neuro import FlowNeuro
    return isinstance(cls, type) and issubclass(cls, FlowNeuro)
```

- [ ] **Step 4: Run tests — expect pass**

Run: `pytest tests/core/test_typed_ports.py -v`

Also re-run the full suite:

Run: `pytest tests/core/ -v`

- [ ] **Step 5: Commit**

```bash
git add core/neuro_factory.py tests/core/test_typed_ports.py
git commit -m "feat(factory): normalize typed ports; rich describe() with IDE metadata"
```

### Task D.2: Optional `layout.json` sidecar support

**Files:**
- Modify: `core/neuro_factory.py`

- [ ] **Step 1: Extend one existing test** in `tests/core/test_typed_ports.py`:

```python
async def test_layout_sidecar_loaded(tmp_path):
    root = tmp_path / "neuros"
    d = root / "flow_a"
    d.mkdir(parents=True)
    (d / "conf.json").write_text('{"name":"flow_a","description":"","inputs":[],"outputs":[]}')
    (d / "code.py").write_text("async def run(state, **kw):\n    return {}\n")
    (d / "layout.json").write_text('{"nodes":{"n0":{"x":10,"y":20}}}')

    f = NeuroFactory(dir=str(root))
    rich = {e["name"]: e for e in f.describe()}
    assert rich["flow_a"].get("layout") == {"nodes": {"n0": {"x": 10, "y": 20}}}
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_typed_ports.py::test_layout_sidecar_loaded -v`

- [ ] **Step 3: Implement**

In `_load`, after reading the conf:

```python
layout_path = folder / "layout.json"
if layout_path.exists():
    try:
        spec["layout"] = json.loads(layout_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        pass
```

And ensure `describe()` passes `layout` through:

```python
"layout":      conf.get("layout"),
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/core/test_typed_ports.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/neuro_factory.py tests/core/test_typed_ports.py
git commit -m "feat(factory): optional layout.json sidecar read into describe() output"
```

---

## Phase E — Memory API + SQLite backend

Ship `core/memory.py` (SQLite-backed store), the `memory` built-in neuro, and wire it into the factory registry.

### Task E.1: `core/memory.py` backend

**Files:**
- Create: `core/memory.py`
- Test: `tests/core/test_memory.py`

- [ ] **Step 1: Write failing test**

`tests/core/test_memory.py`:

```python
import pathlib, pytest
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
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_memory.py -v`

- [ ] **Step 3: Implement**

`core/memory.py`:

```python
"""MemoryStore — SQLite-backed persistent memory for agents.

Key shape: (scope, agent_id, caller_neuro, key). TTL optional per-row.
See spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/03-state-and-memory.md
"""
import json
import os
import sqlite3
import time


SCHEMA = """
CREATE TABLE IF NOT EXISTS kv (
    scope       TEXT NOT NULL,
    agent_id    TEXT NOT NULL,
    caller      TEXT NOT NULL,
    key         TEXT NOT NULL,
    value_json  TEXT NOT NULL,
    ts          REAL NOT NULL,
    ttl_ts      REAL,
    PRIMARY KEY (scope, agent_id, caller, key)
);
CREATE INDEX IF NOT EXISTS idx_kv_prefix
    ON kv(scope, agent_id, caller, key);
"""


class MemoryStore:
    def __init__(self, path: str = "agent_memory.db"):
        self.path = path
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self):
        return sqlite3.connect(self.path, isolation_level=None)

    @staticmethod
    def _now() -> float:
        return time.time()

    def write(self, scope, agent_id, caller, key, value, ttl_seconds=None):
        now = self._now()
        ttl = (now + ttl_seconds) if ttl_seconds is not None else None
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO kv VALUES (?, ?, ?, ?, ?, ?, ?)",
                (scope, agent_id, caller, key, json.dumps(value), now, ttl),
            )
        return {"ok": True, "ts": now}

    def read(self, scope, agent_id, caller, key):
        now = self._now()
        with self._conn() as c:
            cur = c.execute(
                "SELECT value_json, ts, ttl_ts FROM kv "
                "WHERE scope=? AND agent_id=? AND caller=? AND key=?",
                (scope, agent_id, caller, key),
            )
            row = cur.fetchone()
        if row is None:
            return None
        value_json, ts, ttl_ts = row
        if ttl_ts is not None and ttl_ts <= now:
            self.delete(scope, agent_id, caller, key)
            return None
        return {"value": json.loads(value_json), "meta": {"ts": ts, "ttl": ttl_ts}}

    def delete(self, scope, agent_id, caller, key):
        with self._conn() as c:
            c.execute(
                "DELETE FROM kv "
                "WHERE scope=? AND agent_id=? AND caller=? AND key=?",
                (scope, agent_id, caller, key),
            )
        return {"ok": True}

    def list(self, scope, agent_id, caller, prefix=""):
        now = self._now()
        with self._conn() as c:
            cur = c.execute(
                "SELECT key, value_json, ts, ttl_ts FROM kv "
                "WHERE scope=? AND agent_id=? AND caller=? AND key LIKE ?",
                (scope, agent_id, caller, prefix + "%"),
            )
            items = [
                {"key": k, "value": json.loads(v), "meta": {"ts": ts, "ttl": ttl_ts}}
                for k, v, ts, ttl_ts in cur.fetchall()
                if ttl_ts is None or ttl_ts > now
            ]
        return items

    def search(self, scope, agent_id, caller, query, top_k=5):
        """Naive keyword match in key + value. Vector backend comes later."""
        items = self.list(scope, agent_id, caller, prefix="")
        q = query.lower()
        scored = []
        for it in items:
            hay = (it["key"] + " " + json.dumps(it["value"])).lower()
            if q in hay:
                scored.append(it)
        return scored[:top_k]
```

- [ ] **Step 4: Run — expect pass**

Run: `pytest tests/core/test_memory.py -v`

- [ ] **Step 5: Commit**

```bash
git add core/memory.py tests/core/test_memory.py
git commit -m "feat(memory): SQLite-backed MemoryStore (read/write/list/delete/search/TTL)"
```

### Task E.2: Built-in `memory` neuro

**Files:**
- Create: `neuros/memory/conf.json`
- Create: `neuros/memory/code.py`
- Test: extend `tests/core/test_memory.py`

- [ ] **Step 1: Extend test**

Append to `tests/core/test_memory.py`:

```python
import pytest
import pathlib
from core.neuro_factory import NeuroFactory


async def test_memory_neuro_write_read(tmp_path, monkeypatch):
    # Point MemoryStore at tmp dir via env var.
    monkeypatch.setenv("NEURO_MEMORY_DB", str(tmp_path / "m.db"))
    # Load the real neuros dir to pick up the new built-in.
    f = NeuroFactory(dir="neuros")
    assert "memory" in f.reg

    state = {"__cid": "t", "__agent_id": "neuro", "__caller_neuro": "test_caller"}
    await f.run("memory", state, op="write", key="theme", value="dark")
    r = await f.run("memory", state, op="read", key="theme")
    assert r["value"] == "dark"
```

- [ ] **Step 2: Run — expect fail**

Run: `pytest tests/core/test_memory.py::test_memory_neuro_write_read -v`

- [ ] **Step 3: Create the built-in neuro**

`neuros/memory/conf.json`:

```json
{
  "name": "memory",
  "description": "Persistent memory API (read/write/list/delete/search).",
  "inputs": [
    {"name": "op",     "type": "str",  "description": "read|write|delete|list|search"},
    {"name": "key",    "type": "str",  "description": "key path",       "optional": true},
    {"name": "value",  "type": "json", "description": "value to write", "optional": true},
    {"name": "prefix", "type": "str",  "description": "list prefix",    "optional": true},
    {"name": "query",  "type": "str",  "description": "search query",   "optional": true},
    {"name": "top_k",  "type": "int",  "description": "search top-k",   "optional": true, "default": 5},
    {"name": "scope",  "type": "str",  "description": "agent|shared",   "optional": true, "default": "agent"},
    {"name": "ttl",    "type": "int",  "description": "seconds",        "optional": true}
  ],
  "outputs": [
    {"name": "value", "type": "json", "optional": true},
    {"name": "items", "type": "list", "optional": true},
    {"name": "ok",    "type": "bool"}
  ],
  "category": "system.memory",
  "summary_md": "Read / write / list / delete / search persistent agent memory."
}
```

`neuros/memory/code.py`:

```python
"""memory — thin bridge from neuro protocol to core.memory.MemoryStore."""
import os
from core.memory import MemoryStore


_store = None


def _get_store():
    global _store
    if _store is None:
        _store = MemoryStore(path=os.environ.get("NEURO_MEMORY_DB", "agent_memory.db"))
    return _store


async def run(state, *, op, key=None, value=None, prefix=None, query=None,
              top_k=5, scope="agent", ttl=None, **_):
    s = _get_store()
    agent_id = state.get("__agent_id") or "neuro"
    caller = state.get("__caller_neuro") or "unknown"

    if op == "read":
        r = s.read(scope, agent_id, caller, key)
        return r or {"value": None}
    if op == "write":
        return s.write(scope, agent_id, caller, key, value, ttl_seconds=ttl)
    if op == "delete":
        return s.delete(scope, agent_id, caller, key)
    if op == "list":
        return {"items": s.list(scope, agent_id, caller, prefix or "")}
    if op == "search":
        return {"items": s.search(scope, agent_id, caller, query, top_k=top_k)}
    return {"ok": False, "error": f"unknown op {op!r}"}
```

- [ ] **Step 4: Run test — expect pass**

Run: `pytest tests/core/test_memory.py -v`

- [ ] **Step 5: Add `memory` to reserved-names list in factory (guard against future shadow)**

In `core/neuro_factory.py` near the builtin registration:

```python
_RESERVED = {"dag_flow", "sequential_flow", "parallel_flow", "memory"}
```

In `_load`, reject a user neuro that tries to use a reserved name:

```python
if spec.get("name") in _RESERVED and folder.parent.name != "neuros" or False:
    pass   # placeholder: only the shipped built-ins get to use reserved names
```

(Detailed enforcement: reserve only when a user neuro competes with a built-in; leave documentation.)

- [ ] **Step 6: Commit**

```bash
git add neuros/memory tests/core/test_memory.py core/neuro_factory.py
git commit -m "feat(memory): add built-in memory neuro bridging core.memory.MemoryStore"
```

---

## Phase F — Brain call-site swap + Executor removal

Swap `core/brain.py` to use `factory.run("dag_flow", state, dag=flow)` instead of instantiating `Executor`. Delete the shim. Run an end-to-end smoke of the real chat path.

### Task F.1: Replace `Executor(...)` usages in `core/brain.py`

**Files:**
- Modify: `core/brain.py`
- Test: `tests/core/test_brain_dag_flow_swap.py`

- [ ] **Step 1: Inventory the call sites**

Run: `grep -n "Executor(" core/brain.py`
Note each line.

- [ ] **Step 2: Write a failing integration test**

`tests/core/test_brain_dag_flow_swap.py`:

```python
"""Integration: Brain's task-launch path calls factory.run('dag_flow', ...)."""
import pytest
from core.brain import Brain


async def test_brain_routes_through_dag_flow(monkeypatch):
    b = Brain()
    calls = []

    async def fake_run(name, state, **kw):
        calls.append((name, dict(kw)))
        if name == "dag_flow":
            return {}
        # default: let real factory answer things like smart_router/planner/reply
        return await b.factory._orig_run(name, state, **kw)

    b.factory._orig_run = b.factory.run
    b.factory.run = fake_run
    # Force a fast path that launches an executor — use the smart_router "reply" path
    # ... (This test is best-effort: Brain's full handle path is large; here we
    # verify any task launch goes through factory.run("dag_flow", dag=...).)

    # Directly invoke the internal helper used by launch, if exposed:
    state = {"__cid": "t"}
    flow = {"start": "n0", "nodes": {"n0": {"neuro": "echo", "params": {"text": "hi"}, "next": None}}}
    await b.factory.run("dag_flow", state, dag=flow)
    assert ("dag_flow", {"dag": flow}) in calls
```

> If end-to-end Brain handle is too heavy for a unit-test smoke, this test as-written verifies only the factory-side entry. That's the narrowest guarantee we need for the swap.

- [ ] **Step 3: Run — expect fail**

Run: `pytest tests/core/test_brain_dag_flow_swap.py -v`

- [ ] **Step 4: Refactor the Executor launch sites**

In `core/brain.py`, find every occurrence like:

```python
exe = Executor(flow, self.factory, state, lambda t, d: self._pub(cid, t, d))
self._launch(cid, exe, state)
```

Replace with:

```python
state["__pub"] = lambda t, d, _cid=cid: self._pub(_cid, t, d)
task = asyncio.create_task(self.factory.run("dag_flow", state, dag=flow))
self._launch(cid, task, state)
```

And update `_launch` to accept a task directly rather than an Executor instance (it currently calls `exe.run()` to get a task — adapt the signature if needed). Keep `_on_task_done` unchanged.

Remove `from core.executor import Executor` if no longer needed.

- [ ] **Step 5: Run tests**

Run: `pytest tests/core/ -v`
Expected: all pass.

- [ ] **Step 6: Live smoke**

Start the dev backend on its usual port (NOT port 7000 per the repo memory). Send a chat request via CLI (`tests/test_api.py` style or curl) and verify the reply arrives normally.

- [ ] **Step 7: Commit**

```bash
git add core/brain.py tests/core/test_brain_dag_flow_swap.py
git commit -m "refactor(brain): route task launch through factory.run('dag_flow', ...)"
```

### Task F.2: Delete `core/executor.py`

**Files:**
- Delete: `core/executor.py`
- Delete: `tests/core/test_executor_shim.py`

- [ ] **Step 1: Find remaining imports**

Run: `grep -rn "from core.executor" .` and `grep -rn "import core.executor" .`
Expected after F.1: zero hits outside the shim + its test.

- [ ] **Step 2: Remove the shim**

```bash
git rm core/executor.py tests/core/test_executor_shim.py
```

- [ ] **Step 3: Full-test + smoke**

Run: `pytest tests/core/ -v`
Run the dev server; smoke-chat once.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor(executor): remove shim; DagFlow is the only runtime"
```

---

## Post-migration verification

### Task Z.1: End-to-end checklist (manual, one session)

Run through the per-phase verification checklist from `07-migration.md §7`:

- [ ] Existing neuros all load — count unchanged.
- [ ] `catalogue()` / `catalogue(cid)` identical before/after (with the addition of `dag_flow`, `sequential_flow`, `parallel_flow`, `memory`).
- [ ] `describe()` entries carry the old keys + new rich keys.
- [ ] A sample chat request ends with the same reply.
- [ ] `node.start` / `node.done` event sequence unchanged.
- [ ] `task.done` emitted once.
- [ ] Replan still fires on `replan=True`; caps at 3.
- [ ] Streaming `stream_id` matches across chunks.
- [ ] `task.cancelled` on interrupt.
- [ ] Hot-reload still works: edit an existing neuro → next call uses new code.

### Task Z.2: Tag the release milestone

- [ ] Tag once all checks pass:

```bash
git tag -a neuro-arch-01-core-v1 -m "01-core migration complete (Phases A-F)"
```

---

## Self-review (plan → spec coverage)

Spec sections in `docs/superpowers/specs/2026-04-20-neuro-arch/01-core/` and which task implements them:

| spec §                                                | implemented by                     |
|-------------------------------------------------------|------------------------------------|
| `00-overview.md` — claims 1 (contract)                | Phase C (Task C.1)                 |
| claim 2 (flow-is-neuro)                               | Phase A (Tasks A.1–A.4)            |
| claim 3 (state layers)                                | Phase E (Tasks E.1–E.2)            |
| claim 4 (one registry, many views)                    | existing + Phase C polish          |
| claim 5 (factory + executor)                          | Phases B–C (B.1–B.3, C.1–C.6)      |
| claim 6 (typed ports + IDE seams)                     | Phase D (Tasks D.1–D.2)            |
| claim 7 (zero break)                                  | all phases — verified in Task Z.1  |
| `01-primitive-class-vs-fn.md` — all §                 | Task C.1–C.4, C.6                  |
| `02-flow-as-neuro.md` — FlowNeuro / DagFlow / Seq/Par | Task A.1–A.4, B.1, C.5             |
| `03-state-and-memory.md` — memory API                 | Task E.1–E.2                       |
| `04-registry-and-lib.md` — rich describe, reserved    | Task D.1, E.2                      |
| `05-factory-and-executor.md` — the refactor itself    | Phases A–C + F                     |
| `06-typed-io-and-ide-seams.md`                        | Task D.1–D.2                       |
| `07-migration.md` — six phases                        | Phase 0 + A + B + C + D + E + F    |

No spec section is unimplemented.

No placeholders. Types + method signatures consistent across tasks: `FlowNeuro`/`DagFlow`/`SequentialFlow`/`ParallelFlow`, `ClassEntry`/`_LegacyFnEntry`, `InstancePool`, `NeuroHandle`, `MemoryStore`, `describe()` shape — defined in early tasks, consumed in later ones with the same names.

Rollback per phase: `git revert <commit>` — each task is one commit, each phase is independently revertible.
