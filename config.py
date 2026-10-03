"""Luca configuration system.

All application settings in one place.  Secrets come from environment
variables; identity from an optional YAML file; everything else from
sensible defaults.  No hard-coded identity values leak into the rest
of the codebase.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent          # D:/PA/luca
_DEFAULT_IDENTITY_FILE = _PROJECT_ROOT / "identity.yaml"


# ═══════════════════════════════════════════════════════════════════════
#  Sub-configs
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class IdentityConfig:
    """Configurable assistant / user identity."""
    assistant_name: str = "Luca"
    user_title: str = "Boss"
    wake_name: str = "Luca"
    personality: str = "friendly, helpful, concise"


@dataclass
class LLMConfig:
    """LLM provider settings."""
    provider: str = "ollama"
    model: str = "phi3:mini"
    host: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 1024
    timeout_seconds: int = 60


@dataclass
class MemoryConfig:
    """Memory / database settings."""
    backend: str = "sqlite"
    sqlite_path: str = ""          # resolved at runtime
    conversation_retention_days: int = 30


@dataclass
class VoiceConfig:
    """Voice pipeline settings (Phase 6+)."""
    stt_provider: str = "none"
    tts_provider: str = "none"
    wake_provider: str = "none"
    speaker_verification_provider: str = "none"
    tts_voice: str = "default"
    tts_speed: float = 1.0


@dataclass
class SafetyConfig:
    """Safety / permission defaults."""
    auto_approve_low_risk: bool = True
    auto_approve_medium_risk: bool = False
    block_high_risk: bool = False   # False = ask user, True = always block


@dataclass
class UIConfig:
    """Character / UI settings (Phase 7+)."""
    character_enabled: bool = False
    tray_enabled: bool = True


@dataclass
class InternetConfig:
    """Internet access policy."""
    enabled: bool = False
    search_provider: str = "none"
    browser_provider: str = "none"


# ═══════════════════════════════════════════════════════════════════════
#  Top-level Settings
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class Settings:
    """Top-level application settings aggregate."""
    identity: IdentityConfig = field(default_factory=IdentityConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    voice: VoiceConfig = field(default_factory=VoiceConfig)
    safety: SafetyConfig = field(default_factory=SafetyConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    internet: InternetConfig = field(default_factory=InternetConfig)

    # Paths
    project_root: str = ""
    data_dir: str = ""
    user_data_dir: str = ""
    logs_dir: str = ""
    models_dir: str = ""

    # Runtime
    debug: bool = False
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if not self.project_root:
            self.project_root = str(_PROJECT_ROOT)
        root = Path(self.project_root)
        if not self.data_dir:
            self.data_dir = str(root / "data")
        if not self.user_data_dir:
            self.user_data_dir = str(root / "user_data")
        if not self.logs_dir:
            self.logs_dir = str(root / "logs")
        if not self.models_dir:
            self.models_dir = str(root / "models")
        if not self.memory.sqlite_path:
            self.memory.sqlite_path = str(Path(self.user_data_dir) / "luca_memory.db")


# ═══════════════════════════════════════════════════════════════════════
#  Identity helper
# ═══════════════════════════════════════════════════════════════════════

class Identity:
    """Runtime identity derived from configuration."""

    def __init__(self, cfg: IdentityConfig) -> None:
        self.assistant_name = cfg.assistant_name
        self.user_title = cfg.user_title
        self.wake_name = cfg.wake_name
        self.personality = cfg.personality

    def greeting(self) -> str:
        return f"Hello, {self.user_title}. {self.assistant_name} is ready."


# ═══════════════════════════════════════════════════════════════════════
#  Loader
# ═══════════════════════════════════════════════════════════════════════

def _apply_env_overrides(settings: Settings) -> None:
    """Apply environment-variable overrides (secrets & debug flags)."""
    if val := os.environ.get("OLLAMA_HOST"):
        settings.llm.host = val
    if val := os.environ.get("OLLAMA_MODEL"):
        settings.llm.model = val
    if os.environ.get("LUCA_DEBUG", "").lower() in ("1", "true", "yes"):
        settings.debug = True
        settings.log_level = "DEBUG"
    if val := os.environ.get("LUCA_LOG_LEVEL"):
        settings.log_level = val.upper()


def _load_identity_file(settings: Settings, path: Path | None = None) -> None:
    """Load identity overrides from a YAML file if present."""
    filepath = path or _DEFAULT_IDENTITY_FILE
    if not filepath.exists():
        return
    try:
        import yaml  # optional dependency
        with open(filepath, "r", encoding="utf-8") as fh:
            data: dict[str, Any] = yaml.safe_load(fh) or {}
        ident = data.get("identity", {})
        for key in ("assistant_name", "user_title", "wake_name", "personality"):
            if key in ident:
                setattr(settings.identity, key, ident[key])
        logger.debug("Identity loaded from %s", filepath)
    except ImportError:
        logger.debug("PyYAML not installed — skipping identity file %s", filepath)
    except Exception:
        logger.warning("Failed to parse identity file %s", filepath, exc_info=True)


def load_settings(identity_path: Path | None = None, *, apply_env: bool = True) -> Settings:
    """Create and return a fully resolved Settings instance."""
    settings = Settings()
    _load_identity_file(settings, identity_path)
    if apply_env:
        _apply_env_overrides(settings)
    return settings
