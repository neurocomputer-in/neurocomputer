# 01-core · 06 · Typed I/O and IDE seams

**Status**: drafted. Awaiting user approval.

---

## 1 · Scope

Evolve `conf.json` so the runtime gains lightweight type tags on ports and the future 3D IDE has enough metadata to render, validate, and explain neuros — without coupling the runtime to the IDE.

## 2 · Port shape evolution

Current `conf.json`:

```json
{
  "name": "echo",
  "inputs":  ["text"],
  "outputs": ["reply"]
}
```

New `conf.json` (backward-compatible):

```json
{
  "name": "echo",
  "inputs":  [
    {"name": "text", "type": "str", "description": "Text to echo back.", "optional": false}
  ],
  "outputs": [
    {"name": "reply", "type": "str", "description": "Echoed output."}
  ]
}
```

### 2.1 · Backward compat

- `inputs`/`outputs` entries are normalized at load time:
  - `"text"` → `{"name": "text", "type": "any", "description": "", "optional": false}`
  - `{"name": "text"}` → fills missing fields with defaults.
- Old-shape entries load exactly as today. No forced migration.
- The IDE shows `type: any` as a neutral grey port; dev-agent can suggest upgrades.

### 2.2 · Port entry fields

| field         | required | type    | meaning                                                              |
|---------------|----------|---------|----------------------------------------------------------------------|
| `name`        | yes      | str     | Port identifier (must match kwarg name in `run` for inputs).         |
| `type`        | no       | str     | Type tag (see §3). Defaults to `"any"`.                              |
| `description` | no       | str     | One-line human description. Used in IDE tooltip.                     |
| `optional`    | no       | bool    | Input may be omitted (default false). Outputs ignore this field.     |
| `default`     | no       | json    | Default value if `optional` and not provided.                        |
| `example`     | no       | json    | Sample value for docs / IDE preview.                                 |

## 3 · Type tags (v1, nominal)

Strings. No structural shape checking. The runtime does *not* enforce types; this is metadata for the IDE, planner prompts, and future validators.

| tag          | meaning                                                            |
|--------------|--------------------------------------------------------------------|
| `any`        | untyped (default)                                                  |
| `str`        | string                                                             |
| `int`        | integer                                                            |
| `float`      | floating point                                                     |
| `bool`       | boolean                                                            |
| `json`       | arbitrary JSON-serializable value                                  |
| `list`       | JSON array                                                         |
| `dict`       | JSON object                                                        |
| `neuro_ref`  | the name of another neuro (used by meta-neuros that invoke others) |
| `flow_ref`   | a DAG dict accepted by `DagFlow`                                   |
| `file_path`  | filesystem path (IDE offers a file picker)                         |
| `url`        | URL (IDE validates format)                                         |
| `prompt`     | LLM prompt text (IDE gives a large text area, sticky-note render)  |

Parameterized tags (future, v2): `list<str>`, `dict<str,int>`. Tag grammar is free-form string; parsers just look at the tag name today.

### 3.1 · Why nominal not structural

- Structural (TypedDict-style) requires a schema language. Premature until the IDE catches traction.
- Nominal tags cover 95% of IDE needs (color ports, validate connections, pick sensible editors).
- Upgrade path: add a `schema` field alongside `type` when a structural shape is actually needed. Doesn't break existing confs.

## 4 · Visual metadata (optional)

All optional. Factory ignores them except when exposing through `describe()`.

```json
{
  "icon":       "sparkles",           // lucide icon name, or inline SVG path
  "color":      "#7c3aed",            // node accent color
  "category":   "text.nlp",           // dotted path → library tree folder
  "summary_md": "Condenses text to N sentences using the session LLM.",
  "long_md":    "path/to/docs.md"     // optional, relative to neuro folder
}
```

- `icon` / `color` — render hints, no runtime effect.
- `category` — groups neuros in the IDE's library sidebar.
- `summary_md` — english-mode description (IDE zoom-out view). Max ~240 chars for tiles; longer content lives in `long_md`.
- `long_md` — full reference doc the IDE opens when the user requests details. Markdown, rendered in-app.

## 5 · IDE semantic-zoom modes

The arch exposes the data; the IDE decides rendering. Three canonical levels (IDE free to add more):

### 5.1 · Summary mode (highest zoom)

- Node tile shows: `icon`, `name`, `summary_md` (truncated), `kind` badge (`leaf`/`flow`).
- No ports, no wires. A clean organigram-style view for english-mode conversations.

### 5.2 · Ports mode (mid zoom)

- Full node frame, named typed ports.
- Port color keyed on `type` (str = blue, json = purple, neuro_ref = orange, etc — IDE's choice).
- Wires validated on drop: type-mismatched connections flash red with a tooltip.
- Composite nodes collapsed; double-click expands.

### 5.3 · Internals mode (deepest zoom)

- Leaf: shows `code.py`'s `run` signature + a code snippet, highlighted.
- Flow: expands the graph inside, re-rendered at the same zoom level. Recursive.
- Hot edit: clicking a field surfaces the dev-agent edit channel (`02-dev-agent/`).

Switching modes is instantaneous — the IDE reads all three from the same `describe()` response. No runtime round-trip.

## 6 · Layout / position metadata

Where do node coordinates live?

**Decision**: in a sidecar file per flow, not in `conf.json`.

- `neuros/<flow_name>/layout.json` — optional. Ignored by runtime.
- Contains `{nodes: {n0: {x,y}, n1: {x,y}}, viewport: {x,y,zoom}}` and edge routing hints.
- Git-trackable but decoupled from behavior. Deleting it only loses layout, not function.
- Non-flow neuros don't need layout (they're atoms).

Why sidecar:

- Layout changes (dragging nodes) are frequent and visual; keeping them out of `conf.json` keeps behavioral diffs clean.
- Multiple IDE views can write independent layout files if needed (`layout-3d.json`, `layout-mobile.json`).
- Nothing in the runtime or the dev agent cares — they work on the behavioral spec only.

## 7 · Describe contract (IDE read-only surface)

From `04-registry-and-lib.md` §6, `describe(cid)` returns rich metadata. With this subdoc's additions, a typical entry now looks like:

```json
{
  "name": "summarize",
  "description": "Condense text to N sentences.",
  "category":   "text.nlp",
  "icon":       "sparkles",
  "color":      "#7c3aed",
  "summary_md": "Condenses text to N sentences using the session LLM.",
  "long_md":    "README.md",
  "kind":       "leaf",
  "scope":      "call",
  "uses":       [],
  "inputs":  [
    {"name": "text",      "type": "str", "description": "Input text",       "optional": false},
    {"name": "sentences", "type": "int", "description": "Target length",    "optional": true, "default": 3}
  ],
  "outputs": [
    {"name": "summary", "type": "str", "description": "Condensed output."}
  ]
}
```

Stable keys; additions are additive.

## 8 · Who writes these fields?

- **Hand-authored neuros**: developer fills fields they care about; unset = defaults.
- **AI-authored neuros** (via `neuro_crafter`, `dev_new`, etc.): dev-agent's schema validator (`02-dev-agent/01-robustness-patterns.md`) enforces a minimum — `name`, `description`, at least one input, at least one output. LLM is prompted to fill `summary_md`, `category`, port types.
- **IDE author mode**: the IDE can write `icon`/`color`/`category` through dev-agent edit channels. Runtime reads only; IDE is not privileged to write `conf.json` directly.

## 9 · Decisions locked

1. **Port entries are objects** with `{name, type, description, optional, default?, example?}`. Old string form auto-normalizes.
2. **Nominal types v1** — 13 core tags. No structural validation. Runtime does not enforce.
3. **Visual metadata is optional**: `icon`, `color`, `category`, `summary_md`, `long_md`. Zero runtime effect.
4. **Layout in sidecar** (`layout.json`), never in `conf.json`. Keeps behavior diffs clean.
5. **Three zoom modes** (summary / ports / internals) driven entirely by `describe()` output. Arch doesn't dictate rendering — just supplies data.
6. **Additive only**: every old `conf.json` still loads. Every old caller of `describe()` sees a superset.
7. **Dev-agent enforces minimum metadata** on AI-authored neuros; humans free to skip.

## 10 · Deferred

- Parameterized type tags (`list<str>`, `dict<str,int>`).
- Structural validation with JSON Schema / TypedDict.
- 3D position fields (`z` coordinate, depth layering).
- IDE-specific rendering hints (node shape, port position, collapse state persistence).
- Multi-viewport layout files (mobile / desktop / XR).
- Localization of `description` / `summary_md`.
