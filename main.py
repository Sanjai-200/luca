"""Luca — main entry point.

Usage:
    python main.py              Start Luca in interactive text mode
    python main.py --check      Run a quick startup health check and exit
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path so all modules import cleanly.
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config import load_settings
from controller import Controller


def setup_logging(level: str = "INFO", logs_dir: str = "") -> None:
    """Configure logging to console (and optionally to a file)."""
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if logs_dir:
        log_path = Path(logs_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path / "luca.log", encoding="utf-8"))
    logging.basicConfig(level=getattr(logging, level, logging.INFO),
                        format=fmt, handlers=handlers)


def health_check() -> bool:
    """Run a quick startup/import/init check and return True if everything is OK."""
    print("=== Luca Health Check ===")
    settings = load_settings()
    print(f"  Project root : {settings.project_root}")
    print(f"  Assistant    : {settings.identity.assistant_name}")
    print(f"  User title   : {settings.identity.user_title}")
    print(f"  LLM provider : {settings.llm.provider} ({settings.llm.model})")
    print(f"  Memory       : {settings.memory.backend} -> {settings.memory.sqlite_path}")
    print(f"  Debug        : {settings.debug}")

    ctrl = Controller(settings)
    ctrl.start()
    print(f"  State        : {ctrl.state.state.value}")
    print(f"  Memory       : initialised OK")
    print(f"  Tools        : {len(ctrl.tools.tool_names)} registered")
    ctrl.shutdown()
    print("=== All checks passed ===")
    return True


def interactive_loop(ctrl: Controller) -> None:
    """Interactive text input loop with Phase 1 conversation pipeline."""
    name = ctrl.identity.assistant_name
    title = ctrl.identity.user_title
    print(f"\n{ctrl.identity.greeting()}")
    print(f"Type a message to talk to {name}, or 'quit' to exit.\n")

    while True:
        try:
            user_input = input(f"{title}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "shutdown"):
            break

        response = ctrl.chat(user_input)
        print(f"{name}: {response}\n")


def main() -> None:
    if "--check" in sys.argv:
        success = health_check()
        sys.exit(0 if success else 1)

    settings = load_settings()
    setup_logging(settings.log_level, settings.logs_dir)

    ctrl = Controller(settings)
    try:
        ctrl.start()
        interactive_loop(ctrl)
    except Exception:
        logging.exception("Fatal error")
    finally:
        ctrl.shutdown()


if __name__ == "__main__":
    main()
