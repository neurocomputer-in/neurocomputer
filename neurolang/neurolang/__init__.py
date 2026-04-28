"""NeuroLang — the Python framework for AI-native agentic coding.

Public API:
    Neuro, neuro          — the typed unit + decorator
    Flow                  — composition; built via | & + operators
    Plan                  — first-class execution plan
    Memory                — scoped storage
    Effect                — effect categories
    Budget                — cost / latency annotations
    register              — register a custom neuro
    LocalNeuroNet         — minimal in-process runtime
    NeuroNet              — runtime Protocol
    with_retry, with_fallback, with_escalation — recovery primitives
    compile_source        — NL prompt → NeuroLang Python
    decompile_summary     — NeuroLang Python → NL summary
    propose_plan          — NL prompt → ProposedPlan (catalog-grounded)
    discover_neuros       — eager filesystem scan + import of user neuros
"""
from .neuro import Neuro, NeuroLike, neuro
from .flow import Flow, Step, Sequential, Parallel
from .plan import Plan
from .memory import Memory, MemoryLike, LocalMemory
from .effect import Effect
from .budget import Budget, ZERO_BUDGET
from .registry import default_registry, register
from .recovery import with_retry, with_fallback, with_escalation
from .runtime import NeuroNet, LocalNeuroNet, current_memory

__version__ = "0.0.1"

# `compile_source` and `decompile_summary` need __version__ to be defined first
from .compile import compile_source, decompile_summary, CompileError  # noqa: E402
from .discover import discover_neuros, DiscoveryReport, find_project_root  # noqa: E402
from .propose import (  # noqa: E402
    propose_plan, ProposedPlan, NeuroChoice, MissingCapability, ProposeError,
)

__all__ = [
    # Core
    "Neuro", "NeuroLike", "neuro",
    "Flow", "Step", "Sequential", "Parallel",
    "Plan",
    "Memory", "MemoryLike", "LocalMemory",
    "Effect",
    "Budget", "ZERO_BUDGET",
    # Registry
    "default_registry", "register",
    # Recovery
    "with_retry", "with_fallback", "with_escalation",
    # Runtime
    "NeuroNet", "LocalNeuroNet", "current_memory",
    # Compiler
    "compile_source", "decompile_summary", "CompileError",
    # Discovery
    "discover_neuros", "DiscoveryReport", "find_project_root",
    # Propose
    "propose_plan", "ProposedPlan", "NeuroChoice", "MissingCapability", "ProposeError",
    # Meta
    "__version__",
]
