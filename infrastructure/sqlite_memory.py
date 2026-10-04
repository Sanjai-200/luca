"""SQLite Memory Store — infrastructure implementation of MemoryStore.

This module contains ONLY the SQLite persistence logic.
It implements the core.interfaces.MemoryStore contract.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from core.interfaces import MemoryCategory, MemoryItem, MemoryStore

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = 1


class SQLiteMemoryStore(MemoryStore):
    """Local SQLite memory backend (zero external deps)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    # ── MemoryStore contract ──────────────────────────────────────────

    def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()
        logger.info("SQLite memory store ready: %s", self._db_path)

    def save(self, item: MemoryItem) -> str:
        conn = self._ensure()
        now = datetime.now(timezone.utc).isoformat()
        item_id = item.id or uuid.uuid4().hex
        conn.execute(
            """INSERT INTO memory (id, category, key, content, metadata, importance, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 category=excluded.category, key=excluded.key, content=excluded.content,
                 metadata=excluded.metadata, importance=excluded.importance, updated_at=excluded.updated_at""",
            (item_id, item.category.value, item.key, item.content,
             json.dumps(item.metadata), item.importance,
             item.created_at.isoformat() if item.created_at else now, now),
        )
        conn.commit()
        return item_id

    def get(self, item_id: str) -> MemoryItem | None:
        row = self._ensure().execute("SELECT * FROM memory WHERE id=?", (item_id,)).fetchone()
        return self._to_item(row) if row else None

    def search(self, query: str, *, category: MemoryCategory | None = None, limit: int = 10) -> list[MemoryItem]:
        sql = "SELECT * FROM memory WHERE (content LIKE ? OR key LIKE ?)"
        params: list[object] = [f"%{query}%", f"%{query}%"]
        if category:
            sql += " AND category=?"
            params.append(category.value)
        sql += " ORDER BY importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)
        return [self._to_item(r) for r in self._ensure().execute(sql, params).fetchall()]

    def delete(self, item_id: str) -> bool:
        cur = self._ensure().execute("DELETE FROM memory WHERE id=?", (item_id,))
        self._ensure().commit()
        return cur.rowcount > 0

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ── Internal ──────────────────────────────────────────────────────

    def _ensure(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("SQLiteMemoryStore not initialised — call initialize() first")
        return self._conn

    def _create_tables(self) -> None:
        self._ensure().executescript("""
            CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);
            CREATE TABLE IF NOT EXISTS memory (
                id TEXT PRIMARY KEY, category TEXT NOT NULL, key TEXT NOT NULL DEFAULT '',
                content TEXT NOT NULL DEFAULT '', metadata TEXT NOT NULL DEFAULT '{}',
                importance REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memory_category ON memory(category);
            CREATE INDEX IF NOT EXISTS idx_memory_key ON memory(key);
        """)
        if not self._ensure().execute("SELECT version FROM schema_version").fetchone():
            self._ensure().execute("INSERT INTO schema_version(version) VALUES(?)", (_SCHEMA_VERSION,))
            self._ensure().commit()

    @staticmethod
    def _to_item(row: sqlite3.Row) -> MemoryItem:
        return MemoryItem(
            id=row["id"], category=MemoryCategory(row["category"]),
            key=row["key"], content=row["content"],
            metadata=json.loads(row["metadata"]), importance=row["importance"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
