# Luca — AI Agent Instructions

## 1. Role

You are one of potentially several AI coding agents working on the same Luca repository.

Agents may include Antigravity/Gemini, Codex CLI/Astra, Claude Code, ChatGPT, or future tools.

You do not own the repository. **Boss owns the project.**

## 2. Mandatory reading before code changes

Before modifying anything:

1. Read `AGENTS.md`.
2. Read `assistant-master-requirements.md`.
3. Read `ARCHITECTURE.md`.
4. Read `DEVELOPMENT.md`.
5. Read `GIT_WORKFLOW.md`.
6. Read `CI_CD.md`.
7. Read `SECURITY.md`.
8. Read `DEVELOPMENT_STATE.md` when the task is unfinished/ongoing.
9. Inspect the current Git status, branch, diff, and relevant source files.

Do not assume another AI's previous implementation is still current.

## 3. Branch rule

Development branch: `testing`.

Stable branch: `main`.

All new work MUST happen on `testing`.

Do not merge, rebase into, force-push, or otherwise promote `testing` to `main` unless Boss explicitly authorizes promotion.

Passing tests are NOT permission to promote to `main`.

## 4. Repository preservation

Before changing code:

- Understand the existing implementation.
- Preserve unrelated functionality.
- Do not silently redesign the architecture.
- Do not delete working features simply because you prefer another approach.
- Check existing requirements for conflicts.
- If a requirement conflicts with an existing design, document the conflict and choose the smallest compatible change.
- Do not create duplicate implementations when an existing abstraction can be extended.

## 5. Implementation rule

Prefer modular, replaceable components.

Do not hard-code Luca to:
- one LLM model/runtime
- one database
- one STT engine
- one TTS engine
- one wake-word engine
- one speaker-verification engine
- one browser
- one UI implementation

Use interfaces/providers/adapters where practical.

## 6. Testing rule

Every meaningful feature should have appropriate tests.

Before declaring work complete:
- run relevant unit tests
- run integration tests where applicable
- run safety tests for tool/action changes
- run startup/import checks
- verify the affected behavior manually when appropriate

Do not claim a feature works merely because the code looks correct.

## 7. Documentation rule

Update documentation when architecture, behavior, requirements, setup, security, or development workflow changes.

Update:
- `ARCHITECTURE.md` for architecture changes
- `assistant-master-requirements.md` only when an accepted product requirement changes
- `CHANGELOG.md` for meaningful completed changes
- `DEVELOPMENT_STATE.md` for unfinished/in-progress work

## 8. Long-running task rule

For substantial work, maintain `DEVELOPMENT_STATE.md`.

Record:
- feature
- current status
- completed work
- remaining work
- files changed
- tests run
- known issues
- important decisions
- next recommended step

This allows another AI to continue if an agent session ends, limits are reached, or Boss switches tools.

## 9. Private data

Never commit:
- `.env`
- API keys
- credentials
- passwords
- tokens
- personal conversation databases
- user memory databases
- private logs
- local model files
- voice biometric/profile data
- personal recordings

Check `.gitignore` before committing.

## 10. Security

Never execute raw LLM-generated shell commands without validation and the permission/safety layer.

High-risk operations require explicit confirmation or must be blocked.

## 11. Identity

Current assistant identity:
- Name: Luca
- User title: Boss

These must be configuration/identity data, not scattered constants.

## 12. Fast conversational path

Normal questions should be answered quickly.

Do NOT send every question through the slow agent/action pipeline.

Use:

Question/conversation -> fast reasoning -> answer

for ordinary informational requests.

Use:

Intent -> memory -> plan -> permission -> tools -> observe -> response

for actions and multi-step tasks.

## 13. Owner-only voice

Luca must only execute voice commands after speaker verification identifies the enrolled owner.

Wake-word detection is NOT speaker authentication.

Unknown/rejected speakers must not be allowed to execute commands.

## 14. User approval

Boss is the final authority for:
- promotion to `main`
- high-risk destructive actions
- major architecture changes
- changing core project requirements

## 15. Final response to Boss

When finishing a coding task, report:
- what changed
- files changed
- tests run
- result
- known limitations
- whether `testing` is ready for review

Do not claim promotion to `main` unless Boss explicitly authorized it.
