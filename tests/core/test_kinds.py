import pytest
from core.kinds import parse_kind, Kind, KNOWN_NAMESPACES


def test_plain_namespace_defaults_to_leaf_for_skill():
    k = parse_kind("skill")
    assert k.namespace == "skill"
    assert k.subtype == "leaf"
    assert k.full == "skill.leaf"


def test_dotted_kind_roundtrip():
    k = parse_kind("prompt.block")
    assert k.namespace == "prompt"
    assert k.subtype == "block"
    assert k.full == "prompt.block"


def test_three_segment_kind():
    k = parse_kind("skill.flow.sequential")
    assert k.namespace == "skill"
    assert k.subtype == "flow"
    assert k.variant == "sequential"
    assert k.full == "skill.flow.sequential"


def test_none_or_empty_defaults_to_skill_leaf():
    assert parse_kind(None).full == "skill.leaf"
    assert parse_kind("").full == "skill.leaf"


def test_legacy_aliases_map_to_canonical():
    assert parse_kind("sequential_flow").full == "skill.flow.sequential"
    assert parse_kind("parallel_flow").full == "skill.flow.parallel"
    assert parse_kind("dag_flow").full == "skill.flow.dag"


def test_unknown_namespace_is_permissive():
    k = parse_kind("weirdkind.subtype")
    # permissive: parser doesn't reject; validator flags
    assert k.namespace == "weirdkind"
    assert k.is_known() is False


def test_known_namespaces_all_recognized():
    for ns in ("skill", "prompt", "memory", "context", "model",
              "instruction", "agent", "library"):
        assert ns in KNOWN_NAMESPACES
        assert parse_kind(ns).is_known() is True
