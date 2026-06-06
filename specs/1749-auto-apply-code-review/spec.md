# Feature Specification: Auto-apply Code Review Suggestions via GraphQL in AI PR Loop

**Feature Branch**: `speckit/1749/phase-2-clarify`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: User description: "Implement an automated step in the ai-pr-loop workflow to programmatically apply all available autofixable GitHub PR review suggestions using the GraphQL
`createCommitOnBranch` mutation before dispatching an AI repair job."  
**Source Issue**: #1749 (<https://github.com/ayaiayorg/agentic-devtools/issues/1749>)

---

## Clarifications

### Session 2026-06-03

- Q: Should the maximum suggestion batch size threshold (FR-011) be configurable per-repository via `.github/agdt-config.json`, or is a hardcoded default of 50 sufficient for the initial
  implementation? → A: A hardcoded threshold of 50 is sufficient for the initial implementation. Per-repository configuration via `.github/agdt-config.json` should be deferred to a follow-up iteration
  once production usage patterns are observed.

- Q: In the partial-apply + repair-dispatched path, should `SquashAction` squash the autofix commit together with the repair agent's commit in the same loop run, or should it defer until a subsequent
  run? → A: `SquashAction` should defer squash when `repair_dispatched` is True (it already does via its `no_repair_dispatched` precondition). In the "all suggestions auto-applied, no repair" path,
  `SquashAction` will squash normally since `repair_dispatched` is False. In the partial-apply + repair path, `SquashAction` defers in the current run and squashes all commits (autofix + repair) on
  the next run after the repair agent completes. No behavioral change to `SquashAction` is required.

- Q: Should `ApplySuggestionsAction` set `invalidates_snapshot = True` on its `ActionResult` when it successfully commits, causing the pipeline runner to refresh the snapshot before evaluating
  `DispatchRepairAction`? → A: Yes. When `ApplySuggestionsAction` successfully applies suggestions and produces a commit, it MUST set `invalidates_snapshot = True` on its `ActionResult`. This ensures
  `DispatchRepairAction` evaluates against the refreshed post-commit state (new HEAD SHA, updated CI status, updated review thread resolution). `DispatchRepairAction` must have
  `runs_after_invalidation = True` to opt into the refreshed snapshot path.

- Q: How does the system identify which review comment IDs to pass to repair dispatch for exclusion — by the suggestion's GraphQL node ID, or by the parent review comment's database ID (`databaseId`)?
  → A: The exclusion context uses the parent review comment's REST API numeric ID (`databaseId` from GraphQL), since `provider.list_review_comments()` in the repair dispatch already works with REST
  API comment IDs. The `ExclusionContext.resolved_comment_ids` field stores these numeric IDs.

- Q: When bisection fallback produces multiple mutation calls, should each successful call produce its own commit, or should the action attempt to consolidate into a single commit? → A: Each
  successful `createCommitOnBranch` mutation call produces its own commit (this is GitHub API behavior — each mutation creates one commit). The `ApplySuggestionsResult.commit_shas` list captures all
  commits produced. `SquashAction` will consolidate them on a subsequent run. The action should NOT attempt manual squashing; it relies on the existing pipeline squash mechanism.

---

## Problem Statement

The AI PR Loop (`ai-pr-loop.yml`) currently treats all actionable Copilot review comments uniformly — when a review with suggestions lands, the pipeline dispatches a full agentic repair job that must
read each comment, understand the suggested change, apply it manually in code, commit, and push. This approach works but introduces unnecessary overhead for a significant subset of review feedback:
suggestions that GitHub renders as autofixable diffs. These suggestions carry explicit replacement code that can be extracted from markdown ` ```suggestion ` blocks and applied programmatically via the
`createCommitOnBranch` GraphQL mutation.

The inefficiency manifests in three dimensions. First, AI agent tokens and compute cycles are consumed processing suggestions whose resolution is deterministic and requires no reasoning. A suggestion
with explicit replacement code is, by definition, a solved problem — the reviewer has already written the fix. Passing this to an AI repair agent is analogous to asking a software engineer to retype
code that has already been authored by the reviewer. Second, the time-to-convergence for PRs increases because the repair agent must clone the repository, start a Copilot session, process all comments
sequentially, and push a commit — a pipeline that takes several minutes even for trivial fixes. Applying structured suggestions via a single GraphQL call would reduce this to seconds. Third, the
current approach cannot distinguish between suggestions that were applied by the autofix step and those that require creative problem-solving by the repair agent, leading to potential double-handling
where the repair agent attempts to re-address comments whose suggested changes have already been committed.

The desired state is a new pipeline action — positioned between the guards evaluation and the repair dispatch action in the AI PR Loop's action sequence — that identifies all non-outdated, autofixable
suggestions on the current PR head, applies them in a single batched commit via GraphQL, and then re-evaluates whether a full repair dispatch is still necessary. If the batch application resolves all
actionable review threads and CI passes on the new commit, the loop should skip repair entirely. If some comments remain unresolved or CI still fails, the repair dispatch proceeds but explicitly
excludes the already-applied review comment IDs (root thread comments) from its context, preventing redundant work.

---

## User Scenarios & Testing

### User Story 1 — Batch Apply All Autofixable Suggestions (Priority: P1)

As a developer whose PR has received a Copilot review containing one or more code suggestions with explicit replacement code, I want the AI PR Loop to automatically apply all valid suggestions in a
single commit before considering a full repair dispatch, so that deterministic fixes are applied instantly without consuming AI agent time or my attention.

**Why this priority**: This is the core value proposition of the feature. The majority of Copilot review suggestions include explicit replacement code (e.g., "rename this variable", "add a missing
import", "use this null-safe pattern"). Batch-applying these via GraphQL is the highest-impact change — it eliminates the most common class of repair dispatches entirely and delivers the fastest path
to PR convergence.

**Independent Test**: Can be fully tested by creating a PR that triggers a Copilot review with three suggestions containing replacement code, running the AI PR Loop pipeline, and verifying that all
three suggestions are applied in a single commit, the corresponding review threads are resolved, and no repair job is dispatched if CI passes afterward.

**Acceptance Scenarios**:

1. **Given** a PR with 4 non-outdated Copilot review suggestions each containing replacement code and no other actionable comments, **When** the AI PR Loop runs the apply-suggestions action, **Then**
   all 4 suggestions are applied in a single commit attributed to the bot PAT user, the 4 review threads are marked resolved, and the repair dispatch action evaluates to SKIP because no actionable
   comments remain.

2. **Given** a PR with 2 autofixable suggestions and CI currently passing on the head commit, **When** the AI PR Loop applies the suggestions successfully, **Then** a new commit appears on the PR
   branch, the pipeline waits for CI to run on the new commit, and if CI passes, the loop proceeds toward merge without dispatching repair.

3. **Given** a PR with 0 autofixable suggestions (all comments are prose feedback without replacement code), **When** the AI PR Loop evaluates the apply-suggestions action, **Then** the action returns
   SKIP with a clear reason indicating no applicable suggestions were found, and the pipeline proceeds to the repair dispatch evaluation unchanged.

---

### User Story 2 — Graceful Fallback on Partial Application Failure (Priority: P1)

As a pipeline operator, I want the auto-apply step to handle conflicts and outdated suggestions gracefully by applying as many valid suggestions as possible and clearly reporting which could not be
applied, so that the pipeline never fails fatally due to suggestion state issues and the repair agent receives accurate context about what remains unresolved.

**Why this priority**: In practice, suggestion application can fail due to overlapping hunks (two suggestions modifying the same lines), suggestions that became outdated between the review being
posted and the loop running, or race conditions where a human pushed new commits. Handling these failures gracefully is essential for production reliability — without this, the feature would be
fragile and could block the entire PR pipeline on transient conditions.

**Independent Test**: Can be tested by mocking GraphQL responses that return partial errors (e.g., 3 of 5 suggestion IDs fail with conflict errors), verifying that the action retries with the
remaining 2, commits those successfully, and passes the 3 failed suggestion IDs to the repair dispatch context.

**Acceptance Scenarios**:

1. **Given** a PR with 5 autofixable suggestions where 2 have overlapping hunks that conflict with each other, **When** the batch apply mutation returns a conflict error, **Then** the action falls
   back to a bisection strategy that identifies and applies the 3 non-conflicting suggestions in a subsequent mutation call, reports the 2 conflicting suggestions as unresolvable by autofix, and
   includes them in the repair dispatch context.

2. **Given** a PR with 3 suggestions where 1 has become outdated (the `outdated` field is `true`), **When** the action queries suggestion nodes, **Then** the outdated suggestion is excluded from the
   batch before mutation, only the 2 valid suggestions are applied, and the outdated suggestion is logged as skipped for auto-apply while remaining eligible for repair-dispatch review context.

3. **Given** a transient GitHub API error (e.g., 502 gateway timeout) during the apply mutation, **When** the action encounters the error, **Then** it retries up to 2 times with exponential backoff,
   and if all retries fail, it returns a SKIP result (logging the error at `ERROR` level) so that the pipeline continues and repair dispatch proceeds as if no autofix was attempted. (Returning
   `FAILED` would halt the pipeline via the "Pipeline halted" mechanism and prevent repair dispatch from running.)

---

### User Story 3 — Exclusion of Applied Suggestions from Repair Dispatch (Priority: P2)

As a developer, I want the repair agent to receive only the review comments that were NOT successfully auto-applied, so that the agent does not waste time re-implementing fixes that are already
committed and does not create merge conflicts with the autofix commit.

**Why this priority**: This story depends on User Story 1 being implemented first. Its value is in preventing redundant work and potential conflicts between the autofix commit and the repair agent's
commit. Without this exclusion logic, the repair agent might attempt to apply the same change that was already committed, leading to duplicated code or merge conflicts.

**Independent Test**: Can be tested by running a scenario where 3 of 5 suggestions are auto-applied, then verifying that the repair dispatch's `review_comments` list contains only the 2 remaining
comments, and the repair agent's prompt excludes the 3 resolved review comment IDs (root thread comments).

**Acceptance Scenarios**:

1. **Given** 5 actionable review comments where 3 are autofixable suggestions that were successfully applied, **When** the repair dispatch action fetches review comments, **Then** the
   `review_comments` list excludes the 3 resolved comments and contains only the 2 unresolved ones, and the repair type is correctly set to "review" (not "both" unless CI also fails).

2. **Given** all actionable review comments were successfully auto-applied and CI passes on the resulting commit, **When** the repair dispatch action evaluates preconditions, **Then** `needs_repair`
   is `False` and the action returns SKIP, preventing any repair dispatch.

---

### User Story 4 — Safety Guards for Privileged Paths and Forks (Priority: P2)

As a repository maintainer, I want the auto-apply suggestions step to respect the same safety guards as the repair dispatch (privileged paths, fork PRs, exclusion labels), so that automated commits
are never made to PRs that touch sensitive infrastructure files or originate from untrusted sources.

**Why this priority**: Security and trust boundaries must be maintained. The existing guards in `GuardsAction` already gate the repair dispatch, but since the new apply-suggestions action produces
commits (not just comments), it carries higher risk and must be equally guarded. This is a prerequisite for production deployment but not the core algorithmic challenge.

**Independent Test**: Can be tested by creating a PR that modifies `.github/workflows/ci.yml` (a privileged path), triggering a review with suggestions, and verifying that the apply-suggestions action
returns SKIP with a guard-blocked reason.

**Acceptance Scenarios**:

1. **Given** a PR from a fork repository that has received autofixable suggestions, **When** the AI PR Loop evaluates the apply-suggestions action, **Then** the action returns SKIP with details
   indicating "fork PR — skipping autofix", and the pipeline falls through to repair dispatch evaluation.

2. **Given** a PR that modifies files under `.github/workflows/` and has autofixable suggestions on those files, **When** the AI PR Loop evaluates the apply-suggestions action, **Then** the action
   returns SKIP because privileged paths are touched, regardless of whether the suggestions target the privileged files or other files in the same PR.

---

### User Story 5 — Summary Comment for Transparency (Priority: P3)

As a developer reviewing the PR timeline, I want a brief summary comment posted after suggestions are auto-applied, listing which suggestions were committed and which (if any) could not be applied, so
that I have a clear audit trail of automated actions taken on my PR.

**Why this priority**: This is a transparency and UX improvement rather than a functional requirement. The feature works without it, but the summary comment helps developers understand what happened
during automated processing, especially when reviewing the PR timeline after the fact. This can be deferred to a follow-up iteration if needed.

**Independent Test**: Can be tested by applying suggestions and verifying that a comment appears on the PR with the expected format, listing applied suggestion IDs and any skipped ones with reasons.

**Acceptance Scenarios**:

1. **Given** 4 suggestions were successfully batch-applied, **When** the apply-suggestions action completes, **Then** a PR comment is posted in the format: "🔧 **Auto-applied N suggestions** in commit
   `abc1234`.\n\n- Applied: [list of thread URLs]\n- Skipped: none" with the commit SHA linked to the commit.

2. **Given** 2 of 4 suggestions were applied and 2 were skipped due to conflicts, **When** the action completes, **Then** the summary comment lists the 2 applied suggestions and the 2 skipped
   suggestions with their skip reasons (e.g., "conflicting hunks", "outdated").

---

### Edge Cases

The system must handle the following boundary conditions:

- **Deleted file reference**: When a suggestion references a file that was deleted in a subsequent commit pushed between review and loop execution, the action should detect this via thread
  `isOutdated` or mutation error and exclude the suggestion gracefully, logging it as skipped with reason "file deleted / outdated".

- **Single conflicting suggestion**: When the PR has exactly one suggestion and it conflicts, the bisection fallback should degrade gracefully to a no-op since there is nothing left to split, and the
  single suggestion passes through to repair dispatch.

- **Branch protection violation**: When the `createCommitOnBranch` mutation succeeds but the resulting commit triggers a branch protection rule violation (e.g., required status checks), the pipeline
  should treat this as any other post-commit state and re-evaluate CI status in the next loop iteration. The `invalidates_snapshot = True` flag refreshes pipeline state; only actions that opt in via
  `runs_after_invalidation=True` continue in the same run.

- **Concurrent loop executions**: When two instances attempt to apply the same suggestions, the deduplication guard (existing `check_deduplication` mechanism) should prevent double-application, and
  the GraphQL mutation itself is idempotent for already-resolved suggestions (returning a no-op or error that the action handles gracefully).

- **Bisection producing multiple commits**: When bisection fallback applies suggestions in multiple mutation calls, each call produces one commit (GitHub API behavior). The `commit_shas` list in
  `ApplySuggestionsResult` records all produced commits. `SquashAction` consolidates them on a subsequent pipeline run. The action does NOT attempt manual squashing.

---

## Requirements

### Functional Requirements

- **FR-001**: The system MUST query the GitHub GraphQL API to retrieve unresolved review-thread comments and detect apply-able suggestions via markdown body fence parsing
  (```` ```suggestion ````) combined with comment location fields (`path`, `line`, `startLine`).

- **FR-002**: The system MUST attempt to apply all valid suggestions in a single `createCommitOnBranch` GraphQL mutation call, producing exactly one commit when the batch succeeds without conflicts.

- **FR-003**: When the batch mutation fails due to conflicting hunks or partial errors, the system MUST fall back to a bisection strategy that subdivides the suggestion set and retries application of
  non-conflicting subsets, minimizing the number of API calls while maximizing the number of successfully applied suggestions.

- **FR-004**: The system MUST exclude suggestions from outdated threads (`isOutdated: true`) from any application attempt and log them as skipped for auto-apply; this exclusion MUST NOT, by itself,
  remove their parent review comments from repair dispatch context.

- **FR-005**: The system MUST record the `databaseId` of each `PullRequestReviewComment` node that contains an applied suggestion (i.e., the `reviewComment.databaseId` REST API numeric ID) and pass
  those IDs to the repair dispatch action via `ExclusionContext` so that `provider.list_review_comments()` can exclude those comments from the repair context.

- **FR-006**: The system MUST re-evaluate whether repair dispatch is necessary after suggestions are applied — if no unresolved actionable comments remain AND CI is not failing, the repair dispatch
  action MUST return SKIP. This re-evaluation is facilitated by `invalidates_snapshot = True` on the apply-suggestions `ActionResult`, which triggers a snapshot refresh before `DispatchRepairAction`
  evaluates.

- **FR-007**: The apply-suggestions action MUST be positioned after `GuardsAction` in the pipeline sequence so that the pipeline runner's existing guard-blocking mechanism applies. When any guard
  fires (`GuardsAction` returns `ActionDecision.BLOCKED`), the pipeline runner marks the apply-suggestions action as `ActionDecision.BLOCKED_BY_GUARD` and never evaluates or executes it, ensuring
  no mutations are attempted. The full guard set enforced by `GuardsAction` is: WIP title, no-changes, fork PR, exclusion label, privileged paths, and Docker files.

- **FR-008**: The system MUST attribute the autofix commit to the bot PAT user (the same identity used by the AI PR Loop for all automated operations), maintaining consistency with existing commit
  attribution patterns.

- **FR-009**: The system MUST be positioned in the pipeline action sequence after `GuardsAction` evaluation and before `DispatchRepairAction`, ensuring guards are checked first and repair dispatch
  receives the updated post-autofix state.

- **FR-010**: The system MUST handle GitHub API rate limits and transient errors (5xx responses) with retry logic (up to 2 retries with exponential backoff, starting at 1 second) before reporting
  failure. On exhausted retries, the action returns `ActionDecision.SKIP` (not `FAILED`) to avoid halting the pipeline.

- **FR-011**: The system MUST NOT apply suggestions when the total number of applicable suggestions exceeds a hardcoded safety threshold of 50, logging a warning and deferring to repair dispatch
  instead. This prevents runaway batch commits on PRs with an unusually high suggestion count that may indicate a systemic review pattern requiring human judgment. Per-repository configurability via
  `.github/agdt-config.json` is deferred to a follow-up iteration.

- **FR-012**: When the apply-suggestions action successfully produces one or more commits, it MUST set `invalidates_snapshot = True` on its `ActionResult`, causing the pipeline runner to refresh the
  `PRStateSnapshot` before evaluating subsequent actions (specifically `DispatchRepairAction`).

- **FR-013**: `DispatchRepairAction` MUST have `runs_after_invalidation = True` to opt into the refreshed snapshot path when `ApplySuggestionsAction` invalidates the snapshot.

### Non-Functional Requirements

- **NFR-001**: The apply-suggestions action MUST complete within 30 seconds for PRs with up to 20 suggestions (excluding network latency variance), ensuring it does not significantly extend the AI PR
  Loop's total execution time compared to the existing repair-dispatch-only path.

- **NFR-002**: The action MUST produce structured logging output consistent with the existing pipeline action pattern (`logger.info` for decisions, `logger.warning` for recoverable errors,
  `logger.error` for failures), enabling debugging via the same log analysis tools used for other actions.

- **NFR-003**: The action MUST follow the existing `ActionResult` return pattern
  (with `ActionDecision.EXECUTE`, `SKIP`, `FAILED`, `BLOCKED`,
  or `BLOCKED_BY_GUARD`) and populate `preconditions` and `details` fields,
  maintaining CLI UX consistency with all other pipeline actions.

- **NFR-004**: The GraphQL queries and mutations MUST use pagination (handling PRs with more than 100 review threads) and MUST not assume a maximum number of suggestions per comment.

### Key Entities

- **SuggestedChange**: Represents a single autofixable code change proposed in a review comment. Key attributes: `id` (GraphQL node ID), `outdated` (boolean indicating staleness), parent
  `reviewComment.databaseId` (REST API numeric ID from the parent `PullRequestReviewComment`, used for exclusions), parent `reviewThread` (for thread resolution tracking).

- **ApplySuggestionsResult**: The output of the apply-suggestions action,
  containing: `applied_ids` (list of successfully applied suggestion IDs),
  `skipped_ids` (list of suggestions excluded due to outdated status or
  conflicts), `commit_shas` (ordered list of autofix commit SHAs produced by
  batch and/or fallback application — each `createCommitOnBranch` mutation call produces exactly one commit, so multiple entries indicate bisection fallback was used; empty when nothing was applied),
  `error`
  (optional error detail for partial failures).

- **ExclusionContext**: Data structure passed from the apply-suggestions action
  to the repair dispatch action via `DerivedState`, containing the set of resolved review comment
  IDs (parent review comment REST API numeric IDs / `databaseId`) that should be excluded from repair comment
  fetching.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: For PRs where all actionable review comments are autofixable
  suggestions, the system achieves zero repair dispatches — meaning 100% of
  such PRs converge without triggering the repair agent, measured across a
  2-week production observation period.

- **SC-002**: The batch application of suggestions produces exactly 1 commit per successful action execution in at least 90% of cases (the remaining 10% accounts for bisection fallback scenarios
  requiring multiple mutations, each producing one commit; `SquashAction` consolidates them on a subsequent run).

- **SC-003**: The apply-suggestions action adds no more than 10 seconds of wall-clock time to the AI PR Loop execution for PRs with 10 or fewer suggestions, as measured by action-level timing
  instrumentation.

- **SC-004**: The repair dispatch action's `review_comments` list correctly excludes 100% of review comment IDs (parent review comment REST API numeric IDs) that were auto-applied, verified by unit
  tests covering the
  exclusion logic with at least 95% branch coverage on the new action module.

- **SC-005**: Zero false positives on guard enforcement — the action MUST never produce a commit on a fork PR or a PR touching privileged paths, validated by integration tests that assert SKIP on
  guarded scenarios.

- **SC-006**: The bisection fallback strategy successfully applies at least 60% of originally valid suggestions in scenarios where the full batch fails due to 1-2 conflicting pairs, measured by unit
  tests with mock conflict responses.

- **SC-007**: Test coverage for the new `ApplySuggestionsAction` module achieves 100% branch coverage, consistent with the project's existing coverage requirements enforced by `agdt-test-file`.

---

## Open Questions

- **Resolved** (see Clarifications): `SquashAction` already squashes when `commit_count > 1`, no repair was dispatched, and no Copilot session is active; in the "all suggestions auto-applied, no
  repair" path this already produces a single commit in the same loop run. In the partial-apply + repair-dispatched path, `SquashAction` defers (via its `no_repair_dispatched` precondition) and
  squashes all commits on the next run after repair completes.

- **Resolved** (see Clarifications): The maximum suggestion batch size threshold (FR-011) uses a hardcoded default of 50 for the initial implementation. Per-repository configurability is deferred to a
  follow-up iteration.

---
*Generated by Copilot SDK (claude-opus-4.6)*
