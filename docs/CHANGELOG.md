# Luca Changelog

All meaningful project changes are recorded here.

## Unreleased / testing

### Phase 1 — Conversational Pipeline & Self-Improvement (2026-10-04)

**Added:**
- `intent.py` — two-stage intent classifier (fast keyword + LLM fallback)
  - Classifies into: CONVERSATION, ACTION, FEEDBACK, STATUS, META
  - Fast path uses zero-latency regex/keyword matching
  - LLM fallback only for ambiguous messages (confidence < 0.7)
- `conversation.py` — conversation history management
  - Rolling buffer (last 10 turns) for multi-turn context
  - Importance-based persistence (only saves important exchanges)
  - 30-day automatic retention with cleanup on startup
  - Learned rules are PERMANENT and never purged
- `learning.py` — self-reinforcement feedback system
  - FeedbackEvaluator uses LLM to detect preferences/corrections/facts/rules
  - Confidence threshold (0.6) prevents noise
  - LearnedRuleStore persists permanent rules with deduplication
  - Rules injected into every system prompt for personalization
- `controller.py` — added `chat_stream()` for real-time word-by-word streaming
- `main.py` — interactive console now streams responses dynamically
- Response latency optimization:
  - Feedback evaluation decoupled into background daemon thread (zero chat delay)
  - Small-talk and greeting heuristic skips unnecessary second LLM inference pass
  - **Latency Fix:** Background feedback evaluation is now STRICTLY limited to messages explicitly flagged as feedback intent by the fast classifier. This completely eliminates Ollama queue blocking for standard conversations.
  - Conversation `max_tokens` set to 256 for rapid conversational generation
- `tests/test_phase1.py` — added `chat_stream` tests (47 tests passing)

**Changed:**
- `controller.py` — rewritten with full Phase 1 pipeline:
  - Intent classification → memory retrieval → rules injection → history → LLM → feedback → learn
  - Status command shows learned rules count and history turns
- `llm.py` — enhanced system prompt:
  - Owner-only identity (Luca serves ONLY Boss, refuses others)
  - Learned rules and memory context injection
  - Stronger personality enforcement
- `main.py` — updated interactive loop for Phase 1
- `docs/ARCHITECTURE.md` — updated module tree to match flat structure
- `docs/DEVELOPMENT_STATE.md` — Phase 1 state tracking
- `docs/CHANGELOG.md` — Phase 1 entries

### Phase 0 — Foundation (2026-10-03)

**Added:**
- Flat project structure — all source at root, docs in `docs/`
- `config.py` — centralised settings (identity, LLM, memory, voice, safety, UI, internet)
- `identity.yaml` — configurable assistant name / user title (no hard-coded values)
- `state.py` — thread-safe observable state machine with listener pattern
- `memory.py` — abstract MemoryStore + SQLite backend + MemoryManager façade
- `llm.py` — abstract LLMProvider + OllamaProvider (stdlib only) + prompt templates
- `safety.py` — risk classification + dangerous-pattern validator + permission manager
- `tools.py` — abstract Tool base + ToolRegistry
- `controller.py` — central orchestrator with startup/shutdown lifecycle + fast chat path
- `main.py` — entry point with `--check` health check and interactive text mode
- `tests/test_phase0.py` — 33 tests covering all Phase 0 components
- `scripts/` — PowerShell check, test, build, release scripts
- `.gitignore` — protects secrets, user data, models, logs
- `.env.example` — documented environment variable template
- `requirements.txt` — minimal (pytest only; core uses stdlib)
- Git repository with `main` and `testing` branches

**Changed:**
- Moved all documentation from root to `docs/` folder
- Updated `AGENTS.md` doc references to use `docs/` paths
- Updated `README.md` with new structure and quick-start guide

No production/stable release exists yet.
