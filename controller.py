"""Luca assistant controller.

The central orchestrator that:
  1. Loads configuration
  2. Initialises memory, safety, tools, and state
  3. Provides the fast conversation path (Phase 0 text-only)
  4. Provides clean startup/shutdown lifecycle

This is the only file that wires subsystems together.
"""

from __future__ import annotations

import logging
from pathlib import Path

from config import Identity, Settings, load_settings
from llm import LLMProvider, Message, OllamaProvider, system_prompt
from memory import MemoryManager, SQLiteMemoryStore
from safety import PermissionManager
from state import AppState, StateManager
from tools import ToolRegistry

logger = logging.getLogger(__name__)


class Controller:
    """Luca's brain — connects config, state, memory, LLM, safety, and tools."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.identity = Identity(self.settings.identity)
        self.state = StateManager()
        self.memory = MemoryManager(SQLiteMemoryStore(self.settings.memory.sqlite_path))
        self.permissions = PermissionManager(self.settings.safety)
        self.tools = ToolRegistry()
        self._llm: LLMProvider | None = None

    # ── Lifecycle ────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialise all subsystems and transition to STANDBY."""
        logger.info("Starting %s …", self.identity.assistant_name)

        # Ensure runtime directories exist
        for d in (self.settings.data_dir, self.settings.user_data_dir,
                  self.settings.logs_dir, self.settings.models_dir):
            Path(d).mkdir(parents=True, exist_ok=True)

        # Memory
        self.memory.initialize()

        # LLM (lazy — don't crash if Ollama isn't running)
        self._init_llm()

        self.state.transition(AppState.STANDBY)
        logger.info("%s", self.identity.greeting())

    def shutdown(self) -> None:
        """Clean shutdown."""
        self.state.transition(AppState.SHUTTING_DOWN)
        self.memory.close()
        logger.info("%s shut down.", self.identity.assistant_name)

    # ── Fast conversation path ───────────────────────────────────────

    def chat(self, user_input: str) -> str:
        """Handle a single text exchange (fast path).

        If no LLM is available, returns a friendly fallback message.
        """
        if not user_input.strip():
            return ""

        self.state.transition(AppState.THINKING)

        if self._llm is None or not self._llm.is_available():
            self.state.transition(AppState.STANDBY)
            return (f"[{self.identity.assistant_name}] I don't have an LLM "
                    f"connected right now. Please make sure Ollama is running.")

        messages = [
            Message("system", system_prompt(
                self.identity.assistant_name,
                self.identity.user_title,
                self.identity.personality,
            )),
            Message("user", user_input),
        ]

        try:
            response = self._llm.generate(messages)
            self.state.transition(AppState.STANDBY)
            return response.content
        except Exception as exc:
            logger.error("LLM error: %s", exc)
            self.state.transition(AppState.ERROR)
            return f"[{self.identity.assistant_name}] Sorry, something went wrong: {exc}"

    # ── Internal ─────────────────────────────────────────────────────

    def _init_llm(self) -> None:
        """Create the LLM provider.  Does NOT fail if Ollama is offline."""
        cfg = self.settings.llm
        if cfg.provider == "ollama":
            provider = OllamaProvider(
                host=cfg.host, model=cfg.model,
                temperature=cfg.temperature, max_tokens=cfg.max_tokens,
                timeout=cfg.timeout_seconds,
            )
            if provider.is_available():
                logger.info("Ollama connected (%s)", cfg.model)
            else:
                logger.warning("Ollama not reachable at %s — LLM features disabled until it starts", cfg.host)
            self._llm = provider
        else:
            logger.warning("Unknown LLM provider '%s' — no LLM loaded", cfg.provider)
