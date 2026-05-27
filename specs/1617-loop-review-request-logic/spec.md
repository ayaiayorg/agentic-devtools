# Feature Specification: AI PR Loop Review Request Guards and Squash-First Review Strategy

**Feature Branch**: `1617-ai-pr-loop-review-request-guards`  
**Created**: 2026-05-27  
**Status**: Draft  
**Input**: GitHub Issue #1617  
**Source Issue**: #1617 (<https://github.com/ayaiayorg/agentic-devtools/issues/1617>)

## Problem Statement

The ai-pr-loop orchestrator has logic errors in its review request and merge pathways:

1. **Review requests fire during repair dispatch** — When a repair (Copilot agent fix pass) has just been dispatched or is actively in progress, the orchestrator may still request a new Copilot
   review. This triggers duplicate or premature reviews that conflict with the repair cycle.

2. **Review requests fire when unresolved comments exist** — If prior review comments remain unresolved/actionable, requesting a fresh review is premature and can defeat approval safety gates.

3. **Squash is not used as the primary review trigger for multi-commit PRs** — For PRs with >1 commit, the force-push from a squash naturally triggers a new Copilot review via GitHub's `push` event.
   The current code requests review directly via the API without first attempting the squash path, leading to reviews against non-squashed history.

4. **Squash is blocked by pending reviews** — The current `SquashAction` defers when `copilot_review_pending` is true, but per the issue, squash should only be blocked by an active coding/repair
   session, not by a pending review.

5. **Merge always uses "rebase" strategy** — The `MergeAction` unconditionally merges via rebase. When a PR still has multiple commits at merge time (e.g., squash failed or was skipped), it should use
   squash merge instead of rebase to maintain clean linear history.

## User Scenarios & Testing

### User Story 1 - Review Request Blocked During Active Repair (Priority: P1)

As a repository maintainer relying on the ai-pr-loop automation, I want review requests to be suppressed when a repair cycle is active or was just dispatched, so that the Copilot reviewer is not asked
to review code that is about to change.

**Why this priority**: This is the most impactful bug — triggering reviews during repairs creates noise, wastes Copilot API quota, and can cause race conditions where a review arrives on stale code
that the repair agent is about to overwrite.

**Independent Test**: Can be tested by simulating a repair dispatch event and verifying that subsequent `request_review` evaluations return SKIP with a "repair active" reason.

**Acceptance Scenarios**:

1. **Given** a PR where the orchestrator has just dispatched a repair (exit code = EXIT_REPAIR_DISPATCHED), **When** the review request logic is evaluated, **Then** no Copilot review request is sent
   and the decision summary includes `"reason": "repair_dispatched"`.

2. **Given** a PR with an active Copilot session (detected via squash-wait marker or events API showing session in progress), **When** the `RequestReviewAction.evaluate()` is called, **Then** it
   returns `ActionDecision.SKIP` with details indicating repair/session is active.

3. **Given** a PR where a repair was dispatched in a prior run and the repair agent has not yet pushed new code, **When** the ai-pr-loop is re-triggered (e.g., by a workflow_run event), **Then** the
   review request is suppressed until the repair cycle produces a new HEAD SHA.

---

### User Story 2 - Review Request Blocked When Unresolved Comments Exist (Priority: P1)

As a repository maintainer, I want review requests to be blocked when there are unresolved or actionable review comments on the PR, so that authors address existing feedback before requesting fresh
reviews.

**Why this priority**: Requesting a new review while prior feedback is unresolved defeats the safety gate model — reviewers expect all prior comments to be addressed before re-review.

**Independent Test**: Can be tested by configuring a PR snapshot with unresolved review threads or actionable inline comments and verifying `RequestReviewAction` returns SKIP.

**Acceptance Scenarios**:

1. **Given** a PR with 2 unresolved review comment threads from a previous Copilot review, **When** `RequestReviewAction.evaluate()` is called, **Then** it returns `ActionDecision.SKIP` with details
   "Unresolved review comments exist".

2. **Given** a PR where all prior review comments have been resolved (0 unresolved threads), **When** `RequestReviewAction.evaluate()` is called and other preconditions are met, **Then** it returns
   `ActionDecision.EXECUTE`.

3. **Given** a PR with unresolved comments from a non-Copilot human reviewer, **When** `RequestReviewAction.evaluate()` is called, **Then** it returns `ActionDecision.SKIP` (any unresolved comment
   blocks new review requests).

---

### User Story 3 - Squash-First Review Trigger for Multi-Commit PRs (Priority: P2)

As a repository maintainer, I want the ai-pr-loop to squash multi-commit PRs before requesting a Copilot review, so that the force-push from squash naturally triggers a review on clean single-commit
history, and a direct API review request is only used as a fallback.

**Why this priority**: This aligns with the repository's 1-commit-per-PR policy and ensures Copilot reviews single, cohesive commits rather than fragmented multi-commit history. It is P2 because it is
an optimization of an existing functional path rather than a correctness fix.

**Independent Test**: Can be tested by setting up a multi-commit PR snapshot where CI passes and no session is active, verifying that squash executes before request_review, and that request_review
only fires as a fallback if squash did not invalidate the snapshot.

**Acceptance Scenarios**:

1. **Given** a PR with 3 commits above merge-base and CI passing, **When** the pipeline action sequence runs, **Then** `SquashAction` executes first and `RequestReviewAction` is skipped because the
   squash force-push will trigger a Copilot review automatically.

2. **Given** a PR with 3 commits where squash fails (e.g., rebase conflict), **When** the pipeline action sequence continues, **Then** `RequestReviewAction` fires as a fallback and requests review on
   the current HEAD.

3. **Given** a PR with exactly 1 commit, **When** the pipeline evaluates, **Then** `SquashAction` is skipped (nothing to squash) and `RequestReviewAction` proceeds normally.

---

### User Story 4 - Squash Not Blocked by Pending Review (Priority: P2)

As a repository maintainer, I want the squash operation to proceed even when a Copilot review is pending (requested but not yet submitted), so that squash is only deferred by active coding/repair
sessions where force-pushing would disrupt an in-progress agent.

**Why this priority**: The current behavior incorrectly defers squash whenever a review is pending, but a pending review is not impacted by a force-push (GitHub will re-trigger the review on the new
HEAD). Only active coding sessions are disrupted by squash.

**Independent Test**: Can be tested by configuring a snapshot with `copilot_review_pending=True` and `active_session=False` and verifying `SquashAction.evaluate()` returns EXECUTE.

**Acceptance Scenarios**:

1. **Given** a PR with >1 commit, a pending Copilot review, and no active Copilot coding session, **When** `SquashAction.evaluate()` is called, **Then** it returns `ActionDecision.EXECUTE` (squash
   proceeds).

2. **Given** a PR with >1 commit and an active Copilot coding session, **When** `SquashAction.evaluate()` is called, **Then** it returns `ActionDecision.SKIP` with "Copilot session active — deferring
   squash".

3. **Given** a PR with >1 commit, no pending review, and no active session, **When** `SquashAction.evaluate()` is called, **Then** it returns `ActionDecision.EXECUTE`.

---

### User Story 5 - Squash Merge for Multi-Commit PRs at Merge Time (Priority: P2)

As a repository maintainer, I want the merge action to use squash merge strategy when a PR still has multiple commits at merge time, with a commit message sourced from the Copilot SDK when available,
so that even if pre-merge squash was skipped or failed, the resulting merge maintains clean linear history.

**Why this priority**: This is a safety net ensuring that multiple commits never result in a polluted main branch history, regardless of whether the pre-merge squash succeeded.

**Independent Test**: Can be tested by configuring a PR snapshot with `commit_count > 1` at the merge step and verifying `MergeAction.execute()` calls `provider.merge_pr()` with strategy `"squash"`
and a Copilot-generated commit message.

**Acceptance Scenarios**:

1. **Given** a PR with 2 commits above merge-base that passes all merge preconditions, **When** `MergeAction.execute()` runs, **Then** it calls `provider.merge_pr()` with method `"squash"` and a
   descriptive commit message.

2. **Given** a PR with exactly 1 commit that passes all merge preconditions, **When** `MergeAction.execute()` runs, **Then** it calls `provider.merge_pr()` with method `"rebase"` (existing behavior
   preserved).

3. **Given** a multi-commit PR where the Copilot SDK is unavailable for commit message generation, **When** `MergeAction.execute()` runs with squash strategy, **Then** it falls back to a deterministic
   commit message built from the commit subjects (same pattern as `_build_squash_commit_message`).

---

### Edge Cases

- What happens when a repair is dispatched but the repair agent never pushes code (stale repair)? The system should rely on the existing squash-wait timeout mechanism to eventually proceed.
- How does the system handle a race condition where repair finishes and a review is requested simultaneously? The SHA-based deduplication ensures only one review per HEAD is active.
- What happens when squash invalidates the snapshot but CI hasn't run on the new HEAD yet? The `invalidates_snapshot=True` flag causes the pipeline to exit early; the next workflow trigger (on the
  force-push event) re-evaluates from scratch.
- What happens when `commit_count` is unavailable (provider doesn't support it)? The merge should fall back to rebase, maintaining current behavior.

## Requirements

### Functional Requirements

- **FR-001**: The `RequestReviewAction` MUST skip (return `ActionDecision.SKIP`) when a repair has been dispatched in the current pipeline run (i.e., when `DispatchRepairAction` returned
  `ActionDecision.EXECUTE` in the same action sequence).

- **FR-002**: The `RequestReviewAction` MUST skip when an active Copilot coding session is detected (via `snapshot.active_session == True`).

- **FR-003**: The `RequestReviewAction` MUST skip when unresolved review comment threads exist on the PR (thread count > 0 as reported by the provider).

- **FR-004**: The `_request_copilot_review_if_needed` function in the legacy orchestrator path MUST check for repair dispatch status and unresolved comments before requesting review, mirroring FR-001
  and FR-003.

- **FR-005**: The `SquashAction` MUST NOT use `copilot_review_pending` as a blocking precondition. It MUST only defer when `snapshot.active_session` is true (active coding/repair session).

- **FR-006**: When the pipeline action sequence includes both `SquashAction` and `RequestReviewAction`, the `RequestReviewAction` MUST be suppressed (skip) if `SquashAction` executed successfully and
  set `invalidates_snapshot=True`, since the force-push will naturally trigger a new review.

- **FR-007**: `RequestReviewAction` MUST fire as a fallback if `SquashAction` was skipped (e.g., only 1 commit) or failed.

- **FR-008**: `MergeAction.execute()` MUST select merge strategy based on commit count: use `"squash"` when `snapshot.commit_count > 1`, use `"rebase"` when `snapshot.commit_count == 1`.

- **FR-009**: When using squash merge, the system MUST attempt to generate a commit message via the Copilot SDK, falling back to a deterministic message built from commit subjects if the SDK is
  unavailable or returns an error.

- **FR-010**: The decision summary JSON MUST include the reason when a review request is suppressed (e.g., `"review_request_skipped_reason": "repair_active"` or `"unresolved_comments"`).

### Non-Functional Requirements

- **NFR-001**: The additional guard checks (repair status, unresolved comments) MUST NOT add more than 1 additional API call per orchestrator invocation. Unresolved thread count SHOULD be derivable
  from data already fetched in the pipeline snapshot.

- **NFR-002**: All new precondition checks MUST be logged at INFO level with structured context (PR number, reason, counts) for diagnosability.

- **NFR-003**: The changes MUST maintain backward compatibility with the legacy orchestrator path (`run_ai_pr_loop`) and the pipeline path (`pipeline/command.py`) — both must enforce the same guards.

- **NFR-004**: All new logic MUST have unit test coverage following the 1:1:1 test structure policy. Each new precondition check MUST have at least one positive and one negative test case.

### Key Entities

- **PRStateSnapshot**: Extended with `unresolved_thread_count` field to support FR-003 without additional API calls.
- **DerivedState**: Extended with `repair_dispatched` flag set by `DispatchRepairAction` to communicate repair status to downstream actions like `RequestReviewAction`.
- **ActionResult**: Already supports `invalidates_snapshot` which is used by the squash-first logic (FR-006).

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 (zero) review requests are sent within the same pipeline run that dispatches a repair — measured across 100% of ai-pr-loop invocations in CI logs post-deployment.

- **SC-002**: 0 (zero) review requests are sent when the PR has ≥1 unresolved comment thread — verified by auditing decision summary JSON for the `review_request_skipped_reason` field across all
  pipeline runs.

- **SC-003**: For PRs with >1 commit, `SquashAction` executes before `RequestReviewAction` in 100% of pipeline runs where no active coding session blocks it — measured by action sequence order in
  pipeline summary output.

- **SC-004**: 100% of PRs merged via ai-pr-loop that have >1 commit at merge time use the `"squash"` merge strategy — verified via the `merge_method` field in GitHub merge event payloads.

- **SC-005**: `SquashAction` defers in 0% of cases where `copilot_review_pending=True` but `active_session=False` — verified by unit tests and pipeline decision logs showing EXECUTE instead of SKIP
  for this condition.

- **SC-006**: 100% of pre-existing orchestrator and pipeline unit tests pass without modification after changes are applied (0 regressions introduced).

- **SC-007**: New guard logic achieves ≥95% branch coverage in unit tests, with a minimum of 2 test cases (1 positive, 1 negative) per new precondition check.

- **SC-008**: The Copilot SDK commit message generation path succeeds in ≥80% of squash-merge invocations (remaining ≤20% use the deterministic fallback) — measured over the first 30 days
  post-deployment.

- **SC-009**: End-to-end latency of the `RequestReviewAction.evaluate()` method remains under 500ms (p95) with the new guard checks, adding no more than 50ms over the baseline without guards.

---
*Generated by Copilot SDK (claude-opus-4.6)*
