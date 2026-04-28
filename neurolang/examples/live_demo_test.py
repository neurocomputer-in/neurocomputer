#!/usr/bin/env python3
"""NeuroLang live capability demo — real LLM calls, no mocks.

Run: cd /home/ubuntu/neurolang && python examples/live_demo_test.py
"""
import json
import sys

sys.path.insert(0, "/home/ubuntu/neurolang")

import neurolang  # noqa: F401 — triggers stdlib registration
from neurolang import Memory, default_registry
from neurolang.stdlib import reason, memory_neuros

ARTICLE = (
    "Transformer architecture, introduced in 'Attention Is All You Need' (2017), "
    "replaced recurrent networks with self-attention. This allowed massively parallel "
    "training and led to GPT, BERT, and modern LLMs. The key insight: attention weights "
    "let each token attend to every other token in a sequence, capturing long-range "
    "dependencies without sequential bottlenecks."
)

FEEDBACK = "I waited 45 minutes and the food arrived cold. Staff were rude when I complained."
SHORT_TOPIC = "ways to make developer onboarding faster"


def sep(label):
    print(f"\n{'=' * 62}")
    print(f"  {label}")
    print("=" * 62)


# ─── 1. reason.summarize ──────────────────────────────────────────────────────
sep("1. reason.summarize  (max_words=20)")
print(f"Input: {ARTICLE[:90]}...")
result = reason.summarize(ARTICLE, max_words=20)
print(f"Output: {result!r}")
assert isinstance(result, str) and len(result) > 0, "summarize returned empty"
print("✅ PASS")

# ─── 2. reason.classify ───────────────────────────────────────────────────────
sep("2. reason.classify")
cases = [
    (FEEDBACK, ["positive", "negative", "neutral"]),
    ("The Fed raised rates by 50bps today.", ["finance", "politics", "sports", "tech"]),
    ("Researchers demo a new quantum error-correction protocol.", ["finance", "science", "sports", "tech"]),
]
for text, labels in cases:
    out = reason.classify(text, labels=labels)
    status = "✅" if out in labels else "⚠️ (not in labels)"
    print(f"  {status}  {text[:55]!r}")
    print(f"        → {out!r}  (labels={labels})")

# ─── 3. reason.brainstorm ─────────────────────────────────────────────────────
sep("3. reason.brainstorm  (n=3)")
print(f"Topic: {SHORT_TOPIC!r}")
bullets = reason.brainstorm(SHORT_TOPIC, n=3)
print(bullets)
lines = [l for l in bullets.split("\n") if l.strip()]
print(f"✅ PASS — got {len(lines)} non-empty lines")

# ─── 4. Sequential flow: summarize | brainstorm ───────────────────────────────
sep("4. Sequential flow: reason.summarize | reason.brainstorm")
flow_seq = reason.summarize | reason.brainstorm
print(f"Flow repr:  {flow_seq}")
print(f"Budget:     latency={flow_seq.budget().latency_ms}ms  cost=${flow_seq.budget().cost_usd:.4f}")
print(f"Effects:    {flow_seq.effects()}")
print(f"\nMermaid:\n{flow_seq.to_mermaid()}")
print("\nRunning flow_seq.run(ARTICLE) ...")
print("  Step 1: summarize article → short summary")
print("  Step 2: brainstorm(summary) → angles on the summary topic")
seq_result = flow_seq.run(ARTICLE)
print(f"\nFinal output:\n{seq_result}")
assert isinstance(seq_result, str) and len(seq_result) > 0, "sequential flow returned empty"
print("✅ PASS")

# ─── 5. Parallel flow: summarize & brainstorm ─────────────────────────────────
sep("5. Parallel flow: reason.summarize & reason.brainstorm")
flow_par = reason.summarize & reason.brainstorm
print(f"Flow repr:  {flow_par}")
print(f"Budget:     latency={flow_par.budget().latency_ms}ms  cost=${flow_par.budget().cost_usd:.4f}")
print(f"\nMermaid:\n{flow_par.to_mermaid()}")
print("\nRunning flow_par.run(ARTICLE) — both get ARTICLE as input, run concurrently ...")
par_result = flow_par.run(ARTICLE)
summary_part, bullets_part = par_result
print(f"\nSummary branch:\n  {summary_part!r}")
print(f"\nBrainstorm branch:\n{bullets_part}")
assert isinstance(summary_part, str) and isinstance(bullets_part, str), "parallel flow type error"
print("✅ PASS")

# ─── 6. Memory neuros ─────────────────────────────────────────────────────────
sep("6. memory_neuros.store + recall")
mem = Memory.discrete()
memory_neuros.store.run("Build NeuroLang agentic OS for individuals", key="goal", memory=mem)
memory_neuros.store.run("Phase 1.7 — multi-provider LLM registry", key="current_phase", memory=mem)

goal = memory_neuros.recall.run(key="goal", memory=mem)
phase = memory_neuros.recall.run(key="current_phase", memory=mem)
missing = memory_neuros.recall.run(key="nonexistent", default="(not found)", memory=mem)

print(f"  stored+recalled goal:          {goal!r}")
print(f"  stored+recalled current_phase: {phase!r}")
print(f"  missing key default:           {missing!r}")

assert goal == "Build NeuroLang agentic OS for individuals", "store/recall mismatch"
assert missing == "(not found)", "default not returned"
print("✅ PASS")

# ─── 7. Registry introspection ────────────────────────────────────────────────
sep("7. Registry introspection")
llm_neuros = default_registry.by_effect("llm")
print(f"LLM-effect neuros ({len(llm_neuros)}):")
for n in llm_neuros:
    print(f"  {n.name}  budget=latency:{n.budget.latency_ms}ms cost:${n.budget.cost_usd:.4f}")

reason_neuros = default_registry.by_kind("skill.reason")
print(f"\nkind=skill.reason ({len(reason_neuros)}): {[n.name.split('.')[-1] for n in reason_neuros]}")

search_hits = default_registry.search("summarize")
print(f"search('summarize'): {[n.name.split('.')[-1] for n in search_hits]}")
assert len(llm_neuros) >= 4, f"expected >=4 LLM neuros, got {len(llm_neuros)}"
print("✅ PASS")

# ─── 8. Plan introspection ────────────────────────────────────────────────────
sep("8. Plan introspection")
p = reason.summarize.plan(ARTICLE, max_words=15)
print(f"Plan hash:   {p.hash()}")
print(f"Effects:     {p.effect_signature()}")
serialized = p.serialize()
print(f"Serialized:\n{json.dumps(serialized, indent=2)}")
assert len(p.hash()) == 16, "hash should be 16 hex chars"
print("✅ PASS")

# ─── 9. reason.deep_research ──────────────────────────────────────────────────
sep("9. reason.deep_research  (depth='standard')")
question = "What are the main architectural tradeoffs between transformer and SSM (state space model) based LLMs?"
print(f"Question: {question}")
print("Running... (this is the slowest call — scaffolded multi-step prompt)")
research = reason.deep_research(question, depth="standard")
print(f"\n{research}")
word_count = len(research.split())
print(f"\nWord count: {word_count}")
assert word_count > 100, f"expected >100 words, got {word_count}"
print("✅ PASS")

# ─── Done ─────────────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("  ALL SECTIONS COMPLETE")
print("=" * 62)
