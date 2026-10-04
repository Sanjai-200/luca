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

    _UWP_MAP = {
        "whatsapp": "whatsapp:",
        "spotify": "spotify:",
        "netflix": "netflix:",
        "settings": "ms-settings:",
        "calculator": "calculator:",
        "paint": "ms-paint:",
        "mail": "mailto:",
        "camera": "microsoft.windows.camera:",
        "maps": "bingmaps:",
        "store": "ms-windows-store:",
        "photos": "ms-photos:",
        "clock": "ms-clock:",
        "calendar": "outlookcal:",
        "weather": "bingweather:",
        "news": "bingnews:",
        "xbox": "xbox:",
        "discord": "discord:",
        "zoom": "zoommtg:",
    }

    def _search_for_shortcut(self, app_name: str) -> str | None:
        """Search the Start Menu and Desktop for a shortcut matching the app name."""
        search_paths = [
            os.path.expandvars(r"%ProgramData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%AppData%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            os.path.expandvars(r"%PUBLIC%\Desktop"),
        ]
        
        app_name_lower = app_name.lower().replace(".exe", "")
        
        for base_path in search_paths:
            if not os.path.exists(base_path):
                continue
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        name_without_ext = file[:-4].lower()
                        if app_name_lower in name_without_ext:
                            return os.path.join(root, file)
        return None

    def execute(self, **kwargs: Any) -> ToolResult:
        target = kwargs.get("target", "").strip()
        if not target:
            return ToolResult(success=False, error="No target provided")

        lower_target = target.lower()
        if lower_target in self._UWP_MAP:
            target = self._UWP_MAP[lower_target]

        logger.info("OpenAppTool opening: %s", target)

        # Handle URLs and protocols directly
        if target.startswith(("http://", "https://")) or target.endswith(":"):
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

        # Search for Start Menu/Desktop shortcuts
        shortcut_path = self._search_for_shortcut(target)
        if shortcut_path:
            logger.info("OpenAppTool found shortcut: %s", shortcut_path)
            try:
                os.startfile(shortcut_path)
                return ToolResult(success=True, output=f"Opened {target} via shortcut")
            except Exception as exc:
                logger.warning("Failed to open shortcut %s: %s", shortcut_path, exc)

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
#  Win32 SendInput helpers (stdlib ctypes — no external deps)
# ═══════════════════════════════════════════════════════════════════════════

import ctypes
import ctypes.wintypes
import time

# Win32 constants
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

# C structures for SendInput
class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT(ctypes.Structure):
    class _INPUT_UNION(ctypes.Union):
        _fields_ = [("ki", KEYBDINPUT)]
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


def _send_unicode_char(char: str) -> None:
    """Send a single Unicode character via SendInput (keydown + keyup)."""
    code = ord(char)
    inputs = (INPUT * 2)()

    # Key down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].union.ki.wVk = 0
    inputs[0].union.ki.wScan = code
    inputs[0].union.ki.dwFlags = KEYEVENTF_UNICODE
    inputs[0].union.ki.time = 0
    inputs[0].union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))

    # Key up
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].union.ki.wVk = 0
    inputs[1].union.ki.wScan = code
    inputs[1].union.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
    inputs[1].union.ki.time = 0
    inputs[1].union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))

    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


def _send_vk_key(vk_code: int) -> None:
    """Send a virtual-key press via SendInput (keydown + keyup)."""
    scan = ctypes.windll.user32.MapVirtualKeyW(vk_code, 0)
    inputs = (INPUT * 2)()

    # Key down
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].union.ki.wVk = vk_code
    inputs[0].union.ki.wScan = scan
    inputs[0].union.ki.dwFlags = 0
    inputs[0].union.ki.time = 0
    inputs[0].union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))

    # Key up
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].union.ki.wVk = vk_code
    inputs[1].union.ki.wScan = scan
    inputs[1].union.ki.dwFlags = KEYEVENTF_KEYUP
    inputs[1].union.ki.time = 0
    inputs[1].union.ki.dwExtraInfo = ctypes.pointer(ctypes.c_ulong(0))

    ctypes.windll.user32.SendInput(2, ctypes.byref(inputs), ctypes.sizeof(INPUT))


# Virtual key codes for special keys
_VK_MAP = {
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "escape": 0x1B,
    "esc": 0x1B,
    "space": 0x20,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
    "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
    "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
    "capslock": 0x14,
    "numlock": 0x90,
    "scrolllock": 0x91,
    "insert": 0x2D,
    "printscreen": 0x2C,
}


# ═══════════════════════════════════════════════════════════════════════════
#  Type Keys Tool (GUI Automation via Win32 SendInput)
# ═══════════════════════════════════════════════════════════════════════════

class TypeKeysTool(Tool):
    """Simulate keyboard typing into the currently active window using Win32 SendInput."""

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

    def execute(self, **kwargs: Any) -> ToolResult:
        keys = kwargs.get("keys", "")
        if not keys:
            return ToolResult(success=False, error="No keys provided")

        logger.info("TypeKeysTool typing: %s", keys[:80])
        try:
            time.sleep(0.3)  # brief pause to let target window become ready
            for ch in keys:
                _send_unicode_char(ch)
                time.sleep(0.02)  # small inter-key delay for reliability
            return ToolResult(success=True, output=f"Typed: {keys}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


# ═══════════════════════════════════════════════════════════════════════════
#  Press Key Tool (via Win32 SendInput)
# ═══════════════════════════════════════════════════════════════════════════

class PressKeyTool(Tool):
    """Simulate pressing a special keyboard key (e.g. Enter, Tab, Escape, Space)."""

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

        vk = _VK_MAP.get(raw_key)
        if vk is None:
            if len(raw_key) == 1:
                # Single printable character — send as unicode
                logger.info("PressKeyTool pressing char: %s", raw_key)
                try:
                    time.sleep(0.15)
                    _send_unicode_char(raw_key)
                    return ToolResult(success=True, output=f"Pressed {raw_key}")
                except Exception as exc:
                    return ToolResult(success=False, error=str(exc))
            else:
                return ToolResult(
                    success=False,
                    error=f"Unsupported key '{raw_key}'. Supported keys: {', '.join(sorted(_VK_MAP.keys()))}"
                )

        logger.info("PressKeyTool pressing: %s -> VK 0x%02X", raw_key, vk)
        try:
            time.sleep(0.15)
            _send_vk_key(vk)
            return ToolResult(success=True, output=f"Pressed {raw_key}")
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
