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
    setup_logging(config.log_level, config.logs_dir)

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
