# 03-react-orchestrator · 00 · Research brief

**Status**: open research. Feeds into a future design doc; not itself a committed design.

---

## 1 · The gap we're closing

The current planner emits a flow upfront, the executor (→ `DagFlow` after `01-core/07`) walks it with a bounded 3-round replan loop. That's adequate for:

- Short tasks (≤10 steps).
- Well-scoped goals where the plan barely needs to react.
- Static environments (no concurrent user input, no external state churn).

It is inadequate for:

- **Long-running work** (tens to hundreds of steps) — context blows up, state drifts.
- **Dynamic environments** — filesystem changing, external APIs timing out, user sending new instructions mid-run.
- **Goal decomposition** — tasks the planner can't fully specify upfront and must break down as it goes.
- **Observation-driven reasoning** — ReAct's core value proposition: *observe → reason → act → observe …*, where every observation can reshape the plan.

## 2 · What we're designing (eventually)

A `ReactFlow` neuro: a `FlowNeuro` subclass that implements a ReAct-style loop on top of the same primitives (`BaseNeuro`, `memory` API, `NeuroHandle`). It composes with the rest of the system — it *is* a neuro, so it plugs wherever any neuro plugs.

The subdocs in this folder answer the questions that shape the design:

- `01-prior-art.md` — which agentic patterns to borrow, which to reject.
- `02-env-state-tracking.md` — what to observe, how to store it, how to surface it to the LLM.
- `03-dynamic-replan.md` — triggers, budget, rollback, termination.

After those three, a design doc (`04-reactflow-design.md` or similar) pulls the answers together and commits a specification. That step follows research; we don't write it speculatively.

## 3 · Success criteria for the eventual `ReactFlow` design

- Runs tasks of arbitrary length (bounded only by budget, not context).
- Handles filesystem / external-state changes between steps without getting confused.
- Survives user interrupts mid-run gracefully (pause, accept new input, resume or re-plan).
- Composes cleanly with existing neuros — no special privileges in the runtime.
- Reuses the `memory` API from `01-core/03` for long-term episodic storage.
- Reuses `core/environment_state.py` for short-term per-session observation log.
- Emits the same events (`node.start`, `node.done`, `stream_chunk`, `thinking`, etc.) the rest of the system already consumes.

## 4 · Constraints on the research

- We will not rebuild prior-art wheels. If LangGraph / ReAct / Reflexion already solves a piece well, we adapt their idea, not their code.
- Context budget matters. Any strategy requiring unbounded-growth scratchpads is disqualified for long-horizon use.
- No runtime changes required to ship the orchestrator. It must be implementable as a single `FlowNeuro` subclass + supporting small neuros (observers, summarizers, critics).
- Safe default for budget ceilings: **max 50 steps**, **max 15 min wall time**, **max 3 replans**. Configurable per-invocation.

## 5 · Key questions (explicit, to answer in subdocs)

Context handling:

- Do we use a rolling scratchpad, recursive summarization, vector recall, or a hybrid?
- How short is "short" for the per-step prompt? (~2k tokens target; hard cap 8k.)

Action selection:

- Does the orchestrator produce a plan-ahead DAG + adjust it, or pure step-by-step?
- How does it decide when to run a sub-flow vs a single neuro?

Observation:

- What's the smallest useful observation record? (candidate: `{action, neuro, params, result_summary, success, ts, duration}`)
- Which env dimensions need snapshotting? (cwd, tracked files, external service pings, last-N user messages, open resources.)

Replan:

- When does the orchestrator decide the current plan is wrong?
- When does it give up vs retry?
- Does it escalate to a larger model when stuck?

Termination:

- How does the orchestrator know the goal is met?
- How does it signal "done" vs "needs human input"?

## 6 · Non-goals (explicit)

- **Generic multi-agent simulator.** A separate orchestrator track could do that. Not here.
- **RLHF / fine-tuning of the orchestrator itself.** Prompt-engineering only, v1.
- **Full planner replacement.** The orchestrator is one option; simple `planner` + `DagFlow` stays available for short tasks.
- **Agentic evals.** Interesting but orthogonal; covered in a future track.

## 7 · Expected output of this research track

At the end of subdocs 01–03, we should be able to write a design doc that:

1. Names a specific orchestration pattern (or a synthesis of a few).
2. Specifies the observation schema.
3. Specifies the replan trigger rules.
4. Specifies the `ReactFlow` class shape, `uses` list, and `run` loop pseudocode.
5. Leaves minimal open questions going into implementation.

Until we've done the reading, the design doc isn't writable. Hence: research first.
