# S4 — 3D IDE Profile Mode

**Master plan:** [`2026-04-28-MASTER-neurolang-integration-plan.md`](./2026-04-28-MASTER-neurolang-integration-plan.md)
**Status:** DRAFT
**Depends on:** S1 (NL profile shipped — provides `nl_*` neuros to highlight)
**Blocks:** demo
**ETA:** 30–45 minutes

---

## Goal

Make the existing 3D IDE **aware of which profile is active** and surface that visually so the user can see at a glance: "I am in NeuroLang dev mode — these are NeuroLang neuros, those are not." The change is small and visual; we are NOT rebuilding the IDE.

Three pieces:

1. A **profile badge** — a small chip in the IDE header showing the active profile (e.g., `🔬 neurolang_dev`).
2. **Color-coded nodes** — when a profile is active, the neuros in that profile's `neuros` glob list pulse / glow in the profile's accent color; non-matching neuros are dimmed.
3. **Profile switcher** — a dropdown next to the badge that switches profile via the existing agent-switching API (`POST /agent/switch`-like endpoint that already exists).

---

## Background — what exists today

`neuro_web/components/neuroide/Graph3D.tsx` already has a `NS_COLOR` table that paints each neuro by its `kind_namespace`. We will:

- **Add** `nl: '#22d3ee'` (cyan) to `NS_COLOR` for NeuroLang neuros (matches the `kind_namespace="nl"` set in S1's `conf.json`).
- **Add** a `dimmedFor: string[] | null` prop to `<Graph3D>` that, when non-null, dims any neuro whose name does not match any glob in the list.
- **Add** an emission/glow uniform on the meshes for the active set (subtle cyan pulse — drei's `<Sparkles>` or a custom shader pass).

`neuro_web/components/neuroide/NeuroIDEPanel.tsx` already fetches from the backend at `localhost:7001`. It will:

- **Fetch** the active profile from `/api/profile/active` (new endpoint — minimal, returns `{profile, planner, replier, neuros}`).
- **Pass** `dimmedFor={activeProfile.neuros}` to `<Graph3D>`.

---

## Files to add / edit

### New

- `neuro_web/components/neuroide/ProfileBadge.tsx` — tiny component (~40 lines): chip + dropdown.
- `neuro_web/lib/profileApi.ts` — typed fetch wrapper for `/api/profile/active`, `/api/profile/list`, `/api/profile/switch`.

### Edit

- `neuro_web/components/neuroide/Graph3D.tsx`
  - Add `'nl': '#22d3ee'` (and matching `'nl_dev': '#a78bfa'` for the agent badge later) to `NS_COLOR`.
  - Add `dimmedFor?: string[] | null` to `Props`.
  - Apply `material.opacity = 0.25` (or scale 0.6) to non-matching nodes.
  - Apply a subtle pulse animation to matching nodes (multiply emissive intensity by `0.5 + 0.5*sin(t*2)`).
- `neuro_web/components/neuroide/NeuroIDEPanel.tsx`
  - Render `<ProfileBadge>` above the search input.
  - Track active profile in state; pass globs to `<Graph3D dimmedFor=...>`.
- `neurocomputer/server.py` — add three small endpoints:
  - `GET /api/profile/active` → returns the profile of the currently-selected agent (looked up via `agent_manager`).
  - `GET /api/profile/list` → returns all profiles in `neurocomputer/profiles/*.json`.
  - `POST /api/profile/switch` → body `{agent_id: string}`, sets the active agent. (Likely just delegates to existing agent-switch logic; if none exists, create the smallest possible flag in `agent_manager`.)

---

## Glob matching for `dimmedFor`

The profile JSON has `"neuros": ["nl_*", "neuro_list", "load_neuro"]`. Frontend matching:

```ts
function matchesProfile(name: string, globs: string[]): boolean {
  return globs.some(g => {
    if (g.endsWith('*')) return name.startsWith(g.slice(0, -1));
    return name === g;
  });
}
```

Apply at render time — no list filtering, just opacity / scale.

---

## Implementation Checklist

- [ ] **4.1** Add `'nl'` (and any other namespaces S1 introduces) to `NS_COLOR` in `Graph3D.tsx`. Verify the IDE renders `nl_*` neuros in cyan.
- [ ] **4.2** Add `dimmedFor?: string[] | null` prop to `Graph3D` `Props` type.
- [ ] **4.3** In Graph3D's mesh loop, look up `dimmedFor` and set `material.opacity` (and/or `scale`) per node.
- [ ] **4.4** Add a subtle pulse to matching nodes — drei `<Sparkles>` cluster around them or a simple emissive scale animated via `useFrame`.
- [ ] **4.5** Create `lib/profileApi.ts` with `getActiveProfile()`, `listProfiles()`, `switchProfile(agentId)`.
- [ ] **4.6** Create `ProfileBadge.tsx`. Layout: emoji + profile name + chevron dropdown. On select, calls `switchProfile`.
- [ ] **4.7** Mount `<ProfileBadge>` at the top of `NeuroIDEPanel.tsx`. Wire `dimmedFor` from active profile.
- [ ] **4.8** Add `GET /api/profile/active`, `GET /api/profile/list`, `POST /api/profile/switch` to `server.py`. Each is < 20 lines.
- [ ] **4.9** Test: open the IDE, switch agent to `nl_dev`, confirm cyan pulse on `nl_*` nodes and dim on others. Switch back to `neuro` agent, confirm pulse turns off.
- [ ] **4.10** Mark spec `Status: SHIPPED`.

---

## Acceptance criteria

1. **Visual diff is unmistakable.** When `neurolang_dev` is active, `nl_*` nodes are clearly highlighted (color + pulse), and non-matching nodes are clearly dimmed.
2. **Switcher works.** Clicking a profile in the badge dropdown updates the active agent and the highlight changes accordingly within ~200ms.
3. **No layout shift** when the badge appears or the profile switches.
4. **Backend endpoints** return correct shapes: `{profile: "neurolang_dev", planner: "nl_planner", replier: "nl_reply", neuros: ["nl_*", ...]}`.
5. **Other modes still work** — switching to `code_dev` highlights `code_*` neuros (the same mechanism, no special-casing for NeuroLang).

---

## Out of scope

- Drag-and-drop authoring in the 3D scene → much later.
- Editing a NeuroLang flow's source by clicking a node → defer (S1's `nl_compile` already saves the file; double-click could open the existing `NeuroEditor` pane in a future round).
- Per-namespace icons (only color + pulse this round).
- Animated transitions between profiles — accept hard switch.

---

## Open questions

- **Pulse vs. plain color?** Pulse is more visually appealing (matches user's "visually appealing 3D IDE" ask) but consumes a uniform per node. Plan: pulse on the *active set* only (small N), plain color elsewhere. If FPS drops below 30 with the pulse on, fall back to plain color and add a static glow ring instead.
- **Should the badge show the agency too?** Defer until multi-agency is being actively switched in the UI; for now, agency=`default` is implicit.

---

## Notes for the executing agent

- The IDE uses `@react-three/fiber` + `@react-three/drei`. Use `useFrame` for the pulse — do not write your own RAF loop.
- Don't introduce a new state-management library. Local React state in `NeuroIDEPanel.tsx` is sufficient.
- Test on Chrome first; only verify Firefox if FPS holds in Chrome.
- Match the existing dark theme palette in `DESIGN.md` — pulse color should be a brighter variant of the namespace color (`#22d3ee` → `#67e8f9` at peak).
