"""Tests for the NL ↔ NeuroLang compiler.

Mocks the LLM call so the suite runs offline.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from neurolang import neuro, Flow
from neurolang.cache import CompilerCache
from neurolang.compile import (
    compile_source, decompile_summary, validate_source, _render_catalog, CompileError,
)


@neuro
def _t_double(n: int) -> int:
    """Double the input."""
    return n * 2


@neuro
def _t_add_one(n: int) -> int:
    """Add one."""
    return n + 1


# Source the LLM "should" produce — used in mocks
_GOOD_SOURCE = """\
from neurolang import Flow
from tests.test_compile import _t_double, _t_add_one

flow = _t_double | _t_add_one
"""


def fake_llm_good(prompt, system, *, model, **kwargs):
    return _GOOD_SOURCE


def fake_llm_with_fences(prompt, system, *, model, **kwargs):
    return f"```python\n{_GOOD_SOURCE}\n```"


def fake_llm_invalid_python(prompt, system, *, model, **kwargs):
    return "this is not python +++"


def fake_llm_no_neurolang(prompt, system, *, model, **kwargs):
    return "x = 1\nflow = x"


def fake_llm_no_flow_var(prompt, system, *, model, **kwargs):
    return "from neurolang import Flow\nresult = 42"


def fake_llm_summary(prompt, system, *, model, **kwargs):
    return "Doubles a number then adds one."


# --- Catalog rendering -------------------------------------------------------

def test_catalog_renders_registered_neuros():
    md = _render_catalog()
    assert md.startswith("# Available NeuroLang neuros")
    # Our test neuros register by default
    assert "_t_double" in md or "test_compile" in md


# --- Validation --------------------------------------------------------------

def test_validate_source_finds_imports_and_flow():
    findings = validate_source(_GOOD_SOURCE)
    assert findings.has_neurolang_import is True
    assert findings.declares_flow is True


def test_validate_source_rejects_invalid_python():
    with pytest.raises(SyntaxError):
        validate_source("def +bad(:\n    return")


# --- Forward compile ---------------------------------------------------------

def test_compile_returns_source(tmp_path):
    cache = CompilerCache(tmp_path)
    src = compile_source("double then add one", llm_fn=fake_llm_good,
                  output="source", cache=cache, use_cache=False)
    assert "_t_double" in src
    assert "flow" in src


def test_compile_strips_code_fences(tmp_path):
    cache = CompilerCache(tmp_path)
    src = compile_source("anything", llm_fn=fake_llm_with_fences,
                  output="source", cache=cache, use_cache=False)
    assert not src.startswith("```")
    assert "_t_double" in src


def test_compile_returns_executable_flow(tmp_path):
    cache = CompilerCache(tmp_path)
    flow = compile_source("double then add one", llm_fn=fake_llm_good,
                    output="flow", cache=cache, use_cache=False)
    assert isinstance(flow, Flow)
    # Run it: 5 -> double=10 -> add_one=11
    assert flow.run(5) == 11


def test_compile_rejects_invalid_python(tmp_path):
    cache = CompilerCache(tmp_path)
    with pytest.raises(CompileError):
        compile_source("anything", llm_fn=fake_llm_invalid_python,
                cache=cache, use_cache=False)


def test_compile_rejects_missing_neurolang_import(tmp_path):
    cache = CompilerCache(tmp_path)
    with pytest.raises(CompileError):
        compile_source("anything", llm_fn=fake_llm_no_neurolang,
                cache=cache, use_cache=False)


def test_compile_rejects_missing_flow_var(tmp_path):
    cache = CompilerCache(tmp_path)
    with pytest.raises(CompileError):
        compile_source("anything", llm_fn=fake_llm_no_flow_var,
                cache=cache, use_cache=False)


# --- Cache behavior ----------------------------------------------------------

def test_compile_caches_and_skips_llm_on_hit(tmp_path):
    cache = CompilerCache(tmp_path)
    calls = {"n": 0}

    def counting_llm(prompt, system, *, model, **kwargs):
        calls["n"] += 1
        return _GOOD_SOURCE

    # First call hits LLM
    src1 = compile_source("same prompt", llm_fn=counting_llm, output="source",
                    cache=cache, use_cache=True)
    assert calls["n"] == 1

    # Second call uses cache — no LLM
    src2 = compile_source("same prompt", llm_fn=counting_llm, output="source",
                    cache=cache, use_cache=True)
    assert calls["n"] == 1
    assert src1 == src2


def test_cache_keys_differ_for_different_prompts(tmp_path):
    cache = CompilerCache(tmp_path)
    k1 = cache.make_key("alpha", model="openai", library_version="0.0.1")
    k2 = cache.make_key("beta", model="openai", library_version="0.0.1")
    assert k1 != k2


def test_cache_keys_differ_for_different_models(tmp_path):
    cache = CompilerCache(tmp_path)
    k1 = cache.make_key("p", model="openai", library_version="0.0.1")
    k2 = cache.make_key("p", model="anthropic", library_version="0.0.1")
    assert k1 != k2


def test_cache_keys_differ_for_different_system_fingerprints(tmp_path):
    cache = CompilerCache(tmp_path)
    k1 = cache.make_key("p", model="openai", library_version="0.0.1", system_fingerprint="aabbccdd")
    k2 = cache.make_key("p", model="openai", library_version="0.0.1", system_fingerprint="11223344")
    assert k1 != k2


def test_cache_key_backward_compat_no_fingerprint(tmp_path):
    cache = CompilerCache(tmp_path)
    # system_fingerprint defaults to "" — existing callers with no fingerprint arg still work
    k1 = cache.make_key("p", model="openai", library_version="0.0.1")
    k2 = cache.make_key("p", model="openai", library_version="0.0.1", system_fingerprint="")
    assert k1 == k2


def test_compile_source_key_changes_when_system_prompt_changes(tmp_path, monkeypatch):
    """Patching _SYSTEM_PROMPT in compile module → different fingerprint → cache miss."""
    import neurolang.compile as compile_mod
    calls = {"n": 0}

    def counting_llm(prompt, system, *, model, kind, **_):
        calls["n"] += 1
        return _GOOD_SOURCE

    cache = CompilerCache(tmp_path)
    compile_source("my prompt", llm_fn=counting_llm, cache=cache, use_cache=True)
    assert calls["n"] == 1

    # Simulate a prompt change between sessions
    monkeypatch.setattr(compile_mod, "_SYSTEM_PROMPT", compile_mod._SYSTEM_PROMPT + "\n# changed")
    compile_source("my prompt", llm_fn=counting_llm, cache=cache, use_cache=True)
    assert calls["n"] == 2, "prompt change must cause a cache miss"


# --- Reverse decompile -------------------------------------------------------

def test_decompile_from_source(tmp_path):
    cache = CompilerCache(tmp_path)
    summary = decompile_summary(_GOOD_SOURCE, llm_fn=fake_llm_summary,
                        cache=cache, use_cache=False)
    assert "Doubles" in summary or "double" in summary.lower()


def test_decompile_from_flow_object(tmp_path):
    cache = CompilerCache(tmp_path)
    flow = _t_double | _t_add_one
    summary = decompile_summary(flow, llm_fn=fake_llm_summary,
                        cache=cache, use_cache=False)
    assert isinstance(summary, str) and len(summary) > 0


def test_decompile_rejects_bad_input(tmp_path):
    cache = CompilerCache(tmp_path)
    with pytest.raises(TypeError):
        decompile_summary(42, llm_fn=fake_llm_summary, cache=cache, use_cache=False)


# --- Strict-refs validation ---------------------------------------------

@neuro(name="webfake.search")
def _t_webfake_search(q: str) -> str:
    """Fake search."""
    return q


@neuro(name="webfake.scrape")
def _t_webfake_scrape(url: str) -> str:
    """Fake scrape."""
    return url


def test_strict_refs_passes_for_attribute_refs_in_registry():
    src = (
        "from neurolang import Flow\n"
        "from tests.test_compile import _t_webfake_search, _t_webfake_scrape\n"
        "import sys  # noqa\n"
        "flow = _t_webfake_search | _t_webfake_scrape\n"
    )
    findings = validate_source(src, strict_refs=True)
    assert findings.unknown_refs == []
    assert findings.suggestions == {}


def test_strict_refs_passes_for_bare_name_refs_in_registry():
    src = _GOOD_SOURCE  # uses bare _t_double, _t_add_one, both registered
    findings = validate_source(src, strict_refs=True)
    assert findings.unknown_refs == []


def test_strict_refs_flags_unknown_attribute_ref():
    # `email.fetch`: no `email` import, no `email.fetch` registered
    src = (
        "from neurolang import Flow\n"
        "flow = email.fetch\n"
    )
    findings = validate_source(src, strict_refs=True)
    assert "email.fetch" in findings.unknown_refs
    assert "email.fetch" in findings.suggestions  # suggestions dict has the key (may be empty list)


def test_strict_refs_allows_locally_defined_helper():
    # A locally-defined function used in the flow expression — accept,
    # defer to runtime if it's broken.
    src = (
        "from neurolang import Flow, neuro\n"
        "@neuro(register=False)\n"
        "def my_helper(x): return x\n"
        "flow = my_helper\n"
    )
    findings = validate_source(src, strict_refs=True)
    assert findings.unknown_refs == []


def test_strict_refs_allows_imported_module_attr_not_in_registry():
    # `web` imported but `web.foo_unknown` not registered: the head `web`
    # IS locally defined, so we accept (defer to runtime AttributeError).
    src = (
        "from neurolang import Flow\n"
        "from neurolang.stdlib import web\n"
        "flow = web.foo_unknown\n"
    )
    findings = validate_source(src, strict_refs=True)
    assert findings.unknown_refs == []


def test_strict_refs_default_off_for_validate_source():
    # Backward-compat: callers of validate_source() without the kwarg
    # don't pay for strict-mode work.
    src = (
        "from neurolang import Flow\n"
        "flow = email.fetch\n"
    )
    findings = validate_source(src)  # no strict_refs
    assert findings.unknown_refs == []


def test_compile_strict_refs_raises_with_message(tmp_path):
    # compile_source() hardcodes strict_refs=True. A source that references an
    # unknown neuro must raise CompileError with the unknown name and
    # suggestions in the message.
    cache = CompilerCache(tmp_path)

    def bad_llm(prompt, system, *, model, **kwargs):
        return (
            "from neurolang import Flow\n"
            "from neurolang.stdlib import web\n"
            "flow = web.search | webfake.serach\n"  # typo
        )

    with pytest.raises(CompileError) as ei:
        compile_source("anything", llm_fn=bad_llm, cache=cache, use_cache=False)

    msg = str(ei.value)
    assert "webfake.serach" in msg
    # Suggestion should mention the closest match
    assert "webfake.search" in msg
