"""Recovery primitives — retry, fallback, escalate."""
import pytest

from neurolang import neuro, with_retry, with_fallback, with_escalation


def test_retry_eventually_succeeds():
    counter = {"n": 0}

    @neuro
    def flaky(x):
        counter["n"] += 1
        if counter["n"] < 3:
            raise RuntimeError("not yet")
        return x * 10

    retried = with_retry(flaky, attempts=5, backoff_s=0.0)
    # Note: retry returns a Neuro; call its underlying fn (it's async)
    import asyncio
    result = asyncio.run(retried.fn(7))
    assert result == 70
    assert counter["n"] == 3


def test_retry_gives_up_after_attempts():
    counter = {"n": 0}

    @neuro
    def always_fails(x):
        counter["n"] += 1
        raise RuntimeError("nope")

    retried = with_retry(always_fails, attempts=2, backoff_s=0.0)
    import asyncio
    with pytest.raises(RuntimeError):
        asyncio.run(retried.fn(1))
    assert counter["n"] == 2


def test_fallback_runs_on_failure():
    @neuro
    def primary(x):
        raise RuntimeError("primary down")

    @neuro
    def fallback(x):
        return f"fallback({x})"

    wrapped = with_fallback(primary, fallback)
    import asyncio
    assert asyncio.run(wrapped.fn(5)) == "fallback(5)"


def test_fallback_skipped_on_success():
    @neuro
    def primary(x):
        return f"primary({x})"

    @neuro
    def fallback(x):
        return f"fallback({x})"

    wrapped = with_fallback(primary, fallback)
    import asyncio
    assert asyncio.run(wrapped.fn(5)) == "primary(5)"


def test_escalation_invoked_on_failure():
    @neuro
    def primary(x):
        raise ValueError("oops")

    captured = {}

    def escalate(exc, args, kwargs):
        captured["exc"] = exc
        captured["args"] = args
        return "escalated"

    wrapped = with_escalation(primary, escalate_to=escalate)
    import asyncio
    assert asyncio.run(wrapped.fn(42)) == "escalated"
    assert isinstance(captured["exc"], ValueError)
    assert captured["args"] == (42,)
