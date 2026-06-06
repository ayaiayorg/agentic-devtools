# Feature Specification: PR review scaffolding 403 on cross-identity thread recovery — PATCH fails on comments authored by different user

> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace
> placeholder content with detailed, issue-specific information.

**Feature Branch**: `1915-review-scaffolding-403-cross`  
**Created**: 2026-06-06  
**Status**: Draft  
**Input**: User description: "PR review scaffolding 403 on cross-identity thread recovery — PATCH fails on comments authored by different user"  
**Source Issue**: #1915 (<https://github.com/ayaiayorg/agentic-devtools/issues/1915>)

## Clarifications

### Session 2026-06-06

- Q: Should the system proactively detect cross-identity ownership at recovery time (by comparing thread author to current PAT identity) and tag recovered threads as "cross-identity" in ReviewState,
  or should it rely solely on catching 403 responses at PATCH time? → A: The system should detect ownership at recovery time by comparing `comments[0].author.id` against the current authenticated
  identity as the primary comparator (falling back to `author.uniqueName` only if `author.id` is missing), fetched once via the Azure DevOps `_apis/connectionData` or profile endpoint. Recovered
  threads authored by a different identity should be tagged with `crossIdentity: true`
  in the `FileEntry` of `review-state.json`. This enables the reply-based update path to be selected proactively (avoiding the 403 round-trip), while still using 403 as a fallback signal for
  unexpected ownership mismatches.

- Q: When a reply-based update is posted instead of a PATCH, should the reply contain the full updated scaffold content (identical to what would have been PATCHed into the main comment), or a
  condensed delta/status-only message? → A: The reply should contain the full updated scaffold content (same markdown that would have been PATCHed). This preserves the same information density and
  keeps the most recent review status visible at the bottom of the thread. The reply should be prefixed with a short header line: `<!-- agdt-review:v1 type:{thread_type} mode:cross-identity-update -->`
  marker and `**[Updated by {current_identity}]**` so readers understand why a reply was used instead of an in-place edit.

- Q: For the duplicate marker thread edge case (same file, multiple identities created threads), which thread should be selected: the one authored by the current identity (enabling PATCH), or the
  chronologically earliest thread (preserving history)? → A: Prefer the thread authored by the current identity if one exists (enabling direct PATCH without fallback). If no thread is owned by the
  current identity, select the chronologically earliest thread (lowest thread ID). This deterministic selection rule should be applied during recovery and documented in the activity log entry that
  reports which duplicate thread IDs were ignored.

- Q: Should the 120-second NFR-001 timeout apply per-batch-submission or to the entire end-to-end scaffold-recovery-plus-submission workflow? → A: The 120-second limit applies to the batch submission
  phase only (the loop that iterates over thread updates and posts PATCH/reply operations). Recovery itself and cascade status derivation are separate phases with their own implicit timeouts
  (30-second per-request timeouts already enforced). This means a batch of N thread updates must complete all N operations (including retries and fallback attempts) within 120 seconds total.

- Q: When both PATCH and reply are forbidden (User Story 3), should the PR-level summary comment be a new standalone thread or appended to the existing activity-log thread? → A: The blocked-update
  summary should be appended as a reply to the existing activity-log thread (not a new standalone thread). This keeps all review session metadata in one place, avoids thread proliferation, and is
  consistent with how recovery events are already logged. The reply should include a structured list of blocked thread IDs, file paths, and the reason (e.g., "403 on PATCH and reply").

## Problem Statement

When PR review scaffolding state is recovered from threads authored by a different identity,
the tool correctly reuses thread IDs but later fails to update those threads with `PATCH` due
to Azure DevOps ownership restrictions. This causes 403 failures during submission, breaks
structured review updates, and forces sessions to fall back to free-form comments.

The current implementation in `_patch_comment_content` and `patch_comment` does not handle HTTP 403 responses from Azure DevOps, propagating ownership errors as
unhandled exceptions that abort the entire batch. While `patch_comment` already handles HTTP 429 (rate-limiting), no equivalent fallback path exists for cross-identity PATCH failures.

## Description

During the duplicate Copilot session incident on PR #28407 (DFLYP-5279), neither session successfully used the structured PR review thread scaffolding. Both sessions posted free-form approval comments
directly to the PR instead.

The `_try_recover_state_from_pr_threads` function in `review_scaffold.py` successfully recovers thread IDs from any identity but does not record authorship metadata. Downstream PATCH operations then
fail because Azure DevOps enforces that only the comment author (or project administrators) can edit a comment via PATCH.

## Root Cause Analysis

The scaffolding **was correctly recovered** from existing PR threads. The `_try_recover_state_from_pr_threads` function found 5 existing file threads, an overall summary, and an activity log that had
been created by a **different reviewer identity** (Okvist Nils Petter). The recovery code correctly:

1. Detected the agdt-marker threads from any identity
2. Reused their thread IDs (avoiding duplicate thread creation)
3. Reset all file entries to `UNREVIEWED` status
4. Posted a "State Recovered" activity log entry

However, both sessions then hit **403 Forbidden** when attempting to update the recovered threads via PATCH:

### Session 1 (Marsnik Albert Carl, pid=9296)

```text
all submissions are failing with 403 Forbidden errors when trying to post comment threads
to the Azure DevOps PR API. This is a permissions issue -- your Azure DevOps token doesn't
have write access to PR comment threads on this repository.
```

Session 1 fell back to `agdt-mark-file-reviewed` (local-only marking) and `agdt-add-pull-request-comment`.

### Session 2 (Marsnik Albert Carl, pid=30408)

```text
The batch submission failed with 403 Forbidden errors -- this is a permissions issue.
Your Azure DevOps account (Albert Carl Marsnik) appears to lack permission to update
some of the existing comment threads in this pull request.
```

Session 2 also fell back to non-scaffolded behavior after recovery succeeded but cross-identity PATCH operations were rejected.

### Technical Root Cause

The following code paths propagate 403 without fallback:

1. `helpers.py:patch_comment` — `response.raise_for_status()` raises `HTTPError` on 403
2. `review_scaffold.py:_patch_comment_content` — same pattern
3. `status_cascade.py:execute_cascade` — calls `patch_comment` without catching ownership errors
4. `file_review_commands.py` — thread closing in `_resolve_file_threads()` performs a direct
   `requests.patch(...).raise_for_status()` call, while other update paths route through
   `helpers.patch_comment()` / `helpers.patch_thread_status()` that currently handle 429 but
   still propagate 403 ownership errors without a cross-identity fallback path

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a reviewer resuming PR scaffolding created by another identity, I want submission to
complete without 403 aborts so that recovered thread state remains usable and the review can
finish in one pass.

**Why this priority**: This is the primary failure mode observed in production and blocks
structured review completion for cross-identity recoveries.

**Independent Test**: Can be fully tested by recovering scaffolding where at least one thread
was authored by another identity and verifying submission completes without fatal errors.

**Acceptance Scenarios**:

1. **Given** recovered per-file scaffolding threads authored by a different reviewer, **When**
   submit is executed, **Then** any 403 from cross-identity PATCH is handled and the batch
   continues.

2. **Given** a recovered thread where PATCH is forbidden but replying is allowed, **When** the
   tool updates review status, **Then** it posts a reply authored by the current identity instead
   of editing the original comment. The reply contains the full scaffold content prefixed with
   `<!-- agdt-review:v1 type:{thread_type} mode:cross-identity-update -->` and `**[Updated by {current_identity}]**`. Retry
   attempts for the same session/thread MUST be idempotent and MUST NOT create additional
   cross-identity update replies.

3. **Given** a thread authored by the current identity exists alongside a cross-identity thread
   for the same file, **When** recovery runs, **Then** the current-identity thread is preferred
   for reuse (enabling direct PATCH).

4. **Given** recovery processes multiple candidate threads in one session, **When** ownership
   detection runs, **Then** the authenticated identity is fetched once and reused from cache for
   all ownership comparisons in that session.

### User Story 2 - Error Recovery (Priority: P1)

As a reviewer submitting a mixed-ownership batch, I want one cross-identity 403 to affect only
the blocked update so that other files and summary/activity updates still complete.

**Why this priority**: Batch-level aborts are the main reason sessions fell back to free-form
behavior and lost scaffold continuity.

**Independent Test**: Can be tested with a batch containing both same-identity and
different-identity threads, confirming the same-identity updates still succeed when 403 occurs
for one thread.

**Acceptance Scenarios**:

1. **Given** a submission batch with five updates where one target thread rejects PATCH with 403,
   **When** the batch runs, **Then** the remaining four updates are still submitted and recorded.

2. **Given** a 403 on a recovered thread during batch submit, **When** fallback handling runs,
   **Then** the final result reports partial fallback details without marking the whole submission
   as failed.

### User Story 3 - Graceful Degradation (Priority: P2)

As a reviewer facing a thread where both PATCH and reply are forbidden, I want transparent
fallback artifacts so that review completion and auditability are preserved.

**Why this priority**: This ensures predictable behavior in restrictive permission setups without
silently losing review intent.

**Independent Test**: Can be tested by forcing both PATCH and reply APIs to return forbidden and
verifying local state + PR-level reporting still completes.

**Acceptance Scenarios**:

1. **Given** both PATCH and reply are forbidden for a thread, **When** submit runs, **Then** the
   tool records local mark-reviewed state and emits an activity-log reply describing the blocked
   update (appended to the existing activity-log thread).

2. **Given** blocked thread updates remain after fallback, **When** the workflow finalizes,
   **Then** a reply to the activity-log thread summarizes which thread updates were skipped and why,
   including thread IDs, file paths, and the failure reason.

### Edge Cases

- What happens when a recovered thread is deleted after state recovery but before submit?
  The update for that thread should be reported as skipped/not found (HTTP 404), while other
  thread updates continue and completion output includes the skipped thread ID.

- How does the system handle a mixed-ownership batch where PATCH and reply both
  fail for only one thread? The batch should still finish for other updates and
  emit both an activity-log reply entry and the blocked-thread summary for the affected thread.

- What happens when recovery finds duplicate marker threads for the same file from
  multiple identities? The system should prefer the thread authored by the current identity
  (enabling direct PATCH). If no current-identity thread exists, it selects the chronologically
  earliest thread (lowest thread ID). Ignored duplicate thread IDs are reported in the
  activity log entry.

- What happens if the identity-detection call itself fails (e.g., `_apis/connectionData` returns
  an error)? The system should fall back to the 403-catching behavior at PATCH time (no proactive
  tagging) and log a warning that ownership pre-detection was unavailable.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST recover and reuse existing scaffolding threads created by any reviewer identity when matching agdt markers are present.

- **FR-002**: When a recovered thread comment is authored by a different identity and
  cross-identity PATCH is rejected (or proactively detected via `crossIdentity: true` tagging),
  the system MUST avoid editing the original comment and MUST post a reply-based update in that
  existing thread instead. The reply MUST contain the full scaffold content prefixed with
  `<!-- agdt-review:v1 type:{thread_type} mode:cross-identity-update -->` marker and `**[Updated by {current_identity}]**` header.

- **FR-003**: The system MUST treat 403 responses on recovered thread updates as expected cross-identity ownership constraints and continue the review flow without aborting the full submission batch.
  Each thread update MUST be independent — a failure on one thread MUST NOT prevent other thread updates from executing.

- **FR-004**: The system MUST preserve thread de-duplication guarantees so that recovery does not create duplicate per-file, summary, or activity threads across sessions. When duplicate marker threads
  exist for the same file from multiple identities, the system MUST prefer the thread authored by the current identity (if available), otherwise select the chronologically earliest thread (lowest
  thread ID).

- **FR-005**: The system MUST record fallback activity in a way that keeps scaffold state
  consistent while using safe alternatives (for example, local mark-reviewed state plus new
  comments authored by the current identity). When both PATCH and reply are forbidden, blocked
  updates MUST be summarized as a reply to the activity-log thread.

- **FR-006**: At recovery time, the system MUST detect cross-identity ownership by comparing
  `comments[0].author.id` against the current authenticated identity as the primary comparator.
  If `author.id` is missing, the system MAY fall back to `author.uniqueName`. Recovered threads
  detected as cross-identity MUST be tagged with `crossIdentity: true` in the `FileEntry` of
  `review-state.json`. If identity detection fails, the system MUST fall back to 403-based
  detection at PATCH time.

- **FR-007**: The system MUST fetch the current authenticated identity once per session (via
  Azure DevOps `_apis/connectionData` or equivalent endpoint) and cache it for use in ownership
  comparison during recovery.

### Non-Functional Requirements

- **NFR-001**: The batch submission phase (iterating over all thread updates including retries and fallback attempts) MUST complete within 120 seconds under normal conditions. The baseline budget is
  ≤50 file threads × typical ≤2 API calls per thread update × average Azure DevOps API latency ≤1.0s per request (≤100s), leaving ≥20 seconds of headroom for limited retries/fallback attempts.
  Recovery and cascade derivation phases have independent per-request timeouts of 30 seconds.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts. Specifically: (a) `review-state.json` schema additions (`crossIdentity` field) MUST be
  optional/nullable so existing state files remain valid, (b) the `patch_comment` and `_patch_comment_content` function signatures MUST not change in a breaking way, and (c) existing callers that do
  not encounter cross-identity threads MUST experience no behavioral change.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In test runs with recovered cross-identity scaffolding, 403 responses on thread
  PATCH do not abort submission (0 aborted batches across 20 runs).

- **SC-002**: For every cross-identity thread that rejects PATCH but allows replies, the system
  posts exactly one reply update and performs zero duplicate scaffold thread creations.

- **SC-003**: In mixed-ownership submission batches, same-identity thread updates complete even
  when at least one cross-identity update returns 403.

- **SC-004**: When both PATCH and reply are forbidden, each blocked update produces an
  activity-log reply entry containing the blocked thread ID, file path, and failure reason.

- **SC-005**: Proactive ownership detection correctly tags ≥95% of cross-identity threads at
  recovery time (measured by comparing `crossIdentity` tags against actual 403 occurrences in
  integration tests).

- **SC-006**: Within a single recovery/submit session, ownership detection performs exactly one
  authenticated-identity fetch call and reuses cached identity data for all thread author
  comparisons.

---
*Generated via fallback skeleton — manual enrichment required*

---
*Generated by Copilot SDK (claude-opus-4.6)*
