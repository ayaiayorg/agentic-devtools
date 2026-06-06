# Feature Specification: PR review scaffolding 403 on cross-identity thread recovery — PATCH fails on comments authored by different user

> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace
> placeholder content with detailed, issue-specific information.

**Feature Branch**: `1915-review-scaffolding-403-cross`  
**Created**: 2026-06-06  
**Status**: Draft  
**Input**: User description: "PR review scaffolding 403 on cross-identity thread recovery — PATCH fails on comments authored by different user"  
**Source Issue**: #1915 (<https://github.com/ayaiayorg/agentic-devtools/issues/1915>)

## Problem Statement

When PR review scaffolding state is recovered from threads authored by a different identity,
the tool correctly reuses thread IDs but later fails to update those threads with `PATCH` due
to Azure DevOps ownership restrictions. This causes 403 failures during submission, breaks
structured review updates, and forces sessions to fall back to free-form comments.

## Description

During the duplicate Copilot session incident on PR #28407 (DFLYP-5279), neither session successfully used the structured PR review thread scaffolding. Both sessions posted free-form approval comments
directly to the PR instead.

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
   of editing the original comment.

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
   tool records local mark-reviewed state and emits an activity-log entry describing the blocked
   update.

2. **Given** blocked thread updates remain after fallback, **When** the workflow finalizes,
   **Then** a PR-level comment summarizes which thread updates were skipped and why.

### Edge Cases

- What happens when a recovered thread is deleted after state recovery but before submit?
  The update for that thread should be reported as skipped/not found, while other
  thread updates continue and completion output includes the skipped thread ID.

- How does the system handle a mixed-ownership batch where PATCH and reply both
  fail for only one thread? The batch should still finish for other updates and
  emit both an activity-log entry and PR-level summary for the blocked thread.

- What happens when recovery finds duplicate marker threads for the same file from
  multiple identities? The system should deterministically select one thread to
  reuse, avoid creating another scaffold thread, and report which duplicate thread
  IDs were ignored.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST recover and reuse existing scaffolding threads created by any reviewer identity when matching agdt markers are present.

- **FR-002**: When a recovered thread comment is authored by a different identity and
  cross-identity PATCH is rejected, the system MUST avoid editing the original comment
  and MUST post a reply-based update in that existing thread instead.

- **FR-003**: The system MUST treat 403 responses on recovered thread updates as expected cross-identity ownership constraints and continue the review flow without aborting the full submission.

- **FR-004**: The system MUST preserve thread de-duplication guarantees so that recovery does not create duplicate per-file, summary, or activity threads across sessions.

- **FR-005**: The system MUST record fallback activity in a way that keeps scaffold state
  consistent while using safe alternatives (for example, local mark-reviewed state plus new
  comments authored by the current identity).

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In test runs with recovered cross-identity scaffolding, 403 responses on thread
  PATCH do not abort submission (0 aborted batches across 20 runs).

- **SC-002**: For every cross-identity thread that rejects PATCH but allows replies, the system
  posts exactly one reply update and performs zero duplicate scaffold thread creations.

- **SC-003**: In mixed-ownership submission batches, same-identity thread updates complete even
  when at least one cross-identity update returns 403.

- **SC-004**: When both PATCH and reply are forbidden, each blocked update produces both an
  activity-log record and a PR-level summary entry of the skipped update reason.

---
*Generated via fallback skeleton — manual enrichment required*

---
*Generated by Copilot SDK (claude-opus-4.6)*
