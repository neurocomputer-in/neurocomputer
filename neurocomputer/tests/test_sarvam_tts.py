"""Tests for SarvamTTS plugin — mocked HTTP.

Note: livekit-agents 1.5.2 API differences from plan:
- ChunkedStream.__init__ requires tts=, input_text=, conn_options=
- _run(output_emitter) receives an AudioEmitter argument
- Iteration yields SynthesizedAudio with .frame (rtc.AudioFrame), not .data/.sample_rate
"""
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


@pytest.mark.asyncio
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
            # livekit-agents 1.5.2: SynthesizedAudio.frame is an rtc.AudioFrame
            assert f.frame.sample_rate == 22050
            assert f.frame.num_channels == 1
            assert len(bytes(f.frame.data)) > 0


@pytest.mark.asyncio
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
