# neuro_web — Mobile UX + Chrome-style Tabs

**Date:** 2026-04-26
**Status:** Approved
**Depends on:** `2026-04-24-neuroweb-pwa-android-design.md`

## Goal

Two related changes to neuro_web:

1. **Phone-native UI/UX on mobile** — hybrid model: fullscreen one-app-at-a-time by default, multiple windows accessed via app-switcher card view. Maximum screen real estate; no permanent dock or menu bar eating pixels.
2. **Chrome-style tabs-per-window** — each window holds N tabs of mixed app types (Chat / Terminal / NeuroIDE / agents). Works on both desktop and mobile; same data model, two presentations.

## Non-goals (v1)

- Tab tear-off (drag tab out of window into a new window). Tabs reorder within a strip; new windows spawn via "+ new window" only.
- Split-screen / floating PiP on mobile. Card-stacked fullscreen windows only.
- Cross-window drag-and-drop on desktop.
- Offline support for tab state (tabs persist via localStorage, same as today).

## Decisions (from brainstorm)

| # | Question | Decision |
|---|---|---|
| 1 | Mobile paradigm | **Hybrid** — fullscreen default, app-switcher cards for multi-window |
| 2 | Tab model | **Tabs-per-window**, mixed app types |
| 3 | Mobile chrome | **Single top bar only** (~36px); no permanent dock; bottom-edge swipe for switcher |
| 4 | Tab switching | **Inline scrollable strip + pill → card overview** when overflowing |
| 5 | Multi-window mobile | **App-switcher cards only** — no split, no PiP |
| 6 | Desktop tab integration | **Tabs-in-title-bar**, no tear-off in v1 |
| 7 | "+" button | **Mini app picker** (dropdown desktop / bottom sheet mobile) |

## Architecture

### Data model — `osSlice.ts`

`WindowState` is restructured so each window owns a list of tabs.

```ts
interface WindowTab {
  id: string;          // window-local tab id (uuid)
  cid: string;         // conversation/terminal/ide id (existing)
  appId: AppId;        // for icon + routing
  title: string;
  type: 'chat' | 'terminal' | 'neuroide';
}

interface WindowState {
  id: string;
  x: number; y: number; width: number; height: number;
  zIndex: number;
  minimized: boolean;
  maximized: boolean;
  prevBounds?: ...;
  tabs: WindowTab[];          // NEW
  activeTabId: string;        // NEW
  // REMOVED: appId, cid, title  (now per-tab)
}
```

`conversationSlice.openTabs` remains the global registry of open `cid`s (used for restore, persistence, dedup). Windows reference cids; closing the last tab in a window closes the window; closing a tab that exists in another window does not affect that other window's reference (cids may be open in only one window at a time — enforced by the reducers).

### New reducers

- `addTabToWindow({windowId, tab, makeActive?})`
- `closeTab({windowId, tabId})` — if last tab, also `closeWindow`
- `setActiveTab({windowId, tabId})`
- `reorderTabs({windowId, fromIndex, toIndex})`
- `moveTabToNewWindow({windowId, tabId, x, y})` — used by "new window" action

### Persistence

`localStorage` key extended:

```
neuro_os_${workspaceId}_${projectId} = {
  windows: [ {id, x, y, w, h, tabs:[{cid, appId, title, type}], activeTabId} ],
  activeWindowId
}
```

Existing `neuro_tabs_${ws}_${project}` continues to drive the cid registry; on hydrate we reconcile windows ↔ openTabs.

### Auto-window logic in `page.tsx`

Replace existing "one window per orphan tab" effect with: if a tab is opened (e.g., via Dock) and no window is active, spawn one window containing that tab; otherwise add the tab to the active window.

## Components

### Shared

| Component | Path | Purpose |
|---|---|---|
| `WindowTabStrip` | `components/os/WindowTabStrip.tsx` | Horizontal scrollable tab list — used by both desktop window title bar and mobile top bar. Props: `tabs`, `activeTabId`, callbacks. |
| `AppPicker` | `components/os/AppPicker.tsx` | "+" target — dropdown on desktop, bottom-sheet on mobile (responsive via `useIsMobile`). |
| `AppSwitcher` | `components/os/AppSwitcher.tsx` | Card grid overlay showing all windows. Mobile: full-screen, swipe-to-close. Desktop: centered overlay. |
| `TabOverviewPopover` | `components/os/TabOverviewPopover.tsx` | Triggered by overflow pill — grid of tab thumbnails for current window. |

### Desktop changes

- `Window.tsx` — title bar replaced by `<WindowTabStrip />`. Window controls (min/max/close) sit to the right of strip. Tab right-click → context menu (close, close others, move to new window).
- `Dock.tsx` — right-click reveals "Show all windows" → opens `AppSwitcher`.

### Mobile changes

- `page.tsx` — when `isMobile`, renders a different shell:
  ```
  <MobileTabStrip />        // top, ~36px, fixed
  <ActiveWindowContent />   // fills screen
  // no MenuBar, no Dock, no Sidebar
  ```
- `MobileTabStrip` — wraps `WindowTabStrip` + adds workspace/project menu icon (left) and pill+"+" buttons (right).
- Bottom-edge swipe-up gesture on `<ActiveWindowContent>` opens `AppSwitcher`. Implemented with `@use-gesture/react` `useDrag` with vertical threshold; framer-motion handles the card transition.
- App-switcher cards: vertical scroll, each card = scaled-down preview of its window with app icon + active tab title + tab count badge. Swipe card horizontally → close window. Tap → focus.

## Library choices

| Need | Library | Reason |
|---|---|---|
| Animation, transitions, card stack | `framer-motion` | already in deps; layout animations + AnimatePresence are first-class |
| Mobile bottom sheets (AppPicker, long-press menus) | `vaul` (^0.9) | gold-standard mobile sheet (Emil Kowalski / shadcn). Native-feeling drag-to-dismiss, snap points, focus management. |
| Gestures (swipe-up switcher, swipe-to-close cards, long-press tabs) | `@use-gesture/react` (^10) | composes cleanly with framer-motion; handles drag/pinch/long-press in one API. |
| Tab reorder (desktop drag-within-strip) | `@dnd-kit/core` + `@dnd-kit/sortable` (^6) | accessible, modern, no flushSync issues; React 18-safe. (`react-beautiful-dnd` is unmaintained.) |

All four are small, tree-shakable, and SSR-safe with `'use client'`.

## Behaviour details

### Desktop tab strip
- Height: 32px. Active tab background = window bg; inactive = subtle dim.
- Drag to reorder via `@dnd-kit`. Long press / drag-out reserved for v2 (tear-off).
- Overflow: when total tab width > strip width, tabs shrink to min 80px then horizontal scroll appears with overflow pill.
- Keyboard: `Cmd/Ctrl+T` new tab in active window, `Cmd/Ctrl+W` close active tab, `Cmd/Ctrl+Tab` cycle tabs, `Cmd/Ctrl+1..9` jump to tab N.

### Mobile tab strip
- Height: 36px (touch target). Tabs min 96px, scrollable.
- Long-press tab → `vaul` sheet with: Close, Close others, Move to new window.
- Pill shows count when tabs > 3. Tap pill → `TabOverviewPopover` (full-screen sheet on mobile).
- "+" → `AppPicker` bottom sheet.

### App-switcher (cards)
- Trigger: mobile swipe-up from bottom 16px edge; desktop Cmd/Ctrl+` or dock right-click.
- Layout: vertical scroll of cards on mobile (one per row, ~80% width), 3-col grid on desktop.
- Card content (v1): app icon (active tab), title, tab count, gradient header keyed by `appId`. No live preview in v1 (see Out of scope).
- Actions: tap = focus + dismiss; horizontal swipe (mobile) / × button (desktop) = close; "+ New window" tile at end.

### Persistence + restore
- On mount, hydrate `osSlice` from `neuro_os_${ws}_${proj}`.
- Reconcile: drop tabs whose cid is no longer in `openTabs`; if a cid in `openTabs` is unattached to any window, attach it to the most-recent window (or spawn a new one if none).

## Files changed

| File | Change |
|---|---|
| `neuro_web/package.json` | add `vaul`, `@use-gesture/react`, `@dnd-kit/core`, `@dnd-kit/sortable` |
| `neuro_web/store/osSlice.ts` | restructure WindowState + new reducers |
| `neuro_web/components/os/Window.tsx` | replace title bar with WindowTabStrip |
| `neuro_web/components/os/WindowManager.tsx` | render active tab content (was: cid prop) |
| `neuro_web/components/os/WindowTabStrip.tsx` | NEW |
| `neuro_web/components/os/MobileTabStrip.tsx` | NEW |
| `neuro_web/components/os/AppPicker.tsx` | NEW |
| `neuro_web/components/os/AppSwitcher.tsx` | NEW |
| `neuro_web/components/os/TabOverviewPopover.tsx` | NEW |
| `neuro_web/app/page.tsx` | mobile-shell branch + reworked auto-window effect |
| `neuro_web/hooks/useKeyboardShortcuts.ts` | NEW — Cmd+T/W/Tab/1-9 |

## Out of scope

- Tab tear-off / drag-between-windows
- Split-screen, PiP, floating overlays
- Tab-group colors / pinning
- Tab thumbnails as live previews (use static gradient for v1)
- Migration UI for users with old `neuro_tabs_*` shape — auto-reconcile is silent

## Success criteria

- On phone, opening neuro_web shows fullscreen active tab with only a 36px top bar; swiping up from the bottom edge reveals an app-switcher card grid.
- On desktop, each window shows a Chrome-style tab strip with multiple tabs of mixed types; tabs reorder via drag; "+" opens an app picker.
- Tab/window state survives reload on both platforms.
- No regressions in chat / terminal / NeuroIDE functionality inside a tab.
