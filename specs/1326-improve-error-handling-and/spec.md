# Feature Specification: Resilient Error Handling and Retry Logic for SpecKit Pipeline Scripts

**Feature Branch**: `speckit/1326/phase-2-clarify`  
**Created**: 2026-05-04  
**Status**: Draft  
**Input**: GitHub Issue #1326  
**Source Issue**: #1326 (<https://github.com/ayaiayorg/agentic-devtools/issues/1326>)

## Problem Statement

Several SpecKit pipeline shell scripts in `.github/scripts/speckit-trigger/` do not reliably propagate failures or handle transient errors. The most critical defect is in `create-spec-pr.sh`, where a
failed `gh pr create` (e.g., HTTP 504) logs a warning but exits with code 0, causing the GitHub Actions step to report success. Additionally, `post-issue-comment.sh` uses `curl -s` without inspecting
the HTTP response code or retrying on transient failures. A proven `call_with_retry` helper already exists in `generate-spec-from-issue.sh` but is not shared across scripts.

## Clarifications

### Session 2026-05-05

- Q: How should `create-spec-pr.sh` distinguish between retryable transient failures (e.g., HTTP 504, network timeout) and non-retryable failures (e.g., validation error "branch does not exist") given
  that `gh pr create` only returns a non-zero exit code without structured error classification? → A: Inspect the combined stderr output (from both the shell and `gh`) for known non-retryable
  patterns (e.g., "not found", "does not exist", "permission denied", "authentication", "command not found") using a simple grep check. Additionally, detect a missing `gh` binary
  via exit code 127. If stderr matches a known non-retryable pattern or exit code is 127, fail immediately. All other non-zero exits are treated as retryable. This approach errs on the side of
  retrying (safe default) and can be refined over time by adding patterns. Note: "already exists" is intentionally excluded from the non-retryable list because `gh pr create` may report
  "already exists" when the PR was actually created on a previous attempt that timed out client-side — this is an ambiguous success, not a definitive failure (see Edge Cases).
- Q: Should the `call_with_retry` function in the shared library support an optional callback/hook for classifying errors as retryable vs. non-retryable (to support both `gh` exit-code-based and
  `curl` HTTP-status-based retry decisions), or should `post-issue-comment.sh` implement its own retry loop for HTTP-aware retries? → A: The shared `call_with_retry` function should remain simple
  (retry on any non-zero exit code, as it does today). For `post-issue-comment.sh`, implement an HTTP-aware wrapper function (e.g., `curl_with_retry`) that internally handles HTTP status
  classification and calls `curl` in a retry loop with the same exponential backoff semantics. This wrapper can source the shared library for the backoff delay calculation helper but manages its own
  retry decisions based on HTTP status codes and a defined set of retryable transport-level `curl` exit codes (6=DNS failure, 7=connection refused, 28=timeout, 35=TLS handshake,
  52=empty reply, 56=receive failure).
- Q: For the `post-issue-comment.sh` HTTP 429 (rate limit) handling, should the script parse the `Retry-After` header value and sleep for exactly that duration, or should it use the maximum of the
  `Retry-After` value and the calculated exponential backoff delay? → A: Use the maximum of the `Retry-After` header value and the calculated exponential backoff delay. This ensures the script never
  sleeps less than what the API requires while still respecting the overall exponential backoff strategy. If `Retry-After` exceeds 60 seconds, fail immediately per NFR-002.
- Q: What constitutes the "primary external command" for scripts audited in User Story 4 — specifically, should scripts like `sanitize-branch-name.sh` and `validate-label.sh` that perform only local
  operations (no API calls) be included in the hardening scope? → A: Only scripts that make external network calls (API requests via `gh`, `curl`, or similar) are in scope for retry logic. Pure local
  scripts (`sanitize-branch-name.sh`, `validate-label.sh`, `check-idempotency.sh`) should still be audited for proper exit-code propagation (i.e., they must not mask failures) but do NOT need retry
  logic since their failures are deterministic and not transient.
- Q: Should the shared retry library file (`.github/scripts/speckit-trigger/lib/retry.sh`) also export a `calculate_backoff_delay` utility function that `post-issue-comment.sh`'s HTTP-aware retry loop
  can use, or should each script independently compute backoff delays? → A: Yes, the shared library should export a `calculate_backoff_delay` helper function (accepting retry number — 1-based, where
  retry 1 is the first retry after the initial attempt fails — and initial delay, returning the computed delay via `initial_delay × 2^(retry_number-1)`) so that all scripts share identical backoff
  arithmetic. For the default configuration (initial_delay=5): retry 1 → 5s, retry 2 → 10s, matching NFR-001. This keeps the exponential backoff logic DRY and ensures consistent delay behaviour
  across `call_with_retry` and the HTTP-aware `curl_with_retry` wrapper.

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

1. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails with a transient error (e.g., HTTP 504 timeout) on all retry attempts, **Then** `create-spec-pr.sh` exits
   with a non-zero exit code and writes a descriptive error message (including the failing command and exit code) to stderr, consistent with FR-002's retry-then-fail behaviour.
2. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails on the first attempt but succeeds on a subsequent retry, **Then** the script completes successfully, outputs
   the PR URL, and sets `pr_url` / `pr_number` in `GITHUB_OUTPUT`.
3. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails on all retry attempts, **Then** the script exits with a non-zero exit code, logs the number of attempts made
   and the final error, and writes empty values (`pr_url=` and `pr_number=`) to `GITHUB_OUTPUT`, preserving both keys' presence per NFR-005.
4. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails with stderr containing a non-retryable pattern (e.g., "not found", "does not exist",
   "permission denied", or "authentication"), **Then** the script fails immediately without retrying and exits with a non-zero exit code.
5. **Given** a valid branch with committed spec artifacts, **When** `gh` is not installed (the shell returns exit code 127 with "command not found" in stderr), **Then** the script fails immediately
   without retrying and exits with a non-zero exit code.
6. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails on the first attempt with a transient error but succeeds on the second attempt, **Then** the script waits
   with exponential backoff (5s delay before the first retry, as computed by `calculate_backoff_delay` from the shared retry library per FR-012) before the retry attempt, consistent with NFR-001.
7. **Given** the implementation of `create-spec-pr.sh`, **When** the script is inspected via four checks — (a) `grep -cE '^[[:space:]]*(source|\.)[[:space:]]+.*lib/retry\.sh' .github/scripts/speckit-trigger/create-spec-pr.sh`
   returns at least 1, confirming it contains an actual `source` (or `.`) statement loading the shared library (excluding comments),
   AND (b) `grep -v '^[[:space:]]*#' .github/scripts/speckit-trigger/create-spec-pr.sh | grep -cE 'call_with_retry[[:space:]]*(\(|\{)'`
   returns 0, confirming it does NOT define its own `call_with_retry` function (comment lines are excluded via `grep -v '^[[:space:]]*#'` to avoid false positives),
   AND (c) `grep -v '^[[:space:]]*#' .github/scripts/speckit-trigger/create-spec-pr.sh | grep -c 'call_with_retry '` returns at least **1**, confirming
   at least one `call_with_retry` invocation exists on non-comment lines — proving the shared helper is actively used (not merely sourced). This check intentionally avoids
   hard-coding a specific number of literal call sites, since a compliant implementation may route multiple retry paths through a local wrapper that delegates to `call_with_retry`,
   AND (d) `grep -v '^[[:space:]]*#' .github/scripts/speckit-trigger/create-spec-pr.sh | grep -c 'call_with_retry.*gh pr create\|gh pr create.*call_with_retry'` returns at least 1,
   OR the `call_with_retry` invocation on the line immediately preceding or wrapping the `gh pr create` call can be confirmed via context-aware inspection (e.g.,
   `grep -v '^[[:space:]]*#' .github/scripts/speckit-trigger/create-spec-pr.sh | grep -B2 -A2 'gh pr create' | grep -c 'call_with_retry'` returns at least 1),
   confirming the primary PR creation command is wrapped by `call_with_retry` — **Then** all four checks pass, verifying FR-012's structural requirement that retry logic
   for the `gh pr create` path is provided exclusively by the shared library and is actively used (not only present for the recovery lookup).
8. **Given** a valid branch with committed spec artifacts, **When** `gh pr create` fails with stderr containing "already exists" (indicating the PR was created on a previous timed-out attempt),
   **Then** the script treats this as an ambiguous success: it attempts to recover the existing PR URL and number (via `call_with_retry` wrapping
   a recovery function that invokes `gh pr list --head <branch> --json url,number --jq '.[0]'` and treats an empty or null result as a non-zero
   exit — i.e., the wrapper returns failure when `gh pr list` exits 0 but produces no output, so that `call_with_retry` retries the lookup to
   accommodate GitHub's eventual consistency), and if recovery succeeds (non-empty JSON output), the script exits 0 and sets `pr_url` /
   `pr_number` in `GITHUB_OUTPUT`; if recovery fails after exhausting retries, the script writes empty values (`pr_url=` / `pr_number=`) to
   `GITHUB_OUTPUT` per NFR-005 and exits with a non-zero exit code (per FR-013).

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
5. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 429 with a `Retry-After: 10` header, **Then** the script sleeps for the maximum of the `Retry-After` value and the
   calculated exponential backoff delay before retrying.
6. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 429 with a `Retry-After` value exceeding 60 seconds, **Then** the script fails immediately without waiting, per
   NFR-002.
7. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 429 without a `Retry-After` header (plain rate-limit response), **Then** the script retries using exponential
   backoff (the calculated delay only, since no `Retry-After` value is present), consistent with FR-006's classification of 429 as always retryable regardless of header presence.
8. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 403 with a `Retry-After` header (secondary rate-limit response), **Then** the script treats it as a retryable
   rate-limit response and sleeps for the maximum of the `Retry-After` value and the calculated exponential backoff delay before retrying, consistent with FR-006.
9. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 403 with a `Retry-After` value exceeding 60 seconds (secondary rate-limit response), **Then** the script fails
   immediately without waiting, per NFR-002.
10. **Given** a valid issue number and template, **When** the GitHub API returns HTTP 403 without a `Retry-After` header (plain forbidden response, not a rate-limit), **Then** the script does NOT
    retry (403 without `Retry-After` is a non-retryable client error per FR-006) and exits with a non-zero exit code immediately.
11. **Given** a valid issue number and template, **When** `curl` fails with a transport-level error (e.g., exit code 6 for DNS resolution failure, exit code 7 for connection refused, or exit code 28
   for connection timeout) without producing an HTTP status code, **Then** the script treats the failure as a retryable transient error and retries with exponential backoff up to the configured
   maximum attempts.
12. **Given** a valid issue number and template, **When** the GitHub API endpoint returns an HTTP redirect, **Then** `curl_with_retry` follows the redirect while preserving POST semantics
    (using `curl -L --post301 --post302 --post303`) and evaluates only the final response status code for success/failure classification, per FR-011. This scenario MUST be validated
    independently for each redirect type (301, 302, and 303) to ensure all three `--postNNN` flags are exercised.
13. **Given** a valid issue number and template, **When** the GitHub API returns a non-2xx status on all retry attempts, **Then** each retry-related error message logged to stderr includes the
    failing command name (`curl`) and the HTTP status code, per FR-010.
14. **Given** a valid issue number and template, **When** `curl` fails with a transport-level error (e.g., exit code 6 for DNS resolution failure) on all retry attempts, **Then** each retry-related
    error message logged to stderr includes the failing command name (`curl`) and the transport exit code, per FR-010.
15. **Given** a valid issue number and template, **When** `curl` fails with a transport-level error (e.g., exit code 6 for DNS resolution failure, exit code 7 for connection refused, or exit code 28
    for connection timeout) on all retry attempts, **Then** the script exits with a non-zero exit code, consistent with FR-004's terminal failure requirement extended to transport errors.
16. **Given** a valid issue number and template, **When** `curl` fails with a non-retryable transport exit code (e.g., exit code 3 for malformed URL or exit code 60 for certificate verification
    failure), **Then** `curl_with_retry` does NOT retry and the script fails immediately with a non-zero exit code, per FR-005's distinction between retryable transport errors (codes 6, 7, 28,
    35, 52, 56) and deterministic local/configuration errors (all other non-zero `curl` exit codes).
17. **Given** the implementation of `post-issue-comment.sh`, **When** the script is inspected via four checks —
    (a) `grep -cE '^[[:space:]]*(source|\.)[[:space:]]+.*lib/retry\.sh' .github/scripts/speckit-trigger/post-issue-comment.sh`
    returns at least 1, confirming it contains an actual `source` (or `.`) statement loading the shared library (excluding comments),
    AND (b) `grep -v '^[[:space:]]*#' .github/scripts/speckit-trigger/post-issue-comment.sh | grep -cE 'calculate_backoff_delay[[:space:]]*(\(|\{)'`
    returns 0, confirming it does NOT define its own inline `calculate_backoff_delay` function (comment lines are excluded via `grep -v '^[[:space:]]*#'` to avoid false positives),
    AND (c) `grep -v '^[[:space:]]*#' .github/scripts/speckit-trigger/post-issue-comment.sh | grep -c 'calculate_backoff_delay'`
    returns at least 1, confirming `calculate_backoff_delay` is invoked on non-comment lines,
    AND (d) `sed -nE '/^[[:space:]]*(function[[:space:]]+)?curl_with_retry[[:space:]]*[({]/,/^[[:space:]]*}/p' .github/scripts/speckit-trigger/post-issue-comment.sh |`
    `grep -v '^[[:space:]]*#' | grep -c 'calculate_backoff_delay'`
    returns at least 1 (proving `calculate_backoff_delay` is called on a non-comment line inside the `curl_with_retry` function body).
    The `sed` pattern allows optional leading whitespace and matches both `curl_with_retry() {` and
    `function curl_with_retry {` declaration styles (including indented declarations) so that alternative Bash syntax does not cause a false negative.
    Comment lines are excluded via `grep -v '^[[:space:]]*#'` to avoid false positives from comments mentioning the function name.
    OR if `curl_with_retry` delegates delay computation through a local helper,
    then `sed -nE '/^[[:space:]]*(function[[:space:]]+)?<helper_name>[[:space:]]*[({]/,/^[[:space:]]*}/p' .github/scripts/speckit-trigger/post-issue-comment.sh |`
    `grep -v '^[[:space:]]*#' | grep -c 'calculate_backoff_delay'` returns at least 1 for that helper AND
    `sed -nE '/^[[:space:]]*(function[[:space:]]+)?curl_with_retry[[:space:]]*[({]/,/^[[:space:]]*}/p' .github/scripts/speckit-trigger/post-issue-comment.sh |`
    `grep -v '^[[:space:]]*#' | grep -c '<helper_name>'` also returns at least 1 (proving the call chain),
    confirming `calculate_backoff_delay` is reachable from `curl_with_retry`'s execution path rather than at an unrelated call site —
    **Then** all four checks pass, verifying FR-005's mandate that the script's retry logic delegates backoff delay computation to the shared library's `calculate_backoff_delay`
    function rather than duplicating the backoff arithmetic. This check intentionally avoids constraining which function body the call appears in, since a compliant implementation
    may delegate through a small local delay helper that calls the shared function.
18. **Given** a valid issue number and template, **When** the GitHub API returns a transient error (5xx) on the first attempt and `curl_with_retry` retries, **Then** each intermediate retry log
    written to stderr includes the attempt number, total configured attempts, and the computed delay before the next retry — satisfying FR-009's observability requirement independently for
    `post-issue-comment.sh`'s HTTP-aware retry loop, not only for the shared `call_with_retry` helper validated in US3 scenario 5.

---

### User Story 3 — Shared Retry Helper Library (Priority: P2)

As a **pipeline script developer**, I want a single, sourced shell library containing the `call_with_retry` function and a `calculate_backoff_delay` helper, so that all SpecKit scripts use consistent
retry semantics without duplicating the implementation.

**Why this priority**: The retry helper already exists and works well in `generate-spec-from-issue.sh`. Extracting it removes duplication and makes it trivial for User Stories 1 and 2 (and future
scripts) to adopt retry logic.

**Independent Test**: Source the shared library in a test script, invoke `call_with_retry` with a command that fails twice then succeeds, and verify it returns 0 after the third attempt. Invoke it
with a command that always fails and verify it returns non-zero after exhausting attempts. Additionally, verify `calculate_backoff_delay 1 5` returns `5` (delay before the 1st retry) and
`calculate_backoff_delay 2 5` returns `10` (delay before the 2nd retry), consistent with NFR-001's 5s → 10s delay sequence.

**Acceptance Scenarios**:

1. **Given** a shell script that sources the shared retry library, **When** `call_with_retry 3 2 <command>` is invoked and `<command>` fails on the first two attempts then succeeds, **Then** the
   function returns 0, having retried with exponential backoff (2s, 4s delays).
2. **Given** a shell script that sources the shared retry library, **When** `call_with_retry 3 2 <command>` is invoked and `<command>` fails on all three attempts, **Then** the function returns 1 and
   logs `"All 3 attempts failed. Command: '<command>', last exit code: <exit_code>"` to stderr, per FR-010.
3. **Given** `generate-spec-from-issue.sh` currently contains an inline `call_with_retry` function, **When** the shared library is adopted, **Then** `generate-spec-from-issue.sh` sources the library
   instead of defining its own copy, and its existing behaviour is unchanged except for enhanced retry error messages (now including the failing command name per FR-010).
4. **Given** a shell script that sources the shared retry library, **When** `calculate_backoff_delay 2 5` is invoked, **Then** the function outputs `10` (5 × 2^(2-1)) representing the delay before the
   2nd retry (i.e., before the 3rd attempt), consistent with NFR-001's 5s → 10s delay sequence.
5. **Given** a shell script that sources the shared retry library, **When** `call_with_retry 3 2 <command>` is invoked and `<command>` fails on the first attempt then succeeds on the second, **Then**
   the intermediate retry log written to stderr for the first failed attempt includes: the attempt number (`1`), total configured attempts (`3`), the computed delay before the next retry, the
   failing command name (`<command>`), and its exit code — satisfying both FR-009 (attempt/total/delay observability) and FR-010 (command name and exit code diagnostics).
6. **Given** a consuming script (e.g., `create-spec-pr.sh`) that sources the shared retry library via `BASH_SOURCE[0]`-relative path, **When** the script is invoked from a working directory
   different from the script's own directory (e.g.,
   `cd /tmp && GH_TOKEN=fake GITHUB_REPOSITORY=owner/repo bash /path/to/.github/scripts/speckit-trigger/create-spec-pr.sh feature/1326 /path/to/specs/1326-improve-error-handling-and 1326 "Title"`,
   where `GH_TOKEN` and `GITHUB_REPOSITORY` are set to satisfy the script's environment validation before it reaches the library-sourcing code, and the `SPEC_DIR` argument is an absolute
   path so that the script's directory-existence validation also passes),
   **Then** the library is sourced successfully and `call_with_retry` is available, verifying FR-007's portability guarantee.

---

### User Story 4 — Audit and Harden Remaining Scripts (Priority: P3)

As a **pipeline reliability engineer**, I want all other SpecKit pipeline scripts audited for silent-success-on-failure patterns, so that no script masks errors that should fail the GitHub Actions
step.

**Why this priority**: After fixing the two most critical scripts, a sweep of the remaining scripts prevents regressions and undiscovered silent failures. This is lower priority because only
`create-spec-pr.sh` and `post-issue-comment.sh` have confirmed issues today.

**Independent Test**: For each script identified during the audit: (a) for scripts making external network calls, introduce a simulated failure for the primary external call (e.g., `gh`, `curl`,
external process) and verify the script exits non-zero; (b) for pure local scripts, introduce an internal error condition (e.g., invalid input, missing required variable) and verify the script exits
non-zero rather than masking the failure.

**Scope Clarification**: Only scripts making external network calls (`gh`, `curl`, or similar) require retry logic. Pure local scripts (`sanitize-branch-name.sh`, `validate-label.sh`,
`check-idempotency.sh`) must still be audited for proper exit-code propagation but do NOT need retry logic since their failures are deterministic and not transient.

**Acceptance Scenarios**:

1. **Given** the set of SpecKit pipeline shell scripts under `.github/scripts/speckit-trigger/` that make external network calls (excluding test harnesses and helper wrappers), **When** each script's
   primary external command is stubbed to fail, **Then** no script exits with code 0 on failure unless the failure is explicitly documented as non-fatal (e.g., optional label application).
2. **Given** the set of pure local SpecKit pipeline shell scripts under `.github/scripts/speckit-trigger/` (e.g., `sanitize-branch-name.sh`, `validate-label.sh`, `check-idempotency.sh`; excluding test
   harnesses and helper wrappers), **When** an internal error condition is introduced (e.g., invalid input, missing required environment variable), **Then** each script exits with a non-zero exit
   code rather than silently succeeding.
3. **Given** a script that already uses `call_with_retry` inline (e.g., `generate-spec-from-issue.sh`), **When** the shared library from User Story 3 is available, **Then** the script is migrated to
   source the shared library with no behavioural change except for enhanced retry error messages (now including the failing command name and exit code per FR-010), consistent with User Story 3
   scenario 3.

---

### Edge Cases

- **What happens when the GitHub API rate-limits the caller (HTTP 429 or 403 with `Retry-After` header)?** The retry logic should respect the `Retry-After` header when present, using the maximum of
  the `Retry-After` value and the calculated exponential backoff delay. If `Retry-After` exceeds 60 seconds, the script fails immediately per NFR-002. Both 429 (primary rate limit) and 403 with
  `Retry-After` (secondary rate limit) are treated as retryable rate-limit responses.
- **What happens when the GitHub API returns HTTP 429 without a `Retry-After` header?** The response is still retryable — 429 is always treated as a rate-limit response per FR-006. The script
  retries using only the calculated exponential backoff delay (since no `Retry-After` value is available to take the maximum of).
- **What happens when the GitHub API returns HTTP 403 without a `Retry-After` header?** This is a plain forbidden/client error, NOT a rate-limit response. Per FR-006, 403 is only retryable when
  accompanied by a `Retry-After` header (indicating a secondary rate-limit). Without the header, 403 is treated as a non-retryable client error and the script fails immediately.
- **What happens when `gh` CLI is not installed or not authenticated?** The script should fail immediately on the first attempt (authentication errors are not transient) rather than retrying.
  A missing `gh` binary is detected via exit code 127 or the "command not found" pattern in stderr. Authentication failures are detected via the non-retryable pattern list
  ("authentication", "permission denied", "not found", "does not exist", "command not found").
- **What happens when `GITHUB_OUTPUT` is unset (e.g., running outside GitHub Actions)?** The existing fallback to `/dev/stdout` must be preserved; error handling changes must not break local testing.
- **What happens when the network is completely unavailable (DNS failure)?** The retry mechanism should still apply — DNS failures are transient. All attempts should be exhausted before failing.
- **What happens when `curl` receives a redirect (3xx)?** Redirects should be followed while preserving POST semantics (using
  `curl -L --post301 --post302 --post303`). Only final response codes should be evaluated for success/failure.
- **What happens when `gh pr create` reports "already exists"?** This is an ambiguous outcome: the PR may have been created on a previous attempt that timed out client-side. The script
  MUST NOT treat this as a non-retryable failure. Instead, it attempts to recover the existing PR URL and number (via `gh pr list --head <branch> --json url,number`), using `call_with_retry`
  for the recovery lookup to handle transient network failures during recovery. If recovery succeeds,
  the script exits 0 with both `pr_url` and `pr_number` populated in `GITHUB_OUTPUT`. If no matching PR is found after exhausting retries, the script writes empty values
  (`pr_url=` and `pr_number=`) to `GITHUB_OUTPUT` per NFR-005 and exits with a non-zero exit code. This ensures the resilient
  retry path does not discard a successfully-created PR.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `create-spec-pr.sh` MUST exit with a non-zero exit code when `gh pr create` fails after all retry attempts are exhausted.
- **FR-002**: `create-spec-pr.sh` MUST retry the `gh pr create` command with exponential backoff on transient failures (non-zero exit code from `gh` indicative of
  network or server errors). Non-retryable failures — such as missing `gh` binary (command not found) or authentication errors — MUST cause immediate
  failure without retry. Non-retryable failures are detected via two mechanisms:
  1. **Exit code 127** (shell "command not found"): If the subshell exits with code 127, the `gh` binary is missing and the script MUST fail immediately without retry.
  2. **Stderr pattern matching**: The combined stderr output (from both the shell and `gh`) is inspected for known non-retryable patterns: "not found",
     "does not exist", "permission denied", "authentication", "command not found". Matching any pattern causes immediate failure without retry.
     Note: "already exists" is intentionally excluded — see FR-013 for the ambiguous-success recovery path.

  All other non-zero exits are treated as retryable (safe default). This means some validation errors whose stderr messages do not match the known patterns will be retried
  rather than failing immediately; the pattern list can be extended over time as new non-retryable messages are identified.
- **FR-003**: `post-issue-comment.sh` MUST capture and inspect the HTTP response status code from the `curl` call.
- **FR-004**: `post-issue-comment.sh` MUST exit with a non-zero exit code when the HTTP response status is not in the 2xx range after applying the retry rules
  defined in FR-005 and FR-006 (i.e., after exhausting retries for retryable errors, or immediately for non-retryable errors). This requirement also applies to transport-level
  `curl` failures (e.g., DNS resolution failure, connection refused, timeout) where no HTTP status is available: after exhausting retries for such failures, the script MUST exit
  with a non-zero exit code.
- **FR-005**: `post-issue-comment.sh` MUST retry `curl` calls on transient server errors (HTTP 5xx) and network/transport errors with exponential backoff. The retry logic MUST be implemented via an
  HTTP-aware wrapper function (`curl_with_retry`) that manages its own retry decisions based on two failure modes:
  1. **HTTP status codes**: When `curl` succeeds at the transport level (exit code 0) but the server returns a retryable status (5xx), the wrapper retries.
  2. **Transport errors**: When `curl` exits with a non-zero exit code matching a known transient transport failure, the wrapper retries — no HTTP status is available in this case.
     Only the following `curl` exit codes are retryable (all others cause immediate failure):
     - **6** — DNS resolution failure
     - **7** — Connection refused
     - **28** — Operation timeout
     - **35** — TLS/SSL handshake failure (transient negotiation error)
     - **52** — Empty reply from server
     - **56** — Network data receive failure

     Any other non-zero `curl` exit code (e.g., exit code 3 for malformed URL, exit code 60 for certificate verification failure) indicates a deterministic
     local or configuration error and MUST cause immediate failure without retry.

  The wrapper uses the shared library's `calculate_backoff_delay` function for consistent delay computation.
- **FR-006**: `post-issue-comment.sh` MUST NOT retry on client errors (HTTP 4xx) except for 429 (rate limit) and 403 when accompanied by a `Retry-After` header (secondary rate-limit response). For
  rate-limited responses, the sleep duration MUST be the maximum of the `Retry-After` header value and the calculated exponential backoff delay.
- **FR-007**: A shared shell library file MUST be created at `.github/scripts/speckit-trigger/lib/retry.sh` containing the `call_with_retry` function and a `calculate_backoff_delay` helper function,
  sourceable by all SpecKit pipeline
  scripts. Consuming scripts MUST source it relative to their own directory via `BASH_SOURCE[0]` to ensure reliable sourcing from any working directory.
- **FR-008**: `generate-spec-from-issue.sh` MUST be updated to source the shared retry library instead of defining `call_with_retry` inline.
- **FR-009**: The retry mechanism MUST log each retry attempt number, total attempts, and delay to stderr for observability in GitHub Actions logs.
- **FR-010**: All retry-related error messages MUST include the failing command name and the exit code or HTTP status code for diagnostics.
- **FR-011**: `post-issue-comment.sh` MUST follow HTTP redirects while preserving POST semantics (using `curl -L --post301 --post302 --post303`) and evaluate only the final
  response status code for success/failure classification.
- **FR-012**: `create-spec-pr.sh` MUST source the shared retry library (`.github/scripts/speckit-trigger/lib/retry.sh`) and use its `call_with_retry` function for retry logic, ensuring
  consistent exponential backoff behaviour across all SpecKit scripts. This eliminates the risk of `create-spec-pr.sh` implementing a divergent retry schedule.
- **FR-013**: `create-spec-pr.sh` MUST treat an "already exists" error from `gh pr create` as an ambiguous success rather than a non-retryable failure. When stderr contains "already exists",
  the script MUST attempt to recover the existing PR URL by querying for an open PR on the same head branch (e.g., via `gh pr list --head <branch> --json url,number --jq '.[0]'`). The recovery
  lookup MUST itself use `call_with_retry` (from the shared library) to handle the case where the network is still flaky at recovery time — without retry, a transient failure during recovery
  would discard a PR that was actually created. If recovery succeeds (a matching PR is found after retries),
  the script sets `pr_url` / `pr_number` in `GITHUB_OUTPUT` and exits 0. If recovery fails after exhausting retries (no matching PR found or persistent network failure), the script MUST still
  write empty values (`pr_url=` and `pr_number=`) to `GITHUB_OUTPUT` — preserving the keys' presence per NFR-005 — before exiting with a non-zero exit code. This handles the case where
  `gh pr create` succeeds server-side but the client times out before receiving the response, causing a subsequent retry to report "already exists".

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

- **Shared Retry Library** (`.github/scripts/speckit-trigger/lib/retry.sh`): A sourceable shell file exporting the `call_with_retry` function and `calculate_backoff_delay` helper with configurable max
  attempts, initial delay, and exponential backoff. The `calculate_backoff_delay` function accepts a retry number (1-based, where retry 1 is the first retry after the initial attempt fails) and
  initial delay, returning the computed delay (`initial_delay × 2^(retry_number-1)`). For the default configuration (initial_delay=5): retry 1 → 5s, retry 2 → 10s, matching NFR-001's delay
  sequence. Scripts MUST source this library relative to their own directory using `BASH_SOURCE[0]` (e.g.,
  `SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; source "$SCRIPT_DIR/lib/retry.sh"`) so that sourcing works reliably regardless of the caller's working directory.
- **HTTP Response Validator**: Logic within `post-issue-comment.sh` implemented as a `curl_with_retry` wrapper function that handles two failure modes: (1) HTTP status classification — evaluates
  response status codes as success (2xx), transient/retryable (5xx, 429, 403 with `Retry-After`), or permanent failure (other 4xx); (2) transport-level failures — when `curl` exits with a non-zero
  exit code from the retryable set (exit codes 6, 7, 28, 35, 52, 56 — see FR-005) without producing an HTTP status, the wrapper treats the failure as a retryable
  transient error. Any other non-zero `curl` exit code (e.g., 3 for malformed URL, 60 for certificate verification failure) causes immediate failure without retry.
  This wrapper uses `calculate_backoff_delay` from the shared library for consistent delay computation across both failure modes.
- **Non-Retryable Pattern List**: A set of stderr patterns used by `create-spec-pr.sh` to identify non-retryable failures: "not found", "does not exist", "permission denied",
  "authentication", "command not found". Matching any pattern in the combined stderr output causes immediate failure without retry. Additionally, exit code 127 (shell "command not found")
  triggers immediate failure regardless of stderr content. Note: "already exists" is intentionally excluded from this list because it may indicate an ambiguous success (see FR-013).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: When `gh pr create` returns a non-zero exit code **and** the failure is non-recoverable (retries exhausted or a non-retryable pattern detected), the `create-spec-pr.sh` step in
  GitHub Actions is reported as **failed** (not succeeded) — verified by CI run logs. This excludes the FR-013 recovery path where "already exists" leads to a successful PR URL lookup and exit 0.
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
