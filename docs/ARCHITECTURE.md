# Luca Architecture

## 1. High-level architecture

```text
Boss
  |
Voice/Text Input
  |
Wake Detection
  |
Speaker Verification
  |
Speech-to-Text
  |
Assistant Controller
  |
  +-- Identity
  +-- Memory
  +-- Learning/Feedback
  |
Intent Router
  |
  +---------------------------+
  |                           |
FAST CONVERSATION PATH       ACTION/TASK PATH
  |                           |
Local LLM                  Planner
  |                           |
Fast response              Permission/Safety
                              |
                          Tool Router
                              |
                +-------------+-------------+
                |       |       |          |
             Windows  Files   Shell     Projects
                              |
                           Browser
                              |
                           Observe
                              |
                         Replan/Result
                              |
                         Final response
                              |
                    TTS + Luca Character
```

## 2. Core modules (layered OOP architecture)

```text
D:\PA\luca\
├── main.py                          Entry point (--check / interactive loop)
├── identity.yaml                    Configurable assistant/user identity
├── requirements.txt                 Dependencies
├── core/                            Domain entities & interfaces
│   ├── interfaces.py                ABCs: AIProvider, MemoryStore, Tool, etc.
│   └── exceptions.py               Domain exceptions
├── infrastructure/                  Concrete implementations
│   ├── ollama_provider.py           Ollama HTTP transport
│   └── sqlite_memory.py            SQLite memory backend
├── tools/                           Extensible tool system
│   ├── registry.py                  ToolRegistry (discovery & lookup)
│   └── system_tools.py             ShellTool, OpenAppTool, CloseAppTool,
│                                    TypeKeysTool, PressKeyTool, WaitTool,
│                                    SearchWebTool (Win32 SendInput for keyboard)
├── application/                     Use cases & orchestration
│   ├── orchestrator.py              Central coordinator (wires subsystems)
│   ├── prompt_builder.py            System prompt construction
│   ├── tool_parser.py               Parse <tool>JSON</tool> & stream filtering
│   ├── intent_router.py             Keyword + LLM intent classification
│   ├── conversation.py              Rolling buffer + persistent store
│   ├── memory_manager.py            Memory facade over MemoryStore
│   └── learning.py                  Feedback evaluator + learned rules
├── app/                             Dependency injection
│   └── bootstrap.py                 Configuration + composition root
├── security/                        Safety pipeline (risk classification)
├── tests/                           Test suite
│   ├── test_phase0.py               Foundation tests (18 tests)
│   └── test_phase1.py               Conversation/intent/learning tests (46 tests)
├── scripts/                         PowerShell dev scripts
├── docs/                            Project documentation
├── user_data/                       SQLite DB, user preferences (gitignored)
├── models/                          Local model files (gitignored)
└── logs/                            Runtime logs (gitignored)
```



## 3. Replaceable providers

Use interfaces such as:

```python
class LLMProvider:
    def generate(self, messages, tools=None):
        ...

class MemoryStore:
    def save(self, item):
        ...

    def search(self, query):
        ...

class STTProvider:
    def transcribe(self, audio):
        ...

class TTSProvider:
    def speak(self, text, voice=None):
        ...

class SpeakerIdentityProvider:
    def verify(self, audio):
        ...
```

## 4. Identity

Store configurable values:
- assistant name
- user title
- wake name
- personality settings
- voice selection

Current:
- Luca
- Boss

## 5. Controller state

The controller emits state events to the UI.

Example:

```text
TASK_STARTED
LISTENING
THINKING
WORKING
TASK_PROGRESS
SPEAKING
SUCCESS
ERROR
WARNING
SLEEPING
```

The character UI maps these states to animations.

## 6. Fast path

Ordinary questions:

```text
Input
-> intent classification
-> relevant memory
-> LLM
-> streaming response
```

Do not invoke the full tool planner unless necessary.

## 7. Action path

Actions:

```text
Input
-> intent
-> memory
-> plan
-> permission
-> validated tool
-> execution
-> observation
-> replan
-> response
```

## 8. Memory boundary

The controller interacts with `MemoryManager`, not raw SQL.

This permits SQLite to be replaced later.

## 9. Security boundary

The LLM cannot directly execute OS commands.

Every action goes through:

```text
Planner
-> Validator
-> Permission Manager
-> Tool Router
-> Tool
```

## 10. Data separation

Application code:
Git/GitHub

Personal data:
local `user_data/`

Models:
local `models/`

Secrets:
`.env`

Logs:
local `logs/`

## 11. Persistence

Updating application code must not delete user memory.

Database migrations must be versioned.

## 12. UI

The character is presentation-only.

The brain must work even if the character UI is disabled.

The UI receives state/progress events.

## 13. Offline

Core functions should operate without internet:
- conversation using local LLM
- memory
- local file tools
- Windows tools
- local voice where supported

Internet-dependent features fail gracefully when offline.
