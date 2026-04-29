# Trinity Reframe + Hero Imagery — Design

> Date: 2026-04-30
> Status: spec, awaiting user review
> Scope: docs + website + screenshots only — no code changes in this spec

## 1. Context

The repo's "Trinity" framing — the three-name system **NeuroLang / NeuroNet /
Neurocomputer** — currently treats `NeuroNet` as the *runtime*. That framing
is muddled because the runtime concept is already part of Neurocomputer
(it's literally "IDE + execution environment"), leaving no clean name for the
*compiled, runnable, shareable artifact* that the codebase already produces
and stores in `~/.neurolang/neuros/`.

The reframe (decided 2026-04-30):

- **NeuroLang** is the *language* — typed Python primitives, plans-as-values,
  composition syntax. The thing you write in.
- **NeuroNet** is the *program* — a composed network of neuros, runnable,
  shareable, installable. The thing you ship.
- **Neurocomputer** is the *environment* — IDE + runtime + OS shell that
  hosts NeuroNets as apps. The thing you run on.

Tagline pattern: **write in NeuroLang → ship a NeuroNet → run on Neurocomputer**.

The apps on the Neurocomputer launcher (NeuroResearch, NeuroVoice, OpenCode,
NL Dev, NeuroWrite, etc.) **are NeuroNets**. That closes the loop.

This spec covers two parallel deliverables:
1. Sweeping the new framing across README + neurolang/README + website +
   key docs, with a single canonical source of truth.
2. Two new hero images (NeuroLang, NeuroNet) matching the existing
   Neurocomputer screenshot, plus README/website integration.

## 2. Doc/code drift policy

The Python library currently exports `NeuroNet` (Protocol) and
`LocalNeuroNet` from `neurolang/runtime/` — these are the *runtime contract*,
reflecting the old framing. Under the new framing, that role belongs in
Neurocomputer (the environment), and `NeuroNet` should name the *program*
(the compiled+packaged Plan).

**Decision: docs lead, code follows.**

We update prose now; we do not rename Python symbols in this spec. Pre-alpha,
no external consumers, but a code rename touches imports across many files
and is its own work item. The drift is tracked, not hidden.

The future code rename (out of scope here, to be planned separately):

- `NeuroNet` (Protocol, `neurolang/runtime/protocol.py`) → `Runtime`
  (or `Host` / `NeuroHost` — to be decided in the rename spec)
- `LocalNeuroNet` (`neurolang/runtime/local.py`) → `LocalRuntime`
- `Plan` (or a `Plan` + manifest wrapper carrying name/version/deps/signature)
  → exposed as `NeuroNet` to user-facing API

Until the rename lands, the rule is:
- In **Python imports** (`from neurolang import NeuroNet`), `NeuroNet` means
  the old "runtime contract" sense.
- In **prose** (READMEs, website, slides, docs), `NeuroNet` means the new
  "program / artifact" sense.

This entry will be added to `neurolang/docs/OPEN_DECISIONS.md` so future
contributors see it.

## 3. Canonical source of truth — `docs/TRINITY.md` (new file)

A single page that defines the Trinity. README, neurolang/README, and the
website all link here. This avoids 25 files drifting out of sync later.

Full content:

```markdown
# The Trinity

Neurocomputer is one third of a three-name system. Each name is a different
*kind of thing*, not a different view of the same thing.

| | Role | What it is | Where |
|---|---|---|---|
| **NeuroLang** | the *language* | Typed Python primitives, plans-as-values, composition syntax. The thing you write in. | `pip install neurolang` |
| **NeuroNet**  | the *program*  | A composed network of neuros — runnable, shareable, installable. The thing you ship. | Output of NeuroLang. Lives in `~/.neurolang/neuros/` or any package registry. |
| **Neurocomputer** | the *environment* | IDE + runtime + OS shell that hosts NeuroNets as apps. The thing you run on. | This repo. |

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

Tracked in `neurolang/docs/OPEN_DECISIONS.md` (entry: *Trinity rename*).
Until that change lands, when you read `NeuroNet` in *Python imports* it
means the old "runtime" sense; when you read it in *prose* it means the new
"program" sense. Imports are the only place the old usage survives.
```

## 4. Sweep targets — per-file changes

Tagline pattern across all surfaces (rhythmic, brand-cohesive):

- **NeuroLang** → "The AI-Native Language for Thinkers, Builders, and Creators."
- **NeuroNet** → "AI-Native Programs for Thinkers, Builders, and Creators."
- **Neurocomputer** → "The AI-Native OS for Thinkers, Builders, and Creators." (existing, locked)

### 4.1 `README.md` (top of repo)

Replace the existing `## The Trinity` section (lines 9–19) with the new
table and tagline. Add a "see [`docs/TRINITY.md`](./docs/TRINITY.md) for the
canonical definition" link. Keep everything else (Quickstart, framework
docs, etc.) untouched.

### 4.2 `neurolang/README.md`

Replace the existing `## The Trinity` section (lines 9–19) with the same
new table. Link to `docs/TRINITY.md` in the parent repo (or relative
`../docs/TRINITY.md` since the neurolang dir is vendored).

### 4.3 `docs/website/index.html`

- **Meta description** (line 7): update to reflect new framing.
- **Hero label** (line 59): unchanged ("Open Source · NeuroLang · NeuroNet · Neurocomputer").
- **Trinity section** (lines 89–113):
  - Update intro `<p class="section-desc">` (line 93) to:
    *"NeuroLang is the language. NeuroNet is the program. Neurocomputer is the environment — write in NeuroLang, ship a NeuroNet, run on Neurocomputer."*
  - Update card labels (lines 97, 103, 109): `Library` → `Language`,
    `Runtime` → `Program`, `Environment` → `Environment` (unchanged).
  - Update NeuroNet card body (line 105) to the new "program" framing.
  - Add (where appropriate) the trio of hero images (see §5).
- **CTA section** (line 304): swap "trinity is taking shape" line if it now
  reads as obsolete; keep otherwise.

### 4.4 `docs/website/neurolang.html`

- **Trinity section** (lines 60–64): update the section-desc to the new
  framing.

### 4.5 `docs/website/slides-pitch.html`

- **Slide 3** (lines 52–72): update NeuroNet card body (line 63) and
  pull-quote (line 70) to the new framing.

### 4.6 `docs/website/slides-tech.html`

- **Slide 16** (lines 355+): update NeuroNet card body (line 366) to the
  new framing. Note: the body references `net.topology()`, `net.snapshot()`,
  `net.render()` which are runtime APIs — these are *true of the runtime*,
  not the program. Keep as a footnote: "These are runtime APIs (the
  environment side), not part of the NeuroNet program itself." Or remove
  the API references and replace with manifest fields (`name`, `version`,
  `deps`).

### 4.7 `STATUS.md`

Grep for `Trinity|trinity|NeuroNet` references in this file during
implementation. If a Trinity one-liner exists, update it to the new
framing. If the only mention is `NeuroNet` in a non-definitional context
(e.g., a feature note), no change required. If no match, no change.

### 4.8 `neurolang/docs/FRAMEWORK.md`

This doc is structurally tied to the old framing (entire section 2 is
"NeuroNet — The Live Network"). Do **not** rewrite the whole doc.
Instead, add a clearly-marked block at the top:

```markdown
> **Reframing note (2026-04-30):** Since this doc was written, the
> Trinity has been reframed. NeuroNet is now the *program* (the
> compiled, runnable, shareable artifact), not the *runtime*. The
> runtime concept moves under Neurocomputer. See
> [`docs/TRINITY.md`](../../docs/TRINITY.md) for the canonical definition.
> This document still describes the old framing for §2 ("The Live
> Network") — it is queued for rewrite alongside the code rename
> (tracked in `docs/OPEN_DECISIONS.md`).
```

Mark this doc as `needs-rewrite-when-code-renamed`.

### 4.9 `neurolang/docs/NEUROCODE_NEURONET.md`

Same approach: add a short reframing-note block at the top pointing to
`docs/TRINITY.md`. Body left intact for now.

### 4.10 `neurolang/docs/OPEN_DECISIONS.md`

Add a new tracked decision:

```markdown
## Trinity rename (deferred)

Status: deferred — docs reframed 2026-04-30, code unchanged.

The Trinity was reframed: NeuroNet now means *the program* (the artifact),
not *the runtime contract*. Code still uses the old meaning:
- `NeuroNet` (Protocol) in `neurolang/runtime/protocol.py`
- `LocalNeuroNet` in `neurolang/runtime/local.py`
- Re-exports in `neurolang/__init__.py`

Pending rename when we have appetite:
- `NeuroNet` Protocol → `Runtime` (final name TBD: `Runtime` / `Host` / `NeuroHost`)
- `LocalNeuroNet` → `LocalRuntime`
- `Plan` (or `Plan` + manifest wrapper) → `NeuroNet`

Blast radius: `neurolang/__init__.py` exports, ~5 internal call sites in
`neurolang/`, and any consumer in `neurocomputer/` that imports from
`neurolang`. Pre-alpha, no external consumers — safe window for the rename.

See `docs/TRINITY.md` (parent repo) for the prose framing this rename
is intended to align code with.
```

### 4.11 `.claude/CONTEXT.md`

Grep for `Trinity|trinity|NeuroNet` during implementation. If the file
summarizes Trinity for Claude/agent context, update the one-liner to
the new framing. If only passing mentions, leave alone.

### 4.12 Files **not touched** in this spec

- `neurolang/neurolang/__init__.py` (code)
- `neurolang/neurolang/runtime/protocol.py` (code)
- `neurolang/neurolang/runtime/local.py` (code)
- `neurolang/neurolang/runtime/__init__.py` (code)
- `neurolang/CHANGELOG.md` — historical, leave as-is (noting the change in
  the sweep summary commit message is enough)
- `neurolang/docs/PAPER_NEUROLANG_FOUNDATIONS.md` — paper, frozen
- `neurolang/docs/VISION.md`, `RESEARCH.md`, `LITERATURE_REVIEW_*.md`,
  `RESEARCH_BRAINSTORM_*.md`, `VISION_NOTES_RAW.md` — research/vision
  docs, frozen
- All other spec/plan files in `docs/superpowers/specs/` and
  `neurolang/docs/specs/` — historical specs, frozen

These files retain the old framing as historical context. They are not
load-bearing for new readers (who land on README → TRINITY.md first).

## 5. Hero imagery — three-image triptych

### 5.1 Brand constants (apply to all 3 images)

```
ASPECT: 3:2 landscape (~1536×1024)
COMPOSITION:
  - Tablet left (~60% frame width), phone right (~35%), both modern bezel-less
  - Photorealistic, slight 3D tilt facing camera, suspended in space (no ground)
  - Screens self-illuminated, fully readable, casting colored light onto bezels
  - Wordmark top-center w/ infinity-loop logo, tagline directly below in light gray
  - Tiny role label under tagline (italic, small): "the language" / "the program" / "the environment"
BACKGROUND:
  - Full-bleed deep navy → dark purple radial gradient
  - Soft starfield (small white/blue points)
  - Faint constellation lines (~10-15% opacity, neural-network feel)
  - Subtle corner vignette
LIGHTING:
  - Soft top-down ambient + cool rim-light on bezels
  - Screen content drives accent color spilling onto bezel edges
STYLE:
  - Photorealistic hardware, flat modern dark-mode UI on screens
  - Premium product-shot vibe; calm, futuristic, not neon-overload
  - Sans-serif type (Inter / SF-Pro feel)
NEGATIVE:
  - No human hands, no people, no watermarks, no third-party logos
  - No chromatic aberration overload, no busy 3D render artifacts
  - No fictional brand names on screens
REFERENCE:
  - Match the look-and-feel of screenshots/desk_mobile_home.png (the existing
    Neurocomputer hero). That image is kept as-is; the two new images should
    sit beside it as a triptych.
```

### 5.2 Prompt 1 — NeuroLang (the language)

```
WORDMARK: "NeuroLang" + infinity-loop logo (white)
TAGLINE: "The AI-Native Language for Thinkers, Builders, and Creators."
ROLE LABEL: "the language"
ACCENT: cyan / electric blue
TABLET SCREEN: dark code editor (deep navy bg)
  - Python source for a neuro composition, line numbers in dim gray
  - import line: from neurolang import Plan, Model, Memory, Skill
  - @neuro decorator highlighted cyan
  - Plan composition visible: Plan.then(model).then(memory).parallel(skill_a, skill_b)
  - inline type signatures glowing soft cyan, e.g. Plan[Context, Reply]
  - syntax: keywords cyan, strings soft green, functions soft yellow
  - small "▷ compile" pill bottom-right, glowing cyan
PHONE SCREEN: the compiled plan rendered as a glowing DAG
  - vertical labeled nodes: Context → Model → Memory → (Skill A ‖ Skill B) → Reply
  - rounded rectangles with type name + small icon
  - cyan edges, labeled w/ type names (: Context, : Reply)
VISUAL LINK: faint cyan trail drifting from tablet's compile pill toward phone's DAG
  (reads as: source compiles to plan-as-value)
```

### 5.3 Prompt 2 — NeuroNet (the program)

```
WORDMARK: "NeuroNet" + infinity-loop logo (white)
TAGLINE: "AI-Native Programs for Thinkers, Builders, and Creators."
ROLE LABEL: "the program"
ACCENT: magenta / violet
BOTH SCREENS: render the same NeuroNet artifact as a bordered "chip"
TABLET SCREEN: large detailed view
  - rectangular frame, beveled metallic edge w/ subtle violet rim-light
  - name plate top: "NeuroResearch · v1.2 · signed"
  - inside the frame: a clear topology of named neuro nodes wired together —
      Researcher (Agent), web_search (Skill), pdf_read (Skill),
      summarize (Tool-loop), memory_write (Memory), gpt-5 (Model)
  - edges glowing magenta/violet
  - footer pills: "7 neuros · 3 deps · 14 KB"
  - reads as: a sealed-but-transparent module, like a chip under glass
PHONE SCREEN: same chip rendered more compactly (card view)
  - same name plate, smaller topology
  - subtle "Install" pill at bottom (hints at shareability, not the focus)
VISUAL CUE: chip casts magenta glow onto bezels; phone implies portability
```

### 5.4 Prompt 3 — Neurocomputer (the environment)

**Decision: keep the existing `screenshots/desk_mobile_home.png` as the
Neurocomputer hero.** It's a real screenshot composite of the actual product
and reads more authentic than a fully-generated image would. The other two
images are generated to match its bg/composition/wordmark style.

For documentation, the spec the existing image conforms to:

```
WORDMARK: "Neuro" + infinity-loop logo (white)   [matches existing image]
TAGLINE: "The AI-Native OS for Thinkers, Builders, and Creators."   [locked, existing]
ROLE LABEL: "the environment"
ACCENT: multi (warm+cool spread from app icons)
TABLET SCREEN: Desk launcher
  - left sidebar: Main Workspace, All Projects, Open Sessions, Profile, Settings
  - large grid of colorful rounded-square app icons (the NeuroNets):
      Neuro, OpenClaw, OpenCode, NL Dev, IDE, NeuroVoice, NeuroResearch,
      NeuroWrite, NeuroData, NeuroFiles, NeuroEmail, NeuroCalendar,
      NeuroNotes, NeuroBrowse, Terminal, Desktop
  - bottom dock w/ frequently-used apps
PHONE SCREEN: same launcher, mobile layout
  - 4-col grid of same apps, bottom dock
SUBTITLE INSIDE FRAME (aspirational; absent in current image):
  "Every app is a NeuroNet."
NOTE: closes the loop — the chips authored in NeuroLang and packaged as
NeuroNets are the apps shown here, running on Neurocomputer.
```

The current `desk_mobile_home.png` does **not** include the "Every app is
a NeuroNet." subtitle. Decision: **keep the image as-is for now**; place
the closing-the-loop line in surrounding markup (caption under the
triptych in README/website) instead of inside the image. If we later
regenerate or photoshop the Neurocomputer hero, add the subtitle then.

### 5.5 Image storage + integration

- New images saved to `screenshots/`:
  - `screenshots/neurolang_mobile_home.png` (NeuroLang hero)
  - `screenshots/neuronet_mobile_home.png` (NeuroNet hero)
  - `screenshots/desk_mobile_home.png` (existing, unchanged)
- Embedded in `README.md` Trinity section as a stacked or side-by-side
  triptych (final markup decided in implementation plan).
- Embedded in `docs/website/index.html` Trinity section, one image per
  trinity-card, sized to fit existing card layout.
- Optional: also in `neurolang/README.md` Trinity section.

## 6. Out of scope

- Renaming Python symbols (`NeuroNet` Protocol, `LocalNeuroNet`, `Plan`).
  Tracked in `neurolang/docs/OPEN_DECISIONS.md`; needs its own spec.
- Rewriting `neurolang/docs/FRAMEWORK.md` body (§2 onward) to the new
  framing. Queued for the rename spec.
- Generating the actual hero images. The prompts are produced here; image
  generation happens in implementation.
- Updating frozen historical docs (papers, vision notes, old specs).

## 7. Open follow-ups (deferred, tracked)

1. Code rename spec (above).
2. FRAMEWORK.md / NEUROCODE_NEURONET.md rewrite to match new framing
   (paired with code rename).
3. Decide final name for the runtime Protocol class (`Runtime` /
   `Host` / `NeuroHost` / other).

## 8. Approval

This spec is awaiting user review. Once approved, implementation plan
follows (writing-plans skill).
