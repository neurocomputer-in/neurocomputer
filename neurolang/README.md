# NeuroLang

> The Python framework for AI-native agentic coding.
>
> Write agents in natural language. The library compiles your prompts into typed, composable, inspectable Python programs.

---

## The Trinity

NeuroLang is one third of a three-name system. See [`docs/TRINITY.md`](../docs/TRINITY.md) for the canonical definition.

| | Role | What it is | Where |
|---|---|---|---|
| **NeuroLang** | the *language* | Typed Python primitives, plans-as-values, composition syntax. The thing you write in. | `pip install neurolang` (this repo) |
| **NeuroNet** | the *program* | A composed network of neuros — runnable, shareable, installable. The thing you ship. | Output of NeuroLang. Lives in `~/.neurolang/neuros/` (or a package registry, planned). |
| **Neurocomputer** | the *environment* | IDE + execution environment + OS shell that hosts NeuroNets as apps. The thing you run on. | [`neurocomputer-in/neurocomputer`](https://github.com/neurocomputer-in/neurocomputer) |

NeuroLang is the **language**. NeuroNet is the **program**. Neurocomputer is the **environment** — write in NeuroLang, ship a NeuroNet, run on Neurocomputer.

---

## Status

Pre-alpha. APIs are not stable yet. Watch the repo for the first usable release.

## Install

```bash
pip install neurolang
```

(Not yet published — install from source for now.)

```bash
git clone https://github.com/neurocomputer-in/neurolang
cd neurolang
pip install -e ".[dev]"
```

---

## The shape

NeuroLang surfaces what general-purpose languages don't: **deliberation, cost, memory scope, effects, and recovery as first-class primitives.**

| Primitive | Purpose |
|-----------|---------|
| `Neuro` | Typed, composable unit (identity + behavior + optional prompt surface) |
| `Flow` | Composition (sequential `\|`, parallel `&` / `+`, DAG, loop) |
| `Plan` | First-class value — inspect, modify, replay, diff, hash |
| `Memory` | Scoped read/write declarations per neuro |
| `Context` | Typed memory + prompt assembly slice |
| `Effect` | `pure` / `llm` / `tool` / `human` / `time` / `voice` — tracked by the runtime |
| `Budget` | Latency + cost bounds, enforced |
| `Recovery` | `fallback` / `retry` / `escalate` as language primitives |
| `Mailbox` | Multi-agent message-passing (no shared mutable state) |
| `Agent` | Long-lived neuro with mailbox + memory + role |

---

## Two-line example

```python
from neurolang import neuro, Flow, Memory
from neurolang.stdlib import web, reason, memory_neuros

@neuro(effect="tool")
def extract_book_metadata(url: str) -> dict:
    """Scrape title, author, summary from URL."""
    ...

research_flow: Flow = (
    web.search | extract_book_metadata | reason.summarize | memory_neuros.store
)

plan = research_flow.plan(query="best books on category theory")
result = plan.run(memory=Memory.discrete())
```

---

## Philosophy

- **If a capability matters for intelligent behavior, it should be representable as a neuro.**
- **If neuros are composable and reusable, the system becomes programmable intelligence.**
- **If programmable intelligence is scalable, we have a credible path toward agentic OS engineering.**

The categorical, dimensional foundations are the language's bones — see [`docs/RESEARCH.md`](./docs/RESEARCH.md) for the deep version.

---

## Documentation

**Process / state** (read these to know where the project is):
- [`docs/STATUS.md`](./docs/STATUS.md) — **start here.** Current state, last shipped, next up.
- [`docs/ROADMAP.md`](./docs/ROADMAP.md) — long-term phase plan + the rule for context preservation.
- [`CHANGELOG.md`](./CHANGELOG.md) — append-only log of shipped features.

**Design / theory** (read these to understand why):
- [`docs/FRAMEWORK.md`](./docs/FRAMEWORK.md) — the trinity, current canonical design
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — three-layer architecture (NL surface / library / runtime)
- [`docs/RESEARCH.md`](./docs/RESEARCH.md) — categorical foundations, deep theoretical backing
- [`docs/COMPARISON.md`](./docs/COMPARISON.md) — vs. LangChain, DSPy, Pydantic AI, AutoGen
- [`docs/LANDSCAPE.md`](./docs/LANDSCAPE.md) — competitive analysis + honest gaps
- [`docs/OPEN_DECISIONS.md`](./docs/OPEN_DECISIONS.md) — implementation decisions to lock
- [`docs/NEUROCODE_NEURONET.md`](./docs/NEUROCODE_NEURONET.md) — the perfect pair: NeuroCode ↔ NeuroNet duality
- [`docs/VISION.md`](./docs/VISION.md) — original two-layer vision

---

## License

MIT — see [LICENSE](./LICENSE).
