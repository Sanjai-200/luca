"""Bootstrap — Dependency Injection wiring and application assembly.

This is the ONLY place where concrete implementations are instantiated and
injected into the application layer. Changing a provider (e.g., Ollama → Gemini,
SQLite → PostgreSQL) requires modifying ONLY this file.

No business logic lives here.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from infrastructure.ollama_provider import OllamaProvider
from infrastructure.sqlite_memory import SQLiteMemoryStore
from application.memory_manager import MemoryManager
from application.orchestrator import Orchestrator
from tools.registry import ToolRegistry
from tools.system_tools import ShellTool, OpenAppTool, CloseAppTool, TypeKeysTool, WaitTool

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent  # D:/PA/luca


# ═══════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class LucaConfig:
    """Complete application configuration — typed, centralized, no magic."""

    # Identity
    assistant_name: str = "Luca"
    user_title: str = "Boss"
    personality: str = "friendly, helpful, concise"

    # AI Provider
    ai_provider: str = "ollama"
    ai_model: str = "phi3:mini"
    ai_host: str = "http://localhost:11434"
    ai_temperature: float = 0.7
    ai_max_tokens: int = 256
    ai_timeout: int = 60

    # Memory
    memory_backend: str = "sqlite"
    sqlite_path: str = ""

    # Paths
    project_root: str = ""
    data_dir: str = ""
    user_data_dir: str = ""
    logs_dir: str = ""

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
        if not self.sqlite_path:
            self.sqlite_path = str(Path(self.user_data_dir) / "luca_memory.db")


def load_config() -> LucaConfig:
    """Load configuration from environment variables with sensible defaults."""
    config = LucaConfig()

    # Try loading identity from YAML if available
    identity_file = Path(config.project_root) / "identity.yaml"
    if identity_file.exists():
        try:
            import yaml
            with open(identity_file, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            ident = data.get("identity", {})
            if "assistant_name" in ident:
                config.assistant_name = ident["assistant_name"]
            if "user_title" in ident:
                config.user_title = ident["user_title"]
            if "personality" in ident:
                config.personality = ident["personality"]
        except ImportError:
            logger.debug("PyYAML not installed — skipping identity.yaml")
        except Exception:
            logger.warning("Failed to parse identity.yaml", exc_info=True)

    # Environment overrides
    if val := os.environ.get("OLLAMA_HOST"):
        config.ai_host = val
    if val := os.environ.get("OLLAMA_MODEL"):
        config.ai_model = val
    if os.environ.get("LUCA_DEBUG", "").lower() in ("1", "true", "yes"):
        config.debug = True
        config.log_level = "DEBUG"
    if val := os.environ.get("LUCA_LOG_LEVEL"):
        config.log_level = val.upper()

    return config


# ═══════════════════════════════════════════════════════════════════════════
#  Assembly (Dependency Injection)
# ═══════════════════════════════════════════════════════════════════════════

def create_orchestrator(config: LucaConfig | None = None) -> Orchestrator:
    """Assemble the entire Luca application from configuration.

    This is the composition root — the ONLY place where concrete
    implementations are instantiated and injected.
    """
    if config is None:
        config = load_config()

    # Ensure directories exist
    for d in (config.data_dir, config.user_data_dir, config.logs_dir):
        Path(d).mkdir(parents=True, exist_ok=True)

    # 1. Infrastructure: AI Provider
    ai_provider = None
    if config.ai_provider == "ollama":
        provider = OllamaProvider(
            host=config.ai_host,
            model=config.ai_model,
            temperature=config.ai_temperature,
            max_tokens=config.ai_max_tokens,
            timeout=config.ai_timeout,
        )
        if provider.is_available():
            logger.info("Ollama connected (%s)", config.ai_model)
            ai_provider = provider
        else:
            logger.warning("Ollama not reachable — LLM features disabled")
            ai_provider = provider  # Still inject it — it will report unavailable

    # 2. Infrastructure: Memory Store
    memory_store = SQLiteMemoryStore(config.sqlite_path)
    memory_manager = MemoryManager(memory_store)

    # 3. Tools: Register all available tools
    tool_registry = ToolRegistry()
    tool_registry.register(ShellTool())
    tool_registry.register(OpenAppTool())
    tool_registry.register(CloseAppTool())
    tool_registry.register(TypeKeysTool())
    tool_registry.register(WaitTool())

    # 4. Assemble the Orchestrator (all dependencies injected)
    orchestrator = Orchestrator(
        ai_provider=ai_provider,
        memory=memory_manager,
        tool_registry=tool_registry,
        assistant_name=config.assistant_name,
        user_title=config.user_title,
        personality=config.personality,
        max_response_tokens=config.ai_max_tokens,
    )

    return orchestrator
