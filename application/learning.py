"""Learning & Feedback — self-improvement via feedback extraction.

Migrated into the application layer. Depends only on core interfaces,
MemoryManager, and AIProvider (injected, not concrete).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from core.interfaces import AIProvider, LLMResponse, Message, MemoryCategory, MemoryItem
from application.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


@dataclass
class FeedbackResult:
    """Result of evaluating a conversation turn for feedback."""
    has_feedback: bool
    rule_text: str = ""
    category: str = ""
    confidence: float = 0.0


_FEEDBACK_EVAL_PROMPT = """\
You are Luca's self-improvement module. Analyze the following conversation \
exchange between the user (Boss) and the assistant (Luca).

Decide whether this exchange contains ANY of:
1. A user PREFERENCE (e.g. "I prefer dark mode", "always use VS Code")
2. A CORRECTION (e.g. "No, don't do it that way", "that's wrong")
3. An important FACT about Boss (e.g. "I'm a Python developer", "my name is Sanjai")
4. A BEHAVIORAL RULE (e.g. "never delete files without asking")

IMPORTANT:
- Normal questions and casual chat are NOT feedback.
- Simple greetings are NOT feedback.

Respond with EXACTLY this JSON (no markdown fences, no extra text):
{{"has_feedback": true/false, "rule_text": "concise rule or fact", "category": "preference/correction/fact/behavioral_rule", "confidence": 0.0-1.0}}

If there is no feedback:
{{"has_feedback": false, "rule_text": "", "category": "", "confidence": 0.0}}

--- CONVERSATION ---
Boss: {user_message}
Luca: {assistant_response}
--- END ---
"""


class FeedbackEvaluator:
    """Uses the AI provider to decide whether a turn contains learnable feedback."""

    CONFIDENCE_THRESHOLD = 0.6

    def __init__(self, ai_provider: AIProvider) -> None:
        self._ai = ai_provider

    def evaluate(self, user_message: str, assistant_response: str) -> FeedbackResult:
        if not self._ai.is_available():
            return FeedbackResult(has_feedback=False)

        prompt = _FEEDBACK_EVAL_PROMPT.format(
            user_message=user_message,
            assistant_response=assistant_response,
        )
        messages = [
            Message("system", "You are a JSON-only analysis module. Output valid JSON only."),
            Message("user", prompt),
        ]
        try:
            resp: LLMResponse = self._ai.generate(messages, temperature=0.1, max_tokens=256)
            return self._parse_response(resp.content)
        except Exception as exc:
            logger.debug("Feedback evaluation failed: %s", exc)
            return FeedbackResult(has_feedback=False)

    def _parse_response(self, raw: str) -> FeedbackResult:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            data = json.loads(text)
            result = FeedbackResult(
                has_feedback=bool(data.get("has_feedback", False)),
                rule_text=str(data.get("rule_text", "")),
                category=str(data.get("category", "")),
                confidence=float(data.get("confidence", 0.0)),
            )
            if result.has_feedback and result.confidence < self.CONFIDENCE_THRESHOLD:
                result.has_feedback = False
            return result
        except (json.JSONDecodeError, ValueError, KeyError):
            return FeedbackResult(has_feedback=False)


class LearnedRuleStore:
    """Manages permanent learned rules via MemoryManager.

    These rules survive conversation cleanup and remain from day one.
    """

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def save_rule(self, feedback: FeedbackResult) -> str | None:
        if not feedback.has_feedback or not feedback.rule_text.strip():
            return None

        # Deduplicate
        existing = self._memory.recall(
            feedback.rule_text, category=MemoryCategory.LEARNED_RULE, limit=3
        )
        for item in existing:
            existing_words = set(item.content.lower().split())
            new_words = set(feedback.rule_text.lower().split())
            if len(existing_words & new_words) / max(len(new_words), 1) > 0.7:
                return None

        item_id = self._memory.remember(
            content=feedback.rule_text,
            category=MemoryCategory.LEARNED_RULE,
            key=feedback.category,
            importance=0.9,
        )
        logger.info("Learned rule saved [%s]: %s", feedback.category, feedback.rule_text)
        return item_id

    def get_all_rules(self, limit: int = 50) -> list[MemoryItem]:
        return self._memory.recall("", category=MemoryCategory.LEARNED_RULE, limit=limit)

    def get_rules_text(self, limit: int = 30) -> str:
        rules = self.get_all_rules(limit=limit)
        if not rules:
            return ""
        lines = [f"- {r.content}" for r in rules]
        return "Learned rules and preferences about Boss:\n" + "\n".join(lines)
