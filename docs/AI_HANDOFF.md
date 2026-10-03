# Luca AI Agent Handoff

This file exists so one AI can continue work performed by another.

## Canonical repository

```text
D:/PA/luca/
```

## Primary branch

```text
testing
```

## Stable branch

```text
main
```

## Current assistant identity

Luca

## User title

Boss

## Current work

See `DEVELOPMENT_STATE.md`.

## Before continuing another agent's work

1. Read `AGENTS.md`.
2. Read `assistant-master-requirements.md`.
3. Read `ARCHITECTURE.md`.
4. Read `DEVELOPMENT_STATE.md`.
5. Inspect Git status.
6. Inspect current diff.
7. Inspect relevant tests.
8. Run tests before making assumptions.

## If implementation is incomplete

Do not discard it automatically.

Determine:
- what already works
- what is partially implemented
- what is missing
- whether architecture decisions were made
- whether tests exist

Continue from the current state.

## Agent session limits

An agent may:
- stop unexpectedly
- reach usage limits
- lose context
- be replaced by another agent

The repository must therefore always be left in a recoverable state.

## Handoff update format

Update `DEVELOPMENT_STATE.md` with:

```text
Feature:
Status:
Completed:
Remaining:
Files:
Tests:
Known issues:
Important decisions:
Next step:
```

## Multi-agent rule

Agents share one repository.

Do not create separate local copies.

Do not overwrite another agent's work without inspecting it.

Do not promote to `main` without Boss approval.
