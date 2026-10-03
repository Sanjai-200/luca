# Luca Changelog

All meaningful project changes are recorded here.

## Unreleased / testing

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
