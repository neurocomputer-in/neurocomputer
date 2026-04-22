"""dev_pipeline — bridge from neuro protocol to core.dev_agent helpers.

Note: first positional arg of factory.run() is 'name' (the neuro to
invoke), so this neuro uses 'neuro_name' for the target neuro name
to avoid kwarg collision.
"""
from core.dev_agent import (
    validate_conf_json,
    validate_code_py,
    atomic_save_neuro,
    rollback_neuro,
    list_snapshots,
    delete_neuro,
)


async def run(state, *, op, neuro_name=None, conf=None, code=None, prompt=None,
              author="ai", snapshot_ts=None, folder=None, **_):
    if op == "validate":
        if conf is not None:
            vc = validate_conf_json(conf)
            if not vc["ok"]:
                return {"ok": False, "stage": "schema", "errors": vc["errors"]}
        if code is not None:
            vcode = validate_code_py(code, author=author)
            if not vcode["ok"]:
                return {"ok": False, "stage": "syntax", "errors": vcode["errors"]}
        return {"ok": True, "stage": "validated"}

    if op == "save":
        if not neuro_name or conf is None or code is None:
            return {"ok": False,
                    "errors": ["save requires neuro_name, conf, code"]}
        return atomic_save_neuro(neuro_name, conf, code, prompt=prompt,
                                  author=author)

    if op == "rollback":
        if not neuro_name:
            return {"ok": False, "errors": ["rollback requires neuro_name"]}
        return rollback_neuro(neuro_name, snapshot_ts=snapshot_ts)

    if op == "list_snapshots":
        if not neuro_name:
            return {"ok": False, "errors": ["list_snapshots requires neuro_name"]}
        return {"ok": True, "snapshots": list_snapshots(neuro_name)}

    if op == "delete":
        if not neuro_name:
            return {"ok": False, "errors": ["delete requires neuro_name"]}
        return delete_neuro(neuro_name, folder=folder)

    return {"ok": False, "errors": [f"unknown op {op!r}"]}
