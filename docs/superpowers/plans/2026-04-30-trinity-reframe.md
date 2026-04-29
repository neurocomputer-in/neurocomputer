# Trinity Reframe + Hero Imagery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update all user-facing prose (README, neurolang/README, website, slides, key docs) to reflect the reframed Trinity — NeuroNet = the *program* (compiled runnable shareable artifact), not the *runtime* — add a canonical `docs/TRINITY.md`, track the code rename as a deferred decision, and embed the existing Neurocomputer hero image with slots for the two pending hero images.

**Architecture:** Pure prose/HTML edits. No code changes. New canonical `docs/TRINITY.md` becomes the single source of truth; every other surface links to it. A hero image prompt reference file (`docs/hero-image-prompts.md`) stores the prompts for the two images yet to be generated. The drift between docs (new framing) and Python code (old `NeuroNet` Protocol class) is made explicit and tracked in `neurolang/docs/OPEN_DECISIONS.md`.

**Tech Stack:** Markdown, HTML. No build tools. No tests — verification is grep-based after each write.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `docs/TRINITY.md` | **Create** | Canonical Trinity definition, drift note |
| `docs/hero-image-prompts.md` | **Create** | Image-gen prompts for NeuroLang + NeuroNet heroes |
| `README.md` | **Modify** lines 9–19 | New Trinity table + tagline + image section |
| `neurolang/README.md` | **Modify** lines 9–19 | Same Trinity table; link to TRINITY.md |
| `docs/website/index.html` | **Modify** lines 7, 93, 97–113 | Meta desc + Trinity section (card labels, body, intro) |
| `docs/website/neurolang.html` | **Modify** lines 63–82 | Trinity section |
| `docs/website/slides-pitch.html` | **Modify** lines 58–70 | Slide 3 cards + pull-quote |
| `docs/website/slides-tech.html` | **Modify** lines 358, 365–366 | Slide 16 h2 + NeuroNet card |
| `neurolang/docs/FRAMEWORK.md` | **Modify** line 1 (prepend block) | Reframing note at top |
| `neurolang/docs/NEUROCODE_NEURONET.md` | **Modify** line 1 (prepend block) | Reframing note at top |
| `neurolang/docs/OPEN_DECISIONS.md` | **Modify** (append section) | Trinity rename tracked decision |

**Not touched:** any file under `neurolang/neurolang/` (code off-limits), frozen docs (`PAPER_*.md`, `VISION.md`, `RESEARCH*.md`, `LANDSCAPE.md`, `COMPARISON.md`), old specs in `docs/superpowers/specs/` and `neurolang/docs/specs/`, `STATUS.md` and `.claude/CONTEXT.md` (grep confirmed no Trinity refs), `CHANGELOG.md`.

---

## Task 1: Create `docs/TRINITY.md` (canonical source of truth)

**Files:**
- Create: `docs/TRINITY.md`

- [ ] **Step 1: Verify the file doesn't exist yet**

```bash
ls docs/TRINITY.md 2>&1
```

Expected: `ls: cannot access 'docs/TRINITY.md': No such file or directory`

- [ ] **Step 2: Write the file**

Create `docs/TRINITY.md` with this exact content:

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

- [ ] **Step 3: Verify**

```bash
grep "the \*program\*" docs/TRINITY.md
```

Expected: `| **NeuroNet**  | the *program*  | ...`

- [ ] **Step 4: Commit**

```bash
git add docs/TRINITY.md
git commit -m "docs(trinity): add canonical TRINITY.md — NeuroNet is the program"
```

---

## Task 2: Create `docs/hero-image-prompts.md` (image-gen reference)

**Files:**
- Create: `docs/hero-image-prompts.md`

- [ ] **Step 1: Write the file**

Create `docs/hero-image-prompts.md` with this exact content:

```markdown
# Hero Image Prompts — Trinity Triptych

Three hero images for the Trinity. The Neurocomputer image already exists at
`screenshots/desk_mobile_home.png`. The NeuroLang and NeuroNet images need to
be generated and saved to `screenshots/neurolang_mobile_home.png` and
`screenshots/neuronet_mobile_home.png` respectively.

Once generated, embed them in `README.md` and `docs/website/index.html`
(see the `<!-- HERO IMAGES -->` comments already in those files).

---

## Brand Constants (apply to all 3)

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

---

## Prompt 1 — NeuroLang (the language)

Save output to: `screenshots/neurolang_mobile_home.png`

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

---

## Prompt 2 — NeuroNet (the program)

Save output to: `screenshots/neuronet_mobile_home.png`

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

---

## Prompt 3 — Neurocomputer (the environment)

**Already exists at `screenshots/desk_mobile_home.png`. No generation needed.**
```

- [ ] **Step 2: Verify**

```bash
grep "neurolang_mobile_home\|neuronet_mobile_home" docs/hero-image-prompts.md | wc -l
```

Expected: `2`

- [ ] **Step 3: Commit**

```bash
git add docs/hero-image-prompts.md
git commit -m "docs(hero-images): add image-gen prompts for NeuroLang and NeuroNet heroes"
```

---

## Task 3: Update `README.md` Trinity section

**Files:**
- Modify: `README.md` lines 9–19

Current content to replace:
```markdown
## The Trinity

Neurocomputer is one third of a three-name system co-developed with [NeuroLang](./neurolang/):

| | What | Where |
|---|---|---|
| **NeuroLang** | The Python library — typed primitives, plans-as-values, composition | [`./neurolang/`](./neurolang/) (vendored) |
| **NeuroNet** | The live runtime — agents, memory, plans-in-flight, effects | inside any process running NeuroLang code |
| **Neurocomputer** | The IDE + execution environment — fused, like a Lisp Machine | this repo |

NeuroLang is the **language**. NeuroNet is the **runtime**. Neurocomputer is the **environment**.
```

- [ ] **Step 1: Verify old text is present**

```bash
grep "NeuroNet.*live runtime" README.md
```

Expected: `| **NeuroNet** | The live runtime — agents, memory, plans-in-flight, effects | inside any process running NeuroLang code |`

- [ ] **Step 2: Replace the Trinity section**

Replace the block from `## The Trinity` through `NeuroLang is the **language**...` (lines 9–19) with:

```markdown
## The Trinity

Three names. One system. See [`docs/TRINITY.md`](./docs/TRINITY.md) for the canonical definition.

| | Role | What it is | Where |
|---|---|---|---|
| **NeuroLang** | the *language* | Typed Python primitives, plans-as-values, composition syntax. The thing you write in. | [`./neurolang/`](./neurolang/) (vendored) |
| **NeuroNet** | the *program* | A composed network of neuros — runnable, shareable, installable. The thing you ship. | Output of NeuroLang. Lives in `~/.neurolang/neuros/`. |
| **Neurocomputer** | the *environment* | IDE + runtime + OS shell that hosts NeuroNets as apps. The thing you run on. | this repo |

NeuroLang is the **language**. NeuroNet is the **program**. Neurocomputer is the **environment** — write in NeuroLang, ship a NeuroNet, run on Neurocomputer.

### In Images

![Neurocomputer — The AI-Native OS for Thinkers, Builders, and Creators.](screenshots/desk_mobile_home.png)

<!-- HERO IMAGES: Once generated, add side-by-side triptych here.
     See docs/hero-image-prompts.md for NeuroLang and NeuroNet prompts.
     Files go to: screenshots/neurolang_mobile_home.png and screenshots/neuronet_mobile_home.png
-->
```

- [ ] **Step 3: Verify**

```bash
grep "the \*program\*" README.md
grep "hero-image-prompts" README.md
grep "desk_mobile_home.png" README.md
```

All three should return a match.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): update Trinity section — NeuroNet is the program"
```

---

## Task 4: Update `neurolang/README.md` Trinity section

**Files:**
- Modify: `neurolang/README.md` lines 9–19

Current content to replace (lines 9–19):
```markdown
## The Trinity

NeuroLang is one third of a three-name system:

| | What it is | Where it lives |
|---|---|---|
| **NeuroLang** | The Python library — typed primitives, composition, plans-as-values | `pip install neurolang` (this repo) |
| **NeuroNet** | The live runtime graph — agents, memory, plans-in-flight, effects | Inside any process running NeuroLang code |
| **Neurocomputer** | The IDE + execution environment — fused, like a Lisp Machine | [`neurocomputer-in/neurocomputer`](https://github.com/neurocomputer-in/neurocomputer) (reference implementation) |

NeuroLang is the **language**. NeuroNet is the **runtime**. Neurocomputer is the **environment** where you author, compile, execute, and visualize.
```

- [ ] **Step 1: Verify old text is present**

```bash
grep "NeuroNet.*live runtime graph" neurolang/README.md
```

Expected: `| **NeuroNet** | The live runtime graph — agents, memory, plans-in-flight, effects | ...`

- [ ] **Step 2: Replace the Trinity section**

Replace lines 9–19 with:

```markdown
## The Trinity

NeuroLang is one third of a three-name system. See [`docs/TRINITY.md`](../docs/TRINITY.md) for the canonical definition.

| | Role | What it is | Where |
|---|---|---|---|
| **NeuroLang** | the *language* | Typed Python primitives, plans-as-values, composition syntax. The thing you write in. | `pip install neurolang` (this repo) |
| **NeuroNet** | the *program* | A composed network of neuros — runnable, shareable, installable. The thing you ship. | Output of NeuroLang. Lives in `~/.neurolang/neuros/`. |
| **Neurocomputer** | the *environment* | IDE + runtime + OS shell that hosts NeuroNets as apps. The thing you run on. | [`neurocomputer-in/neurocomputer`](https://github.com/neurocomputer-in/neurocomputer) |

NeuroLang is the **language**. NeuroNet is the **program**. Neurocomputer is the **environment** — write in NeuroLang, ship a NeuroNet, run on Neurocomputer.
```

- [ ] **Step 3: Verify**

```bash
grep "the \*program\*" neurolang/README.md
grep "TRINITY.md" neurolang/README.md
```

Both should return a match.

- [ ] **Step 4: Commit**

```bash
git add neurolang/README.md
git commit -m "docs(neurolang): update Trinity section — NeuroNet is the program"
```

---

## Task 5: Update `docs/website/index.html` Trinity section

**Files:**
- Modify: `docs/website/index.html` (lines 7, 93, 97–113)

- [ ] **Step 1: Verify old text is present**

```bash
grep "NeuroNet is the runtime" docs/website/index.html
grep "/// Runtime" docs/website/index.html
```

Both should return a match.

- [ ] **Step 2: Update meta description (line 7)**

Change:
```html
    <meta name="description" content="Neurocomputer is the IDE + runtime for NeuroLang — programmable intelligence built from a single composable unit, the neuro. Voice, web, mobile, 3D IDE, multi-agent rooms.">
```

To:
```html
    <meta name="description" content="Neurocomputer is the environment for NeuroLang — write AI-native programs (NeuroNets) in NeuroLang, run them on Neurocomputer. Voice, web, mobile, 3D IDE, multi-agent rooms.">
```

- [ ] **Step 3: Update Trinity intro paragraph (line 93)**

Change:
```html
            <p class="section-desc">NeuroLang is the language. NeuroNet is the runtime. Neurocomputer is the environment where you author, compile, execute, and visualise — fused, like a Lisp Machine.</p>
```

To:
```html
            <p class="section-desc">NeuroLang is the language. NeuroNet is the program. Neurocomputer is the environment — write in NeuroLang, ship a NeuroNet, run on Neurocomputer.</p>
```

- [ ] **Step 4: Update NeuroLang card label (line 97)**

Change:
```html
                    <div class="label">/// Library</div>
```

To:
```html
                    <div class="label">/// Language</div>
```

- [ ] **Step 5: Update NeuroNet card (lines 102–107) — label + body + link**

Change:
```html
                <div class="trinity-card">
                    <div class="label">/// Runtime</div>
                    <h3>NeuroNet</h3>
                    <p>The live network of running neuros, agents with mailboxes, memory cells, plans-in-flight, effects in motion. Inspectable. Snapshotable. Replayable. Topology you can render, traverse, and modify mid-execution.</p>
                    <p style="margin-top:var(--sp-2);"><a href="architecture.html" style="color:var(--accent);font-size:var(--fs-sm);">See the architecture →</a></p>
                </div>
```

To:
```html
                <div class="trinity-card">
                    <div class="label">/// Program</div>
                    <h3>NeuroNet</h3>
                    <p>A composed network of neuros — authored in NeuroLang, packaged as a runnable, shareable, installable artifact. The apps on the Neurocomputer launcher <em>are</em> NeuroNets. Written once, shipped anywhere.</p>
                    <p style="margin-top:var(--sp-2);"><a href="neurolang.html" style="color:var(--accent);font-size:var(--fs-sm);">Author a NeuroNet →</a></p>
                </div>
```

- [ ] **Step 6: Verify all changes**

```bash
grep "/// Language\|/// Program\|NeuroNet is the program\|Author a NeuroNet" docs/website/index.html
```

Expected: 4 matching lines.

- [ ] **Step 7: Commit**

```bash
git add docs/website/index.html
git commit -m "docs(website): update Trinity section in index.html — NeuroNet is the program"
```

---

## Task 6: Update `docs/website/neurolang.html` Trinity section

**Files:**
- Modify: `docs/website/neurolang.html` lines 63–82

- [ ] **Step 1: Verify old text is present**

```bash
grep "NeuroNet is the runtime" docs/website/neurolang.html
```

Expected: `One system, three names. NeuroLang is the language. NeuroNet is the runtime. Neurocomputer is the environment — fused, like a Lisp Machine.`

- [ ] **Step 2: Update Trinity intro paragraph (line 64)**

Change:
```html
            <p class="section-desc">One system, three names. NeuroLang is the language. NeuroNet is the runtime. Neurocomputer is the environment — fused, like a Lisp Machine.</p>
```

To:
```html
            <p class="section-desc">One system, three names. NeuroLang is the language. NeuroNet is the program. Neurocomputer is the environment — write in NeuroLang, ship a NeuroNet, run on Neurocomputer.</p>
```

- [ ] **Step 3: Update card labels and NeuroNet body (lines 68, 73–76)**

Change:
```html
                <div class="trinity-card">
                    <div class="label">Library</div>
                    <h3>NeuroLang</h3>
                    <p>The Python library. Typed primitives, the <code>@neuro</code> decorator, composition operators. <code>pip install neurolang</code> (vendored at <code>./neurolang/</code> in this repo).</p>
                </div>
                <div class="trinity-card">
                    <div class="label">Runtime</div>
                    <h3>NeuroNet</h3>
                    <p>The live network of running neuros, agents with mailboxes, memory, and plans-in-flight. <code>net.topology()</code>, <code>net.snapshot()</code>, <code>net.render()</code>. Inspectable from any process.</p>
                </div>
                <div class="trinity-card">
                    <div class="label">Environment</div>
                    <h3>Neurocomputer</h3>
                    <p>The IDE + runtime. Author, compile, execute, visualise. Voice in. 3D graph editing. Multi-agent rooms. The flagship implementation of the trinity.</p>
                </div>
```

To:
```html
                <div class="trinity-card">
                    <div class="label">Language</div>
                    <h3>NeuroLang</h3>
                    <p>The Python library. Typed primitives, the <code>@neuro</code> decorator, composition operators. <code>pip install neurolang</code> (vendored at <code>./neurolang/</code> in this repo).</p>
                </div>
                <div class="trinity-card">
                    <div class="label">Program</div>
                    <h3>NeuroNet</h3>
                    <p>A composed network of neuros — authored in NeuroLang, packaged as a runnable, shareable, installable artifact. The apps on the Neurocomputer launcher <em>are</em> NeuroNets.</p>
                </div>
                <div class="trinity-card">
                    <div class="label">Environment</div>
                    <h3>Neurocomputer</h3>
                    <p>The IDE + runtime. Author, compile, execute, visualise. Voice in. 3D graph editing. Multi-agent rooms. The flagship implementation of the trinity.</p>
                </div>
```

- [ ] **Step 4: Verify**

```bash
grep "NeuroNet is the program\|<div class=\"label\">Program" docs/website/neurolang.html
```

Expected: 2 matches.

- [ ] **Step 5: Commit**

```bash
git add docs/website/neurolang.html
git commit -m "docs(website): update Trinity section in neurolang.html — NeuroNet is the program"
```

---

## Task 7: Update `docs/website/slides-pitch.html` Slide 3

**Files:**
- Modify: `docs/website/slides-pitch.html` lines 62–70

- [ ] **Step 1: Verify old text is present**

```bash
grep "live runtime.*mailboxes\|NeuroNet is the runtime" docs/website/slides-pitch.html
```

Expected: matching line.

- [ ] **Step 2: Update NeuroNet card body (line 62–64) and pull-quote (line 70)**

Change:
```html
                <div class="gcard">
                    <h4>NeuroNet</h4>
                    <p>The live runtime. Agents with mailboxes, memory cells, plans-in-flight, effects in motion.</p>
                </div>
```

To:
```html
                <div class="gcard">
                    <h4>NeuroNet</h4>
                    <p>The program. A composed network of neuros — authored in NeuroLang, runnable, shareable, installable. The apps are NeuroNets.</p>
                </div>
```

Change:
```html
            <div class="pull" style="margin-top:1em;">NeuroLang is the language. NeuroNet is the runtime. Neurocomputer is the environment.</div>
```

To:
```html
            <div class="pull" style="margin-top:1em;">NeuroLang is the language. NeuroNet is the program. Neurocomputer is the environment.</div>
```

- [ ] **Step 3: Verify**

```bash
grep "NeuroNet is the program\|runnable, shareable, installable" docs/website/slides-pitch.html
```

Expected: 2 matches.

- [ ] **Step 4: Commit**

```bash
git add docs/website/slides-pitch.html
git commit -m "docs(website): update Trinity slide in slides-pitch.html"
```

---

## Task 8: Update `docs/website/slides-tech.html` Slide 16

**Files:**
- Modify: `docs/website/slides-tech.html` lines 358, 365–366

- [ ] **Step 1: Verify old text is present**

```bash
grep "Library\. Runtime\. Environment\." docs/website/slides-tech.html
grep "live runtime.*plans-in-flight" docs/website/slides-tech.html
```

Both should return a match.

- [ ] **Step 2: Update slide h2 (line 358)**

Change:
```html
            <h2>Library. Runtime. Environment.</h2>
```

To:
```html
            <h2>Language. Program. Environment.</h2>
```

- [ ] **Step 3: Update NeuroNet card (lines 364–367)**

Change:
```html
                <div class="gcard">
                    <h4>NeuroNet</h4>
                    <p>The live runtime. Agents, memory, plans-in-flight. <code>net.topology()</code>, <code>net.snapshot()</code>, <code>net.render()</code>.</p>
                </div>
```

To:
```html
                <div class="gcard">
                    <h4>NeuroNet</h4>
                    <p>The program. Composed neuros packaged as a runnable, shareable artifact. Apps on Neurocomputer are NeuroNets. Manifest: name, version, deps, signature.</p>
                </div>
```

- [ ] **Step 4: Verify**

```bash
grep "Language\. Program\. Environment\.\|runnable, shareable artifact" docs/website/slides-tech.html
```

Expected: 2 matches.

- [ ] **Step 5: Commit**

```bash
git add docs/website/slides-tech.html
git commit -m "docs(website): update Trinity slide in slides-tech.html"
```

---

## Task 9: Add reframing note to `neurolang/docs/FRAMEWORK.md`

**Files:**
- Modify: `neurolang/docs/FRAMEWORK.md` (prepend block before line 1)

- [ ] **Step 1: Verify current first line**

```bash
head -3 neurolang/docs/FRAMEWORK.md
```

Expected:
```
# The NeuroLang Framework — The Trinity

> **NeuroLang** (the library) · **NeuroNet** (the live network) · **Neurocomputer** (the IDE + execution environment)
```

- [ ] **Step 2: Prepend reframing note**

Insert the following block at the very top of the file (before line 1):

```markdown
> **⚠ Reframing note (2026-04-30):** Since this document was written, the
> Trinity has been reframed. **NeuroNet is now the *program*** (the compiled,
> runnable, shareable artifact), not the *runtime*. The runtime concept moves
> under Neurocomputer (the environment). See
> [`docs/TRINITY.md`](../../docs/TRINITY.md) for the canonical definition.
> This document retains the old framing in §2 ("The Live Network") and is
> queued for a full rewrite alongside the code rename (tracked in
> [`OPEN_DECISIONS.md`](./OPEN_DECISIONS.md)).

---

```

(Two trailing newlines after `---` before the existing `# The NeuroLang Framework` heading.)

- [ ] **Step 3: Verify**

```bash
head -5 neurolang/docs/FRAMEWORK.md
```

Expected: first line is `> **⚠ Reframing note (2026-04-30):**`

- [ ] **Step 4: Commit**

```bash
git add neurolang/docs/FRAMEWORK.md
git commit -m "docs(framework): add Trinity reframing note at top of FRAMEWORK.md"
```

---

## Task 10: Add reframing note to `neurolang/docs/NEUROCODE_NEURONET.md`

**Files:**
- Modify: `neurolang/docs/NEUROCODE_NEURONET.md` (prepend block before line 1)

- [ ] **Step 1: Verify current first line**

```bash
head -3 neurolang/docs/NEUROCODE_NEURONET.md
```

Expected:
```
# NeuroCode ↔ NeuroNet — The Perfect Pair

> **NeuroCode** is what you write. **NeuroNet** is what it becomes.
```

- [ ] **Step 2: Prepend reframing note**

Insert the following block at the very top of the file (before line 1):

```markdown
> **⚠ Reframing note (2026-04-30):** Since this document was written, the
> Trinity has been reframed. **NeuroNet is now the *program*** — which aligns
> well with this document's framing of "NeuroCode is what you write, NeuroNet
> is what it becomes." The key update: "what it becomes" is now understood as
> a *packaged runnable artifact* (not the live runtime graph). See
> [`docs/TRINITY.md`](../../docs/TRINITY.md) for the canonical definition. The
> body of this document remains valid in spirit; update "live runtime graph"
> references when the code rename lands.

---

```

- [ ] **Step 3: Verify**

```bash
head -3 neurolang/docs/NEUROCODE_NEURONET.md
```

Expected: first line is `> **⚠ Reframing note (2026-04-30):**`

- [ ] **Step 4: Commit**

```bash
git add neurolang/docs/NEUROCODE_NEURONET.md
git commit -m "docs(neurolang): add Trinity reframing note at top of NEUROCODE_NEURONET.md"
```

---

## Task 11: Add Trinity rename decision to `neurolang/docs/OPEN_DECISIONS.md`

**Files:**
- Modify: `neurolang/docs/OPEN_DECISIONS.md` (append new cluster at bottom, before the closing line)

- [ ] **Step 1: Verify the file ends with the Cluster K section**

```bash
tail -10 neurolang/docs/OPEN_DECISIONS.md
```

Expected: last content line is `*Document at `/docs/OPEN_DECISIONS.md`. Maintained as decisions are resolved.*`

- [ ] **Step 2: Append the new cluster**

Append the following to the end of `neurolang/docs/OPEN_DECISIONS.md`, after the existing closing line:

```markdown

---

## Cluster L — Trinity Rename (Deferred)

**Status: deferred — docs reframed 2026-04-30, code unchanged.**

The Trinity was reframed: NeuroNet now means *the program* (the artifact),
not *the runtime contract*. Docs, README, and website already reflect the
new framing. Code still uses the old meaning:

- `NeuroNet` (Protocol) in `neurolang/runtime/protocol.py`
- `LocalNeuroNet` in `neurolang/runtime/local.py`
- Re-exports in `neurolang/__init__.py`

### L1. Pending rename

When we have appetite (pre-alpha, no external consumers — safe window):

| Symbol | Current | Rename to |
|---|---|---|
| `NeuroNet` (Protocol) | runtime contract | `Runtime` (or `Host` / `NeuroHost` — TBD) |
| `LocalNeuroNet` | in-process runtime impl | `LocalRuntime` |
| `Plan` (or `Plan` + manifest wrapper) | compiled flow | `NeuroNet` (the program) |

**Recommendation:** rename to `Runtime` for the Protocol (short, clear, no brand conflict). Expose a `NeuroNet` type as `Plan` + a manifest dataclass (`name: str`, `version: str`, `deps: list[str]`, `signature: str`) so a NeuroNet can be serialized, packaged, and installed.

### L2. Blast radius

- `neurolang/__init__.py` — re-export names change
- `neurolang/runtime/protocol.py` — class rename
- `neurolang/runtime/local.py` — class rename + `__repr__`
- Any consumer in `neurocomputer/` that imports `NeuroNet` or `LocalNeuroNet` from `neurolang`
- `FRAMEWORK.md` and `NEUROCODE_NEURONET.md` body text (already flagged for rewrite)

### L3. Doc drift rule (until rename lands)

In **Python imports**: `NeuroNet` means the old "runtime contract".
In **prose**: `NeuroNet` means the new "program / artifact". Imports are
the only surviving use of the old sense.
```

- [ ] **Step 3: Verify**

```bash
grep "Cluster L\|Trinity Rename" neurolang/docs/OPEN_DECISIONS.md
```

Expected: `## Cluster L — Trinity Rename (Deferred)`

- [ ] **Step 4: Commit**

```bash
git add neurolang/docs/OPEN_DECISIONS.md
git commit -m "docs(open-decisions): track Trinity rename as Cluster L (deferred)"
```

---

## Self-Review

Running spec coverage check against `docs/superpowers/specs/2026-04-30-trinity-reframe-design.md`:

| Spec §  | Plan task |
|---|---|
| §3 Create `docs/TRINITY.md` | Task 1 ✓ |
| §4.1 `README.md` | Task 3 ✓ |
| §4.2 `neurolang/README.md` | Task 4 ✓ |
| §4.3 `docs/website/index.html` | Task 5 ✓ |
| §4.4 `docs/website/neurolang.html` | Task 6 ✓ |
| §4.5 `docs/website/slides-pitch.html` | Task 7 ✓ |
| §4.6 `docs/website/slides-tech.html` | Task 8 ✓ |
| §4.7 `STATUS.md` | Confirmed no Trinity refs (grep returned empty) — no task needed ✓ |
| §4.8 `neurolang/docs/FRAMEWORK.md` | Task 9 ✓ |
| §4.9 `neurolang/docs/NEUROCODE_NEURONET.md` | Task 10 ✓ |
| §4.10 `neurolang/docs/OPEN_DECISIONS.md` | Task 11 ✓ |
| §4.11 `.claude/CONTEXT.md` | Confirmed no Trinity refs (grep returned empty) — no task needed ✓ |
| §5 Hero image prompts | Task 2 ✓ |
| §5.5 Image slots in README | Task 3 (image section added) ✓ |
| §5.5 Image slots in index.html | Not explicitly in a task — **gap**. Task 5 updates the Trinity section body but doesn't add an image slot. Add a step to Task 5. *(Fixed below.)* |

**Gap fix:** Task 5 is missing an image slot in `docs/website/index.html`. After the trinity cards close (`</div>` closing the `trinity-row`), add:

```html
            <!-- HERO IMAGES: Replace this comment once hero images are generated.
                 See docs/hero-image-prompts.md. Files:
                   screenshots/neurolang_mobile_home.png
                   screenshots/neuronet_mobile_home.png
                   screenshots/desk_mobile_home.png (exists)
            -->
```

Add this as **Step 6a** in Task 5, between the existing Step 6 (verify) and Step 7 (commit). Insert after line 114 (`</section>`) or at the bottom of the trinity `<section>` block.

**Placeholder scan:** No TBD, TODO, or incomplete steps found.

**Type consistency:** No code types — prose/HTML only. No inconsistencies.
