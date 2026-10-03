# Luca Git Workflow

## Branches

Only two primary long-lived branches:

```text
main
testing
```

## Meaning

`main`:
- stable
- user-approved
- should remain usable

`testing`:
- all development
- features
- fixes
- experiments
- refactors
- provider changes
- UI work

## Normal workflow

```text
Boss request
    |
testing
    |
implement
    |
test
    |
review diff
    |
commit
    |
push testing
```

## Promotion

Never promote automatically.

Only after Boss explicitly says something equivalent to:
- "Promote testing to main"
- "Merge this into main"
- "Update main with the tested changes"

Then:

```text
testing
  |
final tests
  |
merge
  |
main
```

## GitHub Desktop

GitHub Desktop may be used as the primary visual Git interface.

Useful operations:
- inspect changed files
- review diffs
- commit
- switch branches
- push
- pull
- inspect history
- create/inspect branches

## Commands for recovery

Check status:

```powershell
git status
```

Check branches:

```powershell
git branch
```

Check history:

```powershell
git log --oneline --decorate --graph --all
```

## Remote

Recommended remote:
private GitHub repository.

## No separate copies

Do not create:
- Luca-GPT
- Luca-Claude
- Luca-Gemini
- Luca-final
- Luca-final-2

Use only:

```text
D:/PA/luca/
```

## Commit guidance

Use meaningful commits, for example:

```text
feat: add local memory store
feat: add owner speaker verification
fix: validate shell tool arguments
refactor: separate planner from controller
test: add permission manager tests
docs: update architecture
```

## Checkpoint commits

Long tasks should create useful checkpoints on `testing`.

This protects work if an AI session stops or reaches a usage limit.

## Never

- force-push main without explicit authorization
- delete history casually
- commit secrets
- commit personal memory databases
- commit voice profiles
- push `.env`
- promote to main without Boss approval
