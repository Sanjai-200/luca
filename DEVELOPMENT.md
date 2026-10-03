# Luca Development Guide

## Primary environment

Primary IDE: Antigravity

Canonical repository:

```text
D:/PA/luca/
```

Antigravity should always open this exact folder.

## Other agents

Optional:
- Codex CLI / Astra
- Claude Code
- other coding agents

All must use the same repository.

## Development order

### Phase 0 — Foundation
- Git repository
- `main` and `testing`
- documentation
- configuration
- source skeleton
- tests
- `.gitignore`

### Phase 1 — Core brain
- controller
- identity
- LLM provider interface
- Ollama provider
- text input/output
- fast conversational path

### Phase 2 — Memory
- SQLite
- MemoryStore
- MemoryManager
- retrieval
- preferences
- conversation context

### Phase 3 — Learning
- feedback extraction
- behavioral rules
- preference application
- success/failure history

### Phase 4 — Desktop tools
- application control
- files
- Windows
- projects
- safe shell

### Phase 5 — Agent
- structured tool calls
- planner
- permission manager
- observation
- replanning

### Phase 6 — Voice
- STT
- TTS
- wake word
- speaker verification
- active conversation window

### Phase 7 — UI
- tray
- transparent character
- emotions
- expressions
- progress indicators
- speech bubble
- idle movement

### Phase 8 — Internet
- controlled web search
- browser automation
- current information

### Phase 9 — Packaging
- Windows executable
- startup
- settings
- updates
- rollback

## Feature procedure

When Boss requests a feature:

1. Read requirements.
2. Check architecture.
3. Inspect current implementation.
4. Check `git status`.
5. Confirm branch is `testing`.
6. Identify conflicts.
7. Implement minimally and modularly.
8. Add tests.
9. Run tests.
10. Update documentation.
11. Update `DEVELOPMENT_STATE.md` if unfinished.
12. Update `CHANGELOG.md` when meaningfully complete.
13. Leave work on `testing`.
14. Report results.

## If an agent stops

Do not restart from zero.

Read:
- current Git diff
- `DEVELOPMENT_STATE.md`
- requirements
- architecture
- tests

Determine completed/remaining work and continue.

## If another AI changed files

Treat the current repository as authoritative.

Inspect before editing.

## Coding style

Prefer:
- small modules
- typed interfaces
- dependency injection where useful
- clear error handling
- testable functions
- configuration over hard-coded values
- provider abstractions

Avoid:
- giant files
- hidden global state
- duplicated implementations
- direct SQL everywhere
- raw shell execution from LLM output
- hard-coded personal paths
