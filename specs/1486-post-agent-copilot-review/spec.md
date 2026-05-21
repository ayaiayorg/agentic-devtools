# Feature Specification: Post-Agent Copilot Review Evaluator

**Feature Branch**: `speckit/1486/phase-2-clarify`
**Created**: 2026-05-19
**Status**: Draft
**Input**: User description: "GitHub Issue #1486 - Post-Agent Copilot Review Evaluator: Programmatic & Agentic Automation for Stuck PRs"
**Source Issue**: #1486 (<https://github.com/ayaiayorg/agentic-devtools/issues/1486>)

## Clarifications

### Session 2026-05-20

- Q: Should thread verification (FR-008) use semantic code analysis (AST-level comparison) or heuristic matching (keyword/line-range diff comparison)? → A: Use heuristic matching based on diff
  line-range overlap. The evaluator checks whether the lines referenced by a review comment have been modified in the current HEAD diff relative to the review commit. This is a new verification
  step for this evaluator; the existing `GitHubActionsProvider.finalize_post_repair()` flow replies to review comments and resolves threads without diff-based verification. Semantic analysis
  can be added as a future enhancement behind a feature flag.
- Q: Should the workflow YAML reuse the existing `issue_comment` trigger in `ai-pr-loop.yml`
  or add a separate workflow file? → A: Reuse the existing `ai-pr-loop.yml` workflow with
  the `issue_comment` trigger. The orchestrator (`run_ai_pr_loop`) already dispatches based
  on event type; add a new guard/handler branch in the orchestrator for the post-agent
  evaluation scenario. This maintains zero decision logic in YAML (NFR-004) and avoids
  workflow file proliferation.
- Q: What constitutes the "sentinel marker" — is it a specific string constant already
  defined in the codebase? → A: The evaluator should introduce and consistently reuse a
  single sentinel marker value for both detection and synthesis. The current documented
  result-comment sentinel is `<!-- copilot-agent-result -->`; the evaluator passes that
  marker value (or a future shared equivalent) into
  `CIPlatformProvider.find_comment(pr_number, marker)` when checking for result comments
  and includes the same marker when synthesizing a missing result comment.
- Q: How should the system handle concurrent evaluator invocations on the same PR (race
  condition)? → A: Use optimistic concurrency with a dedicated lock marker comment
  (`<!-- copilot-evaluator-lock -->`). The evaluator calls
  `CIPlatformProvider.find_comment(pr_number, LOCK_MARKER)` to locate the lock comment and
  MUST maintain a single-comment invariant: if no lock comment exists, create one; if one
  already exists (regardless of its state), update that same comment in-place via
  `CIPlatformProvider.update_comment(comment_id, new_body)`. This guarantees at most one
  comment per PR ever contains the lock marker, so detection stays deterministic without
  relying on provider-specific ordering behavior. If the found comment's parsed lock age is
  less than or equal to 5 minutes, the second invocation exits with
  `concurrent_evaluation_skipped` and takes no action. Releasing the lock updates the
  comment body to a released/expired state (provider-compatible; no delete needed).
- Q: For the `PostAgentSnapshot` dataclass, should thread data include full comment bodies
  or just metadata (IDs, resolution status, line references)? → A: Include metadata plus a
  truncated body excerpt (first 500 characters) for each review comment. Full bodies are not
  needed for heuristic matching (which uses line-range overlap), but excerpts enable logging,
  debugging, and future semantic enhancement. This keeps the snapshot lightweight while
  preserving diagnostic value.

## Problem Statement

When a Copilot review runs on a PR and the agent responds via a Copilot comment (e.g., says
fixes already done), but **no machine-parseable final result** (no sentinel) and **no
reply/resolve on review threads**, the review loop is left hanging for human intervention —
even if the code is fine. The system needs a Post-Agent Copilot Review Evaluator that can
programmatically analyze PR state after the Copilot comment, classify the scenario, and take
the appropriate action to unblock the PR.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PR State Classification (Priority: P1)

As a repository maintainer, I want the system to programmatically classify the PR state after
a Copilot agent comment, so that the correct remediation action can be determined without
human intervention.

**Why this priority**: Classification is the foundation — all other actions depend on correctly
identifying the current PR state. Without this, no automated remediation is possible.

**Independent Test**: Can be tested by providing various PR state snapshots (with/without
sentinels, with/without unresolved threads, with/without code changes, with/without an
active lock) and verifying the correct classification is returned.

**Applies to**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-014

**Acceptance Scenarios**:

1. **Given** a PR where the Copilot agent posted a comment saying "already fixed" but no
   sentinel is present, **When** the evaluator runs, **Then** the state is classified as
   `agent_claims_fixed_no_sentinel`.
2. **Given** a PR where the Copilot agent posted a comment and all review threads are already
   resolved, **When** the evaluator runs, **Then** the state is classified as
   `threads_resolved_no_sentinel`.
3. **Given** a PR where the sentinel is present and all threads are resolved, **When** the
   evaluator runs, **Then** the state is classified as `complete` and no further action is
   needed.
4. **Given** a PR where the agent comment indicates changes were made but threads remain
   unresolved, **When** the evaluator runs, **Then** the state is classified as
   `changes_made_threads_unresolved`.
5. **Given** a PR where the agent session ended without any comment, **When** the evaluator
   runs, **Then** the state is classified as `agent_silent`.
6. **Given** a PR where a concurrent evaluation is already in progress (lock marker body
   encodes an acquisition time within 5 minutes), **When** the evaluator runs, **Then** the
   state is classified as `concurrent_evaluation_skipped` and no action is taken.

---

### User Story 2 - Verify-and-Resolve Threads (Priority: P1)

As a repository maintainer, I want the system to verify that Copilot review feedback has been
addressed in the code and then resolve the corresponding threads, so that the PR can proceed
without manual thread resolution.

**Why this priority**: Thread resolution is the most common missing step that blocks PRs. If
classification says "code is fixed", the system must be able to verify and resolve threads
to complete the loop.

**Independent Test**: Can be tested by setting up a PR with unresolved Copilot review threads
where the code diff shows the issues were addressed, and verifying threads are resolved.

**Applies to**: FR-006, FR-008, FR-009

**Acceptance Scenarios**:

1. **Given** a classified state of `agent_claims_fixed_no_sentinel` with unresolved threads,
   **When** the verify-and-resolve action runs, **Then** each thread's referenced line range
   is checked against the HEAD diff as a heuristic proxy — threads whose referenced lines
   were modified in the diff (a proxy signal for "addressed", not a semantic guarantee) are
   resolved.
2. **Given** a thread whose feedback is NOT addressed in the code (referenced lines
   unchanged in the diff), **When** the verify-and-resolve action runs, **Then** that thread
   remains unresolved and a comment is posted noting the unresolved item.
3. **Given** all threads have been verified and resolved, **When** the action completes,
   **Then** a re-review request is posted to trigger the next Copilot review cycle.

---

### User Story 3 - Synthesize Result Summary (Priority: P1)

As a repository maintainer, I want the system to synthesize a machine-parseable result summary
(with the sentinel marker) when the agent failed to produce one, so that the AI PR loop can
proceed to its next phase.

**Why this priority**: The sentinel is the machine-parseable signal that downstream automation
depends on. Without it, the loop cannot finalize.

**Independent Test**: Can be tested by verifying that after the evaluator processes a PR with
no sentinel, a properly formatted result comment with the sentinel is posted.

**Applies to**: FR-007

**Acceptance Scenarios**:

1. **Given** a classified state where the agent completed successfully but no sentinel is
   present, **When** the synthesize action runs, **Then** a PR comment is posted containing
   the shared sentinel marker value used for `CIPlatformProvider.find_comment(...)` and a
   summary of what the agent did.
2. **Given** the synthesized result, **When** downstream automation reads the PR comments,
   **Then** it can detect the sentinel and proceed normally.

---

### User Story 4 - CLI Entry Point (Priority: P1)

As a CI/CD workflow, I want a single CLI command (`agdt-evaluate-post-agent-state`) that
invokes the evaluator, so that the workflow YAML remains minimal and all logic resides in
testable Python code.

**Why this priority**: The CLI entry point is the integration point between the workflow
trigger and the Python logic. Keeping it as a single command ensures zero decision logic in
YAML.

**Independent Test**: Can be tested by invoking the CLI command with mocked PR state and
verifying it produces the correct classification and action output.

**Applies to**: FR-010, FR-011, FR-013

**Acceptance Scenarios**:

1. **Given** the workflow triggers on a Copilot comment (via the existing `issue_comment`
   trigger in `ai-pr-loop.yml`), **When** `agdt-evaluate-post-agent-state` is invoked with
   a PR number, **Then** it analyzes the PR state, classifies it, and executes the
   appropriate action.
2. **Given** the CLI is invoked, **When** it completes, **Then** it outputs a structured JSON
   result containing the classification, action taken, and success/failure status.
3. **Given** a `--dry-run` flag, **When** the CLI is invoked, **Then** it classifies the
   state and reports what action would be taken without executing it.

---

### User Story 5 - Retry Trigger (Priority: P2)

As a repository maintainer, I want the system to re-trigger a Copilot review after resolving
threads and posting the sentinel, so that the PR gets a fresh review pass confirming
everything is clean.

**Why this priority**: A re-review ensures the automated resolution actually satisfied the
original feedback. It's important but depends on the core classification and resolution
stories being functional first.

**Independent Test**: Can be tested by verifying that after thread resolution, a re-review
request is posted and the Copilot review is triggered.

**Applies to**: FR-009

**Acceptance Scenarios**:

1. **Given** the verify-and-resolve action completed successfully, **When** the retry trigger
   runs, **Then** a Copilot re-review is requested on the PR via
   `CIPlatformProvider.request_reviewer`.
2. **Given** the re-review has been requested, **When** the system polls for the new review,
   **Then** it detects the new review and the loop can proceed.

---

### User Story 6 - Agentic Fallback (Priority: P3)

As a repository maintainer, I want the system to trigger a full Copilot agent session with
structured context when programmatic resolution is not possible, so that complex edge cases
are still handled without human intervention.

**Why this priority**: This is the safety net for cases that cannot be resolved
programmatically. It's lowest priority because it requires the classification system to first
identify that programmatic resolution failed.

**Independent Test**: Can be tested by providing a PR state that the programmatic classifier
cannot resolve and verifying a Copilot agent session is triggered with the correct context.

**Applies to**: FR-012

**Acceptance Scenarios**:

1. **Given** a classified state where programmatic resolution is not possible (e.g.,
   `agent_silent` or ambiguous feedback), **When** the agentic fallback runs, **Then** a
   Copilot agent session is triggered via `CIPlatformProvider.dispatch_repair` with
   structured context including the PR diff, unresolved threads, and agent history.
2. **Given** the fallback has been triggered, **When** the Copilot agent session completes,
   **Then** the evaluator can be re-invoked to verify the agent's work.

---

### Edge Cases

- What happens when the Copilot agent's comment is ambiguous (neither "fixed" nor "can't
  fix")? → Classified as `agent_silent` (no actionable signal) and routed to the agentic
  fallback (FR-012).
- How does the system handle a PR where the agent made partial fixes (some threads addressed,
  others not)? → The verify-and-resolve action resolves only threads whose referenced lines
  were modified; remaining threads stay open with a posted comment noting they remain unresolved.
  The sentinel is NOT synthesized until all threads are resolved or a re-review cycle clears them.
- What if the sentinel is present but malformed or incomplete? → Detected via `find_comment`
  with the configured sentinel marker value; malformed sentinels that do not contain the exact
  marker string are treated as absent (no sentinel detected).
- What if thread resolution fails due to GitHub API rate limiting? → NFR-006 applies:
  exponential backoff with retry. If retries are exhausted, the `EvaluationResult`
  reports partial success with `error_details` listing the failed thread IDs.
- What if the Copilot review was dismissed or superseded by a new review? → The evaluator uses
  the most recent non-dismissed review. If all reviews are dismissed, it is classified as
  `agent_silent` (no actionable Copilot review signal remains); `complete` requires the sentinel
  to be present and all threads resolved regardless of dismissal state.
- How does the system handle concurrent evaluator invocations on the same PR? → Optimistic
  concurrency via a dedicated lock marker comment (`<!-- copilot-evaluator-lock -->`). The
  evaluator locates the comment via `find_comment(pr_number, LOCK_MARKER)`; to keep detection
  deterministic without provider-ordering assumptions, only one comment per PR ever holds the
  lock marker: create it on first use, update it in-place on subsequent operations. If the
  parsed lock age is ≤ 5 minutes, the second invocation exits with
  `concurrent_evaluation_skipped`; on completion the lock comment is updated to a
  released/expired state (provider-compatible; deletion not required).
- What if the PR branch has been force-pushed between the agent session and the evaluator
  run? → The evaluator detects HEAD SHA mismatch by comparing `PRMetadata.head_sha` against
  the review's commit SHA. If mismatched, it re-fetches the current diff for heuristic
  matching against the new HEAD.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a `classify_post_agent_state()` pure function that takes a
  `PostAgentSnapshot` (input dataclass capturing PR threads, sentinel presence, head changes)
  and returns a `PostAgentClassification` enum.
- **FR-002**: System MUST detect the presence/absence of the sentinel marker in PR comments
  using a single shared marker value passed to `CIPlatformProvider.find_comment`.
- **FR-003**: System MUST check unresolved review threads and their resolution status.
- **FR-004**: System MUST detect whether code changes were made after the review was posted
  by comparing the review's commit SHA against the current HEAD SHA.
- **FR-005**: System MUST detect reply status on review threads (replied vs unreplied).
- **FR-006**: System MUST provide action handlers for each classified state, following the
  provider abstraction pattern (`CIPlatformProvider`).
- **FR-007**: System MUST synthesize a sentinel-containing result comment when the agent
  fails to produce one, using the same shared marker value used for detection.
- **FR-008**: System MUST verify that review feedback is addressed in code before resolving
  threads, using heuristic diff line-range overlap matching (checking whether lines
  referenced by the review comment have been modified in the HEAD diff).
  Implementing this requirement requires extending `ReviewCommentInfo`
  (in `agentic_devtools/cli/ci/models.py`) to add `start_line` (int | None) and
  `end_line` (int | None) fields, populated from the GitHub REST API's `start_line`
  and `line` fields on review comments.
  `ThreadInfo.thread_id` is the review comment's integer REST `id` cast to str; it is
  used as a stable key for diff matching and resolution. GraphQL node IDs are not
  required for this heuristic; thread resolution continues through the existing
  `CIPlatformProvider` abstraction.
- **FR-009**: System MUST request a Copilot re-review after resolving threads via
  `CIPlatformProvider.request_reviewer`.
- **FR-010**: System MUST provide a CLI entry point (`agdt-evaluate-post-agent-state`) that
  orchestrates classification and action execution.
- **FR-011**: System MUST support `--dry-run` mode for safe previewing of actions.
- **FR-012**: System MUST trigger an agentic fallback session via
  `CIPlatformProvider.dispatch_repair` when programmatic resolution is not possible.
- **FR-013**: System MUST output structured JSON results from the CLI command.
- **FR-014**: System MUST coordinate concurrent evaluator invocations using a dedicated lock
  marker (`<!-- copilot-evaluator-lock -->`) embedded in a single PR comment whose body also
  embeds the acquisition timestamp. The single-comment invariant MUST be maintained: on each
  lock operation the evaluator checks via `CIPlatformProvider.find_comment` for an existing
  lock comment; if none exists it creates one, if one exists it updates that same comment
  in-place via `CIPlatformProvider.update_comment` (acquire, extend, or release). Snapshot
  construction MUST expose the parsed lock metadata (`lock_comment_id`, `lock_age_seconds`),
  an active lock less than or equal to 300 seconds old MUST classify as
  `concurrent_evaluation_skipped`, and lock release MUST update the existing comment body to
  a released/expired state unless future provider capabilities add delete support.

### Non-Functional Requirements

- **NFR-001**: Classification function MUST execute in under 5 seconds (excluding API calls).
- **NFR-002**: All scenario handlers MUST be fully unit-testable with mocked
  `CIPlatformProvider` interfaces (decision logic is pure; side effects are injected).
- **NFR-003**: New edge cases MUST be addable as new Python handler functions + test cases,
  not configuration changes.
- **NFR-004**: Zero decision logic in workflow YAML — all branching MUST reside in the Python
  codebase. The evaluator is invoked from the existing `ai-pr-loop.yml` via the
  `issue_comment` trigger with a new orchestrator guard/handler branch.
- **NFR-005**: CLI output MUST follow existing `agdt-*` command patterns (structured JSON,
  state key updates).
- **NFR-006**: System MUST handle GitHub API rate limiting gracefully with exponential
  backoff and retry using the existing `retry_with_backoff` utility defaults in
  `agentic_devtools.cli.ci.retry` (initial delay 1 second, maximum 5 retries, exponential
  backoff with jitter).

### Key Entities

- **PostAgentSnapshot**: Input dataclass (frozen) capturing the PR state at evaluation time.
  Fields:
  - `pr_number` (int)
  - `head_sha` (str)
  - `review_commit_sha` (str)
  - `sentinel_present` (bool)
  - `unresolved_threads` (tuple of `ThreadInfo`, ...)
  - `agent_comments` (tuple of `CommentInfo`, ...)
  - `head_changed_since_review` (bool)
  - `review_id` (int)
  - `review_dismissed` (bool)
  - `lock_comment_id` (int | None)
  - `lock_age_seconds` (int | None)

  `ThreadInfo` fields:
  - `thread_id` (str) — REST review comment `id` cast to str; stable key for diff
    matching and resolution
  - `body_excerpt` (str, max 500 chars)
  - `path` (str)
  - `start_line` (int | None) — populated from the extended `ReviewCommentInfo`
  - `end_line` (int | None) — populated from the extended `ReviewCommentInfo`
  - `is_resolved` (bool)
  - `has_reply` (bool)

  `CommentInfo` fields:
  - `comment_id` (int)
  - `body_excerpt` (str, max 500 chars)
  - `author` (str)
  - `created_at` (str)
- **PostAgentClassification**: Enum classifying the snapshot into a scenario:
  `agent_claims_fixed_no_sentinel`, `threads_resolved_no_sentinel`, `complete`,
  `changes_made_threads_unresolved`, `agent_silent`, `concurrent_evaluation_skipped`.
- **PostAgentAction**: Enum of possible remediation actions: `verify_and_resolve`,
  `synthesize_sentinel`, `trigger_re_review`, `agentic_fallback`, `no_action`.
- **CIPlatformProvider**: Existing provider abstraction used for platform-agnostic API calls
  (thread resolution, comment posting, review requests). Already defined in
  `agentic_devtools/cli/ci/provider.py`.
- **EvaluationResult**: Dataclass containing `classification` (PostAgentClassification),
  `action_taken` (PostAgentAction), `success` (bool), `threads_resolved` (int),
  `threads_unresolved` (int), `error_details` (str | None), `dry_run` (bool).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 90% of "stuck PR" scenarios (agent commented but loop not finalized) are
  automatically resolved without human intervention within 5 minutes of detection.
- **SC-002**: `classify_post_agent_state()` achieves 100% unit test coverage across all
  defined state variants (all `PostAgentClassification` enum values exercised).
- **SC-003**: Zero decision logic exists in the workflow YAML — confirmed by workflow file
  containing only trigger + CLI invocation.
- **SC-004**: New edge case scenarios can be added with only a new handler function and
  corresponding test (no changes to existing code or configuration required).
- **SC-005**: The evaluator CLI command completes execution (classification + action) within
  30 seconds for a typical PR with fewer than 20 review threads.

## Clarification Items

- **CLARIFY-001**: ~~Should thread verification use semantic code analysis (AST-level
  comparison of feedback vs current code) or heuristic matching (keyword/line-range based)?~~
  **Resolved**: Use heuristic matching based on diff line-range overlap. The evaluator checks
  whether the lines referenced by a review comment have been modified in the current HEAD
  diff relative to the review commit. This is new evaluator behavior rather than existing
  `GitHubActionsProvider.finalize_post_repair()` behavior. Semantic analysis can be added
  later behind a feature flag.
- **CLARIFY-002**: ~~Should the workflow YAML reuse the existing `issue_comment` trigger in
  `ai-pr-loop` or add a separate workflow file?~~ **Resolved**: Reuse the existing
  `ai-pr-loop.yml` workflow. The orchestrator already dispatches based on event type; add a
  new guard/handler branch for the post-agent evaluation scenario. This maintains NFR-004.

---
*Generated from issue #1486 — Phase 1 specification*

---
*Generated by Copilot SDK (claude-opus-4.6)*
