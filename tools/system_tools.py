"""System tools — Shell execution, application launch, keyboard automation.

Each tool is a single-responsibility class implementing the Tool interface.
Tools are independently reusable and registered via ToolRegistry.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from core.interfaces import Tool, ToolResult, ToolSpec, RiskLevel

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  Shell Tool
# ═══════════════════════════════════════════════════════════════════════════

class ShellTool(Tool):
    """Execute a PowerShell command on the local system."""

    TIMEOUT = 30  # seconds

    @property
    def name(self) -> str:
        return "run_shell"

    @property
    def description(self) -> str:
        return "Run a PowerShell command. Args: {\"command\": \"string\"}"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
            parameters={"command": {"type": "string", "required": True}},
        )

    def validate(self, **kwargs: Any) -> bool:
        return bool(kwargs.get("command"))

    def execute(self, **kwargs: Any) -> ToolResult:
        cmd = kwargs.get("command", "")
        if not cmd:
            return ToolResult(success=False, error="No command provided")

        logger.info("ShellTool executing: %s", cmd[:120])
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=self.TIMEOUT,
            )
            if result.returncode == 0:
                return ToolResult(success=True, output=result.stdout.strip())
            return ToolResult(success=False, output=result.stdout.strip(), error=result.stderr.strip())
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"Command timed out after {self.TIMEOUT}s")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ═══════════════════════════════════════════════════════════════════════════
#  Open Application Tool
# ═══════════════════════════════════════════════════════════════════════════

class OpenAppTool(Tool):
    """Open an application or file using the Windows default handler."""

    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return "Open an application or file. Args: {\"target\": \"string\"}"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
            parameters={"target": {"type": "string", "required": True}},
        )

    def validate(self, **kwargs: Any) -> bool:
        return bool(kwargs.get("target"))

    def execute(self, **kwargs: Any) -> ToolResult:
        target = kwargs.get("target", "")
        if not target:
            return ToolResult(success=False, error="No target provided")

        logger.info("OpenAppTool opening: %s", target)
        try:
            os.startfile(target)
            return ToolResult(success=True, output=f"Opened {target}")
        except Exception:
            try:
                subprocess.Popen(
                    ["powershell", "-NoProfile", "-Command", f"Start-Process '{target}'"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                return ToolResult(success=True, output=f"Started {target} via PowerShell")
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to open {target}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════
#  Type Keys Tool (GUI Automation)
# ═══════════════════════════════════════════════════════════════════════════

class TypeKeysTool(Tool):
    """Simulate keyboard typing into the currently active window."""

    @property
    def name(self) -> str:
        return "type_keys"

    @property
    def description(self) -> str:
        return "Type text into the active window. Args: {\"keys\": \"string\"}"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
            parameters={"keys": {"type": "string", "required": True}},
        )

    def validate(self, **kwargs: Any) -> bool:
        return bool(kwargs.get("keys"))

    @staticmethod
    def _escape_sendkeys(text: str) -> str:
        """Escape characters so SendKeys treats them as literal characters, not hotkeys."""
        specials = {
            "{": "{{}",
            "}": "{}}",
            "+": "{+}",
            "^": "{^}",
            "%": "{%}",
            "~": "{~}",
            "(": "{(}",
            ")": "{)}",
            "[": "{[}",
            "]": "{]}",
        }
        escaped = []
        for ch in text:
            if ch in specials:
                escaped.append(specials[ch])
            elif ch == "'":
                escaped.append("''")
            else:
                escaped.append(ch)
        return "".join(escaped)

    def execute(self, **kwargs: Any) -> ToolResult:
        keys = kwargs.get("keys", "")
        if not keys:
            return ToolResult(success=False, error="No keys provided")

        safe_keys = self._escape_sendkeys(keys)
        ps_script = (
            "Start-Sleep -Milliseconds 500; "
            "Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.SendKeys]::SendWait('{safe_keys}')"
        )
        logger.info("TypeKeysTool typing: %s", keys[:80])
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return ToolResult(success=True, output=f"Typed: {keys}")
            return ToolResult(success=False, error=result.stderr.strip())
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ═══════════════════════════════════════════════════════════════════════════
#  Wait Tool
# ═══════════════════════════════════════════════════════════════════════════

class WaitTool(Tool):
    """Wait for a specified duration (used for tool chaining)."""

    @property
    def name(self) -> str:
        return "wait"

    @property
    def description(self) -> str:
        return "Wait for n seconds. Args: {\"seconds\": float}"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
            parameters={"seconds": {"type": "float", "required": True}},
        )

    def execute(self, **kwargs: Any) -> ToolResult:
        import time
        seconds = float(kwargs.get("seconds", 1.0))
        time.sleep(seconds)
        return ToolResult(success=True, output=f"Waited {seconds}s")
