# 3D Spatial View — Design Spec (Phase A prototype)

**Date:** 2026-04-19
**Status:** Approved for prototype. Follow-up phases (office metaphor, agent avatars, multi-session-per-agent, walk-mode, spatial audio) are out of scope here.

## Goal

Give the user a 3D spatial alternative to the linear tab bar. Open sessions float as cards in a navigable 3D scene. Clicking a card flies the camera in and opens **focus mode**, which is today's chat/terminal/voice UI overlaid on a dimmed 3D scene. Exiting focus flies back out. A minimap shows the scene from overhead. A setting toggles the whole app between `Classic tabs` and `3D spatial`.

Zero backend changes. Everything is rendered from the existing `conversations` Redux state.

## Decisions

1. **Renderer:** `@react-three/fiber` + `@react-three/drei` over `three@0.183` (already installed). No raw three.js in component code — R3F components only.
2. **Scope of scene (MVP):** open tabs only — not chat history, not the whole project graph. If a session isn't in `openTabs`, it's not in the scene.
3. **Clustered by project:** session nodes for the same `project_id` cluster together on a 2D plane in 3D space. Projects separated by distance.
4. **Focus mode UI is unchanged:** the existing `ChatPanel + ChatInput`, `TerminalPanel`, and voice call panel continue to render exactly as today, just overlaid on the 3D scene instead of filling the pane.
5. **Mode toggle in Settings:** `ui.interfaceMode = 'classic' | 'spatial'`, localStorage-backed. Switch is instant.
6. **No imported 3D assets:** cards are procedural RoundedBox + Text. Minimal particle ambient. Keep download + render cost tiny.

## Architecture

```
app/page.tsx
  └─ interfaceMode selector
      ├─ 'classic'  → existing ChatPanel / TerminalPanel / TabBar chain
      └─ 'spatial'  → SpatialRoot
                       ├─ <Canvas> (r3f)
                       │    ├─ Lighting (ambient + key)
                       │    ├─ ParticlesBackdrop (optional, cheap)
                       │    ├─ GroundGrid (procedural)
                       │    ├─ SessionNodes (one per openTab, clustered by project_id)
                       │    ├─ CameraController (orbit + programmatic fly-to)
                       │    └─ Selector (raycasts on click)
                       ├─ Minimap (absolute top-right, small <Canvas>)
                       ├─ FocusOverlay (conditionally rendered when a node is focused)
                       │    └─ reuses ChatPanel/TerminalPanel as today
                       └─ HUD (workspace/project chips, minimap toggle, keyboard hints)
```

## Data model (frontend only)

`uiSlice` gains:
```ts
interfaceMode: 'classic' | 'spatial'   // default: 'classic'
focusedCid: string | null              // cid currently in focus mode within spatial
```

Actions:
```ts
setInterfaceMode(mode)
setFocusedCid(cid | null)
```

Nothing new on the backend. Nothing persists beyond localStorage (via existing ui-slice persistence pattern).

## Scene composition

**Project clusters:** for each unique `project_id` among `openTabs`, a cluster center at `(clusterIndex * 6, 0, 0)`. Clusters laid out in a row; if more than 6 projects, wrap to the next `z` row.

**Session nodes within a cluster:** sessions sharing a project sit on a small `XZ` grid around the cluster center, spaced by 1.8 units.

**Node visual:** RoundedBox 1.6 × 0.9 × 0.12 unit card, facing camera via `<Billboard>`. Front face shows:
- Icon glyph (chat = speech bubble, terminal = `>_`, dashboard = bar chart)
- Title (ellipsised to 18 chars)
- Activity dot — green (running), grey (idle), red (error)

**Color by type:**
- chat → `#3b82f6`
- terminal → `#22c55e`
- dashboard → `#a855f7` (reserved, even without dashboard feature yet)

**Hover:** scale 1.05 + emissive glow `#7170ff`.
**Selected:** persistent ring at base.

## Interactivity

| Input | Action |
|---|---|
| Left-drag | orbit |
| Right-drag | pan |
| Scroll | zoom |
| Click node | select |
| Double-click node or `Enter` on selected | enter focus mode |
| `Esc` | exit focus mode (if focused), else deselect |
| `F` | frame selected node |
| `M` | toggle minimap |
| `Tab` / `Shift+Tab` | cycle selection through nodes |
| WASD | fly camera (translate in camera-local XZ) |
| Q / E | move camera up / down |

Camera fly-in on focus: tween over ~450ms to a pose `0.9` units in front of the node, looking at it. Scene dims to 0.35 opacity during focus via a post-processing lerp on the R3F scene wrapper. Focus overlay fades in over the same period.

Exit reverses: camera interpolates back to the pre-focus pose, scene brightens, overlay fades out.

## Minimap

- Canvas-in-canvas: separate `<Canvas>` top-right, `180 × 120 px`, orthographic camera looking straight down at `(y = 40)`.
- Renders the same nodes list (instanced small squares), no hover/glow effects, no text.
- Camera's XZ position shown as a yellow triangle pointing the yaw direction.
- Click inside minimap → translates main camera to `(clickX, currentY, clickZ)` preserving height.

## Settings integration

`Settings → Appearance → Interface mode` (new row above `Tab bar position`):

```tsx
<Row label="Interface mode" description="Switch between classic tabs and a 3D spatial view of your sessions.">
  <SegmentedControl
    value={interfaceMode}
    options={[
      { value: 'classic', label: 'Classic' },
      { value: 'spatial', label: '3D' },
    ]}
    onChange={v => dispatch(setInterfaceMode(v))}
  />
</Row>
```

## Failure modes

| Scenario | Handling |
|---|---|
| WebGL unsupported / context lost | Fall back to classic; one-line toast: "3D unavailable — reverted to classic". |
| Zero open tabs | Scene renders a single "empty" billboard: "Open a chat or terminal to see it here." |
| Many open tabs (> 60) | Instanced render for nodes; labels rendered as sprites with `maxLabels = 40` (beyond that, labels suppressed until zoomed in). |
| R3F throws while mounting | `<ErrorBoundary>` around `SpatialRoot`, fallback = classic view + console log. |
| User switches to spatial during a voice call | Voice call panel overlay stays functional; it just renders on top of the 3D scene (fixed-position as today). |

## Testing plan

No automated tests in the prototype. Manual checklist:

- [ ] Toggle Settings → 3D → chat pane area is replaced by a 3D scene with one card per open tab.
- [ ] Drag rotates camera; scroll zooms; WASD flies.
- [ ] Click card selects; double-click flies in and chat panel appears.
- [ ] While focused: type a message, send, receive reply — all works.
- [ ] Esc exits; camera returns; scene brightens.
- [ ] Open a terminal tab → green card appears; focus into it → xterm works.
- [ ] Minimap in corner shows dots + yaw triangle; click teleports camera.
- [ ] Toggle back to Classic → tab bar restored, state intact.
- [ ] Close a tab via context menu → node disappears immediately.
- [ ] Voice call while focused → voice panel overlays correctly; audio works.

## Out of scope (follow-ups)

- 3D office / workspace room metaphor.
- Agent avatars with animations.
- Agent-status visualization beyond activity dot.
- Walk-mode (first-person) + gravity / collisions.
- Spatial audio for voice calls.
- Multi-session-per-agent data model change on backend.
- Drag-to-reposition, saved layouts.
- Collaboration (multiple users in the same scene).
- Mobile / touch-first tuning (MVP optimised for laptop).
