"""Luca Orchestrator — the central coordinator (replaces the old God-object controller).

This is the ONLY class that wires subsystems together.
It does NOT contain business logic for prompts, tools, memory, or AI.
It coordinates the flow: input → intent → context → AI → tools → response → learn.

All dependencies are injected — the Orchestrator knows interfaces, not implementations.
"""

from __future__ import annotations

import logging
import threading
from typing import Iterator

from core.interfaces import AIProvider, AppState, Message, MemoryCategory
from application.prompt_builder import build_system_prompt
from application.tool_parser import (
    parse_tool_calls,
    execute_tool_calls,
    filter_stream_tool_tags,
    strip_tool_tags,
)
from application.memory_manager import MemoryManager
from application.conversation import ConversationHistory, ConversationStore, ConversationTurn
from application.learning import FeedbackEvaluator, LearnedRuleStore
from application.intent_router import IntentClassifier, IntentType, LLMIntentClassifier
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Casual greetings that never contain learnable rules
_SKIP_FEEDBACK = {
    "hi", "hello", "hey", "sup", "howdy", "greetings",
    "good morning", "good afternoon", "good evening", "good night",
    "thanks", "thank you", "ok", "okay", "cool", "bye", "goodbye",
    "yes", "no", "yep", "nope", "sure", "fine",
}


class Orchestrator:
    """Luca's brain — coordinates all subsystems via injected dependencies.

    Replaces the old monolithic Controller with clean separation of concerns.
    """

    def __init__(
        self,
        *,
        ai_provider: AIProvider | None,
        memory: MemoryManager,
        tool_registry: ToolRegistry,
        assistant_name: str = "Luca",
        user_title: str = "Boss",
        personality: str = "friendly, helpful, concise",
        max_response_tokens: int = 256,
    ) -> None:
        self._ai = ai_provider
        self._memory = memory
        self._tools = tool_registry
        self._assistant_name = assistant_name
        self._user_title = user_title
        self._personality = personality
        self._max_tokens = max_response_tokens

        # Subsystems
        self._state = AppState.INITIALIZING
        self._history = ConversationHistory(max_turns=10)
        self._conversation_store: ConversationStore | None = None
        self._intent_classifier = IntentClassifier()
        self._llm_intent_classifier: LLMIntentClassifier | None = None
        self._feedback_evaluator: FeedbackEvaluator | None = None
        self._learned_rules: LearnedRuleStore | None = None

    # ── Properties ────────────────────────────────────────────────────

    @property
    def state(self) -> AppState:
        return self._state

    @property
    def assistant_name(self) -> str:
        return self._assistant_name

    @property
    def user_title(self) -> str:
        return self._user_title

    # ── Lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialize all subsystems."""
        logger.info("Starting %s …", self._assistant_name)

        self._memory.initialize()

        self._conversation_store = ConversationStore(
            self._memory,
            retention_days=30,
        )
        self._learned_rules = LearnedRuleStore(self._memory)

        if self._ai and self._ai.is_available():
            self._feedback_evaluator = FeedbackEvaluator(self._ai)
            self._llm_intent_classifier = LLMIntentClassifier(
                self._ai, self._intent_classifier
            )
            logger.info("AI provider connected: %s", self._ai.model_name)
        else:
            logger.warning("AI provider not available — LLM features disabled")

        self._conversation_store.purge_old_conversations()
        self._state = AppState.STANDBY
        logger.info("Hello, %s. %s is ready.", self._user_title, self._assistant_name)

    def shutdown(self) -> None:
        """Clean shutdown."""
        self._state = AppState.SHUTTING_DOWN
        self._memory.close()
        logger.info("%s shut down.", self._assistant_name)

    # ── Main streaming entry point ────────────────────────────────────

    def chat_stream(self, user_input: str) -> Iterator[str]:
        """Stream a response token-by-token, then execute any tool calls.

        This is the primary entry point for the interactive loop.
        STRICT LATENCY RULE: Normal questions go straight to the LLM.
        """
        stripped = user_input.strip()
        if not stripped:
            return

        # Intent classification (use LLM fallback if available)
        classifier = self._llm_intent_classifier if getattr(self, "_llm_intent_classifier", None) else self._intent_classifier
        intent_result = classifier.classify(stripped)

        # Status is handled locally — no LLM needed
        if intent_result.intent == IntentType.STATUS:
            yield self._handle_status()
            return

        # Everything else needs the LLM
        if self._ai is None or not self._ai.is_available():
            yield (f"[{self._assistant_name}] I don't have an LLM connected. "
                   "Please make sure Ollama is running.")
            return

        is_feedback = (intent_result.intent == IntentType.FEEDBACK)
        self._state = AppState.THINKING

        # Build context
        learned_rules_text = ""
        if self._learned_rules:
            learned_rules_text = self._learned_rules.get_rules_text()

        memory_context = self._get_memory_context(stripped)

        # Build system prompt with tool specs (only if action is intended)
        active_tools = self._tools.list_specs() if intent_result.intent == IntentType.ACTION else None
        
        sys_msg = build_system_prompt(
            self._assistant_name,
            self._user_title,
            self._personality,
            learned_rules=learned_rules_text,
            memory_context=memory_context,
            tool_specs=active_tools,
        )

        # Assemble message list
        messages: list[Message] = [Message("system", sys_msg)]
        messages.extend(self._history.to_messages())
        messages.append(Message("user", stripped))

        # Stream LLM response
        chunks: list[str] = []

        def token_collector() -> Iterator[str]:
            for token in self._ai.stream(messages, max_tokens=self._max_tokens):
                chunks.append(token)
                yield token

        try:
            for clean_token in filter_stream_tool_tags(token_collector()):
                yield clean_token
        except Exception as exc:
            logger.error("LLM stream error: %s", exc)
            self._state = AppState.ERROR
            yield f"[{self._assistant_name}] Sorry, something went wrong: {exc}"
            return

        self._state = AppState.STANDBY
        reply = "".join(chunks)

        # Parse and execute tool calls
        tool_calls = parse_tool_calls(reply)
        if tool_calls:
            self._state = AppState.WORKING
            for status_msg in execute_tool_calls(tool_calls, self._tools):
                yield status_msg
            self._state = AppState.STANDBY

        # Keep tool tags in the history so the LLM retains few-shot context of how to use tools
        history_reply = reply
        importance = 0.7 if is_feedback else 0.3
        turn = self._history.add(stripped, history_reply, importance=importance)

        # Background learning (non-blocking)
        self._evaluate_and_learn_async(stripped, reply, turn, is_feedback=is_feedback)

    # ── Status handler ────────────────────────────────────────────────

    def _handle_status(self) -> str:
        ai_status = "connected" if (self._ai and self._ai.is_available()) else "disconnected"
        ai_model = self._ai.model_name if self._ai else "none"
        rule_count = len(self._learned_rules.get_all_rules()) if self._learned_rules else 0
        return (
            f"[{self._assistant_name} Status]\n"
            f"  State         : {self._state.value}\n"
            f"  Owner         : {self._user_title}\n"
            f"  AI Provider   : {ai_status} ({ai_model})\n"
            f"  Learned rules : {rule_count}\n"
            f"  History turns : {len(self._history)}\n"
            f"  Tools         : {len(self._tools)} registered"
        )

    # ── Memory context retrieval ──────────────────────────────────────

    def _get_memory_context(self, query: str) -> str:
        if not query.strip():
            return ""
        items = self._memory.recall(query, limit=5)
        relevant = [
            item for item in items
            if item.category in (
                MemoryCategory.USER, MemoryCategory.PREFERENCE,
                MemoryCategory.FEEDBACK, MemoryCategory.PROJECT,
                MemoryCategory.LEARNED_RULE,
            )
        ]
        if not relevant:
            return ""
        return "\n".join(f"- {item.content}" for item in relevant[:5])

    # ── Background learning ───────────────────────────────────────────

    def _evaluate_and_learn_async(
        self, user_input: str, reply: str,
        turn: ConversationTurn, *, is_feedback: bool = False,
    ) -> None:
        """Run feedback evaluation in a background thread (zero user delay)."""
        if not is_feedback:
            if self._conversation_store:
                self._conversation_store.save_if_important(turn)
            return

        thread = threading.Thread(
            target=self._evaluate_and_learn,
            args=(user_input, reply, turn),
            daemon=True,
            name="feedback-evaluator",
        )
        thread.start()

    def _evaluate_and_learn(
        self, user_input: str, reply: str, turn: ConversationTurn,
    ) -> None:
        if not self._feedback_evaluator or not self._learned_rules:
            return
        try:
            result = self._feedback_evaluator.evaluate(user_input, reply)
            if result.has_feedback:
                saved_id = self._learned_rules.save_rule(result)
                if saved_id:
                    logger.info("Self-improvement: learned '%s'", result.rule_text)
                    turn.importance = max(turn.importance, 0.8)
        except Exception as exc:
            logger.debug("Feedback evaluation error (non-fatal): %s", exc)

        if self._conversation_store:
            self._conversation_store.save_if_important(turn)
