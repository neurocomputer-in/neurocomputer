"""Plan immutability, hashing, serialization, replay."""
from neurolang import neuro, Plan


@neuro
def double(n: int) -> int:
    return n * 2


@neuro
def add_three(n: int) -> int:
    return n + 3


def test_plan_hash_stable_for_same_inputs():
    flow = double | add_three
    p1 = flow.plan(5)
    p2 = flow.plan(5)
    assert p1.hash() == p2.hash()


def test_plan_hash_changes_with_inputs():
    flow = double | add_three
    assert flow.plan(5).hash() != flow.plan(6).hash()


def test_plan_serialize_includes_neuros_and_args():
    flow = double | add_three
    plan = flow.plan(5)
    s = plan.serialize()
    assert "neuros" in s
    assert "hash" in s
    assert "args_repr" in s
    assert s["args_repr"] == ["5"]


def test_plan_run_and_replay_pure():
    flow = double | add_three
    plan = flow.plan(7)
    r1 = plan.run()
    r2 = plan.replay()
    assert r1 == r2 == add_three(double(7))


def test_plan_steps_listing():
    flow = double | add_three
    plan = flow.plan(1)
    names = [s.name.split(".")[-1] for s in plan.steps]
    assert names == ["double", "add_three"]
