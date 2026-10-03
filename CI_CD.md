# Luca CI/CD and Local Delivery

Luca is a local Windows application, not primarily a cloud website.

## CI meaning

CI validates changes before they are considered complete.

Recommended checks:

```text
format/lint
type checks
unit tests
integration tests
safety tests
memory tests
provider tests
startup/import test
```

## Suggested scripts

```text
scripts/
├── check.ps1
├── test.ps1
├── build.ps1
└── release.ps1
```

## `check.ps1`

Should eventually run:
- formatting/lint
- type checks
- tests

## `test.ps1`

Should run the test suite.

## Build

Future release pipeline:

```text
testing
  |
tests
  |
build Luca.exe
  |
version
  |
package
  |
backup current user data
  |
install/update
```

## Rollback

Application updates must not delete:

```text
user_data/
```

If an application version fails:
- restore previous application version
- preserve user data
- preserve database
- inspect logs

## Database migrations

Schema changes must have migrations/versioning.

Never silently destroy an existing database during an update.

## CI safety

A passing test suite does NOT authorize promotion to `main`.

Promotion is a user decision.

## Local vs GitHub

Source code/history can be synchronized with GitHub.

Personal data remains local unless an explicitly designed encrypted backup/sync feature is later added.
