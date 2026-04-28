"""Voice stdlib neuros — TTS and STT.

These are thin adapters over external services. Real audio pipelines
(LiveKit rooms, Twilio bridges, persistent voice agents) live in the
Neurocomputer environment, not here.
"""
from __future__ import annotations

import os
from typing import Optional, Union

from ..neuro import neuro
from ..budget import Budget


def _require(module_name: str):
    try:
        return __import__(module_name)
    except ImportError as e:
        raise ImportError(
            f"This neuro needs `{module_name}`. Install with: pip install {module_name}"
        ) from e


@neuro(
    effect="voice",
    kind="skill.voice",
    name="neurolang.stdlib.voice.transcribe",
    budget=Budget(latency_ms=4000, cost_usd=0.01),
)
def transcribe(audio: Union[bytes, str], *, model: str = "whisper-1",
               language: Optional[str] = None) -> str:
    """Transcribe audio to text via OpenAI Whisper.

    `audio` is either raw bytes or a file path.
    """
    oai = _require("openai")
    client = oai.OpenAI()
    if isinstance(audio, str):
        with open(audio, "rb") as f:
            resp = client.audio.transcriptions.create(
                model=model,
                file=f,
                language=language,
            )
    else:
        # OpenAI client wants a file-like object with a name
        import io
        bio = io.BytesIO(audio)
        bio.name = "audio.wav"
        resp = client.audio.transcriptions.create(
            model=model,
            file=bio,
            language=language,
        )
    return resp.text


@neuro(
    effect="voice",
    kind="skill.voice",
    name="neurolang.stdlib.voice.synthesize",
    budget=Budget(latency_ms=2500, cost_usd=0.015),
)
def synthesize(text: str, *, model: str = "tts-1", voice: str = "alloy",
               output_path: Optional[str] = None) -> bytes:
    """Synthesize speech from text using OpenAI TTS.

    Returns raw audio bytes; if `output_path` is given, also writes to disk.
    """
    oai = _require("openai")
    client = oai.OpenAI()
    resp = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
    )
    audio_bytes = resp.content
    if output_path:
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
    return audio_bytes
