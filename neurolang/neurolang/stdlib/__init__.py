"""NeuroLang standard library — built-in neuros for common agentic tasks.

These are normal `@neuro`-decorated functions; nothing special about them
except that they ship in the package and serve as exemplars for users
writing their own neuros.

Optional external dependencies (openai, anthropic, requests, elevenlabs,
whisper, etc.) are checked at use time so the base install stays light.
"""
from . import web, reason, memory_neuros, model, voice, agent
from . import email_neuros as email

__all__ = ["web", "reason", "memory_neuros", "model", "voice", "agent", "email"]
