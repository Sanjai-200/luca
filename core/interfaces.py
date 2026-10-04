"""Luca core interfaces — Abstract Base Classes for all replaceable components.

These interfaces define the contracts that infrastructure implementations must fulfill.
Domain and application layers depend ONLY on these interfaces, never on concrete implementations.

Dependency direction:
    Domain/Application → core.interfaces ← Infrastructure implementations
"""

from __future__ import annotations

import abc
import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator


# ═══════════════════════════════════════════════════════════════════════════
#  Domain value objects (shared across all interfaces)
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Message:
    """A single message in a conversation."""
    role: str       # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from an AI provider."""
    content: str
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = ""


class RiskLevel(enum.Enum):
    """Risk classification for operations."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MemoryCategory(enum.Enum):
    """Categories of memory items."""
    USER = "user"
    IDENTITY = "identity"
    PREFERENCE = "preference"
    PROJECT = "project"
    FEEDBACK = "feedback"
    TASK_HISTORY = "task_history"
    CONVERSATION = "conversation"
    LEARNED_RULE = "learned_rule"


@dataclass
class MemoryItem:
    """A single item stored in memory."""
    id: str | None = None
    category: MemoryCategory = MemoryCategory.USER
    key: str = ""
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    importance: float = 0.5


@dataclass
class ToolResult:
    """Standardized result from any tool execution."""
    success: bool
    output: str = ""
    error: str = ""
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSpec:
    """Metadata describing a tool's capabilities for the LLM."""
    name: str
    description: str
    risk_level: RiskLevel = RiskLevel.MEDIUM
    parameters: dict[str, Any] = field(default_factory=dict)


class AppState(enum.Enum):
    """All possible application states."""
    INITIALIZING = "initializing"
    STANDBY = "standby"
    LISTENING = "listening"
    THINKING = "thinking"
    WORKING = "working"
    SPEAKING = "speaking"
    SLEEPING = "sleeping"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class PermissionDecision(enum.Enum):
    """Outcome of a permission check."""
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class PermissionResult:
    """Result of checking permissions for an operation."""
    decision: PermissionDecision
    risk_level: RiskLevel
    reason: str = ""


# ═══════════════════════════════════════════════════════════════════════════
#  AI Provider Interface
# ═══════════════════════════════════════════════════════════════════════════

class AIProvider(abc.ABC):
    """Abstract interface for all AI/LLM providers.

    Implementations: OllamaProvider, GeminiProvider, OpenAIProvider, etc.
    The rest of Luca depends on AIProvider, never on a specific SDK.
    """

    @abc.abstractmethod
    def generate(self, messages: list[Message], *,
                 temperature: float | None = None,
                 max_tokens: int | None = None) -> LLMResponse:
        """Generate a complete response."""
        ...

    @abc.abstractmethod
    def stream(self, messages: list[Message], *,
               temperature: float | None = None,
               max_tokens: int | None = None) -> Iterator[str]:
        """Stream response tokens one at a time."""
        ...

    @abc.abstractmethod
    def is_available(self) -> bool:
        """Check whether the provider is reachable and healthy."""
        ...

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Return the name/identifier of the current model."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
#  Memory Store Interface
# ═══════════════════════════════════════════════════════════════════════════

class MemoryStore(abc.ABC):
    """Abstract interface for memory persistence backends.

    Implementations: SQLiteMemoryStore, PostgresMemoryStore, etc.
    """

    @abc.abstractmethod
    def initialize(self) -> None:
        """Set up the storage backend (create tables, connect, etc.)."""
        ...

    @abc.abstractmethod
    def save(self, item: MemoryItem) -> str:
        """Save or upsert a memory item. Returns the item ID."""
        ...

    @abc.abstractmethod
    def get(self, item_id: str) -> MemoryItem | None:
        """Retrieve a single item by ID."""
        ...

    @abc.abstractmethod
    def search(self, query: str, *,
               category: MemoryCategory | None = None,
               limit: int = 10) -> list[MemoryItem]:
        """Search for items matching a query."""
        ...

    @abc.abstractmethod
    def delete(self, item_id: str) -> bool:
        """Delete a single item. Returns True if it existed."""
        ...

    @abc.abstractmethod
    def close(self) -> None:
        """Release resources (close connections, etc.)."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
#  Tool Interface
# ═══════════════════════════════════════════════════════════════════════════

class Tool(abc.ABC):
    """Abstract interface for all executable tools.

    Every tool must declare its name, description, risk level, and
    how to execute it. Tools are discovered via the ToolRegistry.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        ...

    @property
    @abc.abstractmethod
    def description(self) -> str:
        ...

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @property
    def spec(self) -> ToolSpec:
        """Return a machine-readable spec for LLM tool instructions."""
        return ToolSpec(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
        )

    @abc.abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments."""
        ...

    def validate(self, **kwargs: Any) -> bool:
        """Validate arguments before execution. Override for custom validation."""
        return True


# ═══════════════════════════════════════════════════════════════════════════
#  Permission Manager Interface
# ═══════════════════════════════════════════════════════════════════════════

class PermissionChecker(abc.ABC):
    """Abstract interface for the permission/safety system."""

    @abc.abstractmethod
    def check(self, operation: str, **context: Any) -> PermissionResult:
        """Check whether an operation is permitted."""
        ...


# ═══════════════════════════════════════════════════════════════════════════
#  Event System Interface
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Event:
    """Base class for all internal events."""
    name: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)


class EventBus(abc.ABC):
    """Abstract interface for the internal event system."""

    @abc.abstractmethod
    def emit(self, event: Event) -> None:
        ...

    @abc.abstractmethod
    def subscribe(self, event_name: str, handler: Any) -> None:
        ...
