# API Contracts — Spec: Split State Directory Race Condition

No new public CLI API contracts are introduced by this specification.
The changes are internal (environment variable propagation and state directory
resolution logic) and do not affect any public-facing CLI interfaces.

Existing CLI commands (`agdt-approve-file`, `agdt-request-changes`, etc.) retain
their current signatures. Their behavior is unchanged except for state directory
resolution during active PR review sessions, where the new pinning mechanism
(environment variable and `.agdt/pinned-state-dir.json`) determines the resolved
state directory.

## Observable side effects

- **Pin file**: During an active PR review workflow, a new file
  `.agdt/pinned-state-dir.json` is created at the repository root. This file
  contains the resolved state directory path and is used by `get_state_dir()` to
  ensure all commands resolve to the same directory for the duration of the
  session. The file is cleared on workflow completion or `agdt-clear-workflow`.
- **Race condition elimination**: The split-state race condition that caused
  duplicate state directories is eliminated.
