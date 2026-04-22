"""DagFlow — interprets a JSON DAG. Houses the Executor body.

Runtime events published via state["__pub"]:
  node.start        {id, neuro}
  node.done         {id, neuro, out}
  node.log          {id, neuro, logs}
  thinking          {id, neuro, content}
  stream_chunk      {stream_id, chunk, neuro}   (from child neuros via stream_callback)
  stream_end        {stream_id}
  assistant         reply text
  task.cancelled    {state}
  task.done         {state}

Param templating: node `params` may contain `{{state.KEY}}` tokens which
are substituted from the live state dict at dispatch time. Makes it
possible to thread values produced by upstream nodes (e.g. memory.read
returning `value`) into downstream node params (e.g. memory.write
`value="{{state.value}}"`). Supported in strings, lists, and nested dicts.
"""
import asyncio
import re
from uuid import uuid4
from core.flows.flow_neuro import FlowNeuro


_TMPL = re.compile(r"\{\{\s*state\.([^}\s]+?)\s*\}\}")


def _resolve_params(params, state):
    """Recursively substitute {{state.KEY}} tokens in params from state."""
    if isinstance(params, str):
        def sub(m):
            key = m.group(1)
            val = state.get(key, m.group(0))
            return str(val) if not isinstance(val, str) else val
        return _TMPL.sub(sub, params)
    if isinstance(params, dict):
        return {k: _resolve_params(v, state) for k, v in params.items()}
    if isinstance(params, list):
        return [_resolve_params(v, state) for v in params]
    return params


class DagFlow(FlowNeuro):
    MAX_REPLAN_ROUNDS = 3
    # Pure-conf instances may carry the DAG as a class attribute
    # (populated by NeuroFactory._synthesize_flow_class).
    dag: dict = None

    async def run(self, state, *, dag=None, **kw):
        if dag is None:
            dag = self.dag
        if dag is None:
            raise ValueError(
                f"DagFlow {self.name!r}: no `dag` provided at call time "
                "and no `dag` declared in conf.json"
            )
        try:
            rounds = 0
            current = dag
            while True:  # noqa — dag is either from kwarg or class attr
                need_replan = await self._run_once(state, current)
                if not need_replan:
                    break
                if rounds >= self.MAX_REPLAN_ROUNDS:
                    await _pub(state, "assistant",
                               "⚠️ Replanning aborted after 3 attempts.")
                    break
                rounds += 1
                next_flow = await self._replan(state)
                if next_flow is None:
                    break
                current = next_flow
            return {}
        except asyncio.CancelledError:
            await _pub(state, "task.cancelled", {"state": state})
            raise
        except Exception as exc:
            await _pub(state, "assistant", f"⚠️ Task failed: {exc}")
            return {}
        finally:
            await _pub(state, "task.done", {"state": state})

    async def _run_once(self, state, dag):
        factory = state["__factory"]
        nodes = dag["nodes"]
        node = dag["start"]
        conv = state.get("__conv")
        state.pop("__needs_replan", None)

        while node:
            spec = nodes[node]
            name = spec["neuro"]
            raw_params = spec.get("params", {}) or {}
            params = _resolve_params(raw_params, state)
            on_error = spec.get("on_error", "replan")

            await _pub(state, "node.start", {"id": node, "neuro": name})

            stream_id = f"stream-{node}-{uuid4().hex[:8]}"

            async def _stream_cb(chunk, _sid=stream_id, _neuro=name):
                await _pub(state, "stream_chunk",
                           {"stream_id": _sid, "chunk": chunk, "neuro": _neuro})

            try:
                out = await factory.run(name, state,
                                        stream_callback=_stream_cb, **params)
            except Exception as e:
                err = {"error": type(e).__name__,
                       "message": str(e),
                       "neuro": name}
                await _pub(state, "assistant", f"⚠️ {name} failed: {e}")
                await _pub(state, "node.done", {"id": node, "out": err})
                if on_error == "skip":
                    node = spec.get("next")
                    continue
                if on_error == "abort":
                    break
                state["__needs_replan"] = True
                break

            if not isinstance(out, dict):
                out = {}

            thinking = out.pop("__thinking", None)
            if thinking:
                await _pub(state, "thinking",
                           {"id": node, "neuro": name, "content": thinking})

            logs = out.pop("__logs", None)
            if logs:
                await _pub(state, "node.log",
                           {"id": node, "neuro": name, "logs": logs})

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

            await _pub(state, "node.done",
                       {"id": node, "neuro": name, "out": out})
            node = spec.get("next")

        return bool(state.get("__needs_replan"))

    async def _replan(self, state):
        factory = state["__factory"]
        planner = state.get("__planner", "planner")
        goal = state.get("goal", "")
        cid = state.get("__cid")

        catalogue = []
        if hasattr(factory, "catalogue"):
            try:
                catalogue = factory.catalogue(cid)
            except TypeError:
                catalogue = factory.catalogue()

        reply = await factory.run(planner, state,
                                  goal=goal, catalogue=catalogue)
        plan = reply.get("plan", reply)
        if not plan.get("ok"):
            await _pub(state, "assistant",
                       plan.get("question") or
                       "Planner could not formulate a new plan.")
            return None

        flow = plan["flow"]

        def _wrap(neuro, params=None):
            return {"start": "n0",
                    "nodes": {"n0": {"neuro": neuro,
                                     "params": params or {},
                                     "next": None}}}

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
