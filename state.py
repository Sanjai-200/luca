"""Luca application state machine.

Thread-safe observable state model.  Any UI, logger, or subsystem can
subscribe to state transitions via listeners without tight coupling.
"""

from __future__ import annotations

import enum
import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)


class AppState(enum.Enum):
    """All possible application states."""
    INITIALIZING = "initializing"
    STANDBY = "standby"
    LISTENING = "listening"
    THINKING = "thinking"
    WORKING = "working"
    SPEAKING = "speaking"
    SLEEPING = "sleeping"
    PAUSED = "paused"
    CANCELLING = "cancelling"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


# Type alias for state-change listeners: fn(old_state, new_state)
StateListener = Callable[[AppState, AppState], None]


class StateManager:
    """Thread-safe observable state machine."""

    def __init__(self, initial: AppState = AppState.INITIALIZING) -> None:
        self._state = initial
        self._lock = threading.Lock()
        self._listeners: list[StateListener] = []
        logger.debug("StateManager created — initial: %s", initial.value)

    @property
    def state(self) -> AppState:
        with self._lock:
            return self._state

    def transition(self, new_state: AppState) -> None:
        """Move to *new_state* and notify all listeners."""
        with self._lock:
            old = self._state
            if old is new_state:
                return
            self._state = new_state
            listeners = list(self._listeners)

        logger.info("State: %s -> %s", old.value, new_state.value)
        for fn in listeners:
            try:
                fn(old, new_state)
            except Exception:
                logger.exception("Listener error during %s -> %s", old.value, new_state.value)

    def add_listener(self, listener: StateListener) -> None:
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener: StateListener) -> None:
        with self._lock:
            try:
                self._listeners.remove(listener)
            except ValueError:
                pass
