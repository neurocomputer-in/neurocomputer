# 03-react-orchestrator · 02 · Environment-state tracking

**Status**: open research.

---

## 1 · Starting point

`core/environment_state.py` already exists and is wired into `core/brain.py`: every executor run injects `state["__env_state"]`, and each completed node calls `env_state.add_observation(action, neuro, result, success)`. The orchestrator builds on this rather than reinventing it.

## 2 · What "environment state" means here

A compact structured record that answers, for the next reasoning step:

- What have I done so far this session? (observation log)
- What's the current external context? (cwd, files, external service status)
- What did the user most recently say? (conversation tail)
- What surprises have I seen? (divergences from expectation)

The orchestrator reads this record each loop turn and feeds a relevant slice into the LLM prompt. It is *not* an unbounded scratchpad — it's a structured store the orchestrator can query.

## 3 · Observation record — canonical shape

Each completed step produces one:

```json
{
  "id":        "obs-2026-04-20T15-33-09-abc12345",
  "step":      17,
  "ts":        "2026-04-20T15:33:09.413Z",
  "thought":   "I need to read the file before editing.",
  "action": {
    "kind":    "invoke_neuro",
    "neuro":   "code_file_read",
    "params":  {"path": "core/brain.py"}
  },
  "result": {
    "success":    true,
    "summary":    "Read 731 lines of core/brain.py.",
    "output_ref": "memory:react.obs.abc12345.output",
    "duration_ms": 124
  },
  "env_delta": {
    "files_read":     ["core/brain.py"],
    "files_written":  [],
    "processes_started": []
  }
}
```

Size target: **≤ 500 tokens per record when serialized for prompting**. Large outputs live in `output_ref` (memory API), not inline. The prompt carries `summary` only.

## 4 · Session-level env snapshot

Separate from per-step observations, the orchestrator maintains a session snapshot:

```json
{
  "cwd":            "/home/ubuntu/neurocomputer-dev",
  "user_messages":  ["...last 3 user messages..."],
  "open_files":     [{"path": "core/brain.py", "lines": 731, "last_mtime": "..."}],
  "tracked_goals":  ["refactor factory", "add class-neuro path"],
  "recent_errors":  [{"step": 12, "error_type": "import", "neuro": "dev_save"}],
  "external": {
    "git": {"branch": "dev", "dirty": true, "ahead": 4},
    "services": {"backend": "up", "frontend": "up", "ollama": "up"}
  }
}
```

Updated after each step's `env_delta`. The orchestrator consults this before deciding the next action.

## 5 · What to feed the LLM each turn

Budget-aware selection:

- **Always**: current goal + session snapshot summary (≤ 400 tokens).
- **Recent window**: last N observations in full (default N=5, configurable).
- **Older window**: rolled up into a single summary observation via a `summarizer` neuro when window exceeds ~2k tokens.
- **Episodic recall** (optional): `memory.search` for lessons from similar past goals; prepend any high-confidence matches.

Concretely the prompt has three labelled sections: `goal`, `session`, `recent_steps`, optionally `lessons`.

## 6 · Summarization pipeline

Triggered every K steps (default 10) or when the prompt exceeds the token ceiling:

1. Take all observations older than the recent window.
2. Feed them to a `summarizer` neuro with instruction: "compress into 3-5 bullet points, preserve failed attempts and surprising results".
3. Replace the compressed block with a single `obs` whose `kind = "summary"`.
4. Store the original records in memory under `react.obs.archive.<session>.<id>` for later recall.

The summarizer is itself a neuro — swappable, hot-reloadable, testable in isolation.

## 7 · Divergence detection (surprise signal)

Simple rule (v1): before each action, the orchestrator records an *expectation*:

```python
expectation = await self.planner.run(state, ..., task="predict_outcome", action=next_action)
```

After the action, diff expectation vs actual. If divergence above threshold:

- Emit a surprise observation.
- Trigger replan consideration (see `03-dynamic-replan.md`).

v1 divergence metric: `success_mismatch | summary_cosine < 0.5 | env_delta mismatch`. Simple, interpretable, tunable.

More sophisticated divergence (prediction models, learned classifiers) is v2.

## 8 · Interaction with `memory` API

- **Live per-session** observations and snapshot: kept in `state["__env_state"]`, not persisted. Dropped on session end unless operator config says otherwise.
- **Archived observations**: written to memory API (`scope=agent, key=react.obs.archive.<session>.<id>`) once summarized.
- **Lessons**: written on replan or on failure (key: `react.lessons.<goal_hash>.<ts>`). Recalled via `memory.search` at plan time.

## 9 · Concurrency and interrupts

- User interrupts (`/stop`, `/new input`): orchestrator catches, emits `react.paused`, stores current session snapshot, waits.
- On resume: reload snapshot, re-enter loop from last completed step.
- Concurrent sessions: each session has its own `__env_state` and snapshot. No cross-session bleed (agent memory is shared across sessions, but env_state is not).

## 10 · Open questions (to resolve)

- What exactly goes into `env_delta`? Baseline proposal above; needs real-task audit to confirm coverage.
- How aggressive is the summarization trigger? Every 10 steps feels right for 50-step ceiling; needs tuning.
- Do we track token budgets explicitly or rely on LLM provider rate-limits? Probably both; separate budget meter for transparency.
- What's the minimum viable `summarizer` prompt? Needs iteration post-reading prior art.
- Should divergence detection be optional? Likely yes — high overhead for simple tasks. Opt-in flag.

## 11 · Deliverable of this subdoc (when finalized)

- Concrete observation schema (§3).
- Concrete snapshot schema (§4).
- Prompt-assembly rules (§5).
- Summarization trigger + process (§6).
- Divergence detection rule (§7).
- Integration points with `memory` API (§8).

With those fixed, the main `ReactFlow` design doc can reference this as its memory/observation layer.
