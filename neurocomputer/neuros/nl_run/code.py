import importlib.util
from typing import Any, Dict


async def run(state: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    path = kwargs.get("path") or state.get("path") or ""
    if not path:
        return {"error": "nl_run: no path provided"}
    input_val = kwargs.get("input") or state.get("input")
    try:
        spec = importlib.util.spec_from_file_location("_nl_flow", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        flow = getattr(mod, "flow", None)
        if flow is None:
            return {"error": f"nl_run: no 'flow' symbol in {path}"}
        run_fn = getattr(flow, "run_async", None) or getattr(flow, "run", None)
        if run_fn is None:
            return {"error": f"nl_run: flow has no run/run_async method"}
        import asyncio, inspect
        if inspect.iscoroutinefunction(run_fn):
            result = await run_fn(input_val)
        else:
            result = await asyncio.get_event_loop().run_in_executor(None, run_fn, input_val)
    except Exception as exc:
        return {"error": str(exc)}
    return {"result": result}
