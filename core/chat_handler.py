"""
Chat Handler - Manages LiveKit chat rooms and DataChannel messaging.

This module replaces the old WebSocket-based chat system with LiveKit DataChannel.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, Optional, Callable, Any

from livekit import rtc, api

from core.db import db
from core.brain import Brain

logger = logging.getLogger("chat_handler")

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")


class ChatMessage:
    """Represents a chat message."""
    
    def __init__(
        self,
        msg_type: str,
        sender: str,
        content: str = "",
        message_id: Optional[str] = None,
        audio_url: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict] = None,
        origin: Optional[str] = None,
    ):
        self.id = message_id or f"msg_{uuid.uuid4().hex[:12]}"
        self.type = msg_type
        self.sender = sender
        self.content = content
        self.audio_url = audio_url
        self.duration_ms = duration_ms
        self.metadata = metadata or {}
        self.timestamp = datetime.now().isoformat()
        self.origin = origin

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "type": self.type,
            "message_id": self.id,
            "text": self.content,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "audio_url": self.audio_url,
            "duration_ms": self.duration_ms,
        }
        if self.origin:
            d["origin"] = self.origin
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        return cls(
            msg_type=data.get("type", "text"),
            sender=data.get("sender", "user"),
            content=data.get("text", ""),
            message_id=data.get("message_id"),
            audio_url=data.get("audio_url"),
            duration_ms=data.get("duration_ms"),
            metadata=data.get("metadata"),
            origin=data.get("origin"),
        )


class ChatRoom:
    """Manages a single chat room via LiveKit."""
    
    def __init__(
        self,
        room_name: str,
        conversation_id: str,
        agent_id: str = "neuro",
    ):
        self.room_name = room_name
        self.conversation_id = conversation_id
        self.agent_id = agent_id
        
        self.room: Optional[rtc.Room] = None
        self.agent_room: Optional[rtc.Room] = None
        self.agent_identity = f"agent_{agent_id}"
        self.user_identity = f"user_{conversation_id}"
        
        self._brain: Optional[Brain] = None
        self._message_handlers: list[Callable[[ChatMessage], None]] = []
        self._connected = asyncio.Event()
        self._agent_started = False
        self._agent_lock = asyncio.Lock()
        self._message_lock = asyncio.Lock()
        self._agent_ready = asyncio.Event()

    async def connect(self):
        """Connect to the LiveKit room."""
        if not LIVEKIT_URL or not LIVEKIT_API_KEY:
            raise ValueError("LiveKit credentials missing")
        
        self.room = rtc.Room()
        
        async def on_data_received(data_packet: rtc.DataPacket):
            try:
                topic = data_packet.topic
                data = data_packet.data.decode("utf-8")
                logger.debug(f"Received data on topic '{topic}': {data[:100]}")
                
                msg_dict = json.loads(data)
                
                if topic == "chat_message":
                    msg = ChatMessage.from_dict(msg_dict)
                    if msg.sender == "user":
                        await self.handle_user_message(msg)
                    else:
                        await self.broadcast_to_user(msg)
                        
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {data[:100]}")
            except Exception as e:
                logger.error(f"Error handling data packet: {e}")
        
        self.room.on("data_received", on_data_received)
        
        async def on_connection_state_changed(state: rtc.ConnectionState):
            if state == rtc.ConnectionState.CONN_CONNECTED:
                logger.info(f"Chat room {self.room_name} connected")
                self._connected.set()
            elif state == rtc.ConnectionState.CONN_DISCONNECTED:
                logger.info(f"Chat room {self.room_name} disconnected")
                self._connected.clear()
        
        self.room.on("connection_state_changed", on_connection_state_changed)
        
        user_token = self._generate_token(self.user_identity, can_publish=True, can_subscribe=True)
        await self.room.connect(LIVEKIT_URL, user_token)
        
        logger.info(f"User connected to chat room {self.room_name}")

    async def connect_agent(self):
        """Connect agent to the chat room."""
        if not LIVEKIT_URL or not LIVEKIT_API_KEY:
            raise ValueError("LiveKit credentials missing")
        
        # Agent creates its own room connection to the same LiveKit room
        self.agent_room = rtc.Room()
        
        def on_data_received(data_packet: rtc.DataPacket):
            # Wrap async handling in asyncio.create_task
            asyncio.create_task(self._handle_data_packet(data_packet))
        
        self.agent_room.on("data_received", on_data_received)
        
        # Handle audio track subscriptions for voice messages
        audio_chunks = []
        
        def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
            logger.info(f"[Agent] Track subscribed: {track.sid}, kind: {track.kind}")
            if track.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(f"[Agent] Audio track received from {participant.identity}")
                
                @staticmethod
                def on_audio_data(data: rtc.AudioFrame):
                    audio_chunks.append(data)
                    logger.debug(f"[Agent] Audio frame received, samples: {len(data.data)}")
                
                track.start_capture()
                # Note: in production, you'd want proper audio capture callback
                
        self.agent_room.on("track_subscribed", on_track_subscribed)
        
        agent_token = self._generate_token(
            self.agent_identity, 
            can_publish=True, 
            can_subscribe=True,
            is_agent=True
        )
        
        await self.agent_room.connect(LIVEKIT_URL, agent_token)
        logger.info(f"Agent connected to chat room {self.room_name}")

        self._brain = Brain()
        self._agent_ready.set()

    async def _handle_data_packet(self, data_packet: rtc.DataPacket):
        """Handle incoming data packet asynchronously."""
        try:
            topic = data_packet.topic
            data = data_packet.data.decode("utf-8")
            logger.debug(f"[Agent] Received data on topic '{topic}': {data[:100]}")
            
            msg_dict = json.loads(data)
            
            if topic == "chat_message":
                msg = ChatMessage.from_dict(msg_dict)
                if msg.sender == "user":
                    await self.handle_user_message(msg)
            
            elif topic == "ocr_message":
                # Handle OCR message
                ocr_text = msg_dict.get("text", "")
                sender = msg_dict.get("sender", "user")
                if ocr_text and sender == "user":
                    logger.info(f"[Agent] Processing OCR: {ocr_text[:100]}")
                    await self.handle_ocr_message(ocr_text)
                    
        except json.JSONDecodeError:
            logger.warning(f"[Agent] Invalid JSON received: {data[:100] if data else 'empty'}")
        except Exception as e:
            logger.error(f"[Agent] Error handling data packet: {e}")

    async def handle_ocr_message(self, ocr_text: str):
        """Process OCR text and send response via LiveKit DataChannel only."""
        async with self._message_lock:
            logger.info(f"[Agent] Handling OCR message: {ocr_text[:100]}")

            # Save OCR to database for agent context
            await db.add_message(
                conversation_id=self.conversation_id,
                sender="user",
                msg_type="ocr",
                content=ocr_text,
            )

            # Wrap OCR with clear context that user is sharing their phone screen
            formatted_ocr = (
                f"[User is sharing text from their phone screen via OCR]\n"
                f"Screenshot/ screen content:\n"
                f"{ocr_text}\n"
                f"[/end screen content]\n\n"
                f"What would you like to help the user with this screen content?"
            )

            # Wait for agent/brain to be ready
            try:
                await asyncio.wait_for(self._agent_ready.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.error(f"[Agent] Brain not ready for OCR processing")

            # Process through brain - suppress hub publish, send response via DataChannel only
            if self._brain:
                self._brain._suppress_hub = True
                try:
                    response_text = await self._brain.handle(
                        cid=self.conversation_id,
                        user_text=formatted_ocr,
                        agent_id=self.agent_id,
                    )
                finally:
                    self._brain._suppress_hub = False

                if response_text:
                    # Save agent response to database
                    await db.add_message(
                        conversation_id=self.conversation_id,
                        sender="agent",
                        msg_type="text",
                        content=response_text,
                    )
                    # Send response via LiveKit DataChannel
                    agent_msg = ChatMessage(
                        msg_type="text",
                        sender="agent",
                        content=response_text,
                    )
                    await self.send_to_all(agent_msg, topic="agent_response")
                    logger.info(f"[Agent] OCR response sent via DataChannel: {response_text[:50]}")

    async def start_agent(self):
        """Start the agent for this chat room."""
        async with self._agent_lock:
            if self._agent_started:
                return
            self._agent_started = True
        await self.connect_agent()

    def _generate_token(
        self, 
        identity: str, 
        can_publish: bool = True, 
        can_subscribe: bool = True,
        is_agent: bool = False
    ) -> str:
        """Generate a LiveKit access token."""
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(identity)
        token.with_name(identity)
        token.with_grants(api.VideoGrants(
            room_join=True,
            room=self.room_name,
            can_publish=can_publish,
            can_subscribe=can_subscribe,
            agent=is_agent,
        ))
        return token.to_jwt()

    async def handle_user_message(self, msg: ChatMessage):
        """Process user message through the brain and send response."""
        async with self._message_lock:
            logger.info(f"Processing user message: {msg.content[:50]}")

            await db.add_message(
                conversation_id=self.conversation_id,
                sender="user",
                msg_type=msg.type,
                content=msg.content,
                audio_url=msg.audio_url,
                duration_ms=msg.duration_ms,
            )

            for handler in self._message_handlers:
                try:
                    handler(msg)
                except Exception as e:
                    logger.error(f"Message handler error: {e}")

            # Wait for agent/brain to be ready (max 10s)
            try:
                await asyncio.wait_for(self._agent_ready.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.error(f"[ChatRoom] Agent not ready after 10s for cid={self.conversation_id}")

            if self._brain and msg.type in ("text", "voice"):
                logger.info(f"[ChatRoom] Calling brain.handle for cid={self.conversation_id}")
                response_text = await self._brain.handle(
                    cid=self.conversation_id,
                    user_text=msg.content,
                    agent_id=self.agent_id,
                )
                logger.info(f"[ChatRoom] brain.handle returned: {response_text}")

                if response_text:
                    agent_msg = ChatMessage(
                        msg_type="text",
                        sender="agent",
                        content=response_text,
                        origin=msg.origin,
                    )
                    # Use the same ID for DB and DataChannel so TTS can update it
                    await db.add_message_with_id(
                        message_id=agent_msg.id,
                        conversation_id=self.conversation_id,
                        sender="agent",
                        msg_type="text",
                        content=response_text,
                    )
                    logger.info(f"[ChatRoom] Sending agent response via DataChannel: {response_text[:50]}")
                    await self.send_to_all(agent_msg, topic="agent_response")
                    logger.info(f"[ChatRoom] Done sending agent response")
                else:
                    logger.warning(f"[ChatRoom] brain.handle returned empty/None")

    async def send_to_user(self, msg: ChatMessage):
        """Send message to user participant."""
        await self.broadcast_to_user(msg)

    async def broadcast_to_user(self, msg: ChatMessage, topic: str = "chat_message"):
        """Broadcast message to the room."""
        if not self.agent_room:
            logger.warning("Cannot send message - agent room not connected")
            return
        
        try:
            payload = json.dumps(msg.to_dict(), default=str).encode("utf-8")
            logger.info(f"[Broadcast] Publishing to topic '{topic}', payload length: {len(payload)}")
            await self.agent_room.local_participant.publish_data(
                payload,
                reliable=True,
                topic=topic,
            )
            logger.info(f"[Broadcast] Successfully published message {msg.id}")
        except Exception as e:
            logger.error(f"[Broadcast] Error broadcasting message: {e}")

    async def send_to_all(self, msg: ChatMessage, topic: str = "chat_message"):
        """Alias for broadcast_to_user for clarity."""
        await self.broadcast_to_user(msg, topic)

    def on_message(self, handler: Callable[[ChatMessage], None]):
        """Register a message handler."""
        self._message_handlers.append(handler)

    async def disconnect(self):
        """Disconnect from the room."""
        if self.room:
            await self.room.disconnect()
            self.room = None
        if self.agent_room:
            await self.agent_room.disconnect()
            self.agent_room = None
        self._connected.clear()


class ChatManager:
    """Manages all chat rooms."""
    
    def __init__(self):
        self._rooms: Dict[str, ChatRoom] = {}
        self._lock = asyncio.Lock()
        
    async def get_or_create_room(
        self, 
        conversation_id: str, 
        agent_id: str = "neuro"
    ) -> ChatRoom:
        """Get existing room or create new one."""
        async with self._lock:
            if conversation_id in self._rooms:
                return self._rooms[conversation_id]
            
            room_name = f"chat-{conversation_id}"
            room = ChatRoom(
                room_name=room_name,
                conversation_id=conversation_id,
                agent_id=agent_id,
            )
            self._rooms[conversation_id] = room
            logger.info(f"Created chat room {room_name}")
            return room
    
    async def get_room(self, conversation_id: str) -> Optional[ChatRoom]:
        """Get existing room."""
        return self._rooms.get(conversation_id)
    
    async def close_room(self, conversation_id: str):
        """Close and remove a room."""
        async with self._lock:
            if conversation_id in self._rooms:
                room = self._rooms.pop(conversation_id)
                await room.disconnect()
                logger.info(f"Closed chat room for conversation {conversation_id}")

    async def generate_token(
        self,
        conversation_id: str,
        participant_name: str,
        is_agent: bool = False,
        agent_id: str = "neuro",
    ) -> dict:
        """Generate a token for a chat room."""
        room = await self.get_or_create_room(conversation_id, agent_id)

        # Start agent in background — don't block token generation.
        # handle_user_message() waits for _agent_ready before processing.
        if not room._agent_started:
            async def _safe_start():
                try:
                    await room.start_agent()
                except Exception as e:
                    logger.error(f"Failed to start agent for {conversation_id}: {e}")
            asyncio.create_task(_safe_start())
        
        identity = f"agent_{participant_name}" if is_agent else f"user_{participant_name}"
        token = room._generate_token(
            identity=identity,
            can_publish=True,
            can_subscribe=True,
            is_agent=is_agent,
        )
        
        return {
            "token": token,
            "url": LIVEKIT_URL,
            "room_name": room.room_name,
            "conversation_id": conversation_id,
        }


chat_manager = ChatManager()
