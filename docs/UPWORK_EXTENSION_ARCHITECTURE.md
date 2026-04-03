# Infinity Upwork Extension — Architecture Spec

**Status**: Draft — 2026-03-22
**Extension Version**: 1.0.0
**Manifest**: V3 (MV3)

---

## Concept

The Chrome extension is the **browser automation layer** for the Infinity Upwork Agency. It runs inside Chrome, directly manipulates the Upwork DOM, and exposes a local API server that Infinity's agents call. Think of it as a **headless browser controller** that lives in your existing Chrome browser.

```
┌──────────────────────────────────────────────────────────────────┐
│                         USER'S CHROME BROWSER                     │
│                                                                   │
│  ┌─────────────────────┐     ┌────────────────────────────────┐  │
│  │  UPWORK TAB         │     │  INFINITY EXTENSION             │  │
│  │  (upwork.com/...)   │◄───│  Service Worker (MV3)           │  │
│  │                      │     │  ↕ chrome.runtime.sendMessage   │  │
│  │  Content Script      │     │  ↕ chrome.runtime.connect      │  │
│  │  (DOM R/W)           │     │                                 │  │
│  └─────────────────────┘     │  Local API Server               │  │
│           ▲                    │  (127.0.0.1:7788)               │  │
│           │                    │  ↕ WebSocket / HTTP             │  │
│           │                    └────────────┬───────────────────┘  │
│           │                                   │                    │
└───────────│───────────────────────────────────│────────────────────┘
            │                                   │
            │              ┌────────────────────▼────────────────────┐
            │              │       INFINITY SERVER (port 7000)       │
            │              │                                         │
            │              │   Agents (job_crawler, writer, etc.)      │
            │              │   ↕ WebSocket Hub (pubsub)              │
            │              │                                         │
            │              └────────────────────┬────────────────────┘
            │                                   │
            │         ┌────────────────────────┼────────────────────┐
            │         │                         │                     │
            │    ┌────▼────┐           ┌───────▼───────┐      ┌─────▼─────┐
            │    │ Mobile  │           │    Web UI     │      │  Desktop  │
            │    │         │           │               │      │           │
            │    └─────────┘           └───────────────┘      └───────────┘
            │              ↑  Human-in-the-Loop (approve/reject)  ↑
            │              │                                          │
            └──────────────┘                                          │
               (direct use)                                           │
                                                                     │
                                                         (Neo commands)
```

---

## Architecture Components

### 1. Extension Entry Points

```
upwork_extension/
├── manifest.json           # MV3 manifest
├── background.js           # Service Worker — API server + message router
├── content.js              # Content Script — DOM manipulation on Upwork
├── popup.html/js           # Extension popup UI
├── sidebar.html/js         # Side panel (persistent dashboard)
├── icons/                  # Extension icons (16, 48, 128)
└── styles/
    └── injected.css        # UI overrides for Upwork pages
```

---

### 2. The Local API Server (in `background.js`)

The Service Worker runs an HTTP/WebSocket server on `127.0.0.1:7788` using Chrome's `chrome.socket` API or a simple HTTP handler pattern.

**Why a local server?** Infinity agents on the same machine call `http://127.0.0.1:7788/api/...` just like any REST endpoint. This means agents don't need to know about Chrome extension APIs — they just call URLs.

**Protocol**: REST over HTTP + WebSocket for streaming.

### 3. API Endpoints

The extension exposes these endpoints to Infinity:

#### Connection Management
```
POST   /api/connect              # Connect to Upwork (open new tab, login)
GET    /api/status               # Connection status: {connected, page, url}
POST   /api/disconnect           # Close Upwork tab
GET    /api/health              # {ok: true, version: "1.0.0"}
```

#### Job Operations
```
GET    /api/jobs                 # Get all visible jobs on current page
       ?limit=20&skill=react     # Optional filters
POST   /api/jobs/search          # Navigate to search, apply filters
       {query, skills, budget_min, budget_max, job_type, posted_within}
GET    /api/jobs/{id}            # Get full job details
POST   /api/jobs/{id}/open      # Click into a job detail page
```

#### Proposal Operations
```
POST   /proposals/draft          # Open proposal form for a job
       {job_id, cover_letter, rate, milestones}
GET    /proposals/draft/{id}     # Get draft state
PUT    /proposals/draft/{id}     # Update draft (cover letter, etc.)
POST   /proposals/draft/{id}/submit  # Click submit button
GET    /proposals/draft/{id}/validate # Validate form completeness
```

#### Messaging (Client Chat)
```
GET    /messages                 # Get all conversations
GET    /messages/{thread_id}     # Get messages in a thread
POST   /messages/{thread_id}/send  # Send a message
       {text, file_attachments}
GET    /messages/unread          # Get unread message count
```

#### Notifications
```
GET    /notifications            # Get all notifications
GET    /notifications/unread     # Get unread count
POST   /notifications/mark_read  # Mark notification as read
       {notification_ids}
```

#### Page State
```
GET    /page/current             # Current URL, page type, visible elements
GET    /page/screenshot          # Base64 screenshot of Upwork tab
POST   /page/click               # Click element by selector
       {selector}
POST   /page/type                # Type text into focused element
       {text}
POST   /page/navigate            # Navigate to URL
       {url}
```

#### Client Intel
```
GET    /clients/{client_id}      # Get client profile (rating, history, spent)
```

### 4. WebSocket Events (Push to Infinity)

The extension pushes real-time events to Infinity:

```
WS     ws://127.0.0.1:7788/ws

Events emitted:
  - job.list.updated     {count, jobs: [...]}
  - message.received     {thread_id, from, text, timestamp}
  - notification.new     {id, type, title, body}
  - proposal.submitted   {job_id, proposal_id, status}
  - page.changed         {url, page_type}
  - connection.status    {connected: true/false, reason}
  - error               {code, message, context}
```

---

### 5. Content Script (`content.js`)

The content script is injected into Upwork pages and does the actual DOM work.

**What it does**:
- Reads job cards, titles, budgets, skills, client info
- Fills in proposal forms, cover letters
- Reads and sends chat messages
- Clicks buttons, navigates, scrolls
- Detects page changes and notifies the background script
- Injects a floating action bar on Upwork pages

**Communication with background**:
```javascript
// Content → Background
chrome.runtime.sendMessage({
  type: "DOM_READ",
  payload: { selector: ".job-tile", data: [...] }
});

// Content ← Background (via port)
port.postMessage({
  type: "DOM_ACTION",
  action: "click",
  selector: ".submit-btn"
});
```

**DOM Selectors for Upwork** (approximate — Upwork changes these frequently):
```
// Job cards on search page
.air3-token-cache .job-tile-summary

// Job title
.job-title-text

// Budget / rate
[data-test="job-budget"] / .hourly-rate

// Job description
[data-test="job-description"] / .up-line-clamp

// Skills tags
.skills > span

// Client info
.client-info .client-name / .client-rating

// Proposal form
.cover-letter-textarea

// Message thread list
.message-thread-item

// Message content
.message-content

// Submit button
.submit-proposal-button
```

**Smart Selector Strategy**:
Since Upwork changes DOM frequently, use a layered selector approach:
1. Try `data-test` attributes first (most stable)
2. Fall back to semantic selectors (role, aria-label)
3. Fall back to class-based selectors
4. Fall back to XPath

---

### 6. Popup UI (`popup.html`)

A compact popup showing:
- Connection status (green/red dot)
- Quick stats (jobs found, proposals sent, unread messages)
- "Connect to Upwork" / "Disconnect" button
- "Open Infinity Dashboard" link
- Current page type

---

### 7. Side Panel (`sidebar.html`)

A persistent side panel with a mini Upwork dashboard:
- **Jobs Feed**: Last 10 crawled jobs with scores
- **Proposals**: Draft → Submitted → Won/Lost
- **Messages**: Recent conversations, quick reply
- **Notifications**: All alerts in one place
- **Activity Log**: What the extension has been doing
- **Settings**: Upwork login, filter preferences, rate thresholds

The side panel connects via WebSocket to the local API server and can display real-time updates.

---

## Connection Flow

### Auto-Connect on Startup
1. Chrome starts → Service Worker activates
2. Service Worker checks if Upwork tab exists
3. If found → auto-reconnect, restore session state
4. If not → show "Click to connect" in popup
5. User clicks "Connect" → opens upwork.com or uses existing tab

### Manual Connect
1. User clicks extension icon → popup shows "Not Connected"
2. User clicks "Connect to Upwork"
3. Extension checks if Upwork is open in a tab
   - If yes: focuses that tab, injects content script
   - If no: opens new tab to upwork.com
4. Content script detects login state
   - If not logged in: prompts user to log in, waits
   - If logged in: notifies background, status → "connected"
5. Background starts local server on port 7788
6. Popup updates to green, sidebar becomes active

### Connection to Infinity
1. Service Worker starts local server (`127.0.0.1:7788`)
2. Infinity server connects via WebSocket (`ws://127.0.0.1:7788/ws`)
3. Agents call REST endpoints normally
4. Extension pushes events back via WebSocket

---

## Security Considerations

1. **Local-only server**: The API only binds to `127.0.0.1`, not `0.0.0.0` — can't be accessed from other machines
2. **Upwork credentials**: Never stored in extension. User logs in via browser, extension uses active session (cookies)
3. **Rate limiting**: Agents should wait 2-5s between DOM operations to avoid triggering Upwork's anti-bot
4. **CAPTCHA handling**: If Upwork shows CAPTCHA, notify user via popup + sidebar + push to Infinity
5. **Session persistence**: Reconnect automatically if Chrome restarts (via chrome.storage.session)

---

## File Structure

```
upwork_extension/
├── manifest.json              # MV3 manifest
├── background.js              # Service Worker + local API server
├── content.js                 # Content script — DOM automation
├── content-utils.js           # Shared DOM utilities (selectors, parsers)
├── popup.html                 # Extension popup
├── popup.js
├── popup.css
├── sidebar.html               # Side panel dashboard
├── sidebar.js
├── sidebar.css
├── panel.html                 # Panel (different from sidebar on mobile)
├── panel.js
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
├── styles/
│   ├── injected.css           # Floating action bar, overlays
│   └── sidebar.css
├── lib/
│   ├── selector-engine.js    # Smart multi-layer DOM selectors
│   ├── page-detector.js       # Detects current Upwork page type
│   ├── job-parser.js          # Extracts job data from DOM
│   ├── proposal-filler.js     # Fills proposal forms
│   ├── message-reader.js     # Reads/sends messages
│   └── notification-watcher.js # Monitors for new notifications
├── api/
│   ├── router.js             # REST API routing
│   ├── websocket.js          # WebSocket server
│   └── middleware.js         # Auth, rate-limit, logging
└── storage/
    └── session.js            # chrome.storage session management
```

---

## Communication: Extension ↔ Infinity Server

### Pattern: Agents call extension as HTTP client

Infinity agents (running in `neuros/`) make HTTP calls to the extension:

```python
# In neuros/upwork_crawler/code.py
import httpx

async def run(state, *, action="list"):
    base = "http://127.0.0.1:7788"

    if action == "list":
        resp = httpx.get(f"{base}/api/jobs", timeout=30)
        jobs = resp.json()["jobs"]
        return {"jobs": jobs}

    elif action == "search":
        resp = httpx.post(
            f"{base}/api/jobs/search",
            json={"query": "React", "budget_min": 100},
            timeout=60
        )
        return {"status": "searching", "poll_url": f"{base}/api/jobs"}

    elif action == "proposal":
        resp = httpx.post(
            f"{base}/api/proposals/draft",
            json={"job_id": "123", "cover_letter": "..."},
            timeout=30
        )
        return {"proposal_id": resp.json()["id"]}
```

### Pattern: Extension pushes events to Infinity

```javascript
// background.js — WebSocket client connecting to Infinity
const infinityWs = new WebSocket("ws://127.0.0.1:7000/ws/upwork-extension");

infinityWs.on("open", () => {
  infinityWs.send(JSON.stringify({
    type: "extension.register",
    agency: "upwork",
    clientId: "chrome-extension"
  }));
});

// Forward Upwork events to Infinity agents
wsServer.on("connection", (conn) => {
  conn.on("message", (msg) => {
    // route REST/WebSocket calls normally
  });
});

// Push Upwork events → Infinity
function pushToInfinity(event) {
  if (infinityWs.readyState === WebSocket.OPEN) {
    infinityWs.send(JSON.stringify(event));
  }
}

// Example: new message from client
function onMessageReceived(threadId, msg) {
  pushToInfinity({
    type: "upwork.message.received",
    threadId,
    from: msg.from,
    text: msg.text,
    timestamp: Date.now()
  });
}
```

---

## Extension State Machine

```
                    ┌──────────────┐
                    │   IDLE       │  ← Extension installed, not connected
                    └──────┬───────┘
                           │ user clicks "Connect"
                           ▼
                    ┌──────────────┐
              ┌────►│ CONNECTING   │  ← Opening Upwork tab
              │     └──────┬───────┘
              │            │ login detected
              │            ▼
              │     ┌──────────────┐
              │     │  WAITING     │  ← User needs to log in
              │     │  LOGIN       │
              │     └──────┬───────┘
              │            │ logged in
              │            ▼
              │     ┌──────────────┐
              │     │  CONNECTED   │  ← Active, accepting API calls
              │     │  (serving)   │
              │     └──────┬───────┘
              │            │ user disconnects / tab closed
              │            ▼
              │     ┌──────────────┐
              └─────│ DISCONNECTED │  ← Clean shutdown
                    └──────────────┘
                           │
                           │ auto-reconnect (if configured)
                           ▼
                    [back to CONNECTING]
```

---

## Error Handling

| Error | User Impact | Infinity Impact |
|-------|-------------|----------------|
| Upwork CAPTCHA | Popup shows "Action blocked" | `error` event: `{code: "CAPTCHA"}` |
| Rate limited | Extension pauses 30s | `warning` event, agents back off |
| Tab closed | Popup → red, reconnect prompt | `connection.status: {connected: false}` |
| Network error | Retries 3x, then error | `error` event with retry hint |
| Job not found | "Job no longer available" | Remove from list, notify analyst |
| Proposal already submitted | Show "Already applied" | Skip in job tracking |

---

## Implementation Phases

### Phase 1: Core Extension (MVP)
- [ ] `manifest.json` + basic structure
- [ ] Service Worker with local HTTP server (`chrome.socket` or fetch-based routing)
- [ ] Content script with smart selector engine
- [ ] Connection management (connect/disconnect/status)
- [ ] Basic job listing API (`GET /api/jobs`)
- [ ] Popup UI (connection status, quick connect)

### Phase 2: Job Automation
- [ ] Job search API (`POST /api/jobs/search`)
- [ ] Job detail reader (`GET /api/jobs/{id}`)
- [ ] Page navigation (`POST /api/page/navigate`)
- [ ] Screenshot API (`GET /api/page/screenshot`)
- [ ] Job parser (extract title, budget, skills, description)

### Phase 3: Proposal Automation
- [ ] Proposal form filler (`POST /api/proposals/draft`)
- [ ] Draft state reader (`GET /api/proposals/draft/{id}`)
- [ ] Form validation (`GET /api/proposals/draft/{id}/validate`)
- [ ] Submit button trigger (`POST /api/proposals/draft/{id}/submit`)

### Phase 4: Messaging
- [ ] Conversation list reader (`GET /api/messages`)
- [ ] Message thread reader (`GET /api/messages/{thread_id}`)
- [ ] Message sender (`POST /api/messages/{thread_id}/send`)
- [ ] Unread count watcher
- [ ] Push events via WebSocket

### Phase 5: Notifications + Polish
- [ ] Notification reader (`GET /api/notifications`)
- [ ] Notification watcher (push on new)
- [ ] Side panel dashboard
- [ ] Infinity server WebSocket connection
- [ ] Auto-reconnect on Chrome startup
- [ ] CAPTCHA detection + user alert

### Phase 6: Intelligence Layer
- [ ] Connect `upwork_extension` API → Infinity neuros
- [ ] `upwork_crawler` neuro calls extension API
- [ ] `upwork_writer` neuro calls proposal API
- [ ] Real-time events from extension → Infinity pub/sub hub
- [ ] Human-in-the-loop: approve proposals from mobile/web UI
