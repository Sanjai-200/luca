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
    """Open an application, file, or URL using the Windows default handler."""

    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return "Open an application, file, or website URL. Args: {\"target\": \"string\"}"

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
        target = kwargs.get("target", "").strip()
        if not target:
            return ToolResult(success=False, error="No target provided")

        logger.info("OpenAppTool opening: %s", target)

        # Handle URLs directly
        if target.startswith(("http://", "https://")):
            try:
                os.startfile(target)
                return ToolResult(success=True, output=f"Opened {target}")
            except Exception:
                pass

        # Try os.startfile for local files/programs without arguments
        if " " not in target and os.path.exists(target):
            try:
                os.startfile(target)
                return ToolResult(success=True, output=f"Opened {target}")
            except Exception:
                pass

        # Use cmd.exe /c start "" for all applications and commands (e.g. 'code', 'notepad', 'calc')
        # completely detached so child application stdout/stderr never leaks into the console
        try:
            DETACHED = 0x00000008
            CREATE_NEW_GROUP = 0x00000200
            subprocess.Popen(
                f'cmd.exe /c start "" {target}',
                shell=False,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=DETACHED | CREATE_NEW_GROUP,
            )
            return ToolResult(success=True, output=f"Opened {target}")
        except Exception as exc:
            return ToolResult(success=False, error=f"Failed to open {target}: {exc}")


# ═══════════════════════════════════════════════════════════════════════════
#  Close Application Tool
# ═══════════════════════════════════════════════════════════════════════════

class CloseAppTool(Tool):
    """Close an application or terminate a process by name."""

    @property
    def name(self) -> str:
        return "close_app"

    @property
    def description(self) -> str:
        return "Close or terminate an application. Args: {\"target\": \"string\"}"

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
        target = kwargs.get("target", "").strip()
        if not target:
            return ToolResult(success=False, error="No target provided")

        proc_name = target[:-4] if target.lower().endswith(".exe") else target
        logger.info("CloseAppTool closing: %s", proc_name)

        ps_script = (
            f"$p = Get-Process -Name '{proc_name}' -ErrorAction SilentlyContinue; "
            f"if ($p) {{ $p | Stop-Process -Force; 'Closed {target}' }} "
            f"else {{ 'Process {target} is not running' }}"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=10,
            )
            out = result.stdout.strip()
            if result.returncode == 0:
                return ToolResult(success=True, output=out or f"Closed {target}")
            return ToolResult(success=False, error=result.stderr.strip() or f"Failed to close {target}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


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
#  Press Key Tool
# ═══════════════════════════════════════════════════════════════════════════

class PressKeyTool(Tool):
    """Simulate pressing a special keyboard key (e.g. Enter, Tab, Escape, Space)."""

    _KEY_MAP = {
        "enter": "{ENTER}",
        "return": "{ENTER}",
        "tab": "{TAB}",
        "escape": "{ESC}",
        "esc": "{ESC}",
        "space": " ",
        "backspace": "{BACKSPACE}",
        "delete": "{DELETE}",
        "del": "{DELETE}",
        "up": "{UP}",
        "down": "{DOWN}",
        "left": "{LEFT}",
        "right": "{RIGHT}",
        "home": "{HOME}",
        "end": "{END}",
        "pageup": "{PGUP}",
        "pagedown": "{PGDN}",
    }

    @property
    def name(self) -> str:
        return "press_key"

    @property
    def description(self) -> str:
        return "Press a special key (e.g. 'enter', 'tab', 'esc', 'space', 'up', 'down'). Args: {\"key\": \"string\"}"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.MEDIUM

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
            parameters={"key": {"type": "string", "required": True}},
        )

    def validate(self, **kwargs: Any) -> bool:
        return bool(kwargs.get("key"))

    def execute(self, **kwargs: Any) -> ToolResult:
        raw_key = kwargs.get("key", "").strip().lower()
        if not raw_key:
            return ToolResult(success=False, error="No key provided")

        send_key = self._KEY_MAP.get(raw_key)
        if not send_key:
            if len(raw_key) == 1:
                send_key = raw_key
            else:
                return ToolResult(
                    success=False,
                    error=f"Unsupported key '{raw_key}'. Supported keys: {', '.join(sorted(self._KEY_MAP.keys()))}"
                )

        ps_script = (
            "Start-Sleep -Milliseconds 200; "
            "Add-Type -AssemblyName System.Windows.Forms; "
            f"[System.Windows.Forms.SendKeys]::SendWait('{send_key}')"
        )
        logger.info("PressKeyTool pressing: %s -> %s", raw_key, send_key)
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return ToolResult(success=True, output=f"Pressed {raw_key}")
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


# ═══════════════════════════════════════════════════════════════════════════
#  Search Web Tool
# ═══════════════════════════════════════════════════════════════════════════

class SearchWebTool(Tool):
    """Search Google or YouTube in the default browser without URL hallucination."""

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return "Search Google or YouTube in the web browser. Args: {\"query\": \"string\", \"site\": \"google|youtube\"}"

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    @property
    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            risk_level=self.risk_level,
            parameters={
                "query": {"type": "string", "required": True},
                "site": {"type": "string", "required": False},
            },
        )

    def validate(self, **kwargs: Any) -> bool:
        return bool(kwargs.get("query"))

    def execute(self, **kwargs: Any) -> ToolResult:
        import urllib.parse
        query = kwargs.get("query", "").strip()
        if not query:
            return ToolResult(success=False, error="No search query provided")

        site = kwargs.get("site", "google").strip().lower()
        encoded = urllib.parse.quote_plus(query)

        if "youtube" in site:
            url = f"https://www.youtube.com/results?search_query={encoded}"
        else:
            url = f"https://www.google.com/search?q={encoded}"

        logger.info("SearchWebTool opening %s search for: %s", site, query)
        try:
            os.startfile(url)
            return ToolResult(success=True, output=f"Opened {site} search for '{query}'")
        except Exception:
            try:
                subprocess.Popen(
                    f'cmd.exe /c start "" "{url}"',
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x00000008 | 0x00000200,
                )
                return ToolResult(success=True, output=f"Opened {site} search for '{query}'")
            except Exception as exc:
                return ToolResult(success=False, error=f"Failed to open browser: {exc}")
