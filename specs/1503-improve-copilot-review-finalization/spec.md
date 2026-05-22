# Feature Specification: Improve Copilot Review Finalization

**Feature Branch**: `speckit/1503/phase-2-clarify`
**Created**: 2026-05-21
**Status**: Draft
**Source Issue**: #1503 (<https://github.com/ayaiayorg/agentic-devtools/issues/1503>)

## Problem Statement

When the AI PR Loop runs after a Copilot review with actionable comments, the orchestrator
sometimes calls `finalize_post_repair()` — which replies to and resolves all review
threads — **before any new commit has been pushed**. This causes premature thread closure
when the underlying code was never updated. Additionally, finalization blindly resolves all
threads regardless of whether the diff actually addresses each comment, meaning threads can
be closed even when the feedback was never acted on.

The two root causes are:

1. No guard verifying that a fresh commit exists after the Copilot review before
   finalization begins.
2. No per-comment, SDK-driven verification that the diff genuinely addresses the
   original feedback before resolving the corresponding thread.

## Clarifications

### Session 2026-05-21

- Q: What is the exact reply text content to post when resolving a thread — a static
  message or a dynamically generated summary from the SDK response? → A: Use the
  existing static reply text already defined in the codebase:
  `Addressed on the updated PR branch.` (the `_ADDRESSED_REPLY_BODY` constant in
  `github_provider.py`). This maintains consistency with the current behavior and
  avoids introducing LLM-generated reply text that could be unpredictable or verbose.
- Q: Which LLM model/endpoint should be used for the `COMMENT_RESOLVE` /
  `COMMENT_UNRESOLVE` structured SDK call — the existing Copilot SDK model, a
  configurable model alias, or a hard-coded model name? → A: Use the existing
  Copilot SDK endpoint authenticated via `COPILOT_GITHUB_TOKEN`, consistent with the
  existing `_generate_commit_message_via_sdk` and
  `_resolve_conflicted_file_content_via_sdk` patterns in `github_provider.py`. No
  new model configuration is needed; the implementation follows the same token-based
  auth and endpoint pattern already established for other SDK calls in the provider.
- Q: What is the maximum diff context window to pass to the SDK call per comment
  (e.g., full diff, ±50 lines around the commented line, or a token budget)? → A:
  Use ±50 lines around the commented line(s) as the default context window. If the
  comment does not reference a specific line (e.g., a general PR-level comment),
  include the full PR diff (all changed files) up to a 4,000-token budget, using a
  deterministic truncation strategy (stable file order, then diff order) when the
  diff exceeds the budget. This balances sufficient context for accurate
  verification against token limits and latency.
- Q: How should the system handle a PR where the same comment appears across multiple
  reviews (duplicate feedback from separate Copilot review cycles)? → A: Process
  each comment independently based on its thread resolution status. If a comment's
  thread is already resolved (from a prior review cycle or manual resolution), skip
  it. Duplicate feedback across reviews is expected — the per-thread resolution
  status is the source of truth, not comment content deduplication.
- Q: What is the expected behavior when a thread was already manually resolved before
  finalization runs (idempotency guarantee)? → A: The system MUST check each thread's
  resolution status before attempting to resolve it. If already resolved, skip it
  silently (no error, no warning, no duplicate reply). This is the idempotency
  guarantee required by NFR-002.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Commit Change Guard (Priority: P1)

As a repository maintainer, I want finalization to be blocked unless a new commit has been
pushed since the Copilot review was posted, so that review threads are never closed on
unchanged code.

**Why this priority**: This is the minimum correctness guard. Without it, all downstream
verification is pointless because the code hasn't changed.

**Independent Test**: Can be tested by mocking a PR where `review.commit_sha` equals the
current HEAD SHA and verifying that `finalize_post_repair()` exits early without resolving
any threads.

**Applies to**: FR-001, FR-002, FR-014

**Acceptance Scenarios**:

1. **Given** the current HEAD SHA equals the commit SHA recorded on the Copilot review,
   **When** `finalize_post_repair()` is called, **Then** finalization is skipped and a
   warning is logged indicating no new commit was found.
2. **Given** the current HEAD SHA differs from the review's commit SHA, **When**
   `finalize_post_repair()` is called, **Then** finalization proceeds to the per-comment
   verification loop.
3. **Given** the review commit SHA cannot be retrieved (e.g., deleted review), **When**
   `finalize_post_repair()` is called, **Then** finalization is skipped and an error is
   logged (fail-safe: default to not resolving).

---

### User Story 2 - Per-Comment SDK Verification (Priority: P1)

As a repository maintainer, I want each unresolved Copilot review comment to be
individually verified against the diff via a Copilot SDK call before its thread is
resolved, so that only genuinely addressed feedback is closed.

**Why this priority**: This is the core correctness requirement. Per-comment verification
ensures review threads accurately reflect the PR's current state.

**Independent Test**: Can be tested by providing a PR with two unresolved comments where
the diff addresses one but not the other, and verifying that only the addressed thread is
resolved while the other remains open.

**Applies to**: FR-003, FR-004, FR-005, FR-006, FR-007, FR-008

**Acceptance Scenarios**:

1. **Given** an unresolved Copilot review comment and a diff that addresses it, **When**
   the SDK call returns `COMMENT_RESOLVE`, **Then** the thread is replied to with
   `_ADDRESSED_REPLY_BODY` (exact text: `Addressed on the updated PR branch.`) and
   resolved.
2. **Given** an unresolved Copilot review comment and a diff that does not address it,
   **When** the SDK call returns `COMMENT_UNRESOLVE`, **Then** the thread is left
   unresolved and no reply is posted.
3. **Given** a Copilot SDK call that fails (timeout, API error), **When** the error is
   caught, **Then** the thread is left unresolved and the error is logged (fail-safe
   default).
4. **Given** a structured SDK response that is neither `COMMENT_RESOLVE` nor
   `COMMENT_UNRESOLVE`, **When** the response is received, **Then** the thread is left
   unresolved and a warning is logged.

---

### User Story 3 - Multi-Review Processing (Priority: P2)

As a repository maintainer, I want all actionable Copilot reviews with unresolved comments
to be processed (not just the latest review), so that feedback from earlier review cycles
is not ignored.

**Why this priority**: Important for correctness in multi-iteration PR flows, but depends
on the P1 guard and per-comment verification stories being functional first.

**Independent Test**: Can be tested by setting up a PR with two separate Copilot reviews
each containing unresolved comments, and verifying that both reviews are processed
independently with correct per-comment resolution decisions.

**Applies to**: FR-009, FR-010

**Acceptance Scenarios**:

1. **Given** a PR with two Copilot reviews each containing unresolved comments, **When**
   finalization runs, **Then** comments from both reviews are evaluated for resolution.
2. **Given** a Copilot review with no unresolved comments, **When** finalization runs,
   **Then** that review is skipped without error.
3. **Given** only the latest review has unresolved comments, **When** finalization runs,
   **Then** only the latest review's comments are processed (no regressions from earlier
   resolved reviews).

---

### User Story 4 - Finalization Outcome Reporting (Priority: P3)

As a repository maintainer, I want a structured summary of the finalization run (how many
comments were resolved vs left unresolved, and why), so that I can audit decisions without
reading raw logs.

**Why this priority**: Useful for debugging and auditing, but the correctness stories
deliver value independently. Outcome reporting is additive.

**Independent Test**: Can be tested by verifying that the finalization function returns (or
logs) a structured result capturing resolved count, unresolved count, skipped count, and
any errors encountered.

**Applies to**: FR-011, FR-012, FR-013

**Acceptance Scenarios**:

1. **Given** finalization completes with a mix of resolved and unresolved threads, **When**
   the run ends, **Then** a structured summary is logged and/or returned, listing resolved
   thread IDs, unresolved thread IDs, skip reason (if guard fired), and any errors.
2. **Given** finalization was skipped due to the commit guard, **When** the run ends,
   **Then** the summary includes `skipped: true` and the reason.
3. **Given** `--dry-run` mode is active, **When** finalization runs, **Then** the summary
   reports what would have been resolved/left-open without actually calling resolve APIs.

---

### Edge Cases

- **Null/incomplete review commit SHA**: When `review.commit_sha` is `null` or the
  review record is incomplete, the system treats this as a fail-safe condition per
  FR-014 — finalization is skipped entirely and an error is logged at higher
  severity than the "no new commit" warning.
- **Duplicate comments across reviews**: Each comment is processed independently
  based on its thread resolution status. If a thread is already resolved (from a
  prior cycle or manual resolution), it is skipped silently per NFR-002.
- **Empty diff (force-push without content change)**: If the diff between `review.commit_sha`
  and HEAD is empty, the SDK call receives an empty diff context. The system does not
  assume a specific SDK output: it resolves only on explicit `COMMENT_RESOLVE` and leaves
  the thread unresolved for `COMMENT_UNRESOLVE`, unexpected responses, or SDK failures.
- **Unexpected SDK response fields**: Per FR-005, any response not exactly
  `COMMENT_RESOLVE` or `COMMENT_UNRESOLVE` is treated as `COMMENT_UNRESOLVE` with a
  warning logged.
- **GitHub API rate limiting mid-loop (HTTP 429)**: Per FR-008, the system stops
  processing remaining threads, leaves them unresolved, and includes them in the
  `FinalizationResult` errors list rather than retrying indefinitely.
- **Already-resolved threads (idempotency)**: Per NFR-002, the system checks each
  thread's resolution status before attempting to resolve it. Already-resolved
  threads are skipped silently — no error, no warning, no duplicate reply.
- **PR branch deleted or PR closed mid-finalization**: If a resolve API call fails
  because the PR is closed or branch deleted, the error is caught per FR-008 and the
  thread is left unresolved. The `FinalizationResult` records the error for that
  thread.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST compare `review.commit_sha` against the current HEAD SHA of the
  PR branch before entering the per-comment verification loop.
- **FR-002**: System MUST skip finalization (no replies, no resolves) and log a warning
  when `review.commit_sha` equals the current HEAD SHA.
- **FR-014**: System MUST treat a null, empty, or unresolvable `review.commit_sha` as a
  fail-safe condition: skip finalization entirely and log an error (higher severity than
  the warning in FR-002).
- **FR-003**: System MUST fetch the diff between `review.commit_sha` and the current HEAD
  SHA for each Copilot review being processed.
- **FR-004**: System MUST make a Copilot SDK call (authenticated via
  `COPILOT_GITHUB_TOKEN`, consistent with existing
  `_generate_commit_message_via_sdk` and `_resolve_conflicted_file_content_via_sdk`
  patterns) for each unresolved review comment, passing the original comment body and
  the relevant diff context (±50 lines around the commented line; full PR diff up to
  4,000 tokens for general PR-level comments, truncated deterministically in stable
  file/diff order when needed).
- **FR-005**: System MUST require the SDK response to be exactly `COMMENT_RESOLVE` or
  `COMMENT_UNRESOLVE`; any other response MUST be treated as `COMMENT_UNRESOLVE` and
  a warning MUST be logged recording the unexpected response value.
- **FR-006**: System MUST reply to and resolve a review thread only when the SDK returns
  `COMMENT_RESOLVE`. The reply text MUST be the static string
  `Addressed on the updated PR branch.` (matching the existing
  `_ADDRESSED_REPLY_BODY` constant).
- **FR-007**: System MUST leave a review thread unresolved when the SDK returns
  `COMMENT_UNRESOLVE` or when the SDK call fails.
- **FR-008**: System MUST handle SDK/API call failures gracefully: catch exceptions, log
  the error, and default to leaving the thread unresolved (fail-safe). For GitHub API
  rate-limit errors (HTTP 429), the system MUST leave all remaining unprocessed threads
  unresolved and include them in the `FinalizationResult` errors list rather than
  retrying indefinitely in a single run.
- **FR-009**: System MUST process all Copilot reviews on a PR that have unresolved
  comments, not only the most recent review.
- **FR-010**: System MUST skip reviews that have no unresolved actionable comments without
  error.
- **FR-011**: System MUST produce a structured finalization result capturing: resolved
  count, unresolved count, skipped flag, and any per-comment errors.
- **FR-012**: System MUST support a `--dry-run` mode that classifies each comment as
  resolve/unresolve and reports the result without executing any resolve API calls.
- **FR-013**: Existing tests for `finalize_post_repair` (e.g., `test_finalize_post_repair`
  in the test suite) MUST be updated to cover the commit guard and per-comment
  verification paths.

### Non-Functional Requirements

- **NFR-001**: The commit guard check MUST add no more than 500 ms of latency (one API
  call to fetch the current HEAD SHA).
- **NFR-002**: The per-comment verification loop MUST be idempotent: re-running
  finalization on an already-resolved thread MUST be a no-op (thread resolution
  status checked before any action; already-resolved threads skipped silently with
  no error, no warning, and no duplicate reply).
- **NFR-003**: All new logic MUST follow the existing `CIPlatformProvider` abstraction so
  that the verification loop is fully unit-testable with mocked API providers.
- **NFR-004**: The fail-safe default (leave thread unresolved on any unexpected condition)
  MUST be enforced at every error boundary in the verification loop.
- **NFR-005**: All new CLI-facing outputs and structured results MUST follow existing
  `agdt-*` command patterns (structured JSON, consistent key names).

### Key Entities

- **ReviewCommitSHA**: The commit SHA recorded on the Copilot review at the time it was
  posted; used by FR-001/FR-002/FR-014 as the guard reference point.
- **HeadSHA**: Current HEAD commit SHA of the PR branch; fetched once at the start of
  finalization.
- **UnresolvedComment**: A Copilot review comment whose thread is not yet resolved; the
  unit of work for the SDK verification loop.
- **VerificationPayload**: The input to the SDK call — the original comment body plus the
  relevant diff lines between ReviewCommitSHA and HeadSHA (±50 lines around
  commented line for line-anchored comments; full PR diff up to a 4,000-token
  budget for general PR-level comments, with deterministic truncation in stable
  file/diff order).
- **VerificationVerdict**: The structured SDK response — exactly `COMMENT_RESOLVE` or
  `COMMENT_UNRESOLVE`.
- **FinalizationResult**: Structured summary of the finalization run (resolved list,
  unresolved list, skipped flag, errors).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0% of review threads are resolved on a PR where no new commit has been
  pushed since the Copilot review — confirmed by the commit guard unit tests.
- **SC-002**: Only threads whose SDK verdict is `COMMENT_RESOLVE` are resolved — confirmed
  by integration tests covering both `COMMENT_RESOLVE` and `COMMENT_UNRESOLVE` paths.
- **SC-003**: All new and modified code paths (commit guard, diff fetch, SDK call loop,
  fail-safe handling) achieve 100% unit-test coverage.
- **SC-004**: All pre-existing `finalize_post_repair` tests continue to pass after the
  refactor (no regression).
- **SC-005**: `--dry-run` mode reports resolution decisions for a PR with 5 review
  comments in under 10 seconds (excluding SDK latency) without calling any resolve APIs.

---

*Phase 2 clarification for issue #1503, derived from the Phase 1 specification and
produced via Copilot SDK workflow automation.*
