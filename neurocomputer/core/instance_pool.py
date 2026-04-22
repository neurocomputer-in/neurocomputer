"""InstancePool — keyed cache of class-neuro instances.

Scope keys:
  call       → never pooled (fresh instance each get)
  session    → keyed by state["__cid"]
  agent      → keyed by state["__agent_id"]
  singleton  → single instance per factory

Spec: docs/superpowers/specs/2026-04-20-neuro-arch/01-core/05-factory-and-executor.md §3.2
"""
import asyncio


class InstancePool:
    def __init__(self, factory):
        self._factory = factory
        self._instances: dict = {}
        self._locks: dict = {}

    async def get(self, entry, state):
        scope = entry.scope or "session"
        if scope == "call":
            return await self._create(entry, state)
        key = (entry.name, self._scope_key(scope, state))
        if key in self._instances:
            return self._instances[key]
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            if key not in self._instances:
                self._instances[key] = await self._create(entry, state)
        return self._instances[key]

    async def invalidate(self, name):
        """Called by hot-reload to drop cached instances of `name`."""
        victims = [k for k in list(self._instances) if k[0] == name]
        for k in victims:
            inst = self._instances.pop(k)
            td = getattr(inst, "teardown", None)
            if td:
                try:
                    result = td()
                    if hasattr(result, "__await__"):
                        await result
                except Exception:
                    pass

    def _scope_key(self, scope, state):
        if scope == "session":
            return state.get("__cid", "_nosess")
        if scope == "agent":
            return state.get("__agent_id", "_default")
        if scope == "singleton":
            return "_singleton"
        raise ValueError(f"unknown scope {scope!r}")

    async def _create(self, entry, state):
        inst = entry.cls()
        inst.name = entry.name
        inst.factory = self._factory

        from core.neuro_handle import NeuroHandle
        deps = list(getattr(inst, "uses", []) or entry.conf.get("uses", []))
        for dep in deps:
            if dep not in self._factory.reg:
                raise RuntimeError(
                    f"neuro {entry.name!r} declares use of "
                    f"{dep!r} which is not registered"
                )
            setattr(inst, dep, NeuroHandle(self._factory, dep))

        setup = getattr(inst, "setup", None)
        if setup:
            result = setup()
            if hasattr(result, "__await__"):
                await result
        return inst
