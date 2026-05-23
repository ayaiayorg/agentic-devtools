# Feature Specification: Idempotent Action Evaluator for AI PR Loop

**Feature Branch**: `speckit/1559/phase-1-specify`  
**Created**: 2026-05-23  
**Status**: Draft  
**Input**: GitHub Issue #1559  
**Source Issue**: #1559 (<https://github.com/ayaiayorg/agentic-devtools/issues/1559>)

## Clarifications

### Session 2026-05-23

- Q: What constitutes the "8 actions" referenced in FR-001? The spec lists guards, publish, request-review, resolve-threads, dispatch-repair, squash, approve, merge — but guards are described as a
  gate (FR-014), not a standard action. Should guards be action 0 (gate) with actions 1–7 being the sequential pipeline, or are guards literally action 1 of 8? → A: Guards are action 1 of 8 in the
  sequential evaluation. They are special only in that a "blocked" result from guards prevents actions 2–8 from executing (FR-014). All 8 are still reported in the summary table uniformly as
  ActionResult entries, with guards showing "blocked" causing downstream actions to show "blocked by guard."
- Q: How does the pipeline handle the "publish" action (action 2) modifying PR state mid-run? FR-011 states later actions MAY use in-memory derived state, but should the snapshot object be mutated or
  should a separate derived-state object track in-run changes? → A: A separate `DerivedState` object (or dictionary) is maintained alongside the frozen `PRStateSnapshot`. When publish executes
  successfully, it updates `DerivedState.is_draft = False`. Subsequent actions read from `DerivedState` (which falls through to `PRStateSnapshot` for unmodified fields). The original snapshot remains
  immutable for logging/summary purposes.
- Q: FR-003 references "issue event IDs" for session detection. The GitHub Issues Events API returns events with monotonically increasing integer `id` fields. Should the implementation fetch ALL issue
  events and filter by label, or use a more targeted approach (e.g., timeline API)? → A: Use the Issues Events API (`GET /repos/{owner}/{repo}/issues/{issue_number}/events`), paginate all available
  pages client-side, and select the session-related event (`copilot_work_started`, `copilot_work_finished`, or `copilot_work_finished_failure`) with the **highest `id`** as the decision source. Event
  `id` is the authoritative ordering key because the API does not guarantee delivery order within or across pages. If no session-related event is found after scanning all pages, treat the session as
  inactive.
- Q: Should the summary comment (FR-008) be a new comment on every run, or should it edit/update a single pinned comment? New comments create noise on active PRs (potentially dozens of comments). → A:
  Post a new comment on every run. Each comment is a point-in-time record of what the pipeline evaluated and decided. To mitigate noise, collapse all prior AI-loop summary comments identified by the
  exact first-line sentinel `<!-- agdt:ai-pr-loop-summary -->` into a `<details>` block via edit when posting the new one, and replace line 1 with `<!-- agdt:ai-pr-loop-summary-collapsed -->` so
  already-collapsed comments are not re-edited on subsequent runs. This preserves history while keeping only the latest visible.
- Q: NFR-003 states that a failure in action N must not prevent evaluation of actions N+1 through 8. Does "failure" include Python exceptions (unhandled crashes) or only graceful API error responses?
  → A: Both. Each action execution is wrapped in a try/except at the pipeline level. Unhandled exceptions from an action are caught, logged with full traceback, and the action is marked as "failed
  (exception)" in the ActionResult. The pipeline continues to the next action. Exception: if guards (action 1) raises an exception, the pipeline fails closed by treating guards as "blocked
  (exception)", logs the guard exception details, and marks downstream actions as "blocked by guard."

## Problem Statement

The current AI PR loop orchestrator (`agentic_devtools/cli/ci/orchestrator.py`) uses event-type branching — it takes different code paths depending on whether the trigger was `issue_comment`,
`workflow_run(completed)`, or `pull_request_review(submitted)`. This architecture causes three systemic problems:

1. **Missed actions**: Thread resolution only runs during specific CI-completion scenarios. `COMMENTED` reviews (the most common Copilot review state) never trigger `finalize_post_repair()`, leaving
   threads permanently open.
2. **Unnecessary complexity**: The squash-wait marker/scheduler/cron system (229+ lines) exists solely because squash cannot be evaluated independently of the event that triggered the run.
3. **Fragile ordering**: `issue_comment` events exit before reaching thread resolution or merge logic, meaning legitimate state transitions are silently dropped.

The fix is to replace event-type branching with a sequential, idempotent action pipeline that evaluates **all** actions on **every** trigger based solely on current PR state.

## User Scenarios & Testing

### User Story 1 — Idempotent Pipeline Execution (Priority: P1)

As a developer with an open PR labeled `ai-auto-merge-allowed`, I want every AI PR loop trigger to evaluate all possible actions against the current PR state so that no action is ever missed
regardless of which GitHub event fired.

**Why this priority**: This is the core architectural change. Without it, no other story delivers value — the branching architecture prevents reliable end-to-end automation.

**Covers**: FR-001, FR-002, FR-011, FR-014

**Independent Test**: Trigger the loop via three different event types (`issue_comment`, `workflow_run`, `pull_request_review`) on the same PR state. All three runs must produce identical action
evaluations and execute the same set of actions (or skip them identically if already completed).

**Acceptance Scenarios**:

1. **Given** a PR with passing CI, a clean Copilot review on HEAD, no unresolved threads, and `ai-auto-merge-allowed` label, **When** the loop runs via any trigger type, **Then** it evaluates all 8
   actions in order and executes approve + merge (skipping already-completed actions).
2. **Given** a PR that has already been approved and merged, **When** the loop runs again,
   **Then** every action evaluates as "skipped" and no mutating API calls are made
   (read-only state snapshot and summary posting may still occur).
3. **Given** a PR with 3 commits above merge-base and no active Copilot session, **When** the loop runs, **Then** squash executes; **When** the loop runs again immediately after, **Then** squash is
   skipped (1 commit detected).
4. **Given** a PR in draft state with changes pushed, **When** the loop runs, **Then** publish executes first, then subsequent actions evaluate against the now-published state via the in-memory
   `DerivedState` object.

---

### User Story 2 — Active Session Detection Replaces Squash-Wait (Priority: P1)

As a maintainer, I want the squash-wait state machine (marker comments, cron scheduler,
attempt counters) replaced by a simple "is Copilot session active?" check so that squash,
thread resolution, and
repair dispatch are gated by a single, stateless precondition.

**Why this priority**: The squash-wait system is the largest source of complexity and the root cause of stuck PRs (e.g., PR #1549). Eliminating it is essential for the idempotent design.

**Covers**: FR-003, FR-005, FR-006, FR-010

**Independent Test**: Simulate a Copilot coding session (start event without terminal event) and verify that actions 4, 5, and 6 are all skipped. Then simulate the terminal event and verify that the
next run evaluates those actions as eligible.

**Acceptance Scenarios**:

1. **Given** a PR with `copilot_work_started` event and no subsequent terminal event,
   **When** the loop runs, **Then** resolve-threads, dispatch-repair, and squash are all
   skipped with reason "active Copilot session".
2. **Given** a PR where `copilot_work_finished` event exists after the latest
   `copilot_work_started`, **When** the loop runs, **Then** the active-session check returns
   false and those actions proceed
   to their other precondition evaluations.
3. **Given** a PR with `copilot_work_finished_failure` as the terminal event, **When** the loop runs, **Then** the session is considered inactive (failure is still terminal).

---

### User Story 3 — Thread Resolution on Every Trigger (Priority: P1)

As a developer, I want unresolved Copilot review threads from prior commits to be evaluated for resolution on every loop trigger so that threads are never left permanently open due to event-routing
gaps.

**Why this priority**: This directly addresses the #1509 spec gap where `COMMENTED` reviews never trigger resolution. It is the most user-visible bug in the current system.

**Covers**: FR-004, FR-005

**Independent Test**: Create a PR with unresolved Copilot review threads from a commit before HEAD, push a fix, then trigger the loop via `workflow_run`. Verify threads are resolved. Repeat via
`issue_comment` trigger — same result.

**Acceptance Scenarios**:

1. **Given** unresolved Copilot review comments from commit A, HEAD is commit B (pushed
   after review), and no active Copilot session, **When** the loop runs, **Then** SDK
   verification runs per-comment
   and threads with `COMMENT_RESOLVE` verdict are resolved.
2. **Given** the same state but a Copilot coding session is active, **When** the loop runs, **Then** thread resolution is skipped (waiting for session to complete).
3. **Given** all threads are already resolved, **When** the loop runs, **Then** the resolve-threads action reports "skipped — 0 unresolved threads".

---

### User Story 4 — Observability Comment on Every Run (Priority: P2)

As a team member monitoring PR progress, I want every loop run to post a concise summary comment on the PR with action results and a link to the workflow run logs so that I can understand what
happened without inspecting CI directly.

**Why this priority**: Critical for debugging and trust, but the loop functions correctly without it. It is the observability layer on top of the working pipeline.

**Covers**: FR-008

**Independent Test**: Trigger a loop run and verify a comment is posted containing the workflow run link, a table of all 8 actions with their precondition results and outcomes, and a collapsed state
snapshot section.

**Acceptance Scenarios**:

1. **Given** any loop trigger, **When** the run completes (success or early exit from guards), **Then** a comment is posted to the PR containing a clickable link to the GitHub Actions run.
2. **Given** a run where 2 actions executed and 6 were skipped, **When** the summary comment is posted, **Then** it contains a table with all 8 actions, their precondition status, and result
   (executed/skipped/blocked).
3. **Given** a run that exits at the guard step, **When** the summary is posted,
   **Then** it clearly indicates which guard blocked and still shows the full 8-action
   table with downstream actions marked blocked by guard.
4. **Given** consecutive runs with no state change, **When** the second run posts its comment, **Then** the comment shows all actions skipped (confirming idempotency visually).
5. **Given** prior AI-loop summary comments exist on the PR, **When** the new summary is posted, **Then** all prior summary comments whose first line is `<!-- agdt:ai-pr-loop-summary -->` are
   collapsed into `<details>` blocks via edit to reduce noise.

---

### User Story 5 — Detailed Workflow Run Logging (Priority: P2)

As a developer debugging a stuck PR, I want every precondition evaluation logged with full input data in the workflow run so that clicking the run link from the summary comment gives complete
traceability.

**Why this priority**: Supplements the PR comment with deep diagnostic data. Not needed for the loop to function but essential for production debugging.

**Covers**: FR-009

**Independent Test**: Trigger a run, open the workflow run link, and verify each action has a
collapsible log group showing the exact data inputs, boolean precondition results, decision
reasoning, and
API call outcomes.

**Acceptance Scenarios**:

1. **Given** any loop run, **When** viewing the workflow run logs, **Then** each action evaluation appears in its own `::group::` with structured key-value logging of all inputs.
2. **Given** an action that was skipped, **When** viewing its log group, **Then** the specific precondition that caused the skip is identified with its input values.
3. **Given** an action that made API calls, **When** viewing its log group, **Then** the API response status and relevant response data are logged.

---

### User Story 6 — Fully Automated Merge Without Manual Approval (Priority: P3)

As a team lead, I want the loop to approve and merge PRs without any manual intervention
when all automated checks pass so that PRs with `ai-auto-merge-allowed` flow from draft to
merged without human
involvement.

**Why this priority**: This is the end-to-end outcome that all other stories enable. It is P3
because it is an emergent property of P1+P2 stories working together, not a distinct
implementation unit.

**Covers**: FR-007, FR-012, FR-013

**Independent Test**: Create a PR, push code, label it `ai-auto-merge-allowed`, and verify the PR goes from draft → published → reviewed → approved → merged across multiple loop triggers without any
manual action.

**Acceptance Scenarios**:

1. **Given** a new PR with `ai-auto-merge-allowed` label, passing CI, clean Copilot review, and mergeable state, **When** the loop runs sufficient times, **Then** the PR is merged without any human
   intervention.
2. **Given** a PR where Copilot requests changes, the agent fixes them, and CI passes, **When** the loop runs after the fix, **Then** threads are resolved, squash occurs, approval is granted, and
   merge executes — all in a single run if preconditions align.

---

### Edge Cases

The following edge cases represent boundary conditions that the implementation must handle gracefully without breaking idempotency or causing duplicate actions.

When the GitHub Issues Events API returns events out of order or with
eventual-consistency gaps, the active-session check must use event `id` ordering
(monotonically increasing) rather than timestamps
to ensure deterministic evaluation regardless of API timing.

When another loop run is executing concurrently on the same PR, the existing evaluator lock mechanism must gate the entire pipeline. If a lock cannot be acquired, the run should exit cleanly and the
summary comment should note "concurrent evaluation skipped — lock held by another run."

When the PR is merged externally (by a human or another automation) between action
evaluations within a single run, each action must re-validate critical preconditions
(such as "PR still open") before
executing rather than relying solely on the initial snapshot. This prevents attempting to approve or squash an already-merged PR.

When the GitHub API returns transient errors during a specific action, the action should fail gracefully and log the error with full context. The summary should
report the action as "failed (transient)" and subsequent actions should continue evaluation. The next loop run will naturally retry the failed action. Both anticipated API errors and unhandled Python
exceptions are caught at the pipeline level — each action is wrapped in a try/except that logs the full traceback and marks the action as "failed (exception)" without halting the pipeline.

When the summary comment itself fails to post (e.g., rate limiting), the pipeline must not fail — the actions themselves already completed successfully. The failure should be logged as a warning and
the exit code should remain successful.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST evaluate all 8 actions (guards, publish, request-review,
  resolve-threads, dispatch-repair, squash, approve, merge) in documented order on every run,
  regardless of trigger
  event type. This means the same code path executes whether the trigger was `issue_comment`, `workflow_run(completed)`, or `pull_request_review(submitted)`. Guards are action 1 and are special only
  in that a "blocked" result prevents actions 2–8 from executing; all 8 actions are reported uniformly in the summary.

- **FR-002**: Each action MUST check its own completion state before executing — running the pipeline N times on unchanged state MUST produce no duplicate side effects. For example, if the PR is
  already published, the publish action returns "skipped" without making any API call.

- **FR-003**: The system MUST determine "active Copilot session" by comparing issue event IDs: a `copilot_work_started` event without a subsequent `copilot_work_finished` or
  `copilot_work_finished_failure` event (by ID ordering) indicates an active session. Implementation MUST call the Issues Events API, paginate all available pages client-side, and identify the
  session-related event (`copilot_work_started`, `copilot_work_finished`, `copilot_work_finished_failure`) with the **highest `id`** as the decision source. Event `id` is the authoritative ordering
  key because the Issues Events API does not guarantee delivery order within or across pages. If no session-related event is found after scanning all pages, session is inactive. Implementations MAY
  apply a performance optimisation (e.g., early termination once a session-complete event is confirmed to have a higher `id` than any session-start event seen so far), but only when the assumption is
  explicitly documented and a full-pagination fallback is provided. This single check replaces the entire squash-wait state machine.

- **FR-004**: Thread resolution (action 4) MUST evaluate all unresolved Copilot review comments from any review targeting a commit before HEAD, using SDK verification to determine resolve/keep-open
  verdicts per thread.

- **FR-005**: Thread resolution MUST NOT execute when a Copilot coding session is active OR a Copilot review is pending on HEAD. Both conditions indicate that new changes or review feedback may be
  incoming, making resolution premature.

- **FR-006**: Squash (action 6) MUST only execute when commits above merge-base > 1 AND no active Copilot session (coding or review) AND CI is passing. All three conditions must be true
  simultaneously.

- **FR-007**: Merge (action 8) MUST only execute when the PR is approved, CI is passing,
  `ai-auto-merge-allowed` label is present, PR is mergeable, and no unresolved threads
  remain. Missing any single
  condition results in "skipped" with the specific missing condition logged.

- **FR-008**: Every run MUST post a summary comment on the PR containing a workflow run link, action evaluation table (all 8 actions with precondition results and outcomes), and a collapsed state
  snapshot section showing key decision inputs. Each new summary comment MUST start with the exact sentinel `<!-- agdt:ai-pr-loop-summary -->` on line 1. Prior comments with that same first-line
  sentinel MUST be collapsed into `<details>` blocks via edit, with line 1 replaced by `<!-- agdt:ai-pr-loop-summary-collapsed -->`. Comments already marked with the collapsed sentinel MUST NOT be
  re-edited.

- **FR-009**: Every action evaluation MUST emit structured log output (via `logger.info`
  and GitHub Actions `::group::`) including all input data, precondition boolean results,
  and decision reasoning.
  This enables traceability from the summary comment link to full diagnostic detail.

- **FR-010**: The squash-wait state machine (marker comments, attempt counters, cron scheduling) MUST be removed and replaced by the active-session check defined in FR-003. No references to
  squash-wait markers shall remain in the production codebase.

- **FR-011**: The system MUST gather a full PR state snapshot once at the beginning of each run (as an immutable data structure; see Key Entities for the suggested `PRStateSnapshot` name) and use it
  as the single external source for evaluations in that run. Later actions MAY evaluate against a separate mutable derived-state structure (see Key Entities for the suggested `DerivedState` name) that
  tracks in-memory state changes produced by earlier actions in the same run (for example, publish changing draft → ready) without re-fetching PR state from external APIs. Concrete class or dictionary
  naming is left to the implementation; the Key Entities section defines these names non-normatively. The original snapshot remains immutable for logging and summary purposes.

- **FR-012**: Approval (action 7) MUST NOT execute if an approval already exists on the
  current HEAD SHA. The check must verify both the approval existence and that it targets
  the current commit, not
  a prior commit.

- **FR-013**: Repair dispatch (action 5) MUST respect existing cycle and deduplication limits to prevent infinite repair loops. The existing `check_cycle_limit` and `check_deduplication` guard logic
  remains applicable but moves into the action's precondition evaluation.

- **FR-014**: The pipeline MUST exit early (after guards) if any hard-blocking guard
  condition is met (fork PR, exclusion label, Docker-only changes, etc.), still posting the
  summary comment with the
  guard failure reason clearly indicated. If guard evaluation raises an exception, it MUST fail closed and be recorded as a guard block with the exception details logged. Downstream actions 2–8 are
  marked "blocked by guard" in the summary table.

### Non-Functional Requirements

- **NFR-001**: A single pipeline run MUST complete within 120 seconds under normal conditions (excluding external API latency spikes beyond 10 seconds per call). This ensures the loop can run
  frequently without accumulating a queue.

- **NFR-002**: The summary comment MUST be concise (< 2000 characters for the visible portion) to avoid PR comment noise. Detailed state data belongs in the collapsed `<details>` section only.

- **NFR-003**: The pipeline MUST be resilient to individual action failures — a failure in action N (including unhandled Python exceptions) MUST NOT prevent evaluation of actions N+1 through 8 (unless
  N is guards, which gates the entire pipeline). Each action execution is wrapped in a try/except at the pipeline level. Failed actions are reported in the summary as "failed (transient)" or "failed
  (exception)" and retried on the next run.

- **NFR-004**: All existing tests in `tests/unit/cli/ci/orchestrator/` MUST be migrated to the new architecture. Test coverage for the new pipeline MUST meet the repository's 100% requirement for
  modified files.

- **NFR-005**: The refactored code MUST follow the existing module structure under `agentic_devtools/cli/ci/` and maintain backward compatibility with the `EventPayload`, `PRMetadata`, and
  `ReviewInfo` dataclasses that are used by other modules.

- **NFR-006**: Log output MUST use structured key-value formatting compatible with GitHub Actions log grouping (`::group::` / `::endgroup::`) for collapsible sections in workflow run views.

### Key Entities

- **ActionResult**: Represents the outcome of a single action evaluation — contains action name, precondition statuses (list of named booleans), decision (executed/skipped/blocked/failed), and
  execution details (e.g., "2 threads resolved, 1 kept open"). This is the fundamental unit that feeds both the summary comment and the structured logging.

- **PipelineRunSummary**: Aggregates all ActionResults for a single run plus the state snapshot used for evaluation. Serialized to markdown for the PR summary comment and to JSON for structured log
  output.

- **PRStateSnapshot**: A frozen representation of all PR state gathered at run start — HEAD SHA, commit count above merge-base, CI status per check, review state (latest Copilot review ID, state,
  inline comment count), active session status, unresolved thread count and IDs, labels, draft status, mergeable status, and requested reviewers. This object is immutable for the duration of the run.

- **DerivedState**: A mutable companion to `PRStateSnapshot` that tracks in-memory state changes caused by earlier actions in the same run (e.g., `is_draft` flipping to `False` after publish).
  Subsequent actions read from `DerivedState` which falls through to the snapshot for unmodified fields. Exists only for the duration of a single pipeline run.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Running the loop 50 times consecutively on an unchanged PR state produces exactly 0 duplicate API calls (verified by mock assertion in integration tests counting provider method
  invocations after the first run).

- **SC-002**: Thread resolution executes on every trigger type — verified by running the loop via `issue_comment`, `workflow_run`, and `pull_request_review` events on a PR with 3 unresolved threads
  and confirming resolution occurs in all three cases (3/3 trigger types produce resolution).

- **SC-003**: The squash-wait state machine code (marker comment parsing, attempt counting, cron scheduling, `read_squash_wait_marker`, `write_squash_wait_marker`, `delete_squash_wait_marker`) is
  fully removed — zero references to squash-wait markers remain in production source files under `agentic_devtools/`.

- **SC-004**: Every loop run produces exactly 1 PR summary comment — verified by checking comment count increases by exactly 1 per run across 10 consecutive runs in integration tests.

- **SC-005**: A PR can go from draft → merged in ≤ 5 loop triggers without any manual intervention (given passing CI and clean review on the first trigger after publish).

- **SC-006**: Existing test files in `tests/unit/cli/ci/orchestrator/` are updated or replaced to cover the new pipeline architecture with 100% line coverage on all modified source files as reported
  by `agdt-test-file`.

- **SC-007**: Mean time from "all preconditions met for an action" to "action executed" is ≤ 1 loop trigger — no multi-trigger waiting is required for any single action (verified by asserting each
  action executes in the same run where its preconditions first become true).

---
*Generated by Copilot SDK (claude-opus-4.6)*
