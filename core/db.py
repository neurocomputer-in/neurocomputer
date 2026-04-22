"""
Database module for chat message persistence using SQLite.
"""

import aiosqlite
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

logger = logging.getLogger("db")

DB_PATH = os.getenv("DB_PATH", "/home/ubuntu/neurocomputer/data/neuro.db")


class Database:
    """Async SQLite database for chat persistence."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        """Initialize database tables."""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id TEXT PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id TEXT PRIMARY KEY,
                        conversation_id TEXT NOT NULL,
                        sender TEXT NOT NULL,
                        type TEXT NOT NULL,
                        content TEXT,
                        audio_url TEXT,
                        duration_ms INTEGER,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        color TEXT DEFAULT '#8B5CF6',
                        session_state TEXT DEFAULT '{"openTabs":[],"activeTab":null}',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_created
                    ON messages(created_at)
                """)
                # Migration: add agents column if missing
                try:
                    await db.execute("ALTER TABLE projects ADD COLUMN agents TEXT DEFAULT '[]'")
                except Exception:
                    pass
                # Migration: add agency_id column to projects if missing
                try:
                    await db.execute("ALTER TABLE projects ADD COLUMN agency_id TEXT")
                except Exception:
                    pass
                # Agencies table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS agencies (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT DEFAULT '',
                        color TEXT DEFAULT '#8B5CF6',
                        emoji TEXT DEFAULT '🏢',
                        agents TEXT DEFAULT '["neuro"]',
                        default_agent TEXT DEFAULT 'neuro',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                # Migration: add theme column to agencies if missing
                try:
                    await db.execute("ALTER TABLE agencies ADD COLUMN theme TEXT DEFAULT 'cosmic'")
                except Exception:
                    pass
                now = datetime.utcnow().isoformat()
                # Legacy `__noproject__` catch-all has been replaced by a
                # per-workspace `main-{workspaceId}` MainProject row. If an
                # older DB still has the legacy row, migrate it: rename id
                # to `main-default`, set name to MainProject, attach it to
                # the default workspace. seed_main_projects() (called at
                # startup after seed_workspaces) then ensures every other
                # workspace gets its own MainProject row.
                try:
                    await db.execute("""
                        UPDATE projects
                        SET id = 'main-default',
                            name = 'MainProject',
                            agency_id = COALESCE(agency_id, 'default')
                        WHERE id = '__noproject__'
                    """)
                except Exception:
                    pass
                await db.commit()
                logger.info(f"Database initialized at {self.db_path}")

    async def create_conversation(self, agent_id: str) -> str:
        """Create a new conversation and return its ID."""
        conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO conversations (id, agent_id) VALUES (?, ?)""",
                    (conversation_id, agent_id)
                )
                await db.commit()
        logger.info(f"Created conversation {conversation_id} for agent {agent_id}")
        return conversation_id

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID."""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM conversations WHERE id = ?",
                    (conversation_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None

    async def add_message_with_id(
        self,
        message_id: str,
        conversation_id: str,
        sender: str,
        msg_type: str,
        content: Optional[str] = None,
        audio_url: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Add a message with a specific ID (for matching DataChannel message IDs)."""
        return await self._insert_message(
            message_id, conversation_id, sender, msg_type, content, audio_url, duration_ms, metadata
        )

    async def add_message(
        self,
        conversation_id: str,
        sender: str,
        msg_type: str,
        content: Optional[str] = None,
        audio_url: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Add a message to a conversation."""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        return await self._insert_message(
            message_id, conversation_id, sender, msg_type, content, audio_url, duration_ms, metadata
        )

    async def _insert_message(
        self,
        message_id: str,
        conversation_id: str,
        sender: str,
        msg_type: str,
        content: Optional[str] = None,
        audio_url: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Internal: insert a message into the database."""
        # Validate sender and type
        if sender not in ('user', 'agent'):
            raise ValueError(f"Invalid sender: {sender}")
        if msg_type not in ('text', 'voice', 'ocr'):
            raise ValueError(f"Invalid message type: {msg_type}")
        metadata_json = json.dumps(metadata) if metadata else None
        
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO messages 
                       (id, conversation_id, sender, type, content, audio_url, duration_ms, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (message_id, conversation_id, sender, msg_type, content, audio_url, duration_ms, metadata_json)
                )
                await db.execute(
                    """UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (conversation_id,)
                )
                await db.commit()
        
        logger.info(f"Added {msg_type} message {message_id} to conversation {conversation_id}")
        return message_id

    async def get_messages(
        self, 
        conversation_id: str, 
        limit: int = 50, 
        before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation, newest first."""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if before:
                    async with db.execute(
                        """SELECT * FROM messages 
                           WHERE conversation_id = ? AND id < ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (conversation_id, before, limit)
                    ) as cursor:
                        rows = await cursor.fetchall()
                else:
                    async with db.execute(
                        """SELECT * FROM messages 
                           WHERE conversation_id = ?
                           ORDER BY created_at DESC LIMIT ?""",
                        (conversation_id, limit)
                    ) as cursor:
                        rows = await cursor.fetchall()
                
                messages = [dict(row) for row in rows]
                messages.reverse()
                return messages

    async def get_or_create_conversation(
        self, 
        conversation_id: str, 
        agent_id: str
    ) -> Dict[str, Any]:
        """Get existing conversation or create new one."""
        conv = await self.get_conversation(conversation_id)
        if conv:
            return conv
        
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR IGNORE INTO conversations (id, agent_id) VALUES (?, ?)""",
                    (conversation_id, agent_id)
                )
                await db.commit()
        
        return await self.get_conversation(conversation_id)


    # ------------------------------------------------------------------
    # Project methods
    # ------------------------------------------------------------------

    async def create_project(
        self,
        name: str,
        description: str = "",
        color: str = "#8B5CF6",
        agents: list = None,
        workspace_id: str | None = None,
    ) -> Dict[str, Any]:
        """Create a new project and return it."""
        if agents is None:
            agents = ["neuro"]
        project_id = uuid.uuid4().hex
        now = datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT INTO projects (id, name, description, color, agents, agency_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (project_id, name, description, color, json.dumps(agents), workspace_id, now, now)
                )
                await db.commit()
        return {"id": project_id, "name": name, "description": description,
                "color": color, "agents": agents, "workspaceId": workspace_id,
                "sessionState": {"openTabs": [], "activeTab": None},
                "createdAt": now, "updatedAt": now}

    async def list_projects(self, workspace_id: str | None = None) -> List[Dict[str, Any]]:
        """List all projects. MainProject rows (id prefix ``main-``) are
        returned alongside user-created projects — they're real default
        projects, not catch-alls."""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                query = "SELECT * FROM projects WHERE id != '__noproject__'"
                params: list = []
                if workspace_id is not None:
                    query += " AND agency_id = ?"
                    params.append(workspace_id)
                # Sort: MainProject first (stable anchor), then most-recent.
                query += " ORDER BY CASE WHEN id LIKE 'main-%' THEN 0 ELSE 1 END, updated_at DESC"
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
        projects = []
        for row in rows:
            d = dict(row)
            try:
                session = json.loads(d.get("session_state") or "{}")
            except Exception:
                session = {}
            try:
                agents_list = json.loads(d.get("agents") or "[]")
            except Exception:
                agents_list = []
            projects.append({
                "id": d["id"],
                "name": d["name"],
                "description": d.get("description", ""),
                "color": d.get("color", "#8B5CF6"),
                "workspaceId": d.get("agency_id"),
                "sessionState": {"openTabs": session.get("openTabs", []),
                                 "activeTab": session.get("activeTab")},
                "agents": agents_list,
                "createdAt": d.get("created_at", ""),
                "updatedAt": d.get("updated_at", ""),
            })
        return projects

    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a project by ID."""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM projects WHERE id = ?", (project_id,)
                ) as cursor:
                    row = await cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            session = json.loads(d.get("session_state") or "{}")
        except Exception:
            session = {}
        try:
            agents_list = json.loads(d.get("agents") or "[]")
        except Exception:
            agents_list = []
        return {
            "id": d["id"],
            "name": d["name"],
            "description": d.get("description", ""),
            "color": d.get("color", "#8B5CF6"),
            "workspaceId": d.get("agency_id"),
            "sessionState": {"openTabs": session.get("openTabs", []),
                             "activeTab": session.get("activeTab")},
            "agents": agents_list,
            "createdAt": d.get("created_at", ""),
            "updatedAt": d.get("updated_at", ""),
        }

    async def update_project(self, project_id: str, **fields) -> bool:
        """Update project fields. Supports: name, description, color, session_state (dict)."""
        if not fields:
            return True
        now = datetime.utcnow().isoformat()
        set_clauses = ["updated_at = ?"]
        values = [now]
        if "name" in fields:
            set_clauses.append("name = ?")
            values.append(fields["name"])
        if "description" in fields:
            set_clauses.append("description = ?")
            values.append(fields["description"])
        if "color" in fields:
            set_clauses.append("color = ?")
            values.append(fields["color"])
        if "session_state" in fields:
            set_clauses.append("session_state = ?")
            values.append(json.dumps(fields["session_state"]))
        if "agents" in fields:
            set_clauses.append("agents = ?")
            values.append(json.dumps(fields["agents"]))
        if "workspace_id" in fields:
            set_clauses.append("agency_id = ?")
            values.append(fields["workspace_id"])
        values.append(project_id)
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    f"UPDATE projects SET {', '.join(set_clauses)} WHERE id = ?",
                    values
                )
                await db.commit()
        return True

    async def delete_project(self, project_id: str) -> bool:
        """Delete a project by ID."""
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
                await db.commit()
        return True

    # ── Workspaces (SQL table still called "agencies" to avoid migration) ─

    async def seed_workspaces(self, configs: dict):
        """Seed default workspaces from WORKSPACE_CONFIGS if they don't exist.
        Also refreshes the seeded workspaces' display name so renames in
        ``workspace_configs.py`` (e.g. "Neuro HQ" → "Main Workspace") take
        effect for existing DBs."""
        now = datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                for wid, cfg in configs.items():
                    theme = getattr(cfg, "theme", None) or "cosmic"
                    await conn.execute("""
                        INSERT OR IGNORE INTO agencies (id, name, description, color, emoji, agents, default_agent, created_at, updated_at, theme)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (wid, cfg.name, cfg.description, cfg.color, cfg.emoji,
                          json.dumps(cfg.agents), cfg.default_agent, now, now, theme))
                    await conn.execute(
                        "UPDATE agencies SET name = ?, updated_at = ? WHERE id = ?",
                        (cfg.name, now, wid),
                    )
                await conn.commit()

    async def seed_main_projects(self, workspace_ids: list[str]):
        """Ensure every workspace has a MainProject row (id ``main-{wid}``).
        Also fix-up:
          * Any project with ``agency_id IS NULL`` is reassigned to ``default``.
          * The MainProject row is non-deletable at the application layer
            (server.py enforces); this method just makes sure it exists.
        Safe to call multiple times.
        """
        now = datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                # Reassign orphaned projects to the default workspace.
                await conn.execute(
                    "UPDATE projects SET agency_id = 'default' WHERE agency_id IS NULL AND id != '__noproject__'"
                )
                for wid in workspace_ids:
                    pid = f"main-{wid}"
                    await conn.execute(
                        """
                        INSERT OR IGNORE INTO projects
                            (id, name, description, color, agents, agency_id,
                             created_at, updated_at)
                        VALUES (?, 'MainProject', 'Default project for this workspace',
                                '#8B5CF6', '[]', ?, ?, ?)
                        """,
                        (pid, wid, now, now),
                    )
                    # Ensure existing row has the right name + workspace
                    # (handles the legacy `__noproject__` → `main-default`
                    # migration, plus defends against manual tampering).
                    await conn.execute(
                        """
                        UPDATE projects
                           SET name = 'MainProject',
                               description = 'Default project for this workspace',
                               color = '#8B5CF6',
                               agency_id = ?,
                               updated_at = ?
                         WHERE id = ?
                        """,
                        (wid, now, pid),
                    )
                await conn.commit()

    async def get_main_project_id(self, workspace_id: str) -> str:
        """Return the ``main-{workspace_id}`` project id, guaranteed to exist.
        Used when a conversation is created or orphaned and needs to land
        somewhere."""
        pid = f"main-{workspace_id}"
        # Best effort: ensure row exists even if seed_main_projects was not
        # called with this workspace (e.g. a workspace created post-startup).
        now = datetime.utcnow().isoformat()
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO projects
                        (id, name, description, color, agents, agency_id,
                         created_at, updated_at)
                    VALUES (?, 'MainProject', 'Default project for this workspace',
                            '#8B5CF6', '[]', ?, ?, ?)
                    """,
                    (pid, workspace_id, now, now),
                )
                await conn.commit()
        return pid

    async def list_workspaces(self) -> List[Dict[str, Any]]:
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("SELECT * FROM agencies ORDER BY name") as cur:
                    rows = await cur.fetchall()
        def _row(r):
            d = dict(r)
            return {
                "id": d["id"], "name": d["name"], "description": d.get("description", ""),
                "color": d.get("color", "#8B5CF6"), "emoji": d.get("emoji", "🏢"),
                "agents": json.loads(d.get("agents") or "[]"),
                "defaultAgent": d.get("default_agent", "neuro"),
                "theme": d.get("theme") or "cosmic",
            }
        return [_row(r) for r in rows]

    async def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("SELECT * FROM agencies WHERE id = ?", (workspace_id,)) as cur:
                    r = await cur.fetchone()
        if not r:
            return None
        d = dict(r)
        return {
            "id": d["id"], "name": d["name"], "description": d.get("description", ""),
            "color": d.get("color", "#8B5CF6"), "emoji": d.get("emoji", "🏢"),
            "agents": json.loads(d.get("agents") or "[]"),
            "defaultAgent": d.get("default_agent", "neuro"),
            "theme": d.get("theme") or "cosmic",
        }

    async def create_workspace(self, workspace_id: str, name: str, description: str = "",
                               color: str = "#8B5CF6", emoji: str = "🏢",
                               agents: list = None, default_agent: str = "neuro",
                               theme: str = "cosmic") -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        agents = agents or ["neuro"]
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO agencies (id, name, description, color, emoji, agents, default_agent, created_at, updated_at, theme)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (workspace_id, name, description, color, emoji, json.dumps(agents), default_agent, now, now, theme))
                await conn.commit()
        return {"id": workspace_id, "name": name, "description": description,
                "color": color, "emoji": emoji, "agents": agents, "defaultAgent": default_agent,
                "theme": theme}

    async def update_workspace(self, workspace_id: str, **fields) -> bool:
        sets, vals = [], []
        for k, v in fields.items():
            col = k
            if k == "defaultAgent":
                col = "default_agent"
            if k == "agents" and isinstance(v, list):
                v = json.dumps(v)
            sets.append(f"{col} = ?")
            vals.append(v)
        if not sets:
            return False
        sets.append("updated_at = ?")
        vals.append(datetime.utcnow().isoformat())
        vals.append(workspace_id)
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(f"UPDATE agencies SET {', '.join(sets)} WHERE id = ?", vals)
                await conn.commit()
        return True

    async def delete_workspace(self, workspace_id: str) -> bool:
        async with self._lock:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("DELETE FROM agencies WHERE id = ?", (workspace_id,))
                await conn.commit()
        return True


db = Database()
