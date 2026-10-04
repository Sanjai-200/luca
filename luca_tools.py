"""Luca core tools implementations (Phase 4/5)."""

import os
import subprocess
from typing import Any

from safety import RiskLevel
from tools import Tool, ToolResult

class ShellTool(Tool):
    @property
    def name(self) -> str:
        return "run_shell"

    @property
    def description(self) -> str:
        return "Run a shell/PowerShell command on the system."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.HIGH

    def execute(self, **kwargs: Any) -> ToolResult:
        cmd = kwargs.get("command")
        if not cmd:
            return ToolResult(success=False, error="No command provided")
        
        try:
            result = subprocess.run(["powershell", "-Command", cmd], 
                                    capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return ToolResult(success=True, output=result.stdout.strip())
            else:
                return ToolResult(success=False, error=result.stderr.strip())
        except Exception as e:
            return ToolResult(success=False, error=str(e))

class OpenAppTool(Tool):
    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return "Open an application or file using the default system handler."

    @property
    def risk_level(self) -> RiskLevel:
        return RiskLevel.LOW

    def execute(self, **kwargs: Any) -> ToolResult:
        target = kwargs.get("target")
        if not target:
            return ToolResult(success=False, error="No target provided")
        
        try:
            os.startfile(target)
            return ToolResult(success=True, output=f"Successfully opened {target}")
        except Exception as e:
            # Fallback to shell start
            try:
                subprocess.run(["powershell", "-Command", f"Start-Process '{target}'"], check=True)
                return ToolResult(success=True, output=f"Started {target} via PowerShell")
            except Exception as e2:
                return ToolResult(success=False, error=f"Failed to open {target}: {e2}")

