"""Tool Registry — runtime discovery and lookup of registered tools.

The registry is the single source of truth for what tools Luca can use.
Agents discover tools through the registry, never by importing tool modules directly.
"""

from __future__ import annotations

import logging
from typing import Any

from core.interfaces import Tool, ToolResult, ToolSpec, RiskLevel
from core.exceptions import ToolNotFoundError, ToolValidationError, ToolExecutionError

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Discover and retrieve tools by name.

    Provides tool listing, lookup, and safe execution with validation.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool. Overwrites if name already exists."""
        if tool.name in self._tools:
            logger.warning("Tool '%s' registered twice — overwriting", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Tool registered: %s (risk=%s)", tool.name, tool.risk_level.value)

    def get(self, name: str) -> Tool | None:
        """Retrieve a tool by name, returning None if not found."""
        return self._tools.get(name)

    def get_strict(self, name: str) -> Tool:
        """Retrieve a tool by name. Raises ToolNotFoundError if missing."""
        tool = self._tools.get(name)
        if tool is None:
            raise ToolNotFoundError(name)
        return tool

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """Look up a tool, validate, and execute it.

        Raises ToolNotFoundError, ToolValidationError, or ToolExecutionError.
        """
        tool = self.get_strict(name)

        if not tool.validate(**kwargs):
            raise ToolValidationError(f"Validation failed for tool '{name}'")

        try:
            return tool.execute(**kwargs)
        except Exception as exc:
            raise ToolExecutionError(f"Tool '{name}' execution failed: {exc}") from exc

    def list_specs(self) -> list[ToolSpec]:
        """Return machine-readable specs for all registered tools."""
        return [t.spec for t in self._tools.values()]

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
