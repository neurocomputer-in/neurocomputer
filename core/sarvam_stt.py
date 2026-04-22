"""
Sarvam AI STT adapter for LiveKit AgentSession.
Uses Sarvam's WebSocket streaming API for real-time speech recognition.
"""

import asyncio
import json
import logging
import os
import base64
import wave
import io
from typing import Optional
from urllib.parse import urlencode

import numpy as np
import websockets
from livekit import rtc
from livekit.agents import stt
from livekit.agents.stt import RecognizeStream
from livekit.agents.utils import AudioBuffer

logger = logging.getLogger("sarvam-stt")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "")
SARVAM_WS_BASE = "wss://api.sarvam.ai/speech-to-text-translate/ws"

class SarvamSTT(stt.STT):
    """
    Sarvam AI based STT for LiveKit AgentSession.
    Uses WebSocket streaming for low-latency transcription.
    """

    def __init__(
        self,
        language: str = "en-IN",
        model: str = "saaras:v3",
        api_key: str = SARVAM_API_KEY,
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(streaming=True, interim_results=True),
        )
        self._language = language
        self._model = model
        self._api_key = api_key

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: Optional[str] = None,
        conn_options=None,
    ) -> stt.SpeechEvent:
        """Non-streaming fallback."""
        stream = self.stream(language=language, conn_options=conn_options)
        for frame in buffer:
            stream.push_frame(frame)
        stream.end_input()

        final_event = None
        async for event in stream:
            if event.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
                final_event = event
        
        if final_event:
            return final_event
        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[stt.SpeechData(language="en-IN", text="")]
        )

    def stream(
        self,
        *,
        language: Optional[str] = None,
        conn_options=None,
    ) -> RecognizeStream:
        """Return a streaming recognize stream."""
        return SarvamRecognizeStream(
            stt=self,
            language=language or self._language,
            conn_options=conn_options,
        )


class SarvamRecognizeStream(RecognizeStream):
    """
    Streaming STT implementation for Sarvam using WebSockets.
    Config is passed via URL query parameters per Sarvam's API spec.
    """

    def __init__(self, stt: SarvamSTT, language: Optional[str] = None, conn_options=None):
        from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS
        super().__init__(stt=stt, conn_options=conn_options or DEFAULT_API_CONNECT_OPTIONS)
        self._stt_instance = stt
        self._language = language or "en-IN"
        self._ws = None

    async def _run(self) -> None:
        """Main loop for streaming."""
        # Build URL with query params (this is how Sarvam expects config)
        params = urlencode({
            "language_code": self._language,
            "model": self._stt_instance._model,
            "mode": "transcribe",
        })
        ws_url = f"{SARVAM_WS_BASE}?{params}"
        headers = {"Api-Subscription-Key": self._stt_instance._api_key}
        
        logger.info(f"Sarvam STT: Connecting to {ws_url}")
        
        try:
            async with websockets.connect(ws_url, additional_headers=headers) as ws:
                self._ws = ws
                logger.info("Sarvam STT: WebSocket connected")

                # Run sender and receiver concurrently
                send_task = asyncio.create_task(self._send_audio())
                recv_task = asyncio.create_task(self._receive_results())
                
                # Wait for either to finish (receiver finishes when WS closes)
                done, pending = await asyncio.wait(
                    [send_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        except Exception as e:
            logger.error(f"Sarvam streaming error: {e}")
            raise

    async def _send_audio(self):
        """Reads from the LiveKit input channel and sends PCM to Sarvam."""
        try:
            first_chunk = True
            
            async for frame in self._input_ch:
                if isinstance(frame, RecognizeStream._FlushSentinel):
                    continue
                
                # Convert to 16kHz mono 16-bit PCM
                pcm_data = self._process_frame(frame)                
                
                if first_chunk:
                    # Construct a valid WAV header for the first chunk to satisfy 'audio/wav' requirement
                    with io.BytesIO() as wav_io:
                        with wave.open(wav_io, 'wb') as wav_file:
                            wav_file.setnchannels(1)
                            wav_file.setsampwidth(2) # 16-bit
                            wav_file.setframerate(16000)
                            wav_file.writeframes(pcm_data)
                        payload_bytes = wav_io.getvalue()
                    first_chunk = False
                else:
                    # Subsequent chunks are pure PCM to avoid audio corruption from repeated headers
                    payload_bytes = pcm_data
                    
                b64_str = base64.b64encode(payload_bytes).decode('utf-8')
                
                payload = {
                    "audio": {
                        "data": b64_str,
                        "encoding": "audio/wav",
                        "sample_rate": 16000
                    }
                }
                
                if self._ws:
                    await self._ws.send(json.dumps(payload))
            
            logger.debug("Sarvam STT: Input channel closed, finished sending audio")
            
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Sarvam STT: WS closed during send")
        except Exception as e:
            logger.error(f"Sarvam sender error: {e}")

    async def _receive_results(self):
        """Receives results from WebSocket and emits SpeechEvents."""
        try:
            async for message in self._ws:
                try:
                    data = json.loads(message)
                except json.JSONDecodeError:
                    logger.warning(f"Sarvam STT: Non-JSON message: {message[:100]}")
                    continue
                    
                logger.debug(f"Sarvam STT received: {data}")
                
                # Sarvam may use different field names
                transcript = (
                    data.get("transcript", "") or 
                    data.get("text", "") or 
                    data.get("result", "")
                )
                is_final = data.get("is_final", data.get("final", False))
                
                if transcript:
                    event_type = (
                        stt.SpeechEventType.FINAL_TRANSCRIPT 
                        if is_final 
                        else stt.SpeechEventType.INTERIM_TRANSCRIPT
                    )
                    
                    self._event_ch.send_nowait(stt.SpeechEvent(
                        type=event_type,
                        alternatives=[stt.SpeechData(
                            language=self._language,
                            text=transcript
                        )]
                    ))
                    
        except websockets.exceptions.ConnectionClosed:
            logger.debug("Sarvam STT: WebSocket closed")
        except Exception as e:
            logger.error(f"Sarvam receiver error: {e}")

    def _process_frame(self, frame: rtc.AudioFrame) -> Optional[bytes]:
        """Convert frame to 16kHz mono 16-bit PCM bytes."""
        try:
            samples = np.frombuffer(frame.data, dtype=np.int16)
            
            # Downsample to 16kHz if needed
            if frame.sample_rate == 48000:
                samples = samples[::3]
            elif frame.sample_rate == 44100:
                # Approximate 44.1k -> 16k
                factor = frame.sample_rate / 16000
                indices = np.arange(0, len(samples), factor).astype(int)
                indices = indices[indices < len(samples)]
                samples = samples[indices]
            elif frame.sample_rate != 16000:
                factor = frame.sample_rate / 16000
                indices = np.arange(0, len(samples), factor).astype(int)
                indices = indices[indices < len(samples)]
                samples = samples[indices]
            
            return samples.tobytes()
        except Exception as e:
            logger.error(f"Error processing audio frame: {e}")
            return None
