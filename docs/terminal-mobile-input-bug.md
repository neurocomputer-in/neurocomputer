# Terminal Mobile Input — "First few submits work, then stops" Bug

## Status
**Root cause identified — fix applied; awaiting on-device verification.**

Server-restart clears the stuck state without any code change, which
means the bad state lives on the server side and is being driven by the
client's reconnect loop leaking orphan WebSocket connections.

### Fix (applied 2026-04-28)

**Client — `neuro_web/hooks/useTerminalWs.ts`:**

1. `connect()` now closes the prior `wsRef.current` before opening a new
   socket — and detaches its event handlers first so its `onclose`
   doesn't fire a stale-state reconnect.
2. The new socket's `onclose` handler bails out early (`return`) if
   `wsRef.current !== ws`, so an orphaned socket's close event can no
   longer null out the reference to the *current* healthy socket and
   schedule yet another `connect()`.
3. Removed the `send()`-driven force-reconnect added in the previous
   round. Letting `send()` initiate `connect()` on a dropped frame was
   stacking extra connections on top of the natural reconnect path —
   the cure was worse than the disease.

**Server — `neurocomputer/server.py`:**

- Track `_active_bridges: dict[cid, PtyBridge]`. When a new WS arrives
  for a cid, evict any prior bridge by calling `prev._cleanup()` (kills
  its `tmux attach` PTY) before registering the new one. Belt-and-
  suspenders against any future client-side bug, and a clean recovery
  path if a stale bridge somehow gets installed.

## Smoking gun (added 2026-04-28)

User restarted the backend (`python3 server.py`) **without changing any
code** and the terminal started working again. Backend logs from before
the restart show this pattern repeating:

```
WebSocket /terminal/ws/c4a34525efcb48e1b55238a75bcd7d02 [accepted]
connection open
WebSocket /terminal/ws/c4a34525efcb48e1b55238a75bcd7d02 [accepted]
connection open                ← second open WITHOUT a close of the first
…
connection closed
connection closed
connection closed
connection closed
connection closed              ← 5 closes back-to-back
```

So the same conversation id was driving 5+ parallel WS connections at
peak, each spawning its own `tmux attach` against the same tmux
session. That isn't supposed to break tmux (multi-attach is fine), but
it does mean we accumulate `PtyBridge` instances on the server, and
client input is racing against whichever bridge happens to be alive
while old bridges' SIGHUP cleanups stomp on the session.

### How the orphans pile up (client side)

`hooks/useTerminalWs.ts`:

```ts
const connect = useCallback(() => {
  if (!cid) return;
  const ws = new WebSocket(terminalWsUrl(cid));
  ws.binaryType = 'arraybuffer';
  wsRef.current = ws;          // ← previous wsRef just gets overwritten
  ...
});
```

Whenever `connect()` is called and `wsRef.current` already holds an
older socket whose `onclose` hasn't fired yet (very common on flaky
mobile networks — TCP can stay half-open for tens of seconds), the new
socket replaces it in `wsRef` but the old one is **not closed**. The
server still sees it as connected and keeps its PtyBridge alive.

Then, when the leaked socket eventually does close (TCP timeout, server
shutdown, etc.), its `onclose` handler runs:

```ts
ws.onclose = () => {
  wsRef.current = null;
  if (!shouldReconnectRef.current) return;
  …
  reconnectTimerRef.current = setTimeout(() => { connect(); }, backoff);
};
```

It nulls `wsRef.current` (even though that ref already pointed to a
*different, healthy* socket — bug #2), and schedules another
`connect()`. The healthy socket is now orphaned too. This avalanches.

To make matters worse, my "fix" from the previous round added a
force-reconnect from `send()` whenever `wsRef.current` looked closed —
which means *every dropped send* during a hiccup queues yet another
`connect()` on top of the existing avalanche.

## Symptom (verbatim from user)

> on phone, terminal app opened, whenever I was trying to type to the terminal
> text input area it used to type into the in app text box, once submitted from
> that inputbox went to terminal but not from next time, it just vanishes

After a follow-up round of fixes:

> Sill I can see the in app text box with voice message, call and other
> options, and types message goes into in app text box then submits to
> terminal, that's okay but it works only for first few times then stops
> working and doesn't submits to the terminal

And after restarting the backend:

> actually it started working again when I restarted the backend server

## Symptom (verbatim from user)

> on phone, terminal app opened, whenever I was trying to type to the terminal
> text input area it used to type into the in app text box, once submitted from
> that inputbox went to terminal but not from next time, it just vanishes

After a follow-up round of fixes:

> Sill I can see the in app text box with voice message, call and other
> options, and types message goes into in app text box then submits to
> terminal, that's okay but it works only for first few times then stops
> working and doesn't submits to the terminal

So the sequence on the user's device is:

1. Open the terminal tab on a phone (Android).
2. Tap a key on the on-screen custom keyboard → the typed character appears
   in the input box (✓ typing path works).
3. Tap `↵` (or the send button) → text travels to the PTY and the shell
   echoes / runs it (✓ first few submits work).
4. After **2–5 successful submits** (non-deterministic), the next submit
   *visually clears the input box* but **nothing reaches the terminal**.
   From that point on, no further submits succeed in that session.

## Where the input lives

Files involved:

- `neuro_web/components/terminal/TerminalPanel.tsx` — owns the xterm
  instance and the WebSocket, renders `TerminalInputBar` below the canvas.
- `neuro_web/components/terminal/TerminalInputBar.tsx` — the input box
  itself, plus mic / voice-call / send buttons. On mobile renders a
  non-focusable `<div>` (not a `<textarea>`) for the typed value.
- `neuro_web/components/keyboard/CustomKeyboardSheet.tsx` &
  `CustomKeyboard.tsx` — the on-screen keyboard. Always open on mobile
  (configurable via the keyboard-toggle button, persisted in
  `localStorage[neuro.terminal.customKeyboardOpen]`).
- `neuro_web/hooks/useTerminalWs.ts` — owns the WS, exposes
  `send / sendControl / resize / close`.

## Mobile data flow (current)

```
CustomKeyboard button onPointerDown
  → handleKey(key) inside CustomKeyboard
    → onKey(combo)              // = handleCustomKey from TerminalInputBar
      → setValue(v => v + ch)   // React state update; div re-renders
    → onClearModifiers()

CustomKeyboard "Return" button onPointerDown
  → handleKey('Return')
    → onKey('Return')
      → handleCustomKey('Return')
        → submit()                       // TerminalInputBar
          → const t = value.trim()
          → if (!t) return                 // ← only short-circuit
          → const ok = onSubmit(t)         // TerminalPanel.sendLine
                       → send(buf)         // useTerminalWs.send
                            ↓
                            ws.send(buf)   if ws.readyState === OPEN
                            return false   if ws not OPEN  ← suspected path
          → if (ok === false) flash red, KEEP value
          → else setValue('')
```

The mobile input is **not a `<textarea>`** anymore. It is a
`pointerEvents:none` `<div>` so the OS keyboard cannot be summoned by
focus. Custom keyboard is the only input source.

## Fixes applied so far (all still in place)

1. **Removed the `input.focus()` call** from `TerminalPanel.onOverlayUp`
   for mobile — tapping the xterm area no longer focuses the textarea, so
   it can no longer accidentally pop the Android native keyboard.
2. **Replaced the mobile textarea with a div** (`TerminalInputBar`) so
   nothing in the DOM is focusable; Android cannot show its native
   keyboard regardless of how the user taps.
3. **Persisted keyboard show/hide preference** to
   `localStorage[neuro.terminal.customKeyboardOpen]` and added a toggle
   button in the input bar.
4. **`useTerminalWs.send` now returns `boolean`** — `true` only when the
   WebSocket was OPEN and the call did not throw. Logs
   `[terminal-ws] send dropped — wsState=<n>` on every drop.
5. **Force-reconnect on dropped send** — instead of waiting for the
   exponential backoff timer to fire, `send` now calls `connect()`
   immediately on a CLOSED socket, with the backoff reset to 1s.
6. **`TerminalInputBar.submit` consults the returned `ok`** — when the
   parent reports `false` (= WS dropped the message), `value` is **kept**
   instead of cleared, the input box flashes red for 1.5s, and the send
   button stays armed for retry.

After (6), a dropped send should be visually obvious (red flash + value
preserved) and the WebSocket should reconnect on its own. Despite this,
the user reports the bug *still* reproduces.

## Why the current theory may be wrong

The "WebSocket silently disconnects" theory predicts that after the bug
hits:

- The DevTools console should contain a `[terminal-ws] send dropped` line.
- The input bar should flash red on the failing submit (per fix #6).
- The status label in `TerminalPanel`'s title bar should switch from
  `connected` to `reconnecting…` or `error`.
- The typed text should *remain* in the input box (per fix #6) instead of
  vanishing.

The user's latest report ("stops working and doesn't submit to the
terminal") doesn't explicitly describe the red flash or the value being
preserved — it sounds like the symptom is the same vanishing behavior as
before. **That suggests the WS path is actually fine and the real bug is
upstream of `send()`** — i.e., `submit()` either isn't being called, or
is being called with `t=''`, **or** `onSubmit` *is* returning truthy
(send appeared to succeed) but the data didn't reach the PTY for a
different reason.

## Hypotheses still on the table

1. **`submit()` not firing.** The `Return` key's `onPointerDown` is
   getting swallowed (e.g. an unrelated overlay starts intercepting
   pointer events after a few re-renders).
2. **`value` is empty when `submit()` runs.** Some code path is calling
   `setValue('')` between when the user typed and when they tapped `↵`.
   Candidates: the `useEffect` we added for cross-tab `localStorage`
   sync, `onClearModifiers()` re-renders, framer-motion's
   `AnimatePresence` doing something unexpected when the keyboard's
   layout shifts, or React batching between submit and the next event.
3. **Server-side**: PTY reads the bytes but the shell doesn't echo (e.g.
   PTY in raw/cooked-mode mismatch after some control sequence).
4. **Backend `_handle_pty_input` quietly drops bytes** under some
   condition (need to check `neurocomputer/server.py` or wherever the
   terminal WS handler lives).
5. **Mobile browser is throttling or coalescing pointer events** after
   N taps. (Less likely — would expect to see typing also fail.)
6. **A second listener is also calling `submit()`** which races and
   clears `value` before our handler reads it. (Unlikely — only the
   custom keyboard's Return key and the desktop textarea's `onKeyDown`
   call submit, and the textarea isn't rendered on mobile.)

## Next debugging steps

The single most useful piece of evidence right now is **what the
DevTools console shows when the bug hits on the user's actual phone**.
Specifically:

- Is `[terminal-ws] send dropped — wsState=<n>` printed? If yes →
  hypothesis is the WS theory and we need to investigate why
  reconnect isn't kicking in. If no → the call is succeeding from the
  client's perspective and the problem is upstream of `send()` or on the
  server.
- Add temporary instrumentation:
  ```ts
  const submit = (text?: string) => {
    const t = (text ?? value).trim();
    console.log('[term-input] submit called, value=', JSON.stringify(value), 'arg=', text);
    if (!t) return;
    ...
  };
  ```
  This will reveal whether `submit` runs at all on the failing taps and
  what `value` looks like at that moment.
- Mirror the same trace on the server: log every byte received on the
  terminal WS along with a session id. If the bytes never arrive but the
  client thinks send succeeded, the issue is between
  `ws.send(...)` and the server's read loop (NAT, proxy, intermediary
  closing the upgrade silently).
- Check whether the bug correlates with screen-off / tab-backgrounded.
  Mobile browsers can suspend WS without firing `onclose` immediately.

## Files touched in attempted fixes

- `neuro_web/components/terminal/TerminalInputBar.tsx`
- `neuro_web/components/terminal/TerminalPanel.tsx`
- `neuro_web/hooks/useTerminalWs.ts`
- `neuro_web/app/globals.css` (caret keyframe)

## Reproduction instructions (Android)

1. `cd /home/ubuntu/neurocomputer && python3 server.py` (port 7000).
2. `cd /home/ubuntu/neurocomputer/neuro_web && npm run dev`.
3. On the Android phone, open the web app via the LAN URL, log in, open
   the **Terminal** app.
4. Run a few quick commands (`ls`, `pwd`, `echo hi`). One of the first
   handful submits will silently stop reaching the PTY.
5. Open `chrome://inspect` from a desktop Chrome and attach to the phone
   to capture the console output.
