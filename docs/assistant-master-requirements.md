# Luca — Master Product Requirements

Version: 1.0
Status: Living specification
Owner: Boss

## 1. Product vision

Build Luca as a local-first personal AI assistant for Windows.

Luca is not merely a chatbot. Luca should:
- understand natural English
- reason about intent
- answer questions
- perform desktop actions
- access applications, files, Windows functions, projects, and permitted internet tools
- remember useful information
- learn from explicit corrections
- execute multi-step tasks
- remain lightweight on low-spec hardware
- gradually become a long-term personal assistant

## 2. Hardware target

Primary target:
- Windows laptop
- approximately 8 GB RAM
- Ryzen-class CPU
- approximately 256 GB storage
- no dedicated GPU assumed

Prefer resource-efficient components and approximately 3B–4B parameter Q4-class local models where practical.

Use lazy loading for expensive components.

## 3. Identity

Current assistant:
- Name: Luca
- User title: Boss

Identity must be configurable.

A future request such as changing Luca's name must not require changing core architecture.

## 4. Local-first principle

Luca should work offline for capabilities that can work offline.

Internet must be optional and permission-controlled.

Cloud services must not be mandatory for core local operation.

## 5. Core execution model

The conceptual behavior is:

Understand
-> Think
-> Plan
-> Check Permission
-> Act
-> Observe
-> Respond
-> Remember/Learn when appropriate

## 6. Fast conversation path (STRICT LATENCY RULE)

Normal informational and conversational questions should feel immediate. 
**Speed and low latency are absolute, non-negotiable core requirements.**
Never introduce new features, heavy background processing, or complex prompt chains that block or slow down this fast conversational path. Speed must not be compromised for any future functionality.

Examples:
- explain a concept
- answer a normal question
- discuss a topic
- answer from local knowledge/context

Do not send every question through browser automation, desktop tools, or the full task planner.

Fast path:

Input
-> intent classification
-> relevant memory/context
-> local LLM
-> streamed/fast response

## 7. Action/task path

Requests requiring real-world actions use the slower controlled path:

Input
-> understand intent
-> retrieve relevant memory
-> plan
-> permission/safety
-> tool selection
-> execute
-> observe
-> replan if needed
-> respond

## 8. Natural language

No fixed command grammar.

Equivalent requests should map to the same intent:
- Open Chrome
- Can you open Chrome?
- Start the browser
- I need Chrome
- Launch the browser

## 9. Desktop control

Luca should eventually support:
- open/close applications
- create/read/move/rename/search files
- open folders
- run development projects
- run scripts
- run safe shell commands
- interact with Windows
- open websites
- search the web
- development workflows
- repetitive tasks

Prefer OS APIs, CLI, PowerShell, Python libraries, application interfaces, and official APIs over coordinate-based mouse automation.

Visible mouse/keyboard automation is a fallback when better interfaces are unavailable.

## 10. Multi-step agent

Example:
"Find my chatbot project and start it."

Luca should be able to:
1. infer the project from context/memory
2. locate it
3. inspect its structure
4. identify the technology/start command
5. install dependencies if permitted
6. start it
7. observe output
8. detect errors
9. recover/replan when safe
10. report the result

## 11. Voice-first experience

Primary user interaction should eventually be voice-first.

Required components:
- speech recognition
- natural TTS
- wake-name detection
- standby/listening/working/speaking states
- owner speaker verification
- temporary conversational window after wake
- return to standby after inactivity

Text input may remain available for debugging and accessibility.

## 12. Owner-only voice

Luca must only accept actionable voice commands from the enrolled owner.

Architecture:
- wake-word detection
- speaker verification
- speech recognition
- intent/action handling

Speaker verification must be separate from wake detection.

Requirements:
- owner enrollment
- re-enrollment
- configurable verification threshold
- rejection of unknown speakers
- protection against false acceptance
- graceful handling of false rejection/noisy conditions
- voice profile stays local by default
- high-risk operations still require stronger confirmation

Speaker verification is an access control signal, not an assumption of perfect biometric security.

## 13. Voice selection

TTS must be replaceable.

Provide a configuration/UI mechanism to choose an available voice and tune practical parameters such as:
- voice
- speed
- expression where supported

Changing the TTS provider must not affect Luca's brain, memory, tools, or identity.

## 14. Memory

Start with local SQLite.

Use a `MemoryStore` abstraction so storage can later change.

Memory categories:
- user memory
- assistant identity
- preferences
- project memory
- feedback/learned rules
- task history
- conversation context

Retrieve only relevant memory.

Do not inject the entire database into every prompt.

## 15. Database portability

Initial:
SQLite

Future options:
- PostgreSQL
- cloud database
- encrypted cloud backup
- hybrid local + cloud synchronization

Cloud must not be required for offline operation.

## 16. Conversation retention

Do not retain raw conversation data forever by default.

- Rolling conversation buffer in memory (last 10 turns) for multi-turn conversational context.
- Importance-based database persistence: only exchanges scored as important (importance >= 0.5, e.g. feedback, facts, instructions) are saved to persistent storage. Ordinary chit-chat is not kept in the DB.
- 30-day rolling retention window for saved conversation history, purged automatically on startup.
- Learned rules, preferences, and facts extracted from conversations are PERMANENT — they remain consistent from day one and are never purged by the 30-day cleanup.

## 17. Learning and self-reinforcement feedback

Luca continuously improves and customizes itself for Boss through an autonomous self-reinforcement feedback pipeline:

- Every conversation turn is evaluated by the LLM post-response to detect if it contains actionable feedback (preferences, corrections, facts about Boss, or behavioral rules).
- Autonomous evaluation determines whether to take something as feedback, avoiding rigid keyword-only triggers while maintaining a confidence threshold (>= 0.6) to reject noise.
- Learned rules are persisted permanently with deduplication and injected into future system prompts so Luca's behavior remains consistent and progressively adapts to Boss.
- Exclusivity: Luca is Boss's exclusive personal assistant and must not serve or answer questions for unauthorized other people. Identity enforcement is injected at both system prompt and speaker-verification layers.

Do not retrain the base local LLM after every correction.

First use:
- memory
- explicit preferences
- feedback rules
- success/failure history

Future optional techniques:
- adapters
- fine-tuning
- preference optimization
- reinforcement-learning experiments

## 18. LLM replaceability

Use an `LLMProvider` abstraction.

Initial likely implementation:
- Ollama

Possible future:
- llama.cpp
- another local runtime
- optional cloud provider

Do not hard-code the whole application to Ollama.

## 19. Modular tool system

Potential modules:
- applications
- files
- Windows
- shell
- browser
- projects

The LLM must produce structured tool intent, not unrestricted raw commands.

## 20. Safety

Never blindly execute LLM output.

Risk levels:

Low:
- open application
- inspect folder
- search file
- read permitted information

Medium:
- modify files
- install software/dependencies
- download
- run certain commands

High:
- delete important files
- format storage
- expose credentials
- change security settings
- destructive commands

High-risk operations require explicit confirmation or blocking.

## 21. Cancellation

"Stop" must be interpreted contextually.

It may mean:
- stop speaking
- stop listening
- cancel current task
- pause task

Do not destroy important work because of ambiguous interruption.

## 22. Internet

Internet access is optional.

Use internet when:
- Boss explicitly requests it
- the task clearly requires current external information and policy/permission allows it

Do not automatically use the internet for every question.

## 23. Email

Gmail/online email integration is currently out of scope.

## 24. Chibi desktop character

Luca should have a small cute, childlike, expressive desktop companion.

The UI must remain lightweight and non-disruptive.

States include:
- standby
- listening
- thinking
- working
- speaking
- success
- error/confused
- warning
- permission required
- sleeping
- walking/idle movement

The character may:
- blink
- change facial expressions
- move/walk
- sit
- sleep
- speak with mouth animation
- display small speech bubbles
- show task progress

The character is presentation/UI, not the core brain.

## 25. Task indication

Long-running tasks should expose concise progress:
- current stage
- progress where measurable
- success/failure
- permission request

Avoid dumping raw logs into the character bubble.

Detailed logs can be accessible from a task/status UI.

## 26. Resource management

Keep lightweight core components available.

Load expensive components only when required:
- browser automation
- document processing
- computer vision
- large models

Sleep/standby should reduce resource use.

## 27. Application states

Core states:
- STANDBY
- LISTENING
- THINKING
- WORKING
- SPEAKING
- SLEEPING
- PAUSED
- CANCELLING
- ERROR
- SHUTTING_DOWN

## 28. Project structure

The application should be modular and avoid one huge Python file.

Recommended structure is documented in `ARCHITECTURE.md`.

## 29. Git governance

Exactly two primary long-lived branches:
- `main`
- `testing`

All development goes to `testing`.

Promotion to `main` requires explicit Boss approval.

## 30. Multi-AI development

The same repository may be modified by:
- Antigravity/Gemini
- Codex CLI/Astra
- Claude Code
- ChatGPT
- future AI agents

All agents must follow `AGENTS.md`.

The repository is the engineering source of truth.

## 31. Single canonical local repository

Canonical path for this project:

`D:/PA/luca/`

Do not maintain separate local copies for different AI tools.

All development tools should open the same folder.

## 32. Documentation

Maintain:
- `AGENTS.md`
- `assistant-master-requirements.md`
- `ARCHITECTURE.md`
- `DEVELOPMENT.md`
- `GIT_WORKFLOW.md`
- `CI_CD.md`
- `AI_HANDOFF.md`
- `SECURITY.md`
- `DEVELOPMENT_STATE.md`
- `CHANGELOG.md`
- `README.md`

## 33. Future expansion

Architecture should permit:
- stronger local models
- cloud fallback
- computer vision
- advanced browser control
- coding agent
- repository management
- plugins
- improved memory
- improved voice identity
- advanced learning
- more capable UI
- Windows packaging and updates
