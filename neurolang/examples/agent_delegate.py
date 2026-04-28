"""Demo: a flow whose middle step is a sub-agent that figures out its own
pipeline at runtime. The outer author specifies WHAT the sub-task is, not
WHICH neuros to use. Requires a live LLM (default: opencode-zen).

Run: python examples/agent_delegate.py
"""
from __future__ import annotations

import sys

sys.path.insert(0, "/home/ubuntu/neurolang")

import neurolang  # noqa: F401  — registers stdlib
from neurolang import neuro
from neurolang.stdlib import agent


@neuro(effect="pure", register=False)
def passthrough(text: str) -> str:
    return text


# The middle step decides its own implementation. The outer author only
# specifies WHAT the sub-task is — not WHICH neuros to use. The catalog
# filter scopes the sub-agent to reason.* neuros so it can't wander.
flow = passthrough | agent.delegate(
    "given input text, produce a two-sentence summary of it",
    catalog=["neurolang.stdlib.reason.*"],
)

ARTICLE = (
    "Recurrent neural networks (RNNs) processed sequences token by token, "
    "which made training slow and limited context length. The 2017 transformer "
    "paper replaced recurrence with self-attention, letting every token attend "
    "to every other token in parallel. This unlocked the modern era of LLMs: "
    "GPT, BERT, and the trillion-parameter scale beyond."
)

print("=== flow ===")
print(flow)
print("\n=== flow.to_mermaid() ===")
print(flow.to_mermaid())
print("\n=== sub-agent figures out its own pipeline now ===\n")
result = flow.run(ARTICLE)
print(result)
