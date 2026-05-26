# Feature Specification: Gate Review Requests on Unresolved PR Comment Threads

**Feature Branch**: `speckit/1566/phase-1-specify`  
**Created**: 2026-05-25  
**Status**: Draft  
**Input**: User description: "ai-pr-loop requests PR review before all prior review comments are resolved"  
**Source Issue**: #1566 (<https://github.com/ayaiayorg/agentic-devtools/issues/1566>)

---

## Problem Statement

The ai-pr-loop orchestrator currently requests new Copilot reviews and proceeds toward approval/merge without verifying that all prior review comments have been resolved. This allows the automation to
bypass review safeguards — a reviewer may leave feedback that is never addressed before the PR is merged.

On PR #1545, the automation requested a fresh Copilot review while multiple review comment threads from the prior review cycle remained unresolved. This violated the expected safeguard that all
feedback must be addressed before the next review cycle begins, creating a path where PRs can be approved and auto-merged with unaddressed review feedback still outstanding.

The root cause is that the orchestrator's `_request_copilot_review_if_needed` function is invoked at three separate control-flow paths — after draft-publish (line 1535), after CI-completion with no
actionable review (line 1390), and in the main Step 7b "no effective review" path (line 1560) — and none of these paths include a precondition check for unresolved review comment threads. The
function's existing skip-reason logic (`_get_copilot_review_request_skip_reason`) checks only for pending Copilot review requests and the "no reviewable files" sentinel, not for outstanding feedback threads.

The desired behavior is that the orchestrator must query the PR's review comment threads and confirm that zero unresolved threads exist before requesting a new review. If unresolved threads remain,
the orchestrator should skip the review request, log the reason with the unresolved count, include the count in the decision summary, and return a non-error exit code so the loop can retry on the next
trigger. This ensures that review requests are only issued when all prior feedback has been addressed, maintaining the integrity of the review-gate safeguard.

---

## User Scenarios & Testing

### User Story 1 - Block Review Request When Unresolved Comments Exist (Priority: P1)

As the ai-pr-loop automation, I must not request a new Copilot review when there are unresolved review comment threads on the PR, so that all prior feedback is addressed before a fresh review cycle
begins. This is the fundamental correctness fix that prevents the observed bug on PR #1545. Without this gate, the entire review safeguard is meaningless because the loop can request new reviews (and
subsequently approve/merge) while ignoring prior feedback.

**Why this priority**: This is the core bug fix. Without this gate, the entire review safeguard is bypassed and PRs can be merged with unaddressed feedback. Every other user story depends on this gate
existing.

**Independent Test**: Can be fully tested by simulating a PR with unresolved review threads and verifying the orchestrator returns a "waiting" decision instead of calling
`provider.request_reviewer()`. Delivers immediate value by preventing the exact bug observed on PR #1545.

**Acceptance Scenarios**:

1. **Given** a PR with 3 unresolved Copilot review comment threads from a prior review, **When** the orchestrator reaches the review-request decision point (Step 7b — no effective review on HEAD),
   **Then** it must NOT call `provider.request_reviewer()` and must return a decision of `"awaiting_thread_resolution"` with `"unresolved_threads": 3` in the summary.

2. **Given** a PR with unresolved review comment threads and CI passing (CI-completion event, the line-1390 path), **When** the orchestrator would normally request a Copilot review after CI passes
   with no actionable review on HEAD, **Then** it must NOT request the review and must return `"awaiting_thread_resolution"`.

3. **Given** a PR where all prior review comment threads have been resolved (all threads marked resolved via GitHub UI or API), **When** the orchestrator reaches any review-request decision point,
   **Then** it must proceed normally and request a Copilot review as it does today.

4. **Given** a PR that has never had a Copilot review (no prior threads exist — fresh PR), **When** the orchestrator reaches the review-request decision point, **Then** it must proceed normally (zero
   unresolved threads means the gate passes trivially).

---

### User Story 2 - Include Unresolved Thread Count in Decision Summary (Priority: P2)

As a developer inspecting the ai-pr-loop decision logs or GitHub Actions workflow summary, I want to see the count of unresolved review threads in the structured decision summary JSON so that I can
understand why a review request was blocked and how many threads remain to be resolved. This observability is critical for debugging the automation when it appears "stuck" — without a clear unresolved
count, operators have to manually inspect the PR timeline to understand what is blocking progress.

**Why this priority**: Observability is essential for debugging automation behavior in production, but is secondary to the correctness fix itself. The gate must work correctly first; knowing *why* it
blocked is a close second.

**Independent Test**: Can be tested independently by examining the JSON decision summary output (logged to stdout and captured by GitHub Actions) when the gate blocks a review request, verifying the
expected `unresolved_threads` and `decision` fields are present with correct values.

**Acceptance Scenarios**:

1. **Given** a PR with 5 unresolved threads where the gate blocks the review request, **When** the decision summary JSON is emitted at the end of the orchestrator run, **Then** it must contain
   `"unresolved_threads": 5` and `"decision": "awaiting_thread_resolution"`.

2. **Given** a PR with 0 unresolved threads where the gate passes and a review is requested normally, **When** the decision summary JSON is emitted, **Then** the `"unresolved_threads"` field must be
   `0` and the decision must reflect the normal flow (e.g., `"awaiting_copilot_review"`).

3. **Given** a PR where the thread-listing API fails and the gate fails closed, **When** the decision summary is emitted, **Then** it must contain `"unresolved_threads_error": true` and `"decision":
   "awaiting_thread_resolution"` so operators can distinguish API failures from genuine unresolved threads.

---

### User Story 3 - Gate Applies Consistently to All Three Review Request Paths (Priority: P1)

As the ai-pr-loop automation, I must enforce the unresolved-comments gate on every code path that requests a Copilot review. There are exactly three such paths in the orchestrator: (1) after
draft-publish at line 1535, (2) after CI-completion with no actionable review at line 1390, and (3) in the main Step 7b "no effective review" path at line 1560. The gate must apply identically on all
three paths to prevent any bypass route.

**Why this priority**: Equal priority to User Story 1 because partial coverage reintroduces the bug. If even one path is missed, the exact scenario from PR #1545 can recur through that unguarded path.

**Independent Test**: Can be tested by triggering each of the three review-request code paths independently (via appropriate event payload construction) and verifying that each one checks unresolved
threads before proceeding. Each path can be tested in isolation.

**Acceptance Scenarios**:

1. **Given** a draft PR being published where unresolved threads exist from a prior review (the line-1535 path after `provider.publish_pr()`), **When** the orchestrator publishes the PR and would
   request a review, **Then** it must check unresolved threads, block the review request, and return `"awaiting_thread_resolution"`.
2. **Given** a CI-completion event where CI passes, no actionable review exists on HEAD, and unresolved threads remain (the line-1390 path), **When** the orchestrator reaches the "request review after
   CI" logic, **Then** it must block the review request and return `"awaiting_thread_resolution"`.

3. **Given** a non-draft PR with no effective Copilot review on HEAD and unresolved threads from a stale review (the line-1560 Step 7b path), **When** the orchestrator reaches the "no effective
   review" decision point, **Then** it must block the review request and return `"awaiting_thread_resolution"`.

---

### User Story 4 - Graceful Degradation on Thread API Failure (Priority: P2)

As the ai-pr-loop automation, if I cannot determine the resolution status of review threads due to a GitHub API error or timeout, I must fail closed (assume unresolved threads exist) to prevent
premature review requests. This is a safety-critical design choice: in the presence of uncertainty about thread resolution state, the safer action is to wait rather than potentially allow a review
request that bypasses unaddressed feedback.

**Why this priority**: Fail-closed behavior is critical for safety but is a secondary concern to the happy-path gate logic. API failures are uncommon in production, but when they occur, the automation
must not degrade into an unsafe state.

**Independent Test**: Can be tested by mocking the GitHub thread-listing API call to raise various exceptions (network timeout, 500 server error, 403 rate limit) and verifying the orchestrator blocks
the review request in each case.

**Acceptance Scenarios**:

1. **Given** a PR where the API call to list review comment threads raises a network timeout exception, **When** the orchestrator attempts to check unresolved threads, **Then** it must treat the PR as
   having unresolved threads (fail closed), log a warning with the exception details, and block the review request.

2. **Given** a PR where the API call to list review comment threads returns a 500 Internal Server Error, **When** the orchestrator attempts to check unresolved threads, **Then** it must fail closed,
   include `"unresolved_threads_error": true` in the decision summary, and return `EXIT_SUCCESS` (so the loop retries on the next trigger).

3. **Given** a PR where the API returns an empty list (no threads exist at all — fresh PR with no prior reviews), **When** the orchestrator checks unresolved threads, **Then** it must proceed normally
   (gate passes — zero threads means nothing is unresolved).

---

### Edge Cases

- What happens when all threads are resolved but a new commit is pushed before the review is requested? The gate should still pass because resolved threads remain resolved regardless of new commits.
  The gate checks thread resolution state, not commit recency.
- What happens when threads belong to non-Copilot reviewers (e.g., human reviewers or other bots)? The gate should check ALL unresolved review comment threads, not just Copilot-authored ones, to
  ensure comprehensive review integrity and prevent scenarios where human feedback is ignored.
- What happens when a thread is marked "outdated" by GitHub (because the file/line changed) but not explicitly resolved? Outdated threads that are not resolved should still count as unresolved. Only
  explicit resolution (via the resolve API or UI toggle) clears a thread from the gate.
- How does this interact with the existing `finalize_post_repair` evaluator flow that resolves threads? The evaluator's thread resolution runs *after* a repair agent addresses feedback. The gate runs
  *before* requesting a new review. These are complementary: the evaluator resolves threads, then on the next loop trigger the gate sees zero unresolved threads and allows the review request.
- What if a PR has hundreds of threads? The thread-listing API call should paginate properly (e.g., via GitHub's GraphQL `reviewThreads` connection). The gate counts all unresolved threads regardless of
  quantity — there is no threshold; even 1 unresolved thread blocks.

---

## Requirements

### Functional Requirements

- **FR-001**: The orchestrator MUST check for unresolved PR review comment threads before requesting a new Copilot review on any code path. This check must occur inside or immediately before the
  `_request_copilot_review_if_needed` function, so that all callers benefit from the gate automatically.

- **FR-002**: The orchestrator MUST NOT request a Copilot review (must not call `provider.request_reviewer()`) when one or more review comment threads on the PR remain in an unresolved state.

- **FR-003**: The orchestrator MUST return a distinct decision value (`"awaiting_thread_resolution"`) when the unresolved-comments gate blocks a review request, distinguishing this state from other
  skip reasons like `"copilot_already_requested"` or `"copilot_no_reviewable_files"`.

- **FR-004**: The orchestrator MUST include the count of unresolved threads (`"unresolved_threads": N`) in the decision summary JSON (use `0` when none).
  If the thread-listing API fails, it MUST include `"unresolved_threads_error": true`, enabling automated monitoring, alerting, and human debugging.
- **FR-005**: The orchestrator MUST apply the unresolved-comments gate consistently across all three review-request paths: Step 7a draft-publish path (line 1535), CI-completion path with no actionable
  review (line 1390), and Step 7b no-effective-review path (line 1560).

- **FR-006**: The orchestrator MUST fail closed (block the review request and treat the PR as having unresolved threads) when the API call to determine thread resolution status fails for any reason
  (network error, HTTP error, rate limit, timeout).

- **FR-007**: The orchestrator MUST consider threads from ALL reviewers (not just Copilot-authored threads) when evaluating the unresolved-comments gate, ensuring that human reviewer feedback cannot
  be bypassed by the automation.

- **FR-008**: The orchestrator MUST return `EXIT_SUCCESS` (exit code 0) when the gate blocks a review request, so that the loop can re-evaluate on the next trigger rather than failing permanently.
  This is consistent with other "waiting" decisions in the orchestrator.

### Non-Functional Requirements

- **NFR-001**: The unresolved-thread check MUST add no more than one additional GitHub thread-listing operation per orchestrator run (the underlying API may paginate). Where possible, the thread data
  should be fetched once and reused across all three gate check points within the same run.

- **NFR-002**: Decision summary output MUST remain backward-compatible. The new `"unresolved_threads"` and `"unresolved_threads_error"` fields are additive; no existing fields in the summary schema
  are removed, renamed, or have their semantics changed.

- **NFR-003**: The gate check MUST complete within the existing orchestrator timeout constraints. The thread-listing API call must not introduce unbounded retries or waits. A single attempt with the
  existing HTTP timeout is sufficient.

- **NFR-004**: All new logic MUST be covered by unit tests following the project's 1:1:1 test structure policy, achieving 100% line coverage for new code.

### Key Entities

- **Review Comment Thread**: A GitHub PR review thread (GraphQL `PullRequestReviewThread`) with an `isResolved` boolean state. (REST “review comments” are individual comments and do not expose thread resolution status.) Threads are identified
  by node ID and associated with a specific review and PR.
- **Unresolved-Comments Gate**: A precondition check applied inside (or immediately before) `_request_copilot_review_if_needed` that evaluates whether all review comment threads on the PR are
  resolved. Returns a skip reason string when the gate blocks.

- **Decision Summary**: The structured JSON object emitted via `_emit_decision_summary()` at the end of each orchestrator run. Contains fields like `decision`, `reason`, `exit_code`, and (with this
  feature) `unresolved_threads`.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of review-request paths (3 out of 3 call sites to `_request_copilot_review_if_needed`) are gated by the unresolved-thread check, verified by unit tests that exercise each path
  independently with unresolved threads present.

- **SC-002**: The structured decision summary contains an `"unresolved_threads"` integer field whenever the gate blocks, and this field accurately reflects the count returned by the GitHub API
  (verified by assertion in integration/unit tests against known thread states).

- **SC-003**: The regression scenario from PR #1545 (review requested despite 2+ unresolved comment threads) does not reproduce when replayed against the fixed orchestrator logic — verified by a
  dedicated regression test that simulates the exact PR #1545 timeline state.

- **SC-004**: No increase in orchestrator run time beyond 2 seconds additional latency attributable to the thread-listing API call (measured as p95 latency delta in CI workflow telemetry over 50+ runs).

- **SC-005**: All new code achieves 100% line coverage under the project's testing policy (e.g., `python3 scripts/check-pr-test-coverage.py` must pass, and the orchestrator tests in `tests/unit/cli/ci/orchestrator/` must cover all new logic).

---
*Generated by Copilot SDK (claude-opus-4.6)*
