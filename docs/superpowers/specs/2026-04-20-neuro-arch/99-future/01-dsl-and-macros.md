# 99-future · 01 · DSL and macros (deferred)

**Status**: deferred. Do not implement until 01-core is stable and patterns crystallize.

## What goes here later

The (d) option from brainstorming: a **tier-5 extensible neuro-lang**.

- Core grammar: composition + state + control (minimal).
- Macro system: neuros written in the lang can *define* new syntactic forms. Homoiconic via the fact that flows are already data.
- Reader macros (optional): parser extension from user code.
- Compiler target: existing `BaseNeuro` / `FlowNeuro` runtime (no new runtime needed).

## Why deferred

- Power without usage patterns = wrong syntax. Let (c) bake first, observe what repeats, then compress.
- Greenspun: we already have a tier-5 substrate (JSON-as-AST, planner-as-macro). Lifting it into a named lang is a presentation change, not a semantic one.

## When to revisit

- At least 100 real neuros authored in (c) across multiple agents.
- At least 5 recurring compositional patterns (fan-out, retry-with-backoff, memoize, cond-branch, map-reduce) that feel awkward in JSON / class form.
- IDE shipped and used, so the audience for the lang is known (humans vs LLMs vs both).
