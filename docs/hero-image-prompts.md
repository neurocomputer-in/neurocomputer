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
