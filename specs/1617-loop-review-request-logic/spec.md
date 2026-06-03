# Feature Specification: AI PR Loop Review Request Guards and Squash-First Review Strategy

**Feature Branch**: `speckit/1617/phase-1-specify`  
**Created**: 2026-05-27  
**Status**: Draft  
**Input**: GitHub Issue #1617  
**Source Issue**: #1617 (<https://github.com/ayaiayorg/agentic-devtools/issues/1617>)

## Clarifications

### Session 2026-05-27

- Q: The spec proposes extending `PRStateSnapshot` with `unresolved_thread_count`, but the existing field is named
  `unresolved_threads` (already present on `PRStateSnapshot`). Should the spec use the existing field name, or does it
  intend a semantically different field? → A: `unresolved_threads` should continue to mean the existing narrower count
  already on `PRStateSnapshot` (unresolved Copilot review threads from prior commits). FR-003 now requires a broader
  all-authors/all-unresolved-threads count, so it should use a separate field such as `total_unresolved_threads` rather
  than reusing `unresolved_threads`. The Key Entities section has been corrected to preserve `unresolved_threads` for
  the existing Copilot-only count and use the new total count for FR-003.

- Q: FR-011 requires suppressing review requests across runs when a repair was dispatched in a prior run and HEAD has
  not changed. How is the "HEAD SHA at repair dispatch time" persisted across workflow invocations? The current
  `repair_dispatched` is a local boolean within a single run. → A: FR-011 uses two distinct PR comment markers with
  different purposes. The existing `DEDUP_MARKER_PREFIX` marker is the run-dedup / dispatch-budget marker used by
  `check_deduplication()` to deduplicate orchestrator runs; because that guard may create or update the marker even
  when no repair is dispatched, the `DEDUP_MARKER_PREFIX` marker MUST NOT be treated as evidence that a repair was
  dispatched. The "repair actually dispatched at SHA" state is instead persisted in a separate repair-dispatch marker
  comment using a different prefix constant, `REPAIR_DISPATCH_MARKER_PREFIX`, whose literal string MUST be distinct
  from `DEDUP_MARKER_PREFIX` (for example, a dedicated `<!-- repair-dispatched-sha:... -->` prefix rather than the
  existing `<!-- repair-dispatch:... -->` prefix). That repair-dispatch marker is written only when
  `DispatchRepairAction` actually dispatches a repair. On re-trigger, the orchestrator reads only the
  `REPAIR_DISPATCH_MARKER_PREFIX` marker to detect a prior repair dispatch and compares the SHA stored in that marker
  against current HEAD. No new persistence mechanism beyond PR comments is needed, but the two marker formats must be
  unambiguously distinguishable when parsed.

- Q: FR-003 says "unresolved review comment threads" but the existing `unresolved_threads` field on `PRStateSnapshot`
  specifically counts "unresolved Copilot review threads from prior commits." Should FR-003 block on ALL unresolved
  threads (including human reviewer threads and threads on current HEAD), or only the subset already tracked? → A:
  FR-003 should block on ALL unresolved review threads on the PR regardless of author or commit, matching User Story 2
  Scenario 3 which explicitly includes non-Copilot human reviewer threads. The `RequestReviewAction` guard should use a
  broader count that includes all unresolved threads, not just the prior-commit subset. A new snapshot field or provider
  call may be needed to capture the full count.

- Q: FR-009 references "the Copilot SDK" for generating squash commit messages. What specific SDK or API is this? The
  current GitHub provider already includes an SDK-based commit message path
  (`GitHubActionsProvider._generate_commit_message_via_sdk`) with deterministic fallback. → A: FR-009 should remain
  deterministic-only in this phase: commit messages for this feature are generated from commit subjects using the
  existing `_build_squash_commit_message` pattern. The existing SDK-based generator is acknowledged as current
  codebase capability, but FR-009 does not require using it, changing it, or expanding its usage in this phase. Any
  future Copilot SDK-based generation standardization should occur behind the `CommitMessageGenerator` interface and is
  explicitly out of scope for this phase.

- Q: FR-006 describes how `RequestReviewAction` behaves when `SquashAction` sets `invalidates_snapshot=True`. How does
  `RequestReviewAction` re-evaluate on the refreshed snapshot within the same pipeline run? The current action pipeline
  evaluates actions sequentially — there is no built-in mechanism for re-running actions after a snapshot refresh.
  → A: The pipeline runner refreshes the PR state snapshot when any action returns `invalidates_snapshot=True`, then
  re-runs all actions that declare `runs_after_invalidation=True`. `RequestReviewAction` opts into this by declaring
  `runs_after_invalidation=True`, so it re-evaluates on the refreshed snapshot and requests review on the new squashed
  HEAD. This replaces the earlier suppression model where `RequestReviewAction` was skipped via a
  `snapshot_invalidated` DerivedState flag.

## Problem Statement

The ai-pr-loop orchestrator has logic errors in its review request and merge pathways:

1. **Review requests fire during repair dispatch** — When a repair (Copilot agent fix pass) has just been dispatched or is actively in progress, the orchestrator may still request a new Copilot
   review. This triggers duplicate or premature reviews that conflict with the repair cycle.

2. **Review requests fire when unresolved comments exist** — If prior review comments remain unresolved/actionable, requesting a fresh review is premature and can defeat approval safety gates.

3. **Squash was coupled to review triggering** — For PRs with >1 commit, the squash step previously relied on force-push to implicitly trigger a Copilot review via GitHub's `push` event.
   Reviews are now always requested explicitly via `RequestReviewAction` after squash completes — the squash step is responsible strictly for commit hygiene.

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

**Mapped FRs**: FR-001, FR-002, FR-011, FR-010.

**Acceptance Scenarios**:

1. **Given** a PR where the orchestrator has just dispatched a repair (exit code = EXIT_REPAIR_DISPATCHED), **When** the review request logic is evaluated, **Then** no Copilot review request is sent
   and the decision summary includes `"reason": "repair_dispatched"`.

2. **Given** a PR with an active Copilot session (detected via squash-wait marker or events API showing session in progress), **When** the `RequestReviewAction.evaluate()` is called, **Then** it
   returns `ActionDecision.SKIP` with details indicating repair/session is active.

3. **Given** a PR where a repair was dispatched in a prior run and the repair agent has not yet pushed new code (HEAD SHA matches the repair-dispatch marker SHA, i.e. the dedicated persisted marker
   written only when `DispatchRepairAction` actually dispatches a repair), **When** the ai-pr-loop is re-triggered (e.g., by a workflow_run event), **Then** the review request is suppressed until the
   repair cycle produces a new HEAD SHA.

---

### User Story 2 - Review Request Blocked When Unresolved Comments Exist (Priority: P1)

As a repository maintainer, I want review requests to be blocked when there are unresolved or actionable review comments on the PR, so that authors address existing feedback before requesting fresh
reviews.

**Why this priority**: Requesting a new review while prior feedback is unresolved defeats the safety gate model — reviewers expect all prior comments to be addressed before re-review.

**Independent Test**: Can be tested by configuring a PR snapshot with unresolved review threads or actionable inline comments and verifying `RequestReviewAction` returns SKIP.

**Mapped FRs**: FR-003, FR-004.

**Acceptance Scenarios**:

1. **Given** a PR with 2 unresolved review comment threads from a previous Copilot review, **When** `RequestReviewAction.evaluate()` is called, **Then** it returns `ActionDecision.SKIP` with details
   "Unresolved review comments exist".

2. **Given** a PR where all prior review comments have been resolved (0 unresolved threads), **When** `RequestReviewAction.evaluate()` is called and other preconditions are met, **Then** it returns
   `ActionDecision.EXECUTE`.

3. **Given** a PR with unresolved comments from a non-Copilot human reviewer, **When** `RequestReviewAction.evaluate()` is called, **Then** it returns `ActionDecision.SKIP` (any unresolved comment
   blocks new review requests, regardless of author).

---

### User Story 3 - Squash-First Review Trigger for Multi-Commit PRs (Priority: P2)

As a repository maintainer, I want the ai-pr-loop to squash multi-commit PRs before requesting a Copilot review, so that the review is always requested explicitly on clean single-commit
history via `RequestReviewAction` after squash completes.

**Why this priority**: This aligns with the repository's 1-commit-per-PR policy and ensures Copilot reviews single, cohesive commits rather than fragmented multi-commit history. It is P2 because it is
an optimization of an existing functional path rather than a correctness fix.

**Independent Test**: Can be tested by setting up a multi-commit PR snapshot where CI passes and no session is active, verifying that squash executes before request_review, and that request_review
runs explicitly on the refreshed snapshot after squash invalidates it.

**Mapped FRs**: FR-006, FR-007.

**Acceptance Scenarios**:

1. **Given** a PR with 3 commits above merge-base and CI passing, **When** the pipeline action sequence runs, **Then** `SquashAction` executes first (invalidating the snapshot) and
   `RequestReviewAction` runs on the refreshed snapshot to explicitly request review on the new squashed HEAD.

2. **Given** a PR with 3 commits where squash fails (e.g., rebase conflict), **When** the pipeline action sequence continues, **Then** subsequent actions are halted due to the failure.

3. **Given** a PR with exactly 1 commit, **When** the pipeline evaluates, **Then** `SquashAction` is skipped (nothing to squash) and `RequestReviewAction` proceeds normally.

---

### User Story 4 - Squash Not Blocked by Pending Review (Priority: P2)

As a repository maintainer, I want the squash operation to proceed even when a Copilot review is pending (requested but not yet submitted), so that squash is only deferred by active coding/repair
sessions where force-pushing would disrupt an in-progress agent.

**Why this priority**: The current behavior incorrectly defers squash whenever a review is pending, but a pending review is not impacted by a force-push. Only active coding sessions are disrupted by squash.

**Independent Test**: Can be tested by configuring a snapshot with `copilot_review_pending=True` and `active_session=False` and verifying `SquashAction.evaluate()` returns EXECUTE.

**Mapped FRs**: FR-005.

**Acceptance Scenarios**:

1. **Given** a PR with >1 commit, a pending Copilot review, and no active Copilot coding session, **When** `SquashAction.evaluate()` is called, **Then** it returns `ActionDecision.EXECUTE` (squash
   proceeds).

2. **Given** a PR with >1 commit and an active Copilot coding session, **When** `SquashAction.evaluate()` is called, **Then** it returns `ActionDecision.SKIP` with "Copilot session active — deferring
   squash".

3. **Given** a PR with >1 commit, no pending review, and no active session, **When** `SquashAction.evaluate()` is called, **Then** it returns `ActionDecision.EXECUTE`.

---

### User Story 5 - Squash Merge for Multi-Commit PRs at Merge Time (Priority: P2)

As a repository maintainer, I want the merge action to use squash merge strategy when a PR still has multiple commits at merge time, with a commit message sourced from the deterministic fallback
(concatenated commit subjects), so that even if pre-merge squash was skipped or failed, the resulting merge maintains clean linear history.

**Why this priority**: This is a safety net ensuring that multiple commits never result in a polluted main branch history, regardless of whether the pre-merge squash succeeded.

**Independent Test**: Can be tested by configuring a PR snapshot with `commit_count > 1` at the merge step and verifying `MergeAction.execute()` calls
`provider.merge_pr()` with method `"squash"` and a deterministic commit message.

**Mapped FRs**: FR-008, FR-009.

**Acceptance Scenarios**:

1. **Given** a PR with 2 commits above merge-base that passes all merge preconditions, **When** `MergeAction.execute()` runs, **Then** it calls `provider.merge_pr()` with method `"squash"` and a
   descriptive commit message built from the commit subjects.

2. **Given** a PR with exactly 1 commit that passes all merge preconditions, **When** `MergeAction.execute()` runs, **Then** it calls `provider.merge_pr()` with method `"rebase"` (existing behavior
   preserved).

3. **Given** a multi-commit PR where the commit message generation interface is not configured, **When** `MergeAction.execute()` runs with squash strategy, **Then** it uses the deterministic
   commit message built from commit subjects (same pattern as `_build_squash_commit_message`).

---

### Edge Cases

- What happens when a repair is dispatched but the repair agent never pushes code (stale repair)? The system should rely on the existing squash-wait timeout mechanism to eventually proceed. The
  repair-dispatch marker SHA comparison ensures that once a new HEAD is pushed (by any means), review requests are unblocked.
- How does the system handle a race condition where repair finishes and a review is requested simultaneously? The SHA-based deduplication ensures only one review per HEAD is active.
- What happens when squash invalidates the snapshot but CI hasn't run on the new HEAD yet? The `invalidates_snapshot=True` flag causes the pipeline runner to refresh the snapshot; `RequestReviewAction`
  (which opts into `runs_after_invalidation`) re-evaluates on the refreshed snapshot and will skip if CI is not yet passing.
- What happens when `commit_count` is unavailable (provider doesn't support it)? The merge should fall back to rebase, maintaining current behavior.
- What happens when `snapshot_invalidated` is set by an action other than `SquashAction` (e.g., a future action that force-pushes)? `RequestReviewAction` still runs after invalidation — it re-evaluates
  all preconditions on the refreshed snapshot regardless of which action caused the invalidation.

## Requirements

### Functional Requirements

- **FR-001**: The `RequestReviewAction` MUST skip (return `ActionDecision.SKIP`) when a repair has been dispatched in the current pipeline run. Detection mechanism: `DispatchRepairAction` sets
  `derived.set("repair_dispatched", True)` upon successful execution, and `RequestReviewAction.evaluate()` checks this flag.

- **FR-002**: The `RequestReviewAction` MUST skip when an active Copilot coding session is detected (via `snapshot.active_session == True`).

- **FR-011**: The `RequestReviewAction` MUST skip on cross-run re-triggers when a repair was dispatched in a prior run and the HEAD SHA has not changed since
  that dispatch. Detection mechanism: a dedicated repair-dispatch marker comment (for example, using `REPAIR_DISPATCH_MARKER_PREFIX`) contains the HEAD SHA at successful dispatch time; this marker
  MUST be written only when `DispatchRepairAction` actually dispatches a repair. On re-trigger, the orchestrator reads this repair-specific marker and compares its SHA against current HEAD.
  Suppression is lifted when HEAD SHA differs from the marker SHA (indicating the repair agent pushed new code).

- **FR-003**: The `RequestReviewAction` MUST skip when unresolved review comment threads exist on the PR (total unresolved thread count > 0 across all reviewers, as reported by the provider). This
  requires a broader thread count than the existing `snapshot.unresolved_threads` field (which only counts prior-commit Copilot threads). A new field `snapshot.total_unresolved_threads` (or equivalent
  provider query) captures all unresolved threads regardless of author or commit.

- **FR-004**: The `_request_copilot_review_if_needed` function in the legacy orchestrator path MUST check for repair dispatch status and unresolved comments before requesting review, mirroring FR-001
  and FR-003.

- **FR-005**: The `SquashAction` MUST NOT use `copilot_review_pending` as a blocking precondition. It MUST only defer when `snapshot.active_session` is true (active coding/repair session). The
  existing `no_pending_review` precondition check must be removed from `SquashAction.evaluate()`.

- **FR-006**: When `SquashAction` returns `invalidates_snapshot=True`, the pipeline runner MUST refresh the PR state
  snapshot and re-run all actions that declare `runs_after_invalidation=True`. `RequestReviewAction` MUST declare
  `runs_after_invalidation=True` so it re-evaluates on the refreshed snapshot after squash completes, requesting
  review on the new squashed HEAD rather than being suppressed.

- **FR-007**: `RequestReviewAction` MUST also evaluate in its normal sequential position if `SquashAction` was skipped
  (e.g., only 1 commit) or did not set `invalidates_snapshot=True`, ensuring review is requested even when no snapshot
  refresh occurs.

- **FR-008**: `MergeAction.execute()` MUST select merge strategy based on commit count: use `"squash"` when `snapshot.commit_count > 1`, use `"rebase"` when
  `snapshot.commit_count == 1`. When `commit_count` is unavailable (e.g., provider does not support it or returns `None`), the system MUST fall back to `"rebase"` to preserve existing behavior.

- **FR-009**: When using squash merge, the system MUST generate a commit message using a deterministic approach built from commit subjects (same pattern as `_build_squash_commit_message`). A future
  Copilot SDK integration point SHOULD be stubbed behind an interface (`CommitMessageGenerator` protocol) so it can be wired in when available, but the initial implementation uses the deterministic
  fallback exclusively.

- **FR-010**: The decision summary JSON MUST include a `"reason"` field when a review request is
  suppressed (e.g., `"reason": "repair_active"`, `"reason": "repair_dispatched"`, `"reason": "repair_dispatched_prior_run"`,
  or `"reason": "unresolved_comments"`), aligning with the existing `summary["reason"]`
  convention used throughout the orchestrator.

### Non-Functional Requirements

- **NFR-001**: The additional guard checks (repair status, unresolved comments) MUST NOT add more than 1 additional API call per orchestrator invocation. The repair dispatch check uses `DerivedState`
  (zero API calls). The unresolved thread count SHOULD be derivable from data already fetched in the pipeline snapshot; if a broader thread count is needed (per FR-003), it MUST be fetched in the
  `build_pr_state_snapshot` phase alongside existing provider calls.

- **NFR-002**: All new precondition checks MUST be logged at INFO level with structured context (PR number, reason, counts) for diagnosability.

- **NFR-003**: The changes MUST maintain backward compatibility with the legacy orchestrator path (`run_ai_pr_loop`) and the pipeline path (`pipeline/command.py`) — both must enforce the same guards.

- **NFR-004**: All new logic MUST have unit test coverage following the 1:1:1 test structure policy. Each new precondition check MUST have at least one positive and one negative test case.

### Key Entities

- **PRStateSnapshot**: The existing `unresolved_threads` field (counts prior-commit Copilot threads) is retained with its current narrow semantics for backward
  compatibility and any existing logic that
  depends on that specific count. A new `total_unresolved_threads` field is added for FR-003 and is the field consumed by `RequestReviewAction` when applying the broader unresolved-thread guard
  (all unresolved threads regardless of author or commit).
- **DerivedState**: Extended with two new flags that MUST be initialized to `False` at the start of every
  orchestrator/pipeline run before any action evaluation occurs, so downstream code can safely use direct
  attribute access without `AttributeError` when a flag was never set during that run:
  - `repair_dispatched` (bool) — initialized to `False` at run start, then set to `True` by `DispatchRepairAction`
    upon successful execution to communicate repair status to downstream actions like `RequestReviewAction`.
  - `snapshot_invalidated` (bool) — initialized to `False` at run start, then set to `True` by the pipeline
    runner when any action returns `ActionResult.invalidates_snapshot == True`. Used by the pipeline runner to
    trigger a snapshot refresh and re-run of actions with `runs_after_invalidation=True` (FR-006).
- **ActionResult**: Already supports `invalidates_snapshot` which is used by the squash-first logic (FR-006).
- **CommitMessageGenerator** (protocol): New interface for commit message generation, with a single `DeterministicCommitMessageGenerator` implementation initially. Stubbed for future Copilot SDK
  integration.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 0 (zero) review requests are sent within the same pipeline run that dispatches a repair — measured across 100% of ai-pr-loop invocations in CI logs post-deployment.

- **SC-002**: 0 (zero) review requests are sent when the PR has ≥1 unresolved comment thread — verified by auditing decision summary JSON for the `reason` field across all
  pipeline runs.

- **SC-003**: For PRs with >1 commit, `SquashAction` executes before `RequestReviewAction` in 100% of pipeline runs where no active coding session blocks it — measured by action sequence order in
  pipeline summary output.

- **SC-004**: 100% of PRs merged via ai-pr-loop that have >1 commit at merge time use the `"squash"` merge strategy — verified via the `merge_method` field in GitHub merge event payloads.

- **SC-005**: `SquashAction` defers in 0% of cases where `copilot_review_pending=True` but `active_session=False` — verified by unit tests and pipeline decision logs showing EXECUTE instead of SKIP
  for this condition.

- **SC-006**: 100% of pre-existing orchestrator and pipeline unit tests pass without modification after changes are applied (0 regressions introduced).

- **SC-007**: New guard logic achieves 100% branch coverage in unit tests (matching the repository's `--cov-fail-under=100` CI gate), with a minimum of 2 test
  cases (1 positive, 1 negative) per new precondition check.

- **SC-008**: The `CommitMessageGenerator` protocol is implemented with the deterministic fallback achieving 100% success. The Copilot SDK path success rate (≥80% target) becomes measurable only after
  the SDK integration is wired in — tracked as a post-integration KPI over the first 30 days after SDK availability.

- **SC-009**: End-to-end latency of the `RequestReviewAction.evaluate()` method remains under 500ms (p95) with the new guard checks, adding no more than 50ms over the baseline without guards.

---
*Generated by Copilot SDK (claude-opus-4.6)*
