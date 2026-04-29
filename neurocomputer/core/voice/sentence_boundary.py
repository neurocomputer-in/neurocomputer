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
