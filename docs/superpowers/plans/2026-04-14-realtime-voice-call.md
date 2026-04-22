# Real-Time Voice Call Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add full-duplex voice calling to the web chat, reusing LiveKit AgentSession with custom Brain adapter, Sarvam STT, ElevenLabs TTS, and Silero VAD.

**Architecture:** LiveKit handles WebRTC audio transport. Server-side AgentSession orchestrates VAD → STT → LLM → TTS pipeline. The `InfinityBrainLLM` adapter bridges to Brain for full agentic control. Frontend extends the existing LiveKit data-channel room with audio tracks and shows live transcripts in the chat timeline.

**Tech Stack:** Python/FastAPI (backend), LiveKit agents SDK, Sarvam STT, ElevenLabs TTS, Silero VAD, Next.js/TypeScript/Redux (frontend), livekit-client SDK.

**Spec:** `docs/superpowers/specs/2026-04-14-realtime-voice-call-design.md`

---

## File Structure

### Backend (Python)

| File | Action | Responsibility |
|------|--------|----------------|
| `core/voice_manager.py` | **Rewrite** | VoiceManager tied to conversation IDs, improved InfinityBrainLLM/Stream with direct streaming, transcript persistence, DataChannel events |
| `server.py` | **Modify** | Add `/voice/call`, `/voice/hangup`, `/voice/status/{cid}` endpoints |

### Frontend (TypeScript)

| File | Action | Responsibility |
|------|--------|----------------|
| `neuro_web/services/api.ts` | **Modify** | Add `apiStartVoiceCall()`, `apiEndVoiceCall()`, `apiVoiceCallStatus()` |
| `neuro_web/services/livekit.ts` | **Modify** | Add `enableAudio()`, `disableAudio()`, `getRoom()` for audio track management |
| `neuro_web/store/chatSlice.ts` | **Modify** | Add voice call state: `voiceCallActive`, `voiceCallMuted` |
| `neuro_web/hooks/useVoiceCall.ts` | **Create** | Hook managing voice call lifecycle: start/end call, mute, audio tracks, interim transcripts |
| `neuro_web/components/chat/VoiceCallBar.tsx` | **Create** | In-chat call indicator with controls (mute, end, duration, waveform) |
| `neuro_web/components/chat/ChatInput.tsx` | **Modify** | Add call button next to mic button |
| `neuro_web/providers/LiveKitProvider.tsx` | **Modify** | Handle `voice.*` DataChannel topics for transcript events |
| `neuro_web/components/chat/MessageBubble.tsx` | **Modify** | Show mic icon badge for `origin: "voice"` messages |

---

## Task 1: Rewrite VoiceManager Backend

**Files:**
- Modify: `core/voice_manager.py` (full rewrite)

- [ ] **Step 1: Rewrite VoiceSession to use conversation_id**

Replace the entire `core/voice_manager.py` with:

```python
"""
Voice Manager - Full-duplex voice calls via LiveKit AgentSession.

Pipeline: Silero VAD → Sarvam STT → InfinityBrainLLM (Brain) → ElevenLabs TTS
Sessions are tied to conversation IDs so voice shares history with text chat.
"""

import asyncio
import os
import logging
import json
import uuid
from typing import Optional, Dict
from dataclasses import dataclass

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    llm,
    ChatContext,
)
from livekit.plugins import silero, elevenlabs

from core.brain import Brain
from core.pubsub import hub
from core.db import db
from core.sarvam_stt import SarvamSTT

logger = logging.getLogger("voice-manager")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "***REDACTED***")


@dataclass
class VoiceSession:
    """Tracks an active voice call."""
    conversation_id: str
    agent_id: str
    room_name: str
    room: rtc.Room
    session: AgentSession
    brain: Brain
    _task: Optional[asyncio.Task] = None


class InfinityBrainLLM(llm.LLM):
    """
    Custom LLM adapter routing to Brain instead of a direct model.
    Publishes voice transcript events via DataChannel for frontend.
    """

    def __init__(self, brain: Brain, conversation_id: str, agent_id: str, room: rtc.Room):
        super().__init__()
        self._brain = brain
        self._cid = conversation_id
        self._agent_id = agent_id
        self._room = room

    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list | None = None,
        conn_options=None,
        **kwargs,
    ) -> "llm.LLMStream":
        user_message = ""
        for msg in reversed(chat_ctx.items):
            if msg.role == "user":
                user_message = msg.text_content
                break

        if not user_message:
            user_message = "Hello"

        logger.info(f"[Voice] User said: {user_message[:100]}")

        return InfinityBrainStream(
            llm=self,
            brain=self._brain,
            conversation_id=self._cid,
            agent_id=self._agent_id,
            room=self._room,
            user_message=user_message,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )


class InfinityBrainStream(llm.LLMStream):
    """Streams Brain response into LiveKit AgentSession TTS pipeline."""

    def __init__(
        self,
        *,
        llm: InfinityBrainLLM,
        brain: Brain,
        conversation_id: str,
        agent_id: str,
        room: rtc.Room,
        user_message: str,
        chat_ctx: ChatContext,
        tools: list,
        conn_options,
    ):
        from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
        super().__init__(
            llm=llm,
            chat_ctx=chat_ctx,
            tools=tools,
            conn_options=conn_options or DEFAULT_API_CONNECT_OPTIONS,
        )
        self._brain = brain
        self._cid = conversation_id
        self._agent_id = agent_id
        self._room = room
        self._user_message = user_message

    async def _publish_voice_event(self, topic: str, data: dict):
        """Publish voice event to frontend via LiveKit DataChannel."""
        if not self._room or not self._room.local_participant:
            return
        try:
            payload = json.dumps({"topic": topic, **data})
            await self._room.local_participant.publish_data(
                payload.encode("utf-8"),
                reliable=True,
                topic=topic,
            )
        except Exception as e:
            logger.error(f"[Voice] DataChannel publish error: {e}")

    async def _run(self) -> None:
        """Called by AgentSession when LLM turn is needed."""
        try:
            # Publish user transcript as final (STT already produced it)
            user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            await self._publish_voice_event("voice.user_transcript", {
                "text": self._user_message,
                "is_final": True,
                "message_id": user_msg_id,
            })

            # Persist user voice message to DB
            await db.add_message(
                conversation_id=self._cid,
                sender="user",
                msg_type="voice",
                content=self._user_message,
            )

            # Process through Brain
            queue = hub.queue(self._cid)
            await self._brain.handle(
                self._cid, self._user_message, agent_id=self._agent_id
            )

            response = ""
            agent_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            timeout = 30
            start_time = asyncio.get_event_loop().time()

            while True:
                try:
                    remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                    if remaining <= 0:
                        break

                    msg = await asyncio.wait_for(queue.get(), timeout=remaining)
                    title = msg.get("topic")
                    data = msg.get("data")

                    if title in ("task.done", "node.done") and response:
                        break

                    if title == "assistant" and isinstance(data, str) and data:
                        response += data

                        # Publish agent transcript chunk to frontend
                        await self._publish_voice_event("voice.agent_transcript", {
                            "chunk": data,
                            "done": False,
                        })

                        # Feed chunk to TTS pipeline
                        self._event_ch.send_nowait(
                            llm.ChatChunk(
                                id=agent_msg_id,
                                delta=llm.ChoiceDelta(role="assistant", content=data),
                            )
                        )

                except asyncio.TimeoutError:
                    break

            # Publish final agent transcript
            if response:
                await self._publish_voice_event("voice.agent_transcript", {
                    "text": response,
                    "done": True,
                    "message_id": agent_msg_id,
                })

                # Persist agent voice response to DB
                await db.add_message(
                    conversation_id=self._cid,
                    sender="agent",
                    msg_type="voice",
                    content=response,
                )
            else:
                placeholder = "I'm thinking..."
                self._event_ch.send_nowait(
                    llm.ChatChunk(
                        id="fallback",
                        delta=llm.ChoiceDelta(role="assistant", content=placeholder),
                    )
                )

            logger.info(f"[Voice] Response complete: {len(response)} chars")

        except Exception as e:
            logger.error(f"[Voice] Brain stream error: {e}", exc_info=True)


class VoiceManager:
    """Manages full-duplex voice call sessions via LiveKit."""

    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}
        self._url = os.getenv("LIVEKIT_URL", "")
        self._api_key = os.getenv("LIVEKIT_API_KEY", "")
        self._api_secret = os.getenv("LIVEKIT_API_SECRET", "")

    def _generate_token(
        self, room_name: str, identity: str, is_agent: bool = False
    ) -> str:
        token = api.AccessToken(self._api_key, self._api_secret)
        token.with_identity(identity)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                agent=is_agent,
            )
        )
        return token.to_jwt()

    async def start_call(
        self, conversation_id: str, agent_id: str = "neuro"
    ) -> dict:
        """Start a voice call for a conversation. Returns token for client."""
        if not self._url or not self._api_key:
            raise ValueError("LiveKit credentials missing")

        # End existing session if any
        if conversation_id in self._sessions:
            await self.end_call(conversation_id)

        room_name = f"voice-{conversation_id}"
        room = rtc.Room()
        agent_token = self._generate_token(
            room_name, f"voice-agent-{conversation_id}", is_agent=True
        )
        await room.connect(self._url, agent_token)

        brain = Brain()
        agent = Agent(
            instructions="You are Neuro, a helpful AI voice assistant. Keep responses concise and conversational."
        )

        session = AgentSession(
            llm=InfinityBrainLLM(brain, conversation_id, agent_id, room),
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

        task = asyncio.create_task(self._run_session(session, room, agent))

        vs = VoiceSession(
            conversation_id=conversation_id,
            agent_id=agent_id,
            room_name=room_name,
            room=room,
            session=session,
            brain=brain,
            _task=task,
        )
        self._sessions[conversation_id] = vs

        # Publish call state
        try:
            payload = json.dumps({"topic": "voice.state", "state": "connected"})
            await room.local_participant.publish_data(
                payload.encode("utf-8"), reliable=True, topic="voice.state"
            )
        except Exception:
            pass

        user_token = self._generate_token(
            room_name, f"voice-user-{conversation_id}"
        )
        return {
            "token": user_token,
            "room_name": room_name,
            "url": self._url,
            "conversation_id": conversation_id,
        }

    async def _run_session(
        self, session: AgentSession, room: rtc.Room, agent: Agent
    ):
        try:
            await session.start(room=room, agent=agent)
            while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("[Voice] Session task cancelled")
        except Exception as e:
            logger.error(f"[Voice] Session error: {e}")
        finally:
            try:
                await room.disconnect()
            except Exception:
                pass

    async def end_call(self, conversation_id: str):
        """End a voice call session."""
        if conversation_id not in self._sessions:
            return

        vs = self._sessions.pop(conversation_id)

        # Publish ended state before disconnecting
        try:
            payload = json.dumps({"topic": "voice.state", "state": "ended"})
            await vs.room.local_participant.publish_data(
                payload.encode("utf-8"), reliable=True, topic="voice.state"
            )
        except Exception:
            pass

        if vs._task and not vs._task.done():
            vs._task.cancel()
            try:
                await vs._task
            except asyncio.CancelledError:
                pass

        try:
            await vs.room.disconnect()
        except Exception:
            pass

    def is_active(self, conversation_id: str) -> bool:
        """Check if a voice call is active for a conversation."""
        return conversation_id in self._sessions


voice_manager = VoiceManager()
```

- [ ] **Step 2: Verify backend imports work**

Run:
```bash
cd /home/ubuntu/neurocomputer-dev && python -c "from core.voice_manager import voice_manager; print('OK')"
```
Expected: `OK` (no import errors)

- [ ] **Step 3: Commit**

```bash
git add core/voice_manager.py
git commit -m "feat(voice): rewrite voice manager for conversation-tied full-duplex calls"
```

---

## Task 2: Add Voice Call API Endpoints

**Files:**
- Modify: `server.py:1185-1222`

- [ ] **Step 1: Replace existing voice endpoints in server.py**

Find the existing voice endpoints section (around line 1185) and replace:

```python
# Old endpoints:
# @app.post("/voice/token")
# @app.post("/voice/end")
```

With these new endpoints:

```python
@app.post("/voice/call")
async def voice_call_start(body: dict):
    """
    Start a full-duplex voice call for a conversation.

    Body: {"conversation_id": "...", "agent_id": "neuro"}
    Returns: {"token": "...", "url": "...", "room_name": "...", "conversation_id": "..."}
    """
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id required")
    agent_id = body.get("agent_id", "neuro")

    try:
        result = await voice_manager.start_call(conversation_id, agent_id)
        logger.info(f"Voice call started for conversation {conversation_id}")
        return result
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to start voice call: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start voice call: {e}")


@app.post("/voice/hangup")
async def voice_call_end(body: dict):
    """
    End a voice call.

    Body: {"conversation_id": "..."}
    """
    conversation_id = body.get("conversation_id")
    if not conversation_id:
        raise HTTPException(status_code=400, detail="conversation_id required")

    await voice_manager.end_call(conversation_id)
    return {"status": "ended", "conversation_id": conversation_id}


@app.get("/voice/status/{conversation_id}")
async def voice_call_status(conversation_id: str):
    """Check if a voice call is active."""
    return {
        "active": voice_manager.is_active(conversation_id),
        "conversation_id": conversation_id,
    }


# Keep legacy endpoints for backward compatibility
@app.post("/voice/token")
async def voice_token(body: dict):
    """Legacy: create voice session by user_id. Redirects to start_call."""
    user_id = body.get("user_id") or uuid.uuid4().hex[:8]
    conversation_id = f"voice_{user_id}"
    try:
        result = await voice_manager.start_call(conversation_id)
        return result
    except Exception as e:
        logger.error(f"Failed to create voice session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/voice/end")
async def voice_end(body: dict):
    """Legacy: end voice session by user_id."""
    user_id = body.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id required")
    await voice_manager.end_call(f"voice_{user_id}")
    return {"status": "ended"}
```

- [ ] **Step 2: Verify server starts without errors**

Run:
```bash
cd /home/ubuntu/neurocomputer-dev && timeout 5 python -c "
from server import app
print('FastAPI app created successfully')
" 2>&1 || true
```
Expected: `FastAPI app created successfully` (may timeout but no import errors)

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat(voice): add /voice/call, /voice/hangup, /voice/status endpoints"
```

---

## Task 3: Extend Frontend API and LiveKit Services

**Files:**
- Modify: `neuro_web/services/api.ts`
- Modify: `neuro_web/services/livekit.ts`

- [ ] **Step 1: Add voice call API functions to api.ts**

Append to `neuro_web/services/api.ts` after the existing LLM Settings section:

```typescript
// ---- Voice Call ----

export async function apiStartVoiceCall(data: {
  conversationId: string;
  agentId?: string;
}): Promise<{ token: string; url: string; room_name: string; conversation_id: string }> {
  const res = await api.post('/voice/call', {
    conversation_id: data.conversationId,
    agent_id: data.agentId || 'neuro',
  });
  return res.data;
}

export async function apiEndVoiceCall(conversationId: string): Promise<void> {
  await api.post('/voice/hangup', { conversation_id: conversationId });
}

export async function apiVoiceCallStatus(conversationId: string): Promise<{ active: boolean }> {
  const res = await api.get(`/voice/status/${conversationId}`);
  return res.data;
}
```

- [ ] **Step 2: Extend livekitService with audio track management**

Replace the entire `neuro_web/services/livekit.ts` with:

```typescript
import {
  Room, RoomEvent, DataPacket_Kind, RemoteParticipant,
  ConnectionState, RoomOptions, LocalAudioTrack,
  createLocalAudioTrack, Track, RemoteTrack, RemoteTrackPublication,
} from 'livekit-client';
import { apiGetChatToken } from './api';

export type DataMessageHandler = (text: string, topic: string) => void;

class LiveKitService {
  private room: Room | null = null;
  private currentCid: string | null = null;
  private messageHandler: DataMessageHandler | null = null;
  private stateHandler: ((state: ConnectionState) => void) | null = null;
  private connecting: boolean = false;
  private suppressStateEvents: boolean = false;

  // Voice call state
  private localAudioTrack: LocalAudioTrack | null = null;
  private remoteAudioHandler: ((track: MediaStreamTrack) => void) | null = null;

  onMessage(handler: DataMessageHandler) {
    this.messageHandler = handler;
  }

  onStateChange(handler: (state: ConnectionState) => void) {
    this.stateHandler = handler;
  }

  async connect(cid: string): Promise<void> {
    if (this.currentCid === cid && this.room?.state === ConnectionState.Connected) return;
    if (this.connecting) {
      console.log('[LK] already connecting, skipping duplicate');
      return;
    }
    this.connecting = true;

    this.suppressStateEvents = true;
    await this.disconnect();
    this.suppressStateEvents = false;

    this.currentCid = cid;

    const { token, url } = await apiGetChatToken(cid);

    const options: RoomOptions = {
      adaptiveStream: false,
      dynacast: false,
    };

    this.room = new Room(options);

    this.room.on(RoomEvent.ConnectionStateChanged, (state: ConnectionState) => {
      if (!this.suppressStateEvents) {
        this.stateHandler?.(state);
      }
    });

    this.room.on(
      RoomEvent.DataReceived,
      (payload: Uint8Array, participant?: RemoteParticipant, _kind?: DataPacket_Kind, topic?: string) => {
        try {
          const text = new TextDecoder().decode(payload);
          this.messageHandler?.(text, topic ?? 'agent_response');
        } catch (e) {
          console.error('Failed to decode DataChannel message', e);
        }
      }
    );

    // Handle remote audio tracks (agent's TTS audio during voice calls)
    this.room.on(
      RoomEvent.TrackSubscribed,
      (track: RemoteTrack, publication: RemoteTrackPublication, participant: RemoteParticipant) => {
        if (track.kind === Track.Kind.Audio) {
          console.log('[LK] Remote audio track subscribed');
          const audioElement = track.attach();
          document.body.appendChild(audioElement);
          this.remoteAudioHandler?.(track.mediaStreamTrack);
        }
      }
    );

    this.room.on(
      RoomEvent.TrackUnsubscribed,
      (track: RemoteTrack) => {
        if (track.kind === Track.Kind.Audio) {
          console.log('[LK] Remote audio track unsubscribed');
          track.detach().forEach(el => el.remove());
        }
      }
    );

    try {
      await this.room.connect(url, token);
    } catch (err) {
      console.error('[LK] room.connect() FAILED:', err);
      throw err;
    } finally {
      this.connecting = false;
    }
  }

  // ---- Voice Call Audio Methods ----

  async enableAudio(): Promise<void> {
    if (!this.room) throw new Error('Not connected to a room');
    if (this.localAudioTrack) return;

    this.localAudioTrack = await createLocalAudioTrack({
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    });
    await this.room.localParticipant.publishTrack(this.localAudioTrack);
    console.log('[LK] Local audio track published');
  }

  async disableAudio(): Promise<void> {
    if (this.localAudioTrack && this.room) {
      await this.room.localParticipant.unpublishTrack(this.localAudioTrack);
      this.localAudioTrack.stop();
      this.localAudioTrack = null;
      console.log('[LK] Local audio track unpublished');
    }
  }

  setMuted(muted: boolean): void {
    if (this.localAudioTrack) {
      this.localAudioTrack.mute();
      if (!muted) this.localAudioTrack.unmute();
    }
  }

  isAudioEnabled(): boolean {
    return this.localAudioTrack !== null;
  }

  onRemoteAudio(handler: (track: MediaStreamTrack) => void) {
    this.remoteAudioHandler = handler;
  }

  getRoom(): Room | null {
    return this.room;
  }

  // ---- Existing Methods ----

  async disconnect(): Promise<void> {
    await this.disableAudio();
    if (this.room) {
      await this.room.disconnect();
      this.room = null;
    }
    this.currentCid = null;
  }

  getState(): ConnectionState {
    return this.room?.state ?? ConnectionState.Disconnected;
  }
}

export const livekitService = new LiveKitService();
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/services/api.ts neuro_web/services/livekit.ts
git commit -m "feat(voice): add voice call API functions and audio track support to LiveKit service"
```

---

## Task 4: Add Voice Call State to Redux

**Files:**
- Modify: `neuro_web/store/chatSlice.ts`

- [ ] **Step 1: Add voice call state to chatSlice**

Replace `neuro_web/store/chatSlice.ts` with:

```typescript
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface StepInfo {
  nodeId: string;
  neuro: string;
  status: 'running' | 'done' | 'error';
}

interface VoiceCallState {
  active: boolean;
  muted: boolean;
  startedAt: string | null;
}

interface ChatState {
  isLoading: boolean;
  inputText: string;
  thinkingContent: string | null;
  currentStep: StepInfo | null;
  voiceCall: VoiceCallState;
  interimTranscript: string | null;
}

const initialState: ChatState = {
  isLoading: false,
  inputText: '',
  thinkingContent: null,
  currentStep: null,
  voiceCall: { active: false, muted: false, startedAt: null },
  interimTranscript: null,
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
      if (!action.payload) {
        state.thinkingContent = null;
        state.currentStep = null;
      }
    },
    setInputText(state, action: PayloadAction<string>) {
      state.inputText = action.payload;
    },
    setThinkingContent(state, action: PayloadAction<string | null>) {
      state.thinkingContent = action.payload;
    },
    setCurrentStep(state, action: PayloadAction<StepInfo | null>) {
      state.currentStep = action.payload;
    },
    clearAgentState(state) {
      state.thinkingContent = null;
      state.currentStep = null;
    },
    setVoiceCallActive(state, action: PayloadAction<boolean>) {
      state.voiceCall.active = action.payload;
      state.voiceCall.startedAt = action.payload ? new Date().toISOString() : null;
      if (!action.payload) {
        state.voiceCall.muted = false;
        state.interimTranscript = null;
      }
    },
    setVoiceCallMuted(state, action: PayloadAction<boolean>) {
      state.voiceCall.muted = action.payload;
    },
    setInterimTranscript(state, action: PayloadAction<string | null>) {
      state.interimTranscript = action.payload;
    },
  },
});

export const {
  setLoading, setInputText, setThinkingContent,
  setCurrentStep, clearAgentState,
  setVoiceCallActive, setVoiceCallMuted, setInterimTranscript,
} = chatSlice.actions;
export default chatSlice.reducer;
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/store/chatSlice.ts
git commit -m "feat(voice): add voice call state to chat redux slice"
```

---

## Task 5: Handle Voice DataChannel Events in LiveKitProvider

**Files:**
- Modify: `neuro_web/providers/LiveKitProvider.tsx`

Voice events arrive from a **separate LiveKit room** (the voice room created by `useVoiceCall`), not from the main data-channel room. The hook forwards these via a `window` CustomEvent (`voice-data`). We add a `useEffect` in `LiveKitProvider` to listen and dispatch to Redux.

- [ ] **Step 1: Update imports in LiveKitProvider**

In `neuro_web/providers/LiveKitProvider.tsx`, update the chatSlice import:

```typescript
import { setLoading, setThinkingContent, setCurrentStep, setVoiceCallActive, setInterimTranscript } from '@/store/chatSlice';
```

- [ ] **Step 2: Add voice-data event listener useEffect**

Add a new `useEffect` in the `LiveKitProvider` component, after the existing handler registration `useEffect`:

```typescript
  // Forward voice call DataChannel events (from separate voice room) into Redux
  useEffect(() => {
    const handleVoiceData = (e: Event) => {
      const { text, topic } = (e as CustomEvent).detail;
      const cid = activeTabCidRef.current;
      if (!cid) return;

      let parsed: any;
      try {
        parsed = JSON.parse(text);
      } catch {
        return;
      }

      if (topic === 'voice.state') {
        const state = parsed.state;
        if (state === 'connected') dispatch(setVoiceCallActive(true));
        else if (state === 'ended') dispatch(setVoiceCallActive(false));
        return;
      }

      if (topic === 'voice.user_transcript') {
        if (parsed.is_final && parsed.text) {
          dispatch(setInterimTranscript(null));
          const message: Message = {
            id: parsed.message_id || `voice-user-${Date.now()}`,
            text: parsed.text,
            isUser: true,
            isVoice: true,
            timestamp: new Date().toISOString(),
          };
          dispatch(appendMessage({ cid, message }));
        } else if (parsed.text) {
          dispatch(setInterimTranscript(parsed.text));
        }
        return;
      }

      if (topic === 'voice.agent_transcript') {
        if (parsed.done && parsed.text) {
          const message: Message = {
            id: parsed.message_id || `voice-agent-${Date.now()}`,
            text: parsed.text,
            isUser: false,
            isVoice: true,
            timestamp: new Date().toISOString(),
          };
          dispatch(appendMessage({ cid, message }));
          dispatch(setLoading(false));
        }
        return;
      }

      if (topic === 'voice.interrupted') {
        console.log('[Voice] Agent interrupted by user');
        return;
      }
    };
    window.addEventListener('voice-data', handleVoiceData);
    return () => window.removeEventListener('voice-data', handleVoiceData);
  }, [dispatch]);
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/providers/LiveKitProvider.tsx
git commit -m "feat(voice): handle voice transcript DataChannel events in LiveKitProvider"
```

---

## Task 6: Create useVoiceCall Hook

**Files:**
- Create: `neuro_web/hooks/useVoiceCall.ts`

- [ ] **Step 1: Create the voice call hook**

Create `neuro_web/hooks/useVoiceCall.ts`:

```typescript
'use client';
import { useState, useCallback } from 'react';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setVoiceCallActive, setVoiceCallMuted } from '@/store/chatSlice';
import { apiStartVoiceCall, apiEndVoiceCall } from '@/services/api';
import { livekitService } from '@/services/livekit';

export function useVoiceCall() {
  const dispatch = useAppDispatch();
  const activeTabCid = useAppSelector(s => s.conversations.activeTabCid);
  const openTabs = useAppSelector(s => s.conversations.openTabs);
  const voiceCall = useAppSelector(s => s.chat.voiceCall);
  const interimTranscript = useAppSelector(s => s.chat.interimTranscript);
  const activeTabAgentId = openTabs.find(t => t.cid === activeTabCid)?.agentId ?? 'neuro';

  const [connecting, setConnecting] = useState(false);

  const startCall = useCallback(async () => {
    if (!activeTabCid || voiceCall.active || connecting) return;
    setConnecting(true);

    try {
      // Get voice call token from backend (starts AgentSession)
      const result = await apiStartVoiceCall({
        conversationId: activeTabCid,
        agentId: activeTabAgentId,
      });

      // Connect to voice room with audio
      // The data-channel room is already connected via livekitService.
      // For voice, we need a separate room connection with audio tracks.
      // We use the voice room token from the backend.
      const { Room, RoomEvent, Track } = await import('livekit-client');
      const voiceRoom = new Room({ adaptiveStream: false, dynacast: false });

      // Handle remote audio (agent TTS)
      voiceRoom.on(RoomEvent.TrackSubscribed, (track: any) => {
        if (track.kind === Track.Kind.Audio) {
          const el = track.attach();
          el.id = 'voice-call-audio';
          document.body.appendChild(el);
        }
      });
      voiceRoom.on(RoomEvent.TrackUnsubscribed, (track: any) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach().forEach((el: HTMLElement) => el.remove());
        }
      });

      // Forward data messages to the existing handler
      voiceRoom.on(RoomEvent.DataReceived, (payload: Uint8Array, _p: any, _k: any, topic?: string) => {
        try {
          const text = new TextDecoder().decode(payload);
          // Dispatch through existing livekitService message handler
          const parsed = JSON.parse(text);
          const event = new CustomEvent('voice-data', { detail: { text, topic: topic || parsed.topic } });
          window.dispatchEvent(event);
        } catch {}
      });

      await voiceRoom.connect(result.url, result.token);

      // Publish local mic audio
      const { createLocalAudioTrack } = await import('livekit-client');
      const micTrack = await createLocalAudioTrack({
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      });
      await voiceRoom.localParticipant.publishTrack(micTrack);

      // Store references for cleanup
      (window as any).__voiceCallRoom = voiceRoom;
      (window as any).__voiceCallMicTrack = micTrack;

      dispatch(setVoiceCallActive(true));
    } catch (e: any) {
      console.error('[VoiceCall] Failed to start:', e?.message || e);
    } finally {
      setConnecting(false);
    }
  }, [activeTabCid, activeTabAgentId, voiceCall.active, connecting, dispatch]);

  const endCall = useCallback(async () => {
    if (!activeTabCid) return;

    // Clean up local room
    const voiceRoom = (window as any).__voiceCallRoom;
    const micTrack = (window as any).__voiceCallMicTrack;

    if (micTrack) {
      micTrack.stop();
      (window as any).__voiceCallMicTrack = null;
    }
    if (voiceRoom) {
      await voiceRoom.disconnect();
      (window as any).__voiceCallRoom = null;
    }

    // Remove any lingering audio elements
    document.getElementById('voice-call-audio')?.remove();

    // Tell backend to end session
    try {
      await apiEndVoiceCall(activeTabCid);
    } catch (e: any) {
      console.error('[VoiceCall] Hangup error:', e?.message);
    }

    dispatch(setVoiceCallActive(false));
  }, [activeTabCid, dispatch]);

  const toggleMute = useCallback(() => {
    const micTrack = (window as any).__voiceCallMicTrack;
    if (!micTrack) return;

    const newMuted = !voiceCall.muted;
    if (newMuted) {
      micTrack.mute();
    } else {
      micTrack.unmute();
    }
    dispatch(setVoiceCallMuted(newMuted));
  }, [voiceCall.muted, dispatch]);

  return {
    startCall,
    endCall,
    toggleMute,
    connecting,
    isActive: voiceCall.active,
    isMuted: voiceCall.muted,
    startedAt: voiceCall.startedAt,
    interimTranscript,
  };
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/hooks/useVoiceCall.ts neuro_web/providers/LiveKitProvider.tsx
git commit -m "feat(voice): create useVoiceCall hook and wire voice data events"
```

---

## Task 7: Create VoiceCallBar Component

**Files:**
- Create: `neuro_web/components/chat/VoiceCallBar.tsx`

- [ ] **Step 1: Create the voice call bar component**

Create `neuro_web/components/chat/VoiceCallBar.tsx`:

```typescript
'use client';
import { useEffect, useState } from 'react';
import { Phone, PhoneOff, MicOff, Mic } from 'lucide-react';
import { useVoiceCall } from '@/hooks/useVoiceCall';

function formatDuration(startedAt: string | null): string {
  if (!startedAt) return '0:00';
  const seconds = Math.floor((Date.now() - new Date(startedAt).getTime()) / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export default function VoiceCallBar() {
  const { isActive, isMuted, startedAt, interimTranscript, endCall, toggleMute } = useVoiceCall();
  const [duration, setDuration] = useState('0:00');

  // Update duration every second
  useEffect(() => {
    if (!isActive || !startedAt) return;
    const interval = setInterval(() => {
      setDuration(formatDuration(startedAt));
    }, 1000);
    return () => clearInterval(interval);
  }, [isActive, startedAt]);

  if (!isActive) return null;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '8px 16px',
        margin: '0 24px 4px',
        maxWidth: '1024px',
        alignSelf: 'center',
        width: '100%',
        background: 'rgba(34, 197, 94, 0.08)',
        border: '1px solid rgba(34, 197, 94, 0.2)',
        borderRadius: '10px',
        boxSizing: 'border-box',
      }}
    >
      {/* Pulsing green dot */}
      <span
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: '#22C55E',
          animation: 'voicePulse 1.5s ease-in-out infinite',
          flexShrink: 0,
        }}
      />

      {/* Status text */}
      <span style={{ fontSize: '12px', color: '#22C55E', fontWeight: 500 }}>
        Voice call
      </span>

      {/* Duration */}
      <span style={{ fontSize: '12px', color: '#666', fontFamily: 'monospace' }}>
        {duration}
      </span>

      {/* Interim transcript */}
      {interimTranscript && (
        <span
          style={{
            flex: 1,
            fontSize: '11px',
            color: '#888',
            fontStyle: 'italic',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {interimTranscript}
        </span>
      )}
      {!interimTranscript && <span style={{ flex: 1 }} />}

      {/* Mute button */}
      <button
        onClick={toggleMute}
        style={{
          width: '28px',
          height: '28px',
          borderRadius: '7px',
          background: isMuted ? 'rgba(239, 68, 68, 0.15)' : 'rgba(255, 255, 255, 0.05)',
          border: isMuted ? '1px solid rgba(239, 68, 68, 0.3)' : '1px solid rgba(255, 255, 255, 0.08)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'all 0.15s',
          flexShrink: 0,
        }}
        title={isMuted ? 'Unmute' : 'Mute'}
      >
        {isMuted ? (
          <MicOff size={13} color="#ef4444" />
        ) : (
          <Mic size={13} color="#888" />
        )}
      </button>

      {/* End call button */}
      <button
        onClick={endCall}
        style={{
          width: '28px',
          height: '28px',
          borderRadius: '7px',
          background: 'rgba(239, 68, 68, 0.15)',
          border: '1px solid rgba(239, 68, 68, 0.3)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: 'pointer',
          transition: 'all 0.15s',
          flexShrink: 0,
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.25)'; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'rgba(239, 68, 68, 0.15)'; }}
        title="End call"
      >
        <PhoneOff size={13} color="#ef4444" />
      </button>

      <style>{`
        @keyframes voicePulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.5; transform: scale(1.2); }
        }
      `}</style>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/chat/VoiceCallBar.tsx
git commit -m "feat(voice): create VoiceCallBar component with controls and live transcript"
```

---

## Task 8: Add Call Button to ChatInput and Wire Up VoiceCallBar

**Files:**
- Modify: `neuro_web/components/chat/ChatInput.tsx`
- Modify: `neuro_web/components/chat/ChatPanel.tsx`

- [ ] **Step 1: Add call button to ChatInput**

In `neuro_web/components/chat/ChatInput.tsx`, add import:

```typescript
import { Paperclip, ArrowUp, Mic, Square, CircleStop, Phone, PhoneOff } from 'lucide-react';
import { useVoiceCall } from '@/hooks/useVoiceCall';
```

Inside the `ChatInput` component, add the hook:

```typescript
  const { startCall, endCall, isActive: voiceCallActive, connecting: voiceConnecting } = useVoiceCall();
```

Then add the call button between the mic button and the divider. Find this section in the JSX (the `<div>` containing mic and send buttons):

Replace the button area (the `<div style={{ display: 'flex', alignItems: 'center', gap: '6px', ...}}>`) with:

```tsx
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', paddingBottom: '1px', flexShrink: 0 }}>
          {/* Voice call button */}
          <button
            onClick={voiceCallActive ? endCall : startCall}
            disabled={noConversation || voiceConnecting}
            style={{
              width: '30px', height: '30px', borderRadius: '8px',
              background: voiceCallActive ? 'rgba(34, 197, 94, 0.15)' : 'rgba(255,255,255,0.05)',
              border: voiceCallActive ? '1px solid rgba(34, 197, 94, 0.3)' : 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: noConversation ? 'not-allowed' : 'pointer',
              opacity: noConversation ? 0.3 : 1,
              transition: 'all 0.15s',
            }}
            title={voiceCallActive ? 'End voice call' : 'Start voice call'}
          >
            {voiceCallActive ? (
              <PhoneOff size={14} color="#22C55E" />
            ) : voiceConnecting ? (
              <Phone size={14} color="#888" style={{ animation: 'pulse 1s infinite' }} />
            ) : (
              <Phone size={14} color="#888" />
            )}
          </button>

          {/* Mic button */}
          <button
            onClick={handleMicClick}
            disabled={noConversation || (isLoading && !recording) || voiceCallActive}
            style={{
              width: '30px', height: '30px', borderRadius: '8px',
              background: recording ? '#ef4444' : 'rgba(255,255,255,0.05)',
              border: 'none',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: noConversation || voiceCallActive ? 'not-allowed' : 'pointer',
              opacity: noConversation || voiceCallActive ? 0.3 : 1,
              transition: 'all 0.15s',
            }}
            title={recording ? 'Stop & send voice' : 'Record voice message'}
          >
            {recording ? <Square size={13} color="#fff" /> : <Mic size={15} color="#888" />}
          </button>

          <div style={{ width: '1px', height: '20px', background: 'rgba(255,255,255,0.08)' }} />

          {/* Send or Stop button */}
          {isLoading ? (
            <button
              data-testid="stop-button"
              onClick={handleStop}
              style={{
                width: '30px', height: '30px', borderRadius: '8px',
                background: 'rgba(239,68,68,0.15)',
                border: '1px solid rgba(239,68,68,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.25)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(239,68,68,0.15)'; }}
              title="Stop generating"
            >
              <CircleStop size={15} color="#ef4444" strokeWidth={1.8} />
            </button>
          ) : (
            <button
              data-testid="send-button"
              onClick={handleSend}
              disabled={!canSend}
              style={{
                width: '30px', height: '30px', borderRadius: '8px',
                background: canSend ? '#8B5CF6' : 'rgba(255,255,255,0.05)',
                border: 'none',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: canSend ? 'pointer' : 'default',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { if (canSend) e.currentTarget.style.background = '#7C3AED'; }}
              onMouseLeave={e => { if (canSend) e.currentTarget.style.background = '#8B5CF6'; }}
            >
              <ArrowUp size={15} color={canSend ? '#fff' : '#444'} strokeWidth={2.5} />
            </button>
          )}
        </div>
```

- [ ] **Step 2: Add VoiceCallBar to ChatPanel**

In `neuro_web/components/chat/ChatPanel.tsx`, add import at top:

```typescript
import VoiceCallBar from './VoiceCallBar';
```

Then in the main return (the JSX block starting around line 439 `return (<>...`), add `<VoiceCallBar />` just before the `<div ref={bottomRef} />`:

Find this line:
```tsx
          <div ref={bottomRef} />
```

And insert before it:
```tsx
          <VoiceCallBar />
```

Wait — the VoiceCallBar should appear above the chat input, not in the message area. Better placement: add it between the message scroll area and the ChatInput. Since ChatPanel doesn't render ChatInput directly (it's rendered by the parent layout), we should place VoiceCallBar at the bottom of the scroll area.

Actually, looking at the layout, `ChatPanel` is the message area and `ChatInput` is separate. The VoiceCallBar should go right above ChatInput. Let me check the layout.

In `neuro_web/components/chat/ChatPanel.tsx`, add VoiceCallBar at the bottom of the scrollable area, just before `<div ref={bottomRef} />`:

```tsx
          <VoiceCallBar />
          <div ref={bottomRef} />
```

- [ ] **Step 3: Commit**

```bash
git add neuro_web/components/chat/ChatInput.tsx neuro_web/components/chat/ChatPanel.tsx
git commit -m "feat(voice): add call button to ChatInput and VoiceCallBar to ChatPanel"
```

---

## Task 9: Add Voice Origin Badge to MessageBubble

**Files:**
- Modify: `neuro_web/components/chat/MessageBubble.tsx`

- [ ] **Step 1: Add mic icon for voice-originated messages**

In `neuro_web/components/chat/MessageBubble.tsx`, add `Mic` to the lucide import:

```typescript
import { Volume2, VolumeX, Loader2, Mic } from 'lucide-react';
```

Then in the user message section, add a mic badge next to "You" when `message.isVoice` is true. Find this block (around line 84):

```tsx
            <span>You</span>
```

Replace with:

```tsx
            <span>You</span>
            {message.isVoice && <Mic size={9} color="#666" />}
```

Similarly, in the agent message section, find the agent name line (around line 152):

```tsx
          <span style={{ fontWeight: 500, color: '#777' }}>{agentName}</span>
```

Replace with:

```tsx
          <span style={{ fontWeight: 500, color: '#777' }}>{agentName}</span>
          {message.isVoice && <Mic size={9} color="#666" />}
```

- [ ] **Step 2: Commit**

```bash
git add neuro_web/components/chat/MessageBubble.tsx
git commit -m "feat(voice): add mic icon badge on voice-originated messages"
```

---

## Task 10: End-to-End Verification

- [ ] **Step 1: Verify backend starts cleanly**

```bash
cd /home/ubuntu/neurocomputer-dev && python -c "
from core.voice_manager import voice_manager, VoiceManager, InfinityBrainLLM
print('voice_manager OK')
print(f'Methods: start_call, end_call, is_active')
print(f'is_active test: {voice_manager.is_active(\"test\")}')
"
```

Expected:
```
voice_manager OK
Methods: start_call, end_call, is_active
is_active test: False
```

- [ ] **Step 2: Verify frontend builds**

```bash
cd /home/ubuntu/neurocomputer-dev/neuro_web && npx next build 2>&1 | tail -20
```

Expected: Build succeeds without type errors.

- [ ] **Step 3: Verify all new files exist**

```bash
ls -la neuro_web/hooks/useVoiceCall.ts neuro_web/components/chat/VoiceCallBar.tsx
```

Expected: Both files exist.

- [ ] **Step 4: Final commit with all changes**

If any uncommitted changes remain:

```bash
git add -A && git status
git commit -m "feat(voice): complete real-time voice call implementation (web)"
```

---

## Summary of Changes

| Component | What Changed |
|-----------|-------------|
| `core/voice_manager.py` | Full rewrite — conversation-tied sessions, transcript persistence, DataChannel events |
| `server.py` | New endpoints: `/voice/call`, `/voice/hangup`, `/voice/status/{cid}` |
| `neuro_web/services/api.ts` | Added `apiStartVoiceCall`, `apiEndVoiceCall`, `apiVoiceCallStatus` |
| `neuro_web/services/livekit.ts` | Added audio track management: `enableAudio`, `disableAudio`, remote audio handling |
| `neuro_web/store/chatSlice.ts` | Added `voiceCall` state, `interimTranscript`, new actions |
| `neuro_web/hooks/useVoiceCall.ts` | New hook — full call lifecycle management |
| `neuro_web/components/chat/VoiceCallBar.tsx` | New component — call indicator with controls |
| `neuro_web/components/chat/ChatInput.tsx` | Added phone call button |
| `neuro_web/components/chat/ChatPanel.tsx` | Added VoiceCallBar rendering |
| `neuro_web/providers/LiveKitProvider.tsx` | Handles `voice.*` DataChannel events |
| `neuro_web/components/chat/MessageBubble.tsx` | Mic icon badge for voice messages |
