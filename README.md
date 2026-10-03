# Luca — Personal Desktop AI Assistant

Luca is a local-first Windows personal AI assistant designed to understand natural language, answer questions quickly, and safely perform multi-step desktop tasks.

## Current identity

- Assistant name: **Luca**
- User address: **Boss**
- Both are configurable via `identity.yaml` — no code changes needed.

## Quick start

```powershell
# Run the health check
python main.py --check

# Start Luca in interactive text mode
python main.py

# Run tests
python -m pytest tests/ -v
```

## Project structure

```
D:\PA\luca\
├── main.py           Entry point
├── config.py         All configuration
├── controller.py     Central orchestrator
├── state.py          Application state machine
├── memory.py         Memory system (abstraction + SQLite)
├── llm.py            LLM providers (abstraction + Ollama)
├── safety.py         Risk classification + permissions
├── tools.py          Tool abstraction + registry
├── identity.yaml     Configurable assistant identity
├── requirements.txt  Dependencies
├── .env.example      Environment variable template
├── .gitignore        Git ignore rules
├── AGENTS.md         AI agent development rules
├── README.md         This file
├── docs/             All project documentation
├── tests/            Test suite
└── scripts/          PowerShell dev scripts
```

## Branch policy

- `main` — stable and explicitly approved
- `testing` — all development

**Never promote `testing` to `main` without explicit Boss approval.**

## Documentation

All project docs live in `docs/`:
- `assistant-master-requirements.md` — product requirements
- `ARCHITECTURE.md` — architecture
- `DEVELOPMENT.md` — development guide
- `DEVELOPMENT_STATE.md` — current work state
- `CHANGELOG.md` — change history
- See `docs/` for the full list.

Read the relevant documents before modifying the project.
