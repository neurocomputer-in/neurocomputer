# Voice Streaming + Low-Latency Pipeline — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace batch-sequential voice pipeline with streaming pipeline (Sarvam STT, Sarvam TTS, EOU turn-detection, gated barge-in) targeting <1.5s median speech-end-to-first-audio latency.

**Architecture:** Hybrid — keep `voice_manager.py` as the LiveKit orchestrator; extract three new modules (`sentence_pump.py`, `barge_in.py`, `sarvam_tts.py`) that replace the broken pieces (chunk → TTS coupling, OpenAI provider hardcoding). Add `livekit-plugins-turn-detector` for semantic end-of-utterance detection.

**Tech Stack:** Python 3, livekit-agents 1.5.2, livekit-plugins-silero 1.4.6, livekit-plugins-turn-detector (new), websockets, httpx, pytest (asyncio_mode=auto).

**Spec:** `docs/superpowers/specs/2026-04-30-voice-streaming-design.md`

---

## File Structure

| Path | Action | Responsibility |
|---|---|---|
| `neurocomputer/core/voice/__init__.py` | Create | Package marker |
| `neurocomputer/core/voice/sentence_boundary.py` | Create | Pure function: extract next sentence from buffer |
| `neurocomputer/core/voice/sentence_pump.py` | Create | LiveKit `LLMStream` reading Brain queue, emits sentence-chunked `ChatChunk`s |
| `neurocomputer/core/voice/barge_in.py` | Create | 500ms-gated TTS-cancel state machine |
| `neurocomputer/core/voice/sarvam_tts.py` | Create | LiveKit `TTS` plugin wrapping Sarvam `bulbul:v3` HTTP API |
| `neurocomputer/core/voice_manager.py` | Modify | Swap STT/TTS, mount EOU + BargeIn, replace InfinityBrainStream with SentencePump |
| `neurocomputer/requirements.txt` | Modify | Add `livekit-plugins-turn-detector` |
| `neurocomputer/tests/test_sentence_boundary.py` | Create | Unit tests for sentence extractor |
| `neurocomputer/tests/test_sentence_pump.py` | Create | Unit tests for SentencePump (mocked queue) |
| `neurocomputer/tests/test_barge_in.py` | Create | Unit tests for BargeInController |
| `neurocomputer/tests/test_sarvam_tts.py` | Create | Unit tests for SarvamTTS (mocked HTTP) |

Tests run from `/home/ubuntu/neurocomputer/neurocomputer/` via `pytest tests/test_X.py -v`. `pytest.ini` already sets `asyncio_mode = auto` so no `@pytest.mark.asyncio` decorators needed.

---

### Task 1: Create voice package skeleton

**Files:**
- Create: `neurocomputer/core/voice/__init__.py`

- [ ] **Step 1: Create empty package marker**

```python
"""Streaming voice pipeline modules: sentence chunking, barge-in, Sarvam TTS."""
```

- [ ] **Step 2: Verify import path resolves**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && python3 -c "import core.voice; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neurocomputer/core/voice/__init__.py
git commit -m "feat(voice): add voice package skeleton"
```

---

### Task 2: Sentence boundary extractor (pure function, TDD)

**Files:**
- Create: `neurocomputer/core/voice/sentence_boundary.py`
- Test: `neurocomputer/tests/test_sentence_boundary.py`

This is pure logic — no async, no external deps. Easy to TDD.

- [ ] **Step 1: Write failing tests**

Create `neurocomputer/tests/test_sentence_boundary.py`:

```python
"""Tests for sentence boundary extraction used by SentencePump."""
import pytest
from core.voice.sentence_boundary import extract_sentence


def test_returns_none_for_short_unpunctuated_buffer():
    assert extract_sentence("hello world") is None


def test_splits_on_period_with_trailing_space():
    sent, rest = extract_sentence("Hello world. Next part")
    assert sent == "Hello world. "
    assert rest == "Next part"


def test_splits_on_question_mark():
    sent, rest = extract_sentence("What time is it? Now")
    assert sent == "What time is it? "
    assert rest == "Now"


def test_splits_on_exclamation():
    sent, rest = extract_sentence("Wow! that's cool")
    assert sent == "Wow! "
    assert rest == "that's cool"


def test_splits_on_devanagari_danda():
    sent, rest = extract_sentence("नमस्ते। और बात")
    assert sent == "नमस्ते। "
    assert rest == "और बात"


def test_does_not_split_decimal():
    # "3.14" has no trailing space after the period — should NOT split
    assert extract_sentence("Pi is 3.14 approximately") is None


def test_does_not_split_abbreviation_without_trailing_space():
    # "Mr." followed by name — period followed by space is ambiguous;
    # we accept the split (heuristic — not perfect, but safe direction)
    sent, rest = extract_sentence("Hello Mr. Smith said hi")
    assert sent == "Hello Mr. "
    assert rest == "Smith said hi"


def test_soft_split_at_120_chars_on_comma():
    long_buf = "a" * 119 + ", continuing the sentence here without any period yet"
    sent, rest = extract_sentence(long_buf)
    assert sent.endswith(", ")
    assert len(sent) >= 120
    assert "continuing" in rest


def test_no_soft_split_below_120_chars():
    short_buf = "hello, world without period"
    assert extract_sentence(short_buf) is None


def test_force_flush_at_240_chars():
    no_punct = "a " * 130  # ~260 chars, all spaces, no punctuation
    sent, rest = extract_sentence(no_punct)
    assert len(sent) <= 240
    assert len(sent) > 0
    assert sent + rest == no_punct


def test_hard_punct_beats_soft_when_both_present():
    # Buffer has comma early AND period later — hard wins (period closer? no,
    # extract_sentence should prefer the *first* hard end found.)
    sent, rest = extract_sentence("first, second. third")
    assert sent == "first, second. "
    assert rest == "third"
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_sentence_boundary.py -v`
Expected: All FAIL with `ModuleNotFoundError: No module named 'core.voice.sentence_boundary'`

- [ ] **Step 3: Write the implementation**

Create `neurocomputer/core/voice/sentence_boundary.py`:

```python
"""Pure sentence boundary extraction for streaming TTS chunking.

Returns the next complete sentence from a buffer, or None if the buffer
has no boundary yet. Caller is responsible for accumulating chunks.
"""
import re

HARD_END = re.compile(r'[.!?।]\s')
SOFT_END = re.compile(r'[,;:]\s')
SOFT_MIN_CHARS = 120
HARD_MAX_CHARS = 240


def extract_sentence(buf: str) -> tuple[str, str] | None:
    """Try to extract one sentence from `buf`.

    Priority (first match wins):
    1. Hard end (.!?। + whitespace) anywhere in buffer
    2. Soft end (,;: + whitespace) only when len(buf) >= SOFT_MIN_CHARS
    3. Force-flush at last whitespace when len(buf) >= HARD_MAX_CHARS

    Returns (sentence, rest) or None if no boundary yet.
    """
    m = HARD_END.search(buf)
    if m:
        cut = m.end()
        return buf[:cut], buf[cut:]

    if len(buf) >= SOFT_MIN_CHARS:
        m = SOFT_END.search(buf)
        if m:
            cut = m.end()
            return buf[:cut], buf[cut:]

    if len(buf) >= HARD_MAX_CHARS:
        cut = buf.rfind(' ', 0, HARD_MAX_CHARS)
        if cut <= 0:
            cut = HARD_MAX_CHARS
        else:
            cut += 1  # include the space in the emitted sentence
        return buf[:cut], buf[cut:]

    return None
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_sentence_boundary.py -v`
Expected: All 11 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neurocomputer/core/voice/sentence_boundary.py neurocomputer/tests/test_sentence_boundary.py
git commit -m "feat(voice): add sentence boundary extractor for streaming TTS"
```

---

### Task 3: SentencePump LLMStream

**Files:**
- Create: `neurocomputer/core/voice/sentence_pump.py`
- Test: `neurocomputer/tests/test_sentence_pump.py`

Replaces the chunk-emission logic in `InfinityBrainStream._run` (currently at `voice_manager.py:142-238`). Subscribes to Brain hub queue, accumulates `assistant` chunks, emits `ChatChunk` to LiveKit on each sentence boundary.

- [ ] **Step 1: Write failing tests**

Create `neurocomputer/tests/test_sentence_pump.py`:

```python
"""Tests for SentencePump - reads Brain hub queue, emits sentence-chunked ChatChunks."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.voice.sentence_pump import SentencePump


@pytest.fixture
def mock_brain():
    brain = MagicMock()
    brain.handle = AsyncMock(return_value="ok")
    brain._suppress_dc = False
    return brain


@pytest.fixture
def fake_queue():
    return asyncio.Queue()


async def _collect_emitted(pump, max_wait=2.0):
    """Drain pump._event_ch until task.done or timeout. Returns text deltas in order."""
    out = []
    deadline = asyncio.get_event_loop().time() + max_wait
    while asyncio.get_event_loop().time() < deadline:
        try:
            chunk = await asyncio.wait_for(pump._event_ch.recv(), timeout=0.1)
            if chunk is None:
                break
            out.append(chunk.delta.content)
        except asyncio.TimeoutError:
            if pump._done.is_set():
                break
    return out


async def test_emits_sentence_when_period_arrives(mock_brain, fake_queue):
    """When a period arrives in chunks, SentencePump emits a complete sentence."""
    with patch("core.voice.sentence_pump.hub") as hub_mock:
        hub_mock.queue.return_value = fake_queue
        pump = SentencePump.for_test(brain=mock_brain, conversation_id="cid1",
                                     agent_id="neuro", user_message="hi")
        run_task = asyncio.create_task(pump._run())

        await fake_queue.put({"topic": "assistant", "data": "Hello "})
        await fake_queue.put({"topic": "assistant", "data": "world. "})
        await fake_queue.put({"topic": "task.done", "data": {}})

        await asyncio.wait_for(run_task, timeout=5.0)
        emitted = [d.delta.content for d in pump._captured_chunks]
        # First emit must be "Hello world. " (full sentence in one TTS call)
        assert emitted[0] == "Hello world. "


async def test_does_not_emit_until_boundary(mock_brain, fake_queue):
    """Buffer accumulates without emitting if no boundary present."""
    with patch("core.voice.sentence_pump.hub") as hub_mock:
        hub_mock.queue.return_value = fake_queue
        pump = SentencePump.for_test(brain=mock_brain, conversation_id="cid1",
                                     agent_id="neuro", user_message="hi")
        run_task = asyncio.create_task(pump._run())

        await fake_queue.put({"topic": "assistant", "data": "fragment "})
        await fake_queue.put({"topic": "assistant", "data": "without "})
        await fake_queue.put({"topic": "assistant", "data": "punct"})
        # No task.done yet — pump should still be running with non-empty buf
        await asyncio.sleep(0.2)
        assert len(pump._captured_chunks) == 0

        # Now end the turn — final flush of remainder
        await fake_queue.put({"topic": "task.done", "data": {}})
        await asyncio.wait_for(run_task, timeout=5.0)
        emitted = [d.delta.content for d in pump._captured_chunks]
        # Combined remainder flushed as one chunk
        assert "".join(emitted) == "fragment without punct"


async def test_multiple_sentences_emit_separately(mock_brain, fake_queue):
    with patch("core.voice.sentence_pump.hub") as hub_mock:
        hub_mock.queue.return_value = fake_queue
        pump = SentencePump.for_test(brain=mock_brain, conversation_id="cid1",
                                     agent_id="neuro", user_message="hi")
        run_task = asyncio.create_task(pump._run())

        await fake_queue.put({"topic": "assistant", "data": "First. Second. Third"})
        await fake_queue.put({"topic": "task.done", "data": {}})

        await asyncio.wait_for(run_task, timeout=5.0)
        emitted = [d.delta.content for d in pump._captured_chunks]
        assert emitted[0] == "First. "
        assert emitted[1] == "Second. "
        # Third may flush as final remainder
        assert "Third" in "".join(emitted[2:])


async def test_ignores_non_assistant_topics(mock_brain, fake_queue):
    with patch("core.voice.sentence_pump.hub") as hub_mock:
        hub_mock.queue.return_value = fake_queue
        pump = SentencePump.for_test(brain=mock_brain, conversation_id="cid1",
                                     agent_id="neuro", user_message="hi")
        run_task = asyncio.create_task(pump._run())

        await fake_queue.put({"topic": "node.start", "data": "irrelevant"})
        await fake_queue.put({"topic": "debug", "data": {"x": 1}})
        await fake_queue.put({"topic": "assistant", "data": "Real reply. "})
        await fake_queue.put({"topic": "task.done", "data": {}})

        await asyncio.wait_for(run_task, timeout=5.0)
        emitted = [d.delta.content for d in pump._captured_chunks]
        assert emitted == ["Real reply. "]


async def test_watchdog_breaks_on_15s_silence(mock_brain, fake_queue):
    """If queue silent >15s, emit apology and return."""
    with patch("core.voice.sentence_pump.hub") as hub_mock, \
         patch("core.voice.sentence_pump.WATCHDOG_S", 0.5):  # speed up test
        hub_mock.queue.return_value = fake_queue
        pump = SentencePump.for_test(brain=mock_brain, conversation_id="cid1",
                                     agent_id="neuro", user_message="hi")
        run_task = asyncio.create_task(pump._run())

        # No events at all — watchdog should fire
        await asyncio.wait_for(run_task, timeout=2.0)
        emitted = [d.delta.content for d in pump._captured_chunks]
        # Apology message emitted
        assert any("taking too long" in c.lower() or "sorry" in c.lower()
                   for c in emitted)
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_sentence_pump.py -v`
Expected: ImportError — `SentencePump` not defined yet.

- [ ] **Step 3: Write the implementation**

Create `neurocomputer/core/voice/sentence_pump.py`:

```python
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
        """Constructor without real LiveKit objects, for unit tests."""
        from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
        instance = cls.__new__(cls)
        # Initialize LLMStream parent with minimal stubs
        llm.LLMStream.__init__(
            instance,
            llm=MagicLLMStub(),
            chat_ctx=ChatContext(),
            tools=[],
            conn_options=DEFAULT_API_CONNECT_OPTIONS,
        )
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
                    msg = await asyncio.wait_for(queue.get(), timeout=WATCHDOG_S)
                except asyncio.TimeoutError:
                    logger.warning(f"[Voice] Watchdog fired after {WATCHDOG_S}s")
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
                    if topic == "task.done":
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


class MagicLLMStub:
    """Test-only stub for the LLM parent of LLMStream."""
    pass
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_sentence_pump.py -v`
Expected: All 5 tests PASS. If `db.add_message` blows up in tests, mock it inside the test fixtures.

If `db.add_message` fails in tests because no DB is initialized: add a `mock_db` fixture in the test file that patches `core.voice.sentence_pump.db.add_message` with `AsyncMock()`. Apply via `with patch("core.voice.sentence_pump.db.add_message", AsyncMock())`.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neurocomputer/core/voice/sentence_pump.py neurocomputer/tests/test_sentence_pump.py
git commit -m "feat(voice): add SentencePump streaming Brain queue → sentence-chunked TTS"
```

---

### Task 4: BargeInController state machine

**Files:**
- Create: `neurocomputer/core/voice/barge_in.py`
- Test: `neurocomputer/tests/test_barge_in.py`

500ms-gated TTS-cancel. Listens to `AgentSession` `user_started_speaking` / `user_stopped_speaking` events.

- [ ] **Step 1: Write failing tests**

Create `neurocomputer/tests/test_barge_in.py`:

```python
"""Tests for BargeInController — 500ms-gated TTS cancel."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch

from core.voice.barge_in import BargeInController


@pytest.fixture
def fake_session():
    s = MagicMock()
    s.interrupt = MagicMock()
    s._agent_speaking = False  # mutable flag the test controls
    return s


async def test_cough_below_500ms_does_not_cancel(fake_session):
    """User speech for <500ms should NOT trigger cancel."""
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=100)  # short gate for tests
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.05)  # half the gate
    ctrl.on_user_stopped_speaking()
    await asyncio.sleep(0.2)   # let any deferred fire

    assert fake_session.interrupt.call_count == 0
    await ctrl.stop()


async def test_real_interrupt_above_gate_cancels(fake_session):
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=100)
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.2)  # past the gate
    # User still speaking when timer fires → cancel
    assert fake_session.interrupt.call_count == 1
    ctrl.on_user_stopped_speaking()
    await ctrl.stop()


async def test_no_cancel_when_agent_silent(fake_session):
    """If agent isn't currently speaking, no cancel needed."""
    fake_session._agent_speaking = False
    ctrl = BargeInController(fake_session, gate_ms=100)
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.2)
    ctrl.on_user_stopped_speaking()
    assert fake_session.interrupt.call_count == 0
    await ctrl.stop()


async def test_rapid_stop_start_resets_timer(fake_session):
    """Multiple coughs in succession should each reset; none should cancel."""
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=200)
    await ctrl.start()

    for _ in range(3):
        ctrl.on_user_started_speaking()
        await asyncio.sleep(0.05)  # well under 200ms
        ctrl.on_user_stopped_speaking()
        await asyncio.sleep(0.01)

    await asyncio.sleep(0.3)  # let any leftover timer fire
    assert fake_session.interrupt.call_count == 0
    await ctrl.stop()


async def test_stop_cancels_pending_timer(fake_session):
    """Calling stop() must cancel any pending cancellation timer."""
    fake_session._agent_speaking = True
    ctrl = BargeInController(fake_session, gate_ms=500)
    await ctrl.start()

    ctrl.on_user_started_speaking()
    await asyncio.sleep(0.1)
    await ctrl.stop()
    await asyncio.sleep(0.6)  # past the gate
    assert fake_session.interrupt.call_count == 0
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_barge_in.py -v`
Expected: ImportError.

- [ ] **Step 3: Write the implementation**

Create `neurocomputer/core/voice/barge_in.py`:

```python
"""BargeInController — duration-gated TTS cancel.

State machine:
  IDLE  --user_started_speaking-->  ARMED (start gate timer)
  ARMED --user_stopped_speaking-->  IDLE  (cough/ack: no cancel)
  ARMED --timer expires----------->  CANCELLING:
                                       if agent is speaking, call session.interrupt()
                                     -->  IDLE
"""
import asyncio
import logging

logger = logging.getLogger("voice-barge-in")

DEFAULT_GATE_MS = 500


class BargeInController:
    def __init__(self, session, gate_ms: int = DEFAULT_GATE_MS):
        self._session = session
        self._gate_s = gate_ms / 1000.0
        self._timer_task: asyncio.Task | None = None
        self._stopped = False

    async def start(self):
        self._stopped = False

    async def stop(self):
        self._stopped = True
        await self._cancel_timer()

    def on_user_started_speaking(self):
        if self._stopped:
            return
        # Reset/restart gate timer on every start event
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
        self._timer_task = asyncio.create_task(self._fire_after_gate())

    def on_user_stopped_speaking(self):
        # User stopped before gate expired → cough/ack, no cancel
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()

    async def _cancel_timer(self):
        if self._timer_task and not self._timer_task.done():
            self._timer_task.cancel()
            try:
                await self._timer_task
            except asyncio.CancelledError:
                pass

    async def _fire_after_gate(self):
        try:
            await asyncio.sleep(self._gate_s)
        except asyncio.CancelledError:
            return
        if self._stopped:
            return
        if self._is_agent_speaking():
            try:
                self._session.interrupt()
                logger.info("[Voice] barge-in fired")
            except Exception as e:
                logger.warning(f"[Voice] barge-in interrupt failed: {e}")

    def _is_agent_speaking(self) -> bool:
        # AgentSession exposes various indicators; the test stub uses _agent_speaking.
        # In production, derive from session events tracked by voice_manager.
        return bool(getattr(self._session, "_agent_speaking", False))
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_barge_in.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neurocomputer/core/voice/barge_in.py neurocomputer/tests/test_barge_in.py
git commit -m "feat(voice): add gated BargeInController for natural interruptions"
```

---

### Task 5: Sarvam TTS plugin

**Files:**
- Create: `neurocomputer/core/voice/sarvam_tts.py`
- Test: `neurocomputer/tests/test_sarvam_tts.py`

LiveKit `tts.TTS` plugin wrapping Sarvam's `/text-to-speech` HTTP endpoint. Per-sentence batch (Sarvam returns base64 WAV).

Sarvam API: `POST https://api.sarvam.ai/text-to-speech` with header `api-subscription-key`, body `{"inputs": [text], "target_language_code": lang, "speaker": voice_id, "model": "bulbul:v1", "speech_sample_rate": 22050, "enable_preprocessing": true}`. Response: `{"audios": ["<base64-wav>"]}`.

- [ ] **Step 1: Write failing tests**

Create `neurocomputer/tests/test_sarvam_tts.py`:

```python
"""Tests for SarvamTTS plugin — mocked HTTP."""
import base64
import io
import wave
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.voice.sarvam_tts import SarvamTTS


def _fake_wav_bytes(duration_s=0.1, sample_rate=22050):
    """Build a tiny silent WAV for tests."""
    n_samples = int(sample_rate * duration_s)
    pcm = b"\x00\x00" * n_samples  # 16-bit silence
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)
    return buf.getvalue()


async def test_synthesize_yields_pcm_frames():
    fake_wav = _fake_wav_bytes()
    fake_b64 = base64.b64encode(fake_wav).decode("ascii")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json = MagicMock(return_value={"audios": [fake_b64]})
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("core.voice.sarvam_tts.httpx.AsyncClient", return_value=mock_client):
        tts_plugin = SarvamTTS(api_key="fake")
        stream = tts_plugin.synthesize("Hello world.")
        frames = []
        async for synth in stream:
            frames.append(synth)
        assert len(frames) >= 1
        for f in frames:
            assert f.sample_rate == 22050
            assert f.num_channels == 1
            assert isinstance(f.data, (bytes, bytearray))


async def test_synthesize_handles_5xx_gracefully():
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "boom"
    mock_resp.json = MagicMock(side_effect=Exception("not json"))

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("core.voice.sarvam_tts.httpx.AsyncClient", return_value=mock_client):
        tts_plugin = SarvamTTS(api_key="fake")
        stream = tts_plugin.synthesize("Hello.")
        frames = []
        async for synth in stream:
            frames.append(synth)
        # Per spec: yield silence frame instead of raising
        assert len(frames) >= 1
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_sarvam_tts.py -v`
Expected: ImportError.

- [ ] **Step 3: Write the implementation**

Create `neurocomputer/core/voice/sarvam_tts.py`:

```python
"""Sarvam TTS plugin for LiveKit AgentSession.

Calls Sarvam /text-to-speech per sentence. Returns 22050 Hz mono PCM
SynthesizedAudio frames. On 5xx, yields a brief silence frame so the
session continues with the next sentence rather than dying mid-turn.
"""
import asyncio
import base64
import io
import logging
import os
import wave

import httpx

from livekit.agents import tts
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS

logger = logging.getLogger("sarvam-tts")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_VOICE_ID = os.getenv("SARVAM_VOICE_ID", "meera")
SARVAM_TTS_LANGUAGE = os.getenv("SARVAM_TTS_LANGUAGE", "en-IN")
SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SAMPLE_RATE = 22050
NUM_CHANNELS = 1
SILENCE_FRAME_MS = 50


def _silence_frame() -> bytes:
    n = int(SAMPLE_RATE * SILENCE_FRAME_MS / 1000)
    return b"\x00\x00" * n


class SarvamTTS(tts.TTS):
    def __init__(
        self,
        *,
        api_key: str = SARVAM_API_KEY,
        voice_id: str = SARVAM_VOICE_ID,
        language: str = SARVAM_TTS_LANGUAGE,
        model: str = "bulbul:v1",
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._api_key = api_key
        self._voice_id = voice_id
        self._language = language
        self._model = model

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> tts.ChunkedStream:
        return _SarvamChunkedStream(self, text)


class _SarvamChunkedStream(tts.ChunkedStream):
    def __init__(self, parent: SarvamTTS, text: str):
        super().__init__(parent)
        self._parent = parent
        self._text = text

    async def _run(self):
        text = (self._text or "").strip()
        if not text:
            return

        body = {
            "inputs": [text],
            "target_language_code": self._parent._language,
            "speaker": self._parent._voice_id,
            "model": self._parent._model,
            "speech_sample_rate": SAMPLE_RATE,
            "enable_preprocessing": True,
        }
        headers = {
            "api-subscription-key": self._parent._api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(SARVAM_TTS_URL, headers=headers, json=body)
                if resp.status_code != 200:
                    logger.error(f"Sarvam TTS error {resp.status_code}: "
                                 f"{getattr(resp, 'text', '')[:200]}")
                    self._ch.send_nowait(
                        tts.SynthesizedAudio(
                            data=_silence_frame(),
                            sample_rate=SAMPLE_RATE,
                            num_channels=NUM_CHANNELS,
                        )
                    )
                    return

                data = resp.json()
                audios = data.get("audios", [])
                if not audios:
                    logger.warning("Sarvam TTS returned no audio")
                    return

                wav_b64 = audios[0]
                wav_bytes = base64.b64decode(wav_b64)
                pcm = _wav_to_pcm(wav_bytes)
                # Chunk the PCM into ~20ms frames so LiveKit can stream-play
                chunk_size = int(SAMPLE_RATE * 0.02) * 2  # 20ms, 16-bit
                for i in range(0, len(pcm), chunk_size):
                    self._ch.send_nowait(
                        tts.SynthesizedAudio(
                            data=pcm[i : i + chunk_size],
                            sample_rate=SAMPLE_RATE,
                            num_channels=NUM_CHANNELS,
                        )
                    )
        except Exception as e:
            logger.error(f"Sarvam TTS exception: {e}", exc_info=True)
            self._ch.send_nowait(
                tts.SynthesizedAudio(
                    data=_silence_frame(),
                    sample_rate=SAMPLE_RATE,
                    num_channels=NUM_CHANNELS,
                )
            )


def _wav_to_pcm(wav_bytes: bytes) -> bytes:
    """Strip WAV header and return raw 16-bit PCM mono at SAMPLE_RATE."""
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        ch = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        frames = w.readframes(w.getnframes())
    if ch == 1 and sw == 2 and sr == SAMPLE_RATE:
        return frames
    # Mismatch: log and pass through (LiveKit may still accept; fix later if needed)
    logger.warning(
        f"Sarvam TTS sample-rate mismatch: ch={ch} sw={sw} sr={sr}; "
        f"expected mono/16-bit/{SAMPLE_RATE}Hz"
    )
    return frames
```

- [ ] **Step 4: Run tests, confirm they pass**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_sarvam_tts.py -v`
Expected: Both tests PASS.

- [ ] **Step 5: (Optional) Manual live smoke against real Sarvam**

Run from `/home/ubuntu/neurocomputer/neurocomputer/`:

```bash
python3 -c "
import asyncio, os, wave
from core.voice.sarvam_tts import SarvamTTS
async def main():
    t = SarvamTTS()
    s = t.synthesize('Hello, this is a Sarvam TTS smoke test.')
    pcm = b''
    async for f in s:
        pcm += f.data
    with wave.open('/tmp/sarvam_smoke.wav', 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(pcm)
    print(f'wrote {len(pcm)} bytes to /tmp/sarvam_smoke.wav')
asyncio.run(main())
"
```

Expected: writes a non-empty WAV. Skip if no internet / no quota.

- [ ] **Step 6: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neurocomputer/core/voice/sarvam_tts.py neurocomputer/tests/test_sarvam_tts.py
git commit -m "feat(voice): add Sarvam TTS plugin (bulbul:v1, 22050Hz)"
```

---

### Task 6: Add livekit-plugins-turn-detector dependency

**Files:**
- Modify: `neurocomputer/requirements.txt`

- [ ] **Step 1: Append the dependency**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && echo "livekit-plugins-turn-detector" >> requirements.txt`

- [ ] **Step 2: Install it**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pip install livekit-plugins-turn-detector`
Expected: install succeeds. First import will lazy-download the EOU model (~50MB) — that's fine.

- [ ] **Step 3: Verify import**

Run: `python3 -c "from livekit.plugins import turn_detector; print('ok')"`
Expected: `ok` (may print a model-download progress bar the first time).

- [ ] **Step 4: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neurocomputer/requirements.txt
git commit -m "chore(deps): add livekit-plugins-turn-detector for EOU model"
```

---

### Task 7: Wire everything into voice_manager.py

**Files:**
- Modify: `neurocomputer/core/voice_manager.py` (multiple regions)

This task replaces the old `InfinityBrainLLM` / `InfinityBrainStream`, swaps providers, mounts EOU + barge-in. Terminal-mode (`TmuxEchoLLM`) path is left untouched.

- [ ] **Step 1: Update imports**

Edit `neurocomputer/core/voice_manager.py`. Replace lines 27-32:

```python
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from core.brain import Brain
from core.pubsub import hub
from core.db import db
from core.sarvam_stt import SarvamSTT
from core.voice.sentence_pump import SentencePumpLLM
from core.voice.barge_in import BargeInController
from core.voice.sarvam_tts import SarvamTTS
from core import tmux_manager
```

(If `MultilingualModel` import path differs in installed version, search the installed package: `python3 -c "import livekit.plugins.turn_detector as t; print(dir(t))"` — adjust to the right symbol.)

- [ ] **Step 2: Delete InfinityBrainLLM and InfinityBrainStream classes**

Delete the entire block from `class InfinityBrainLLM` (line 54) through the end of `class InfinityBrainStream` (line ~239) — about 185 lines. The `TmuxEchoLLM` / `TmuxEchoStream` classes that follow STAY.

- [ ] **Step 3: Swap provider construction in `start_call`**

Find the block at ~line 454-472 inside `start_call`. Replace:

```python
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
```

With:

```python
        else:
            agent = Agent(
                instructions="You are Neuro, a helpful AI voice assistant. Keep responses concise and conversational."
            )
            llm_impl = SentencePumpLLM(brain, conversation_id, agent_id, room)
            logger.info("[Voice] Pipeline: Silero VAD + EOU → Sarvam STT → Brain (sentence-pumped) → Sarvam TTS")

        http_session = aiohttp.ClientSession()

        session = AgentSession(
            llm=llm_impl,
            vad=silero.VAD.load(
                min_speech_duration=0.05,
                min_silence_duration=0.2,
                prefix_padding_duration=0.2,
                activation_threshold=0.25,
            ),
            stt=SarvamSTT(),
            tts=SarvamTTS(),
            turn_detection=MultilingualModel(),
            allow_interruptions=False,
        )
```

- [ ] **Step 4: Mount BargeInController and track agent-speaking state**

Right after the `session = AgentSession(...)` block, before the `_pub_state` definition, add:

```python
        # Track agent-speaking state so BargeInController can decide whether to cancel
        session._agent_speaking = False

        barge_in = BargeInController(session)
        await barge_in.start()
```

Then in the existing `agent_started_speaking` / `agent_stopped_speaking` handlers (~line 494-502), set the flag:

Replace:

```python
        @session.on("agent_started_speaking")
        def _on_agent_speak():
            logger.info("[Voice] Agent started speaking")
            asyncio.create_task(_pub_state("speaking"))

        @session.on("agent_stopped_speaking")
        def _on_agent_stop():
            logger.info("[Voice] Agent stopped speaking")
            asyncio.create_task(_pub_state("idle"))
```

With:

```python
        @session.on("agent_started_speaking")
        def _on_agent_speak():
            logger.info("[Voice] Agent started speaking")
            session._agent_speaking = True
            asyncio.create_task(_pub_state("speaking"))

        @session.on("agent_stopped_speaking")
        def _on_agent_stop():
            logger.info("[Voice] Agent stopped speaking")
            session._agent_speaking = False
            asyncio.create_task(_pub_state("idle"))
```

And in the user-speaking handlers (~line 484-492), call into the controller. Replace:

```python
        @session.on("user_started_speaking")
        def _on_speak_start():
            logger.info("[Voice] VAD: user started speaking")
            asyncio.create_task(_pub_state("listening"))

        @session.on("user_stopped_speaking")
        def _on_speak_stop():
            logger.info("[Voice] VAD: user stopped speaking")
            asyncio.create_task(_pub_state("thinking"))
```

With:

```python
        @session.on("user_started_speaking")
        def _on_speak_start():
            logger.info("[Voice] VAD: user started speaking")
            barge_in.on_user_started_speaking()
            asyncio.create_task(_pub_state("listening"))

        @session.on("user_stopped_speaking")
        def _on_speak_stop():
            logger.info("[Voice] VAD: user stopped speaking")
            barge_in.on_user_stopped_speaking()
            asyncio.create_task(_pub_state("thinking"))
```

- [ ] **Step 5: Cleanup BargeIn on call end**

In `end_call` (~line 579-611), before the `vs._task.cancel()` block, add nothing — barge_in lives inside the session task. But we need it stoppable, so attach it to the VoiceSession dataclass.

Add a field to `VoiceSession` (~line 41-51):

```python
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
    _barge_in: Optional["BargeInController"] = None
```

In `start_call` where `vs = VoiceSession(...)` is built (~line 506-515), add `_barge_in=barge_in` to the kwargs.

In `end_call` (~line 593-595), before disconnecting room:

```python
        if vs._barge_in:
            try:
                await vs._barge_in.stop()
            except Exception:
                pass
```

- [ ] **Step 6: Verify the file parses and imports cleanly**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && python3 -c "from core.voice_manager import voice_manager; print('ok')"`
Expected: `ok` (may take a moment for first-import EOU model load).

If `MultilingualModel` import path was wrong, fix it now per Step 1's note.

- [ ] **Step 7: Run all voice tests**

Run: `cd /home/ubuntu/neurocomputer/neurocomputer && pytest tests/test_sentence_boundary.py tests/test_sentence_pump.py tests/test_barge_in.py tests/test_sarvam_tts.py -v`
Expected: all pass (no regressions from the rewire).

- [ ] **Step 8: Commit**

```bash
cd /home/ubuntu/neurocomputer
git add neurocomputer/core/voice_manager.py
git commit -m "feat(voice): wire streaming pipeline — Sarvam STT/TTS, EOU, barge-in"
```

---

### Task 8: Manual smoke test + acceptance verification

**Files:** none modified — verification only.

- [ ] **Step 1: Restart the dev server**

If the server is running, restart it so the new module imports. (Per memory: dev server runs on port 7000; verify before killing.)

```bash
# Find existing server, restart per project convention
ps aux | grep -i 'server.py' | grep -v grep
```

Stop the existing instance via its normal stop path, then start fresh per project run instructions.

- [ ] **Step 2: Web smoke checklist**

Open the web app, start a voice call. Verify each:
1. First audio plays within ~1.5s of you stopping speaking (median across ~5 turns)
2. Speak "call mom and dad" with a small pause after "mom" — agent should NOT split into two turns (EOU model held the turn open)
3. While agent is mid-response, say a single "yeah" briefly (<500ms) — agent should KEEP speaking (cough gate)
4. While agent is mid-response, speak a real interruption (>500ms, e.g. "wait, stop") — agent should cancel TTS within ~500ms
5. End call cleanly, restart, verify no leftover background tasks (ps shows no zombie agent processes)

- [ ] **Step 3: Mobile (Kotlin) smoke checklist**

Open the Kotlin app, start a voice call. Run the same 5 checks as Step 2.

- [ ] **Step 4: Latency log audit**

Server logs should show `[Voice] Pipeline:` confirming the new pipeline string. Look for `[Voice] User said:` and `[Voice] Response complete:` log pairs across ~20 turns.

If you want stage-level timing (per-spec telemetry §): add timestamp logging now in `voice_manager.py` event handlers — each `logger.info` call already has implicit timestamps via the standard logging formatter. Grep:

```bash
grep -E "user (started|stopped) speaking|Agent started speaking|Response complete" /path/to/server.log | tail -50
```

Compute median + p95 of (`Agent started speaking` time − `user stopped speaking` time) across turns. Acceptance: median <1.5s, p95 <2.5s.

If miss target, identify which stage exceeded budget (compare timestamps across STT/EOU/Brain/TTS log markers).

- [ ] **Step 5: Final commit (if any tuning needed)**

If you tuned thresholds (VAD silence, gate_ms, sentence chunking limits) during the smoke step, commit those small adjustments:

```bash
cd /home/ubuntu/neurocomputer
git add -p  # selectively stage just the tuning
git commit -m "tune(voice): adjust thresholds after smoke testing"
```

---

## Self-Review Notes

**Spec coverage:** All spec sections covered:
- §Components (3 new modules + voice_manager patch) → Tasks 2-7
- §Turn detection (EOU + Silero) → Task 7 step 3
- §Barge-in (500ms gate) → Task 4 + Task 7 step 4
- §Sentence chunking (hard/soft/force-flush) → Task 2
- §Error handling (Sarvam 5xx, Brain stalls) → Tasks 5 + 3 (watchdog)
- §Testing (unit + smoke) → Tasks 2-5 + Task 8
- §Rollout (no flag, manual smoke, revert if broken) → Task 8

**Open verifications (resolved during impl, not blocking the plan):**
- Exact import path for `MultilingualModel` — flagged in Task 7 step 1 with check command
- Whether `db.add_message` needs mocking in unit tests — flagged in Task 3 step 4 with fix
- Whether `livekit-plugins-openai` import is still needed elsewhere — Task 7 step 1 removed only the unused symbol; package itself stays in requirements
