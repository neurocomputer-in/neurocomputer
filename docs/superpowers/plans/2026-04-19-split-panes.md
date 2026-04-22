# Split Panes — Implementation Plan (up to 3 horizontal panes)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** VS Code-style horizontal split of the main content area into up to 3 independent panes. Each pane owns its own active session (chat / terminal / dashboard). A picker in each pane lets the user swap the displayed session. Focused pane receives new-tab actions. Works with the existing single-pane flow unchanged when only one pane is open.

**Architecture:**
- `ui.panes: [{id, activeCid|null}]`, `ui.focusedPaneId` in Redux.
- React `PaneContext` providing a per-pane `activeCid` override. Components (`ChatPanel`, `ChatInput`, `TerminalPanel`) read context first, fall back to Redux.
- `page.tsx` renders a flex row of `PaneFrame` components; each frame wraps the existing content renderer in a `PaneContext.Provider`.
- Split / close buttons in the TopBar. Pane picker is a tiny dropdown at the top of each `PaneFrame`.

**Tech Stack:** existing React 18 + Redux Toolkit + Next 14. No new deps.

---

## Task 1: Redux — panes + focusedPaneId in uiSlice

**Files:**
- Modify: `neuro_web/store/uiSlice.ts`

- [ ] **Step 1: Add state + actions**

Add to `UIState`:
```ts
export interface PaneState { id: string; activeCid: string | null }
panes: PaneState[];   // default: [{id: 'p0', activeCid: null}]
focusedPaneId: string; // default: 'p0'
```

Initial:
```ts
panes: [{ id: 'p0', activeCid: null }],
focusedPaneId: 'p0',
```

Actions:
```ts
splitPane(state)                                 // append new pane if <3
closePane(state, {id})                           // remove; collapse focus to remaining first
setPaneActiveCid(state, {id, cid})
setFocusedPaneId(state, {id})
```

Helper: new-pane id is `p${Date.now().toString(36)}`.
On `closePane`, if `focusedPaneId` was the closed pane, fall back to the first remaining.
Guard: never below 1 pane, never above 3.

- [ ] **Step 2: Export actions**

```ts
export const { ..., splitPane, closePane, setPaneActiveCid, setFocusedPaneId } = uiSlice.actions;
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/store/uiSlice.ts
git commit -m "feat(split): panes + focusedPaneId in uiSlice"
```

---

## Task 2: PaneContext + hook

**Files:**
- Create: `neuro_web/components/panes/PaneContext.tsx`

- [ ] **Step 1: Create context**

```tsx
'use client';
import { createContext, useContext } from 'react';

export interface PaneBinding {
  paneId: string;
  activeCid: string | null;
}

export const PaneContext = createContext<PaneBinding | null>(null);

/** Returns the pane-scoped active cid if inside a pane, else null
 *  (so callers can fall back to the Redux activeTabCid). */
export function usePaneCid(): string | null {
  const binding = useContext(PaneContext);
  return binding?.activeCid ?? null;
}

/** Returns the pane id of the current pane frame, or null if outside. */
export function usePaneId(): string | null {
  return useContext(PaneContext)?.paneId ?? null;
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/panes
git commit -m "feat(split): PaneContext + usePaneCid / usePaneId hooks"
```

---

## Task 3: PaneFrame renderer

**Files:**
- Create: `neuro_web/components/panes/PaneFrame.tsx`

- [ ] **Step 1: Scaffold**

```tsx
'use client';
import { useMemo } from 'react';
import dynamic from 'next/dynamic';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setFocusedPaneId, closePane } from '@/store/uiSlice';
import { PaneContext, PaneBinding } from './PaneContext';
import ChatPanel from '@/components/chat/ChatPanel';
import ChatInput from '@/components/chat/ChatInput';
import VoiceCallPanel from '@/components/chat/VoiceCallPanel';
import PanePickerBar from './PanePickerBar';
import { X } from 'lucide-react';

const TerminalPanel = dynamic(() => import('@/components/terminal/TerminalPanel'), { ssr: false });

interface Props { paneId: string; activeCid: string | null }

export default function PaneFrame({ paneId, activeCid }: Props) {
  const dispatch = useAppDispatch();
  const focusedPaneId = useAppSelector(s => s.ui.focusedPaneId);
  const paneCount = useAppSelector(s => s.ui.panes.length);
  const focused = focusedPaneId === paneId;
  const binding: PaneBinding = useMemo(() => ({ paneId, activeCid }), [paneId, activeCid]);
  const tab = useAppSelector(s => s.conversations.openTabs.find(t => t.cid === activeCid) || null);
  const kind = tab?.type === 'terminal' ? 'terminal' : 'chat';

  return (
    <PaneContext.Provider value={binding}>
      <div
        onMouseDown={() => { if (!focused) dispatch(setFocusedPaneId(paneId)); }}
        style={{
          flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column',
          position: 'relative',
          borderLeft: paneCount > 1 ? '1px solid rgba(255,255,255,0.05)' : undefined,
          boxShadow: focused && paneCount > 1 ? 'inset 0 0 0 1px rgba(94,106,210,0.35)' : undefined,
          transition: 'box-shadow 0.15s',
        }}
      >
        {paneCount > 1 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '4px 8px',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            background: 'rgba(15,16,17,0.6)', flexShrink: 0,
          }}>
            <PanePickerBar paneId={paneId} activeCid={activeCid} />
            <div style={{ flex: 1 }} />
            <button
              onClick={(e) => { e.stopPropagation(); dispatch(closePane(paneId)); }}
              title="Close pane"
              style={{
                width: 20, height: 20, borderRadius: 4, border: 'none',
                background: 'transparent', color: '#62666d', cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            ><X size={12} /></button>
          </div>
        )}
        {activeCid
          ? (kind === 'terminal'
              ? <TerminalPanel />
              : <><ChatPanel /><VoiceCallPanel /><ChatInput /></>)
          : <EmptyPane paneId={paneId} />
        }
      </div>
    </PaneContext.Provider>
  );
}

function EmptyPane({ paneId }: { paneId: string }) {
  return (
    <div style={{
      flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
      color: '#62666d', fontSize: 13, padding: 24, textAlign: 'center',
    }}>
      <div>
        <div style={{ marginBottom: 8 }}>Empty pane</div>
        <div style={{ fontSize: 11, color: '#50565d' }}>
          Use the picker above to drop a session into this pane.
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/panes/PaneFrame.tsx
git commit -m "feat(split): PaneFrame renderer with focus ring + close button"
```

---

## Task 4: Consumers read PaneContext first

**Files:**
- Modify: `neuro_web/components/chat/ChatPanel.tsx`
- Modify: `neuro_web/components/chat/ChatInput.tsx`
- Modify: `neuro_web/components/terminal/TerminalPanel.tsx`

- [ ] **Step 1: Add context fallback**

For each file, replace the `const activeTabCid = useAppSelector(s => s.conversations.activeTabCid)` line with:

```ts
import { usePaneCid } from '@/components/panes/PaneContext';
// ...
const paneCid = usePaneCid();
const globalCid = useAppSelector(s => s.conversations.activeTabCid);
const activeCid = paneCid ?? globalCid;
```

Use `activeCid` everywhere it would have been `activeTabCid`. Leave other Redux selectors that read from `openTabs` / `tabMessages` as-is — they look up by cid, which is now the pane's cid.

- [ ] **Step 2: useVoiceCall + useChat similar fallback**

In `hooks/useChat.ts` and `hooks/useVoiceCall.ts`, do the same swap so they post to the pane's cid, not the global one.

- [ ] **Step 3: Smoke test single-pane**

Run the app — with only 1 pane, everything should behave unchanged. The context injects the same cid the global selector would produce (because the single pane's activeCid is kept in sync with `activeTabCid` by Task 6).

- [ ] **Step 4: Commit**

```bash
git add neuro_web/components/chat neuro_web/components/terminal neuro_web/hooks
git commit -m "feat(split): components read PaneContext cid first, Redux fallback"
```

---

## Task 5: PanePickerBar

**Files:**
- Create: `neuro_web/components/panes/PanePickerBar.tsx`

- [ ] **Step 1: Implement**

```tsx
'use client';
import { useEffect, useRef, useState } from 'react';
import { ChevronDown, MessageSquare, Terminal as TerminalIcon } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setPaneActiveCid } from '@/store/uiSlice';

interface Props { paneId: string; activeCid: string | null }

export default function PanePickerBar({ paneId, activeCid }: Props) {
  const dispatch = useAppDispatch();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);
  const tabs = useAppSelector(s => s.conversations.openTabs);
  const active = tabs.find(t => t.cid === activeCid);

  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const icon = (type?: string) =>
    type === 'terminal' ? <TerminalIcon size={11} /> : <MessageSquare size={11} />;

  const pick = (cid: string) => {
    dispatch(setPaneActiveCid({ id: paneId, cid }));
    setOpen(false);
  };

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v); }}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '3px 8px', borderRadius: 5,
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.08)',
          color: '#d0d6e0', fontSize: 11, cursor: 'pointer',
          fontFamily: 'inherit',
        }}
        title="Pick a session for this pane"
      >
        {icon(active?.type)}
        <span style={{ maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {active ? active.title : 'Pick a session'}
        </span>
        <ChevronDown size={10} />
      </button>
      {open && (
        <div className="glass-dropdown" style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          minWidth: 260, borderRadius: 8, zIndex: 50,
          boxShadow: '0 8px 30px rgba(0,0,0,0.5)', overflow: 'hidden',
        }}>
          {tabs.length === 0 && (
            <div style={{ padding: '10px 12px', color: '#62666d', fontSize: 12 }}>
              No sessions open. Start one first.
            </div>
          )}
          {tabs.map(t => {
            const isActive = t.cid === activeCid;
            return (
              <button
                key={t.cid}
                onClick={(e) => { e.stopPropagation(); pick(t.cid); }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  width: '100%', padding: '8px 10px',
                  background: isActive ? 'rgba(94,106,210,0.12)' : 'transparent',
                  border: 'none', color: isActive ? '#f7f8f8' : '#d0d6e0',
                  fontSize: 12, cursor: 'pointer', textAlign: 'left',
                  fontFamily: 'inherit',
                }}
                onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
              >
                {icon(t.type)}
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {t.title}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/panes/PanePickerBar.tsx
git commit -m "feat(split): pane picker dropdown (VS Code-style quick pick)"
```

---

## Task 6: page.tsx renders PaneFrames + keeps single-pane default in sync

**Files:**
- Modify: `neuro_web/app/page.tsx`

- [ ] **Step 1: Replace content area with pane row**

Replace the single-content block:

```tsx
{interfaceMode === 'spatial'
  ? <SpatialErrorBoundary ...>...</SpatialErrorBoundary>
  : (activeTabKind === 'terminal'
      ? <TerminalPanel />
      : (<><ChatPanel /><VoiceCallPanel /><ChatInput /></>))}
```

with:

```tsx
{interfaceMode === 'spatial' && panes.length === 1
  ? <SpatialErrorBoundary ...>...</SpatialErrorBoundary>
  : (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'row' }}>
      {panes.map(p => (
        <PaneFrame key={p.id} paneId={p.id} activeCid={p.activeCid} />
      ))}
    </div>
  )}
```

Read `panes` from Redux:
```ts
const panes = useAppSelector(s => s.ui.panes);
```

- [ ] **Step 2: Keep first pane synced with activeTabCid on single-pane**

When `panes.length === 1`, mirror `activeTabCid` into `panes[0].activeCid` on change:

```tsx
useEffect(() => {
  if (panes.length === 1 && panes[0].activeCid !== activeTabCid) {
    dispatch(setPaneActiveCid({ id: panes[0].id, cid: activeTabCid }));
  }
}, [activeTabCid, panes, dispatch]);
```

Import `setPaneActiveCid`. This is a compatibility bridge — existing TabBar logic continues dispatching `setActiveTab`; the pane state just shadows it in single-pane mode.

- [ ] **Step 3: Remove or disable 3D mode when multi-pane**

In the spatial branch, the guard `panes.length === 1` makes the 3D view auto-collapse to classic when split. Add a one-line toast (optional, `console.info` is fine for v1): "3D view disabled while split; close other panes to re-enable."

- [ ] **Step 4: Smoke test single-pane**

Nothing should visibly change until you hit Split. Verify chat + terminal + new-tab flows still work.

- [ ] **Step 5: Commit**

```bash
git add neuro_web/app/page.tsx
git commit -m "feat(split): render PaneFrames row; mirror activeTabCid→pane0 in single-pane mode"
```

---

## Task 7: TopBar split / focus-pane controls

**Files:**
- Modify: `neuro_web/components/layout/TopBar.tsx`

- [ ] **Step 1: Add split button**

Between the interface-mode toggle and the theme selector, add:

```tsx
const panes = useAppSelector(s => s.ui.panes);
const canSplit = panes.length < 3;

<button
  onClick={() => canSplit && dispatch(splitPane())}
  disabled={!canSplit}
  title={canSplit ? 'Split pane (up to 3)' : 'Max 3 panes'}
  style={{
    display: 'inline-flex', alignItems: 'center', gap: 4,
    padding: '5px 10px', borderRadius: 6, border: '1px solid rgba(255,255,255,0.08)',
    background: 'rgba(255,255,255,0.02)',
    color: canSplit ? '#d0d6e0' : '#50565d',
    fontSize: 12, cursor: canSplit ? 'pointer' : 'default',
    ...noDragStyle,
  }}
>
  <Columns size={12} /> Split
</button>
```

Import `Columns` from `lucide-react` and `splitPane` from `@/store/uiSlice`.

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/layout/TopBar.tsx
git commit -m "feat(split): Split button in TopBar"
```

---

## Task 8: New-tab actions target focused pane

**Files:**
- Modify: `neuro_web/app/page.tsx`
- Modify: `neuro_web/components/terminal/TerminalButton.tsx`

- [ ] **Step 1: After creating a new conversation, also set the pane's active cid**

In `handleNewTab` (chat):
```ts
if (createConversation.fulfilled.match(result)) {
  const conv = result.payload;
  dispatch(openTab({ ... }));                     // existing
  dispatch(setPaneActiveCid({ id: focusedPaneId, cid: conv.id })); // NEW
  await connectToConversation(conv.id);
}
```

Read `focusedPaneId` via Redux.

- [ ] **Step 2: Same for TerminalButton.createNew**

```ts
dispatch(openTab({ ... }));
dispatch(setPaneActiveCid({ id: focusedPaneId, cid: t.cid }));
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web
git commit -m "feat(split): new chat / new terminal targets focused pane"
```

---

## Task 9: Keyboard shortcuts

**Files:**
- Create: `neuro_web/components/panes/usePaneShortcuts.ts`
- Modify: `neuro_web/app/page.tsx`

- [ ] **Step 1: Hook**

```ts
'use client';
import { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { splitPane, setFocusedPaneId, closePane } from '@/store/uiSlice';

export function usePaneShortcuts() {
  const dispatch = useAppDispatch();
  const panes = useAppSelector(s => s.ui.panes);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && /^(input|textarea|select)$/i.test(target.tagName)) return;
      if (target?.isContentEditable) return;

      if (e.ctrlKey && !e.shiftKey && e.key === '\\') {
        e.preventDefault();
        if (panes.length < 3) dispatch(splitPane());
      }
      if (e.ctrlKey && ['1', '2', '3'].includes(e.key)) {
        e.preventDefault();
        const idx = parseInt(e.key, 10) - 1;
        if (panes[idx]) dispatch(setFocusedPaneId(panes[idx].id));
      }
      if (e.ctrlKey && e.key === 'w' && panes.length > 1) {
        e.preventDefault();
        // close the focused pane
        const focusedId = (document as any).__neuroFocusedPaneId;
        if (focusedId) dispatch(closePane(focusedId));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [panes, dispatch]);
}
```

(We'll read `focusedPaneId` directly via Redux instead of the document hack — update the hook to pull it from `useAppSelector`.)

- [ ] **Step 2: Mount in `page.tsx`**

```tsx
usePaneShortcuts();
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web
git commit -m "feat(split): Ctrl+\\ split, Ctrl+1/2/3 focus, Ctrl+W close"
```

---

## Task 10: Manual smoke + cleanup

- [ ] Split → 2 panes, each with its own active session via picker. Typing in one pane doesn't affect the other.
- [ ] New chat from TopBar lands in the focused pane.
- [ ] Close pane → remaining pane fills, its session continues.
- [ ] 3D mode disabled while split; re-enabling closes down to 1 pane.
- [ ] Live voice call only active on focused pane's input area (per-pane VoiceCallPanel).
- [ ] Cmd+W / Ctrl+W closes the focused pane.
- [ ] Commit anything you polished.

---

## Critical files

| Action | Path |
|---|---|
| Create | `neuro_web/components/panes/PaneContext.tsx` |
| Create | `neuro_web/components/panes/PaneFrame.tsx` |
| Create | `neuro_web/components/panes/PanePickerBar.tsx` |
| Create | `neuro_web/components/panes/usePaneShortcuts.ts` |
| Modify | `neuro_web/store/uiSlice.ts` |
| Modify | `neuro_web/app/page.tsx` |
| Modify | `neuro_web/components/layout/TopBar.tsx` |
| Modify | `neuro_web/components/chat/ChatPanel.tsx` |
| Modify | `neuro_web/components/chat/ChatInput.tsx` |
| Modify | `neuro_web/components/terminal/TerminalPanel.tsx` |
| Modify | `neuro_web/components/terminal/TerminalButton.tsx` |
| Modify | `neuro_web/hooks/useChat.ts` |
| Modify | `neuro_web/hooks/useVoiceCall.ts` |

No backend changes.

## Out of scope (v1.1 / later)

- Vertical splits
- Drag-and-drop tabs between panes
- Panes in 3D mode
- Per-pane tab bars (currently only the picker surface)
- Splits on mobile (hidden or auto-collapse below 900px viewport)
