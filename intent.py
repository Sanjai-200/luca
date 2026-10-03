"""Luca intent classification system.

Contains:
  - IntentType         — enumeration of intent categories
  - IntentResult       — classification result with confidence
  - IntentClassifier   — keyword + pattern based fast classifier
  - LLMIntentClassifier — uses the LLM for ambiguous cases

Design:
  Two-stage classification:
    1. Fast keyword/pattern matching (zero latency) catches obvious intents
    2. LLM fallback for ambiguous messages (only when keyword match fails)

  This keeps the fast conversation path FAST — most casual questions are
  classified instantly without an LLM call.
"""

from __future__ import annotations

import enum
import logging
import re
from dataclasses import dataclass

from llm import LLMProvider, Message

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Data model
# ═══════════════════════════════════════════════════════════════════════

class IntentType(enum.Enum):
    """Categories of user intent."""
    CONVERSATION = "conversation"   # casual chat, questions, reasoning
    ACTION = "action"               # desktop tasks, tool use, commands
    FEEDBACK = "feedback"           # corrections, preferences, rules
    STATUS = "status"               # "status", system inspection
    META = "meta"                   # about Luca itself ("who are you?")


@dataclass
class IntentResult:
    """Result of intent classification."""
    intent: IntentType
    confidence: float = 1.0        # 0.0–1.0
    action_hint: str = ""          # optional: what action was detected


# ═══════════════════════════════════════════════════════════════════════
#  Pattern-based fast classifier (zero latency)
# ═══════════════════════════════════════════════════════════════════════

# Status commands
_STATUS_PATTERNS = re.compile(
    r"^(status|state|health|check|info|diagnostics)$", re.IGNORECASE
)

# Meta / identity questions
_META_PATTERNS = re.compile(
    r"\b(who are you|what are you|your name|about yourself|introduce yourself"
    r"|what can you do|your purpose|your capabilities)\b", re.IGNORECASE
)

# Feedback / correction patterns
_FEEDBACK_PATTERNS = re.compile(
    r"\b(don't do|do not|stop doing|never|always|i prefer|i like|i want you to"
    r"|remember that|from now on|instead of|that's wrong|that is wrong"
    r"|correct that|fix that|no,\s|not like that)\b", re.IGNORECASE
)

# Action / command patterns
_ACTION_PATTERNS = re.compile(
    r"\b(open|launch|start|run|close|create|make|delete|remove|move|copy"
    r"|rename|find|search|install|download|navigate|go to|show me|execute"
    r"|build|compile|deploy|restart|stop|kill|browse|visit)\b", re.IGNORECASE
)

# Targets that strongly indicate an action
_ACTION_TARGETS = re.compile(
    r"\b(file|folder|directory|app|application|browser|chrome|edge|firefox"
    r"|terminal|powershell|cmd|notepad|vs\s?code|project|script|website"
    r"|url|program|process|server|command)\b", re.IGNORECASE
)


class IntentClassifier:
    """Fast keyword and pattern based intent classifier.

    Designed for zero-latency classification of obvious intents.
    Falls back to IntentType.CONVERSATION for ambiguous messages.
    """

    def classify(self, text: str) -> IntentResult:
        """Classify user input into an intent category."""
        stripped = text.strip()
        if not stripped:
            return IntentResult(IntentType.CONVERSATION, confidence=1.0)

        # Status — exact match
        if _STATUS_PATTERNS.match(stripped):
            return IntentResult(IntentType.STATUS, confidence=1.0)

        # Meta — questions about Luca
        if _META_PATTERNS.search(stripped):
            return IntentResult(IntentType.META, confidence=0.9)

        # Feedback — corrections and preferences
        if _FEEDBACK_PATTERNS.search(stripped):
            return IntentResult(IntentType.FEEDBACK, confidence=0.8)

        # Action — commands with action verbs + targets
        action_match = _ACTION_PATTERNS.search(stripped)
        target_match = _ACTION_TARGETS.search(stripped)
        if action_match and target_match:
            return IntentResult(
                IntentType.ACTION, confidence=0.85,
                action_hint=action_match.group(0).lower()
            )
        if action_match:
            # Action verb without a clear target — could be conversation
            return IntentResult(IntentType.ACTION, confidence=0.6,
                                action_hint=action_match.group(0).lower())

        # Default: conversation (fast path)
        return IntentResult(IntentType.CONVERSATION, confidence=0.7)


# ═══════════════════════════════════════════════════════════════════════
#  LLM-backed classifier (for ambiguous cases — used sparingly)
# ═══════════════════════════════════════════════════════════════════════

_INTENT_LLM_PROMPT = """\
Classify the following user message into exactly ONE category:
- CONVERSATION: casual chat, questions, reasoning, explanations, greetings
- ACTION: requests to perform desktop tasks, open apps, manage files, run commands
- FEEDBACK: corrections, preferences, behavioral rules for the assistant
- STATUS: asking about system status or diagnostics
- META: questions about the assistant itself

Respond with ONLY the category name in uppercase. No explanation.

User message: "{text}"
"""


class LLMIntentClassifier:
    """Uses the LLM for ambiguous intent classification.

    Only invoked when the fast keyword classifier has low confidence.
    """

    CONFIDENCE_THRESHOLD = 0.7  # use LLM when fast classifier is below this

    def __init__(self, llm: LLMProvider, fast_classifier: IntentClassifier) -> None:
        self._llm = llm
        self._fast = fast_classifier

    def classify(self, text: str) -> IntentResult:
        """Two-stage classification: fast first, LLM fallback if needed."""
        fast_result = self._fast.classify(text)

        # If fast classifier is confident enough, use it
        if fast_result.confidence >= self.CONFIDENCE_THRESHOLD:
            return fast_result

        # LLM fallback
        if not self._llm.is_available():
            return fast_result

        try:
            messages = [
                Message("system", "You are an intent classifier. Respond with one word only."),
                Message("user", _INTENT_LLM_PROMPT.format(text=text)),
            ]
            resp = self._llm.generate(messages, temperature=0.0, max_tokens=16)
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
