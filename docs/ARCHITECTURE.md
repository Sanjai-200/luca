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

## 2. Core modules (flat structure at project root)

```text
D:\PA\luca\
├── main.py              Entry point (--check / interactive loop)
├── config.py            All settings, identity loader, sub-configs
├── controller.py        Central orchestrator — wires everything together
├── state.py             Thread-safe observable state machine
├── intent.py            Two-stage intent classifier (keyword + LLM fallback)
├── conversation.py      Rolling history buffer + persistent conversation store
├── learning.py          LLM-driven feedback evaluator + permanent learned rules
├── llm.py               LLMProvider ABC + OllamaProvider + prompt templates
├── memory.py            MemoryStore ABC + SQLiteMemoryStore + MemoryManager
├── safety.py            Risk classification + command validation + permissions
├── tools.py             Tool ABC + ToolRegistry
├── identity.yaml        Configurable assistant/user identity
├── requirements.txt     Dependencies (pytest only for core)
├── tests/
│   ├── test_phase0.py   Phase 0 foundation tests (33 tests)
│   └── test_phase1.py   Phase 1 conversation/intent/learning tests (40+ tests)
├── scripts/             PowerShell dev scripts
├── docs/                Project documentation
├── user_data/           SQLite DB, user preferences (gitignored)
├── models/              Local model files (gitignored)
└── logs/                Runtime logs (gitignored)
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
