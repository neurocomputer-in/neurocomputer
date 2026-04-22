# Window Selector Feature Implementation

## Overview

The Window Selector allows users to view and switch between open windows on the Ubuntu desktop from the mobile app, when in remote screen mode. It provides a grouped view of windows by application with optional screenshots.

## Architecture

```
┌─────────────────────────┐                    ┌─────────────────────────────┐
│   Ubuntu Desktop        │                    │   Android Phone             │
│                         │                    │                             │
│  server.py              │◄───HTTPS──────────►│  WindowSelectorOverlay.kt  │
│  + Window API endpoints │    (Cloudflare)    │  (Composable UI)            │
│                         │                    │                             │
│  Uses:                  │                    │  Uses:                      │
│  - xdotool (windows)    │                    │  - OkHttpClient             │
│  - xprop (window info)  │                    │  - Bitmap decoding          │
│  - xwd (screenshots)    │                    │  - Compose UI               │
└─────────────────────────┘                    └─────────────────────────────┘
```

## Server-Side Implementation (server.py)

### Dependencies
- `xdotool` - Window enumeration and control
- `xprop` - Window property extraction
- `ImageMagick (convert)` - XWD to PNG conversion

### API Endpoints

#### GET /windows
Lists all open windows grouped by application class.

**Response:**
```json
{
  "windows": [
    {
      "id": "65011722",
      "title": "ubuntu@ubuntu: ~/neurocomputer",
      "class": "gnome-terminal-server",
      "display_class": "Gnome-terminal"
    }
  ],
  "apps": [
    {
      "class": "gnome-terminal-server",
      "display_class": "Gnome-terminal",
      "windows": [...]
    }
  ]
}
```

#### GET /windows/{window_id}/screenshot
Captures a screenshot of the specified window.

**Response:**
```json
{
  "screenshot": "<base64-encoded PNG>",
  "window_id": "65011722"
}
```

**Implementation:**
1. Uses `xwd -id <window_id>` to capture the window
2. Converts XWD format to PNG using ImageMagick `convert`
3. Returns base64-encoded PNG image

#### POST /windows/{window_id}/focus
Activates/focuses the specified window.

**Response:**
```json
{
  "success": true,
  "window_id": "65011722"
}
```

**Implementation:**
- Uses `xdotool windowactivate --sync <window_id>`

## Mobile Implementation

### WindowSelectorOverlay.kt

A Jetpack Compose component that displays:

1. **App Groups** - Collapsible list of applications
   - Each app shows: icon, name, window count
   - Tap to expand and see all windows

2. **Window Items** - Individual windows under each app
   - Window title
   - Screenshot (loaded on demand when selected)
   - Tap to select, then tap again to confirm focus

3. **State Management**
   - `apps` - List of WindowApp objects from API
   - `expandedApps` - Set of currently expanded app classes
   - `screenshots` - Map of window_id to Bitmap (lazy loaded)
   - `selectedApp` - Currently selected app/window for confirmation

### API Integration

```kotlin
// List windows
GET /windows → parse JSON to List<WindowApp>

// Load screenshot (lazy)
GET /windows/{id}/screenshot → decode base64 → Bitmap

// Focus window
POST /windows/{id}/focus
```

### UI States
- **Loading** - Circular progress indicator
- **Error** - Error message display
- **Content** - Scrollable list of app groups

## Integration Points

### ConversationScreen.kt

1. Added state:
```kotlin
private val _isWindowSelectorMode = MutableStateFlow(false)
val isWindowSelectorMode: StateFlow<Boolean> = _isWindowSelectorMode.asStateFlow()
```

2. Added toggle function:
```kotlin
fun toggleWindowSelectorMode() {
    _isWindowSelectorMode.value = !_isWindowSelectorMode.value
}
```

3. Added toolbar button (fullscreen mode):
```kotlin
IconButton(
    onClick = { viewModel.toggleWindowSelectorMode() },
    modifier = Modifier.background(
        if (isWindowSelectorMode) Color(0xFF50FA7B.toInt()).copy(alpha = 0.2f)
        else Color.Transparent,
        shape = CircleShape
    )
) {
    Icon(Icons.Default.Window, ...)
}
```

4. Added overlay rendering:
```kotlin
if (isWindowSelectorMode) {
    WindowSelectorOverlay(
        baseUrl = viewModel.backendUrl,
        onExit = { viewModel.toggleWindowSelectorMode() },
        onWindowSelected = { windowId -> ... }
    )
}
```

## Window Information Flow

1. **Enumeration**: `xdotool search --onlyvisible ''` returns all window IDs
2. **Details**: For each ID, query `xdotool getwindowname` and `xprop -id WM_CLASS`
3. **Grouping**: Group windows by `WM_CLASS` (application identifier)
4. **Screenshot**: `xwd -id <id>` → `convert` → base64 → HTTP response

## Privacy Considerations

- Window enumeration requires X11 (works on X11, limited on Wayland)
- Screenshots are only captured when explicitly requested
- All communication goes through the existing Cloudflare tunnel

## Future Enhancements

1. **AI OCR Mode** - Extract text from screenshots using ML Kit
2. **Clickable Windows** - Click on screenshot regions to send mouse events
3. **Window Thumbnails** - Show all window thumbnails in a grid
4. **Keyboard Shortcuts** - Send keyboard events to focused window
