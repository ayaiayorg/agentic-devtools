# Feature Specification: ai-pr-loop Complete Should State — Event-Driven PR Lifecycle Automation

**Feature Branch**: `speckit/1509/phase-2-clarify`
**Created**: 2026-05-21
**Status**: Draft
**Source Issue**: #1509 (<https://github.com/ayaiayorg/agentic-devtools/issues/1509>)

## Problem Statement

The ai-pr-loop currently handles the core PR lifecycle (publish, squash, review dispatch, approve, merge) but has several gaps that require manual intervention or produce suboptimal results:

1. **Thread resolution is unconditional** — after a Copilot coding agent pushes fixes, all review threads are resolved without evaluating whether the change actually addresses the comment. This can
   lead to unaddressed feedback being silently dismissed.
2. **Merge strategy is squash instead of rebase** — since commits are already squashed in step 2, the merge step should use rebase to preserve the carefully generated commit message. Currently it uses
   squash merge, which may alter the message.
3. **Conflict resolution context is limited** — the Copilot SDK receives only the conflicted file content but not the three-way merge versions (`:1:`, `:2:`, `:3:`) or commit messages that touched the
   file, reducing resolution quality.
4. **No post-conflict test validation** — after conflict resolution, the force-push happens without verifying tests still pass, potentially introducing broken code to the PR branch.
5. **Commit message generation lacks full context** — the SDK doesn't receive the full PR diff summary or `COMMIT_CONVENTION.md` content, leading to less descriptive commit messages.
6. **Copilot review re-trigger is not verified** — after a force-push from the human PAT, there's no verification that a Copilot review is actually triggered, and no fallback mechanism if it isn't.
7. **Workflow approval monitor is unimplemented** — workflow runs stuck in `action_required` state require manual approval; the spec exists (#1393) but implementation is missing.

## Scope

**In scope:**

- Copilot SDK evaluation of review comment threads before resolution
- Changing merge strategy from squash to rebase
- Enriching conflict resolution SDK prompts with three-way merge context
- Adding post-conflict-resolution test validation
- Enriching commit message generation with full diff and convention context
- Copilot review re-trigger verification and fallback mechanism
- Workflow approval monitor implementation

**Out of scope:**

- Changes to the squash-wait scheduler timing or detection mechanism
- Changes to guard logic (fork detection, label checks, cycle limits)
- Changes to the Copilot coding agent dispatch mechanism
- UI/UX changes to the PR comments or review formatting
- Changes to secrets/token management

---

## Clarifications

### Session 2026-05-22

- Q: Should the post-conflict test run execute the full test suite or a subset (e.g., only tests related to changed files)? Full suite provides higher confidence but may exceed the 5-minute timeout
  for large projects. → A: Run the full test suite (via the existing `scripts/run-pr-checks.sh` or the project's CI test command). The 5-minute timeout provides the safety valve — if the full suite
  exceeds it, the system proceeds with force-push and logs a warning (graceful degradation). This matches NFR-002's existing specification and avoids the complexity of determining "related tests"
  which is error-prone.

- Q: Should the workflow approval monitor be a standalone workflow (`workflow-approval-monitor.yml`) or integrated into the existing `ai-pr-loop.yml` as an additional trigger path? → A: Implement as a
  standalone workflow (`workflow-approval-monitor.yml`) triggered on `schedule` (every 5 minutes) and `workflow_dispatch`. This avoids complicating the existing `ai-pr-loop.yml` concurrency model and
  event filtering, keeps concerns separated, and allows independent iteration on the approval monitor without risk to the core loop. The monitor's Python implementation lives in
  `agentic_devtools/cli/ci/` alongside the existing provider/orchestrator.

- Q: When the SDK evaluation for thread resolution returns "ambiguous", should the system retry with additional context (e.g., full file content instead of just diff), or leave the thread unresolved
  immediately? → A: Leave the thread unresolved immediately on "ambiguous" — do not retry with enriched context. Rationale: (1) the fail-safe principle (FR-002) favors leaving threads open over
  risking false resolution; (2) adding retry-with-enriched-context doubles token cost and increases per-thread latency toward the 30-second NFR-001 timeout; (3) unresolved threads will be re-evaluated
  on the next loop iteration when the coding agent may have made additional changes. The "ambiguous" response and raw SDK output are logged for post-hoc debugging.

- Q: What is the expected behavior when `merge_pr()` is called with `"rebase"` strategy but the PR has more than one commit (e.g., due to a race condition where the coding agent pushes between squash
  and merge)? → A: The orchestrator already re-counts commits above merge-base before proceeding to merge (via `count_commits_above_merge_base`). If the commit count is >1 at merge time, the system
  MUST re-trigger the squash step and exit the current iteration rather than attempting a rebase merge with multiple commits. This preserves the invariant that rebase merge always operates on a single
  commit. Add an explicit guard before `merge_pr()` that verifies `commit_count == 1`.

- Q: For the Copilot review re-trigger verification (FR-011), what polling mechanism should be used — a loop within the workflow step, or a separate delayed step? → A: Use a polling loop within the
  same workflow job step (the `squash_post_repair` method). After the force-push completes, poll `agdt-gh-copilot-review-status` every 10 seconds for up to 60 seconds. If no review appears, call
  `request_copilot_review()` explicitly and then poll for an additional 60 seconds. This keeps the logic self-contained in the provider method and avoids needing an additional workflow trigger or
  step. The existing `_request_copilot_review` import in `github_provider.py` already supports this pattern.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — SDK-Based Thread Evaluation Before Resolution (Priority: P1)

As a PR author relying on the ai-pr-loop, I want the system to evaluate whether each Copilot review comment was actually addressed by the coding agent's fix before resolving the thread, so that
unaddressed feedback is not silently dismissed.

**Why this priority**: This is the most impactful gap — unconditional thread resolution can mask real issues that the coding agent failed to address, leading to merged PRs with unresolved feedback.

**Independent Test**: Can be tested by mocking the Copilot SDK to return "addressed" or "not_addressed" for different comment/diff pairs and verifying threads are only resolved when the SDK confirms
the fix.

**Acceptance Scenarios**:

1. **Given** a Copilot review comment requesting a null check on line 42 and the coding agent adds a null check on that line, **When** the SDK evaluates the comment against the latest diff, **Then**
   the evaluation returns "addressed" and the thread is resolved.

2. **Given** a Copilot review comment requesting error handling and the coding agent pushes a commit that doesn't modify the relevant file, **When** the SDK evaluates the comment, **Then** the
   evaluation returns "not_addressed" and the thread remains unresolved.

3. **Given** a Copilot review comment and the coding agent leaves an explanation comment without code changes, **When** the SDK evaluates the comment with the agent's response, **Then** the evaluation
   considers the explanation and may return "addressed" if the reasoning is sound.

4. **Given** the SDK evaluation times out (>30 seconds), **When** the timeout is detected, **Then** the thread is left unresolved (fail-safe: don't resolve without confirmation).

5. **Given** the SDK returns an ambiguous or unparseable response, **When** the response is processed, **Then** the thread is left unresolved immediately (no retry with enriched context) and the raw
   response is logged for debugging.

---

### User Story 2 — Rebase Merge Strategy (Priority: P1)

As a repository maintainer, I want the ai-pr-loop to use rebase merge (not squash merge) when merging approved PRs, so that the carefully generated commit message from the squash step is preserved
exactly as-is in the target branch history.

**Why this priority**: The current squash merge may alter the commit message that was carefully generated via the Copilot SDK in step 2. Since commits are already squashed to a single commit before
merge, rebase merge preserves the message verbatim.

**Independent Test**: Can be tested by verifying the merge API call uses `--rebase` instead of `--squash` and that the resulting commit on the target branch has the exact same message as the PR branch
commit.

**Acceptance Scenarios**:

1. **Given** a PR with a single squashed commit and all merge conditions met, **When** the ai-pr-loop executes the merge, **Then** `merge_pr()` is called with strategy `"rebase"` instead of
   `"squash"`.

2. **Given** a successful rebase merge, **When** the target branch is inspected, **Then** the commit message matches exactly the message generated by the Copilot SDK during the squash step.

3. **Given** a PR where rebase merge fails due to conflicts with the target branch, **When** the failure is detected, **Then** the system logs the error and does NOT fall back to squash merge
   automatically (requires a new squash+rebase cycle).

4. **Given** a PR with more than one commit at merge time (race condition), **When** the orchestrator detects `commit_count > 1` before calling `merge_pr()`, **Then** the system re-triggers the squash
   step and exits the current iteration without attempting the merge.

---

### User Story 3 — Enriched Conflict Resolution Context (Priority: P1)

As a developer whose PR encounters merge conflicts during the rebase step, I want the Copilot SDK to receive the three-way merge versions and commit intent context, so that conflict resolution
produces semantically correct results.

**Why this priority**: The current conflict resolution only provides the conflicted file content with markers. Providing the common ancestor, ours, and theirs versions (plus commit messages)
significantly improves the SDK's ability to understand what each side intended.

**Independent Test**: Can be tested by verifying the SDK prompt includes the three git stages (`:1:`, `:2:`, `:3:`) and relevant commit messages for each conflicted file.

**Acceptance Scenarios**:

1. **Given** a conflicted file during rebase, **When** the SDK is invoked for resolution, **Then** the prompt includes the common ancestor version (`git show :1:<path>`), the ours version (`git show
   :2:<path>`), and the theirs version (`git show :3:<path>`).

2. **Given** a conflicted file, **When** the SDK is invoked, **Then** the prompt includes commit messages from both branches that modified the file (obtained via `git log --oneline -- <path>`).

3. **Given** a JSON file with conflicts, **When** the SDK resolves it, **Then** the prompt includes a hint to merge and re-sort keys (file-type-specific strategy).

4. **Given** a Markdown file with conflicts, **When** the SDK resolves it, **Then** the prompt includes a hint to preserve section numbering and heading hierarchy.

---

### User Story 4 — Post-Conflict Test Validation (Priority: P2)

As a repository maintainer, I want the system to run tests after conflict resolution and before force-pushing, so that broken code from a bad resolution is not pushed to the PR branch.

**Why this priority**: Force-pushing broken code after conflict resolution wastes a full review cycle (Copilot reviews broken code, dispatches repair, etc.). A quick test run catches resolution errors
early.

**Independent Test**: Can be tested by mocking the test runner to return success/failure and verifying the force-push only proceeds on test success.

**Acceptance Scenarios**:

1. **Given** conflict resolution succeeds and tests pass (full test suite via the project's CI test command), **When** the post-resolution validation completes, **Then** the force-push proceeds
   normally.

2. **Given** conflict resolution succeeds but tests fail, **When** the failure is detected, **Then** the rebase is aborted (`git rebase --abort`), the original squashed commit is preserved, and a
   warning comment is posted on the PR.

3. **Given** the test run times out (>5 minutes), **When** the timeout is detected, **Then** the force-push proceeds with a warning log (graceful degradation: don't block indefinitely on test
   infrastructure issues).

---

### User Story 5 — Richer Commit Message Generation (Priority: P2)

As a repository maintainer, I want the Copilot SDK to receive the full PR diff summary and repository commit conventions when generating the squash commit message, so that messages are more
descriptive and consistently follow conventions.

**Why this priority**: The current SDK call has limited context. Providing the full diff summary and `COMMIT_CONVENTION.md` content enables more accurate type selection, scope identification, and body
content.

**Independent Test**: Can be tested by verifying the SDK prompt includes the diff stat summary and the content of `COMMIT_CONVENTION.md`.

**Acceptance Scenarios**:

1. **Given** a PR with changes across 5 files, **When** the commit message is generated via SDK, **Then** the prompt includes a `git diff --stat` summary of all changed files.

2. **Given** the repository has a `COMMIT_CONVENTION.md` file, **When** the SDK is invoked, **Then** the prompt includes the full content of `COMMIT_CONVENTION.md` as reference for format rules.

3. **Given** the SDK generates a message following conventions, **When** the message is validated, **Then** it passes Conventional Commit format checks (type, scope with issue link, subject ≤100
   chars).

---

### User Story 6 — Copilot Review Re-Trigger Verification (Priority: P2)

As a pipeline operator, I want the system to verify that a Copilot review is actually triggered after a force-push and fall back to explicit review request if not, so that the review cycle is never
blocked waiting for a review that never arrives.

**Why this priority**: The force-push from the human PAT is the primary mechanism for triggering a new Copilot review, but there's no guarantee it works every time. Without verification and fallback,
the loop can stall indefinitely.

**Independent Test**: Can be tested by mocking the review status check to return "no review pending" after the force-push window and verifying the fallback `request_copilot_review()` is called.

**Acceptance Scenarios**:

1. **Given** a force-push is completed successfully, **When** a Copilot review appears within 60 seconds (polled every 10 seconds via `agdt-gh-copilot-review-status`), **Then** no fallback action is
   taken and the loop proceeds normally.

2. **Given** a force-push is completed but no Copilot review appears within 60 seconds, **When** the timeout fires, **Then** `request_copilot_review()` is called explicitly as a fallback.

3. **Given** both the force-push and explicit review request fail to trigger a review within 120 seconds total, **When** the extended timeout fires, **Then** a warning comment is posted on the PR and
   the current loop iteration exits (will retry on next event).

---

### User Story 7 — Workflow Approval Monitor (Priority: P3)

As a repository maintainer, I want stuck workflow runs in `action_required` state to be automatically approved for PRs authored by trusted bots, so that the CI/review cycle is never blocked by manual
approval requirements.

**Why this priority**: This is a known blocker (#1393) but is lower priority because a workaround exists (manual click) and the implementation requires careful security consideration (which bots to
trust, which workflows to approve).

**Independent Test**: Can be tested by mocking the GitHub Actions API to return runs in `action_required` state and verifying the approval API is called for trusted bot PRs.

**Acceptance Scenarios**:

1. **Given** a workflow run is stuck in `action_required` state for a PR authored by a trusted bot (listed in `.github/ai-pr-loop-config.json`), **When** the monitor runs, **Then** the workflow is
   approved via `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve`.

2. **Given** a workflow run is stuck for a PR authored by a non-trusted actor, **When** the monitor runs, **Then** no automatic approval occurs.

3. **Given** the approval API returns a failure after 3 retries, **When** retries are exhausted, **Then** a failure comment is posted on the associated PR.

4. **Given** a workflow run is already `completed` or `in_progress`, **When** the monitor runs, **Then** it is skipped (only `action_required` runs are processed).

---

### Edge Cases

- **What happens when the SDK evaluation for thread resolution is unavailable (SDK down)?** The system falls back to NOT resolving threads (fail-safe). Threads remain open and will be evaluated on the
  next loop iteration.

- **What happens when a rebase merge has conflicts with the target branch at merge time?** The merge fails, the loop exits this iteration, and on the next trigger the squash+rebase cycle runs again
  with the latest `origin/main`.

- **What happens when the test suite is flaky and fails after conflict resolution?** The system aborts the rebase, preserves the original commit, and does not force-push in that iteration. It posts a
  warning comment on the PR and retries the full squash+rebase cycle on a later trigger.

- **What happens when the commit conventions file doesn't exist?** The SDK call proceeds without convention context, using only the diff summary. A warning is logged.

- **What happens when no workflow runs are in `action_required` state?** The monitor exits cleanly with no action taken (idempotent no-op).

- **What happens when the force-push fails (e.g., branch protection, network error)?** The error is caught, logged, and a comment is posted on the PR. The loop exits this iteration and will retry on
  the next event.

- **What happens when the PR has more than one commit at merge time due to a race condition?** The orchestrator re-triggers the squash step and exits the current iteration without attempting the
  merge. The next cycle will squash and proceed normally.

- **What happens when the SDK evaluation returns "ambiguous"?** The thread is left unresolved immediately (no retry with enriched context). The raw SDK response is logged. The thread will be
  re-evaluated on the next loop iteration after additional changes.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST evaluate each Copilot review comment thread via the Copilot SDK before resolving, providing the SDK with the file diff, comment content, and any agent response comment.

- **FR-002**: The system MUST only resolve a thread when the SDK evaluation confirms the comment was adequately addressed (verdict: "addressed"); threads with "not_addressed" or "ambiguous" verdicts
  MUST remain open without retry.

- **FR-003**: The system MUST use rebase merge strategy (not squash) when merging approved PRs, since commits are already squashed in the force-push step.

- **FR-003a**: The system MUST verify that the PR has exactly one commit above the merge-base before calling `merge_pr()` with rebase strategy; if commit count is >1, the system MUST re-trigger the
  squash step and exit the current iteration.

- **FR-004**: The system MUST provide the Copilot SDK with three-way merge context (common ancestor `:1:`, ours `:2:`, theirs `:3:`) for each conflicted file during conflict resolution.

- **FR-005**: The system MUST provide commit messages that touched the conflicted file from both branches to give the SDK intent context.

- **FR-006**: The system MUST include file-type-specific resolution hints in the SDK conflict resolution prompt (JSON: merge + re-sort; Markdown: preserve numbering; Code: preserve both logical
  changes).

- **FR-007**: The system MUST run the project's full test suite after conflict resolution and before force-pushing the resolved commit, using the same test command as CI (e.g.,
  `scripts/run-pr-checks.sh` or equivalent).

- **FR-008**: The system MUST abort the rebase and preserve the original commit if post-resolution tests fail, posting a warning comment on the PR.

- **FR-009**: The system MUST include a `git diff --stat` summary in the commit message generation SDK prompt.

- **FR-010**: The system MUST include the content of `COMMIT_CONVENTION.md` in the commit message generation SDK prompt when the file exists.

- **FR-011**: The system MUST verify that a Copilot review is triggered within 60 seconds after a force-push (polling every 10 seconds via `agdt-gh-copilot-review-status`); if not, it MUST explicitly
  call `request_copilot_review()` as a fallback and poll for an additional 60 seconds.

- **FR-012**: The system MUST implement a workflow approval monitor as a standalone workflow (`workflow-approval-monitor.yml`) that detects `action_required` workflow runs for trusted bot PRs and
  approves them via the GitHub API.

- **FR-013**: The workflow approval monitor MUST only approve runs for PR authors listed in the trusted bot allow-list (`.github/ai-pr-loop-config.json`).

- **FR-014**: The system MUST retry failed API calls (approval, review request, thread resolution) up to 3 times with exponential backoff before treating the operation as failed.

### Non-Functional Requirements

- **NFR-001**: SDK evaluation for thread resolution MUST complete within 30 seconds per comment; timeouts result in the thread being left unresolved (fail-safe).

- **NFR-002**: Post-conflict test validation MUST complete within 5 minutes (full test suite); timeouts result in graceful degradation (proceed with force-push, log warning).

- **NFR-003**: The Copilot review re-trigger verification window MUST be 60 seconds for the initial check (polling every 10 seconds) and 120 seconds total including the fallback request.

- **NFR-004**: The workflow approval monitor MUST run on a schedule (every 5 minutes via cron trigger) as a standalone workflow and complete within 30 seconds per execution.

- **NFR-005**: All new functionality MUST be implemented in the existing Python package (`agentic_devtools/cli/ci/`) following established patterns (provider pattern, orchestrator pattern).

- **NFR-006**: All retry mechanisms MUST use exponential backoff (base 2 seconds, max 16 seconds) to avoid API rate limiting.

- **NFR-007**: All new functions MUST have unit test coverage ≥100% in the `tests/unit/` directory following the 1:1:1 test structure policy.

- **NFR-008**: Thread evaluation, conflict resolution enrichment, and commit message enrichment MUST NOT increase the overall loop execution time by more than 120 seconds in the worst case (all
  features active, all retries exhausted).

### Key Entities

- **Thread Evaluator**: A function that invokes the Copilot SDK with a review comment, the file diff, and any agent response, returning a structured verdict ("addressed" / "not_addressed" /
  "ambiguous"). On "ambiguous", the thread is left unresolved immediately without retry.

- **Merge Strategy Configuration**: The merge method parameter passed to `merge_pr()`, changed from `"squash"` to `"rebase"` in the Step 9 merge gate of `orchestrator.py`. Guarded by a pre-merge
  commit count verification.

- **Three-Way Conflict Context**: The three git object stages (`:1:` common ancestor, `:2:` ours, `:3:` theirs) extracted for each conflicted file during interactive rebase, passed to the SDK
  alongside the conflicted content.

- **Post-Resolution Validator**: A function that runs the project's full test suite (via the CI test command) after conflict resolution, returning pass/fail status with output logs. Subject to a
  5-minute timeout with graceful degradation.

- **Review Trigger Verifier**: A polling loop within `squash_post_repair` that checks for a pending Copilot review after force-push (polling every 10 seconds), with a fallback to explicit
  `request_copilot_review()` on 60-second timeout.

- **Workflow Approval Monitor**: A standalone GitHub Actions workflow (`workflow-approval-monitor.yml`) triggered on cron schedule (every 5 minutes) that scans for `action_required` runs and
  auto-approves those associated with trusted bot PRs. Python implementation in `agentic_devtools/cli/ci/`.

- **Trusted Bot Allow-List**: A JSON configuration file (`.github/ai-pr-loop-config.json`) listing GitHub accounts whose PRs are eligible for automatic workflow approval.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of resolved review threads have been confirmed as "addressed" by the Copilot SDK evaluation before resolution; 0 threads are auto-resolved without evaluation.

- **SC-002**: All PR merges from the ai-pr-loop use rebase strategy, and the merged commit message matches the SDK-generated message exactly (verified by post-merge commit message comparison in CI
  logs).

- **SC-003**: Conflict resolution success rate improves by ≥20% (measured as percentage of conflicts resolved without manual intervention) compared to the pre-enrichment baseline over the first 30
  conflict occurrences.

- **SC-004**: 0 force-pushes occur with failing tests after conflict resolution; all post-resolution test failures result in rebase abort and warning comment.

- **SC-005**: Copilot review is triggered within 120 seconds of force-push in ≥99% of cases (either via automatic trigger or explicit fallback request).

- **SC-006**: Workflow runs stuck in `action_required` state for trusted bot PRs are auto-approved within 10 minutes (2 cron cycles) in ≥95% of cases.

---

## Clarifications Needed

All clarifications from the original draft have been resolved in the [Clarifications](#clarifications) section above:

1. ~~**Test suite scope for post-conflict validation**~~ → Resolved: Full test suite with 5-minute timeout and graceful degradation.

2. ~~**Workflow approval monitor deployment**~~ → Resolved: Standalone workflow (`workflow-approval-monitor.yml`) with cron trigger.

3. ~~**SDK evaluation retry budget**~~ → Resolved: No retry on "ambiguous" — leave thread unresolved immediately.

---

*Generated by Copilot SDK (claude-opus-4.6)*
