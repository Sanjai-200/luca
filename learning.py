"""Luca learning and feedback system.

Contains:
  - FeedbackEvaluator  — uses the LLM to decide whether a conversation turn
                         contains actionable feedback worth remembering permanently
  - LearnedRuleStore   — persists durable learned rules via the memory system

Design:
  Luca does NOT blindly store every correction.  After each exchange the
  FeedbackEvaluator asks the LLM:  "Does this exchange contain a preference,
  correction, behavioral rule, or important fact about Boss?"  Only if the
  LLM says YES does Luca extract and save a concise rule.

  Learned rules are PERMANENT — they survive conversation cleanup and
  remain from the very first day Luca was used.  They are injected into
  every future system prompt so Luca's behavior improves over time.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from llm import LLMProvider, LLMResponse, Message
from memory import MemoryCategory, MemoryItem, MemoryManager

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
#  Data model
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class FeedbackResult:
    """Result of evaluating a conversation turn for feedback."""
    has_feedback: bool
    rule_text: str = ""          # concise rule to store (empty if no feedback)
    category: str = ""           # preference | correction | fact | behavioral_rule
    confidence: float = 0.0      # 0.0–1.0  how confident the LLM is


# ═══════════════════════════════════════════════════════════════════════
#  Prompt for the LLM to evaluate feedback
# ═══════════════════════════════════════════════════════════════════════

_FEEDBACK_EVAL_PROMPT = """\
You are Luca's self-improvement module.  Analyze the following conversation \
exchange between the user (Boss) and the assistant (Luca).

Decide whether this exchange contains ANY of:
1. A user PREFERENCE  (e.g. "I prefer dark mode", "always use VS Code")
2. A CORRECTION       (e.g. "No, don't do it that way", "that's wrong")
3. An important FACT about Boss (e.g. "I'm a Python developer", "my name is Sanjai", "my project is at D:\\PA\\luca")
4. A BEHAVIORAL RULE  (e.g. "never delete files without asking", "always explain before acting")

IMPORTANT:
- Normal questions and casual chat are NOT feedback.
- Simple greetings, thank-yous, and small talk are NOT feedback.
- Only extract genuinely useful information that would improve future interactions.

Respond with EXACTLY this JSON (no markdown fences, no extra text):
{{"has_feedback": true/false, "rule_text": "concise rule or fact", "category": "preference/correction/fact/behavioral_rule", "confidence": 0.0-1.0}}

If there is no feedback, respond:
{{"has_feedback": false, "rule_text": "", "category": "", "confidence": 0.0}}

--- CONVERSATION ---
Boss: {user_message}
Luca: {assistant_response}
--- END ---
"""


# ═══════════════════════════════════════════════════════════════════════
#  Feedback Evaluator
# ═══════════════════════════════════════════════════════════════════════

class FeedbackEvaluator:
    """Uses the LLM to decide whether a turn contains learnable feedback."""

    CONFIDENCE_THRESHOLD = 0.6  # only save if LLM is at least 60% confident

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def evaluate(self, user_message: str, assistant_response: str) -> FeedbackResult:
        """Evaluate a single exchange.  Returns FeedbackResult."""
        if not self._llm.is_available():
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
            resp: LLMResponse = self._llm.generate(messages, temperature=0.1, max_tokens=256)
            return self._parse_response(resp.content)
        except Exception as exc:
            logger.debug("Feedback evaluation failed: %s", exc)
            return FeedbackResult(has_feedback=False)

    def _parse_response(self, raw: str) -> FeedbackResult:
        """Parse the LLM's JSON response into a FeedbackResult."""
        # Strip markdown fences if present
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
            # Apply confidence threshold
            if result.has_feedback and result.confidence < self.CONFIDENCE_THRESHOLD:
                logger.debug("Feedback below confidence threshold (%.2f): %s",
                             result.confidence, result.rule_text)
                result.has_feedback = False
            return result
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.debug("Failed to parse feedback JSON: %s — raw: %s", exc, raw[:200])
            return FeedbackResult(has_feedback=False)


# ═══════════════════════════════════════════════════════════════════════
#  Learned Rule Store
# ═══════════════════════════════════════════════════════════════════════

class LearnedRuleStore:
    """Manages permanent learned rules via the MemoryManager.

    These rules survive conversation cleanup and remain from day one.
    They are injected into system prompts to personalize Luca.
    """

    def __init__(self, memory: MemoryManager) -> None:
        self._memory = memory

    def save_rule(self, feedback: FeedbackResult) -> str | None:
        """Persist a feedback result as a permanent learned rule.

        Returns the memory item ID, or None if the feedback was not saved
        (duplicate or invalid).
        """
        if not feedback.has_feedback or not feedback.rule_text.strip():
            return None

        # Check for duplicates — don't save the same rule twice
        existing = self._memory.recall(
            feedback.rule_text, category=MemoryCategory.LEARNED_RULE, limit=3
        )
        for item in existing:
            # Simple similarity: if the existing rule contains most of the same words
            existing_words = set(item.content.lower().split())
            new_words = set(feedback.rule_text.lower().split())
            if len(existing_words & new_words) / max(len(new_words), 1) > 0.7:
                logger.debug("Duplicate learned rule skipped: %s", feedback.rule_text)
                return None

        item_id = self._memory.remember(
            content=feedback.rule_text,
            category=MemoryCategory.LEARNED_RULE,
            key=feedback.category,
            importance=0.9,  # learned rules are high importance — they persist forever
        )
        logger.info("Learned rule saved [%s]: %s", feedback.category, feedback.rule_text)
        return item_id

    def get_all_rules(self, limit: int = 50) -> list[MemoryItem]:
        """Retrieve all learned rules for system prompt injection."""
        return self._memory.recall("", category=MemoryCategory.LEARNED_RULE, limit=limit)

    def get_rules_text(self, limit: int = 30) -> str:
        """Return all learned rules as a formatted text block for prompt injection."""
        rules = self.get_all_rules(limit=limit)
        if not rules:
            return ""
        lines = [f"- {r.content}" for r in rules]
        return "Learned rules and preferences about Boss:\n" + "\n".join(lines)
