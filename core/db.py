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
                    CREATE INDEX IF NOT EXISTS idx_messages_conversation 
                    ON messages(conversation_id)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_messages_created 
                    ON messages(created_at)
                """)
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


db = Database()
