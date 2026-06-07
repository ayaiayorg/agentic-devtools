# Feature Specification: fix: stale prompt file causes premature Copilot session start on PR review re-runs

> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace
> placeholder content with detailed, issue-specific information.

**Source Issue**: #1746 (<https://github.com/ayaiayorg/agentic-devtools/issues/1746>)

## Problem Statement

When re-running `agdt-initiate-pull-request-review-workflow` in a worktree that has already had it executed once, the Copilot session starts immediately because the prompt file
(`temp-pull-request-review-initiate-prompt.md`) is still present from the previous review.

`_wait_for_prompt_file()` finds the leftover file and returns immediately, before the new background setup (`setup_pull_request_review_async`) has completed. This means the Copilot session starts with
stale context from the previous review.

## Root Cause

The prompt filename is static (`temp-pull-request-review-initiate-prompt.md`) in the state directory. On re-runs, the file from the previous execution is still present when `_wait_for_prompt_file()`
polls for it.

## Solution

Delete the stale prompt file **before** spawning `setup_pull_request_review_async()`. This ensures `_wait_for_prompt_file()` only succeeds after the fresh file is written by the new background setup
task.

Without this change, every PR-review re-run in the same worktree can launch Copilot against stale prompt content, producing incorrect review context and requiring users to manually clean state files
between runs.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a developer re-running pull request review in an existing worktree, I want stale initiate prompt files to be ignored/removed before waiting for the next prompt so that Copilot only starts after the
new setup completes and writes fresh context.

**Acceptance Scenarios**:

1. **Given** a previous run already left `temp-pull-request-review-initiate-prompt.md` in the state directory, **When** `agdt-initiate-pull-request-review-workflow` is run again, **Then** the stale
   file is removed before background setup starts.

2. **Given** a re-run in the same worktree, **When** `_wait_for_prompt_file()` executes, **Then** it waits for the newly generated prompt file from the current
   `setup_pull_request_review_async` run instead of returning immediately on a stale file.

### User Story 2 - Error Recovery (Priority: P1)

As a developer re-running pull request review, I want the workflow to fail fast with clear guidance if stale prompt cleanup cannot complete so that Copilot is not launched with stale review context.

**Acceptance Scenarios**:

1. **Given** `temp-pull-request-review-initiate-prompt.md` exists but cannot be deleted (for example permissions/lock), **When** the workflow performs stale-file cleanup, **Then** it exits with an
   explicit cleanup error before launching `setup_pull_request_review_async`.

2. **Given** stale-file cleanup fails, **When** the workflow reports the failure, **Then** the error message tells the user how to remove or unlock the file and retry safely.

### User Story 3 - Graceful Degradation (Priority: P2)

As a developer running multiple consecutive PR-review re-runs in the same worktree, I want readiness detection to remain tied to the current run so that each run waits for freshly generated prompt content.

**Acceptance Scenarios**:

1. **Given** three consecutive re-runs in the same worktree, **When** each run starts, **Then** stale prompt state from prior runs never causes `_wait_for_prompt_file()` to return before
   current-run setup writes the file.

2. **Given** a previous run has completed and a new run is triggered immediately, **When** the new run reaches the wait step, **Then** Copilot launch occurs only after the prompt file produced by
   that new run is present.

## Requirements

### Functional Requirements

- **FR-001**: Before starting `setup_pull_request_review_async`, the workflow MUST check for `temp-pull-request-review-initiate-prompt.md` in the resolved state directory and remove it when present.

- **FR-002**: If stale prompt-file deletion fails, the workflow MUST surface a clear error and MUST NOT proceed to wait on the prompt file.

- **FR-003**: `_wait_for_prompt_file()` MUST only consider a prompt file produced by the current run (i.e., after stale-file cleanup) as the readiness signal for launching Copilot.

- **FR-004**: On a first-time run where no prompt file exists, workflow behavior MUST remain unchanged except for the added pre-check.

- **FR-005**: Re-running pull request review in the same worktree MUST no longer start Copilot before `setup_pull_request_review_async` has completed writing fresh prompt content.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

- **SC-001**: In a re-run scenario with a pre-existing `temp-pull-request-review-initiate-prompt.md`, logs show stale-file cleanup occurs before `setup_pull_request_review_async` is launched.

- **SC-002**: In repeated re-runs within the same worktree, Copilot session start no longer occurs before the current run writes a fresh initiate prompt file.

- **SC-003**: First-run behavior (no existing prompt file) remains functionally equivalent to current behavior, aside from the added stale-file pre-check.

---
*Generated via fallback skeleton — manual enrichment required*

---
*Generated by Copilot SDK (claude-opus-4.6)*
