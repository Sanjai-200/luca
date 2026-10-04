"""Security — Permission Manager and input validation.

Migrated into a proper security module.
Implements the PermissionChecker interface from core.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from core.interfaces import (
    PermissionChecker, PermissionDecision, PermissionResult, RiskLevel,
)

logger = logging.getLogger(__name__)


# ── Risk classification table ────────────────────────────────────────

_DEFAULT_RISKS: dict[str, RiskLevel] = {
    "open_application": RiskLevel.LOW, "list_directory": RiskLevel.LOW,
    "read_file": RiskLevel.LOW, "search_files": RiskLevel.LOW,
    "get_system_info": RiskLevel.LOW, "open_app": RiskLevel.LOW,
    "wait": RiskLevel.LOW,
    "create_file": RiskLevel.MEDIUM, "modify_file": RiskLevel.MEDIUM,
    "type_keys": RiskLevel.MEDIUM, "run_command": RiskLevel.MEDIUM,
    "run_shell": RiskLevel.HIGH,
    "delete_file": RiskLevel.HIGH, "delete_directory": RiskLevel.HIGH,
    "format_disk": RiskLevel.HIGH, "modify_security": RiskLevel.HIGH,
}


def classify_risk(operation: str) -> RiskLevel:
    return _DEFAULT_RISKS.get(operation, RiskLevel.MEDIUM)


# ── Dangerous pattern detection ──────────────────────────────────────

_DANGEROUS_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/", re.IGNORECASE),
    re.compile(r"format\s+[a-z]:", re.IGNORECASE),
    re.compile(r"del\s+/[sfq]", re.IGNORECASE),
    re.compile(r"rmdir\s+/[sq]", re.IGNORECASE),
    re.compile(r"reg\s+delete", re.IGNORECASE),
    re.compile(r"net\s+user\s+", re.IGNORECASE),
]


@dataclass
class ValidationResult:
    valid: bool
    reason: str = ""


def validate_tool_call(tool_name: str, args: dict) -> ValidationResult:
    """Validate a tool call before it reaches the permission manager."""
    if not tool_name or not isinstance(tool_name, str):
        return ValidationResult(False, "Empty or invalid tool name")

    command = args.get("command", "") or args.get("cmd", "")
    if isinstance(command, str):
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(command):
                logger.warning("BLOCKED dangerous pattern in '%s': %s", tool_name, command[:120])
                return ValidationResult(False, f"Dangerous pattern: {pattern.pattern}")

    return ValidationResult(True)


# ── Permission Manager ───────────────────────────────────────────────

@dataclass
class SafetyConfig:
    """Safety / permission defaults."""
    auto_approve_low_risk: bool = True
    auto_approve_medium_risk: bool = False
    block_high_risk: bool = False


class PermissionManager(PermissionChecker):
    """Decides whether an operation should proceed based on risk + config.

    Implements the PermissionChecker interface from core.
    """

    def __init__(self, cfg: SafetyConfig) -> None:
        self._cfg = cfg

    def check(self, operation: str, **context: Any) -> PermissionResult:
        risk = classify_risk(operation)

        if risk is RiskLevel.LOW:
            if self._cfg.auto_approve_low_risk:
                return PermissionResult(PermissionDecision.ALLOW, risk)
            return PermissionResult(PermissionDecision.ASK, risk, "Low-risk — confirmation requested")

        if risk is RiskLevel.MEDIUM:
            if self._cfg.auto_approve_medium_risk:
                return PermissionResult(PermissionDecision.ALLOW, risk)
            return PermissionResult(PermissionDecision.ASK, risk, "Medium-risk — confirmation required")

        # HIGH
        if self._cfg.block_high_risk:
            return PermissionResult(PermissionDecision.DENY, risk, "High-risk operations blocked")
        return PermissionResult(PermissionDecision.ASK, risk, "High-risk — confirmation required")
