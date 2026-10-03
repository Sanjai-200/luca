# Luca Security and Privacy

## Local-first

Private personal data should remain on the machine by default.

## Never commit

- `.env`
- API keys
- passwords
- tokens
- credentials
- personal memory databases
- conversation history
- voice recordings
- speaker biometric/profile data
- private logs
- local model files

## Voice security

Luca must verify the enrolled owner's speaker identity before executing voice commands.

Wake word is not authentication.

Unknown speakers:
- do not execute commands
- remain silent or provide a minimal non-action response depending on policy

High-risk commands require explicit confirmation even after speaker verification.

## LLM security

Never treat model output as trusted executable code.

Tool calls must be:
- structured
- schema validated
- permission checked
- risk classified

## Shell

Do not directly execute arbitrary generated shell commands.

Use allowlisted/safe operations where possible.

For unavoidable shell operations:
- validate arguments
- classify risk
- request confirmation when required
- capture output
- report failures

## File safety

Protect:
- user home
- important project directories
- credentials
- system directories

Deletion should be conservative.

## Internet

External network access is not automatically assumed.

Use only when required/permitted.

## Logging

Logs should avoid:
- credentials
- tokens
- sensitive personal data
- raw voice recordings

## Data retention

Raw conversations and task logs should have configurable retention.

Durable memories should be stored separately.

## UI safety

The character should not impersonate system security dialogs or hide dangerous confirmations.

## Privacy principle

Luca should collect the minimum information needed to perform a requested function.
