"""IDE API routes — shared by server.py and scripts/ide_server.py.

Both servers just call `register_ide_routes(app)` to attach the same
endpoints. One NeuroFactory instance is shared across them for
library reads + AI-modify writes.

Endpoints (all under /api/...):
    GET  /api/ide/health              — liveness
    GET  /api/neuros                  — factory.describe() list
    GET  /api/neuros/{name}           — describe + conf/code/prompt src
    GET  /api/kinds                   — {namespace: [names]}
    GET  /api/categories              — {category: [names]}
    GET  /api/snapshots/{name}        — dev_pipeline list_snapshots
    POST /api/neuros/validate         — dev_pipeline validate op
    POST /api/neuros/save             — dev_pipeline save op
    POST /api/neuros/{name}/rollback  — dev_pipeline rollback
    POST /api/modify                  — ide_assistant natural-language edit
"""
import json
import pathlib
from fastapi import FastAPI, HTTPException, Request

from core.neuro_factory import NeuroFactory


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

_factory = None


def _get_factory() -> NeuroFactory:
    global _factory
    if _factory is None:
        _factory = NeuroFactory(dir=str(REPO_ROOT / "neuros"))
        print(f"[ide_api] loaded {len(_factory.reg)} neuros")
    return _factory


def register_ide_routes(app: FastAPI) -> None:
    """Attach IDE endpoints to a FastAPI app. Idempotent-ish; calling
    twice just re-adds routes (FastAPI allows duplicates — avoid)."""

    @app.get("/api/ide/health")
    async def ide_health():
        f = _get_factory()
        return {"ok": True, "neuros": len(f.reg)}

    @app.get("/api/neuros")
    async def list_neuros():
        return {"neuros": _get_factory().describe()}

    @app.get("/api/neuros/{name}")
    async def get_neuro(name: str):
        f = _get_factory()
        if name not in f.reg:
            raise HTTPException(404, f"neuro {name!r} not found")
        describe = next((e for e in f.describe() if e["name"] == name), None)
        entry = f.reg[name]
        folder = getattr(entry, "folder", None)
        if folder is None:
            # Fallback: name-based flat path
            folder = REPO_ROOT / "neuros" / name
        conf_src = _read(folder / "conf.json") if folder else None
        code_src = _read(folder / "code.py") if folder else None
        prompt_src = _read(folder / "prompt.txt") if folder else None
        layout = _read_json(folder / "layout.json") if folder else None
        return {
            "describe":   describe,
            "conf_src":   conf_src,
            "code_src":   code_src,
            "prompt_src": prompt_src,
            "layout":     layout,
            "folder":     str(folder) if folder else None,
        }

    @app.get("/api/kinds")
    async def grouped_by_kind():
        groups: dict = {}
        for e in _get_factory().describe():
            ns = e.get("kind_namespace") or "misc"
            groups.setdefault(ns, []).append(e["name"])
        return {"kinds": groups}

    @app.get("/api/categories")
    async def grouped_by_category():
        groups: dict = {}
        for e in _get_factory().describe():
            cat = e.get("category") or "uncategorized"
            groups.setdefault(cat, []).append(e["name"])
        return {"categories": groups}

    @app.get("/api/snapshots/{name}")
    async def snapshots(name: str):
        f = _get_factory()
        out = await f.run("dev_pipeline", {"__cid": "ide"},
                          op="list_snapshots", neuro_name=name)
        return out

    @app.post("/api/neuros/validate")
    async def validate_neuro_ep(req: Request):
        body = await req.json()
        f = _get_factory()
        out = await f.run("dev_pipeline", {"__cid": "ide"},
                          op="validate",
                          conf=body.get("conf"),
                          code=body.get("code"),
                          author=body.get("author", "ai"))
        return out

    @app.post("/api/neuros/save")
    async def save_neuro_ep(req: Request):
        body = await req.json()
        name = body.get("neuro_name") or body.get("name")
        if not name:
            raise HTTPException(400, "neuro_name required")
        f = _get_factory()
        out = await f.run("dev_pipeline", {"__cid": "ide"},
                          op="save",
                          neuro_name=name,
                          conf=body.get("conf"),
                          code=body.get("code"),
                          prompt=body.get("prompt"),
                          author=body.get("author", "ai"))
        return out

    @app.post("/api/neuros/{name}/rollback")
    async def rollback_neuro_ep(name: str, req: Request):
        body = {}
        try:
            body = await req.json()
        except Exception:
            pass
        f = _get_factory()
        out = await f.run("dev_pipeline", {"__cid": "ide"},
                          op="rollback", neuro_name=name,
                          snapshot_ts=body.get("snapshot_ts"))
        return out

    @app.delete("/api/neuros/{name}")
    async def delete_neuro_ep(name: str):
        f = _get_factory()
        if name not in f.reg:
            raise HTTPException(404, f"neuro {name!r} not found")
        # Resolve the actual on-disk folder (taxonomized paths aren't the name)
        folder = getattr(f.reg[name], "folder", None)
        out = await f.run("dev_pipeline", {"__cid": "ide"},
                          op="delete",
                          neuro_name=name,
                          folder=str(folder) if folder else None)
        if out.get("ok"):
            # Drop from factory registry so it disappears from /api/neuros immediately
            f.reg.pop(name, None)
        return out

    @app.post("/api/modify")
    async def ai_modify(req: Request):
        body = await req.json()
        user_request = body.get("user_request") or body.get("request")
        if not user_request:
            raise HTTPException(400, "user_request required")
        target = body.get("target_neuro")
        max_retries = int(body.get("max_retries", 2))
        state = {"__cid": "ide", "__agent_id": "ide"}
        f = _get_factory()
        out = await f.run("ide_assistant", state,
                          user_request=user_request,
                          target_neuro=target,
                          max_retries=max_retries)
        return out


# ── helpers ─────────────────────────────────────────────────────────

def _read(p: pathlib.Path):
    try:
        return p.read_text(encoding="utf-8") if p.exists() else None
    except OSError:
        return None


def _read_json(p: pathlib.Path):
    txt = _read(p)
    if not txt:
        return None
    try:
        return json.loads(txt)
    except (json.JSONDecodeError, ValueError):
        return None
