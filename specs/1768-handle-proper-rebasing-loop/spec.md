# Feature Specification: Rebase Action for Stale Single-Commit PRs in ai-pr-loop

**Feature Branch**: `1768-rebase-stale-single-commit-prs`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: User description: "Handle proper rebasing in ai-pr-loop when multiple PRs are processed"  
**Source Issue**: #1768 (<https://github.com/ayaiayorg/agentic-devtools/issues/1768>)

## Clarifications

### Session 2026-06-04

- Q: How should the RebaseAction determine the "commits behind" count — via the existing `CIPlatformProvider` interface (API-based) or via local git operations (requiring a local clone)? → A: The
  `evaluate()` method should use the `CIPlatformProvider` to query the behind-count via the GitHub API (compare endpoint), consistent with how `_count_commits` works for the commit count. The
  `execute()` method performs the actual git operations (fetch, rebase, push) via the provider's existing git execution interface used by `squash_post_repair`. This keeps evaluate() fast (API call
  only) and execute() as the only method performing local git work.

- Q: Should the PRStateSnapshot be extended with a `commits_behind` field populated during snapshot construction, or should RebaseAction query this on demand in `evaluate()`? → A: Extend
  PRStateSnapshot with a `commits_behind: int = 0` field, populated during `build_pr_state_snapshot()` alongside `commit_count`. This keeps `evaluate()` a pure data-driven decision (no I/O),
  consistent with how other actions use snapshot fields, and satisfies the NFR-001 5-second evaluation requirement without needing a network call in evaluate().

- Q: Should the RebaseAction set `runs_after_invalidation = True` (like RequestReviewAction) so it can run after Squash invalidates the snapshot, or should it only run on its own clean snapshot? → A:
  No, RebaseAction should NOT set `runs_after_invalidation = True`. When Squash invalidates the snapshot, Squash already performs its own internal rebase as part of `squash_post_repair()`. The runner
  refreshes the snapshot for `runs_after_invalidation` actions, but RebaseAction positioned after Squash in the sequence will be skipped (pipeline halted by snapshot invalidation) and will evaluate
  freshly on the next pipeline iteration with a correct `commits_behind` value. This avoids double-rebasing.

- Q: What `CIPlatformProvider` method should `execute()` call for the rebase operation — should a new dedicated method (e.g., `rebase_onto_base`) be added, or should it reuse/extend
  `squash_post_repair`? → A: Add a new dedicated provider method `rebase_onto_base(pr_number: int, base_branch: str, head_branch: str, head_sha: str) -> None` to the CIPlatformProvider protocol. This
  method encapsulates fetch, rebase, and force-push-with-lease. It is semantically distinct from squash (no commit collapsing), so a separate method maintains clarity and single-responsibility. The
  implementation shares git primitives (fetch, force-push) with squash but differs in the core operation.

- Q: For FR-004, should the deferred decision when a repair or active session is detected return `ActionDecision.SKIP` or `ActionDecision.BLOCKED`? The spec says "SKIP or BLOCKED" — which is it? → A:
  Return `ActionDecision.SKIP` (not BLOCKED), consistent with how SquashAction handles the same precondition failures. SKIP means "nothing to do this iteration, try again next time" and does NOT halt
  downstream actions. BLOCKED would prevent the rest of the pipeline from running, which is undesirable when the reason is simply "defer to next iteration." BLOCKED should only be used when the rebase
  itself encounters an unresolvable conflict (FR-006).

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

- What happens when the PR's base branch is not `main` but another feature branch? The rebase action must respect the PR's configured base branch (available as `snapshot.base_branch`), not assume
  `main`.
- How does the system handle a race condition where `main` advances again during the rebase operation? The force-push with `--force-with-lease` ensures the push fails if the remote branch was updated
  concurrently; the pipeline should retry on the next iteration.
- What happens if the rebase action runs but the force-push fails due to network errors? The action should return FAILED, halting downstream actions, and the branch should remain in its pre-rebase
  state (no partial state pushed).
- What happens when a DispatchRepair was already triggered in this pipeline run? The rebase action should defer (return SKIP) to avoid moving HEAD while a repair session is active, consistent with how
  the
  Squash action handles this case.

## Requirements

### Functional Requirements

- **FR-001**: The pipeline MUST include a dedicated rebase evaluation step (implemented as `RebaseAction` conforming to the `Action` protocol) that runs independently of the Squash action. This step
  must assess whether the PR's branch is behind its base branch (using the `commits_behind` field on `PRStateSnapshot`) and, if so, perform a rebase and force-push. The evaluation must occur
  regardless of the PR's commit count, ensuring single-commit PRs receive the same freshness guarantee as multi-commit PRs that pass through the squash flow.

- **FR-002**: The rebase step MUST set `invalidates_snapshot=True` when it performs a force-push, causing the pipeline runner to refresh the PR snapshot and halt downstream actions (those without
  `runs_after_invalidation = True`) for the current iteration. This ensures subsequent actions (RequestReview, Approve, Merge) operate on the correct HEAD SHA and fresh CI status on the next pipeline
  iteration.

- **FR-003**: The rebase step MUST skip execution (return `ActionDecision.SKIP`) when the branch is already up-to-date with the base branch (`snapshot.commits_behind == 0`). This avoids unnecessary
  force-pushes and CI re-runs when the PR is already current.

- **FR-004**: The rebase step MUST defer execution (return `ActionDecision.SKIP`) when a repair session is active (`is_copilot_session_active_via_agent_task()` returns True) or when a DispatchRepair
  was triggered in the current pipeline run (`derived.repair_dispatched` is True). This prevents HEAD from moving while other operations depend on a stable commit reference. The preconditions dict
  must include `no_repair_dispatched` and `no_active_session` keys, consistent with SquashAction's pattern.

- **FR-005**: The rebase step MUST use `--force-with-lease` for the push operation to prevent overwriting concurrent changes to the remote branch. If the lease check fails, the action MUST return
  `ActionDecision.FAILED` without retrying within the same pipeline iteration.

- **FR-006**: The rebase step MUST attempt SDK-powered conflict resolution when a rebase encounters merge conflicts, consistent with the existing behavior in `_squash_and_force_push()`. If automated
  resolution fails, the rebase MUST be aborted (`git rebase --abort`) and the action MUST return `ActionDecision.BLOCKED`.

- **FR-007**: The pipeline action ordering MUST place the rebase step after Squash and before ResolveThreads. The resulting order is: Guards → Publish → DispatchRepair → Squash → **Rebase** →
  ResolveThreads → RequestReview → Approve → Merge. This ensures that if Squash runs (multi-commit PRs), its own internal rebase is performed first, and the standalone Rebase action can then verify
  the branch is current. For single-commit PRs where Squash skips, the Rebase action serves as the sole freshness check. RebaseAction does NOT set `runs_after_invalidation = True` — when Squash
  invalidates the snapshot, Rebase is skipped for this iteration and re-evaluated with a fresh snapshot on the next run.

- **FR-008**: The pipeline MUST detect when a previously-approved review has been dismissed due to the rebase force-push and ensure the RequestReview action re-requests Copilot review on the
  subsequent pipeline iteration. The existing RequestReview action's `evaluate()` logic already accounts for review state being stale relative to the current HEAD SHA (via `review_state` and
  `has_approval_on_head` snapshot fields); no changes to RequestReview are expected — the snapshot refresh after rebase naturally provides updated review state.

- **FR-009**: The rebase step MUST respect the PR's configured base branch (derived from `snapshot.base_branch`), not hard-code `main`. The base branch reference is passed to the provider's
  `rebase_onto_base()` method.

### Non-Functional Requirements

- **NFR-001**: The rebase action's `evaluate()` method MUST complete within 5 seconds. Since `commits_behind` is pre-computed in the snapshot (no I/O in evaluate), this is satisfied by pure in-memory
  field access and precondition checks.

- **NFR-002**: The rebase action MUST produce structured log output consistent with other pipeline actions (using Python `logging` at INFO level), including the number of commits behind, whether
  rebase was attempted, and the outcome (success, skipped, conflict, error). Log messages must include the PR number prefix (e.g., `PR #%d: ...`). This enables debugging of multi-PR orchestration
  issues.

- **NFR-003**: The rebase action MUST NOT leave the local repository in a dirty or mid-rebase state. On any failure path, the working tree must be restored to a clean state (via `git rebase --abort`
  or equivalent). The provider's `rebase_onto_base()` method is responsible for this guarantee.

- **NFR-004**: The rebase action MUST achieve 100% branch coverage in its unit tests, consistent with the project's testing policy. Tests must cover: skip (already up-to-date), successful rebase,
  conflict with successful resolution, conflict with failed resolution, deferred due to active session, deferred due to repair dispatched, and force-push-with-lease failure. Minimum 15 test cases
  following the 1:1:1 test structure at `tests/unit/cli/ci/pipeline/actions/rebase/`.

### Key Entities

- **RebaseAction**: A pipeline action class implementing the `Action` protocol (`evaluate` + `execute` methods, `name` property). Located at `agentic_devtools/cli/ci/pipeline/actions/rebase.py`.
  Responsible for detecting branch staleness via `snapshot.commits_behind` and performing rebase-onto-base-branch with force-push via `provider.rebase_onto_base()`.
- **PRStateSnapshot**: The existing frozen dataclass (`agentic_devtools/cli/ci/pipeline/snapshot.py`) extended with a new `commits_behind: int = 0` field populated during `build_pr_state_snapshot()`.
- **ActionResult**: The existing result dataclass (`agentic_devtools/cli/ci/pipeline/models.py`) returned by actions, with fields for `decision` (ActionDecision enum: EXECUTE/SKIP/BLOCKED/FAILED),
  `invalidates_snapshot`, `preconditions`, and diagnostic `details`/`error` messages.
- **CIPlatformProvider**: The existing provider protocol extended with a new `rebase_onto_base(pr_number: int, base_branch: str, head_branch: str, head_sha: str) -> None` method that encapsulates
  fetch, rebase, conflict resolution attempt, and force-push-with-lease. Raises on conflict or push failure.

## Success Criteria

### Measurable Outcomes

- **SC-001**: When two PRs target the same base branch and one merges, the remaining single-commit PR must be automatically rebased and merged without manual intervention in 100% of cases where no
  conflicts exist. This can be verified by an integration test that merges PR A and asserts PR B completes its pipeline cycle (rebase → CI → merge) autonomously.

- **SC-002**: After a rebase force-push, the pipeline must NOT attempt to approve or merge until fresh CI checks report a terminal status (success or failure). Zero instances of approve/merge on a
  stale SHA are acceptable. This is verified by asserting that the Approve action's `evaluate()` returns SKIP (due to snapshot invalidation) in the same pipeline run where rebase executed.

- **SC-003**: The rebase action must add no more than 10 seconds of wall-clock time to a pipeline iteration when the branch is already up-to-date (the skip path). Since evaluate() performs only
  in-memory field access when `commits_behind == 0`, the overhead is sub-millisecond. The 10-second budget accounts for any future provider overhead. This ensures the new action does not degrade
  performance for PRs that don't need rebasing.

- **SC-004**: The rebase action must handle conflict scenarios without leaving orphaned git state (mid-rebase markers, detached HEAD) in 100% of tested conflict cases. Verified by asserting clean `git
  status` output after every abort path in unit tests.

- **SC-005**: Unit test coverage for the new rebase action module must be 100% branch coverage, with a minimum of 15 test cases covering the evaluation and execution paths enumerated in NFR-004. Tests
  located at `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`.

- **SC-006**: In a simulated environment with 3 concurrent PRs merging sequentially, the total time from first merge to last merge must not exceed 3× the single-PR cycle time (accounting for CI wait),
  demonstrating that the rebase mechanism does not introduce quadratic delays through unnecessary re-reviews or repeated failures.

---
*Generated by Copilot SDK (claude-opus-4.6)*
