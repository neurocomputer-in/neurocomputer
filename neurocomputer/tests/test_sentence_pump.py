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
    with patch("core.voice.sentence_pump.hub") as hub_mock, \
         patch("core.voice.sentence_pump.db.add_message", AsyncMock()):
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
    with patch("core.voice.sentence_pump.hub") as hub_mock, \
         patch("core.voice.sentence_pump.db.add_message", AsyncMock()):
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
    with patch("core.voice.sentence_pump.hub") as hub_mock, \
         patch("core.voice.sentence_pump.db.add_message", AsyncMock()):
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
    with patch("core.voice.sentence_pump.hub") as hub_mock, \
         patch("core.voice.sentence_pump.db.add_message", AsyncMock()):
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
         patch("core.voice.sentence_pump.WATCHDOG_S", 0.5), \
         patch("core.voice.sentence_pump.db.add_message", AsyncMock()):
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
