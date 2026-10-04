"""Conversation History — rolling buffer + persistent storage.

Migrated from the flat conversation.py into the application layer.
Depends only on core interfaces and MemoryManager.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from core.interfaces import Message, MemoryCategory, MemoryItem
from application.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class ConversationTurn:
    """A single user–assistant exchange."""
    user_message: str
    assistant_response: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    importance: float = 0.3


class ConversationHistory:
    """Fixed-size rolling buffer of recent conversation turns.

    Keeps the last N turns in memory for multi-turn LLM context.
    """

    def __init__(self, max_turns: int = 10) -> None:
        self._max_turns = max_turns
        self._turns: deque[ConversationTurn] = deque(maxlen=max_turns)

    def add(self, user_message: str, assistant_response: str,
            importance: float = 0.3) -> ConversationTurn:
        turn = ConversationTurn(
            user_message=user_message,
            assistant_response=assistant_response,
            importance=importance,
        )
        self._turns.append(turn)
        return turn

    def to_messages(self) -> list[Message]:
        """Convert history to LLM Message list for context injection."""
        messages: list[Message] = []
        for turn in self._turns:
            messages.append(Message("user", turn.user_message))
            messages.append(Message("assistant", turn.assistant_response))
        return messages

    def clear(self) -> None:
        self._turns.clear()

    @property
    def turns(self) -> list[ConversationTurn]:
        return list(self._turns)

    def __len__(self) -> int:
        return len(self._turns)


class ConversationStore:
    """Persists important conversation turns to the memory database.

    Only saves turns above an importance threshold.
    Automatically purges conversations older than retention_days.
    Learned rules are NEVER purged.
    """

    IMPORTANCE_SAVE_THRESHOLD = 0.5

    def __init__(self, memory: MemoryManager, retention_days: int = 30) -> None:
        self._memory = memory
        self._retention_days = retention_days

    def save_if_important(self, turn: ConversationTurn) -> str | None:
        if turn.importance < self.IMPORTANCE_SAVE_THRESHOLD:
            return None
        content = f"Boss: {turn.user_message}\nLuca: {turn.assistant_response}"
        item_id = self._memory.remember(
            content=content,
            category=MemoryCategory.CONVERSATION,
            key=turn.timestamp.isoformat(),
            importance=turn.importance,
        )
        logger.debug("Saved important conversation turn (importance=%.2f)", turn.importance)
        return item_id

    def purge_old_conversations(self) -> int:
        """Delete conversation entries older than retention_days.
        Learned rules, preferences, and user facts are NEVER touched.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=self._retention_days)
        old_items = self._memory.recall(
            "", category=MemoryCategory.CONVERSATION, limit=500
        )
        deleted = 0
        for item in old_items:
            if item.created_at and item.created_at < cutoff:
                self._memory.forget(item.id)
                deleted += 1
        if deleted:
            logger.info("Purged %d old conversation entries", deleted)
        return deleted
