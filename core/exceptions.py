"""Luca core exception hierarchy.

All Luca-specific exceptions inherit from LucaError.
This provides centralized, typed error handling across all layers.
"""

from __future__ import annotations


class LucaError(Exception):
    """Base exception for all Luca errors."""

    def __init__(self, message: str = "", *, recoverable: bool = True) -> None:
        super().__init__(message)
        self.recoverable = recoverable


class ConfigurationError(LucaError):
    """Invalid or missing configuration."""


class AIProviderError(LucaError):
    """Error communicating with an AI provider."""


class AIProviderUnavailableError(AIProviderError):
    """AI provider is not reachable or not configured."""

    def __init__(self, provider: str = "unknown") -> None:
        super().__init__(f"AI provider '{provider}' is unavailable")
        self.provider = provider


class AgentError(LucaError):
    """Error during agent execution."""


class ToolError(LucaError):
    """Error during tool execution."""


class ToolNotFoundError(ToolError):
    """Requested tool does not exist in the registry."""

    def __init__(self, tool_name: str) -> None:
        super().__init__(f"Tool '{tool_name}' not found")
        self.tool_name = tool_name


class ToolValidationError(ToolError):
    """Tool arguments failed validation."""


class ToolExecutionError(ToolError):
    """Tool execution failed at runtime."""


class MemoryError_(LucaError):
    """Error accessing memory storage.

    Named with trailing underscore to avoid shadowing the builtin MemoryError.
    """


class PermissionDeniedError(LucaError):
    """Operation was denied by the permission system."""

    def __init__(self, operation: str, reason: str = "") -> None:
        msg = f"Permission denied for '{operation}'"
        if reason:
            msg += f": {reason}"
        super().__init__(msg, recoverable=False)
        self.operation = operation
        self.reason = reason


class ValidationError(LucaError):
    """Input or data validation failed."""


class NetworkError(LucaError):
    """Network-related error."""


class ExecutionError(LucaError):
    """General execution error in a pipeline or workflow."""
