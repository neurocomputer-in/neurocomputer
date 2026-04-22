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
        self.llm_settings = {}
        self._session_role = None
        self._selection_type = None
        self._type = "chat"
        self._tmux_session = None
        self._workdir = None
        self._summary = ""
        self._fp  = os.path.join(_CONV_DIR, f"{self.id}.json")
        data = self._load()
        # Handle both old format (list) and new format (dict)
        if isinstance(data, list):
            self._log = data
            # agent_id already set via constructor or stays None
        else:
            self._log = data.get("messages", []) if data else []
            self.agent_id = data.get("agent_id") if data else None
            self.llm_settings = data.get("llm_settings", {}) if data else {}
            self._session_role = (data.get("session_role") or None) if data else None
            raw_sel = data.get("selection_type") if data else None
            self._selection_type = raw_sel if raw_sel in ("raw", "role") else None
            raw_type = data.get("type") if data else None
            self._type = raw_type if raw_type in ("chat", "terminal") else "chat"
            self._tmux_session = (data.get("tmux_session") or None) if data else None
            self._workdir = (data.get("workdir") or None) if data else None
            self._summary = data.get("history_summary", "") if data else ""

    # ---------- public helpers -------------------------------------------
    def set_agent_id(self, agent_id: str) -> None:
        """Set the agent_id for this conversation."""
        self.agent_id = agent_id
        self._save()

    def get_llm_settings(self) -> dict:
        return dict(self.llm_settings or {})

    def set_llm_settings(self, provider: str | None = None, model: str | None = None) -> dict:
        settings = dict(self.llm_settings or {})
        if provider is not None:
            settings["provider"] = provider
        if model is not None:
            settings["model"] = model
        self.llm_settings = settings
        self._save()
        return settings

    def get_session_role(self) -> str | None:
        return self._session_role or None

    def set_session_role(self, role: str | None) -> str | None:
        value = (role or "").strip() if isinstance(role, str) else None
        self._session_role = value or None
        self._save()
        return self._session_role

    def get_selection_type(self) -> str | None:
        return self._selection_type or None

    def set_selection_type(self, selection_type: str | None) -> str | None:
        self._selection_type = selection_type if selection_type in ("raw", "role") else None
        self._save()
        return self._selection_type

    def get_type(self) -> str:
        return self._type or "chat"

    def set_type(self, t: str) -> str:
        self._type = t if t in ("chat", "terminal") else "chat"
        self._save()
        return self._type

    def get_tmux_session(self) -> str | None:
        return self._tmux_session or None

    def set_tmux_session(self, name: str | None) -> str | None:
        self._tmux_session = (name or "").strip() or None
        self._save()
        return self._tmux_session

    def get_workdir(self) -> str | None:
        return self._workdir or None

    def set_workdir(self, path: str | None) -> str | None:
        self._workdir = (path or "").strip() or None
        self._save()
        return self._workdir

    def get_history_summary(self) -> str:
        """Return cached history summary, or empty string."""
        return self._summary or ""

    def set_history_summary(self, summary: str) -> None:
        """Cache a history summary. Persisted to disk."""
        self._summary = summary
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
            "messages": self._log,
            "llm_settings": self.llm_settings or {},
            "session_role": self._session_role or None,
            "selection_type": self._selection_type or None,
            "type": self._type or "chat",
            "tmux_session": self._tmux_session or None,
            "workdir": self._workdir or None,
            "history_summary": self._summary or "",
        }
        with open(self._fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
