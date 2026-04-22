# 03-react-orchestrator · 01 · Prior art

**Status**: open research. Fill with concrete evaluations as we study each system.

---

## 1 · Lay of the land

The space we're in is "agentic orchestration on top of LLMs." The last 24 months produced a dozen named patterns and frameworks. We borrow ideas, not code.

## 2 · Candidates and one-line summaries

| system / paper                  | year | core idea                                                              | relevance to neuro |
|---------------------------------|------|------------------------------------------------------------------------|--------------------|
| **ReAct** (Yao et al.)           | 2022 | alternate Thought → Action → Observation; simple, strong baseline      | high — the skeleton we want |
| **Reflexion** (Shinn et al.)     | 2023 | verbal self-reflection on failure, stored as episodic memory           | high — maps directly to `memory` API |
| **Tree of Thoughts**             | 2023 | branch reasoning paths, evaluate, prune                                | medium — useful for combinatorial sub-problems only |
| **AutoGPT / BabyAGI**            | 2023 | goal decomposition + task queue + reflection                           | low — famously unreliable; study failure modes |
| **MetaGPT**                      | 2023 | role-based multi-agent (PM, architect, dev); SOPs as prompt templates  | medium — the "role = neuro" analogy is tempting |
| **AutoGen**                      | 2023 | conversational multi-agent; message passing                            | medium — inter-agent comms patterns |
| **LangGraph**                    | 2024 | state-machine graph for agents; checkpoints + resumption               | high — structurally similar to `FlowNeuro` |
| **Voyager (Minecraft)**          | 2023 | self-generated curriculum; skill library grows over episodes           | medium — skill persistence, less for orchestration |
| **Reflexion-Voyager** hybrids    | 2023 | persistent skill + error memory                                        | medium                |
| **SWE-agent / Cursor agent**     | 2024 | code-editing in dynamic filesystem; env-as-tool interface              | high — direct analog of our dev-agent use case |
| **ToolFormer / HuggingGPT**      | 2023 | learned tool selection                                                 | low — we name tools explicitly |
| **OpenAgents**                   | 2023 | web/data/plugins triad                                                 | low — domain-specific |
| **OSWorld / AgentBench**         | 2024 | benchmarks, not frameworks                                             | low — useful for evals later, not design |
| **Plan-and-Solve** (Wang et al.) | 2023 | explicit planning prompt pattern                                       | medium |
| **ReWOO**                        | 2023 | plan without tool calls first, then execute; context-frugal            | high — aligns with our "planner then executor" shape |

## 3 · Axes of comparison (to populate)

Each cell is a short fact per system. Left blank where not yet studied; fill as research proceeds.

| system              | context strategy            | replan trigger                    | termination            | memory shape           | failure recovery           |
|---------------------|-----------------------------|-----------------------------------|------------------------|------------------------|----------------------------|
| ReAct               | full trace in prompt        | none (single trajectory)          | LLM self-report         | none                   | none (one shot)            |
| Reflexion           | trace + lesson text         | after full-episode failure        | episode done            | verbal lessons         | append lesson, retry       |
| LangGraph           | checkpointed node state     | explicit node edges to retry      | terminal node           | graph state + long-term| resume from checkpoint     |
| SWE-agent           | file-window + cmd history   | shell error / diff mismatch       | commit made             | edit log + env view    | revert + rethink           |
| AutoGPT             | append-only thought chain   | on every loop                     | `task_complete` self-call | vector DB (unreliable) | loop, often thrashes       |
| MetaGPT             | role-partitioned prompts    | role handoff                       | full SOP done           | role-specific artifacts| hand back for rework       |
| ReWOO               | plan upfront, no thought during exec | re-plan on tool error  | plan complete           | execution log          | replan                     |
| Tree of Thoughts    | branched state              | on eval score drop                | leaf accepted           | tree snapshot          | prune, explore sibling     |
| Voyager             | skill library + env state   | skill acquisition failure         | curriculum step done    | skill code repo        | regenerate skill           |

## 4 · Patterns worth pulling into `ReactFlow`

Provisional — confirm or reject after reading each source:

1. **Observation record = (thought, action, neuro, params, result_summary, success, ts).** Narrow, JSON-serializable. From ReAct; extended.
2. **Rolling scratchpad of the last N steps + periodic summarization.** Keeps prompt bounded. Inspired by Reflexion + LangGraph checkpoints.
3. **Lesson log** (Reflexion) — verbal takeaways from failed sub-trajectories, stored in agent memory, prepended to future prompts on similar goals.
4. **Checkpoint resume** (LangGraph) — a long run can pause and resume from the last completed node without rerunning.
5. **Env snapshot diff** (SWE-agent) — before/after views of the environment; divergence triggers replan.
6. **Plan-then-execute with in-exec replan hooks** (ReWOO + DagFlow) — our current shape already matches; reinforce rather than replace.

## 5 · Patterns we reject or defer

- **Monolithic thought chain blown into the prompt** — ReAct baseline; hits context wall fast. Use only with summarization.
- **Generic multi-agent role dispatch** (MetaGPT / AutoGen style) — interesting but not our immediate problem; one agent running `ReactFlow` is v1.
- **Tree of Thoughts branching at every step** — expensive, marginal return for non-combinatorial tasks. Keep for targeted sub-problems.
- **Vector-DB long-term memory as the main recall mechanism** — AutoGPT-style recall is famously noisy. Prefer structured memory keys + small vector search on specific record types.

## 6 · Implementation shape (preview, not commitment)

```python
class ReactFlow(FlowNeuro):
    uses  = ["memory", "planner", "summarizer", "critic"]
    scope = "session"

    async def run(self, state, *, goal, max_steps=50, wall_budget_s=900):
        env_state = state.setdefault("__env_state", EnvironmentState())
        env_state.current_goal = goal
        history = []       # rolling scratchpad
        start = time.time()

        for step in range(max_steps):
            if time.time() - start > wall_budget_s: break

            thought, action = await self._decide(state, goal, history, env_state)
            if action.kind == "done":
                return {"reply": action.summary, "steps": step}

            result = await self._act(state, action)
            history.append(Observation(step, thought, action, result))

            if len(history) % 10 == 0:
                history = await self._summarize(state, history)

            if await self._should_replan(state, history, env_state):
                goal = await self._replan(state, goal, history)

        return {"reply": "…max steps reached; best-effort result", "partial": True}
```

This is *illustrative*, not spec. The design doc (after research) will make the shapes concrete.

## 7 · What's still to read

Priority order:

1. ReAct paper itself (original prompt design + ablations).
2. Reflexion paper (failure-taxonomy + memory mechanism).
3. LangGraph docs on checkpointing + interruption.
4. SWE-agent paper (env-as-tool interface + edit log).
5. ReWOO paper (context budgeting).

Each reading produces bullet notes under `§3` and optionally a new bullet in `§4`. When all five are ingested, we're ready to write the `ReactFlow` design.
