"""Luca tool system.

Contains:
  - ToolResult    — standard result from any tool invocation
  - Tool          — abstract base class every tool must implement
  - ToolRegistry  — runtime discovery / lookup of registered tools
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from typing import Any

from safety import RiskLevel

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""
    data: dict[str, Any] = field(default_factory=dict)


class Tool(abc.ABC):
    @property
    @abc.abstractmethod
    def name(self) -> str: ...

    @property
    @abc.abstractmethod
    def description(self) -> str: ...

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @abc.abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult: ...


class ToolRegistry:
    """Discover and retrieve tools by name."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            logger.warning("Tool '%s' registered twice — overwriting", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Tool registered: %s", tool.name)

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools.keys())
