"""Intent Router — fast keyword classification with optional LLM fallback.

Migrated into the application layer.
The fast classifier uses zero-latency regex patterns.
LLM fallback is only used for genuinely ambiguous cases.
"""

from __future__ import annotations

import enum
import logging
import re
from dataclasses import dataclass

from core.interfaces import AIProvider, Message

logger = logging.getLogger(__name__)


class IntentType(enum.Enum):
    CONVERSATION = "conversation"
    ACTION = "action"
    FEEDBACK = "feedback"
    STATUS = "status"
    META = "meta"


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float = 1.0
    action_hint: str = ""


# ── Pattern sets ──────────────────────────────────────────────────────

_STATUS_PATTERNS = re.compile(
    r"^(status|state|health|check|info|diagnostics)$", re.IGNORECASE
)
_META_PATTERNS = re.compile(
    r"\b(who are you|what are you|your name|about yourself|introduce yourself"
    r"|what can you do|your purpose|your capabilities)\b", re.IGNORECASE
)
_FEEDBACK_PATTERNS = re.compile(
    r"\b(don't do|do not|stop doing|never|always|i prefer|i like|i want you to"
    r"|remember that|from now on|instead of|that's wrong|that is wrong"
    r"|correct that|fix that|no,\s|not like that"
    r"|my name is|call me|i am called|i live in|my job is|my role is)\b", re.IGNORECASE
)
_ACTION_PATTERNS = re.compile(
    r"\b(open|launch|start|run|close|create|make|delete|remove|move|copy"
    r"|rename|find|search|install|download|navigate|go to|show me|execute"
    r"|build|compile|deploy|restart|stop|kill|browse|visit|type|write)\b", re.IGNORECASE
)
_ACTION_TARGETS = re.compile(
    r"\b(file|folder|directory|app|application|browser|chrome|edge|firefox"
    r"|terminal|powershell|cmd|notepad|vs\s?code|project|script|website"
    r"|url|program|process|server|command)\b", re.IGNORECASE
)


class IntentClassifier:
    """Zero-latency keyword/pattern based intent classifier."""

    def classify(self, text: str) -> IntentResult:
        stripped = text.strip()
        if not stripped:
            return IntentResult(IntentType.CONVERSATION, confidence=1.0)

        if _STATUS_PATTERNS.match(stripped):
            return IntentResult(IntentType.STATUS, confidence=1.0)

        if _META_PATTERNS.search(stripped):
            return IntentResult(IntentType.META, confidence=0.9)

        if _FEEDBACK_PATTERNS.search(stripped):
            return IntentResult(IntentType.FEEDBACK, confidence=0.8)

        action_match = _ACTION_PATTERNS.search(stripped)
        target_match = _ACTION_TARGETS.search(stripped)
        if action_match and target_match:
            return IntentResult(IntentType.ACTION, confidence=0.85,
                                action_hint=action_match.group(0).lower())
        if action_match:
            return IntentResult(IntentType.ACTION, confidence=0.6,
                                action_hint=action_match.group(0).lower())

        return IntentResult(IntentType.CONVERSATION, confidence=0.7)


class LLMIntentClassifier:
    """Two-stage classifier: fast regex first, LLM fallback for ambiguous cases."""

    CONFIDENCE_THRESHOLD = 0.7

    def __init__(self, ai_provider: AIProvider, fast_classifier: IntentClassifier) -> None:
        self._ai = ai_provider
        self._fast = fast_classifier

    def classify(self, text: str) -> IntentResult:
        fast_result = self._fast.classify(text)
        if fast_result.confidence >= self.CONFIDENCE_THRESHOLD:
            return fast_result

        if not self._ai.is_available():
            return fast_result

        try:
            messages = [
                Message("system", "You are an intent classifier. Respond with one word only."),
                Message("user", (
                    "Classify into: CONVERSATION, ACTION, FEEDBACK, STATUS, META.\n"
                    f'User message: "{text}"\nRespond with one word only.'
                )),
            ]
            resp = self._ai.generate(messages, temperature=0.0, max_tokens=16)
            category = resp.content.strip().upper()
            intent_map = {
                "CONVERSATION": IntentType.CONVERSATION,
                "ACTION": IntentType.ACTION,
                "FEEDBACK": IntentType.FEEDBACK,
                "STATUS": IntentType.STATUS,
                "META": IntentType.META,
            }
            if category in intent_map:
                return IntentResult(intent_map[category], confidence=0.85)
        except Exception as exc:
            logger.debug("LLM intent classification failed: %s", exc)

        return fast_result
