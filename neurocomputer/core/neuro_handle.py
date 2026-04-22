"""NeuroHandle — lazy proxy returned to class-neuros via `uses` injection.

Calling `handle.run(state, **kw)` dispatches through the factory, preserving
hot-reload (the factory resolves the neuro by name each call, so edited
code on disk takes effect without rebuilding the parent instance).
"""


class NeuroHandle:
    __slots__ = ("_factory", "name")

    def __init__(self, factory, name):
        self._factory = factory
        self.name = name

    async def run(self, state, **kw):
        return await self._factory.run(self.name, state, **kw)

    def __repr__(self):
        return f"NeuroHandle({self.name!r})"
