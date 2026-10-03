# Antigravity Bootstrap Prompt — Luca

Copy the prompt below into the Antigravity agent after opening:

```text
D:/PA/luca/
```

---

You are the primary development agent for a long-term Windows desktop AI assistant project named **Luca**.

The repository is located at:

D:/PA/luca/

Your job is to convert this folder into a properly structured, maintainable software project and then develop Luca incrementally.

IMPORTANT: Do not treat this as a throwaway prototype. This is a long-term project shared by multiple AI coding agents.

## FIRST: READ THE REPOSITORY DOCUMENTS

Before changing code, read:

- AGENTS.md
- assistant-master-requirements.md
- ARCHITECTURE.md
- DEVELOPMENT.md
- GIT_WORKFLOW.md
- CI_CD.md
- SECURITY.md
- AI_HANDOFF.md
- DEVELOPMENT_STATE.md
- CHANGELOG.md

These documents are authoritative.

## CURRENT USER/ASSISTANT IDENTITY

Assistant name: Luca

Address the user as: Boss

These are configurable identity values. Do not hard-code them throughout the application.

## IMPORTANT GIT RULE

There are exactly two primary long-lived branches:

main
testing

ALL development must occur on testing.

Never merge/promote testing to main unless Boss explicitly tells you to do so.

Passing tests do not authorize promotion.

## CANONICAL REPOSITORY

Use only:

D:/PA/luca/

Do not create alternate copies such as Luca-Gemini, Luca-Codex, Luca-Claude, or Luca-final.

Other AI agents may work on this same repository:
- Codex CLI / Astra
- Claude Code
- Gemini/Antigravity
- ChatGPT
- future agents

Always inspect the current repository before editing because another agent may have changed it.

## PRODUCT GOAL

Build Luca as a local-first Windows personal AI assistant.

Luca should:
- answer ordinary questions quickly
- understand natural English
- remember useful information
- learn from explicit corrections
- control desktop applications safely
- work with files
- work with projects
- run safe development workflows
- perform multi-step tasks
- use the internet only when needed/permitted
- communicate primarily through voice
- recognize the owner's voice
- have a cute, childlike, expressive desktop character
- remain lightweight on an approximately 8 GB RAM Ryzen-class Windows laptop

## VERY IMPORTANT: TWO EXECUTION PATHS

Do not make every interaction go through the full agent pipeline.

FAST PATH:
ordinary questions/conversation
-> relevant memory/context
-> local LLM
-> quick/streamed answer

TASK PATH:
action/multi-step request
-> understand
-> retrieve memory
-> plan
-> permission
-> validated tools
-> execute
-> observe
-> replan if necessary
-> respond

Luca should feel fast when Boss simply asks questions.

## LOCAL-FIRST

Start with:
- Python
- Ollama
- small quantized local LLM
- SQLite
- local voice components where practical

Use abstractions so these can be replaced later.

## PROVIDER ABSTRACTIONS

Create replaceable interfaces for:
- LLM
- memory
- STT
- TTS
- wake word
- speaker verification

Do not spread Ollama-specific code throughout the application.

## DATABASE

Use SQLite initially.

Access it through a MemoryStore/MemoryManager abstraction.

Do not make the rest of Luca depend directly on SQLite.

Future database replacement must be possible without rewriting the assistant.

## MEMORY

Support:
- user memory
- assistant identity
- preferences
- project memory
- feedback/learned behavior
- task history
- conversation context

Retrieve only relevant memory.

Do not permanently retain every raw conversation by default.

## LEARNING

If Boss says:

"Don't do that again."

or gives a clear behavioral correction, Luca should be able to extract a durable preference/rule.

Do not retrain the base model after every correction.

Use persistent behavior/preferences first.

## OWNER-ONLY VOICE

This is a core requirement.

Luca must only execute actionable voice commands from the enrolled owner's voice.

Wake detection is not speaker authentication.

Runtime flow:

microphone
-> wake detection
-> speaker verification
-> speech recognition
-> intent
-> action

Unknown/rejected speakers must not execute commands.

Voice profiles/biometric data remain local by default.

High-risk commands still require explicit confirmation.

## VOICE

TTS must be replaceable.

Boss should eventually be able to choose the Luca voice and adjust practical voice settings.

## CHARACTER UI

Luca should appear as a small cute, childlike, expressive desktop companion.

The character should react to controller states:

STANDBY
LISTENING
THINKING
WORKING
SPEAKING
SUCCESS
ERROR
WARNING
PERMISSION_REQUIRED
SLEEPING

It can:
- blink
- change expressions
- move
- walk
- sit
- sleep
- speak with mouth animation
- show small speech bubbles
- show concise task progress

Keep it lightweight.

The character is presentation only; Luca's brain must work without it.

## SAFETY

Never execute raw LLM output directly.

Use:

planner
-> validator
-> permission manager
-> tool router
-> tool

Risk categories:
- low
- medium
- high

High-risk destructive operations require explicit confirmation or blocking.

## TOOLS

Create modular tools for:
- applications
- files
- Windows
- shell
- projects
- browser/internet

Prefer APIs/CLI/PowerShell/Python/official application interfaces over coordinate-based automation.

## ARCHITECTURE

Keep code modular.

Do not create one giant Python file.

Follow the architecture described in ARCHITECTURE.md.

## PHASE 0 TASK

Your first job is NOT to build the whole assistant at once.

Perform the foundation setup:

1. Inspect the existing D:/PA/luca/ folder.
2. Check whether Git is already initialized.
3. Preserve existing user files unless they conflict with the project setup.
4. Create/verify the required project documentation.
5. Create the modular source directory structure.
6. Create configuration structure.
7. Create tests structure.
8. Create scripts structure.
9. Create `.gitignore`.
10. Create `.env.example`.
11. Create a Python virtual environment if appropriate.
12. Add an initial dependency strategy without unnecessarily installing huge packages.
13. Create a minimal startup skeleton.
14. Create a minimal configuration/identity loader.
15. Create basic tests for configuration/identity.
16. Ensure the project can start without the full AI/voice/GUI stack installed.
17. Update DEVELOPMENT_STATE.md.
18. Update CHANGELOG.md.
19. Run validation.

## DO NOT DO YET

Do not prematurely implement:
- advanced voice biometrics
- browser automation
- autonomous destructive actions
- large local models
- cloud databases
- complex animated character system
- Windows packaging
- automatic main promotion

Build those later in phases.

## IMPORTANT RESOURCE RULE

The target machine is approximately 8 GB RAM.

Avoid unnecessary dependencies and heavy always-running services.

Use lazy loading.

## IF SOMETHING IS AMBIGUOUS

Prefer the existing master requirements and architecture.

Do not silently invent a conflicting architecture.

If a major decision is genuinely required, document it and tell Boss.

## WHEN YOU FINISH PHASE 0

Report:

1. Repository structure created
2. Git branch detected/created
3. Current branch
4. Files created/changed
5. Tests run
6. Test results
7. Dependencies added
8. Any unresolved issue
9. Recommended next phase

Do not merge to main.

Do not claim the project is production-ready.

The project should remain on testing.

START BY INSPECTING THE CURRENT REPOSITORY. Do not blindly overwrite existing files.
```
