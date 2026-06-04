# Feature Specification: AI PR Loop — No-Commit-Needed Detection, Thread Resolution, Agent Git Instructions, and Copilot Reviewer Custom Instructions

**Feature Branch**: `1916-ai-pr-loop-no-commit-needed`  
**Created**: 2026-06-04  
**Status**: Draft  
**Source Issue**: #1916 (<https://github.com/ayaiayorg/agentic-devtools/issues/1916>)

## Clarifications

### Session 2026-06-04

- Q: What constitutes an "authorized identity" for marker detection — is it only `copilot[bot]` or does it include all identities in the existing `COPILOT_COMMENT_LOGINS` frozenset? → A: The
  authorized identity set is the existing `COPILOT_COMMENT_LOGINS` frozenset (`{"copilot[bot]", "Copilot", "copilot-pull-request-reviewer[bot]"}`), which already centralizes all recognized Copilot
  agent identities in the codebase. No new configuration mechanism is needed.

- Q: How does the orchestrator detect the `repair-satisfied` marker — via polling PR comments or event-driven webhook? → A: The orchestrator uses its existing polling mechanism (the `run_ai_pr_loop`
  cycle). After dispatching a repair and waiting for the agent session to complete, it checks for new commits OR the `repair-satisfied` marker in comments posted since the dispatch timestamp. No new
  webhook infrastructure is required.

- Q: In the mixed scenario (some threads need code changes, some don't), does the agent post `repair-satisfied` or not? → A: The agent does NOT post `repair-satisfied` in mixed scenarios. It only
  posts the marker when ALL evaluated threads require no code changes. In mixed cases, the agent makes code changes and pushes a commit (normal flow); the `thread-evaluated` markers on no-change
  threads are picked up during the standard `finalize_post_repair()` invocation that follows the commit.

- Q: What is the `review-id` format in the `<!-- review-id:{id} -->` marker — the GitHub numeric review ID (integer) or GraphQL node ID? → A: It is the GitHub numeric review ID (integer), consistent
  with the existing `review_id: int` parameter used throughout `finalize_post_repair()`, `list_review_comments()`, and the orchestrator's dispatch tracking.

- Q: Does the `finalize_post_repair()` commit guard (which skips if no new commit since review) need to be bypassed for the no-change-needed path, or is thread resolution invoked through a separate
  code path? → A: Thread resolution for the no-change-needed path is invoked through a SEPARATE code path that does NOT go through `finalize_post_repair()`. The orchestrator directly invokes thread
  resolution (via `ResolveThreadsAction` or equivalent) targeting only threads with `thread-evaluated` markers, bypassing the commit guard entirely.

## Problem Statement

The ai-pr-loop orchestrator dispatches repair actions to the Copilot cloud agent when a Copilot code review identifies issues. In certain situations, the agent evaluates the review feedback and
correctly determines that no code changes are required — either because the issues were already addressed in a prior commit, or because the review comments are invalid (e.g., flagging CI checks that
are already passing). When this happens, the agent posts a comment explaining its reasoning but does not push a new commit. The ai-pr-loop currently has no mechanism to detect this "no changes needed"
outcome as a valid terminal state, resulting in the loop appearing stuck or endlessly retrying.

This problem was concretely observed on PR #1827, where the Copilot reviewer flagged potential MD013 markdownlint violations. The agent correctly identified that these concerns were already addressed
in commit `cb984c6` and that markdownlint was passing on the current HEAD. The agent reported this finding but pushed no commit. The orchestrator, which relies on detecting new commits as the primary
signal that a repair is complete, had no way to recognize this valid outcome. Furthermore, the review comment threads were left unresolved, leaving the PR in an ambiguous state where human reviewers
could not easily determine whether the feedback had been properly addressed.

A contributing root cause is that the Copilot code reviewer comments about potential CI failures (linting, formatting, markdownlint) even though the ai-pr-loop always confirms that all PR checks are
green before requesting a review. This creates unnecessary repair dispatch cycles — the orchestrator dispatches a repair for a comment about a "potential failure" that is provably not a failure.
Additionally, the current agent prompt instructs the use of `agdt-git-save-work` for committing and pushing, but this command attempts operations (force-push, rebase) that are incompatible with the
Copilot cloud agent's restricted environment, causing commit failures even when legitimate changes are made.

## User Scenarios & Testing

### User Story 1 - Agent Determines No Code Changes Needed (Priority: P1)

A Copilot cloud agent is dispatched to address review feedback on a PR. After evaluating each comment, the agent determines that no code modifications are necessary because the concerns have already
been resolved in prior commits. The agent signals this determination back to the orchestrator using structured HTML comment markers, and the orchestrator correctly recognizes this as a valid
completion state, resolves all evaluated threads, and exits cleanly without retrying.

**Why this priority**: This is the core behavioral gap identified in the issue. Without this capability, the ai-pr-loop enters an ambiguous state whenever the agent correctly determines no changes are
needed, which is a common real-world scenario (observed on PR #1827). This directly blocks reliable autonomous PR management.

**Independent Test**: Can be fully tested by simulating a repair dispatch where the agent posts per-thread `<!-- ai-pr-loop:thread-evaluated -->` replies and a summary `<!-- 
ai-pr-loop:repair-satisfied -->` comment, then verifying the orchestrator detects the marker, resolves threads, logs the outcome with reason `"agent_no_changes_needed"`, and does not retry.

**Acceptance Scenarios**:

1. **Given** the ai-pr-loop has dispatched a repair for a Copilot review containing 3 comment threads, **When** the agent replies to each thread with a `<!-- ai-pr-loop:thread-evaluated -->` marker
   and explanation, and posts a summary comment with `<!-- ai-pr-loop:repair-satisfied -->` and `<!-- review-id:{id} -->`, **Then** the orchestrator detects the `repair-satisfied` marker as a valid
   completion event, invokes thread resolution (via a direct resolution path, NOT through `finalize_post_repair()`) for all threads bearing the `thread-evaluated` reply, logs the outcome with reason
   `"agent_no_changes_needed"`, and does not schedule any retry.

2. **Given** a PR has 5 review comment threads and the agent determines 3 need no changes and 2 require code modifications, **When** the agent replies to the 3 no-change threads with the
   `thread-evaluated` marker and makes code changes for the other 2 (without posting `repair-satisfied`), **Then** the orchestrator processes the code changes normally (commit-based completion) and
   also resolves the 3 threads that
   received `thread-evaluated` replies during the standard `finalize_post_repair()` invocation that follows the commit.

3. **Given** the agent posts a `repair-satisfied` marker but one thread is missing a `thread-evaluated` reply, **When** the orchestrator processes thread resolution, **Then** only threads with the
   `thread-evaluated` reply from an identity in `COPILOT_COMMENT_LOGINS` are resolved, and the missing thread remains unresolved with a warning logged.

---

### User Story 2 - Agent Uses Compatible Git Commands in Cloud Environment (Priority: P2)

A Copilot cloud agent needs to commit and push code changes after addressing review feedback. The agent uses raw git commands (`git commit --amend` + `git push`) instead of `agdt-git-save-work`,
because the cloud agent environment does not support force-push or rebase operations. If a regular push is rejected due to non-fast-forward, the agent falls back to creating a new commit and pushing
normally.

**Why this priority**: The current instructions cause commit/push failures in the cloud agent environment, which is a direct blocker for successful repairs even when the agent correctly identifies and
implements fixes. This is a prompt/documentation change with no runtime code changes required.

**Independent Test**: Can be tested by verifying the agent prompt no longer references `agdt-git-save-work` in the Tooling Priority table or Commit & Push section, includes the explicit policy
exception for raw git commands, and provides fallback instructions for non-fast-forward push rejection.

**Acceptance Scenarios**:

1. **Given** the evaluate-and-respond prompt file exists, **When** the prompt content is examined, **Then** the Tooling Priority table does not list `agdt-git-save-work` for commit/push operations,
   the Commit & Push section instructs `git commit --amend --no-edit` followed by `git push`, and an explicit policy exception note is present authorizing raw git commands for this agent.

2. **Given** the agent has made code changes and attempts `git push` after amending, **When** the push is rejected with a non-fast-forward error, **Then** the prompt instructs the agent to create a
   new commit with a conventional commit message including `[ai-repair]` tag and push normally.

3. **Given** the CI Repair Note in the prompt previously stated "Do not fall back to raw `git commit`/`git push`", **When** the updated prompt is examined, **Then** this prohibition is removed and
   replaced with the cloud agent exception authorization.

---

### User Story 3 - Copilot Reviewer Avoids Unnecessary CI-Related Comments (Priority: P2)

The Copilot code reviewer receives custom instructions that prevent it from commenting about potential CI/linting/formatting failures, because the ai-pr-loop always confirms all checks are green
before requesting review. This eliminates unnecessary repair dispatch cycles caused by the reviewer flagging issues that are provably not failures.

**Why this priority**: This addresses the root cause of the PR #1827 scenario — the reviewer should never have commented about MD013 in the first place. Eliminating these false-positive comments
prevents the entire "no changes needed" scenario from occurring unnecessarily, reducing noise and wasted compute cycles.

**Independent Test**: Can be tested by verifying the existence of `.github/copilot-review-instructions.md` with the correct content, and observing that subsequent Copilot reviews on PRs with passing
checks do not include comments about linting, formatting, or CI failures.

**Acceptance Scenarios**:

1. **Given** the file `.github/copilot-review-instructions.md` does not exist in the repository, **When** this feature is implemented, **Then** the file is created with instructions explicitly
   prohibiting comments about CI check failures, linting issues (ruff, markdownlint, MD013), formatting issues, test failures, and type errors.

2. **Given** the copilot-review-instructions file is in place, **When** Copilot reviews a PR where all CI checks are passing green, **Then** Copilot does not comment about potential linting
   violations, line length issues, or formatting concerns that are enforced by CI.

3. **Given** the custom instructions are active, **When** Copilot reviews a PR, **Then** it focuses exclusively on logic correctness, security vulnerabilities, architecture/design issues, code
   clarity, missing edge cases, API contract violations, and race conditions.

---

### User Story 4 - Thread Resolution Engine Recognizes Agent Evaluation Markers (Priority: P1)

The thread resolution logic recognizes `<!-- ai-pr-loop:thread-evaluated -->` replies from identities in `COPILOT_COMMENT_LOGINS` as a HIGH confidence resolution signal,
enabling threads to be resolved without requiring SDK-based diff verification. This extends the existing tiered verification model with a new signal type within the `AutomationMarkerTier` (or as a new
peer tier).

**Why this priority**: Thread resolution is the mechanism that actually cleans up the PR after a "no changes needed" determination. Without this, even if the orchestrator detects the
`repair-satisfied` marker, the threads would remain unresolved and the PR would stay in an ambiguous state.

**Independent Test**: Can be tested by mocking a PR thread that contains a reply with the `<!-- ai-pr-loop:thread-evaluated -->` marker from a `copilot[bot]` user, invoking thread resolution,
and verifying the thread is resolved with HIGH confidence without requiring any diff-based verification.

**Acceptance Scenarios**:

1. **Given** a PR thread has a reply from `copilot[bot]` containing `<!-- ai-pr-loop:thread-evaluated -->`, **When** thread resolution processes this thread, **Then** it classifies the thread
   as HIGH confidence resolution and resolves it immediately without SDK verification.

2. **Given** a PR thread has a reply from a non-bot user (not in `COPILOT_COMMENT_LOGINS`) containing the `<!-- ai-pr-loop:thread-evaluated -->` marker, **When** thread resolution processes this
   thread, **Then** it does NOT
   treat it as a high-confidence signal (author must be in the `COPILOT_COMMENT_LOGINS` set).

3. **Given** multiple threads exist where some have the `thread-evaluated` marker and others do not, **When** thread resolution runs, **Then** only the marked threads receive high-confidence immediate
   resolution; unmarked threads fall through to the existing tiered verification logic (OutdatedTier, SdkEvaluationTier).

---

### Edge Cases

- What happens when the agent posts `repair-satisfied` but the network drops before all per-thread replies are posted? The orchestrator should only resolve threads that actually have the
  `thread-evaluated` reply; missing replies result in those threads remaining unresolved with a warning logged for manual review.

- What happens when the same review is dispatched twice (race condition) and both agents post `repair-satisfied`? The deduplication guard (`check_deduplication()`) should prevent duplicate dispatches,
  but if both complete, the second resolution attempt should be idempotent — resolving already-resolved threads is a no-op.

- What happens if `git push` fails after `git commit --amend` in the cloud agent? The prompt instructs fallback to a new commit with `git push`. If that also fails, the agent should report the failure
  and the orchestrator handles it as a failed repair.

- What happens when the `repair-satisfied` marker is present but the `review-id` does not match the current review being processed? The orchestrator should validate that the `review-id` in the marker
  matches the review that triggered the dispatch; mismatched IDs are ignored.

- What if the Copilot reviewer still comments about CI issues despite custom instructions? The `repair-satisfied` path provides graceful handling — the agent evaluates and confirms no changes needed,
  threads are resolved, and no compute is wasted on actual code changes.

- What if the agent posts the `repair-satisfied` marker but the orchestrator's polling interval means it doesn't check for several seconds? The NFR-001 5-second detection target assumes the
  orchestrator polls after the agent session completes (session completion is the trigger, not continuous polling during agent execution). The marker is detected on the first poll after session end.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST detect `<!-- ai-pr-loop:repair-satisfied -->` HTML comment markers in PR comments from the dispatched agent (identified by membership in the `COPILOT_COMMENT_LOGINS`
  frozenset: `copilot[bot]`, `Copilot`, `copilot-pull-request-reviewer[bot]`) as a valid repair completion signal, equivalent in authority to a new commit being pushed. When this marker is detected,
  the orchestrator MUST treat the repair as complete, invoke thread resolution via a direct resolution path (not through `finalize_post_repair()`), and terminate without retry.

- **FR-002**: The system MUST recognize `<!-- ai-pr-loop:thread-evaluated -->` HTML comment markers in individual thread replies from the dispatched agent as a HIGH confidence thread resolution signal
  within the tiered resolution engine. Threads bearing this marker from an identity in `COPILOT_COMMENT_LOGINS` MUST be resolved immediately without requiring diff-based SDK
  verification.

- **FR-003**: The agent prompt (`.github/prompts/agdt.address-copilot-review.evaluate-and-respond.prompt.md`) MUST instruct the agent to reply to EVERY individual review comment thread with a `<!-- 
  ai-pr-loop:thread-evaluated -->` marker and a human-readable explanation when no code changes are needed for that specific comment. This ensures both machine parseability and human reviewer
  confidence.

- **FR-004**: The agent prompt MUST instruct the agent to post a summary comment containing `<!-- ai-pr-loop:repair-satisfied -->` and `<!-- review-id:{review_id} -->` markers (where `review_id` is
  the numeric GitHub review ID integer) when it determines that
  NO code changes are required for any of the review comments. This summary comment serves as the global signal that the repair dispatch is complete without a commit. The agent MUST NOT post this
  marker in mixed scenarios where some threads require code changes.

- **FR-005**: The orchestrator MUST log the repair completion outcome with reason `"agent_no_changes_needed"` when the `repair-satisfied` marker is detected, distinguishing this path from commit-based
  completion in telemetry and audit logs.

- **FR-006**: The evaluate-and-respond agent prompt MUST replace `agdt-git-save-work` instructions with raw git commands (`git commit --amend --no-edit` + `git push`) including an explicit policy
  exception note stating that this is authorized specifically for the Copilot cloud agent environment due to force-push/rebase incompatibility.

- **FR-007**: The agent prompt MUST include fallback instructions for non-fast-forward push rejection: create a new commit with conventional commit message format including `[ai-repair]` tag, then
  push normally.

- **FR-008**: The agent prompt MUST remove the CI Repair Note that states "Do not fall back to raw `git commit`/`git push`; both violate project policy" and replace it with the cloud agent exception
  authorization.

- **FR-009**: A `.github/copilot-review-instructions.md` file MUST be created containing instructions that prohibit the Copilot code reviewer from commenting about CI check failures, linting issues,
  formatting issues, test failures, type errors, and markdown lint violations when those checks are enforced by automated CI.

- **FR-010**: The thread resolution engine MUST validate that the `<!-- ai-pr-loop:thread-evaluated -->` marker originates from an authorized identity (specifically any login in the
  `COPILOT_COMMENT_LOGINS` frozenset) before treating it as a high-confidence signal. Markers from arbitrary users MUST NOT trigger automatic thread resolution.

- **FR-011**: The orchestrator MUST validate that the `<!-- review-id:{id} -->` in the `repair-satisfied` marker matches the numeric review ID (integer) that triggered the current repair dispatch.
  Markers with
  mismatched review IDs MUST be ignored to prevent cross-review interference.

- **FR-012**: When the `repair-satisfied` marker is detected, the system MUST invoke thread resolution specifically targeting threads that
  contain `<!-- ai-pr-loop:thread-evaluated -->` replies from authorized identities, rather than attempting to resolve all threads indiscriminately. This resolution is invoked through a direct code
  path that bypasses the `finalize_post_repair()` commit guard.

### Non-Functional Requirements

- **NFR-001**: The marker detection logic MUST execute within 5 seconds of the orchestrator's first poll after the agent session completes (assuming GitHub API response times under 2 seconds), to
  avoid perception of the loop being
  stuck between the agent posting and the orchestrator advancing. The detection occurs on the orchestrator's post-session polling cycle, not via continuous polling during agent execution.

- **NFR-002**: The thread resolution for `thread-evaluated` marked threads MUST be idempotent — resolving an already-resolved thread MUST NOT produce errors, throw exceptions, or alter the resolution
  state. This ensures safe handling of duplicate dispatches or retries.

- **NFR-003**: All new orchestrator behavior (marker detection, thread resolution invocation, outcome logging) MUST produce structured log entries at INFO level that include the PR number, review ID,
  number of threads evaluated, and the resolution outcome, enabling debugging and audit trail reconstruction.

- **NFR-004**: The `.github/copilot-review-instructions.md` file MUST be under 1KB in size and use clear, unambiguous language that the Copilot model can reliably interpret. Instructions MUST be
  phrased as prohibitions ("MUST NOT") and positive focus directives ("Focus exclusively on") for maximum clarity.

### Key Entities

- **Repair Satisfaction Marker**: An HTML comment (`<!-- ai-pr-loop:repair-satisfied -->`) posted as a PR comment by the agent to signal that no code changes are needed. Always accompanied by a `<!-- 
  review-id:{id} -->` marker (where `{id}` is the numeric GitHub review ID integer) for correlation.

- **Thread Evaluation Marker**: An HTML comment (`<!-- ai-pr-loop:thread-evaluated -->`) posted as a reply within an individual review thread by the agent, indicating that the specific comment has
  been evaluated and no code change is warranted for it.

- **Repair Outcome Reason**: A string enum value (`"agent_no_changes_needed"`) recorded in the orchestrator's completion log to distinguish no-change-needed completions from commit-based completions
  and failure states.

- **Authorized Agent Identities**: The `COPILOT_COMMENT_LOGINS` frozenset defined in `agentic_devtools/cli/ci/models.py`, currently containing `{"copilot[bot]", "Copilot",
  "copilot-pull-request-reviewer[bot]"}`. This is the single source of truth for validating marker authorship.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of repair dispatches where the agent determines no changes are needed MUST result in a clean loop exit within 60 seconds of the `repair-satisfied` marker being posted, with zero
  retries attempted. This is verified by examining orchestrator logs for the `"agent_no_changes_needed"` reason code and confirming no subsequent dispatch events for the same review ID.

- **SC-002**: At least 95% of threads that receive a `<!-- ai-pr-loop:thread-evaluated -->` reply from an authorized agent MUST be successfully resolved within a single thread resolution invocation.
  The remaining 5% allowance accounts for transient GitHub API failures that trigger retry logic.

- **SC-003**: The Copilot code reviewer MUST produce zero comments about CI check failures (linting, formatting, markdownlint, test failures, type errors) on PRs where all checks are confirmed passing
  at review request time. This is measured over a rolling 30-day window after deployment, targeting 0 false-positive CI comments across all reviewed PRs.

- **SC-004**: The agent prompt changes MUST result in zero `agdt-git-save-work` execution failures in the Copilot cloud agent environment, because the command is no longer invoked. Measured by
  confirming zero occurrences of `agdt-git-save-work` in cloud agent execution logs after deployment.

- **SC-005**: All new code paths (marker detection, thread resolution integration, outcome logging) MUST have 100% branch coverage in unit tests, verified by the existing `agdt-test-file` per-file
  coverage enforcement.

- **SC-006**: The end-to-end "no changes needed" scenario (from agent posting markers to all threads being resolved) MUST complete in under 120 seconds total elapsed time, measured from the agent's
  first `thread-evaluated` reply to the last thread being resolved.

- **SC-007**: The system MUST handle at least 20 concurrent review threads in a single "no changes needed" resolution pass without timeout or rate-limit failures, accommodating large PRs with many
  review comments.

---
*Generated by Copilot SDK (claude-opus-4.6)*
