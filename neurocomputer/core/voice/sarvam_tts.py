"""Sarvam TTS plugin for LiveKit AgentSession.

Calls Sarvam /text-to-speech per sentence. Returns 22050 Hz mono PCM
SynthesizedAudio frames. On 5xx, yields a brief silence frame so the
session continues with the next sentence rather than dying mid-turn.

livekit-agents 1.5.2 API notes:
- ChunkedStream.__init__(*, tts, input_text, conn_options)
- _run(self, output_emitter: AudioEmitter) — receives emitter arg
- output_emitter.initialize(request_id, sample_rate, num_channels, mime_type)
- output_emitter.push(raw_pcm_bytes)  — with mime_type="audio/pcm"
"""
import base64
import io
import logging
import os
import uuid
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


def _silence_pcm() -> bytes:
    n = int(SAMPLE_RATE * SILENCE_FRAME_MS / 1000)
    return b"\x00\x00" * n


class SarvamTTS(tts.TTS):
    def __init__(
        self,
        *,
        api_key: str = SARVAM_API_KEY,
        voice_id: str = SARVAM_VOICE_ID,
        language: str = SARVAM_TTS_LANGUAGE,
        model: str = "bulbul:v2",
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
        return _SarvamChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )


class _SarvamChunkedStream(tts.ChunkedStream):
    def __init__(self, *, tts: SarvamTTS, input_text: str, conn_options: APIConnectOptions):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._sarvam = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        text = (self._input_text or "").strip()
        request_id = str(uuid.uuid4())

        output_emitter.initialize(
            request_id=request_id,
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
        )

        if not text:
            output_emitter.push(_silence_pcm())
            return

        body = {
            "inputs": [text],
            "target_language_code": self._sarvam._language,
            "speaker": self._sarvam._voice_id,
            "model": self._sarvam._model,
            "speech_sample_rate": SAMPLE_RATE,
            "enable_preprocessing": True,
        }
        headers = {
            "api-subscription-key": self._sarvam._api_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(SARVAM_TTS_URL, headers=headers, json=body)
                if resp.status_code != 200:
                    logger.error(
                        "Sarvam TTS error %d: %s",
                        resp.status_code,
                        getattr(resp, "text", "")[:200],
                    )
                    output_emitter.push(_silence_pcm())
                    return

                data = resp.json()
                audios = data.get("audios", [])
                if not audios:
                    logger.warning("Sarvam TTS returned no audio")
                    output_emitter.push(_silence_pcm())
                    return

                wav_bytes = base64.b64decode(audios[0])
                pcm = _wav_to_pcm(wav_bytes)
                output_emitter.push(pcm)

        except Exception as e:
            logger.error("Sarvam TTS exception: %s", e, exc_info=True)
            output_emitter.push(_silence_pcm())


class _WavFormatMismatch(Exception):
    pass


def _wav_to_pcm(wav_bytes: bytes) -> bytes:
    """Strip WAV header and return raw 16-bit PCM mono at SAMPLE_RATE.

    Raises _WavFormatMismatch if the WAV doesn't match the expected
    (mono, 16-bit, 22050 Hz) so the caller can emit silence instead of
    pushing corrupt audio frames downstream.
    """
    with wave.open(io.BytesIO(wav_bytes), "rb") as w:
        ch = w.getnchannels()
        sw = w.getsampwidth()
        sr = w.getframerate()
        frames = w.readframes(w.getnframes())
    if ch != 1 or sw != 2 or sr != SAMPLE_RATE:
        raise _WavFormatMismatch(
            f"Sarvam returned ch={ch} sw={sw} sr={sr}; expected (1, 2, {SAMPLE_RATE})"
        )
    return frames
