import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

_DB_PATH = Path(__file__).parent.parent / "data" / "rooms.db"


def _conn(path: Path = _DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Path = _DB_PATH) -> None:
    with _conn(path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                agents_json     TEXT NOT NULL DEFAULT '[]',
                transcript_json TEXT NOT NULL DEFAULT '[]',
                state_json      TEXT NOT NULL DEFAULT '{}',
                voice_room_id   TEXT,
                turn_policy     TEXT NOT NULL DEFAULT 'round_robin',
                max_turns       INTEGER NOT NULL DEFAULT 20,
                created_at      TEXT NOT NULL,
                status          TEXT NOT NULL DEFAULT 'open'
            )
        """)


def insert(row: dict, path: Path = _DB_PATH) -> None:
    with _conn(path) as conn:
        conn.execute(
            "INSERT INTO rooms (id, name, agents_json, transcript_json, state_json, "
            "voice_room_id, turn_policy, max_turns, created_at, status) "
            "VALUES (:id, :name, :agents_json, :transcript_json, :state_json, "
            ":voice_room_id, :turn_policy, :max_turns, :created_at, :status)",
            row,
        )


def update(room_id: str, fields: dict, path: Path = _DB_PATH) -> None:
    if not fields:
        return
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["room_id"] = room_id
    with _conn(path) as conn:
        conn.execute(f"UPDATE rooms SET {sets} WHERE id = :room_id", fields)


def delete(room_id: str, path: Path = _DB_PATH) -> None:
    with _conn(path) as conn:
        conn.execute("DELETE FROM rooms WHERE id = :id", {"id": room_id})


def get(room_id: str, path: Path = _DB_PATH) -> Optional[dict]:
    with _conn(path) as conn:
        row = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    return dict(row) if row else None


def list_all(path: Path = _DB_PATH) -> List[dict]:
    with _conn(path) as conn:
        rows = conn.execute("SELECT * FROM rooms ORDER BY created_at DESC").fetchall()
    return [dict(r) for r in rows]
