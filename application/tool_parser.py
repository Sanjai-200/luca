"""Tool Parser — extracts and executes tool calls from LLM output.

Single responsibility: parse <tool>JSON</tool> blocks from text and execute them.
Does NOT build prompts, call LLMs, or manage conversation history.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Iterator

from core.interfaces import ToolResult
from core.exceptions import ToolNotFoundError
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Matches <tool>JSON</tool> blocks (case-insensitive, multiline)
_TOOL_PATTERN = re.compile(r"<tool>(.*?)</tool>", re.IGNORECASE | re.DOTALL)


@dataclass
class ToolCall:
    """Parsed tool invocation from LLM output."""
    name: str
    args: dict
    raw: str = ""


def parse_tool_calls(text: str) -> list[ToolCall]:
    """Extract all <tool>JSON</tool> blocks from LLM output."""
    calls: list[ToolCall] = []
    for match in _TOOL_PATTERN.finditer(text):
        raw = match.group(1).strip()
        try:
            data = json.loads(raw)
            name = data.get("name", "")
            args = data.get("args", {})
            if name:
                calls.append(ToolCall(name=name, args=args, raw=raw))
        except json.JSONDecodeError:
            logger.warning("Invalid tool JSON: %s", raw[:100])
    return calls


def strip_tool_tags(text: str) -> str:
    """Remove all <tool>...</tool> tags and any enclosing markdown code fences."""
    cleaned = _TOOL_PATTERN.sub("", text)
    cleaned = re.sub(r"```(?:json)?\s*```", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def filter_stream_tool_tags(token_iterator: Iterator[str]) -> Iterator[str]:
    """Filter out <tool>...</tool> tags from a real-time token stream.

    Yields conversational tokens immediately while holding back tool markup
    so raw JSON is never leaked to the interactive console.
    """
    buffer = ""
    in_tool = False

    for token in token_iterator:
        buffer += token
        while buffer:
            if not in_tool:
                lower = buffer.lower()
                idx = lower.find("<tool")
                if idx != -1:
                    pre = buffer[:idx]
                    # Strip any trailing markdown code fence right before <tool>
                    stripped_pre = re.sub(r"```(?:json)?\s*$", "", pre)
                    if stripped_pre:
                        yield stripped_pre
                    buffer = buffer[idx:]
                    in_tool = True
                else:
                    prefix_match = False
                    for length in range(min(len(buffer), 5), 0, -1):
                        if "<tool"[:length] == lower[-length:]:
                            prefix = buffer[:-length]
                            if prefix:
                                yield prefix
                            buffer = buffer[-length:]
                            prefix_match = True
                            break
                    if prefix_match:
                        break
                    else:
                        yield buffer
                        buffer = ""
            else:
                end_idx = buffer.lower().find("</tool>")
                if end_idx != -1:
                    buffer = buffer[end_idx + 7:]
                    # Strip any trailing markdown code fence right after </tool>
                    buffer = re.sub(r"^\s*```", "", buffer)
                    in_tool = False
                else:
                    break

    if buffer and not in_tool:
        cleaned = re.sub(r"```(?:json)?\s*$", "", buffer)
        if cleaned:
            yield cleaned


def execute_tool_calls(
    calls: list[ToolCall],
    registry: ToolRegistry,
) -> Iterator[str]:
    """Execute a sequence of parsed tool calls and yield status messages.

    Yields human-readable status strings for each tool execution.
    """
    for call in calls:
        yield f"\n[Luca -> {call.name}...]\n"
        try:
            tool = registry.get(call.name)
            if tool is None:
                yield f"x Tool '{call.name}' not found.\n"
                continue
            result = tool.execute(**call.args)
            if result.success:
                yield f"OK: {result.output}\n"
            else:
                yield f"FAIL: {result.error}\n"
        except Exception as exc:
            yield f"Error: {exc}\n"
