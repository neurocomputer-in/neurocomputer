"""BaseNeuro — abstract parent for every neuro.

Two authoring forms:
  1. Function form (today's common shape): module-level `async def run(state, **kw)`.
     The factory wraps this via FnEntry.build_instance() → synthesized subclass.
  2. Class form (new): `class X(BaseNeuro)` with `async def run(self, state, **kw)`.

Legacy-compat: `BaseNeuro(name, fn, inputs, outputs, desc="")` still works —
it constructs a wrapper instance whose `run` delegates to the passed fn.
This keeps the current `NeuroFactory._load` call site working unchanged
until Phase C.4 introduces the ClassEntry / FnEntry dispatch.

Spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/01-primitive-class-vs-fn.md
"""
import inspect


class BaseNeuro:
    # Class-level metadata populated by the factory after instantiation.
    name: str = ""
    desc: str = ""
    inputs: list = []
    outputs: list = []
    uses: list = []
    children: list = []
    scope: str = "session"

    # Runtime-resolved factory handle (set by factory for class form).
    factory = None

    def __init__(self, *args, **kwargs):
        """Supports both forms:

        - Legacy: BaseNeuro(name, fn, inputs, outputs, desc="")
        - Class subclass: pass no args (or passthrough kwargs).
        """
        if args and callable(args[1] if len(args) > 1 else None):
            # Legacy positional form from NeuroFactory._load.
            name, fn, *rest = args
            inputs  = rest[0] if len(rest) > 0 else kwargs.get("inputs", [])
            outputs = rest[1] if len(rest) > 1 else kwargs.get("outputs", [])
            desc    = rest[2] if len(rest) > 2 else kwargs.get("desc", "")
            self._legacy_fn = fn
            sig = inspect.signature(fn)
            self._accepts_var_kw = any(
                p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
            )
            self._accepted = set(sig.parameters.keys()) - {"state"}
            self.name = name
            self.desc = desc
            self.inputs = inputs
            self.outputs = outputs
        else:
            # Class form: no legacy fn, subclass must override `run`.
            self._legacy_fn = None
            self._accepts_var_kw = False
            self._accepted = set()
            for k, v in kwargs.items():
                setattr(self, k, v)

    async def run(self, state, **kw):
        legacy = getattr(self, "_legacy_fn", None)
        if legacy is None:
            raise NotImplementedError(
                f"{type(self).__name__}.run must be overridden"
            )
        if self._accepts_var_kw:
            safe = kw
        else:
            safe = {k: v for k, v in kw.items() if k in self._accepted}
        return await legacy(state, **safe)


class FnEntry:
    """Internal wrapper that converts a top-level `async def run` into a
    one-off BaseNeuro subclass instance on demand. Used by the new load
    path in `core/neuro_factory.py` (Phase C.4).
    """

    def __init__(self, fn, conf):
        self.fn = fn
        self.conf = conf
        sig = inspect.signature(fn)
        self._accepts_var_kw = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )
        self._accepted = set(sig.parameters.keys()) - {"state"}

    def filter_kwargs(self, kw):
        if self._accepts_var_kw:
            return kw
        return {k: v for k, v in kw.items() if k in self._accepted}

    def build_instance(self):
        fn = self.fn
        accepted = self._accepted
        accepts_var_kw = self._accepts_var_kw

        class _Fn(BaseNeuro):
            async def run(self, state, **kw):
                if accepts_var_kw:
                    safe = kw
                else:
                    safe = {k: v for k, v in kw.items() if k in accepted}
                return await fn(state, **safe)

        inst = _Fn()
        inst.name = self.conf.get("name", "")
        inst.desc = self.conf.get("description", "")
        inst.inputs = self.conf.get("inputs", [])
        inst.outputs = self.conf.get("outputs", [])
        return inst
