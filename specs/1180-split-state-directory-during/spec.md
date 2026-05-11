# Spec: Split state directory during PR review workflow — race condition in bootstrap scope resolution

## Status

Proposed

**Source Issue**: #1180
**Priority**: P0

## Summary

The PR review workflow suffers from a race condition in state directory resolution. When
`agdt-initiate-pull-request-review-workflow` runs, the `setup_pull_request_review()` background
task modifies `runtime-bootstrap.json` to set the worktree key. Concurrent CLI commands
(e.g., `agdt-approve-file`) read this shared file at different times, seeing different
`worktree_key` values. This causes state to split across two directories (e.g.,
`workflows/ama/PR25553/` and `workflows/ama/DFLY-2674/`), leading to missing `review-state.json`,
duplicate comments, and legacy fallback activation.

## Problem Statement

The `get_state_dir()` function resolves the state directory by reading `runtime-bootstrap.json`,
a shared file that any process can modify. During the PR review workflow, the setup background
task calls `set_bootstrap_state()` to update the `worktree_key`, but concurrent Copilot session
commands read the bootstrap file before or after this update, causing inconsistent resolution.

This race condition manifests in two scenarios:

1. **Both `--pull-request-id` and `--issue-key` provided**: The initiate function sets bootstrap
   scope to the issue key, but the setup task re-bootstraps to a different key. Commands issued
   between these two writes see different scopes.
2. **Only `--pull-request-id` from an existing worktree**: The setup task modifies the bootstrap
   file while concurrent commands are already running with the pre-modification scope.

The root cause is architectural: `runtime-bootstrap.json` is a shared mutable resource used for
cross-process communication without synchronization.

## Goals

- Eliminate the race condition in state directory resolution during PR review workflows.
- Ensure all commands within a workflow session use a single, consistent state directory.
- Propagate the resolved state directory to background subprocesses without relying on the shared
  `runtime-bootstrap.json` file.
- Maintain backward compatibility with existing single-worktree workflows.

## Non-goals

- Redesigning the entire state management system.
- Supporting truly concurrent workflows in the same worktree (separate issue).
- Changing the `runtime-bootstrap.json` format for non-review workflows.
- Modifying the Azure DevOps or Jira API integration layers.

## Users and stakeholders

- **AI agents** running PR review workflows via `agdt-initiate-pull-request-review-workflow`
- **Developers** using multi-worktree setups with concurrent review sessions
- **CI pipelines** running automated reviews in `--interactive false` mode

## Clarifications

The following ambiguities were identified during a self-review pass and resolved inline. Answers have been applied to the relevant spec sections.

### C1: Atomic write mechanism for the pin file

**Q:** FR-001 states that the initiate function writes `.agdt/pinned-state-dir.json` "atomically" but does not specify the mechanism. What technique should be used?

**A:** Use the standard **write-to-temp-then-rename** pattern: write the JSON content to a temporary file in the same directory (e.g., `.agdt/.pinned-state-dir.json.tmp`), then call `os.replace()`
(which is atomic on all supported platforms — POSIX guarantees, and Windows guarantees when source and destination are on the same volume, which they always are here). This is consistent with the
existing `_atomic_write_text` helper in `review_state.py` which uses the same temp-file-then-`os.replace()` technique. Applied to FR-001 and edge case #10.

### C2: TTL renewal behavior during long-running reviews

**Q:** FR-003 enforces a `ttl_hours` expiration check, but the spec does not say whether the TTL is renewed when the pin is read or used. A 24-hour review session could have its pin expire mid-review.

**A:** The TTL is **not** renewed on read. It is a fixed window from `created_utc`. However, workflow-progress commands that write to the pin file (specifically `agdt-advance-workflow` and
re-invocations of `agdt-initiate-pull-request-review-workflow`) reset `created_utc` to the current time, effectively renewing the TTL. This ensures that actively progressing reviews do not expire,
while truly abandoned pins are cleaned up. Applied to FR-003, FR-010, and edge case #7.

### C3: Logging level and destination for diagnostic warnings

**Q:** FR-003 and FR-009 require "diagnostic logging" and "diagnostic warning" but do not specify the logging level or destination (stdout, stderr, Python `logging` module, or `print`).

**A:** Diagnostic messages must use **`print(..., file=sys.stderr)`** — consistent with the existing pattern in `get_state_dir()` and other CLI functions in `state.py`. These specific diagnostics
do not use the Python `logging` module (note: other components in the codebase may still use `logging` for their own purposes). Messages should be prefixed with `[agdt]` for grep-ability (e.g.,
`[agdt] Pin file expired (created 2026-05-10T12:00:00Z, TTL 24h), falling back to bootstrap`). Applied to FR-003 and FR-009.

### C4: Behavior when `AGENTIC_DEVTOOLS_STATE_DIR` points to a path outside the repo root

**Q:** FR-003 validates that the pin file's `state_dir` is inside the repo root (directory traversal check), but no such check exists for the `AGENTIC_DEVTOOLS_STATE_DIR` environment variable. Should
the env var be constrained to the repo root?

**A:** **No.** The `AGENTIC_DEVTOOLS_STATE_DIR` environment variable is the highest-priority override and is intentionally unconstrained — it may legitimately point outside the repository (e.g., a
shared CI artifacts directory, a tmpfs mount for testing). The directory traversal check in FR-003 applies **only** to the pin file, which is an auto-generated intermediary and should not escape the
repository boundary. This is consistent with the existing behavior where `AGENTIC_DEVTOOLS_STATE_DIR` is already accepted without path validation. No spec changes needed — the existing text is
correct.

### C5: Pin file cleanup scope for `agdt-clear-workflow`

**Q:** FR-001 says the pin is "cleared when the workflow completes or is explicitly cancelled" and edge case #7 mentions `agdt-clear-workflow`. Does `agdt-clear-workflow` unconditionally delete the
pin file, or only if the active workflow matches?

**A:** `agdt-clear-workflow` must **unconditionally** delete `.agdt/pinned-state-dir.json` if it exists, regardless of the `workflow` field value. Rationale: `agdt-clear-workflow` is a deliberate
reset action; leaving a stale pin after an explicit clear would be surprising and could cause the same split-state issues this spec aims to fix. The workflow completion handler, by contrast, should
only delete the pin if the `workflow` field matches the completing workflow. Applied to FR-001 (added clarifying note).

## User Scenarios & Testing

### US1: Consistent state directory during review initiation

As an AI agent, I want the state directory resolved during workflow initiation to remain
consistent for all commands within the same workflow session — both child processes spawned
by the initiate command (background tasks, Copilot sessions) and independent CLI commands
run afterward in the same terminal — so that `review-state.json` and review artifacts are
always found in the expected location.

**Acceptance criteria**

- Given a PR review workflow is initiated with `--pull-request-id` and `--issue-key`, when
  the setup background task runs and concurrent `agdt-approve-file` commands are issued, then
  all commands resolve to the same state directory.
- Given a PR review workflow is initiated with only `--pull-request-id` from an existing
  worktree, when the setup background task modifies bootstrap state, then concurrent commands
  still resolve to the original state directory.
- Given a PR review session has been active for longer than 12 hours, when
  `agdt-advance-workflow` is run to progress the review, then the pin file's `created_utc`
  is refreshed and subsequent commands continue to resolve the pinned state directory
  without TTL expiration.

### US2: Environment-based state directory propagation

As an AI agent, I want the resolved state directory to be propagated to background
subprocesses via an environment variable so that child processes do not need to re-read the
shared `runtime-bootstrap.json` file.

**Acceptance criteria**

- Given a state directory is resolved during initiation, when a background task is spawned,
  then the task inherits the state directory via an environment variable (e.g.,
  `AGENTIC_DEVTOOLS_STATE_DIR`).
- Given `AGENTIC_DEVTOOLS_STATE_DIR` is set, when `get_state_dir()` is called in a subprocess,
  then it returns the value from the environment variable without reading `runtime-bootstrap.json`.

### US3: No duplicate state directories

As a developer, I want the system to never create duplicate state directories for the same
workflow session so that review artifacts are not scattered across multiple locations.

**Acceptance criteria**

- Given a PR review workflow completes end-to-end, when the state directory is inspected, then
  exactly one directory contains all review artifacts.
- Given the scenario from issue #1180 (Scenario A or B), when reproduced after the fix, then
  zero duplicate directories are created.

### US4: Backward compatibility for single-worktree workflows

As a developer, I want existing single-worktree workflows (non-review) to continue working
without changes so that the fix does not introduce regressions.

**Acceptance criteria**

- Given a non-review workflow (e.g., `work-on-jira-issue`), when `get_state_dir()` is called,
  then the resolution behavior is identical to the current implementation.
- Given `AGENTIC_DEVTOOLS_STATE_DIR` is not set and no valid pin file exists (i.e., no
  `.agdt/pinned-state-dir.json` or the pin fails FR-003 validation), when `get_state_dir()`
  is called, then the existing bootstrap resolution chain
  (`runtime-bootstrap.json` → `.agdt/workflows/{identity}/{worktree_key}/`) is used
  unchanged.

### US5: Concurrent workflow isolation

As a developer running multiple review sessions in separate worktrees, I want each session
to maintain its own isolated state so that one session's state changes do not affect another.

**Acceptance criteria**

- Given two PR review workflows are running in separate worktrees, when both modify their
  respective state directories, then neither session's state is visible to the other.
- Given a worktree-scoped environment variable is set, when commands run in that worktree, then
  they use only the worktree's state directory.

## Requirements

### Functional requirements

#### P1

- **FR-001**: The initiate function must resolve the state directory once at workflow start and
  propagate it via two mechanisms:
  1. **Child processes** (background tasks spawned by `run_in_background()` and auto-started
     Copilot sessions) inherit `AGENTIC_DEVTOOLS_STATE_DIR` as a process environment variable.
  2. **Independent CLI commands** (manual `agdt-*` invocations run after the initiate command
     returns) read the pinned state directory from a repo-root-level file
     (`.agdt/pinned-state-dir.json`) containing:

     ```json
     {
       "state_dir": "<absolute-path>",
       "workflow": "pull-request-review",
       "created_utc": "<ISO-8601 timestamp>",
       "ttl_hours": 24
     }
     ```

     This file resides at a well-known location discoverable by walking up to the repository
     root (the same mechanism used to locate `.agdt/runtime-bootstrap.json`), so
     `get_state_dir()` can read it after the environment variable check but before the
     `runtime-bootstrap.json` fallback — without the circular dependency of reading from the
     scoped `state.json` (which itself requires a resolved state directory to locate). The
     initiate function writes this file atomically using the **write-to-temp-then-rename**
     pattern (`os.replace()` on a temp file in the same directory); it is cleared when the
     workflow completes or is explicitly cancelled. `agdt-clear-workflow` unconditionally
     deletes the pin file if it exists, regardless of the `workflow` field value; the workflow
     completion handler deletes it only if the `workflow` field matches the completing workflow.

  **Scoping and validation rules for the pin file:**

  - `get_state_dir()` **always** reads `.agdt/pinned-state-dir.json` as step 2 in the
    resolution chain (after the environment variable check). It then inspects the `workflow`
    field: the pin is honored **only** if the field matches a recognized review workflow
    name (currently `"pull-request-review"`). If the `workflow` field is absent,
    unrecognized, or does not match the expected pattern, the pin is ignored and resolution
    falls through to the `runtime-bootstrap.json` chain. Crucially, the gating signal is
    the `workflow` field value in the pin file — not the calling command's own identity.
    Any `agdt-*` command will honor a valid pin regardless of whether it is itself a
    "review" command (see "Intentional global pinning" below).
  - **Intentional global pinning**: While a valid pin file exists with
    `workflow: "pull-request-review"`, **all** `agdt-*` commands in the repository —
    including non-review commands like `agdt-set` or `agdt-get-jira-issue` — resolve to
    the pinned state directory. This is by design: during an active PR review session, the
    review is the dominant workflow and all state operations should target the review's
    state directory to prevent the split-state race condition. This is safe because:
    (a) the pin has a TTL (default 24 hours) and is validated on every read (FR-003),
    (b) the pin is explicitly cleared on workflow completion or `agdt-clear-workflow`,
    (c) concurrent non-review workflows in the same worktree are an explicit non-goal.
  - The pin file must pass all validation checks (see FR-003 below) before its `state_dir`
    value is used. Invalid pins are ignored with a diagnostic log warning and resolution
    proceeds to the next step in the chain.
  - Non-review workflows (e.g., `work-on-jira-issue`) are unaffected in practice because
    they are not expected to run concurrently with a PR review in the same worktree (see
    Non-goals). If a user does run a non-review command while a valid pin exists, it will
    use the pinned directory — this is acceptable given the TTL-bounded lifetime and the
    explicit cleanup on workflow completion.

- **FR-002**: `get_state_dir()` must resolve the state directory using the following priority
  chain (stopping at the first successful resolution):
  1. `AGENTIC_DEVTOOLS_STATE_DIR` environment variable — return immediately with no
     pin/bootstrap file reads (bypasses both pin file and `runtime-bootstrap.json`;
     directory creation via `mkdir` is still permitted).
  2. `.agdt/pinned-state-dir.json` — read and validate; use `state_dir` value if valid.
  3. `runtime-bootstrap.json` → `.agdt/workflows/{identity}/{worktree_key}/` (existing chain).
  4. `.agdt/workflows/_unscoped/` fallback.

  When `AGENTIC_DEVTOOLS_STATE_DIR` is set, `get_state_dir()` must bypass **both** the pin
  file and `runtime-bootstrap.json` to preserve the O(1) / no-pin/bootstrap-reads guarantee
  (NFR-001). The environment variable is intentionally unconstrained — it may point outside
  the repository root (e.g., a shared CI artifacts directory or a tmpfs mount for testing).
- **FR-003**: `get_state_dir()` must validate the pin file before using it. The following
  conditions cause the pin to be **ignored** (resolution falls through to bootstrap):
  1. The `state_dir` path does not exist and cannot be created.
  2. The `state_dir` path is outside the repository root (directory traversal safety check).
  3. The `created_utc` timestamp is older than `ttl_hours` (default 24 hours) — the pin has
     expired. The TTL is a fixed window from `created_utc` and is **not** renewed on read.
     However, workflow-progress commands that write to the pin file reset `created_utc` to
     the current time, effectively renewing the TTL for actively progressing reviews (see
     FR-010 for the authoritative list of commands that refresh `created_utc`).
  4. The `workflow` field is absent or does not match a recognized workflow name.
  5. The file cannot be parsed as valid JSON.

  When a pin is ignored due to expiration or validation failure, `get_state_dir()` must emit
  a diagnostic warning to stderr using `print(..., file=sys.stderr)`, prefixed with `[agdt]`
  (e.g., `[agdt] Pin file expired (created 2026-05-10T12:00:00Z, TTL 24h), falling back to
  bootstrap`). The expired/invalid pin file is **not** automatically deleted — cleanup is the
  responsibility of the workflow completion handler or the `agdt-clear-workflow` command.
- **FR-004**: `setup_pull_request_review()` must not call `set_bootstrap_state()` to modify
  `runtime-bootstrap.json` when `AGENTIC_DEVTOOLS_STATE_DIR` is already set in its environment.
- **FR-005**: Background task spawning (via `run_in_background()`) must inherit the parent
  process's `AGENTIC_DEVTOOLS_STATE_DIR` environment variable.
- **FR-006**: When `AGENTIC_DEVTOOLS_STATE_DIR` is set, all state file operations
  (`get_value`, `set_value`, `load_state`, etc.) must use the directory specified by the
  environment variable.
- **FR-010**: Workflow-progress commands must refresh the pin file's `created_utc` timestamp
  to prevent TTL expiration during actively progressing reviews. The following commands
  must reset `created_utc` to the current UTC time when they write to
  `.agdt/pinned-state-dir.json`:
  1. **`agdt-advance-workflow`** — updates `created_utc` each time the workflow step is
     advanced, ensuring long-running multi-step reviews do not expire mid-session.
  2. **`agdt-initiate-pull-request-review-workflow`** (re-invocation) — overwrites the pin
     file with a fresh `created_utc` when a new review session is started in the same
     worktree (see edge case #9).

  The TTL is **not** renewed on read (FR-003 validation reads do not update the pin). Only
  explicit pin file writes refresh `created_utc`. This ensures that truly abandoned sessions
  expire after `ttl_hours`, while actively progressing reviews remain valid indefinitely.

#### P2

- **FR-007**: The existing bootstrap resolution chain (`runtime-bootstrap.json` →
  `.agdt/workflows/{identity}/{worktree_key}/`) must remain the fallback when
  `AGENTIC_DEVTOOLS_STATE_DIR` is not set.
- **FR-008**: The initiate function must validate that the resolved state directory exists (or
  can be created) before propagating it to subprocesses.
- **FR-009**: Diagnostic logging must record which resolution path was used (environment
  variable, pin file, or bootstrap file) for debugging purposes. Diagnostics are emitted to
  stderr via `print(..., file=sys.stderr)` with an `[agdt]` prefix, consistent with the
  existing CLI output pattern.

### Non-functional requirements

- **NFR-001 Performance**: State directory resolution via environment variable must be O(1) —
  a single environment variable read with no pin/bootstrap file reads (directory creation
  via `mkdir` is permitted as it only occurs once on first access).
- **NFR-002 Cross-platform safety**: The environment variable propagation must work correctly
  on Windows, macOS, and Linux. The pin file atomic write mechanism (`os.replace()`) is
  guaranteed atomic on POSIX; on Windows it is atomic when source and destination are on the
  same volume, which is always the case for `.agdt/` files within the repository.
- **NFR-003 Test coverage**: All new and modified code must have 100% test coverage per the
  project's existing policy.
- **NFR-004 Backward compatibility**: Existing workflows that do not set
  `AGENTIC_DEVTOOLS_STATE_DIR` must behave identically to current behavior.
- **NFR-005 Atomicity**: The state directory resolution must be atomic — once resolved, the
  value must not change for the duration of the workflow session.

## Key entities

1. **State directory**: The filesystem path where all workflow state files are stored
   (e.g., `.agdt/workflows/{identity}/{worktree_key}/`).
2. **`AGENTIC_DEVTOOLS_STATE_DIR`**: Environment variable used to propagate the resolved state
   directory to subprocesses, bypassing `runtime-bootstrap.json`. Intentionally unconstrained —
   may point outside the repository root.
3. **`runtime-bootstrap.json`**: Shared configuration file containing only `worktree_key` —
   the current (racy) mechanism for state directory resolution. Note: `identity` is stored
   separately in `.agdt/identity.json` (with legacy fallback to reading from the bootstrap
   file for installations that predate the identity cache split).
4. **`setup_pull_request_review()`**: Background task that configures the review environment,
   currently the source of the race condition.
5. **`get_state_dir()`**: Central function that resolves the state directory path.
6. **`.agdt/pinned-state-dir.json`**: Repo-root-level pin file written atomically (via
   write-to-temp-then-rename with `os.replace()`) by the workflow initiate function. Read by
   `get_state_dir()` as step 2 in the resolution chain. Contains `state_dir`, `workflow`,
   `created_utc`, and `ttl_hours` fields.

## Edge cases

1. `AGENTIC_DEVTOOLS_STATE_DIR` is set to a non-existent directory — must create it or fail
   with a clear error.
2. `AGENTIC_DEVTOOLS_STATE_DIR` is set to an empty string — must fall back to bootstrap
   resolution (treated as unset).
3. Multiple background tasks are spawned concurrently — all must inherit the same environment
   variable value.
4. A user manually sets `AGENTIC_DEVTOOLS_STATE_DIR` before running a workflow — the manually
   set value must be respected.
5. The bootstrap file is modified by an external process during a workflow — when the
   environment variable is set, the modification must have no effect on the running workflow.
6. The worktree is deleted while a workflow is in progress:
   - **Environment variable path** (`AGENTIC_DEVTOOLS_STATE_DIR` is set): commands must fail
     gracefully with a clear error rather than falling back to a different directory, because
     the env var is the most authoritative resolution source and has no fallback (FR-002
     step 1 returns immediately).
   - **Pin file path** (resolution via `.agdt/pinned-state-dir.json`): if the pinned
     `state_dir` cannot be created or reached, FR-003 validation (check 1) causes the pin to
     be ignored and resolution falls through to the bootstrap chain with a diagnostic warning.
     This is consistent with edge case #8 (pin pointing to a moved/deleted directory).
7. **Stale pin file after workflow crash**: The workflow crashes or is killed before clearing
   `.agdt/pinned-state-dir.json` — the pin file remains on disk. On the next `get_state_dir()`
   call, the pin must be validated via FR-003 (TTL expiration check). If expired, it is
   ignored and resolution proceeds to the bootstrap chain. The stale file is cleaned up by the
   next `agdt-clear-workflow` invocation or workflow completion handler. Note: actively
   progressing reviews have their TTL renewed by `agdt-advance-workflow` (see C2), so only
   truly abandoned sessions expire.
8. **Pin file pointing to moved/deleted directory**: The `state_dir` path in the pin file no
   longer exists (e.g., worktree was removed) — `get_state_dir()` detects the non-existent
   path during FR-003 validation (check 1), ignores the pin, and falls through to bootstrap
   resolution with a diagnostic warning.
9. **Concurrent review started in same worktree**: A second `agdt-initiate-pull-request-
   review-workflow` is run while a pin file from a prior review still exists — the initiate
   function overwrites the pin file atomically (write-to-temp-then-rename via `os.replace()`)
   with the new session's `state_dir`, `workflow`, `created_utc`, and `ttl_hours`. The prior
   session's commands that relied on the old pin will resolve via the environment variable
   (if set) or fall through to bootstrap. This is acceptable because concurrent workflows in
   the same worktree are explicitly a non-goal.
10. **Pin file with unexpected content or partial writes**: The file exists but contains
    invalid JSON, missing required fields, or is truncated due to a partial write — FR-003
    validation (check 5) causes it to be ignored with a diagnostic log warning. The
    write-to-temp-then-rename pattern (see C1) prevents partial writes under normal operation;
    this edge case covers crash-during-write or external file corruption.

## Affected files

- `agentic_devtools/state.py` — `get_state_dir()`, `set_bootstrap_state()`
- `agentic_devtools/background_tasks.py` — `run_in_background()` environment propagation
- `agentic_devtools/cli/azure_devops/review_commands.py` — `setup_pull_request_review()`
- `agentic_devtools/cli/workflows/commands.py` — `initiate_pull_request_review_workflow()`

## Acceptance criteria

1. Reproducing Scenario A (both `--pull-request-id` and `--issue-key`) results in exactly one
   state directory with all review artifacts.
2. Reproducing Scenario B (only `--pull-request-id` from existing worktree) results in exactly
   one state directory.
3. All existing tests pass without modification.
4. No legacy fallback is triggered during a review workflow when the fix is active.
5. `AGENTIC_DEVTOOLS_STATE_DIR` environment variable is correctly inherited by all background
   tasks.
6. State directory resolution via environment variable completes without pin/bootstrap file
   reads.

## Success Criteria

- Zero duplicate state directories created during PR review workflows.
- All existing tests pass without modification.
- No legacy fallback activation during review workflows.
- Environment variable propagation works on all supported platforms (Windows, macOS, Linux).
- 100% test coverage for new and modified code.
- Race condition from issue #1180 is no longer reproducible.

## Open questions

- Whether `setup_pull_request_review()` should be refactored to run synchronously before the
  Copilot session starts, eliminating the race condition at the scheduling level rather than
  the resolution level.
- Whether the environment variable approach should be extended to all workflows or kept
  specific to the PR review workflow.

---
*Generated by Copilot SDK (claude-opus-4.6)*
