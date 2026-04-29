"""SentencePump: LiveKit LLMStream that reads Brain hub queue and emits
sentence-chunked ChatChunks. Replaces InfinityBrainStream.

Each emitted ChatChunk is a complete sentence so downstream TTS gets
clean prosody and low first-byte latency.
"""
import asyncio
import json
import logging
import uuid

from livekit import rtc
from livekit.agents import llm, ChatContext

from core.brain import Brain
from core.pubsub import hub
from core.db import db
from core.voice.sentence_boundary import extract_sentence

logger = logging.getLogger("voice-pump")

WATCHDOG_S = 15.0  # max seconds between hub events before we give up
APOLOGY = "Sorry, this is taking too long. Try again."


class SentencePumpLLM(llm.LLM):
    """LLM adapter that wraps Brain → SentencePump streams."""

    def __init__(self, brain: Brain, conversation_id: str, agent_id: str, room: rtc.Room):
        super().__init__()
        self._brain = brain
        self._cid = conversation_id
        self._agent_id = agent_id
        self._room = room

    def chat(self, *, chat_ctx: ChatContext, tools=None, conn_options=None, **kwargs):
        user_message = ""
        for msg in reversed(chat_ctx.items):
            if msg.role == "user":
                user_message = msg.text_content
                break
        if not user_message:
            user_message = "Hello"
        logger.info(f"[Voice] User said: {user_message[:100]}")
        return SentencePump(
            llm=self, brain=self._brain, conversation_id=self._cid,
            agent_id=self._agent_id, room=self._room,
            user_message=user_message, chat_ctx=chat_ctx,
            tools=tools or [], conn_options=conn_options,
        )


class SentencePump(llm.LLMStream):
    """Reads Brain hub queue, buffers chunks, emits sentence-aligned ChatChunks."""

    def __init__(self, *, llm, brain, conversation_id, agent_id, room,
                 user_message, chat_ctx, tools, conn_options):
        from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
        super().__init__(
            llm=llm, chat_ctx=chat_ctx, tools=tools,
            conn_options=conn_options or DEFAULT_API_CONNECT_OPTIONS,
        )
        self._brain = brain
        self._cid = conversation_id
        self._agent_id = agent_id
        self._room = room
        self._user_message = user_message
        self._captured_chunks = []  # for tests; harmless in prod
        self._done = asyncio.Event()

    @classmethod
    def for_test(cls, *, brain, conversation_id, agent_id, user_message):
        """Constructor without real LiveKit objects, for unit tests.

        Cancels the auto-spawned _task and _metrics_task from LLMStream.__init__
        so the test can call _run() directly without double-execution.
        """
        from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
        instance = cls.__new__(cls)
        # Initialize LLMStream parent with minimal stubs
        llm.LLMStream.__init__(
            instance,
            llm=_MagicLLMStub(),
            chat_ctx=ChatContext(),
            tools=[],
            conn_options=DEFAULT_API_CONNECT_OPTIONS,
        )
        # LLMStream.__init__ spawns _task and _metrics_task that would call _run()
        # automatically. Cancel them so tests can drive _run() directly.
        instance._task.cancel()
        instance._metrics_task.cancel()
        instance._brain = brain
        instance._cid = conversation_id
        instance._agent_id = agent_id
        instance._room = None
        instance._user_message = user_message
        instance._captured_chunks = []
        instance._done = asyncio.Event()
        return instance

    async def _publish_voice_event(self, topic: str, data: dict):
        if not self._room or not self._room.local_participant:
            return
        try:
            payload = json.dumps({"topic": topic, **data})
            await self._room.local_participant.publish_data(
                payload.encode("utf-8"), reliable=True, topic=topic,
            )
        except Exception as e:
            logger.error(f"[Voice] DataChannel publish error: {e}")

    def _emit(self, msg_id: str, sentence: str):
        """Emit one sentence as a ChatChunk to the LiveKit TTS pipeline."""
        chunk = llm.ChatChunk(
            id=msg_id,
            delta=llm.ChoiceDelta(role="assistant", content=sentence),
        )
        self._captured_chunks.append(chunk)
        try:
            self._event_ch.send_nowait(chunk)
        except Exception as e:
            # In unit tests _event_ch may not be wired; tests inspect _captured_chunks
            logger.debug(f"[Voice] _event_ch send skipped: {e}")

    async def _run(self) -> None:
        # Read WATCHDOG_S at runtime so tests can patch the module-level name
        import core.voice.sentence_pump as _self_module
        watchdog_s = _self_module.WATCHDOG_S

        try:
            user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            await self._publish_voice_event("voice.user_transcript", {
                "text": self._user_message, "is_final": True,
                "message_id": user_msg_id,
            })
            await db.add_message(
                conversation_id=self._cid, sender="user",
                msg_type="voice", content=self._user_message,
            )

            queue = hub.queue(self._cid)
            self._brain._suppress_dc = True
            try:
                # Brain.handle launches a background DAG task and returns quickly
                await self._brain.handle(
                    self._cid, self._user_message, agent_id=self._agent_id,
                    is_voice=True,
                )
            finally:
                self._brain._suppress_dc = False

            buf = ""
            full_response = ""
            agent_msg_id = f"msg_{uuid.uuid4().hex[:12]}"

            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=watchdog_s)
                except asyncio.TimeoutError:
                    logger.warning(f"[Voice] Watchdog fired after {watchdog_s}s")
                    self._emit(agent_msg_id, APOLOGY)
                    full_response += APOLOGY
                    break

                topic = msg.get("topic")
                data = msg.get("data")

                if topic == "assistant" and isinstance(data, str) and data:
                    buf += data
                    await self._publish_voice_event("voice.agent_transcript", {
                        "chunk": data, "done": False,
                    })
                    while True:
                        result = extract_sentence(buf)
                        if result is None:
                            break
                        sentence, buf = result
                        self._emit(agent_msg_id, sentence)
                        full_response += sentence

                elif topic in ("task.done", "node.done"):
                    if buf.strip():
                        self._emit(agent_msg_id, buf)
                        full_response += buf
                        buf = ""
                    if topic == "task.done" or full_response:
                        break

            if full_response:
                await self._publish_voice_event("voice.agent_transcript", {
                    "text": full_response, "done": True,
                    "message_id": agent_msg_id,
                })
                await db.add_message(
                    conversation_id=self._cid, sender="agent",
                    msg_type="voice", content=full_response,
                )

            logger.info(f"[Voice] Response complete: {len(full_response)} chars")

        except Exception as e:
            logger.error(f"[Voice] SentencePump error: {e}", exc_info=True)
        finally:
            self._done.set()


class _MagicLLMStub(llm.LLM):
    """Test-only stub LLM parent for SentencePump.for_test()."""

    def chat(self, **kwargs):  # pragma: no cover
        pass
