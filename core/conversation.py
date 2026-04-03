import os, json, uuid
from datetime import datetime, timezone

_CONV_DIR = os.path.join(os.getcwd(), "conversations")
os.makedirs(_CONV_DIR, exist_ok=True)


class Conversation:
    """
    Thin wrapper around a JSON file that stores:
    { "agent_id": "neuro", "messages": [...] }

    Where messages is a list of {sender, text, timestamp} dictionaries.
    """

    # ---------- lifecycle -------------------------------------------------
    def __init__(self, conv_id: str | None = None, agent_id: str | None = None):
        self.id   = conv_id or uuid.uuid4().hex
        self.agent_id = agent_id
        self._fp  = os.path.join(_CONV_DIR, f"{self.id}.json")
        data = self._load()
        # Handle both old format (list) and new format (dict)
        if isinstance(data, list):
            self._log = data
            # agent_id already set via constructor or stays None
        else:
            self._log = data.get("messages", []) if data else []
            self.agent_id = data.get("agent_id") if data else None

    # ---------- public helpers -------------------------------------------
    def set_agent_id(self, agent_id: str) -> None:
        """Set the agent_id for this conversation."""
        self.agent_id = agent_id
        self._save()

    def add(self, sender: str, text: str, audio_url: str = None, is_voice: bool = False) -> None:
        entry = {
            "sender": sender,
            "text":   text,
            "ts":     datetime.now(timezone.utc).isoformat(timespec="seconds")
        }
        if audio_url:
            entry["audio_url"] = audio_url
        if is_voice:
            entry["is_voice"] = True
        self._log.append(entry)
        self._save()

    def history(self, n: int | None = None) -> list[dict]:
        """Return complete history or last *n* messages."""
        return self._log if n is None else self._log[-n:]

    # ---------- internal io ----------------------------------------------
    def _load(self) -> dict | list:
        if os.path.exists(self._fp):
            with open(self._fp, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save(self):
        data = {
            "agent_id": self.agent_id,
            "messages": self._log
        }
        with open(self._fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
