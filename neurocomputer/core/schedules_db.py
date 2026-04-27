import sqlite3
import json
from pathlib import Path
from typing import List, Optional

_DB_PATH = Path(__file__).parent.parent / "data" / "schedules.db"


def _conn(path: Path = _DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Path = _DB_PATH) -> None:
    with _conn(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id           TEXT PRIMARY KEY,
                target_path  TEXT NOT NULL,
                trigger_kind TEXT NOT NULL,
                trigger_arg  TEXT NOT NULL,
                kwargs_json  TEXT NOT NULL DEFAULT '{}',
                enabled      INTEGER NOT NULL DEFAULT 1,
                created_at   TEXT NOT NULL,
                last_run     TEXT,
                last_status  TEXT,
                next_run     TEXT
            )
        """)


def insert(row: dict, path: Path = _DB_PATH) -> None:
    with _conn(path) as conn:
        conn.execute(
            "INSERT INTO schedules (id, target_path, trigger_kind, trigger_arg, kwargs_json, enabled, created_at) "
            "VALUES (:id, :target_path, :trigger_kind, :trigger_arg, :kwargs_json, :enabled, :created_at)",
            row,
        )


def update(schedule_id: str, fields: dict, path: Path = _DB_PATH) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["schedule_id"] = schedule_id
    with _conn(path) as conn:
        conn.execute(f"UPDATE schedules SET {sets} WHERE id = :schedule_id", fields)


def delete(schedule_id: str, path: Path = _DB_PATH) -> None:
    with _conn(path) as conn:
        conn.execute("DELETE FROM schedules WHERE id = :id", {"id": schedule_id})


def list_all(path: Path = _DB_PATH) -> List[dict]:
    with _conn(path) as conn:
        rows = conn.execute("SELECT * FROM schedules ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]


def get(schedule_id: str, path: Path = _DB_PATH) -> Optional[dict]:
    with _conn(path) as conn:
        row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    return dict(row) if row else None
