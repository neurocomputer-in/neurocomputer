# Real-Time Voice Call with Neuro Agent

**Date:** 2026-04-14
**Status:** Approved
**Scope:** Web application only (mobile later)

## Summary

Full-duplex voice conversation with a single Neuro agent, integrated into the existing web chat view. LiveKit handles audio transport (WebRTC), AgentSession orchestrates the VAD → STT → LLM → TTS pipeline, and the Brain retains full agentic control via the `InfinityBrainLLM` adapter. Voice turns appear as real-time transcripts in the chat timeline alongside text messages.

## Goals

- Ultra-low latency (~800ms–1.2s) full-duplex voice conversation
- Voice is a mode of an existing conversation — same `conversation_id`, same history
- Live transcripts in chat (user STT + agent response) visible in real-time
- Modern conversational features: barge-in, VAD, streaming TTS, smart endpointing
- English + Hindi via Sarvam STT
- Single ElevenLabs voice persona (extensible later)
- Text chat continues working during an active voice call
- Architecture supports mobile (Kotlin/LiveKit Android SDK) without backend changes

## Non-Goals (V1)

- Mobile implementation (deferred — same backend serves both)
- Multi-agent voice / conference calls
- Per-agent voice personas
- Voice-initiated commands (e.g., "switch to OpenClaw")
- Call recording / playback
- Speaker diarization

---

## Architecture

```
┌─────────────────── WEB BROWSER ───────────────────┐
│  ChatInput.tsx ── [Call Button] ── VoiceCallBar    │
│       │                               │            │
│  LiveKit Room (audio tracks + data channel)        │
└───────────────────────┬───────────────────────────┘
                        │ WebRTC (audio + data)
┌───────────────────────▼───────────────────────────┐
│              LIVEKIT CLOUD / SERVER                 │
└───────────────────────┬───────────────────────────┘
                        │
┌───────────────────────▼───────────────────────────┐
│            BACKEND (voice_manager.py)               │
│                                                     │
│  AgentSession pipeline:                             │
│  Silero VAD → Sarvam STT → InfinityBrainLLM → EL TTS │
│                    │                                │
│              Brain.handle()                          │
│         (router → planner → executor)               │
│                    │                                │
│    DataChannel events (transcripts, state, etc.)    │
└─────────────────────────────────────────────────────┘
```

**Key principle:** Voice call is a *mode* of an existing conversation, not a separate entity. Same `conversation_id`, same message history. Click "call" in chat → voice mode activates → messages appear in chat as both audio + transcript.

---

## Backend Pipeline

### Modifications to `voice_manager.py`

1. **Tie voice sessions to existing conversations.** Current `create_session` creates a standalone `voice_{user_id}` conversation. Change to accept the real `conversation_id` so voice shares history/context with text chat.

2. **Persist transcripts to DB in real-time.** As Sarvam STT produces final transcripts → save as user message (`type: "voice"`). As Brain produces response → save as agent message (`type: "voice"`). Both with timestamps.

3. **Broadcast transcripts via DataChannel.** Publish events so web UI shows live transcript bubbles:
   - `voice.user_transcript` — interim + final STT results (user sees their words appear)
   - `voice.agent_transcript` — agent's text response chunks (appears in chat while TTS plays)
   - `voice.state` — call state changes (`ringing`, `connected`, `ended`, `interrupted`)

4. **Brain adapter improvements.** Current `InfinityBrainLLM` reads from hub queue. Use Brain's stream callback directly for token-by-token streaming → lower latency to first TTS byte.

5. **Barge-in handling.** AgentSession's built-in interruption cancels current TTS. Publish `voice.interrupted` so frontend stops playback and shows new user transcript.

### Voice Session Lifecycle

```python
# POST /voice/call endpoint
async def start_voice_call(conversation_id: str, agent_id: str) -> dict:
    # Returns {token, url, room_name} for client to connect
    # Creates AgentSession tied to conversation_id
    # Agent joins same LiveKit room with audio tracks

# POST /voice/hangup endpoint
async def end_voice_call(conversation_id: str) -> dict:
    # Disconnects agent audio tracks
    # Publishes voice.state: ended
    # Cleans up session
```

### AgentSession Configuration

```python
AgentSession(
    llm=InfinityBrainLLM(brain, conversation_id, room),
    vad=silero.VAD.load(
        min_speech_duration=0.05,
        min_silence_duration=0.25,
        prefix_padding_duration=0.15,
        activation_threshold=0.35,
    ),
    stt=SarvamSTT(language="en-IN", model="saaras:v3"),
    tts=elevenlabs.TTS(
        voice_id=ELEVENLABS_VOICE_ID,
        model="eleven_flash_v2_5",
        api_key=ELEVENLABS_API_KEY,
        auto_mode=True,
    ),
)
```

### InfinityBrainLLM Adapter Changes

- Accept `conversation_id` (real conversation, not voice-only)
- Stream response tokens directly via Brain's stream callback instead of polling hub queue
- Publish `voice.user_transcript` and `voice.agent_transcript` events via DataChannel
- Write user STT transcript + agent response to DB with `type: "voice"`

---

## Data Flow — One Voice Turn

```
User speaks
    │
    ▼
Silero VAD detects speech start
    │
    ▼
Audio frames → Sarvam STT (WebSocket streaming)
    │
    ├── interim transcript → DataChannel "voice.user_transcript" {text, is_final: false}
    │   └── Frontend: shows grey typing bubble, updates in real-time
    │
    ▼
VAD detects silence → STT final transcript
    │
    ├── DataChannel "voice.user_transcript" {text, is_final: true}
    │   └── Frontend: solidifies into user message bubble
    │
    ├── DB write: {sender: "user", type: "voice", content: transcript}
    │
    ▼
InfinityBrainLLM → Brain.handle(cid, transcript)
    │
    ├── Brain routes (smart_router → reply or planner)
    │
    ▼
Response streams token-by-token
    │
    ├── DataChannel "voice.agent_transcript" {chunk, done: false}
    │   └── Frontend: agent bubble builds up in real-time
    │
    ├── Tokens → ElevenLabs streaming TTS → audio track → user hears
    │
    ▼
Response complete
    │
    ├── DataChannel "voice.agent_transcript" {text, done: true}
    ├── DB write: {sender: "agent", type: "voice", content: full_response}
    └── Frontend: agent bubble finalized with mic icon badge
```

### Barge-In Flow

```
Agent speaking (TTS playing)
    │
User starts talking
    │
    ▼
VAD fires → AgentSession cancels TTS playback
    │
    ├── DataChannel "voice.interrupted"
    │   └── Frontend: agent bubble shows partial text
    │
    ▼
New STT cycle starts for user's interruption
```

---

## Frontend — Web Voice Call UI

### UI Flow

1. **Initiate call** — phone icon button next to mic button in `ChatInput.tsx`. Click → `POST /voice/call` with current `conversation_id` → gets LiveKit token → connects to voice room with audio tracks enabled.

2. **Active call indicator** — minimal bar above chat input (`VoiceCallBar.tsx`):
   - Pulsing green dot + "Voice call active" + duration timer
   - Waveform visualizer (user's mic level)
   - Mute button, end call button
   - Chat stays visible and scrollable

3. **Live transcripts in chat:**
   - User speech → grey "typing" bubble with interim STT text, solidifies on final transcript
   - Agent response → agent message bubble appears with text while TTS audio plays
   - Messages tagged `origin: "voice"` — UI shows small mic icon on voice-originated messages

4. **Text still works during call** — user can type while on call. Text goes through normal `POST /chat/send`. Both coexist in same timeline.

5. **End call** — click end button → disconnects audio tracks, data channel stays for text chat. Publishes `voice.state: ended`.

### New/Modified Frontend Files

| File | Action | Purpose |
|------|--------|---------|
| `hooks/useVoiceCall.ts` | **New** | LiveKit audio track connection, call state, mic mute |
| `components/chat/VoiceCallBar.tsx` | **New** | In-chat call indicator strip with controls |
| `components/chat/ChatInput.tsx` | **Modify** | Add call button next to mic |
| `services/livekit.ts` | **Modify** | Extend to handle audio tracks (currently data-only) |
| `services/api.ts` | **Modify** | Add `apiStartVoiceCall()`, `apiEndVoiceCall()` endpoints |
| `components/chat/MessageBubble.tsx` | **Modify** | Show mic icon badge for `origin: "voice"` messages |
| `store/chatSlice.ts` | **Modify** | Add voice call state (active, muted, duration) |

### LiveKit Service Extension

Current `livekitService` manages one room per conversation for data channel only. Voice call reuses the **same room** — adds audio tracks to it. No second room.

```typescript
// New methods on livekitService
async enableAudio(): Promise<void>    // publish local mic track
async disableAudio(): Promise<void>   // unpublish mic track
onRemoteAudio(handler): void          // subscribe to agent's audio track
```

---

## Error Handling

| Scenario | Handling |
|----------|----------|
| Network disconnect mid-call | LiveKit auto-reconnect (3 attempts). If fails → end call, show "Call dropped", text chat continues |
| Sarvam STT WebSocket drops | AgentSession reconnects STT stream automatically |
| No mic permission | Show permission prompt, don't start call until granted |
| Mic in use | Catch `NotAllowedError`, show "Mic unavailable" toast |
| Echo / feedback | Browser AEC via `getUserMedia` constraints: `echoCancellation: true, noiseSuppression: true` |
| Brain timeout (>30s) | Existing timeout in `InfinityBrainStream`. TTS says placeholder, call stays alive |
| Brain returns empty | Skip TTS, don't create empty bubble |
| Two tabs same conversation | One voice session per conversation enforced server-side |
| Tab close during call | LiveKit detects participant leave → server cleanup |
| Text + voice concurrent | Both work. Interleave in timeline, same Brain instance |

---

## Backend API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/voice/call` | Start voice call. Body: `{conversation_id, agent_id}`. Returns `{token, url, room_name}` |
| `POST` | `/voice/hangup` | End voice call. Body: `{conversation_id}` |
| `GET` | `/voice/status/{conversation_id}` | Check if call is active |

---

## DataChannel Event Schema

All events published as JSON via LiveKit DataChannel.

```json
// User transcript (interim)
{"topic": "voice.user_transcript", "text": "hello how are", "is_final": false, "language": "en-IN"}

// User transcript (final)
{"topic": "voice.user_transcript", "text": "hello how are you", "is_final": true, "language": "en-IN", "message_id": "msg_abc123"}

// Agent response (streaming)
{"topic": "voice.agent_transcript", "chunk": "I'm doing", "done": false}

// Agent response (complete)
{"topic": "voice.agent_transcript", "text": "I'm doing great, thanks for asking!", "done": true, "message_id": "msg_def456"}

// Call state
{"topic": "voice.state", "state": "connected"}  // ringing | connected | ended
{"topic": "voice.interrupted"}
```

---

## Files to Modify (Backend)

| File | Changes |
|------|---------|
| `core/voice_manager.py` | Rewrite `create_session` to accept `conversation_id`. Improve `InfinityBrainLLM`/`InfinityBrainStream` for direct streaming. Add transcript persistence + DataChannel events. |
| `core/sarvam_stt.py` | No changes needed — already streaming-compatible |
| `server.py` | Add `/voice/call`, `/voice/hangup`, `/voice/status/{cid}` endpoints |
| `core/db.py` | Verify `add_message` supports `type: "voice"` (likely already works) |
| `core/brain.py` | Minor: ensure `handle()` stream callback works for voice adapter |
