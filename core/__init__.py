"""Luca core package — interfaces, exceptions, and domain value objects."""

from core.interfaces import (
    AIProvider,
    AppState,
    Event,
    EventBus,
    LLMResponse,
    MemoryCategory,
    MemoryItem,
    MemoryStore,
    Message,
    PermissionChecker,
    PermissionDecision,
    PermissionResult,
    RiskLevel,
    Tool,
    ToolResult,
    ToolSpec,
)

from core.exceptions import (
    LucaError,
    AIProviderError,
    AIProviderUnavailableError,
    AgentError,
    ConfigurationError,
    ExecutionError,
    MemoryError_,
    NetworkError,
    PermissionDeniedError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolValidationError,
    ValidationError,
)

__all__ = [
    # Interfaces
    "AIProvider", "MemoryStore", "Tool", "PermissionChecker", "EventBus",
    # Value objects
    "Message", "LLMResponse", "MemoryItem", "MemoryCategory", "ToolResult",
    "ToolSpec", "AppState", "RiskLevel", "PermissionDecision", "PermissionResult",
    "Event",
    # Exceptions
    "LucaError", "AIProviderError", "AIProviderUnavailableError", "AgentError",
    "ConfigurationError", "ExecutionError", "MemoryError_", "NetworkError",
    "PermissionDeniedError", "ToolError", "ToolExecutionError", "ToolNotFoundError",
    "ToolValidationError", "ValidationError",
]
