# The Trinity

Neurocomputer is one third of a three-name system. Each name is a different
*kind of thing*, not a different view of the same thing.

| | Role | What it is | Where |
|---|---|---|---|
| **NeuroLang** | the *language* | Typed Python primitives, plans-as-values, composition syntax. The thing you write in. | `pip install neurolang` |
| **NeuroNet**  | the *program*  | A composed network of neuros — runnable, shareable, installable. The thing you ship. | Output of NeuroLang. Lives in `~/.neurolang/neuros/` (or a package registry, planned). |
| **Neurocomputer** | the *environment* | IDE + execution environment + OS shell that hosts NeuroNets as apps. The thing you run on. | This repo. |

> Write in **NeuroLang** → ship a **NeuroNet** → run on **Neurocomputer**.

The apps you see on the Neurocomputer launcher (NeuroResearch, NeuroVoice,
OpenCode, NL Dev, …) **are NeuroNets**. That closes the loop.

---

## Doc/code drift (tracked)

The Python library currently exports `NeuroNet` (Protocol) and
`LocalNeuroNet` as the *runtime contract*, reflecting an earlier framing
where NeuroNet meant "the live runtime graph". The current framing (above)
treats NeuroNet as the *program* — the artifact. The runtime concept moves
under Neurocomputer.

**Pending code change** (deferred — pre-alpha, no external consumers yet):
- `NeuroNet` (Protocol) → `Runtime` (or `Host`)
- `LocalNeuroNet` → `LocalRuntime`
- `Plan` (or a `Plan` + manifest wrapper) → `NeuroNet`

Tracked in `neurolang/docs/OPEN_DECISIONS.md` (entry: *Cluster L — Trinity rename*).
Until that change lands, when you read `NeuroNet` in *Python imports* it
means the old "runtime" sense; when you read it in *prose* it means the new
"program" sense. Imports are the only place the old usage survives.
