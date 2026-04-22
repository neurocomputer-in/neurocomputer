# 01-core · 00 · Overview

**Thesis**: neuro is the only primitive. leaf and composite are the same primitive. the category of neuros is closed under composition.

## Core claims (each expanded in later subdocs)

1. **Neuro = `async run(state, **kw) → dict`** — single contract. any callable conforming is a neuro. (→ `01-primitive-class-vs-fn.md`)
2. **Flow is a neuro** — a `FlowNeuro` calls child neuros. composition is itself a neuro. fractal. (→ `02-flow-as-neuro.md`)
3. **State lives in layers** — per-session (transient), per-agent (persistent), shared (cross-agent). neuros access all three uniformly. (→ `03-state-and-memory.md`)
4. **One registry, many views** — a single global lib; agents see a filtered slice via their profile. (→ `04-registry-and-lib.md`)
5. **Factory reloads + Executor merges** into a single runtime: `FlowNeuro.run()` is the execution loop. (→ `05-factory-and-executor.md`)
6. **Typed ports + visual metadata** leave room for the 3D IDE without touching the runtime. (→ `06-typed-io-and-ide-seams.md`)
7. **Zero break** — current fn-neuros and JSON flows keep working, wrapped transparently. (→ `07-migration.md`)

## Why this shape (summary)

- **Universal**: sequencing + branching + loop + composition + state + I/O — covered by fn-neuros and FlowNeuro.
- **OOP-complete**: class-neuros give inheritance, encapsulation, sub-neuro ownership, lifecycle.
- **Lisp-adjacent**: the flow/DAG is *data*, planner is a *macro*, factory is a *compiler*. already tier-5 in practice.
- **Minimum disruption**: factory adds a second branch (class vs fn); Executor becomes the default flow; everything else is additive.

## Out of scope here (in 99-future)

- A first-class neuro-lang grammar (parser + macros).
- Neuro-Dream (background self-improvement).
- Entropy-guided optimization.

## Glossary (used throughout)

- **neuro** — unit of execution. may be leaf (no children) or composite (flow).
- **flow** / **composite** — neuro whose `run` calls other neuros.
- **agent** — long-lived entity; has lib + memory; runs sessions.
- **session** — one conversation/task invocation under an agent.
- **lib** — registry of neuros visible to an agent (filtered by profile).
- **state** — the dict passed through `run`. per-session scratch.
- **memory** — persistent store (per-agent or shared), accessed via memory API neuros.
