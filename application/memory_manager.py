"""Memory Manager — high-level façade over the MemoryStore interface.

Single responsibility: provide convenient memory operations to the application layer.
Does NOT know about SQLite, PostgreSQL, or any specific backend.
"""

from __future__ import annotations

import logging

from core.interfaces import MemoryCategory, MemoryItem, MemoryStore

logger = logging.getLogger(__name__)


class MemoryManager:
    """High-level memory façade used by services and agents.

    Delegates all persistence to the injected MemoryStore.
    Swapping backends (SQLite → Postgres) requires only changing the injected store.
    """

    def __init__(self, store: MemoryStore) -> None:
        self._store = store

    def initialize(self) -> None:
        self._store.initialize()
        logger.info("MemoryManager ready")

    def close(self) -> None:
        self._store.close()

    def remember(
        self,
        content: str,
        *,
        category: MemoryCategory = MemoryCategory.USER,
        key: str = "",
        importance: float = 0.5,
    ) -> str:
        """Store a memory item. Returns the item ID."""
        return self._store.save(
            MemoryItem(category=category, key=key, content=content, importance=importance)
        )

    def recall(
        self,
        query: str,
        *,
        category: MemoryCategory | None = None,
        limit: int = 5,
    ) -> list[MemoryItem]:
        """Search for relevant memory items."""
        return self._store.search(query, category=category, limit=limit)

    def forget(self, item_id: str) -> bool:
        """Delete a memory item."""
        return self._store.delete(item_id)

    def get(self, item_id: str) -> MemoryItem | None:
        """Retrieve a single item by ID."""
        return self._store.get(item_id)
