"""Effect tracking and budget rollup."""
from neurolang import neuro, Effect, Budget


@neuro(effect="pure")
def pure_op(x):
    return x

@neuro(effect="llm", budget=Budget(latency_ms=2000, cost_usd=0.005))
def llm_op(x):
    return x

@neuro(effect="tool", budget=Budget(latency_ms=500, cost_usd=0.001))
def tool_op(x):
    return x


def test_effects_propagate_through_sequential():
    flow = pure_op | llm_op | tool_op
    eff = flow.effect_signature()
    assert eff == {"pure", "llm", "tool"}


def test_effects_propagate_through_parallel():
    flow = llm_op & tool_op
    eff = flow.effect_signature()
    assert eff == {"llm", "tool"}


def test_budget_sums_through_sequential():
    flow = llm_op | tool_op
    b = flow.cost_estimate()
    assert b.latency_ms == 2500
    assert abs(b.cost_usd - 0.006) < 1e-9


def test_pure_only_flow_has_zero_budget():
    flow = pure_op | pure_op
    b = flow.cost_estimate()
    assert b.latency_ms is None
    assert b.cost_usd is None


def test_budget_addition_handles_partial():
    a = Budget(cost_usd=0.01)
    b = Budget(latency_ms=1000)
    c = a + b
    assert c.cost_usd == 0.01
    assert c.latency_ms == 1000
