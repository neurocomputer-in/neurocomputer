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
from dataclasses import dataclass, field

import aiohttp

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    llm,
    ChatContext,
)
from livekit.agents.voice.room_io import RoomOptions
from livekit.plugins import silero, elevenlabs, openai

from core.brain import Brain
from core.pubsub import hub
from core.db import db
from core.sarvam_stt import SarvamSTT
from core import tmux_manager

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
    _http_session: Optional[aiohttp.ClientSession] = None


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

            # Process through Brain — suppress DataChannel broadcast
            # since voice pipeline handles its own delivery
            queue = hub.queue(self._cid)
            self._brain._suppress_dc = True
            try:
                await self._brain.handle(
                    self._cid, self._user_message, agent_id=self._agent_id,
                    is_voice=True,
                )
            finally:
                self._brain._suppress_dc = False

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


class TmuxEchoLLM(llm.LLM):
    """LLM stand-in for terminal-mode voice calls. Skips Brain entirely:
    each user transcript is written verbatim into the tmux session's
    stdin and is also echoed to the frontend via DataChannel so the UI
    can display it. No agent reply is produced (stream is empty)."""

    def __init__(self, tmux_session: str, conversation_id: str, room: rtc.Room):
        super().__init__()
        self._tmux = tmux_session
        self._cid = conversation_id
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
        logger.info(f"[Voice/term] User said: {user_message[:100]!r} → tmux {self._tmux}")
        return TmuxEchoStream(
            llm=self,
            tmux_session=self._tmux,
            conversation_id=self._cid,
            room=self._room,
            user_message=user_message,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )


class TmuxEchoStream(llm.LLMStream):
    """Writes the user transcript into tmux stdin and closes empty."""

    def __init__(
        self,
        *,
        llm: TmuxEchoLLM,
        tmux_session: str,
        conversation_id: str,
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
        self._tmux = tmux_session
        self._cid = conversation_id
        self._room = room
        self._user_message = (user_message or "").strip()

    async def _publish(self, topic: str, data: dict):
        if not self._room or not self._room.local_participant:
            return
        try:
            payload = json.dumps({"topic": topic, **data})
            await self._room.local_participant.publish_data(
                payload.encode("utf-8"), reliable=True, topic=topic,
            )
        except Exception as e:
            logger.warning(f"[Voice/term] DataChannel publish failed: {e}")

    async def _run(self) -> None:
        try:
            if not self._user_message:
                return
            msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            # Echo transcript so the UI can show what the terminal heard.
            await self._publish("voice.user_transcript", {
                "text": self._user_message,
                "is_final": True,
                "message_id": msg_id,
            })
            # Pipe to tmux stdin. send_keys is synchronous but fast;
            # run in a thread so we don't block the event loop.
            await asyncio.to_thread(
                tmux_manager.send_keys, self._tmux, self._user_message, True,
            )
        except Exception as e:
            logger.error(f"[Voice/term] pipe error: {e}", exc_info=True)


def _conversation_meta(conversation_id: str) -> dict:
    """Read the conv JSON on disk to detect type + tmux_session. Non-fatal."""
    from pathlib import Path
    fp = Path.cwd() / "conversations" / f"{conversation_id}.json"
    try:
        with open(fp, "r") as f:
            return json.load(f)
    except Exception:
        return {}


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
        """Start a voice call for a conversation. Returns token for client.

        Idempotent: if a healthy session already exists for this
        conversation, return a fresh client token for that same room rather
        than tearing it down. Prevents rapid double-clicks / React Strict
        Mode double-mount from cancelling a live call.
        """
        if not self._url or not self._api_key:
            raise ValueError("LiveKit credentials missing")

        # Reuse an existing healthy session for the same conversation.
        existing = self._sessions.get(conversation_id)
        if existing and existing._task and not existing._task.done():
            logger.info(
                f"[Voice] Reusing existing voice session for {conversation_id}"
            )
            user_token = self._generate_token(
                existing.room_name,
                f"voice-user-{conversation_id}",
            )
            return {
                "token": user_token,
                "room_name": existing.room_name,
                "url": self._url,
                "conversation_id": conversation_id,
            }

        # Stale session (task finished/errored) — clean it up before starting fresh.
        if conversation_id in self._sessions:
            await self.end_call(conversation_id)

        room_name = f"voice-{conversation_id}"
        room = rtc.Room()

        # Debug: log participant and track events
        @room.on("participant_connected")
        def _on_participant(participant: rtc.RemoteParticipant):
            logger.info(f"[Voice] Participant joined: {participant.identity}, kind={participant.kind}")

        @room.on("track_subscribed")
        def _on_track(track: rtc.Track, publication, participant: rtc.RemoteParticipant):
            logger.info(f"[Voice] Track subscribed: kind={track.kind}, participant={participant.identity}")

        @room.on("track_published")
        def _on_track_pub(publication, participant: rtc.RemoteParticipant):
            logger.info(f"[Voice] Track published: kind={publication.kind}, participant={participant.identity}")

        agent_token = self._generate_token(
            room_name, f"voice-agent-{conversation_id}", is_agent=True
        )
        await room.connect(self._url, agent_token)
        logger.info(f"[Voice] Agent connected to room {room_name}, participants: {len(room.remote_participants)}")

        brain = Brain()

        # Pick pipeline mode from conversation type on disk.
        meta = _conversation_meta(conversation_id)
        is_terminal = (meta.get("type") == "terminal")
        tmux_session = meta.get("tmux_session") or None

        if is_terminal and tmux_session:
            agent = Agent(
                instructions=(
                    "You are a speech-to-text bridge into a terminal. "
                    "Speak nothing — your user hears the shell output directly."
                )
            )
            llm_impl = TmuxEchoLLM(tmux_session, conversation_id, room)
            logger.info(
                f"[Voice] Pipeline: VAD → STT → tmux(send-keys) [terminal mode, "
                f"session={tmux_session}]"
            )
        else:
            agent = Agent(
                instructions="You are Neuro, a helpful AI voice assistant. Keep responses concise and conversational."
            )
            llm_impl = InfinityBrainLLM(brain, conversation_id, agent_id, room)
            logger.info("[Voice] Pipeline: Silero VAD → OpenAI Whisper STT → Brain → OpenAI TTS")

        http_session = aiohttp.ClientSession()

        session = AgentSession(
            llm=llm_impl,
            vad=silero.VAD.load(
                min_speech_duration=0.05,
                min_silence_duration=0.3,
                prefix_padding_duration=0.2,
                activation_threshold=0.25,
            ),
            stt=openai.STT(model="whisper-1"),
            tts=openai.TTS(model="gpt-4o-mini-tts", voice="nova"),
        )

        # Publish voice activity states to frontend
        async def _pub_state(state: str):
            try:
                payload = json.dumps({"topic": "voice.activity", "state": state})
                await room.local_participant.publish_data(
                    payload.encode("utf-8"), reliable=True, topic="voice.activity"
                )
            except Exception:
                pass

        @session.on("user_started_speaking")
        def _on_speak_start():
            logger.info("[Voice] VAD: user started speaking")
            asyncio.create_task(_pub_state("listening"))

        @session.on("user_stopped_speaking")
        def _on_speak_stop():
            logger.info("[Voice] VAD: user stopped speaking")
            asyncio.create_task(_pub_state("thinking"))

        @session.on("agent_started_speaking")
        def _on_agent_speak():
            logger.info("[Voice] Agent started speaking")
            asyncio.create_task(_pub_state("speaking"))

        @session.on("agent_stopped_speaking")
        def _on_agent_stop():
            logger.info("[Voice] Agent stopped speaking")
            asyncio.create_task(_pub_state("idle"))

        task = asyncio.create_task(self._run_session(session, room, agent, conversation_id))

        vs = VoiceSession(
            conversation_id=conversation_id,
            agent_id=agent_id,
            room_name=room_name,
            room=room,
            session=session,
            brain=brain,
            _task=task,
            _http_session=http_session,
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
        self, session: AgentSession, room: rtc.Room, agent: Agent,
        conversation_id: str,
    ):
        try:
            result = await session.start(
                room=room,
                agent=agent,
                room_options=RoomOptions(
                    close_on_disconnect=False,
                    delete_room_on_close=False,
                ),
            )
            logger.info(f"[Voice] session.start() returned: {result}")

            # Keep the task alive — wait for session close or room disconnect
            close_event = asyncio.Event()

            @session.on("close")
            def _on_close():
                logger.info("[Voice] AgentSession closed")
                close_event.set()

            @room.on("disconnected")
            def _on_disconnected():
                logger.info("[Voice] Room disconnected")
                close_event.set()

            await close_event.wait()
            logger.info(f"[Voice] Session ended for {conversation_id}")

        except asyncio.CancelledError:
            logger.info("[Voice] Session task cancelled")
        except Exception as e:
            logger.error(f"[Voice] Session error: {e}", exc_info=True)
        finally:
            self._sessions.pop(conversation_id, None)
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

        if vs._http_session:
            try:
                await vs._http_session.close()
            except Exception:
                pass

    def is_active(self, conversation_id: str) -> bool:
        """Check if a voice call is active for a conversation."""
        return conversation_id in self._sessions


voice_manager = VoiceManager()
