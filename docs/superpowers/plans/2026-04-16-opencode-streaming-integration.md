# OpenCode Streaming & Tool Usage Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring OpenCode's full multi-step, tool-usage, streaming experience into the NeuroComputer web/mobile app via the existing LiveKit DataChannel.

**Architecture:** The OpenCode delegate connects to the `/event` SSE endpoint (separate from the POST that sends messages). It parses structured events (tool calls, text deltas, step progress) and forwards them as new system_event types through the existing `brain._pub()` -> LiveKit DataChannel pipeline. The frontend adds new Redux actions and a dedicated `OpenCodeMessage` component to render tool cards, streaming text, and step progress. Mobile gets the experience for free — same DataChannel, same Redux store.

**Tech Stack:** Python (aiohttp, SSE parsing), TypeScript/React (Redux Toolkit, Lucide icons), LiveKit DataChannel (existing)

**Reference:** See `docs/opencode-sse-protocol.md` for the full SSE event protocol captured from OpenCode serve v1.4.3.

---

## File Structure

### Backend (Python)
| File | Action | Responsibility |
|------|--------|---------------|
| `neuros/opencode_delegate/code.py` | **Rewrite** | SSE-based delegate: POST message, listen on `/event`, forward structured events via stream_callback |
| `core/executor.py` | **Modify** (lines 44-49, 117-128) | Support new event types from opencode_delegate (`opencode.tool`, `opencode.step`) alongside existing `stream_chunk` |
| `core/brain.py` | **No change** | Already publishes all executor events via `_pub()` → DataChannel. No modifications needed. |
| `core/chat_handler.py` | **No change** | Already handles `system_event` topic with arbitrary metadata. No modifications needed. |

### Frontend (TypeScript/React)
| File | Action | Responsibility |
|------|--------|---------------|
| `neuro_web/types/index.ts` | **Modify** (line 29-41) | Add `OpenCodeTool` and `OpenCodeStep` interfaces, extend `Message` with `toolCalls` and `steps` fields |
| `neuro_web/store/conversationSlice.ts` | **Modify** (line 144-172) | Add `appendToolCall`, `updateToolCall`, `appendStep` reducers |
| `neuro_web/providers/LiveKitProvider.tsx` | **Modify** (line 60-112) | Handle new `opencode.tool`, `opencode.step` event types |
| `neuro_web/components/chat/ToolCallCard.tsx` | **Create** | Expandable card showing tool name, args, status, output |
| `neuro_web/components/chat/OpenCodeMessage.tsx` | **Create** | Composite component: renders interleaved tool cards + streaming text + step indicators |
| `neuro_web/components/chat/MessageBubble.tsx` | **Modify** (line 135-176) | Render `OpenCodeMessage` for messages with `toolCalls` |

---

## Task 1: Rewrite OpenCode Delegate — SSE Event Listener

**Files:**
- Rewrite: `neuros/opencode_delegate/code.py`

This is the core change. Instead of reading the POST response body, the delegate:
1. Opens a persistent SSE connection to `/event`
2. Sends the message via POST (fire-and-forget)
3. Parses SSE events and forwards them through `stream_callback` with structured payloads
4. Returns when `session.idle` is received

- [ ] **Step 1: Rewrite the delegate's `run()` function**

Replace the entire `run()` function (lines 110-255) with the SSE-based implementation. The key change: use `aiohttp` to open an SSE connection on `/event`, send the message via separate POST, then consume SSE events filtered by sessionID.

```python
async def run(
    state,
    *,
    task: str,
    session_id: Optional[str] = None,
    stream_callback: Optional[Callable] = None,
):
    import aiohttp

    stream_callback = stream_callback or state.get("__stream_cb")
    pub = state.get("__pub")  # direct access to executor's pub callback
    cid = session_id or state.get("__cid", "default")

    if not await _ensure_server():
        msg = f"OpenCode server not running. Start with: opencode serve --port {OPENCODE_SERVER_URL.split(':')[-1]}"
        return {"response": msg, "status": "error", "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

    try:
        oc_session_id = await _get_or_create_session(cid)
    except Exception as e:
        msg = f"Failed to create OpenCode session: {e}"
        return {"response": msg, "status": "error", "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

    url = f"{OPENCODE_SERVER_URL}/session/{oc_session_id}/message"
    event_url = f"{OPENCODE_SERVER_URL}/event"
    payload = {"parts": [{"type": "text", "text": task}]}

    accumulated_text = []
    step_count = 0
    done = asyncio.Event()

    async def _consume_sse(session: aiohttp.ClientSession):
        """Listen to /event SSE and forward structured events."""
        nonlocal step_count
        try:
            async with session.get(
                event_url,
                headers={"Accept": "text/event-stream"},
                timeout=aiohttp.ClientTimeout(total=600, sock_read=120),
            ) as resp:
                async for raw_line in resp.content:
                    if done.is_set():
                        break
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    etype = event.get("type", "")
                    props = event.get("properties", {})

                    # Filter by session
                    evt_sid = props.get("sessionID", "")
                    if evt_sid and evt_sid != oc_session_id:
                        continue

                    # ── Text delta (token streaming) ──
                    if etype == "message.part.delta":
                        delta = props.get("delta", "")
                        field = props.get("field", "")
                        if delta and field == "text":
                            accumulated_text.append(delta)
                            if stream_callback:
                                await stream_callback(delta)

                    # ── Part updated (tool calls, text, steps) ──
                    elif etype == "message.part.updated":
                        part = props.get("part", {})
                        ptype = part.get("type", "")

                        if ptype == "text" and part.get("text"):
                            # Final full text — replace accumulated
                            accumulated_text.clear()
                            accumulated_text.append(part["text"])

                        elif ptype == "tool":
                            tool_name = part.get("tool", "unknown")
                            state_obj = part.get("state", {})
                            status = state_obj.get("status", "pending")
                            tool_event = {
                                "tool": tool_name,
                                "call_id": part.get("callID", ""),
                                "status": status,
                                "input": state_obj.get("input", {}),
                                "output": state_obj.get("output", ""),
                                "title": state_obj.get("title", ""),
                                "time": state_obj.get("time", {}),
                            }
                            if pub:
                                await pub("opencode.tool", tool_event)
                            elif stream_callback:
                                # Fallback: format as text
                                if status == "running":
                                    await stream_callback(f"\n\n\U0001f527 **{tool_name}**\n")
                                    inp = tool_event["input"]
                                    if inp and isinstance(inp, dict):
                                        display = inp.get("filePath") or inp.get("command") or inp.get("pattern") or ""
                                        if display:
                                            await stream_callback(f"`{display}`\n")
                                elif status == "completed":
                                    out = tool_event["output"]
                                    if out:
                                        out_str = out if isinstance(out, str) else json.dumps(out)
                                        if len(out_str) > 500:
                                            out_str = out_str[:500] + "\n...(truncated)"
                                        await stream_callback(f"```\n{out_str}\n```\n\n")
                                    else:
                                        await stream_callback("\u2713\n\n")

                        elif ptype == "step-start":
                            step_count += 1
                            if pub:
                                await pub("opencode.step", {
                                    "step": step_count,
                                    "status": "running",
                                    "part_id": part.get("id", ""),
                                })

                        elif ptype == "step-finish":
                            reason = part.get("reason", "")
                            tokens = part.get("tokens", {})
                            if pub:
                                await pub("opencode.step", {
                                    "step": step_count,
                                    "status": "done",
                                    "reason": reason,
                                    "tokens": tokens,
                                    "part_id": part.get("id", ""),
                                })

                    # ── Session idle → done ──
                    elif etype == "session.idle":
                        done.set()
                        break

                    # ── Session error ──
                    elif etype == "session.error":
                        err = props.get("error", {})
                        err_msg = err.get("data", {}).get("message", str(err))
                        if stream_callback:
                            await stream_callback(f"\n\u26a0\ufe0f Error: {err_msg}\n")
                        done.set()
                        break

                    # ── Heartbeat / other → ignore ──

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[OpenCode SSE] Error: {e}")
            done.set()

    try:
        async with aiohttp.ClientSession() as session:
            # Start SSE listener
            sse_task = asyncio.create_task(_consume_sse(session))

            # Give SSE a moment to connect
            await asyncio.sleep(0.3)

            # Send message (fire-and-forget)
            async with session.post(
                url, json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status not in (200, 201):
                    body = await resp.text()
                    msg = f"OpenCode API error {resp.status}: {body[:200]}"
                    done.set()
                    sse_task.cancel()
                    return {"response": msg, "status": "error", "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}"}

            # Wait for completion (with timeout)
            try:
                await asyncio.wait_for(done.wait(), timeout=300)
            except asyncio.TimeoutError:
                pass

            sse_task.cancel()
            try:
                await sse_task
            except asyncio.CancelledError:
                pass

        response_text = "".join(accumulated_text).strip() or "(no response)"
        return {
            "response": response_text,
            "status": "success",
            "badge": "\U0001f4bb",
            "reply": f"\U0001f4bb {response_text}",
            "__streamed": True,
        }

    except asyncio.TimeoutError:
        msg = "OpenCode timed out."
        if stream_callback:
            await stream_callback(f"\n\u26a0\ufe0f {msg}\n")
        return {"response": msg, "status": "error", "badge": "\U0001f4bb", "reply": f"\U0001f4bb {msg}", "__streamed": bool(accumulated_text)}
    except Exception as e:
        msg = str(e) or type(e).__name__
        return {"response": msg, "status": "error", "badge": "\U0001f4bb", "reply": f"\U0001f4bb OpenCode Error: {msg}"}
```

- [ ] **Step 2: Test the delegate manually with curl simulation**

Run the NeuroComputer server and send a test message:
```bash
curl -s http://127.0.0.1:7001/chat/send -X POST -H "Content-Type: application/json" \
  -d '{"cid":"test-sse-001","text":"list files in current directory","agent_id":"opencode"}'
```
Wait 20s, then:
```bash
curl -s http://127.0.0.1:7001/chat/test-sse-001/messages | python3 -m json.tool
```
Expected: Messages include the response text. Check server logs for `[OpenCode SSE]` entries and `opencode.tool` / `opencode.step` events.

- [ ] **Step 3: Commit**

```bash
git add neuros/opencode_delegate/code.py
git commit -m "feat: rewrite opencode delegate to use SSE event stream for tool calls and streaming"
```

---

## Task 2: Wire New Event Types Through Executor

**Files:**
- Modify: `core/executor.py` (lines 117-128)

The executor currently only publishes `stream_chunk` and `stream_end` from neuros. The opencode delegate now also emits `opencode.tool` and `opencode.step` via the `pub` callback. We need to pass `pub` into the neuro's state so the delegate can call it directly.

- [ ] **Step 1: Pass `pub` into state before running neuro**

In `executor.py`, before the `self.factory.run()` call at line 55, inject the pub callback into state:

```python
            # ── Inject pub for neuros that need direct event publishing ──
            self.state["__pub"] = self.pub
```

Add this line at line 54, right before the `try:` block:

```python
            # ── Inject pub for neuros that need direct event publishing ──
            self.state["__pub"] = self.pub

            try:
                out = await self.factory.run(
```

- [ ] **Step 2: Verify existing events still work**

Run the server and send a message to the default `neuro` agent (not opencode). Confirm `stream_chunk`, `stream_end`, `node.start`, `node.done`, and `thinking` events still flow correctly to the frontend.

- [ ] **Step 3: Commit**

```bash
git add core/executor.py
git commit -m "feat: inject pub callback into neuro state for direct event publishing"
```

---

## Task 3: Extend Frontend Types

**Files:**
- Modify: `neuro_web/types/index.ts` (line 29-41)

- [ ] **Step 1: Add OpenCode-specific types and extend Message**

Add new interfaces after line 41 and extend `Message`:

```typescript
export interface OpenCodeToolCall {
  callId: string;
  tool: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  input: Record<string, unknown>;
  output: string;
  title: string;
  time?: { start?: number; end?: number };
}

export interface OpenCodeStep {
  step: number;
  status: 'running' | 'done';
  reason?: string;
  tokens?: { input: number; output: number; reasoning: number };
}
```

Then modify the `Message` interface (line 29-41) to add two optional fields:

```typescript
export interface Message {
  id: string;
  text: string;
  isUser: boolean;
  isVoice: boolean;
  audioUrl?: string;
  timestamp?: string;
  messageType?: 'assistant' | 'thinking' | 'step_progress' | 'error';
  thinking?: string;
  isStreaming?: boolean;
  streamId?: string;
  stepInfo?: { nodeId: string; neuroName: string; status: 'running' | 'done' | 'error' };
  // OpenCode-specific fields
  toolCalls?: OpenCodeToolCall[];
  openCodeSteps?: OpenCodeStep[];
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/types/index.ts
git commit -m "feat: add OpenCode tool call and step types to Message interface"
```

---

## Task 4: Add Redux Reducers for Tool Calls and Steps

**Files:**
- Modify: `neuro_web/store/conversationSlice.ts` (after line 172)

- [ ] **Step 1: Add `appendToolCall`, `updateToolCall`, and `appendStep` reducers**

Add these three reducers after the `finalizeStream` reducer (after line 172):

```typescript
    /** Add or update a tool call on the current streaming message */
    appendToolCall(state, action: PayloadAction<{
      cid: string; streamId: string; callId: string; tool: string;
      status: string; input: Record<string, unknown>; output: string; title: string;
      time?: { start?: number; end?: number };
    }>) {
      const { cid, streamId, callId, tool, status, input, output, title, time } = action.payload;
      if (!state.tabMessages[cid]) state.tabMessages[cid] = [];
      const msgs = state.tabMessages[cid];
      let msg = msgs.find(m => m.streamId === streamId);
      if (!msg) {
        msg = {
          id: streamId,
          text: '',
          isUser: false,
          isVoice: false,
          isStreaming: true,
          streamId,
          messageType: 'assistant' as const,
          timestamp: new Date().toISOString(),
          toolCalls: [],
          openCodeSteps: [],
        };
        msgs.push(msg);
      }
      if (!msg.toolCalls) msg.toolCalls = [];
      const existing = msg.toolCalls.find(tc => tc.callId === callId);
      if (existing) {
        existing.status = status as any;
        existing.input = input;
        existing.output = output;
        existing.title = title;
        if (time) existing.time = time;
      } else {
        msg.toolCalls.push({ callId, tool, status: status as any, input, output, title, time });
      }
    },
    /** Add or update a step on the current streaming message */
    appendStep(state, action: PayloadAction<{
      cid: string; streamId: string; step: number; status: string;
      reason?: string; tokens?: { input: number; output: number; reasoning: number };
    }>) {
      const { cid, streamId, step, status, reason, tokens } = action.payload;
      if (!state.tabMessages[cid]) state.tabMessages[cid] = [];
      const msgs = state.tabMessages[cid];
      let msg = msgs.find(m => m.streamId === streamId);
      if (!msg) {
        msg = {
          id: streamId,
          text: '',
          isUser: false,
          isVoice: false,
          isStreaming: true,
          streamId,
          messageType: 'assistant' as const,
          timestamp: new Date().toISOString(),
          toolCalls: [],
          openCodeSteps: [],
        };
        msgs.push(msg);
      }
      if (!msg.openCodeSteps) msg.openCodeSteps = [];
      const existing = msg.openCodeSteps.find(s => s.step === step);
      if (existing) {
        existing.status = status as any;
        if (reason) existing.reason = reason;
        if (tokens) existing.tokens = tokens;
      } else {
        msg.openCodeSteps.push({ step, status: status as any, reason, tokens });
      }
    },
```

- [ ] **Step 2: Export the new actions**

In the same file, find the `export const { ... } = conversationSlice.actions` line and add `appendToolCall` and `appendStep` to the destructured export.

- [ ] **Step 3: Commit**

```bash
git add neuro_web/store/conversationSlice.ts
git commit -m "feat: add Redux reducers for OpenCode tool calls and step tracking"
```

---

## Task 5: Handle New Events in LiveKitProvider

**Files:**
- Modify: `neuro_web/providers/LiveKitProvider.tsx` (lines 88-101)

- [ ] **Step 1: Add handlers for `opencode.tool` and `opencode.step` events**

After the `stream_end` handler (line 101) and before the `task.done` handler (line 104), add:

```typescript
        if (eventTopic === 'opencode.tool' && data.call_id) {
          // Find the active streamId for this conversation
          const msgs = (store.getState() as any).conversation.tabMessages[cid] || [];
          const streamingMsg = [...msgs].reverse().find((m: any) => m.isStreaming && m.streamId);
          const streamId = streamingMsg?.streamId || `opencode-${cid}-${Date.now()}`;
          dispatch(appendToolCall({
            cid,
            streamId,
            callId: data.call_id,
            tool: data.tool || 'unknown',
            status: data.status || 'pending',
            input: data.input || {},
            output: typeof data.output === 'string' ? data.output : JSON.stringify(data.output || ''),
            title: data.title || '',
            time: data.time,
          }));
          return;
        }

        if (eventTopic === 'opencode.step' && data.step != null) {
          const msgs = (store.getState() as any).conversation.tabMessages[cid] || [];
          const streamingMsg = [...msgs].reverse().find((m: any) => m.isStreaming && m.streamId);
          const streamId = streamingMsg?.streamId || `opencode-${cid}-${Date.now()}`;
          dispatch(appendStep({
            cid,
            streamId,
            step: data.step,
            status: data.status || 'running',
            reason: data.reason,
            tokens: data.tokens,
          }));
          return;
        }
```

- [ ] **Step 2: Add imports for new actions**

At the top of the file, add `appendToolCall` and `appendStep` to the import from `conversationSlice`:

```typescript
import { appendMessage, appendStreamChunk, finalizeStream, appendToolCall, appendStep } from '../store/conversationSlice';
```

Also import `store` for `getState()` access:
```typescript
import { store } from '../store';
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/providers/LiveKitProvider.tsx
git commit -m "feat: handle opencode.tool and opencode.step events in LiveKitProvider"
```

---

## Task 6: Create ToolCallCard Component

**Files:**
- Create: `neuro_web/components/chat/ToolCallCard.tsx`

- [ ] **Step 1: Create the ToolCallCard component**

```tsx
import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Terminal, FileText, Search, Edit3, Globe, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import type { OpenCodeToolCall } from '../../types';

const TOOL_ICONS: Record<string, React.ReactNode> = {
  bash: <Terminal size={13} />,
  read: <FileText size={13} />,
  write: <Edit3 size={13} />,
  edit: <Edit3 size={13} />,
  glob: <Search size={13} />,
  grep: <Search size={13} />,
  webfetch: <Globe size={13} />,
};

const TOOL_LABELS: Record<string, string> = {
  bash: 'Bash',
  read: 'Read',
  write: 'Write',
  edit: 'Edit',
  glob: 'Find Files',
  grep: 'Search',
  webfetch: 'Fetch',
  todowrite: 'Plan',
  task: 'Task',
  skill: 'Skill',
};

function getToolLabel(tool: string): string {
  return TOOL_LABELS[tool] || tool.charAt(0).toUpperCase() + tool.slice(1);
}

function getToolIcon(tool: string): React.ReactNode {
  return TOOL_ICONS[tool] || <Terminal size={13} />;
}

function getInputSummary(tool: string, input: Record<string, unknown>): string {
  if (tool === 'read' || tool === 'edit' || tool === 'write') {
    const fp = (input.filePath || input.file_path || '') as string;
    return fp.split('/').pop() || fp || '';
  }
  if (tool === 'bash') return (input.command || input.description || '') as string;
  if (tool === 'grep') return (input.pattern || '') as string;
  if (tool === 'glob') return (input.pattern || '') as string;
  if (tool === 'webfetch') {
    const url = (input.url || '') as string;
    try { return new URL(url).hostname; } catch { return url; }
  }
  return '';
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'completed') return <CheckCircle2 size={13} color="#22C55E" />;
  if (status === 'error') return <AlertCircle size={13} color="#EF4444" />;
  if (status === 'running') return <Loader2 size={13} color="#8B5CF6" style={{ animation: 'spin 1s linear infinite' }} />;
  return <Loader2 size={13} color="#666" style={{ animation: 'spin 1s linear infinite' }} />;
}

interface ToolCallCardProps {
  toolCall: OpenCodeToolCall;
}

export default function ToolCallCard({ toolCall }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const inputSummary = getInputSummary(toolCall.tool, toolCall.input);
  const duration = toolCall.time?.start && toolCall.time?.end
    ? `${((toolCall.time.end - toolCall.time.start) / 1000).toFixed(1)}s`
    : null;

  return (
    <div style={{
      border: '1px solid rgba(139,92,246,0.15)',
      borderRadius: '8px',
      marginBottom: '6px',
      background: 'rgba(20,18,30,0.5)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div
        onClick={() => setExpanded(!expanded)}
        style={{
          display: 'flex', alignItems: 'center', gap: '8px',
          padding: '8px 12px',
          cursor: 'pointer',
          fontSize: '12px',
          color: '#c4b5fd',
          userSelect: 'none',
        }}
      >
        <StatusIcon status={toolCall.status} />
        <span style={{ color: '#a78bfa', display: 'flex', alignItems: 'center', gap: '4px' }}>
          {getToolIcon(toolCall.tool)}
          {getToolLabel(toolCall.tool)}
        </span>
        {inputSummary && (
          <span style={{ color: '#888', fontFamily: 'monospace', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '300px' }}>
            {inputSummary}
          </span>
        )}
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}>
          {duration && <span style={{ color: '#666', fontSize: '10px' }}>{duration}</span>}
          {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        </span>
      </div>

      {/* Expandable body */}
      {expanded && (
        <div style={{ borderTop: '1px solid rgba(139,92,246,0.1)', padding: '8px 12px' }}>
          {Object.keys(toolCall.input).length > 0 && (
            <div style={{ marginBottom: '8px' }}>
              <div style={{ fontSize: '10px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Input</div>
              <pre style={{
                fontSize: '11px', color: '#ccc', background: 'rgba(0,0,0,0.3)',
                padding: '8px', borderRadius: '4px', overflow: 'auto', maxHeight: '150px',
                margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              }}>
                {JSON.stringify(toolCall.input, null, 2)}
              </pre>
            </div>
          )}
          {toolCall.output && (
            <div>
              <div style={{ fontSize: '10px', color: '#666', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Output</div>
              <pre style={{
                fontSize: '11px', color: '#ccc', background: 'rgba(0,0,0,0.3)',
                padding: '8px', borderRadius: '4px', overflow: 'auto', maxHeight: '200px',
                margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
              }}>
                {toolCall.output.length > 1000 ? toolCall.output.slice(0, 1000) + '\n...(truncated)' : toolCall.output}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/chat/ToolCallCard.tsx
git commit -m "feat: create ToolCallCard component for OpenCode tool call rendering"
```

---

## Task 7: Create OpenCodeMessage Component

**Files:**
- Create: `neuro_web/components/chat/OpenCodeMessage.tsx`

- [ ] **Step 1: Create the OpenCodeMessage composite component**

This component renders the full OpenCode experience: step indicators, tool cards, and streaming text — interleaved in order.

```tsx
import React from 'react';
import type { Message } from '../../types';
import ToolCallCard from './ToolCallCard';
import MarkdownRenderer from './MarkdownRenderer';

interface OpenCodeMessageProps {
  message: Message;
}

export default function OpenCodeMessage({ message }: OpenCodeMessageProps) {
  const steps = message.openCodeSteps || [];
  const tools = message.toolCalls || [];
  const currentStep = steps.length > 0 ? steps[steps.length - 1] : null;
  const hasTools = tools.length > 0;

  return (
    <div>
      {/* Step progress bar */}
      {steps.length > 1 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '4px',
          marginBottom: '8px', fontSize: '10px', color: '#888',
        }}>
          {steps.map((s) => (
            <div key={s.step} style={{
              display: 'flex', alignItems: 'center', gap: '3px',
            }}>
              <div style={{
                width: '5px', height: '5px', borderRadius: '50%',
                background: s.status === 'done' ? '#22C55E' : '#8B5CF6',
                animation: s.status === 'running' ? 'pulse 1.5s ease-in-out infinite' : 'none',
              }} />
              <span>Step {s.step}</span>
              {s.step < steps.length && <span style={{ color: '#444' }}>/</span>}
            </div>
          ))}
        </div>
      )}

      {/* Tool calls */}
      {hasTools && (
        <div style={{ marginBottom: '8px' }}>
          {tools.map((tc) => (
            <ToolCallCard key={tc.callId} toolCall={tc} />
          ))}
        </div>
      )}

      {/* Current step indicator (running) */}
      {currentStep && currentStep.status === 'running' && !message.text && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: '6px',
          padding: '6px 0', fontSize: '11px', color: '#888',
        }}>
          <div style={{
            width: '6px', height: '6px', borderRadius: '50%',
            background: '#8B5CF6',
            animation: 'pulse 1.5s ease-in-out infinite',
          }} />
          <span>Processing step {currentStep.step}...</span>
        </div>
      )}

      {/* Response text */}
      {message.text && (
        <div style={{ marginTop: hasTools ? '8px' : 0 }}>
          <MarkdownRenderer content={message.text} />
          {message.isStreaming && (
            <span style={{
              display: 'inline-block', width: '6px', height: '14px',
              background: '#8B5CF6', borderRadius: '1px',
              animation: 'blink 1s step-end infinite',
              verticalAlign: 'text-bottom', marginLeft: '2px',
            }} />
          )}
        </div>
      )}

      {/* Token usage summary (after completion) */}
      {!message.isStreaming && steps.length > 0 && steps[steps.length - 1].tokens && (
        <div style={{
          marginTop: '8px', fontSize: '10px', color: '#555',
          display: 'flex', gap: '10px',
        }}>
          {tools.length > 0 && <span>{tools.length} tool{tools.length > 1 ? 's' : ''}</span>}
          {steps.length > 1 && <span>{steps.length} steps</span>}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/chat/OpenCodeMessage.tsx
git commit -m "feat: create OpenCodeMessage composite component for multi-step rendering"
```

---

## Task 8: Integrate OpenCodeMessage into MessageBubble

**Files:**
- Modify: `neuro_web/components/chat/MessageBubble.tsx` (line 135-176)

- [ ] **Step 1: Import OpenCodeMessage**

Add at the top of the file:

```typescript
import OpenCodeMessage from './OpenCodeMessage';
```

- [ ] **Step 2: Render OpenCodeMessage for messages with tool calls**

In the agent message section (line 135 onwards), replace the content rendering inside the agent bubble. Find the `MarkdownRenderer` usage inside the agent message div and wrap it with a conditional:

Replace:
```tsx
            <MarkdownRenderer content={message.text} />
```

With:
```tsx
            {(message.toolCalls && message.toolCalls.length > 0) || (message.openCodeSteps && message.openCodeSteps.length > 0) ? (
              <OpenCodeMessage message={message} />
            ) : (
              <MarkdownRenderer content={message.text} />
            )}
```

This is a minimal change — if a message has `toolCalls` or `openCodeSteps`, render `OpenCodeMessage`; otherwise, use the existing `MarkdownRenderer`.

- [ ] **Step 3: Verify existing non-OpenCode messages still render correctly**

Open the app, send a message to the default `neuro` agent. Confirm messages render normally with markdown, code blocks, and streaming cursor.

- [ ] **Step 4: Commit**

```bash
git add neuro_web/components/chat/MessageBubble.tsx
git commit -m "feat: integrate OpenCodeMessage renderer into MessageBubble"
```

---

## Task 9: End-to-End Integration Test

**Files:**
- No new files. Manual verification.

- [ ] **Step 1: Ensure OpenCode serve is running**

```bash
pgrep -af "opencode serve" || opencode serve --port 14096 &
curl -s http://127.0.0.1:14096/global/health
```
Expected: `{"healthy":true,"version":"1.4.3"}`

- [ ] **Step 2: Restart NeuroComputer backend to pick up delegate changes**

```bash
# Kill and restart the Python backend
pkill -f "python.*server.py" && sleep 2
cd /home/ubuntu/neurocomputer-dev && python server.py &
```

- [ ] **Step 3: Build and serve frontend**

```bash
cd /home/ubuntu/neurocomputer-dev/neuro_web && npm run build
```

- [ ] **Step 4: Test via the web UI**

Open the NeuroComputer desktop app or web UI. Switch to the OpenCode agent. Send a message that triggers tool usage:

> "Read the file server.py and tell me what the /health endpoint returns"

Expected behavior:
1. Step indicator appears: "Processing step 1..."
2. Tool card appears: `Read` with `server.py` — status cycles pending → running → completed
3. Step 2 begins, streaming text appears token-by-token
4. Final response with markdown formatting
5. Token usage summary at bottom

- [ ] **Step 5: Test with default neuro agent (regression)**

Switch to the default `Neuro` agent and send a regular message. Confirm it renders normally — streaming text, no tool cards, no step indicators.

- [ ] **Step 6: Commit all remaining changes if any**

```bash
git add -A
git commit -m "feat: complete OpenCode streaming + tool usage integration"
```
