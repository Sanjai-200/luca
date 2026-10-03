# Luca — Personal Desktop AI Assistant

Luca is a local-first Windows personal AI assistant designed to understand natural language, answer questions quickly, and safely perform multi-step desktop tasks.

## Current identity

- Assistant name: **Luca**
- User address: **Boss**
- Both are configurable and must not be hard-coded throughout the codebase.
- The user may rename Luca or change the form of address later.

## Development environment

Primary IDE/agent environment: **Antigravity**

Primary local repository:

```text
D:/PA/luca/
```

Other development agents may include:
- Codex CLI / Astra
- Claude Code
- Gemini/Antigravity agents
- ChatGPT or other coding agents in the future

All agents work on the same canonical repository. No duplicate local copies should be created.

## Branch policy

Exactly two primary long-lived branches:

- `main` — stable and explicitly approved
- `testing` — all development

Every feature, fix, refactor, experiment, model/provider change, UI change, and documentation-affecting implementation starts on `testing`.

**Never promote `testing` to `main` without explicit user approval.**

## Repository truth

The repository is the engineering source of truth:

- `AGENTS.md` — universal AI development rules
- `assistant-master-requirements.md` — complete product requirements
- `ARCHITECTURE.md` — current architecture
- `DEVELOPMENT.md` — implementation strategy
- `GIT_WORKFLOW.md` — Git workflow
- `CI_CD.md` — validation/build/release workflow
- `AI_HANDOFF.md` — handoff between coding agents
- `SECURITY.md` — security and privacy rules
- `DEVELOPMENT_STATE.md` — current unfinished work

Read the relevant documents before modifying the project.
