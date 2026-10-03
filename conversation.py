"""Luca conversation history manager.

Contains:
  - ConversationTurn    — single exchange (user message + assistant response)
  - ConversationHistory — rolling buffer of recent turns for multi-turn context
  - ConversationStore   — persistent storage with 30-day retention + importance scoring

Design:
  - The rolling buffer keeps the last N turns in memory for the current session.
  - Only IMPORTANT turns are persisted to the database (importance evaluated by LLM).
  - Conversation data older than 30 days is automatically purged.
  - Learned rules (from learning.py) are PERMANENT and never purged.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from llm import Message
from memory import MemoryCategory, MemoryItem, MemoryManager

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Data model
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ConversationTurn:
    """A single user–assistant exchange."""
    user_message: str
    assistant_response: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    importance: float = 0.3  # default low; updated by importance scoring


# ═══════════════════════════════════════════════════════════════════════
#  Rolling conversation history (in-memory, per session)
# ═══════════════════════════════════════════════════════════════════════

class ConversationHistory:
    """Fixed-size rolling buffer of recent conversation turns.

    This keeps the last `max_turns` exchanges in memory for the current
    session.  When the buffer is full, the oldest turn is dropped.

    Usage by the controller:
      - Add turns after each exchange
      - Build LLM message list from history for multi-turn context
    """

    def __init__(self, max_turns: int = 10) -> None:
        self._max_turns = max_turns
        self._turns: deque[ConversationTurn] = deque(maxlen=max_turns)

    def add(self, user_message: str, assistant_response: str,
            importance: float = 0.3) -> ConversationTurn:
        """Record a completed exchange."""
        turn = ConversationTurn(
            user_message=user_message,
            assistant_response=assistant_response,
            importance=importance,
        )
        self._turns.append(turn)
        return turn

    def to_messages(self) -> list[Message]:
        """Convert history to LLM Message list for context injection.

        Returns alternating user/assistant messages (no system prompt).
        """
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


# ═══════════════════════════════════════════════════════════════════════
#  Persistent conversation store (SQLite via MemoryManager)
# ═══════════════════════════════════════════════════════════════════════

class ConversationStore:
    """Persists important conversation turns to the memory database.

    Features:
      - Only saves turns with importance >= threshold
      - Automatically purges conversations older than retention_days
      - Learned rules (MemoryCategory.LEARNED_RULE) are NEVER purged
    """

    IMPORTANCE_SAVE_THRESHOLD = 0.5  # only persist turns above this

    def __init__(self, memory: MemoryManager, retention_days: int = 30) -> None:
        self._memory = memory
        self._retention_days = retention_days

    def save_if_important(self, turn: ConversationTurn) -> str | None:
        """Save a turn only if its importance exceeds the threshold."""
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

        IMPORTANT: This ONLY deletes MemoryCategory.CONVERSATION items.
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
            logger.info("Purged %d conversation entries older than %d days",
                        deleted, self._retention_days)
        return deleted

    def get_recent_context(self, query: str, limit: int = 5) -> list[MemoryItem]:
        """Retrieve recent relevant conversations for context injection."""
        return self._memory.recall(query, category=MemoryCategory.CONVERSATION, limit=limit)
