# Feature Specification: fix: stale prompt file causes premature Copilot session start on PR review re-runs

**Source Issue**: #1746 (<https://github.com/ayaiayorg/agentic-devtools/issues/1746>)

## Clarifications

### Session 2026-06-07

- Q: Should the stale file deletion happen inside `_start_copilot_session_for_pr_review()` (closer to `_wait_for_prompt_file`) or earlier in
  `initiate_pull_request_review_workflow()` before `setup_pull_request_review_async` is
  spawned? → A: Deletion should occur as early as possible — immediately before spawning `setup_pull_request_review_async()` in the workflow initiation path. This ensures the file is absent before
  both the background task and the wait loop begin, eliminating any race window.

- Q: Should the cleanup also remove other stale temporary artifacts from prior runs (e.g., `copilot-session-*-prompt.md`, old queue files), or strictly only the initiate prompt file? → A: Strictly
  only `temp-pull-request-review-initiate-prompt.md` for this fix. Other artifact cleanup is a separate concern and should not be bundled into this change to minimize risk.

- Q: What constitutes a "failed deletion" — should the code catch only `PermissionError`/`OSError`, or also handle cases where the file reappears between deletion and the wait loop (race condition
  with another process)? → A: Catch `OSError` (which subsumes `PermissionError` and `FileNotFoundError`). A `FileNotFoundError` during deletion is not an error (file already gone). Any other `OSError`
  (permission denied, file locked) should be treated as a hard failure. Race conditions with another process writing the same filename are not expected in single-user worktree usage and need not be
  guarded.

- Q: Should the cleanup be logged at INFO level (visible in normal output) or DEBUG level (only visible with verbose flags)? → A: Log at INFO level when a stale file is actually removed (confirming
  cleanup occurred), and at DEBUG level when no stale file is found. This gives visibility into re-run scenarios without noise on first runs.

- Q: For NFR-001, does the 120-second budget apply to the entire workflow including `_wait_for_prompt_file()` polling, or only to the stale-file cleanup operation itself? → A: The 120-second budget in
  NFR-001 refers to the stale-file cleanup operation itself, which should be near-instantaneous (single `os.remove` call). The `_wait_for_prompt_file()` polling has its own existing timeout
  configuration and is not constrained by this NFR.

## Problem Statement

When re-running `agdt-initiate-pull-request-review-workflow` in a worktree that has already had it executed once, the Copilot session starts immediately because the prompt file
(`temp-pull-request-review-initiate-prompt.md`) is still present from the previous review.

`_wait_for_prompt_file()` finds the leftover file and returns immediately, before the new background setup (`setup_pull_request_review_async`) has completed. This means the Copilot session starts with
stale context from the previous review.

## Root Cause

The prompt filename is static (`temp-pull-request-review-initiate-prompt.md`) in the state directory. On re-runs, the file from the previous execution is still present when `_wait_for_prompt_file()`
polls for it.

The workflow assumes the prompt file's presence indicates the *current* run's setup has completed, but it makes no distinction between a freshly written file and one left over from a prior execution.
There is no cleanup step between runs to reset this readiness signal.

## Solution

Delete the stale prompt file **before** spawning `setup_pull_request_review_async()`. This ensures `_wait_for_prompt_file()` only succeeds after the fresh file is written by the new background setup
task.

Implementation approach:

1. Immediately before calling `setup_pull_request_review_async()`, resolve the expected prompt file path (`temp-pull-request-review-initiate-prompt.md` in the state directory).
2. If the file exists, delete it and log at INFO level confirming stale-file cleanup.
3. If the file does not exist, log at DEBUG level (no action needed).
4. If deletion raises an `OSError` (other than `FileNotFoundError`), raise a clear error message and abort the workflow before spawning background setup or entering the wait loop.
5. Only after successful cleanup (or confirmation the file is absent), proceed to spawn `setup_pull_request_review_async()` and enter `_wait_for_prompt_file()`.

Without this change, every PR-review re-run in the same worktree can launch Copilot against stale prompt content, producing incorrect review context and requiring users to manually clean state files
between runs.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a developer re-running pull request review in an existing worktree, I want stale initiate prompt files to be ignored/removed before waiting for the next prompt so that Copilot only starts after the
new setup completes and writes fresh context.

**Acceptance Scenarios**:

1. **Given** a previous run already left `temp-pull-request-review-initiate-prompt.md` in the state directory, **When** `agdt-initiate-pull-request-review-workflow` is run again, **Then** the stale
   file is removed before background setup starts, and an INFO-level log message confirms the cleanup.

2. **Given** a re-run in the same worktree, **When** `_wait_for_prompt_file()` executes, **Then** it waits for the newly generated prompt file from the current `setup_pull_request_review_async` run
   instead of returning immediately on a stale file.

### User Story 2 - Error Recovery (Priority: P1)

As a developer re-running pull request review, I want the workflow to fail fast with clear guidance if stale prompt cleanup cannot complete so that Copilot is not launched with stale review context.

**Acceptance Scenarios**:

1. **Given** `temp-pull-request-review-initiate-prompt.md` exists but cannot be deleted (for example permissions/lock), **When** the workflow performs stale-file cleanup, **Then** it exits with an
   explicit `OSError`-based cleanup error before launching `setup_pull_request_review_async`.

2. **Given** stale-file cleanup fails, **When** the workflow reports the failure, **Then** the error message tells the user the exact file path, the OS error reason, and how to remove or unlock the
   file and retry safely.

### User Story 3 - Graceful Degradation (Priority: P2)

As a developer running multiple consecutive PR-review re-runs in the same worktree, I want readiness detection to remain tied to the current run so that each run waits for freshly generated prompt
content.

**Acceptance Scenarios**:

1. **Given** three consecutive re-runs in the same worktree, **When** each run starts, **Then** stale prompt state from prior runs never causes `_wait_for_prompt_file()` to return before current-run
   setup writes the file.

2. **Given** a previous run has completed and a new run is triggered immediately, **When** the new run reaches the wait step, **Then** Copilot launch occurs only after the prompt file produced by that
   new run is present.

## Requirements

### Functional Requirements

- **FR-001**: Before starting `setup_pull_request_review_async`, the workflow MUST check for `temp-pull-request-review-initiate-prompt.md` in the resolved state directory and remove it when present.

- **FR-002**: If stale prompt-file deletion fails with an `OSError` (excluding `FileNotFoundError`), the workflow MUST surface a clear error including the file path and OS error reason, and MUST NOT
  proceed to wait on the prompt file or spawn background setup.

- **FR-003**: `_wait_for_prompt_file()` MUST only consider a prompt file produced by the current run (i.e., after stale-file cleanup) as the readiness signal for launching Copilot.

- **FR-004**: On a first-time run where no prompt file exists, workflow behavior MUST remain unchanged except for the added pre-check (logged at DEBUG level).

- **FR-005**: Re-running pull request review in the same worktree MUST no longer start Copilot before `setup_pull_request_review_async` has completed writing fresh prompt content.

### Non-Functional Requirements

- **NFR-001**: The stale-file cleanup operation must complete within 120 seconds under normal conditions (expected to be near-instantaneous as it is a single `os.remove` call; lock/permission errors
  are treated as immediate failures per FR-002 and SC-004).

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts — no changes to function signatures, CLI arguments, state keys, or prompt file naming
  conventions.

## Success Criteria

- **SC-001**: In a re-run scenario with a pre-existing `temp-pull-request-review-initiate-prompt.md`, logs show stale-file cleanup occurs (INFO-level message) before `setup_pull_request_review_async`
  is launched.

- **SC-002**: In repeated re-runs within the same worktree, Copilot session start no longer occurs before the current run writes a fresh initiate prompt file.

- **SC-003**: First-run behavior (no existing prompt file) remains functionally equivalent to current behavior, aside from the added stale-file pre-check (DEBUG-level log only).

- **SC-004**: When stale file cannot be deleted due to OS-level lock/permission issues, the workflow aborts with a user-actionable error message before any background task or Copilot session is
  started.

---
*Generated by Copilot SDK (claude-opus-4.6)*
