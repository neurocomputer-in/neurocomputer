class Executor:
    """Walk the DAG produced by planner and execute each node sequentially."""
    def __init__(self, flow, factory, state, pub):
        self.flow     = flow
        self.factory  = factory
        self.state    = state
        self.pub      = pub            # async callback

    # ------------------------------------------------------------------ helpers
    async def _run_once(self):
        """
        Execute the **current** flow one time.
        Returns True when a re-plan is requested (error flag or explicit
        \"replan\" key from a neuro).
        """
        conv  = self.state.get("__conv")
        node  = self.flow["start"]
        nodes = self.flow["nodes"]

        # clear previous replanning flags
        self.state.pop("__needs_replan", None)

        while node:
            spec = nodes[node]                        # {neuro, params, next}
            await self.pub("node.start",
                           {"id": node, "neuro": spec["neuro"]})

            print(f"[EXECUTOR] Running neuro: {spec['neuro']} for node: {node}")
            
            # Handler for streaming tokens from neuro
            async def _stream_handler(chunk):
                await self.pub("assistant", chunk)
                
            try:
                out = await self.factory.run(
                    spec["neuro"], self.state, 
                    stream_callback=_stream_handler,
                    **spec.get("params", {})
                )
            except Exception as e:
                err = {
                    "error": type(e).__name__,
                    "message": str(e),
                    "neuro": spec["neuro"],
                }
                # one unified place to surface the error
                await self.pub("assistant", f"⚠️ {spec['neuro']} failed: {e}")
                await self.pub("node.done", {"id": node, "out": err})
                # flag for replanner and stop executing this flow
                self.state["__needs_replan"] = True
                break

            # ── forward captured stdout to listeners ───────────────────
            logs = out.pop("__logs", None)
            if logs:
                await self.pub("node.log", {
                    "id":   node,
                    "neuro": spec["neuro"],
                    "logs": logs
                })

            # merge outputs into shared state
            self.state.update(out)

            # ── ReAct: Record observation in environment state ───────────
            env_state = self.state.get("__env_state")
            if env_state:
                result_str = str(out.get("reply", out.get("result", str(out)[:200])))
                env_state.add_observation(
                    action=f"Execute {spec['neuro']}",
                    neuro=spec["neuro"],
                    result=result_str,
                    success="error" not in out and "__error" not in out
                )

            # any neuro can explicitly ask for another planning round
            if out.get("replan") or out.get("needs_replan"):
                self.state["__needs_replan"] = True
            print(f"[EXECUTOR] Output for node {node}: {out}")

            # ── NEW: persist *and publish* assistant replies ──────────
            if "reply" in out and isinstance(out["reply"], str):
                if conv:                       # save to conversation log
                    conv.add("assistant", out["reply"])
                
                # broadcast so every websocket client receives it (unless already streamed)
                if not out.get("__streamed"):
                    await self.pub("assistant", out["reply"])
                    print(f"[EXECUTOR] Emitted assistant reply: {out['reply'][:60]}…")
                else:
                     print(f"[EXECUTOR] Skipped emitting assistant reply (already streamed)")

            print(f"[EXECUTOR] Publishing node.done event for node: {node}")
            await self.pub("node.done", {"id": node, "out": out})
            print(f"[EXECUTOR] Published node.done event successfully")
            node = spec.get("next")

        # Emit task.done only when no replan is pending
        needs_replan = bool(self.state.get("__needs_replan"))
        if not needs_replan:
            print("[EXECUTOR] All nodes processed, publishing task.done event")
            await self.pub("task.done", {"state": self.state})
        return needs_replan

    # ------------------------------------------------------------------ public
    async def run(self):
        """
        Execute → (optionally) re-plan → execute … until no re-plan is needed
        or the safety cap (3 rounds) is hit.
        """
        max_rounds = 3
        rounds     = 0

        while True:
            need_replan = await self._run_once()
            if not need_replan:
                break

            if rounds >= max_rounds:
                await self.pub("assistant",
                               "⚠️ Replanning aborted after 3 attempts.")
                break

            rounds += 1
            planner = self.state.get("__planner", "planner")
            goal    = self.state.get("goal", "")
            cid     = self.state.get("__cid")

            # build a fresh plan with the updated state
            reply = await self.factory.run(
                planner,
                self.state,
                goal=goal,
                catalogue=self.factory.catalogue(cid)
            )

            plan = reply.get("plan", reply)  # compat with older planners
            if not plan.get("ok"):
                # surfaced failure → bail out gracefully
                await self.pub("assistant",
                               plan.get("question") or
                               "Planner could not formulate a new plan.")
                break

            # ── NORMALISE short-forms so we ALWAYS hold a full DAG ─────────
            def _wrap(neuro, params=None):
                return {
                    "start": "n0",
                    "nodes": {
                        "n0": {
                            "neuro": neuro,
                            "params": params or {},
                            "next": None
                        }
                    }
                }

            flow = plan["flow"]

            if isinstance(flow, str):
                # Plain string → single-node flow
                flow = _wrap("reply" if flow == "reply" else flow)
            elif isinstance(flow, dict):
                # {"type":"reply"}  → chat reply wrapper
                if flow.get("type") == "reply":
                    flow = _wrap("reply", {"text": self.state.get("goal", "")})
                # {"name":"neuro", …} → single-neuro wrapper
                elif "name" in flow:
                    flow = _wrap(flow["name"], flow.get("params", {}))

            self.flow = flow   # ⚡ always a proper DAG now
