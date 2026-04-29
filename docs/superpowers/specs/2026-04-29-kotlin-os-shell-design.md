# neuro_mobile — Kotlin OS Shell (OS Simulator)

**Date:** 2026-04-29
**Status:** Approved — implementation pending
**Branch:** dev
**Depends on:** `2026-04-26-mobile-ux-and-tabs-design.md`, `2026-04-27-mobile-desktop-streaming-web-design.md`

---

## Goal

Rebuild `neuro_mobile` into a native Android OS simulator matching the `neuro_web` mobile shell —
full feature parity: 18-app home screen, two-level windows-with-tabs, app switcher, dock, all apps
rebuilt as clean Compose composables. Pure native Compose (no WebView). Same persistence schema as
web so a future server-sync layer drops in without schema changes.

---

## Decisions Log

| # | Question | Decision |
|---|---|---|
| 1 | Approach | Pure native Compose port (no WebView) |
| 2 | App scope | All 18 apps (parity with web) |
| 3 | Window model | Two-level: windows hold tabs of mixed types (parity with `osSlice.ts`) |
| 4 | Rebuild vs reuse | Rebuild ConversationScreen + Desktop overlays; reuse lower-level components |
| 5 | Persistence | Local DataStore v1; JSON schema matches web localStorage for future server-sync |
| 6 | Swipe-up trigger | Visible ChevronHandle (avoids Android system gesture conflict) |
| 7 | NeuroIDE | 2D Compose graph (lite port, no Three.js) |
| Terminal keyboard | OS IME only (native IME integration; no custom keyboard needed unlike web) |

---

## Architecture

### Component Tree

```
MainActivity (single Activity, edge-to-edge)
└── NeuroOSShell
    ├── HomeScreen              ← icon grid (visible only when activeWindowId == null)
    ├── MobileTabStrip          ← top 36dp bar; tabs of active window
    ├── WindowHost              ← renders active window's active tab fullscreen
    │     └── AppContent        ← switch on tab.type
    │           ├── ChatApp           (chat + voice — all 14 chat-type agents)
    │           ├── TerminalApp       (OS IME + WebSocket pty)
    │           ├── IDEApp            (2D Compose graph)
    │           └── DesktopApp        (LiveKit video + overlays, rebuilt clean)
    ├── MobileDock              ← bottom bar, home screen only
    ├── AppSwitcher             ← card stack overlay (swipe-to-close)
    ├── AppPicker               ← ModalBottomSheet; all 18 apps
    ├── TabOverviewSheet        ← ModalBottomSheet; tabs in current window
    └── ChevronHandle           ← 16dp bar at bottom of WindowHost; drag up → AppSwitcher
```

### Navigation Model

No `NavHost`. Single composable graph driven by `OsViewModel.activeWindowId`:
- `null` → HomeScreen + MobileDock visible, WindowHost hidden
- non-null → WindowHost visible, HomeScreen hidden

`BackHandler` priority chain:
1. AppSwitcher open → close
2. Any sheet open → close
3. DesktopApp kiosk active → exit kiosk (confirm)
4. Active window exists → home (set activeWindowId=null; windows kept)
5. Home + windows exist → minimize app
6. Home + no windows → minimize app

---

## State Model

### `OsState` (in `OsViewModel`)

```kotlin
data class WindowTab(
    val id: String,       // "tab-${cid}"
    val cid: String,
    val appId: AppId,
    val title: String,
    val type: TabType,    // CHAT | TERMINAL | IDE | DESKTOP
)

data class WindowState(
    val id: String,
    val zIndex: Int,
    val minimized: Boolean,
    val tabs: List<WindowTab>,
    val activeTabId: String,
)

data class OsState(
    val windows: List<WindowState>,
    val activeWindowId: String?,
    val nextZIndex: Int,
    val closedCids: Set<String>,
    val launcherOpen: Boolean,
)
```

Key actions:
- `openWindow`, `closeWindow`, `focusWindow`
- `addTabToWindow`, `closeTab` (auto-closeWindow when last tab), `setActiveTab`, `reorderTabs`
- `restoreWindows`

Persistence: state changes → debounced 500ms → `DataStore` JSON, keys:
```
neuro_os_${ws}_${proj}       → { windows, activeWindowId }
neuro_icons_${ws}_${proj}    → { mobileOrder, dockPins }
neuro_tabs_${ws}_${proj}     → { openTabs }
neuro_selected_workspace
neuro_selected_project
```

JSON format intentionally matches web's `localStorage` shape for future `GET/PUT /os-layout` sync.

### Other ViewModels

| ViewModel | Scope | Responsibility |
|---|---|---|
| `OsViewModel` | Activity | Window/tab layout, persistence |
| `IconsViewModel` | Activity | Home grid order, dock pins |
| `ConversationViewModel` | Activity | openTabs registry, messages cache |
| `ChatViewModel` | per-tab (key=cid) | Messages, WS send/receive, voice for one cid |
| `TerminalViewModel` | per-tab (key=cid) | WS pty output, ANSI parsing, input buffer |
| `IDEViewModel` | per-tab (key=cid) | Graph nodes/edges, selection |
| `MobileDesktopViewModel` | Activity | Desktop stream mode/keyboard/toolbar state |
| `WorkspaceViewModel` | Activity | Workspace list + selection |
| `ProjectViewModel` | Activity | Project list + selection |

---

## Per-App Structure

### ChatApp (`ui/apps/chat/`)

```
ChatApp(cid, agentId)
├── ChatMessageList   — LazyColumn, reverse-scroll, MarkdownText items
├── ChatInputBar      — TextField + send + voice button + OCR attach
├── AgentDropdown     — reused from existing
├── VoicePanel        — reused VoiceRecordingPanel
└── SideDrawer        — chat history + project switcher; reused
```

`ChatViewModel(cid)` via `hiltViewModel(key = cid)` — scoped per tab.
All 10 launcher-only apps (NeuroResearch, NeuroWrite, etc.) = `ChatApp` with different `agentId`.

### TerminalApp (`ui/apps/terminal/`)

```
TerminalApp(cid)
├── TerminalOutputView  — LazyColumn of ANSI AnnotatedStrings
│     └── AnsiParser    — escape seq → SpanStyle (color, bold)
└── TerminalInputBar    — BasicTextField, OS IME, Enter → WS send
```

No custom keyboard. Compose `WindowInsets.ime` handles IME inset natively — no viewport jank.
ANSI: standard 16 colors + bold. No xterm dependency.

### DesktopApp (`ui/apps/desktop/`)

```
DesktopApp()
├── DesktopVideoView        — LiveKit VideoTrack → TextureView
├── ServerCursorOverlay     — cursor_position DataChannel → Canvas dot
├── TouchpadOverlay         — reused + extracted clean
├── TabletTouchOverlay      — reused + extracted clean
├── FullKeyboardOverlay     — reused
├── FloatingToolbar         — rebuilt from DraggableToolbar
└── VoiceTypingPanel        — reused VoiceRecordingPanel
```

`kioskActive = true` on connect → hides `MobileTabStrip` + `ChevronHandle`.
Wake lock: `PowerManager.WakeLock` acquired on connect, released on disconnect.
Rotation: `requestedOrientation` toggle in Activity (portrait ↔ landscape).

### IDEApp (`ui/apps/ide/`)

```
IDEApp(cid)
├── GraphCanvas     — Canvas composable; nodes + Bézier edges
├── NodeEditor      — ModalBottomSheet for selected node
└── GraphToolbar    — add node, zoom in/out, fit-screen
```

Gestures: `detectTransformGestures` (pan + pinch-zoom), `detectDragGestures` (node drag).
Data: `GET /neuroide/graph` → `nodes: List<Node>`, `edges: List<Edge>`.

### App Registry (`data/AppRegistry.kt`)

Kotlin equivalent of `appRegistry.ts`. Same 18 apps, same pinned flags, same tabType mapping.

---

## Native-Specific Concerns

### Existing Services (all retained)

| Service | Status | Used by |
|---|---|---|
| `LiveKitService` | Keep | DesktopApp, ChatApp voice |
| `WebSocketService` | Keep | ChatApp, TerminalApp |
| `ChatDataChannelService` | Keep | DesktopApp |
| `VoiceService` | Keep | ChatApp, DesktopApp |
| `OverlayService` | Keep | Independent system overlay feature |
| `CaptureActivity` | Keep | OCR attach in ChatApp input bar |
| `OcrService` | Keep | Used by CaptureActivity |

### Edge-to-Edge + Insets

`WindowCompat.setDecorFitsSystemWindows(false)`. Shell pads:
- `MobileTabStrip`: `WindowInsets.statusBars` top
- `ChevronHandle` / `MobileDock`: `WindowInsets.navigationBars` bottom

DesktopApp kiosk: hides status + nav bars via `WindowInsetsController`.

### Manifest Changes

Only addition: `<uses-permission android:name="android.permission.WAKE_LOCK" />`
All other permissions already present (INTERNET, FOREGROUND_SERVICE, CAMERA, RECORD_AUDIO,
SYSTEM_ALERT_WINDOW, VIBRATE).

---

## Files

### New — OS Shell
```
ui/shell/NeuroOSShell.kt
ui/shell/HomeScreen.kt
ui/shell/MobileTabStrip.kt
ui/shell/WindowHost.kt
ui/shell/AppContent.kt
ui/shell/MobileDock.kt
ui/shell/AppSwitcher.kt
ui/shell/AppPicker.kt
ui/shell/ChevronHandle.kt
ui/shell/TabOverviewSheet.kt
ui/shell/OsViewModel.kt
ui/shell/OsState.kt
ui/shell/IconsViewModel.kt
```

### New — Apps
```
ui/apps/chat/ChatApp.kt
ui/apps/chat/ChatMessageList.kt
ui/apps/chat/ChatInputBar.kt
ui/apps/chat/ChatViewModel.kt
ui/apps/terminal/TerminalApp.kt
ui/apps/terminal/TerminalOutputView.kt
ui/apps/terminal/AnsiParser.kt
ui/apps/terminal/TerminalViewModel.kt
ui/apps/desktop/DesktopApp.kt
ui/apps/desktop/DesktopVideoView.kt
ui/apps/desktop/MobileDesktopViewModel.kt
ui/apps/ide/IDEApp.kt
ui/apps/ide/GraphCanvas.kt
ui/apps/ide/IDEViewModel.kt
```

### New — Data
```
data/AppRegistry.kt
data/model/WindowState.kt
data/model/WindowTab.kt
data/model/TabType.kt
data/model/AppId.kt
data/persistence/OsStateSerializer.kt
data/persistence/IconsStateSerializer.kt
```

### Modified
```
MainActivity.kt                    — setContent { NeuroOSShell() }
ui/screens/MainScreen.kt           — SplashScreen → NeuroOSShell only
AndroidManifest.xml                — add WAKE_LOCK
app/build.gradle.kts               — confirm kotlinx-serialization version
```

### Deleted (replaced)
```
ui/screens/ConversationScreen.kt   → ChatApp + shell
ui/components/TabBar.kt            → MobileTabStrip
ui/components/WindowSelectorOverlay.kt → AppSwitcher
ui/components/DraggableToolbar.kt  → DesktopApp FloatingToolbar
```

### Retained As-Is
```
ui/components/VoiceRecordingPanel.kt
ui/components/TouchpadOverlay.kt
ui/components/TabletTouchOverlay.kt
ui/components/FullKeyboardOverlay.kt
ui/components/MarkdownText.kt
ui/components/AgentDropdown.kt
ui/components/SideDrawer.kt
ui/components/ChatHistoryDrawer.kt
ui/components/ProjectSwitcherSheet.kt
ui/components/SettingsModal.kt
data/service/*
domain/*
di/NetworkModule.kt
ui/theme/*
```

---

## Out of Scope (v1)

- Tab drag-reorder on mobile strip
- Tab tear-off / drag-between-windows
- Split-screen or floating PiP
- Server-synced layout (schema ready, endpoint not built)
- Live animated wallpaper
- Tablet landscape dual-pane
- Push notifications
- Clipboard sync in DesktopApp
- NeuroIDE 3D (2D Compose only)

---

## Success Criteria

- [ ] Splash → HomeScreen with 18 app icons; drag-reorder persists across restarts
- [ ] Tapping any chat-agent opens fullscreen chat window with tab strip; back → home
- [ ] Multiple windows stack; ChevronHandle swipe → AppSwitcher; swipe card → close; tap → focus
- [ ] Terminal: OS keyboard types, ANSI colors render, Enter sends, no viewport jank
- [ ] Desktop: video streams; touchpad/tablet/keyboard/voice/toolbar all work; kiosk hides OS chrome
- [ ] IDE: 2D graph loads, nodes pan/zoom/drag, ModalBottomSheet editor works
- [ ] All 10 launcher-only apps open as chat (differentiated by agentId)
- [ ] Window/tab/icon layout survives app kill + restart
- [ ] BackHandler chain correct at every layer
- [ ] No regressions in voice call, OCR capture, system overlay
