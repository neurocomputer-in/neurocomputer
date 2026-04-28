"""Property tests for the categorical laws of NeuroLang composition.

These verify the operators behave as a category — i.e., associativity
and identity hold up to behavioral equivalence (same input → same output).
"""
from neurolang import neuro, Flow, Plan


@neuro
def f(x: int) -> int:
    return x + 1

@neuro
def g(x: int) -> int:
    return x * 2

@neuro
def h(x: int) -> int:
    return x - 3


def test_sequential_associativity():
    """(f | g) | h  ≡  f | (g | h) — same outputs for any input."""
    left = (f | g) | h
    right = f | (g | h)
    for n in range(-5, 6):
        assert left.run(n) == right.run(n), f"Mismatch at {n}: {left.run(n)} vs {right.run(n)}"


def test_sequential_no_op_identity():
    """Adding a no-op identity neuro produces the same result."""
    @neuro
    def identity(x):
        return x
    left = f | identity
    right = f
    for n in range(-3, 4):
        assert left.run(n) == right.run(n)


def test_parallel_and_returns_tuple():
    """A & B yields a tuple of both results."""
    flow = f & g
    assert flow.run(10) == (11, 20)


def test_parallel_and_associativity():
    """(f & g) & h is structurally a tuple-of-three (modulo nesting)."""
    flow = (f & g) & h
    result = flow.run(10)
    # Result is ((f(10), g(10)), h(10)) → ((11, 20), 7)
    assert result == ((11, 20), 7)


def test_neuro_then_flow():
    """A Neuro can compose with a Flow on either side."""
    inner = g | h
    flow_left = f | inner
    flow_right = inner | f
    assert flow_left.run(5) == h(g(f(5)))
    assert flow_right.run(5) == f(h(g(5)))
