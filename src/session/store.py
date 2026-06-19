"""Async SQLite session persistence using aiosqlite."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    title TEXT NOT NULL DEFAULT 'New session',
    message_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS snippets (
    name TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    language TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class SessionSummary:
    id: str
    created_at: str
    title: str
    message_count: int


class SessionStore:
    """Async SQLite store for sessions, messages, and snippets."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._connected: bool = False

    async def connect(self) -> None:
        """Open the database connection and ensure tables exist."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._create_tables()
        self._connected = True

    async def close(self, session_id: Optional[str] = None) -> None:
        """Close the database connection, updating the latest session timestamp."""
        if self._connected and self._db:
            if session_id:
                await self._db.execute(
                    "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
                    (session_id,),
                )
                await self._db.commit()
            await self._db.close()
            self._connected = False

    async def _create_tables(self) -> None:
        """Create tables if they don't exist."""
        assert self._db is not None
        await self._db.executescript(SCHEMA)
        # Migration: add language column for existing databases
        try:
            await self._db.execute(
                "ALTER TABLE snippets ADD COLUMN language TEXT DEFAULT ''"
            )
        except aiosqlite.OperationalError:
            pass  # Column already exists

    async def create_session(self, session_id: str, title: str = "New session") -> None:
        """Create a new session."""
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO sessions (id, title) VALUES (?, ?)",
            (session_id, title),
        )
        await self._db.commit()

    async def add_message(self, session_id: str, role: str, content: str) -> None:
        """Add a message to a session and update message count + updated_at."""
        assert self._db is not None
        await self._db.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        await self._db.execute(
            "UPDATE sessions SET updated_at = datetime('now'), "
            "message_count = message_count + 1 WHERE id = ?",
            (session_id,),
        )
        await self._db.commit()

    async def update_session_title(self, session_id: str, title: str) -> None:
        """Update a session's title."""
        assert self._db is not None
        await self._db.execute(
            "UPDATE sessions SET title = ? WHERE id = ?",
            (title, session_id),
        )
        await self._db.commit()

    async def list_sessions(self, limit: int = 20) -> list[SessionSummary]:
        """List recent sessions ordered by updated_at."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT id, created_at, title, message_count "
            "FROM sessions ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            SessionSummary(
                id=r["id"],
                created_at=r["created_at"],
                title=r["title"],
                message_count=r["message_count"],
            )
            for r in rows
        ]

    async def get_session_messages(self, session_id: str) -> list[dict[str, str]]:
        """Get all messages for a session."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in rows]

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and its messages (cascade)."""
        assert self._db is not None
        await self._db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await self._db.commit()

    # Snippet methods

    async def save_snippet(self, name: str, content: str, language: str = "") -> None:
        """Save or replace a snippet."""
        assert self._db is not None
        await self._db.execute(
            "INSERT OR REPLACE INTO snippets (name, content, language)"
            " VALUES (?, ?, ?)",
            (name, content, language),
        )
        await self._db.commit()

    async def get_snippet(self, name: str) -> Optional[str]:
        """Get a snippet by name."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT content FROM snippets WHERE name = ?",
            (name,),
        )
        row = await cursor.fetchone()
        return row["content"] if row else None

    async def delete_snippet(self, name: str) -> bool:
        """Delete a snippet. Returns True if deleted."""
        assert self._db is not None
        cursor = await self._db.execute("DELETE FROM snippets WHERE name = ?", (name,))
        await self._db.commit()
        return cursor.rowcount > 0

    async def list_snippets(self) -> list[dict[str, str]]:
        """List all snippets."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT name, content FROM snippets ORDER BY name ASC"
        )
        rows = await cursor.fetchall()
        return [{"name": r["name"], "content": r["content"]} for r in rows]
