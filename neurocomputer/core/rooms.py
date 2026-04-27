"""Room dataclass + RoomManager singleton."""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional

from core import rooms_db as db


@dataclass
class Room:
    room_id: str
    name: str
    agents: List[str]
    voice_room_id: Optional[str] = None
    turn_policy: str = "round_robin"
    max_turns: int = 20
    transcript: List[dict] = field(default_factory=list)
    state: dict = field(default_factory=dict)
    created_at: str = ""
    status: str = "open"

    @property
    def blackboard_path(self) -> str:
        return f"rooms/{self.room_id}/"

    def to_dict(self) -> dict:
        return {
            "id": self.room_id,
            "name": self.name,
            "agents": self.agents,
            "voice_room_id": self.voice_room_id,
            "turn_policy": self.turn_policy,
            "max_turns": self.max_turns,
            "transcript": self.transcript,
            "state": self.state,
            "created_at": self.created_at,
            "status": self.status,
        }


def _row_to_room(row: dict) -> Room:
    return Room(
        room_id=row["id"],
        name=row["name"],
        agents=json.loads(row.get("agents_json") or "[]"),
        voice_room_id=row.get("voice_room_id"),
        turn_policy=row.get("turn_policy", "round_robin"),
        max_turns=row.get("max_turns", 20),
        transcript=json.loads(row.get("transcript_json") or "[]"),
        state=json.loads(row.get("state_json") or "{}"),
        created_at=row.get("created_at", ""),
        status=row.get("status", "open"),
    )


class RoomManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(self) -> None:
        db.init_db()

    def create(self, name: str, agents: List[str], *, voice_room_id: Optional[str] = None,
               turn_policy: str = "round_robin", max_turns: int = 20) -> Room:
        room = Room(
            room_id=uuid.uuid4().hex,
            name=name,
            agents=agents,
            voice_room_id=voice_room_id,
            turn_policy=turn_policy,
            max_turns=max_turns,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        db.insert({
            "id": room.room_id,
            "name": room.name,
            "agents_json": json.dumps(room.agents),
            "transcript_json": "[]",
            "state_json": "{}",
            "voice_room_id": room.voice_room_id,
            "turn_policy": room.turn_policy,
            "max_turns": room.max_turns,
            "created_at": room.created_at,
            "status": "open",
        })
        return room

    def get(self, room_id: str) -> Optional[Room]:
        row = db.get(room_id)
        return _row_to_room(row) if row else None

    def list(self) -> List[Room]:
        return [_row_to_room(r) for r in db.list_all()]

    def append_message(self, room_id: str, sender: str, text: str) -> Room:
        room = self.get(room_id)
        if room is None:
            raise ValueError(f"Room {room_id} not found")
        room.transcript.append({"sender": sender, "text": text,
                                 "ts": datetime.now(timezone.utc).isoformat()})
        db.update(room_id, {"transcript_json": json.dumps(room.transcript)})
        return room

    def close(self, room_id: str) -> bool:
        row = db.get(room_id)
        if not row:
            return False
        db.update(room_id, {"status": "closed"})
        return True

    def delete(self, room_id: str) -> bool:
        if not db.get(room_id):
            return False
        db.delete(room_id)
        return True


room_manager = RoomManager()


def _pick_next_agent(room: "Room", turn_count: int) -> str:
    """Round-robin: pick the next agent after the last speaker."""
    if not room.agents:
        return ""
    if not room.transcript:
        return room.agents[0]
    last_speaker = room.transcript[-1].get("sender", "user")
    if last_speaker in room.agents:
        idx = room.agents.index(last_speaker)
        return room.agents[(idx + 1) % len(room.agents)]
    return room.agents[0]
