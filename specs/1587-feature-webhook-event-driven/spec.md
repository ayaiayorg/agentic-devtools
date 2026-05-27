# Feature Specification: Event-Driven Trigger for AI PR Loop on Agent Session Completion

**Feature Branch**: `1587-feature-webhook-event-driven`  
**Created**: 2026-05-27  
**Status**: Draft  
**Input**: User description: "Add webhook or event-driven trigger for ai-pr-loop when agent session is finished on PR"  
**Source Issue**: #1587 (<https://github.com/ayaiayorg/agentic-devtools/issues/1587>)

## Problem Statement

The AI PR loop (`ai-pr-loop.yml`) currently relies on a polling-based squash-wait state machine to detect when a Copilot agent session has finished working on a pull request. The orchestrator
(`orchestrator.py`) checks Issues Events API for `copilot_work_finished` events during each cron-scheduled cycle, incrementing attempt counters and deferring to the next tick when no terminal event is
found. This introduces latency of up to several minutes between the agent completing its work and the AI PR loop processing the result.

The existing triggers for the workflow include `pull_request`, `pull_request_review`, `issue_comment`, `workflow_run`, and `workflow_dispatch` — but none of these fire directly in response to a
Copilot session completing. The `issue_comment` trigger only fires when Copilot posts a comment, which is a secondary effect that may not always occur or may be delayed. The `workflow_run` trigger
only activates after CI workflows complete, not after agent sessions end.

This gap means that after an agent finishes its work (pushing commits, resolving review comments, etc.), the system must wait for the next scheduled poll cycle before the orchestrator can evaluate the
PR's post-agent state, request reviews, approve, or merge. In practice, this adds 2–5 minutes of unnecessary latency to the feedback loop, degrades developer experience, and creates windows where race
conditions between concurrent triggers can cause duplicate or conflicting runs.

The desired end state is an event-driven architecture where the `copilot_work_finished` signal immediately triggers the AI PR loop for the affected PR, reducing the detection-to-action latency to
under 30 seconds while maintaining idempotency guarantees and not introducing duplicate workflow runs.

## User Scenarios & Testing

### User Story 1 - Immediate Post-Agent PR Processing (Priority: P1)

As a developer with the `ai-auto-merge-allowed` label on my PR, when the Copilot agent finishes addressing review comments on my pull request, I want the AI PR loop to immediately evaluate the PR
state and proceed with approval/merge without waiting for the next polling cycle.

**Why this priority**: This is the core value proposition of the feature. The entire purpose of event-driven triggering is to eliminate the polling delay between agent completion and loop execution.
Without this, the feature delivers no value.

**Independent Test**: Can be tested by having a Copilot agent session complete on a PR and measuring the time between the `copilot_work_finished` event appearing in the Issues Events API and the AI PR
loop workflow starting. The test passes if the workflow starts within 120 seconds (2 minutes) of the event being recorded.

**Acceptance Scenarios**:

1. **Given** a PR with `ai-auto-merge-allowed` label where Copilot is actively working, **When** the agent session completes successfully and a `copilot_work_finished` event is recorded on the PR,
   **Then** the AI PR loop workflow is triggered for that specific PR number within 120 seconds of the event timestamp.
2. **Given** a PR where the AI PR loop is already running for the same PR number, **When** a `copilot_work_finished` event fires and would trigger a second run, **Then** the concurrency group
   mechanism prevents duplicate execution and the second run is queued or skipped gracefully.
3. **Given** a PR where the agent session completes with a failure (`copilot_work_finished_failure`), **When** the event-driven trigger detects this terminal event, **Then** the AI PR loop is still
   triggered so the orchestrator can enter its recovery/failure handling path.

---

### User Story 2 - Idempotent Event Processing (Priority: P1)

As a repository maintainer, I want the event-driven trigger to be safely idempotent so that even if the same `copilot_work_finished` event is detected multiple times (due to polling overlap or retry),
the AI PR loop processes the PR exactly once per unique terminal event.

**Why this priority**: Without idempotency guarantees, the event-driven trigger could cause duplicate approvals, duplicate merge attempts, or conflicting state transitions. This is a safety-critical
requirement that must ship alongside the trigger itself.

**Independent Test**: Can be tested by simulating a scenario where both the event-driven trigger and a residual polling cycle detect the same `copilot_work_finished` event. The system should produce
exactly one workflow run (or the second should be cancelled by concurrency controls).

**Acceptance Scenarios**:

1. **Given** the event-driven monitor has already dispatched the AI PR loop for a `copilot_work_finished` event with a specific event ID, **When** a subsequent polling cycle or duplicate webhook
   delivery detects the same event, **Then** no additional workflow run is dispatched for that event ID.
2. **Given** a PR that has already been merged by the AI PR loop, **When** a late-arriving event-driven trigger fires for the same PR, **Then** the orchestrator's existing guards (dedup markers, state
   checks) cause the run to exit early without side effects.
3. **Given** two `copilot_work_finished` events on the same PR within a short window (e.g., from a retry), **When** the monitor processes both, **Then** only one `repository_dispatch` or
   `workflow_dispatch` is emitted, deduplicated by event ID.

---

### User Story 3 - Graceful Coexistence with Existing Triggers (Priority: P2)

As a developer, I want the new event-driven trigger to coexist with all existing AI PR loop triggers (pull_request, issue_comment, workflow_run, etc.) without causing conflicts, so that PRs continue
to be processed correctly regardless of which event fires first.

**Why this priority**: The existing trigger ecosystem is battle-tested and handles many edge cases. The new event-driven path must integrate cleanly without breaking existing behavior. This is
important but secondary to the core trigger mechanism itself.

**Independent Test**: Can be tested by opening a PR, having Copilot submit a review (triggering `pull_request_review`), then having the agent finish work (triggering the event-driven path), and
verifying that both triggers result in correct orchestrator behavior with no state corruption.

**Acceptance Scenarios**:

1. **Given** a PR where `issue_comment` trigger fires from a Copilot bot comment AND the event-driven trigger fires from `copilot_work_finished` within the same minute, **When** both workflow runs
   start, **Then** the concurrency group `ai-pr-loop-{pr_number}` ensures only one runs at a time and the second is queued.
2. **Given** the event-driven monitor workflow is temporarily disabled or fails, **When** a Copilot session finishes, **Then** the existing `issue_comment` and `workflow_run` triggers still provide
   fallback processing (degraded latency but no loss of functionality).
3. **Given** the event-driven trigger is the first to process a PR after agent completion, **When** a subsequent `workflow_run` trigger fires for the same PR after CI completes, **Then** the
   orchestrator handles both gracefully via its existing dedup marker checks.

---

### User Story 4 - Monitor Workflow Observability (Priority: P3)

As a repository operator, I want visibility into the event-driven monitor's activity — which PRs it detected sessions for, which dispatches it issued, and any failures — so that I can diagnose issues
and tune configuration.

**Why this priority**: Observability is essential for production operation but does not block the core feature from delivering value. It can be incrementally improved after launch.

**Independent Test**: Can be tested by inspecting the monitor workflow's run logs after a Copilot session completes, verifying that structured output indicates which PRs were scanned, which events
were found, and what dispatch actions were taken.

**Acceptance Scenarios**:

1. **Given** the monitor workflow runs on schedule, **When** it detects a `copilot_work_finished` event for PR #42, **Then** the workflow run logs contain a structured entry showing `pr_number=42`,
   `event_id=<id>`, `action=dispatched`, and the timestamp.
2. **Given** the monitor workflow encounters a GitHub API rate limit or transient error, **When** it cannot complete scanning, **Then** it logs the error with sufficient context for debugging and
   exits with a non-zero code (making the failure visible in the Actions UI).

---

### Edge Cases

- What happens when a PR is closed or merged between the time the `copilot_work_finished` event fires and the dispatched workflow starts? The orchestrator must check PR state at the beginning of
  execution and exit early if the PR is no longer open.
- How does the system handle a `copilot_work_started` event that is never followed by a terminal event (orphaned session)? The existing `_DEFAULT_MAX_SESSION_AGE_SECONDS` (3600s) timeout in
  `session_detector.py` provides a staleness boundary; the monitor should respect this and not wait indefinitely.
- What happens if the GitHub Issues Events API has eventual-consistency delays and the `copilot_work_finished` event is not immediately visible? The monitor should retry on the next scheduled cycle;
  the existing orchestrator already handles this via its head-pushed-at timestamp filtering and retry-without-filter fallback.
- What happens when multiple PRs have concurrent agent sessions finishing at the same time? The monitor must dispatch independent triggers for each PR, and the per-PR concurrency group ensures they do
  not conflict.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST provide a mechanism that detects `copilot_work_finished` and `copilot_work_finished_failure` events on open pull requests and triggers the AI PR loop workflow for the
  affected PR number within 120 seconds of the event being recorded in the GitHub Issues Events API.

- **FR-002**: The system MUST deduplicate event-driven triggers so that a single `copilot_work_finished` event (identified by its unique event ID) results in at most one dispatched AI PR loop workflow
  run. The deduplication mechanism must persist state across monitor cycles to prevent re-processing of already-handled events.

- **FR-003**: The system MUST pass the PR number to the AI PR loop workflow when dispatching via `repository_dispatch` or `workflow_dispatch`, using a format compatible with the existing `pr_number`
  input parameter and concurrency group expression.

- **FR-004**: The system MUST only trigger for PRs that belong to the same repository (not forks), are currently open (not closed or merged), and have not been excluded via the `ai-pr-loop-ignore`
  label, consistent with the existing guard checks in the orchestrator.

- **FR-005**: The system MUST include a `trigger_reason` field in dispatched events that identifies the source as the event-driven monitor (e.g., `"agent_session_finished"`) so the orchestrator can
  log and differentiate this trigger path from other dispatch sources.

- **FR-006**: The system MUST coexist with all existing AI PR loop triggers without requiring removal or modification of those triggers. The event-driven mechanism supplements the existing trigger
  set; it does not replace any trigger until explicitly configured to do so.

- **FR-007**: The system MUST handle both successful (`copilot_work_finished`) and failed (`copilot_work_finished_failure`) terminal events, dispatching the AI PR loop for both so that the
  orchestrator's recovery logic can execute for failures.

### Non-Functional Requirements

- **NFR-001**: The event-driven monitor workflow MUST complete each scheduled run within 5 minutes to avoid overlapping with subsequent scheduled cycles. If scanning all open PRs exceeds this budget,
  the monitor must prioritize recently-active PRs.

- **NFR-002**: The event-driven trigger MUST NOT increase the overall GitHub Actions minutes consumption by more than 15% compared to the current polling-based approach, measured over a 7-day rolling
  window. The monitor workflow itself should be lightweight (under 2 minutes per run for typical repositories with fewer than 20 open PRs).

- **NFR-003**: The system MUST be resilient to transient GitHub API failures (rate limits, 5xx errors). A single failed API call must not prevent the monitor from processing other PRs in the same
  cycle, and failed PRs should be retried on the next cycle.

- **NFR-004**: The system MUST produce structured, parseable log output that enables operators to audit which events were processed, which dispatches were issued, and which PRs were skipped (with
  reasons). Log format should be consistent with existing orchestrator logging patterns.

### Key Entities

- **Agent Session Event**: A GitHub Issues Events API entry with event type `copilot_work_finished`, `copilot_work_finished_failure`, or `copilot_work_started`. Identified by a unique numeric event
  ID, associated with a PR number, and timestamped with `created_at`.
- **Event Dispatch Record**: A persistent record (stored as workflow artifact, state file, or issue comment marker) indicating that a specific event ID has already been dispatched to the AI PR loop.
  Used for deduplication across monitor cycles.
- **Monitor Cycle**: A single execution of the scheduled monitor workflow. Scans all eligible open PRs, checks for unprocessed terminal events, and dispatches triggers as needed.

## Success Criteria

### Measurable Outcomes

- **SC-001**: The median time between a `copilot_work_finished` event being recorded and the AI PR loop workflow starting for that PR MUST be under 120 seconds, measured across at least 20 agent
  session completions over a 14-day period after deployment.

- **SC-002**: Zero duplicate AI PR loop runs caused by the event-driven trigger (where "duplicate" means two runs processing the same PR for the same terminal event) over a 30-day observation period.
  The concurrency group and deduplication mechanism must prevent all duplicates.

- **SC-003**: The event-driven monitor workflow MUST achieve a success rate of at least 95% (successful runs / total scheduled runs) over a 30-day period, with failures limited to transient
  infrastructure issues rather than logic errors.

- **SC-004**: After the event-driven trigger is operational, the average end-to-end time from agent session completion to PR merge (for PRs with `ai-auto-merge-allowed` and passing CI) MUST decrease
  by at least 40% compared to the baseline measured in the 14 days prior to deployment.

- **SC-005**: All existing AI PR loop trigger paths (pull_request, pull_request_review, issue_comment, workflow_run, workflow_dispatch) MUST continue to function without regression, verified by the
  existing integration test suite passing at 100% after deployment.

---
*Generated by Copilot SDK (claude-opus-4.6)*
