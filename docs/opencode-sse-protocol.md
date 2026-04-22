# OpenCode SSE Protocol Reference

Captured from `opencode serve` v1.4.6 on 2026-04-17 (envelope re-captured live; earlier v1.4.3 capture was documented as flat, see envelope note below).
Use this to implement the same streaming experience in NeuroComputer web.

**Envelope change from v1.4.3 → v1.4.6:** events now wrap the type+properties
in a `payload` object, and include outer `directory` and `project` fields:

```json
{
  "directory": "/path/to/project",
  "project": "<project-hash>",
  "payload": {"type": "<event-type>", "properties": {...}}
}
```

The examples below show only the `payload` contents for readability. When
implementing a parser, read `event.payload.type` and `event.payload.properties`
— the flat top-level `type`/`properties` documented for v1.4.3 do NOT exist
in v1.4.6. Some `sync`-wrapped events use `payload.aggregateID` instead of
`properties.sessionID` to identify the owning session.

## Architecture

1. **Send message**: `POST /session/{sid}/message` — fire-and-forget, returns echo of input
2. **Listen for events**: `GET /event` — persistent SSE connection, receives ALL events for ALL sessions

The frontend keeps one EventSource open on `/event` and dispatches events by `sessionID`.

## SSE Event Types (in order of a typical request)

### 1. `server.connected`
Sent when SSE connection opens.
```json
{"type":"server.connected","properties":{}}
```

### 2. `session.created` / `session.updated`
Session lifecycle.
```json
{"type":"session.created","properties":{"sessionID":"ses_xxx","info":{...}}}
{"type":"session.updated","properties":{"sessionID":"ses_xxx","info":{"title":"...","summary":{"additions":0,"deletions":0,"files":0}}}}
```

### 3. `session.status`
Indicates busy/idle.
```json
{"type":"session.status","properties":{"sessionID":"ses_xxx","status":{"type":"busy"}}}
```

### 4. `message.updated`
Full message metadata. Sent when a message is created, updated, or completed.
- **No `time.completed`** → message still in progress
- **Has `time.completed`** → message done
- **`finish: "tool-calls"`** → message ended to run tools, next step coming
- **`finish: "stop"`** → final response
```json
{
  "type":"message.updated",
  "properties":{
    "sessionID":"ses_xxx",
    "info":{
      "id":"msg_xxx",
      "parentID":"msg_xxx",
      "role":"assistant",
      "mode":"build",
      "agent":"build",
      "path":{"cwd":"/path","root":"/path"},
      "cost":0,
      "tokens":{"input":4096,"output":17,"reasoning":0,"cache":{"read":0,"write":0}},
      "modelID":"gemma4:e4b",
      "providerID":"ollama",
      "time":{"created":1776277554858,"completed":1776277588960},
      "finish":"stop"
    }
  }
}
```

### 5. `message.part.updated` — step-start
Marks the beginning of a processing step.
```json
{
  "type":"message.part.updated",
  "properties":{
    "sessionID":"ses_xxx",
    "part":{
      "id":"prt_xxx",
      "messageID":"msg_xxx",
      "sessionID":"ses_xxx",
      "snapshot":"git_sha",
      "type":"step-start"
    }
  }
}
```

### 6. `message.part.updated` — tool (pending → running → completed)
Tool call lifecycle. Three updates for each tool call:

**Pending:**
```json
{
  "type":"message.part.updated",
  "properties":{
    "part":{
      "id":"prt_xxx",
      "type":"tool",
      "tool":"read",
      "callID":"call_xxx",
      "state":{"status":"pending","input":{},"raw":""}
    }
  }
}
```

**Running (with args):**
```json
{
  "type":"message.part.updated",
  "properties":{
    "part":{
      "type":"tool",
      "tool":"read",
      "callID":"call_xxx",
      "state":{
        "status":"running",
        "input":{"filePath":"/path/to/file"},
        "raw":"",
        "time":{"start":1776277588356}
      }
    }
  }
}
```

**Completed (with result):**
```json
{
  "type":"message.part.updated",
  "properties":{
    "part":{
      "type":"tool",
      "tool":"read",
      "callID":"call_xxx",
      "state":{
        "status":"completed",
        "input":{"filePath":"/path/to/file"},
        "output":"file contents here...",
        "metadata":{"truncated":false},
        "title":"Read package.json",
        "time":{"start":1776277588356,"end":1776277588366}
      }
    }
  }
}
```

Available tools: `bash`, `read`, `glob`, `grep`, `edit`, `write`, `task`, `webfetch`, `todowrite`, `skill`, `question`

### 7. `message.part.updated` — step-finish
Marks end of a step. Contains token usage for that step.
```json
{
  "type":"message.part.updated",
  "properties":{
    "part":{
      "id":"prt_xxx",
      "type":"step-finish",
      "reason":"tool-calls",
      "tokens":{"total":4113,"input":4096,"output":17,"reasoning":0,"cache":{"write":0,"read":0}},
      "cost":0
    }
  }
}
```
- `reason: "tool-calls"` → step ended to run tools, more steps coming
- `reason: "stop"` → final step

### 8. `message.part.updated` — text (initial, empty)
Created before streaming begins.
```json
{
  "type":"message.part.updated",
  "properties":{
    "part":{
      "id":"prt_xxx",
      "type":"text",
      "text":"",
      "time":{"start":1776277591992}
    }
  }
}
```

### 9. `message.part.delta` — streaming text tokens
Individual tokens streamed in real-time. Append `delta` to the part's text.
```json
{
  "type":"message.part.delta",
  "properties":{
    "sessionID":"ses_xxx",
    "messageID":"msg_xxx",
    "partID":"prt_xxx",
    "field":"text",
    "delta":"Hello"
  }
}
```

### 10. `message.part.updated` — text (final)
Full text after streaming completes.
```json
{
  "type":"message.part.updated",
  "properties":{
    "part":{
      "id":"prt_xxx",
      "type":"text",
      "text":"Full response text here...",
      "time":{"start":1776277591992,"end":1776277593442}
    }
  }
}
```

### 11. `session.diff`
File changes made during the session.
```json
{"type":"session.diff","properties":{"sessionID":"ses_xxx","diff":[]}}
```

### 12. Session done (v1.4.6 has no `session.idle` event-type)

Completion is signalled in two overlapping ways:

1. **`message.updated` with `info.finish` ∈ {stop, length, error, cancelled}**
   on an assistant message matching the user message's id as `parentID`,
   with `info.time.completed` set. This is the authoritative per-turn
   completion signal.
2. **`session.status` with `status.type == "idle"`** fires when the session
   transitions back to idle after a turn. Rely on (1) to terminate a turn;
   use (2) only as a pre-POST idle gate for the next turn.

Intermediate `message.updated` with `finish == "tool-calls"` indicates the
assistant stopped to run tools; the same turn continues with a new
assistant message carrying the same `parentID`. Do NOT treat `tool-calls`
as terminal.

### 13. `server.heartbeat`
Keep-alive, sent every ~10s.
```json
{"type":"server.heartbeat","properties":{}}
```

### 14. `session.error`
Error during processing.
```json
{
  "type":"session.error",
  "properties":{
    "error":{
      "name":"ProviderAuthError",
      "data":{"message":"model not found","providerID":"ollama"}
    }
  }
}
```

## Multi-Step Flow Example

```
User sends message
  → session.status: busy
  → message.updated (assistant created, no time.completed)
  
  STEP 1: Tool usage
    → message.part.updated: step-start
    → message.part.updated: tool (pending)
    → message.part.updated: tool (running, with args)
    → message.part.updated: tool (completed, with output)
    → message.part.updated: step-finish (reason: "tool-calls")
    → message.updated (finish: "tool-calls", time.completed set)
  
  NEW MESSAGE (same parentID, continues the turn)
    → message.updated (new assistant msg, no time.completed)
  
  STEP 2: Text response  
    → message.part.updated: step-start
    → message.part.updated: text (empty)
    → message.part.delta: "Hello" (token by token)
    → message.part.delta: " world"
    → ...
    → message.part.updated: text (final full text)
    → message.part.updated: step-finish (reason: "stop")
    → message.updated (finish: "stop", time.completed set)
  
  → session.status: idle (or session.idle)
```

## Key Design Points for NeuroComputer Integration

1. **Separate SSE connection** from message sending — don't try to stream from POST response
2. **Track parts by ID** — parts get updated multiple times (pending → running → completed)
3. **Track messages by ID** — multiple messages per turn (tool-calls creates new message)
4. **Append deltas** — `message.part.delta` gives token-by-token text, accumulate by partID
5. **Multi-step**: a turn can have multiple messages. `finish: "tool-calls"` means more coming
6. **Show tool cards**: tool parts have `tool` name, `state.input` (args), `state.output` (result)
7. **Session filtering**: the `/global/event` SSE emits events for ALL sessions, filter by `payload.properties.sessionID` (or `payload.aggregateID` on `sync` events).

## Surfacing provider errors

When a model call fails (auth error, rate limit, 402 credits exhausted,
invalid model id, etc.), opencode emits:

```json
{
  "type": "message.updated",
  "properties": {
    "sessionID": "ses_xxx",
    "info": {
      "id": "msg_xxx",
      "parentID": "msg_user_xxx",
      "role": "assistant",
      "error": {"name": "ProviderAuthError",
                "data": {"message": "...", "providerID": "..."}},
      "time": {"created": ...}
    }
  }
}
```

A well-behaved client reads `info.error.data.message` and surfaces it to
the user immediately, rather than continuing to wait for `finish` (which
never arrives on errored turns).

## Endpoint path

The SSE endpoint is **`/global/event`** in v1.4.6. Older drafts of this
doc referred to `/event`; that path 404s in v1.4.6.
