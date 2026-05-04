# Feature Specification: Resilient Error Handling and Retry Logic for SpecKit Pipeline Scripts

**Feature Branch**: `speckit/1326/phase-1-specify`  
**Created**: 2026-05-04  
**Status**: Draft  
**Input**: GitHub Issue #1326  
**Source Issue**: #1326 (<https://github.com/ayaiayorg/agentic-devtools/issues/1326>)

## Problem Statement

Several SpecKit pipeline shell scripts in `.github/scripts/speckit-trigger/` do not reliably propagate failures or handle transient errors. The most critical defect is in `create-spec-pr.sh`, where a
failed `gh pr create` (e.g., HTTP 504) logs a warning but exits with code 0, causing the GitHub Actions step to report success. Additionally, `post-issue-comment.sh` uses `curl -s` without inspecting
the HTTP response code or retrying on transient failures. A proven `call_with_retry` helper already exists in `generate-spec-from-issue.sh` but is not shared across scripts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — PR Creation Failure Surfaces as a Failed Step (Priority: P1)

As a **maintainer relying on the SpecKit pipeline**, I want `create-spec-pr.sh` to exit with a non-zero code when `gh pr create` fails, so that the GitHub Actions step is marked as failed and I am
immediately notified instead of discovering hours later that the PR was never created.

**Why this priority**: This is the bug that motivated the issue — silent success on a critical mutation (PR creation) masks real failures and causes downstream pipeline steps to run on a nonexistent
PR.

**Independent Test**: Run `create-spec-pr.sh` in a test environment where `gh pr create` is stubbed to return a non-zero exit code (simulating a transient failure
such as an HTTP 504 timeout). Verify the script exits with a non-zero code and the GitHub Actions step status is "failure". Optionally assert that stderr contains the
underlying error context (e.g., an HTTP 504 message) for diagnostics.

**Acceptance Scenarios**:

1. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails with a non-zero exit code (e.g., HTTP 504 timeout), **Then** `create-spec-pr.sh` exits with a non-zero exit
   code and writes a descriptive error message to stderr.
2. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails on the first attempt but succeeds on a subsequent retry, **Then** the script completes successfully, outputs
   the PR URL, and sets `pr_url` / `pr_number` in `GITHUB_OUTPUT`.
3. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails on all retry attempts, **Then** the script exits with a non-zero exit code, logs the number of attempts made
   and the final error, and does **not** set `pr_url` in `GITHUB_OUTPUT`.

---

### User Story 2 — Issue Comment Posting Validates HTTP Response and Retries (Priority: P1)

As a **maintainer relying on the SpecKit pipeline**, I want `post-issue-comment.sh` to detect HTTP errors from the GitHub API and retry on transient failures, so that comments are reliably posted and
the step fails visibly when the API is persistently unavailable.

**Why this priority**: Comment posting is used in every pipeline phase to communicate status back to the issue. A silently dropped comment leaves the issue without context and confuses human
reviewers.

**Independent Test**: Run `post-issue-comment.sh` with a mock HTTP endpoint that returns 502 on the first two calls and 201 on the third. Verify the comment is posted and the script exits 0. Then run
with a mock that always returns 500; verify the script exits non-zero.

**Acceptance Scenarios**:

1. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 201, **Then** the script exits 0 and prints a success message.
2. **Given** a valid issue number and template, **When** the GitHub API returns a transient error (5xx), **Then** the script retries with exponential backoff up to the configured maximum attempts.
3. **Given** a valid issue number and template, **When** the GitHub API returns a non-2xx status on all retry attempts, **Then** the script exits with a non-zero exit code and logs the HTTP status
   code and response body to stderr.
4. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 422 (validation error / client error), **Then** the script does **not** retry (client errors are not transient) and
   exits with a non-zero code immediately.

---

### User Story 3 — Shared Retry Helper Library (Priority: P2)

As a **pipeline script developer**, I want a single, sourced shell library containing the `call_with_retry` function, so that all SpecKit scripts use consistent retry semantics without duplicating the
implementation.

**Why this priority**: The retry helper already exists and works well in `generate-spec-from-issue.sh`. Extracting it removes duplication and makes it trivial for User Stories 1 and 2 (and future
scripts) to adopt retry logic.

**Independent Test**: Source the shared library in a test script, invoke `call_with_retry` with a command that fails twice then succeeds, and verify it returns 0 after the third attempt. Invoke it
with a command that always fails and verify it returns non-zero after exhausting attempts.

**Acceptance Scenarios**:

1. **Given** a shell script that sources the shared retry library, **When** `call_with_retry 3 2 <command>` is invoked and `<command>` fails on the first two attempts then succeeds, **Then** the
   function returns 0, having retried with exponential backoff (2s, 4s delays).
2. **Given** a shell script that sources the shared retry library, **When** `call_with_retry 3 2 <command>` is invoked and `<command>` fails on all three attempts, **Then** the function returns 1 and
   logs "All 3 attempts failed." to stderr.
3. **Given** `generate-spec-from-issue.sh` currently contains an inline `call_with_retry` function, **When** the shared library is adopted, **Then** `generate-spec-from-issue.sh` sources the library
   instead of defining its own copy, and its existing behaviour is unchanged.

---

### User Story 4 — Audit and Harden Remaining Scripts (Priority: P3)

As a **pipeline reliability engineer**, I want all other SpecKit pipeline scripts audited for silent-success-on-failure patterns, so that no script masks errors that should fail the GitHub Actions
step.

**Why this priority**: After fixing the two most critical scripts, a sweep of the remaining scripts prevents regressions and undiscovered silent failures. This is lower priority because only
`create-spec-pr.sh` and `post-issue-comment.sh` have confirmed issues today.

**Independent Test**: For each script identified during the audit, introduce a simulated failure for the primary external call (e.g., `gh`, `curl`, external process) and verify the script exits
non-zero.

**Acceptance Scenarios**:

1. **Given** the set of all shell scripts under `.github/scripts/speckit-trigger/`, **When** each script's primary external command is stubbed to fail, **Then** no script exits with code 0 on failure
   unless the failure is explicitly documented as non-fatal (e.g., optional label application).
2. **Given** a script that already uses `call_with_retry` inline (e.g., `generate-spec-from-issue.sh`), **When** the shared library from User Story 3 is available, **Then** the script is migrated to
   source the shared library with no behavioural change.

---

### Edge Cases

- **What happens when the GitHub API rate-limits the caller (HTTP 403 with `Retry-After` header)?** The retry logic should respect the `Retry-After` header when present, or at minimum, the exponential
  backoff should be sufficient to outlast short rate-limit windows.
- **What happens when `gh` CLI is not installed or not authenticated?** The script should fail immediately on the first attempt (authentication errors are not transient) rather than retrying.
- **What happens when `GITHUB_OUTPUT` is unset (e.g., running outside GitHub Actions)?** The existing fallback to `/dev/stdout` must be preserved; error handling changes must not break local testing.
- **What happens when the network is completely unavailable (DNS failure)?** The retry mechanism should still apply — DNS failures are transient. All attempts should be exhausted before failing.
- **What happens when `curl` receives a redirect (3xx)?** Redirects should be followed (using `curl -L`). Only final response codes should be evaluated for success/failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `create-spec-pr.sh` MUST exit with a non-zero exit code when `gh pr create` fails after all retry attempts are exhausted.
- **FR-002**: `create-spec-pr.sh` MUST retry the `gh pr create` command with exponential backoff on transient failures (non-zero exit code from `gh` indicative of
  network or server errors). Non-retryable failures — such as missing `gh` binary (command not found), authentication errors, or validation errors — MUST cause immediate
  failure without retry.
- **FR-003**: `post-issue-comment.sh` MUST capture and inspect the HTTP response status code from the `curl` call.
- **FR-004**: `post-issue-comment.sh` MUST exit with a non-zero exit code when the HTTP response status is not in the 2xx range after applying the retry rules
  defined in FR-005 and FR-006 (i.e., after exhausting retries for retryable errors, or immediately for non-retryable errors).
- **FR-005**: `post-issue-comment.sh` MUST retry `curl` calls on transient server errors (HTTP 5xx) and network errors with exponential backoff.
- **FR-006**: `post-issue-comment.sh` MUST NOT retry on client errors (HTTP 4xx) except for 429 (rate limit) and 403 when accompanied by a `Retry-After` header (secondary rate-limit response).
- **FR-007**: A shared shell library file MUST be created at `.github/scripts/speckit-trigger/lib/retry.sh` containing the `call_with_retry` function, sourceable by all SpecKit pipeline
  scripts. Consuming scripts MUST source it relative to their own directory via `BASH_SOURCE[0]` to ensure reliable sourcing from any working directory.
- **FR-008**: `generate-spec-from-issue.sh` MUST be updated to source the shared retry library instead of defining `call_with_retry` inline.
- **FR-009**: The retry mechanism MUST log each retry attempt number, total attempts, and delay to stderr for observability in GitHub Actions logs.
- **FR-010**: All retry-related error messages MUST include the failing command name and the exit code or HTTP status code for diagnostics.
- **FR-011**: `post-issue-comment.sh` MUST follow HTTP redirects (using `curl -L`) and evaluate only the final response status code for success/failure classification.

### Non-Functional Requirements

- **NFR-001**: The default retry configuration MUST be 3 attempts with an initial delay of 5 seconds and exponential backoff (5s → 10s), consistent with the existing `call_with_retry`
  implementation. The delay sequence lists intervals between consecutive attempts: 5 s before the 2nd attempt, 10 s before the 3rd attempt (2 delays for 3 attempts total).
- **NFR-002**: The maximum wall-clock time added by retries for any single command MUST NOT exceed 60 seconds (to avoid GitHub Actions step timeouts), excluding any sleep time
  mandated by a `Retry-After` header on rate-limit responses (HTTP 429 or 403 with `Retry-After`). If a `Retry-After` value exceeds 60 seconds, the script MUST fail immediately
  rather than waiting.
- **NFR-003**: Error messages MUST be written to stderr; normal operational output MUST remain on stdout, preserving the existing contract for `GITHUB_OUTPUT` and captured output.
- **NFR-004**: The shared retry library MUST be compatible with Bash 4.x+ and function correctly on `ubuntu-latest` GitHub Actions runners.
- **NFR-005**: All changes MUST maintain backward compatibility — existing script arguments, environment variables, and `GITHUB_OUTPUT` key names MUST NOT change.
- **NFR-006**: Scripts MUST remain idempotent where they currently are (e.g., label creation with `--force`).

### Key Entities

- **Shared Retry Library** (`.github/scripts/speckit-trigger/lib/retry.sh`): A sourceable shell file exporting the `call_with_retry` function with configurable max attempts,
  initial delay, and exponential backoff. Scripts MUST source this library relative to their own directory using `BASH_SOURCE[0]` (e.g.,
  `source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/lib/retry.sh"`) so that sourcing works reliably regardless of the caller's working directory.
- **HTTP Response Validator**: Logic within `post-issue-comment.sh` (or extracted to the shared library) that evaluates `curl` HTTP status codes and classifies them as success (2xx),
  transient/retryable (5xx, 429), or permanent failure (other 4xx).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When `gh pr create` returns a non-zero exit code, the `create-spec-pr.sh` step in GitHub Actions is reported as **failed** (not succeeded) — verified by CI run logs.
- **SC-002**: Transient `gh pr create` failures (e.g., HTTP 504) that succeed on retry result in a successful PR creation without manual intervention — verified by a test with a stubbed `gh` that
  fails once then succeeds.
- **SC-003**: When the GitHub API returns HTTP 500/502/503 for comment posting, `post-issue-comment.sh` retries and eventually succeeds or exits non-zero — verified by integration test with mock
  responses.
- **SC-004**: The `call_with_retry` function exists in exactly one shared library file; no other script defines its own copy — verified by
  `grep -rE 'call_with_retry[[:space:]]*(\(|\{)' .github/scripts/` returning exactly one match (the definition in `lib/retry.sh`). This pattern matches both
  `call_with_retry() {` and `function call_with_retry {` declaration styles, ensuring no alternative syntax bypasses the check. The shared library
  MUST use the canonical `call_with_retry() {` declaration style.
- **SC-005**: All existing tests (`test_markdownlint_validation.sh`, `test_content_preservation.sh`, `test_check_analysis_gate.sh`, `test_sc004_regression.sh`) continue to pass after changes —
  verified by CI.
- **SC-006**: The SpecKit pipeline completes a full 5-phase run successfully when no transient errors occur — verified by end-to-end pipeline execution (no regression).

---
*Generated by Copilot SDK (claude-opus-4.6)*
