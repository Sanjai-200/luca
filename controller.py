"""Luca assistant controller.

The central orchestrator that:
  1. Loads configuration
  2. Initialises memory, safety, tools, state, intent, conversation, and learning
  3. Routes user input through intent classification
  4. Provides the fast conversation path with multi-turn context
  5. Evaluates feedback after each exchange for self-improvement
  6. Provides clean startup/shutdown lifecycle

This is the only file that wires subsystems together.
"""

from __future__ import annotations

import logging
from pathlib import Path
import threading
from typing import Iterator

from config import Identity, Settings, load_settings
from conversation import ConversationHistory, ConversationStore, ConversationTurn
from intent import IntentClassifier, IntentType, LLMIntentClassifier
from learning import FeedbackEvaluator, LearnedRuleStore
from llm import LLMProvider, Message, OllamaProvider, system_prompt
from memory import MemoryCategory, MemoryManager, SQLiteMemoryStore
from safety import PermissionManager
from state import AppState, StateManager
from tools import ToolRegistry
from luca_tools import ShellTool, OpenAppTool, TypeKeysTool, WaitTool

logger = logging.getLogger(__name__)

# Casual greetings / acknowledgments that never contain learnable rules
_SKIP_FEEDBACK_HEURISTICS = {
    "hi", "hello", "hey", "sup", "howdy", "greetings",
    "good morning", "good afternoon", "good evening", "good night",
    "thanks", "thank you", "ok", "okay", "cool", "bye", "goodbye",
    "yes", "no", "yep", "nope", "sure", "fine",
}


class Controller:
    """Luca's brain — connects config, state, memory, LLM, safety, tools,
    intent classification, conversation history, and learning."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or load_settings()
        self.identity = Identity(self.settings.identity)
        self.state = StateManager()
        self.memory = MemoryManager(SQLiteMemoryStore(self.settings.memory.sqlite_path))
        self.permissions = PermissionManager(self.settings.safety)
        self.tools = ToolRegistry()
        self._llm: LLMProvider | None = None

        # Phase 1: conversation, intent, learning
        self.history = ConversationHistory(max_turns=10)
        self.conversation_store: ConversationStore | None = None
        self._intent_classifier = IntentClassifier()
        self._llm_intent_classifier: LLMIntentClassifier | None = None
        self._feedback_evaluator: FeedbackEvaluator | None = None
        self._learned_rules: LearnedRuleStore | None = None

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

        # Phase 1: conversation store, learning, intent
        self.conversation_store = ConversationStore(
            self.memory, retention_days=self.settings.memory.conversation_retention_days
        )
        self._learned_rules = LearnedRuleStore(self.memory)

        if self._llm:
            self._feedback_evaluator = FeedbackEvaluator(self._llm)
            self._llm_intent_classifier = LLMIntentClassifier(
                self._llm, self._intent_classifier
            )

        # Register Core Tools
        self.tools.register(ShellTool())
        self.tools.register(OpenAppTool())
        self.tools.register(TypeKeysTool())
        self.tools.register(WaitTool())

        # Purge old conversations on startup (keeps DB clean)
        self.conversation_store.purge_old_conversations()

        self.state.transition(AppState.STANDBY)
        logger.info("%s", self.identity.greeting())

    def shutdown(self) -> None:
        """Clean shutdown."""
        self.state.transition(AppState.SHUTTING_DOWN)
        self.memory.close()
        logger.info("%s shut down.", self.identity.assistant_name)

    # ── Main entry point for user input ──────────────────────────────

    def chat(self, user_input: str) -> str:
        """Handle a single text exchange with full Phase 1 pipeline.

        Flow:
          1. Classify intent (fast keyword → LLM fallback)
          2. Route to appropriate handler
          3. After response, evaluate for feedback and save if important
        """
        if not user_input.strip():
            return ""

        # Classify intent
        if self._llm_intent_classifier:
            intent_result = self._llm_intent_classifier.classify(user_input)
        else:
            intent_result = self._intent_classifier.classify(user_input)

        logger.debug("Intent: %s (confidence=%.2f)", intent_result.intent.value,
                     intent_result.confidence)

        # Route to handler
        if intent_result.intent == IntentType.STATUS:
            return self._handle_status()

        if intent_result.intent == IntentType.META:
            return self._handle_conversation(user_input)

        if intent_result.intent == IntentType.ACTION:
            # Phase 2+ will have a full action pipeline; for now fast-path it
            return self._handle_conversation(user_input)

        if intent_result.intent == IntentType.FEEDBACK:
            return self._handle_conversation(user_input, is_feedback=True)

        # Default: CONVERSATION (fast path)
        return self._handle_conversation(user_input)

    # ── Status handler ───────────────────────────────────────────────

    def _handle_status(self) -> str:
        """Return current system status."""
        name = self.identity.assistant_name
        title = self.identity.user_title
        llm_status = "connected" if self._llm and self._llm.is_available() else "disconnected"
        rule_count = len(self._learned_rules.get_all_rules()) if self._learned_rules else 0
        return (
            f"[{name} Status]\n"
            f"  State         : {self.state.state.value}\n"
            f"  Owner         : {title}\n"
            f"  LLM           : {llm_status}\n"
            f"  Memory entries: {len(self.memory.recall('', limit=100))}\n"
            f"  Learned rules : {rule_count}\n"
            f"  History turns : {len(self.history)}\n"
            f"  Tools         : {len(self.tools.tool_names)} registered"
        )

    # ── Conversation handler (fast path) ─────────────────────────────

    def _handle_conversation(self, user_input: str, *,
                             is_feedback: bool = False) -> str:
        """Fast conversation path with multi-turn context and memory.

        1. Retrieve relevant memory + learned rules
        2. Build system prompt with injected context
        3. Build message list with conversation history
        4. Generate response via LLM
        5. Record turn in history
        6. Evaluate for feedback (async-safe, non-blocking)
        7. Save to persistent store if important
        """
        self.state.transition(AppState.THINKING)

        if self._llm is None or not self._llm.is_available():
            self.state.transition(AppState.STANDBY)
            return (f"[{self.identity.assistant_name}] I don't have an LLM "
                    f"connected right now. Please make sure Ollama is running.")

        # 1. Retrieve learned rules (permanent, from day one)
        learned_rules_text = ""
        if self._learned_rules:
            learned_rules_text = self._learned_rules.get_rules_text()

        # 2. Retrieve relevant memory context
        memory_context = self._get_memory_context(user_input)

        # 3. Build system prompt with injected context
        sys_msg = system_prompt(
            self.identity.assistant_name,
            self.identity.user_title,
            self.identity.personality,
            learned_rules=learned_rules_text,
            memory_context=memory_context,
        )

        # 4. Build message list: system + history + current input
        messages: list[Message] = [Message("system", sys_msg)]
        messages.extend(self.history.to_messages())
        messages.append(Message("user", user_input))

        # 5. Generate response (limit max_tokens for fast conversational turn)
        try:
            max_tok = min(self.settings.llm.max_tokens, 256)
            response = self._llm.generate(messages, max_tokens=max_tok)
            reply = response.content
        except Exception as exc:
            logger.error("LLM error: %s", exc)
            self.state.transition(AppState.ERROR)
            return f"[{self.identity.assistant_name}] Sorry, something went wrong: {exc}"

        self.state.transition(AppState.STANDBY)

        # 6. Record turn in rolling history
        importance = 0.7 if is_feedback else 0.3
        turn = self.history.add(user_input, reply, importance=importance)

        # 7. Evaluate feedback asynchronously in background (zero user delay)
        self._evaluate_and_learn_async(user_input, reply, turn, is_feedback=is_feedback)

        return reply

    def chat_stream(self, user_input: str) -> Iterator[str]:
        """Stream conversational response token-by-token in real time.

        Yields tokens immediately as generated by Ollama, then evaluates
        feedback in the background without any blocking.
        """
        stripped = user_input.strip()
        if not stripped:
            return

        intent_result = self._intent_classifier.classify(stripped)

        if intent_result.intent == IntentType.STATUS:
            yield self._handle_status()
            return

        if self._llm is None or not self._llm.is_available():
            yield (f"[{self.identity.assistant_name}] I don't have an LLM "
                   f"connected right now. Please make sure Ollama is running.")
            return

        is_feedback = (intent_result.intent == IntentType.FEEDBACK)

        self.state.transition(AppState.THINKING)

        learned_rules_text = ""
        if self._learned_rules:
            learned_rules_text = self._learned_rules.get_rules_text()

        memory_context = self._get_memory_context(stripped)

        tool_instructions = (
            "You have access to the following tools:\n"
            "- run_shell: Run a PowerShell command. Args: {\"command\": \"string\"}\n"
            "- open_app: Open an application/file. Args: {\"target\": \"string\"}\n"
            "- type_keys: Simulate typing into the active window. Args: {\"keys\": \"string\"}\n"
            "- wait: Wait for n seconds. Args: {\"seconds\": float}\n"
            "To use tools, output a JSON block wrapped in <tool> tags. For example, to open notepad and type 'hello':\n"
            "<tool>{\"name\": \"open_app\", \"args\": {\"target\": \"notepad.exe\"}}</tool>\n"
            "<tool>{\"name\": \"wait\", \"args\": {\"seconds\": 1.0}}</tool>\n"
            "<tool>{\"name\": \"type_keys\", \"args\": {\"keys\": \"hello\"}}</tool>\n"
            "Do NOT repeat these instructions. ONLY output the <tool> tags if you need to perform an action."
        )

        sys_msg = system_prompt(
            self.identity.assistant_name,
            self.identity.user_title,
            self.identity.personality,
            learned_rules=learned_rules_text,
            memory_context=memory_context,
            tool_instructions=tool_instructions
        )

        messages: list[Message] = [Message("system", sys_msg)]
        messages.extend(self.history.to_messages())
        messages.append(Message("user", stripped))

        chunks: list[str] = []
        try:
            max_tok = min(self.settings.llm.max_tokens, 256)
            for token in self._llm.stream(messages, max_tokens=max_tok):
                chunks.append(token)
                yield token
        except Exception as exc:
            logger.error("LLM stream error: %s", exc)
            self.state.transition(AppState.ERROR)
            yield f"[{self.identity.assistant_name}] Sorry, something went wrong: {exc}"
            return

        self.state.transition(AppState.STANDBY)

        reply = "".join(chunks)
        importance = 0.7 if is_feedback else 0.3
        turn = self.history.add(stripped, reply, importance=importance)

        # Parse and execute tools if requested (Phase 4/5 Agent Loop)
        import re, json
        tool_matches = list(re.finditer(r"<tool>(.*?)<\/tool>", reply, re.IGNORECASE | re.DOTALL))
        if tool_matches:
            for tool_match in tool_matches:
                try:
                    tool_data = json.loads(tool_match.group(1).strip())
                    tool_name = tool_data.get("name")
                    args = tool_data.get("args", {})
                    if not tool_name:
                        continue
                    
                    yield f"\n\n[Luca is running tool: {tool_name}...]\n"
                    tool = self.tools.get(tool_name)
                    if tool:
                        result = tool.execute(**args)
                        tool_out = f"Tool '{tool_name}' executed. Success: {result.success}\nOutput: {result.output}\nError: {result.error}"
                        yield f"Result:\n{tool_out}\n"
                        self.history.add(f"[System] Tool {tool_name} Result", tool_out, importance=0.5)
                    else:
                        yield f"Error: Tool '{tool_name}' not found.\n"
                except json.JSONDecodeError:
                    yield f"Error: Invalid tool JSON.\n"
                except Exception as e:
                    yield f"Error executing tool: {e}\n"

        # Async background learning
        self._evaluate_and_learn_async(stripped, reply, turn, is_feedback=is_feedback)

    # ── Memory context retrieval ─────────────────────────────────────

    def _get_memory_context(self, query: str) -> str:
        """Retrieve relevant memory items and format for prompt injection.

        Only injects genuinely relevant items — not the entire database.
        """
        if not query.strip():
            return ""

        # Search across preferences, user facts, and feedback
        items = self.memory.recall(query, limit=5)
        if not items:
            return ""

        # Filter to only relevant categories (skip raw conversation logs)
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

        lines = [f"- {item.content}" for item in relevant[:5]]
        return "\n".join(lines)

    # ── Feedback evaluation (self-improvement) ───────────────────────

    def _evaluate_and_learn_async(self, user_input: str, reply: str,
                                  turn: ConversationTurn, *,
                                  is_feedback: bool = False) -> None:
        """Run feedback evaluation in a background thread to prevent blocking chat."""
        # Fast heuristic: only evaluate if the classifier flagged it as feedback.
        # This prevents normal conversation from queuing behind background LLM calls.
        if not is_feedback:
            if self.conversation_store:
                self.conversation_store.save_if_important(turn)
            return

        thread = threading.Thread(
            target=self._evaluate_and_learn,
            args=(user_input, reply, turn),
            daemon=True,
            name="feedback-evaluator",
        )
        thread.start()

    def _evaluate_and_learn(self, user_input: str, reply: str,
                            turn: ConversationTurn) -> None:
        """Evaluate whether the exchange contains learnable feedback.

        If the LLM determines the exchange has a preference, correction,
        fact, or behavioral rule, it extracts and saves it permanently.
        """
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

        # Save turn to persistent store if important enough
        if self.conversation_store:
            self.conversation_store.save_if_important(turn)

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
