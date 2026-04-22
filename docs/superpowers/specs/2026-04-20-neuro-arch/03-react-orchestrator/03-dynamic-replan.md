# 03-react-orchestrator · 03 · Dynamic replan

**Status**: open research.

---

## 1 · Why replan is hard

A fixed 3-round replan (today's `DagFlow`) is enough for short tasks. For long-running ReAct loops:

- Replanning too eagerly → thrashing, little progress.
- Replanning too late → stuck executing a broken plan.
- Replanning without state → loses prior learning.
- Replanning without budget → loops forever when the goal is actually infeasible.

This subdoc enumerates the decisions the orchestrator must make each step.

## 2 · Trigger matrix (v1)

What makes `ReactFlow` stop executing and re-plan? Cost is roughly linear with how often we trigger, so tune conservatively.

| trigger                                                        | default  | tunable | notes                                                   |
|----------------------------------------------------------------|----------|---------|---------------------------------------------------------|
| Neuro returned `replan=True` / `needs_replan=True`              | on       | off     | explicit signal from the acting neuro; always honored   |
| Same step failed N times in a row                               | N=2      | 1–5     | per-action counter; reset on success                    |
| Observation divergence above threshold (see `02-env-state-tracking.md` §7) | on | off  | surprise signal                                         |
| User interrupt with new directive                               | on       | —       | unconditional                                           |
| Budget line crossed (token / step / wall-time fraction)         | 70%      | 50–90%  | "halfway through, check we're on track"                 |
| Critic neuro rejects last plan as unproductive                  | optional | —       | requires a `critic` neuro in `uses`                     |
| Goal change detected in user_messages                           | on       | —       | cheap keyword check → deeper classification if matched  |

Multiple triggers in one step are OR'd; one is enough.

## 3 · Replan loop shape

When a trigger fires:

```
1. Pause current loop.
2. Assemble replan prompt:
   - original goal
   - session snapshot
   - recent observations (possibly summarized)
   - trigger reason
   - prior plan (the DAG or task list)
3. Call planner neuro with mode="replan".
4. Validate the new plan (schema, referenced neuros exist).
5. If invalid → retry-with-repair (≤3, same as dev-agent pipeline).
6. If still invalid → escalate (see §5).
7. Adopt new plan; continue the main loop at step 0 of the new plan.
```

The replan call counts against the same budget as normal steps — it's not free.

## 4 · Budget enforcement

Three meters tracked per session:

| meter        | default | purpose                                             |
|--------------|---------|-----------------------------------------------------|
| step count   | 50      | hard ceiling on neuro invocations                    |
| wall time    | 900s    | real-time ceiling (handles long blocking ops)        |
| token budget | 200k    | sum of prompt + completion tokens across all LLM calls |

Additional counter:

| meter            | default | purpose                                    |
|------------------|---------|--------------------------------------------|
| replan attempts  | 5       | cap on replan calls; exceeding → escalate  |

Exceeding any meter → orchestrator terminates gracefully, emits `react.budget_exceeded` with current state, and returns a partial-result reply.

## 5 · Escalation

When automated recovery fails:

1. **Soft escalation**: emit `react.stuck`, ask the user (via `assistant` event): "I'm stuck on X because Y. Should I (a) retry with smaller scope, (b) try approach Z, (c) stop?" Pause until user replies.
2. **Hard stop**: if user doesn't reply within `wait_timeout` (default 60s), orchestrator saves state, emits `react.paused`, and terminates the session loop. User can resume later.
3. **Never silent fail**: every escalation produces a structured `react.event` so the IDE shows it.

## 6 · Rollback

Reversibility of past actions determines whether rollback is even possible.

| action class                 | reversible | mechanism                                    |
|------------------------------|------------|----------------------------------------------|
| `memory.write`               | yes        | keep prior value; restore via `memory.write` |
| File write (dev agent)       | yes        | `.neuros_history/` snapshot                   |
| File write (non-dev, project)| partial    | git stash / git restore if clean hunk         |
| `subprocess` side effect     | no         | log and move on                               |
| External API call (POST/PUT) | no         | log; orchestrator should have thought harder  |
| `memory.read` / listing       | no-op      | no rollback needed                            |

Orchestrator tracks a per-step reversibility flag in the observation record. A rollback request (from replan or user) iterates the reversible tail of observations and undoes them in reverse order.

Non-reversible actions are executed only when the orchestrator has high confidence — a `critic` check can gate them. v1 ships without gating; v2 adds.

## 7 · Hierarchical replan

A long plan decomposes into sub-flows. When a sub-flow fails, the default is:

1. Try to replan within the sub-flow (bounded to 2 rounds).
2. If still failing, bubble up to parent plan and replan there.
3. If the parent has already consumed its replan budget, escalate (§5).

This keeps replanning local when possible, avoiding whole-plan churn over a small setback.

## 8 · Termination conditions

The orchestrator stops when *any* of:

- LLM emits an action of kind `done` with a summary.
- A designated `check_goal` neuro returns `{done: true}`.
- A budget meter is exceeded (graceful termination, §4).
- User sends a `/stop` command.
- Unrecoverable error from a protected neuro (escalate then terminate).

On termination, a final event `react.done` fires with:

```json
{
  "goal": "...",
  "outcome": "success" | "partial" | "stuck" | "cancelled",
  "reply": "...",
  "steps": 17,
  "budget_used": {"tokens": 52300, "wall_ms": 412000, "replans": 2}
}
```

## 9 · Open questions

- Do we want per-sub-flow budget overrides, or inherit from parent?
- How do we detect "unproductive" replans (two plans in a row with similar structure making no progress)? Fingerprint-based comparison? LLM-eval'd similarity?
- Is the budget 50 steps / 15 min / 200k tokens right? Needs empirical calibration on real tasks.
- Should we expose a "dry-run plan" mode where the orchestrator produces a plan and asks the user to approve before executing?
- How do we train the orchestrator over time? Memorized lessons are one path; fine-tuning is another (out of scope for v1).

## 10 · Deliverable of this subdoc (when finalized)

- Full trigger table with tuned defaults (§2).
- Budget meter values (§4).
- Reversibility table and rollback algorithm (§6).
- Hierarchical replan rule (§7).
- Termination schema (§8).

With `02-env-state-tracking.md` fixed, this subdoc fixes the control flow. Then we can write the `ReactFlow` design doc.
