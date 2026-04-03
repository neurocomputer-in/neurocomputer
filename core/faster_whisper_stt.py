"""
Faster-Whisper STT adapter for LiveKit AgentSession.
Uses local faster-whisper model instead of cloud API for lower latency.
"""

import asyncio
import io
import logging
import struct
import wave
from typing import Optional, Union, List

import numpy as np
from livekit import rtc
from livekit.agents import stt
from livekit.agents.stt import RecognizeStream

logger = logging.getLogger("faster-whisper-stt")

# Singleton model instance
_model = None


def get_model(model_size: str = "small", device: str = "cpu"):
    """Get or create the singleton Whisper model."""
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        logger.info(f"Loading faster-whisper model: {model_size} on {device}")
        _model = WhisperModel(model_size, device=device)
        logger.info("faster-whisper model loaded")
    return _model


class FasterWhisperSTT(stt.STT):
    """
    Faster-Whisper based STT for LiveKit AgentSession.
    Runs locally for faster inference (no cloud round-trip).
    """

    def __init__(
        self,
        model_size: str = "small",
        device: str = "cpu",
        language: str = "en",
    ):
        """
        Args:
            model_size: faster-whisper model size (tiny, base, small, medium, large)
            device: cpu or cuda
            language: source language code (e.g., 'en', 'hi', 'auto')
        """
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=True, interim_results=True),
        )
        self._model_size = model_size
        self._device = device
        self._language = language if language != "auto" else None

    async def _recognize_impl(
        self,
        buffer: Union[rtc.AudioFrame, List[rtc.AudioFrame]],
        *,
        language: Optional[str] = None,
        conn_options=None,
    ) -> stt.SpeechEvent:
        """Internal async implementation of recognize."""
        model = get_model(self._model_size, self._device)
        lang = language or self._language or "en"

        # Convert AudioBuffer to bytes
        audio_data = self._audio_frames_to_wav(buffer)

        # Run inference in executor
        loop = asyncio.get_event_loop()
        segments, info = await loop.run_in_executor(
            None,
            lambda: model.transcribe(
                audio_data,
                language=lang,
                beam_size=5,
                vad_filter=True,
            )
        )

        # Collect full text
        full_text = ""
        for segment in segments:
            full_text += segment.text

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.TranscriptionAlternative(language=lang, text=full_text)],
            info=info,
        )

    def stream(
        self,
        *,
        language: Optional[str] = None,
        conn_options=None,
    ) -> RecognizeStream:
        """Return a streaming recognize stream."""
        return FasterWhisperRecognizeStream(
            stt=self,
            language=language or self._language,
            conn_options=conn_options,
        )

    @staticmethod
    def _audio_frames_to_wav(
        buffer: Union[rtc.AudioFrame, List[rtc.AudioFrame]],
    ) -> bytes:
        """Convert LiveKit AudioFrame(s) to WAV bytes for faster-whisper."""
        if isinstance(buffer, list):
            frames = buffer
        else:
            frames = [buffer]

        # Get properties from first frame
        first = frames[0]
        sample_rate = first.sample_rate
        num_channels = first.num_channels

        # Concatenate all samples
        all_samples = []
        for frame in frames:
            samples = np.frombuffer(frame.data.tobytes(), dtype=np.float32)
            all_samples.append(samples)

        combined = np.concatenate(all_samples)

        # Convert to 16-bit PCM
        int_data = (combined * 32767).astype("<i2").tobytes()

        # Write to WAV
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(int_data)

        return wav_io.getvalue()


class FasterWhisperRecognizeStream(RecognizeStream):
    """
    Streaming STT implementation for faster-whisper.
    Accumulates audio frames and performs recognition on end_input.
    """

    def __init__(self, stt: FasterWhisperSTT, language: Optional[str] = None, conn_options=None):
        from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
        super().__init__(stt=stt, conn_options=conn_options or DEFAULT_API_CONNECT_OPTIONS)
        self._stt = stt
        self._language = language or "en"
        self._frames: List[rtc.AudioFrame] = []
        self._finalized = False

    def push_frame(self, frame: rtc.AudioFrame) -> None:
        """Add an audio frame to the buffer."""
        if self._finalized:
            return
        self._frames.append(frame)

    def end_input(self) -> None:
        """Signal end of input, trigger final recognition."""
        self._finalized = True

    async def _run(self) -> None:
        """Perform recognition on accumulated audio."""
        try:
            if not self._frames:
                return

            # Convert frames to WAV
            wav_data = FasterWhisperSTT._audio_frames_to_wav(self._frames)

            # Run faster-whisper in executor
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: get_model(self._stt._model_size, self._stt._device).transcribe(
                    wav_data,
                    language=self._language,
                    beam_size=5,
                    vad_filter=True,
                )
            )

            # Send events as segments are generated
            for segment in segments:
                self._ch.send_nowait(
                    stt.SpeechEvent(
                        type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                        alternatives=[
                            stt.TranscriptionAlternative(
                                language=self._language,
                                text=segment.text,
                            )
                        ],
                    )
                )

        except Exception as e:
            logger.error(f"Faster-whisper streaming error: {e}")
            self._ch.send_nowait(
                stt.SpeechEvent(
                    type=stt.SpeechEventType.ERROR,
                    error=str(e),
                )
            )
