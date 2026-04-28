"""Runtime — the layer that actually executes NeuroLang programs.

Phase 1 ships a minimal in-process runtime (`LocalNeuroNet`) so the
library is usable standalone. Production runtimes live in environments
like Neurocomputer that implement the same `NeuroNet` Protocol.
"""
from .protocol import NeuroNet
from .local import LocalNeuroNet
from .context import current_memory, set_active_memory

__all__ = ["NeuroNet", "LocalNeuroNet", "current_memory", "set_active_memory"]
