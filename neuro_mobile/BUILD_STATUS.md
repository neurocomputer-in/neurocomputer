# neuro_mobile OS Shell — Build Status

**Spec:** `docs/superpowers/specs/2026-04-29-kotlin-os-shell-design.md`
**Branch:** dev
**Last updated:** 2026-04-29

---

## Overview

Rebuilding neuro_mobile into a native Android OS simulator matching neuro_web mobile shell.
Pure Compose, 18 apps, two-level windows-with-tabs, same persistence schema as web.

---

## Phase 1 — Data Layer + App Registry

Foundation that everything else depends on.

- [ ] `data/model/AppId.kt` — AppId enum (18 apps)
- [ ] `data/model/TabType.kt` — TabType enum (CHAT/TERMINAL/IDE/DESKTOP)
- [ ] `data/model/WindowTab.kt` — WindowTab data class
- [ ] `data/model/WindowState.kt` — WindowState data class
- [ ] `data/AppRegistry.kt` — APP_LIST, APP_MAP (mirrors appRegistry.ts)
- [ ] `data/persistence/OsStateSerializer.kt` — kotlinx.serialization JSON
- [ ] `data/persistence/IconsStateSerializer.kt`

---

## Phase 2 — OS Shell ViewModels

State layer, no UI yet.

- [ ] `ui/shell/OsState.kt` — OsState, all actions
- [ ] `ui/shell/OsViewModel.kt` — window/tab ops + DataStore persistence
- [ ] `ui/shell/IconsViewModel.kt` — icon order + dock pins + DataStore
- [ ] `ui/apps/desktop/MobileDesktopViewModel.kt` — desktop stream state (replaces scattered state)

---

## Phase 3 — OS Shell UI

The shell itself: home screen, tab strip, switcher.

- [ ] `ui/shell/NeuroOSShell.kt` — root composable, BackHandler chain
- [ ] `ui/shell/HomeScreen.kt` — 4-col icon grid + drag-reorder
- [ ] `ui/shell/MobileTabStrip.kt` — 36dp top bar, scrollable tabs, workspace chip
- [ ] `ui/shell/WindowHost.kt` — fullscreen active tab content
- [ ] `ui/shell/AppContent.kt` — when(tab.type) router
- [ ] `ui/shell/MobileDock.kt` — bottom bar (home screen only)
- [ ] `ui/shell/AppSwitcher.kt` — fullscreen card stack overlay
- [ ] `ui/shell/AppPicker.kt` — ModalBottomSheet, all 18 apps
- [ ] `ui/shell/ChevronHandle.kt` — swipe-up handle for AppSwitcher
- [ ] `ui/shell/TabOverviewSheet.kt` — ModalBottomSheet tab grid
- [ ] Wire `MainActivity.kt` → `NeuroOSShell`

---

## Phase 4 — ChatApp

Replaces ConversationScreen. All chat-type agents use this.

- [ ] `ui/apps/chat/ChatViewModel.kt` — per-cid, messages + WS + voice
- [ ] `ui/apps/chat/ChatMessageList.kt` — LazyColumn, MarkdownText
- [ ] `ui/apps/chat/ChatInputBar.kt` — TextField + send + voice + OCR
- [ ] `ui/apps/chat/ChatApp.kt` — assembles above + AgentDropdown + SideDrawer + VoicePanel

---

## Phase 5 — TerminalApp ✅

New app. OS IME, WebSocket pty, ANSI colors.

- [x] `ui/apps/terminal/AnsiParser.kt` — escape seq → AnnotatedString SpanStyle
- [x] `ui/apps/terminal/TerminalOutputView.kt` — LazyColumn of parsed lines
- [x] `ui/apps/terminal/TerminalViewModel.kt` — WS subscribe, ANSI parse, input buffer
- [x] `ui/apps/terminal/TerminalApp.kt` — assembles above + TerminalInputBar

---

## Phase 6 — DesktopApp ✅

Rebuilt from existing overlays. Clean composition.

- [x] `ui/apps/desktop/DesktopVideoView.kt` — LiveKit VideoTrack → TextureView
- [x] `ui/apps/desktop/DesktopApp.kt` — assembles all overlays + kiosk logic + wake lock

---

## Phase 7 — IDEApp ✅

2D Compose graph (lite port, no Three.js).

- [x] `ui/apps/ide/IDEViewModel.kt` — load graph, node/edge state
- [x] `ui/apps/ide/GraphCanvas.kt` — Canvas + pan/zoom + node drag + Bézier edges
- [x] `ui/apps/ide/IDEApp.kt` — GraphCanvas + NodeEditor sheet + GraphToolbar

---

## Phase 8 — Cleanup + Manifest

- [x] Delete `ui/screens/ConversationScreen.kt`
- [x] Delete `ui/components/TabBar.kt`
- [x] Delete `ui/components/WindowSelectorOverlay.kt`
- [x] Delete `ui/components/DraggableToolbar.kt`  ← kept (still used by DesktopApp)
- [x] Add `WAKE_LOCK` permission to `AndroidManifest.xml`
- [x] Update `ui/screens/MainScreen.kt` (splash only, hands off to shell)

---

## Phase 9 — QA Checklist

- [ ] Splash → HomeScreen with 18 app icons
- [ ] Drag-reorder icons, restart, order persists
- [ ] Launch chat agent → window opens with tab strip
- [ ] Open 3 different apps → 3 windows in AppSwitcher
- [ ] Swipe card to close window
- [ ] Terminal: type, Enter sends, ANSI colors visible
- [ ] Desktop: video streams, touchpad + tablet mode, keyboard, voice, toolbar
- [ ] IDE: graph loads, pan/zoom, tap node → editor sheet
- [ ] BackHandler chain: switcher → sheets → kiosk → home → minimize
- [ ] Kill app, reopen → windows/tabs/icons restored
- [ ] Voice call no regression
- [ ] OCR capture no regression

---

## Context Recovery

If conversation context is lost, resume from:
1. Read this file to see what's done/pending
2. Read `docs/superpowers/specs/2026-04-29-kotlin-os-shell-design.md` for full design
3. Check git log for last commit on neuro_mobile
4. Pick up at first unchecked item in current phase
5. All new files go under `neuro_mobile/app/src/main/java/com/neurocomputer/neuromobile/`
