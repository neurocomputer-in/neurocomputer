"""Render a Flow as a Mermaid flowchart.

Usage:
    flow.to_mermaid()  # returns a Mermaid source string
"""
from __future__ import annotations

from typing import Any


def to_mermaid(flow) -> str:
    """Return Mermaid `flowchart TD` source describing the flow's topology."""
    from ..flow import Sequential, Parallel, Step

    lines = ["flowchart TD"]
    counter = {"i": 0}

    def fresh_id() -> str:
        counter["i"] += 1
        return f"n{counter['i']}"

    def short_name(neuro) -> str:
        return neuro.name.split(".")[-1]

    def emit(step) -> tuple[str, str]:
        """Render a step. Returns (entry_id, exit_id) — for sequential
        chaining, the entry is what input flows into and the exit is what
        comes out."""
        if step.is_leaf:
            nid = fresh_id()
            label = short_name(step.neuro)
            eff = ",".join(sorted(e.value for e in step.neuro.effects))
            lines.append(f'    {nid}["{label}<br/><i>{eff}</i>"]')
            return nid, nid

        if isinstance(step, Sequential):
            prev_exit = None
            entry = None
            for c in step.children:
                cin, cout = emit(c)
                if entry is None:
                    entry = cin
                if prev_exit is not None:
                    lines.append(f"    {prev_exit} --> {cin}")
                prev_exit = cout
            return entry, prev_exit

        if isinstance(step, Parallel):
            fan_in = fresh_id()
            fan_out = fresh_id()
            label = "AND" if step.strategy == "and" else "OR"
            lines.append(f'    {fan_in}(("{label} in"))')
            lines.append(f'    {fan_out}(("{label} out"))')
            for c in step.children:
                cin, cout = emit(c)
                lines.append(f"    {fan_in} --> {cin}")
                lines.append(f"    {cout} --> {fan_out}")
            return fan_in, fan_out

        # Unknown step type — just label it
        nid = fresh_id()
        lines.append(f'    {nid}["{type(step).__name__}"]')
        return nid, nid

    emit(flow.root)
    return "\n".join(lines)
