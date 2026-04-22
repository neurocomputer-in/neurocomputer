"""
Speech-to-Text Service using OpenAI Whisper API
"""
import os
import logging
from pathlib import Path
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def transcribe_audio(file_path: str, language: str = "en") -> str:
    """
    Transcribe audio file using OpenAI Whisper API.
    
    Args:
        file_path: Path to the audio file (mp3, wav, m4a, webm, etc.)
        language: Language code for transcription (optional, auto-detected if not specified)
    
    Returns:
        Transcribed text
    """
    try:
        logger.info(f"[STT] Transcribing audio: {file_path}")
        
        # Open and send to Whisper API
        with open(file_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="text"
            )
        
        transcription = response.strip()
        logger.info(f"[STT] Transcription complete: {transcription[:50]}...")
        return transcription
        
    except Exception as e:
        logger.error(f"[STT] Transcription failed: {e}")
        raise


async def transcribe_audio_with_timestamps(file_path: str, language: str = "en") -> dict:
    """
    Transcribe audio with word-level timestamps (for future waveform sync).
    
    Returns:
        dict with 'text' and 'words' (list of {word, start, end})
    """
    try:
        logger.info(f"[STT] Transcribing with timestamps: {file_path}")
        
        with open(file_path, "rb") as audio_file:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language,
                response_format="verbose_json",
                timestamp_granularities=["word"]
            )
        
        return {
            "text": response.text,
            "words": response.words if hasattr(response, 'words') else [],
            "duration": response.duration if hasattr(response, 'duration') else 0
        }
        
    except Exception as e:
        logger.error(f"[STT] Transcription with timestamps failed: {e}")
        raise
