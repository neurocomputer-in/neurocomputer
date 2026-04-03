"""
ElevenLabs TTS adapter for LiveKit AgentSession.
Uses StreamAdapter to provide streaming interface for ElevenLabs.
"""

import asyncio
import io
import logging
import os
from typing import Optional, AsyncIterable
import httpx

from livekit import rtc
from livekit.agents import tts
from livekit.agents.tts import StreamAdapter
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS

logger = logging.getLogger("elevenlabs-tts")

# Load from environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjzDR9eL")  # Rachel voice


class ElevenLabsTTS(tts.TTS):
    """
    ElevenLabs TTS adapter for LiveKit.
    Non-streaming implementation that returns full audio.
    Use with StreamAdapter for streaming support.
    """

    def __init__(
        self,
        *,
        voice_id: str = ELEVENLABS_VOICE_ID,
        model: str = "eleven_flash_v2_5",
        api_key: str = ELEVENLABS_API_KEY,
        voice_settings: dict = None,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=44100,
            num_channels=1,
        )

        self._voice_id = voice_id
        self._model = model
        self._api_key = api_key
        self._voice_settings = voice_settings or {
            "stability": 0.3,
            "similarity_boost": 0.7,
            "speed": 1.15,
            "style": 0.3,
            "use_speaker_boost": False,
        }

    @property
    def voice_id(self) -> str:
        return self._voice_id

    @property
    def model(self) -> str:
        return self._model

    async def _synthesize(self, text: str) -> AsyncIterable[bytes]:
        """Internal synthesize that returns audio chunks."""
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"

        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }

        payload = {
            "text": text,
            "model_id": self.model,
            "voice_settings": self._voice_settings,
        }

        buffer = b""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as response:
                    if response.status_code != 200:
                        error_body = await response.aread()
                        logger.error(f"ElevenLabs error: {response.status_code} - {error_body}")
                        return

                    async for chunk in response.aiter_bytes(chunk_size=4096):
                        if chunk:
                            buffer += chunk
                            if len(buffer) >= 4096:
                                pcm = await self._convert_mp3(buffer)
                                if pcm:
                                    yield pcm
                                buffer = b""

                    if buffer:
                        pcm = await self._convert_mp3(buffer)
                        if pcm:
                            yield pcm

        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")

    async def _convert_mp3(self, mp3_data: bytes) -> Optional[bytes]:
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            audio = audio.set_channels(1).set_frame_rate(44100)
            return audio.raw_data
        except Exception as e:
            logger.error(f"MP3 conversion error: {e}")
            return None

    def synthesize(
        self, text: str, *, conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS
    ) -> tts.ChunkedStream:
        # Return a chunked stream from our async generator
        return ElevenLabsChunkedStream(self, text)


class ElevenLabsChunkedStream(tts.ChunkedStream):
    """Chunked stream wrapper for ElevenLabs TTS."""

    def __init__(self, tts: ElevenLabsTTS, text: str):
        super().__init__(tts)
        self.tts = tts
        self.text = text

    async def _run(self):
        async for chunk in self.tts._synthesize(self.text):
            self._ch.send_nowait(
                tts.SynthesizedAudio(
                    data=chunk,
                    sample_rate=44100,
                    num_channels=1,
                )
            )
