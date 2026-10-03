"""Luca safety system.

Contains:
  - RiskLevel + classify_risk()       — risk classification
  - validate_tool_call()              — input validation (blocks dangerous patterns)
  - PermissionManager                 — decides allow / ask / deny per operation

Pipeline: Planner → Validator → PermissionManager → Tool Router → Tool
"""

from __future__ import annotations

import enum
import logging
import re
from dataclasses import dataclass

from config import SafetyConfig

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Risk classification
# ═══════════════════════════════════════════════════════════════════════

class RiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_DEFAULT_RISKS: dict[str, RiskLevel] = {
    # LOW
    "open_application": RiskLevel.LOW, "list_directory": RiskLevel.LOW,
    "read_file": RiskLevel.LOW, "search_files": RiskLevel.LOW,
    "get_system_info": RiskLevel.LOW,
    # MEDIUM
    "create_file": RiskLevel.MEDIUM, "modify_file": RiskLevel.MEDIUM,
    "install_dependency": RiskLevel.MEDIUM, "download_file": RiskLevel.MEDIUM,
    "run_command": RiskLevel.MEDIUM,
    # HIGH
    "delete_file": RiskLevel.HIGH, "delete_directory": RiskLevel.HIGH,
    "format_disk": RiskLevel.HIGH, "modify_security": RiskLevel.HIGH,
    "expose_credentials": RiskLevel.HIGH, "destructive_command": RiskLevel.HIGH,
}


def classify_risk(operation: str) -> RiskLevel:
    """Return the risk level for a given operation name."""
    return _DEFAULT_RISKS.get(operation, RiskLevel.MEDIUM)


# ═══════════════════════════════════════════════════════════════════════
#  Input validator
# ═══════════════════════════════════════════════════════════════════════

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
    """Validate a structured tool call before it reaches the permission manager."""
    if not tool_name or not isinstance(tool_name, str):
        return ValidationResult(False, "Empty or invalid tool name")

    command = args.get("command", "") or args.get("cmd", "")
    if isinstance(command, str):
        for pattern in _DANGEROUS_PATTERNS:
            if pattern.search(command):
                logger.warning("BLOCKED dangerous pattern in '%s': %s", tool_name, command[:120])
                return ValidationResult(False, f"Dangerous pattern: {pattern.pattern}")

    return ValidationResult(True)


# ═══════════════════════════════════════════════════════════════════════
#  Permission manager
# ═══════════════════════════════════════════════════════════════════════

class PermissionDecision(enum.Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class PermissionResult:
    decision: PermissionDecision
    risk_level: RiskLevel
    reason: str = ""


class PermissionManager:
    """Decides whether an operation should proceed based on risk + config."""

    def __init__(self, cfg: SafetyConfig) -> None:
        self._cfg = cfg

    def check(self, operation: str) -> PermissionResult:
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
