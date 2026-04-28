# NeuroLang — Vision

> Status: pre-alpha vision document. Captures the design intent, not yet the implementation.

## 1. Core Idea

NeuroLang is a **modular language for composing intelligent agents**. The core unit is a *neuro* — a typed, composable runtime unit with identity, behavior, and an optional language surface. Neuros compose into flows, agents, and full multi-agent systems.

Anyone can build their own agentic OS, IDE, or product on top.

## 2. Two-Layer Language Design

NeuroLang has **two co-equal authoring surfaces**:

### Layer 1 — Natural Language (NL)
- Hindi, English, or any language the LLM compiler supports
- How most users will author and read code most of the time
- Full sentences, fragments, voice transcription all valid input forms

### Layer 2 — Formal NeuroLang
- Typed, deterministic, executable
- Composition operators, effect annotations, cost bounds, scoped memory
- The runtime executes this layer

### Bidirectional, Cached Compilation
An LLM compiler bridges both layers:
- **Forward (author):** NL → formal NeuroLang
- **Reverse (read/display):** formal NeuroLang → NL summary

Both directions are **cached** so output is stable, inspectable, replayable. The cache is keyed on canonical forms so the same intent produces the same code across runs.

```
┌─────────────────────────┐         ┌──────────────────────────┐
│  Natural Language       │ ◄────► │  Formal NeuroLang        │
│  (Hindi/English/voice)  │   LLM   │  (typed, executable)     │
│                         │  cache  │                          │
│  "summarize emails      │         │  fetch(emails, 7d)       │
│   from last week"       │         │   |> filter(unread)      │
│                         │         │   |> summarize(by:topic) │
└─────────────────────────┘         └──────────────────────────┘
```

## 3. The 3D IDE — Code as Spatial Blocks

The IDE renders programs as 3D blocks (one per neuro / function / class / module).
Each block surfaces:
- **NL summary** — generated from the formal layer (decompile direction), cached
- **Signature** — types, effects, cost bound
- **Drill-in** — formal NeuroLang code on demand

Users author by **speaking, typing NL, or editing formal code directly**. The IDE keeps both layers in sync via the cached compiler.

## 4. Primitives the Language Surfaces

What general-purpose languages don't expose, NeuroLang does:

| Primitive | Why it's load-bearing |
|-----------|------------------------|
| `Neuro`   | Typed unit (identity + behavior + optional prompt) |
| `Flow`    | Composition operators: sequential, parallel, DAG, loop |
| `Plan`    | First-class value — inspect, modify, replay, persist |
| `Memory`  | Scoped read/write declarations per neuro (Rust-ownership-style for context) |
| `Effect`  | `pure` / `llm` / `tool` / `human` / `time` — tracked, enforced |
| `Budget`  | Latency + cost bounds, runtime enforced, compiler warns on overruns |
| `Mailbox` | Multi-agent message-passing (no shared mutable state) |
| `Recovery` | `fallback`, `retry`, `escalate` as language constructs, not bolted-on libs |

## 5. Why Bidirectional Caching Is The Moat

Most "AI coding" tools are one-way (NL → code) and ephemeral.
NeuroLang's bidirectional cached compilation gives:

- **Stability** — same NL prompt produces same formal code (deterministic via cache)
- **Inspectability** — formal layer is readable, reviewable, diffable
- **Editability** — users can edit at either layer; the other auto-updates via compilation
- **Round-trip** — the IDE always shows up-to-date NL summaries, no stale comments

This is what separates NeuroLang from "Python + Copilot + LangChain". The formal target language + cached round-trip is the architectural bet.

## 6. Source-of-Truth Question (Open)

Two candidates:

- **(A) Formal NeuroLang is canonical.** NL is a generated, decompiled view. Edits at NL trigger recompilation; edits at formal layer regenerate NL summary.
- **(B) NL is canonical.** Formal layer is generated and cached. Edits at formal layer "re-anchor" the NL.

(A) is more like Python with auto-comments. (B) is more like Cursor/Copilot but with a formal cache.

**Likely answer:** (A) — formal as truth, NL as derived/cached view. Simpler semantics, easier to verify, supports "I want to read what runs."

## 7. Strategic Question — Is This A Breakthrough?

> Decision pending. Discussed in conversation; assessment to be appended below.

## 8. Design Questions Still Open

1. **Syntax form** — text-only? graph-first? both?
2. **Voice flow** — speak into IDE, materialize as 3D block?
3. **Multi-language NL parity** — does Hindi-authored agent execute identically to English-authored?
4. **Cache invalidation** — when LLM model changes, does cache stay valid? (probably no — version cache by model+prompt+formal-spec)
5. **Determinism vs creativity** — should the LLM compiler be temperature 0 always? Or allow controlled exploration?
6. **What guarantees does the formal layer provide that Python + LangChain doesn't?** (this is the breakthrough question)
