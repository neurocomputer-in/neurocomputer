#!/usr/bin/env python3
"""ide_server — read+write API for the 3D IDE.

Separate process from server.py (port 7000, untouched). Runs on 8000
by default. Serves the neuro library + per-neuro source + write
pipeline to the frontend.

Endpoints:
    GET  /api/health               — liveness
    GET  /api/neuros               — factory.describe() list (rich)
    GET  /api/neuros/{name}        — {describe, conf_src, code_src, prompt_src?}
    GET  /api/kinds                — grouped: {namespace: [name, ...]}
    GET  /api/categories           — grouped: {category: [name, ...]}
    POST /api/neuros/validate      — dev_pipeline validate
    POST /api/neuros/save          — dev_pipeline save
    POST /api/neuros/{name}/rollback — dev_pipeline rollback
    GET  /api/snapshots/{name}     — list available snapshots
    WS   /ws/neuros                — broadcast hot-reload events (future)

CORS open to everything for dev. Tighten before exposing publicly.

Run:
    python3 scripts/ide_server.py [--port 8000]
"""
import argparse
import asyncio
import json
import pathlib
import sys
from contextlib import asynccontextmanager

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware


_factory = None  # type: ignore


@asynccontextmanager
async def _lifespan(app):
    global _factory
    from core.neuro_factory import NeuroFactory
    _factory = NeuroFactory(dir=str(REPO_ROOT / "neuros"))
    print(f"[ide_server] loaded {len(_factory.reg)} neuros")
    yield


app = FastAPI(title="neurocomputer IDE API", lifespan=_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── read endpoints ─────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"ok": True, "neuros": len(_factory.reg) if _factory else 0}


@app.get("/api/neuros")
async def list_neuros():
    return {"neuros": _factory.describe()}


@app.get("/api/neuros/{name}")
async def get_neuron(name: str):
    if name not in _factory.reg:
        raise HTTPException(404, f"neuro {name!r} not found")
    describe = next((e for e in _factory.describe() if e["name"] == name), None)
    folder = REPO_ROOT / "neuros" / name
    conf_src = _read(folder / "conf.json")
    code_src = _read(folder / "code.py")
    prompt_src = _read(folder / "prompt.txt")
    layout = _read_json(folder / "layout.json")
    return {
        "describe":   describe,
        "conf_src":   conf_src,
        "code_src":   code_src,
        "prompt_src": prompt_src,
        "layout":     layout,
    }


@app.get("/api/kinds")
async def grouped_by_kind():
    groups: dict = {}
    for e in _factory.describe():
        ns = e.get("kind_namespace") or "misc"
        groups.setdefault(ns, []).append(e["name"])
    return {"kinds": groups}


@app.get("/api/categories")
async def grouped_by_category():
    groups: dict = {}
    for e in _factory.describe():
        cat = e.get("category") or "uncategorized"
        groups.setdefault(cat, []).append(e["name"])
    return {"categories": groups}


@app.get("/api/snapshots/{name}")
async def snapshots(name: str):
    out = await _factory.run("dev_pipeline", {"__cid": "ide"},
                             op="list_snapshots", neuro_name=name)
    return out


# ── write endpoints (guarded by dev_pipeline) ─────────────────────

@app.post("/api/neuros/validate")
async def validate_neuro(req: Request):
    body = await req.json()
    out = await _factory.run("dev_pipeline", {"__cid": "ide"},
                             op="validate",
                             conf=body.get("conf"),
                             code=body.get("code"),
                             author=body.get("author", "ai"))
    return out


@app.post("/api/neuros/save")
async def save_neuro(req: Request):
    body = await req.json()
    neuro_name = body.get("neuro_name") or body.get("name")
    if not neuro_name:
        raise HTTPException(400, "neuro_name required")
    out = await _factory.run("dev_pipeline", {"__cid": "ide"},
                             op="save",
                             neuro_name=neuro_name,
                             conf=body.get("conf"),
                             code=body.get("code"),
                             prompt=body.get("prompt"),
                             author=body.get("author", "ai"))
    return out


@app.post("/api/neuros/{name}/rollback")
async def rollback_neuro(name: str, req: Request):
    body = {}
    try:
        body = await req.json()
    except Exception:
        pass
    out = await _factory.run("dev_pipeline", {"__cid": "ide"},
                             op="rollback",
                             neuro_name=name,
                             snapshot_ts=body.get("snapshot_ts"))
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


def main():
    ap = argparse.ArgumentParser(description="neurocomputer IDE API")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--host", type=str, default="127.0.0.1")
    args = ap.parse_args()

    import uvicorn
    print(f"[ide_server] starting on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
