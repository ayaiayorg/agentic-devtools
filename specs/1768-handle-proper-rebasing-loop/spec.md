# Feature Specification: Rebase Action for Stale Single-Commit PRs in ai-pr-loop

**Feature Branch**: `1768-rebase-stale-single-commit-prs`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: User description: "Handle proper rebasing in ai-pr-loop when multiple PRs are processed"  
**Source Issue**: #1768 (<https://github.com/ayaiayorg/agentic-devtools/issues/1768>)

## Problem Statement

The ai-pr-loop pipeline processes multiple pull requests concurrently, dispatching separate workflow runs for each PR under management. When multiple PRs target the same base branch, the merge of one
PR advances `main`, leaving remaining PRs behind. The pipeline's current architecture couples rebase logic exclusively to the Squash action — rebase onto the base branch only occurs within
`_squash_and_force_push()`. This means that PRs already containing a single commit (the common case after an initial squash cycle or when authored with the single-commit policy) never pass through the
Squash action's execution path and therefore never receive a rebase, even when their branch is behind `main`.

This gap creates a concrete failure scenario in multi-PR environments. Consider PR A and PR B, both targeting `main`. PR A merges successfully, advancing `main` by one commit. PR B has a single
commit, its Copilot review is clean, and the pipeline proceeds through RequestReview → Approve → Merge. At the Merge step, the GitHub "rebase" merge method is selected (since `commit_count == 1`), but
the branch is stale — it was forked from an older `main`. GitHub may reject the merge outright if branch protection requires branches to be up-to-date, or worse, the merge may succeed with the branch
silently incorporating a stale base, potentially introducing integration issues that CI would have caught had the branch been rebased first.

The existing spec for the pipeline (spec 1509) explicitly states that rebase merge should preserve SDK-generated commit messages and that conflicts require a new squash+rebase cycle rather than a
fallback to squash merge. However, the spec does not address the scenario where a single-commit PR needs rebasing without any squash step. The pipeline's fixed action ordering — Guards → Publish →
DispatchRepair → Squash → ResolveThreads → RequestReview → Approve → Merge — has no action responsible for detecting and resolving branch staleness independently of the squash flow. A dedicated Rebase
action is needed, positioned in the pipeline before approval and merge, to ensure every PR is up-to-date with `main` before attempting to merge, regardless of its commit count.

## User Scenarios & Testing

### User Story 1 - Single-Commit PR Rebased After Sibling Merge (Priority: P1)

As a developer using the ai-pr-loop to manage multiple concurrent PRs, I need the pipeline to automatically detect when my single-commit PR falls behind `main` (because another PR merged) and rebase
it onto the updated `main` before proceeding with approval and merge. This ensures my PR's CI runs against the latest code and branch protection rules requiring up-to-date branches are satisfied
without manual intervention.

**Why this priority**: This is the core scenario described in the issue. Without this capability, the entire multi-PR workflow breaks down — PRs either fail to merge due to branch protection, or merge
with stale bases that bypass CI validation against the latest code. This affects every team using ai-pr-loop with more than one active PR.

**Independent Test**: Can be fully tested by setting up two PRs targeting the same branch, merging the first, and observing that the pipeline automatically rebases the second before attempting merge.
Delivers the fundamental value of correct multi-PR orchestration.

**Acceptance Scenarios**:

1. **Given** a single-commit PR whose branch is 1+ commits behind `origin/main`, **When** the pipeline evaluates this PR during its action sequence, **Then** the pipeline rebases the branch onto
   `origin/main` and force-pushes before proceeding to the Approve action.

2. **Given** a single-commit PR whose branch is already up-to-date with `origin/main`, **When** the pipeline evaluates this PR, **Then** the rebase action is skipped (no force-push occurs) and the
   pipeline proceeds immediately to the next action.

3. **Given** a single-commit PR that requires rebase, **When** the rebase and force-push succeed, **Then** the action result indicates `invalidates_snapshot=True`, causing the pipeline to refresh the
   PR snapshot and re-evaluate CI status before proceeding.

---

### User Story 2 - CI Re-validation After Rebase (Priority: P1)

As a developer relying on CI gates, I need the pipeline to wait for CI checks to pass on the rebased commit before attempting approval or merge. A rebase changes the commit SHA, invalidating any
previous CI results. The pipeline must treat the post-rebase state as requiring fresh validation, exactly as it does after a squash operation.

**Why this priority**: Merging without CI re-validation after rebase defeats the purpose of branch protection. This is inseparable from the rebase itself — a rebase without subsequent CI verification
provides a false sense of correctness.

**Independent Test**: Can be tested by observing that after a force-push from rebase, the pipeline enters a waiting state for CI checks rather than immediately proceeding to approve or merge. The
pipeline iteration should halt (via snapshot invalidation) and resume only after fresh CI results are available.

**Acceptance Scenarios**:

1. **Given** a PR that was just rebased and force-pushed by the pipeline, **When** the pipeline attempts to proceed to the Approve action, **Then** it detects that CI checks are pending on the new
   HEAD and blocks until they complete.

2. **Given** a PR that was rebased and CI subsequently fails on the new HEAD, **When** the pipeline evaluates the PR on the next iteration, **Then** it dispatches a repair action (via DispatchRepair)
   rather than proceeding to approve.

---

### User Story 3 - Re-request Copilot Review After Rebase Invalidates Approval (Priority: P2)

As a developer whose PR was previously approved by Copilot, I need the pipeline to detect when a rebase invalidates the existing review approval (because GitHub dismisses stale reviews on new pushes
or because branch protection requires re-review) and automatically request a new Copilot review once CI passes on the rebased commit.

**Why this priority**: This handles the review gate recovery path. While the rebase itself (P1) is critical, the review re-request is a follow-on concern that only applies when branch protection is
configured to dismiss stale reviews. Many repositories have this setting, making it important but secondary to the core rebase flow.

**Independent Test**: Can be tested by configuring a repository with "dismiss stale reviews" enabled, rebasing a previously-approved PR, and observing that the pipeline requests a new Copilot review
after CI passes rather than attempting to merge with a dismissed approval.

**Acceptance Scenarios**:

1. **Given** a PR that had Copilot approval before rebase and the repository dismisses stale reviews on push, **When** CI passes on the rebased commit, **Then** the pipeline detects the review is no
   longer valid and requests a new Copilot review via the RequestReview action.

2. **Given** a PR that was rebased but the repository does NOT dismiss stale reviews, **When** CI passes on the rebased commit, **Then** the pipeline recognizes the existing approval is still valid
   and proceeds directly to the Approve/Merge actions without re-requesting review.

---

### User Story 4 - Rebase Conflict Handling (Priority: P2)

As a developer whose PR conflicts with recently merged changes on `main`, I need the pipeline to handle rebase conflicts gracefully — either by attempting automated resolution (via the existing
SDK-powered conflict resolver) or by clearly signaling that manual intervention is required, without leaving the branch in a broken state.

**Why this priority**: Conflicts are an expected edge case in multi-PR environments. The pipeline already has SDK-based conflict resolution for the squash path; extending that capability to the
standalone rebase path ensures consistent behavior. However, conflicts are less common than clean rebases, making this secondary to the happy path.

**Independent Test**: Can be tested by creating a PR that conflicts with a recently merged change, triggering the rebase action, and verifying the pipeline either resolves the conflict and
force-pushes or aborts cleanly and reports the conflict.

**Acceptance Scenarios**:

1. **Given** a single-commit PR that conflicts with `origin/main` during rebase, **When** the SDK-powered conflict resolver successfully resolves the conflicts, **Then** the pipeline completes the
   rebase, force-pushes, and sets `invalidates_snapshot=True`.

2. **Given** a single-commit PR that conflicts with `origin/main` and automated resolution fails, **When** the rebase is aborted, **Then** the pipeline returns BLOCKED with a clear diagnostic message
   indicating manual conflict resolution is needed, and does NOT force-push a partially-rebased state.

---

### Edge Cases

- What happens when the PR's base branch is not `main` but another feature branch? The rebase action must respect the PR's configured base branch, not assume `main`.
- How does the system handle a race condition where `main` advances again during the rebase operation? The force-push with `--force-with-lease` ensures the push fails if the remote branch was updated
  concurrently; the pipeline should retry on the next iteration.
- What happens if the rebase action runs but the force-push fails due to network errors? The action should return FAILED, halting downstream actions, and the branch should remain in its pre-rebase
  state (no partial state pushed).
- What happens when a DispatchRepair was already triggered in this pipeline run? The rebase action should defer (skip) to avoid moving HEAD while a repair session is active, consistent with how the
  Squash action handles this case.

## Requirements

### Functional Requirements

- **FR-001**: The pipeline MUST include a dedicated rebase evaluation step that runs independently of the Squash action. This step must assess whether the PR's branch is behind its base branch and, if
  so, perform a rebase and force-push. The evaluation must occur regardless of the PR's commit count, ensuring single-commit PRs receive the same freshness guarantee as multi-commit PRs that pass
  through the squash flow.

- **FR-002**: The rebase step MUST set `invalidates_snapshot=True` when it performs a force-push, causing the pipeline runner to refresh the PR snapshot and halt downstream actions for the current
  iteration. This ensures subsequent actions (RequestReview, Approve, Merge) operate on the correct HEAD SHA and fresh CI status.

- **FR-003**: The rebase step MUST skip execution (return SKIP) when the branch is already up-to-date with the base branch (zero commits behind). This avoids unnecessary force-pushes and CI re-runs
  when the PR is already current.

- **FR-004**: The rebase step MUST defer execution (return SKIP or BLOCKED) when a repair session is active (`no_active_session` is false) or when a DispatchRepair was triggered in the current
  pipeline run (`no_repair_dispatched` is false). This prevents HEAD from moving while other operations depend on a stable commit reference.

- **FR-005**: The rebase step MUST use `--force-with-lease` for the push operation to prevent overwriting concurrent changes to the remote branch. If the lease check fails, the action MUST return
  FAILED without retrying within the same pipeline iteration.

- **FR-006**: The rebase step MUST attempt SDK-powered conflict resolution when a rebase encounters merge conflicts, consistent with the existing behavior in `_squash_and_force_push()`. If automated
  resolution fails, the rebase MUST be aborted (`git rebase --abort`) and the action MUST return BLOCKED.

- **FR-007**: The pipeline action ordering MUST place the rebase step after Squash and before RequestReview. The resulting order is: Guards → Publish → DispatchRepair → Squash → **Rebase** →
  ResolveThreads → RequestReview → Approve → Merge. This ensures that if Squash runs (multi-commit PRs), its own internal rebase is performed first, and the standalone Rebase action can then verify
  the branch is current. For single-commit PRs where Squash skips, the Rebase action serves as the sole freshness check.

- **FR-008**: The pipeline MUST detect when a previously-approved review has been dismissed due to the rebase force-push and ensure the RequestReview action re-requests Copilot review on the
  subsequent pipeline iteration. The existing RequestReview action's `evaluate()` logic must account for the review state being stale relative to the current HEAD SHA.

- **FR-009**: The rebase step MUST respect the PR's configured base branch (not hard-code `main`). The base branch reference must be derived from the PR snapshot's target branch field.

### Non-Functional Requirements

- **NFR-001**: The rebase action MUST complete its evaluation (the `evaluate()` method) within 5 seconds, including the behind-count check. Expensive git operations (fetch, rebase, push) occur only in
  `execute()`.

- **NFR-002**: The rebase action MUST produce structured log output consistent with other pipeline actions, including the number of commits behind, whether rebase was attempted, and the outcome
  (success, skipped, conflict, error). This enables debugging of multi-PR orchestration issues.

- **NFR-003**: The rebase action MUST NOT leave the local repository in a dirty or mid-rebase state. On any failure path, the working tree must be restored to a clean state (via `git rebase --abort`
  or equivalent).

- **NFR-004**: The rebase action MUST achieve 100% branch coverage in its unit tests, consistent with the project's testing policy. Tests must cover: skip (already up-to-date), successful rebase,
  conflict with successful resolution, conflict with failed resolution, deferred due to active session, and force-push-with-lease failure.

### Key Entities

- **RebaseAction**: A pipeline action implementing the action protocol (`evaluate` + `execute`). Responsible for detecting branch staleness and performing rebase-onto-base-branch with force-push.
- **PipelineSnapshot**: The existing immutable snapshot of PR state (commit count, HEAD SHA, CI status, review status, base branch) consumed by all actions. After rebase, a new snapshot is required.
- **ActionResult**: The existing result type returned by actions, with fields for status (EXECUTE/SKIP/BLOCKED/FAILED), `invalidates_snapshot`, and diagnostic messages.

## Success Criteria

### Measurable Outcomes

- **SC-001**: When two PRs target the same base branch and one merges, the remaining single-commit PR must be automatically rebased and merged without manual intervention in 100% of cases where no
  conflicts exist. This can be verified by an integration test that merges PR A and asserts PR B completes its pipeline cycle (rebase → CI → merge) autonomously.

- **SC-002**: After a rebase force-push, the pipeline must NOT attempt to approve or merge until fresh CI checks report a terminal status (success or failure). Zero instances of approve/merge on a
  stale SHA are acceptable. This is verified by asserting that the Approve action's `evaluate()` returns BLOCKED when CI is pending.

- **SC-003**: The rebase action must add no more than 10 seconds of wall-clock time to a pipeline iteration when the branch is already up-to-date (the skip path). This ensures the new action does not
  degrade performance for PRs that don't need rebasing.

- **SC-004**: The rebase action must handle conflict scenarios without leaving orphaned git state (mid-rebase markers, detached HEAD) in 100% of tested conflict cases. Verified by asserting clean `git
  status` output after every abort path in unit tests.

- **SC-005**: Unit test coverage for the new rebase action module must be 100% branch coverage, with a minimum of 15 test cases covering the evaluation and execution paths enumerated in NFR-004.

- **SC-006**: In a simulated environment with 3 concurrent PRs merging sequentially, the total time from first merge to last merge must not exceed 3× the single-PR cycle time (accounting for CI wait),
  demonstrating that the rebase mechanism does not introduce quadratic delays through unnecessary re-reviews or repeated failures.

---
*Generated by Copilot SDK (claude-opus-4.6)*
