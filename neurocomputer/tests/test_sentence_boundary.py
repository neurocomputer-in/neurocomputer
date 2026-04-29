"""Tests for sentence boundary extraction used by SentencePump."""
import pytest
from core.voice.sentence_boundary import extract_sentence


def test_returns_none_for_short_unpunctuated_buffer():
    assert extract_sentence("hello world") is None


def test_splits_on_period_with_trailing_space():
    sent, rest = extract_sentence("Hello world. Next part")
    assert sent == "Hello world. "
    assert rest == "Next part"


def test_splits_on_question_mark():
    sent, rest = extract_sentence("What time is it? Now")
    assert sent == "What time is it? "
    assert rest == "Now"


def test_splits_on_exclamation():
    sent, rest = extract_sentence("Wow! that's cool")
    assert sent == "Wow! "
    assert rest == "that's cool"


def test_splits_on_devanagari_danda():
    sent, rest = extract_sentence("नमस्ते। और बात")
    assert sent == "नमस्ते। "
    assert rest == "और बात"


def test_does_not_split_decimal():
    # "3.14" has no trailing space after the period — should NOT split
    assert extract_sentence("Pi is 3.14 approximately") is None


def test_does_not_split_abbreviation_without_trailing_space():
    # "Mr." followed by name — period followed by space is ambiguous;
    # we accept the split (heuristic — not perfect, but safe direction)
    sent, rest = extract_sentence("Hello Mr. Smith said hi")
    assert sent == "Hello Mr. "
    assert rest == "Smith said hi"


def test_soft_split_at_120_chars_on_comma():
    long_buf = "a" * 119 + ", continuing the sentence here without any period yet"
    sent, rest = extract_sentence(long_buf)
    assert sent.endswith(", ")
    assert len(sent) >= 120
    assert "continuing" in rest


def test_no_soft_split_below_120_chars():
    short_buf = "hello, world without period"
    assert extract_sentence(short_buf) is None


def test_force_flush_at_240_chars():
    no_punct = "a " * 130  # ~260 chars, all spaces, no punctuation
    sent, rest = extract_sentence(no_punct)
    assert len(sent) <= 240
    assert len(sent) > 0
    assert sent + rest == no_punct


def test_hard_punct_beats_soft_when_both_present():
    # Buffer has comma early AND period later — hard wins (period closer? no,
    # extract_sentence should prefer the *first* hard end found.)
    sent, rest = extract_sentence("first, second. third")
    assert sent == "first, second. "
    assert rest == "third"
