"""Luca — main entry point.

Usage:
    python main.py              Start Luca in interactive text mode
    python main.py --check      Run a quick startup health check and exit
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Ensure the project root is on sys.path
_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.bootstrap import load_config, create_orchestrator


def setup_logging(level: str = "INFO", logs_dir: str = "", debug: bool = False) -> None:
    """Configure logging: clean interactive console, detailed file logging."""
    fmt = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
    formatter = logging.Formatter(fmt)

    # Console handler: keep interactive terminal clean unless debug mode is enabled
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.WARNING)
    console_handler.setFormatter(formatter)
    handlers: list[logging.Handler] = [console_handler]

    if logs_dir:
        log_path = Path(logs_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path / "luca.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG if debug else getattr(logging, level, logging.INFO))
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else getattr(logging, level, logging.INFO))
    root_logger.handlers.clear()
    for h in handlers:
        root_logger.addHandler(h)


def health_check() -> bool:
    """Run a quick startup/import/init check."""
    print("=== Luca Health Check ===")
    config = load_config()
    print(f"  Project root : {config.project_root}")
    print(f"  Assistant    : {config.assistant_name}")
    print(f"  User title   : {config.user_title}")
    print(f"  AI provider  : {config.ai_provider} ({config.ai_model})")
    print(f"  Memory       : {config.memory_backend} -> {config.sqlite_path}")

    orchestrator = create_orchestrator(config)
    orchestrator.start()
    print(f"  State        : {orchestrator.state.value}")
    print(f"  Tools        : {len(orchestrator._tools)} registered")
    orchestrator.shutdown()
    print("=== All checks passed ===")
    return True


def interactive_loop(orchestrator) -> None:
    """Interactive text input loop with real-time streaming."""
    name = orchestrator.assistant_name
    title = orchestrator.user_title
    print(f"\nHello, {title}. {name} is ready.")
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

        print(f"{name}: ", end="", flush=True)
        for token in orchestrator.chat_stream(user_input):
            print(token, end="", flush=True)
        print("\n")


def main() -> None:
    if "--check" in sys.argv:
        success = health_check()
        sys.exit(0 if success else 1)

    config = load_config()
    setup_logging(config.log_level, config.logs_dir, debug=config.debug)

    orchestrator = create_orchestrator(config)
    try:
        orchestrator.start()
        interactive_loop(orchestrator)
    except Exception:
        logging.exception("Fatal error")
    finally:
        orchestrator.shutdown()


if __name__ == "__main__":
    main()
