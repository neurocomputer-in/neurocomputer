"""Rendering tests."""
from neurolang import neuro


@neuro
def a(x): return x

@neuro
def b(x): return x

@neuro
def c(x): return x


def test_mermaid_sequential():
    flow = a | b | c
    out = flow.to_mermaid()
    assert out.startswith("flowchart TD")
    assert "a" in out and "b" in out and "c" in out
    # arrows present
    assert "-->" in out


def test_mermaid_parallel_and():
    flow = a & b
    out = flow.to_mermaid()
    assert "AND in" in out and "AND out" in out


def test_mermaid_parallel_or():
    flow = a + b
    out = flow.to_mermaid()
    assert "OR in" in out and "OR out" in out


def test_mermaid_via_render_method():
    flow = a | b
    assert flow.render(format="mermaid") == flow.to_mermaid()
