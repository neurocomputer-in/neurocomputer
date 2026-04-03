"""
Voice Manager - Optimized for ultra-low latency voice interactions.

Key optimizations:
1. Sarvam Streaming STT (WebSocket) - real-time interim results
2. ElevenLabs Streaming TTS - official plugin with auto_mode (sentence-based)
3. Semantic Turn Detection (livekit-plugins-turn-detector) - reduces false interruptions
4. Silero VAD tuned for low-latency detection
5. LLM response streamed token-by-token from Infinity Brain
"""

import asyncio
import os
import logging
import json
from typing import Optional, Dict
from dataclasses import dataclass

from livekit import rtc, api
from livekit.agents import (
    AgentSession,
    Agent,
    llm,
    ChatContext,
)
from livekit.plugins import openai, silero, elevenlabs

from core.brain import Brain
from core.pubsub import hub
from core.sarvam_stt import SarvamSTT

logger = logging.getLogger("voice-manager")

# API Keys from env (fallback to hardcoded for compatibility if env missing)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjzDR9eL")

@dataclass
class VoiceSession:
    """Tracks an active voice session."""
    room_name: str
    room: rtc.Room
    session: AgentSession
    brain: Brain
    conversation_id: str


class InfinityBrainLLM(llm.LLM):
    """
    Custom LLM adapter that routes to Infinity Brain instead of a Direct Model.
    This allows us to leverage LiveKit's AgentSession pipeline while using our internal logic.
    """
    
    def __init__(self, brain: Brain, conversation_id: str, room: rtc.Room):
        super().__init__()
        self._brain = brain
        self._cid = conversation_id
        self._room = room
    
    def chat(
        self,
        *,
        chat_ctx: ChatContext,
        tools: list | None = None,
        conn_options = None,
        **kwargs,
    ) -> "llm.LLMStream":
        """Process chat through Infinity Brain."""
        # Get latest user message
        user_message = ""
        for msg in reversed(chat_ctx.items):
            if msg.role == "user":
                user_message = msg.text_content
                break
        
        if not user_message:
            user_message = "Hello" # Fallback
        
        logger.info(f"[Voice] Input: {user_message}")
        
        return InfinityBrainStream(
            llm=self,
            brain=self._brain,
            conversation_id=self._cid,
            room=self._room,
            user_message=user_message,
            chat_ctx=chat_ctx,
            tools=tools or [],
            conn_options=conn_options,
        )


class InfinityBrainStream(llm.LLMStream):
    """LLMStream that bridges LiveKit to Infinity Brain."""
    
    def __init__(
        self,
        *,
        llm: InfinityBrainLLM,
        brain: Brain,
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
        self._brain = brain
        self._cid = conversation_id
        self._room = room
        self._user_message = user_message
    
    async def _publish_data(self, topic: str, data: any):
        """Publish events to the UI via LiveKit data channel."""
        if not self._room or not self._room.local_participant:
            return
        
        try:
            payload = json.dumps({"topic": topic, "data": data})
            await self._room.local_participant.publish_data(
                payload, 
                reliable=True,
                topic="chat_message" 
            )
        except Exception as e:
            logger.error(f"[Voice] UI publish error: {e}")
    
    async def _run(self) -> None:
        """Called by AgentSession when LLM is needed."""
        try:
            queue = hub.queue(self._cid)
            
            # Send initial USER message to UI for immediate feedback
            await self._publish_data("user", self._user_message)

            # Start Brain processing
            await self._brain.handle(self._cid, self._user_message)
            
            response = ""
            timeout = 30
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                    if remaining <= 0:
                        break
                    
                    msg = await asyncio.wait_for(queue.get(), timeout=remaining)
                    title = msg.get("topic")
                    data  = msg.get("data")
                    
                    # End turn signals
                    if title in ("task.done", "node.done") and response:
                        break
                    
                    # Assistant Transcript Chunks (sent to TTS and UI)
                    if title == "assistant" and isinstance(data, str) and data:
                        response += data
                        await self._publish_data("assistant", data)
                        
                        # Send chunk to TTS engine
                        self._event_ch.send_nowait(
                            llm.ChatChunk(
                                id="infinity-res",
                                delta=llm.ChoiceDelta(role="assistant", content=data)
                            )
                        )
                    
                except asyncio.TimeoutError:
                    break
            
            if not response:
                placeholder = "I'm thinking..."
                self._event_ch.send_nowait(
                    llm.ChatChunk(id="err", delta=llm.ChoiceDelta(role="assistant", content=placeholder))
                )
            
            logger.info(f"[Voice] Brain response complete: {len(response)} chars")
            
        except Exception as e:
            logger.error(f"[Voice] Brain stream error: {e}")


class VoiceManager:
    """
    Manages high-performance LiveKit voice sessions with ElevenLabs and Sarvam.
    """
    
    def __init__(self):
        self._sessions: Dict[str, VoiceSession] = {}
        self._lk_api: Optional[api.LiveKitAPI] = None
        
        self._url = os.getenv("LIVEKIT_URL", "")
        self._api_key = os.getenv("LIVEKIT_API_KEY", "")
        self._api_secret = os.getenv("LIVEKIT_API_SECRET", "")
    
    def _generate_token(self, room_name: str, identity: str, is_agent: bool = False) -> str:
        token = api.AccessToken(self._api_key, self._api_secret)
        token.with_identity(identity)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=room_name,
            can_publish=True,
            can_subscribe=True,
            agent=is_agent,
        ))
        return token.to_jwt()
    
    async def create_session(self, user_id: str) -> dict:
        """Create an optimized voice session."""
        if not self._url or not self._api_key:
            raise ValueError("LiveKit credentials missing")
        
        if user_id in self._sessions:
            await self.end_session(user_id)
        
        room_name = f"voice-{user_id}"
        conversation_id = f"voice_{user_id}"
        
        # Room and Agent setup
        room = rtc.Room()
        agent_token = self._generate_token(room_name, "infinity-agent", is_agent=True)
        await room.connect(self._url, agent_token)
        
        brain = Brain()
        agent = Agent(instructions="You are Infinity, a low-latency AI voice agent.")
        
        # ─── OPTIMIZED PIPELINE CONFIGURATION ───
        session = AgentSession(
            llm=InfinityBrainLLM(brain, conversation_id, room),
            
            # 1. TUNED VAD (Silero)
            vad=silero.VAD.load(
                min_speech_duration=0.05,      # React faster to speech start
                min_silence_duration=0.25,     # Detected silence faster
                prefix_padding_duration=0.15,
                activation_threshold=0.35,     # Filter slightly more background noise
            ),
            
            # 2. SARVAM STREAMING STT
            stt=SarvamSTT(
                language="en-IN",
                model="saaras:v3"
            ),
            
            # 3. ELEVENLABS STREAMING TTS (Official Plugin)
            tts=elevenlabs.TTS(
                voice_id=ELEVENLABS_VOICE_ID,
                model="eleven_flash_v2_5",     # High speed, legacy model
                api_key=ELEVENLABS_API_KEY,
                auto_mode=True                 # Sentence-based chunking
            ),
            
        )
        
        asyncio.create_task(self._run_session(session, room, agent))
        
        self._sessions[user_id] = VoiceSession(
            room_name=room_name,
            room=room,
            session=session,
            brain=brain,
            conversation_id=conversation_id,
        )
        
        return {
            "token": self._generate_token(room_name, f"user-{user_id}"),
            "room_name": room_name,
            "url": self._url,
        }
    
    async def _run_session(self, session: AgentSession, room: rtc.Room, agent: Agent):
        try:
            await session.start(room=room, agent=agent)
            while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"[Voice] Session error: {e}")
        finally:
            await room.disconnect()
    
    async def end_session(self, user_id: str):
        if user_id in self._sessions:
            s = self._sessions.pop(user_id)
            await s.room.disconnect()

voice_manager = VoiceManager()
