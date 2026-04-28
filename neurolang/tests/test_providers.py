"""Tests for _providers.py — max_tokens per kind, and _KIND_MAX_TOKENS mapping."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from neurolang._providers import (
    _KIND_MAX_TOKENS,
    _llm_call_via_openai_sdk,
    PROVIDER_KINDS,
)


def _make_mock_openai(captured: dict):
    """Return a fake openai.OpenAI class that records chat.completions.create kwargs."""
    class FakeCompletions:
        @staticmethod
        def create(**kwargs: Any):
            captured.update(kwargs)
            msg = SimpleNamespace(content="ok")
            choice = SimpleNamespace(message=msg)
            return SimpleNamespace(choices=[choice])

    class FakeChat:
        completions = FakeCompletions()

    class FakeClient:
        chat = FakeChat()

    class FakeOpenAI:
        def __init__(self, **_):
            pass
        chat = FakeChat()

    return FakeOpenAI


# ---- _KIND_MAX_TOKENS mapping -------------------------------------------

def test_kind_max_tokens_compile():
    assert _KIND_MAX_TOKENS["compile"] == 2048


def test_kind_max_tokens_decompile():
    assert _KIND_MAX_TOKENS["decompile"] == 512


def test_kind_max_tokens_plan():
    assert _KIND_MAX_TOKENS["plan"] == 2048


def test_kind_max_tokens_reason():
    assert _KIND_MAX_TOKENS["reason"] == 2048


def test_kind_max_tokens_reason_deep():
    assert _KIND_MAX_TOKENS["reason.deep"] == 4096


def test_provider_kinds_includes_reason_kinds():
    assert "reason" in PROVIDER_KINDS
    assert "reason.deep" in PROVIDER_KINDS


# ---- _llm_call_via_openai_sdk passes max_tokens from kind ---------------

def test_openai_sdk_uses_compile_max_tokens(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr("openai.OpenAI", _make_mock_openai(captured))
    _llm_call_via_openai_sdk("p", "", model="gpt-4o-mini", kind="compile", provider="openai")
    assert captured["max_tokens"] == 2048


def test_openai_sdk_uses_decompile_max_tokens(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr("openai.OpenAI", _make_mock_openai(captured))
    _llm_call_via_openai_sdk("p", "", model="gpt-4o-mini", kind="decompile", provider="openai")
    assert captured["max_tokens"] == 512


def test_openai_sdk_uses_reason_deep_max_tokens(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr("openai.OpenAI", _make_mock_openai(captured))
    _llm_call_via_openai_sdk("p", "", model="gpt-4o-mini", kind="reason.deep", provider="openai")
    assert captured["max_tokens"] == 4096


def test_openai_sdk_unknown_kind_defaults_to_2048(monkeypatch):
    captured: dict = {}
    monkeypatch.setattr("openai.OpenAI", _make_mock_openai(captured))
    _llm_call_via_openai_sdk("p", "", model="gpt-4o-mini", kind="unknown_future_kind", provider="openai")
    assert captured["max_tokens"] == 2048
