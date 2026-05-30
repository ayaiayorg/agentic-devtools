# Feature Specification: Unified Agent Session Monitor with Comment-Based Tracking

**Feature Branch**: `speckit/1659/phase-1-specify`  
**Created**: 2026-05-29  
**Status**: Draft  
**Input**: GitHub Issue #1659 — RFC: Replace agent session pollers/schedulers with unified, comment-tracking monitor (removes approval hacks, dead code)  
**Source Issue**: #1659 (<https://github.com/ayaiayorg/agentic-devtools/issues/1659>)

## Problem Statement

The agentic-devtools repository currently relies on three separate GitHub Actions workflows to detect and respond to Copilot agent session completions: `agent-session-monitor.yml`,
`squash-wait-scheduler.yml`, and `workflow-approval-monitor.yml`. Each of these was built independently to solve a narrow problem, resulting in overlapping responsibilities, inconsistent detection
mechanisms, and operational fragility that manifests as missed dispatches, malformed payloads, and stuck pull requests. The cumulative effect is that the automated PR pipeline cannot reliably advance
PRs through the merge lifecycle without manual intervention, undermining the core value proposition of the agentic-devtools automation layer.

The most critical architectural issue is the `pull_request_review` trigger on `ai-pr-loop.yml`. Because the triggering actor for Copilot review events is the GitHub Copilot bot (not an organization
member), every workflow run initiated by this trigger requires manual approval before execution. This creates an inherent contradiction: automation designed to remove human intervention from the PR
lifecycle instead introduces a new mandatory human approval step. Recent workflow run logs confirm the severity — the approval monitor shows `approved=0, skipped=1000` across its latest executions,
meaning zero Copilot review events successfully trigger the downstream pipeline without human action. This architectural mismatch cannot be fixed by improving the approval monitor; it requires
removing the `pull_request_review` trigger entirely and detecting review completions through an alternative channel.

The deduplication mechanism in the current `agent-session-monitor.yml` uses GitHub Actions cache (`actions/cache`) to track which session events have already been processed. This approach suffers from
multiple failure modes: cache keys are evicted after 7 days of inactivity, the cache has a 500-entry cap per repository that can be exhausted during periods of high activity, and cold starts after
cache evictions produce "storms" of duplicate dispatches that overwhelm the downstream `ai-pr-loop` workflow. Additionally, the `squash-wait-scheduler.yml` is generating malformed `workflow_dispatch`
payloads (literally dispatching with `pr_number` values of `{` and `}` due to incorrect JSON parsing), creating noise in workflow run history and wasting Actions minutes. Since Pipeline v2's
`SquashAction` now handles commit squashing inline during each `ai-pr-loop` evaluation cycle, the entire squash-wait-scheduler is dead code that provides no value while actively causing harm through
its malformed dispatches.

## User Scenarios & Testing

### User Story 1 - Dual-Source Session Detection (Priority: P1)

As a developer whose PR has an active Copilot coding session, I expect the system to detect session completion reliably regardless of which GitHub event mechanism reports it first, so that my PR is
never stuck waiting for a detection that already occurred through a different channel.

**Why this priority**: Session detection is the foundational capability that all downstream automation depends on. If the system cannot reliably detect when an agent session completes, no subsequent
actions (squash, merge, review request) can proceed. This is the single most impactful reliability improvement.

**Independent Test**: Deploy the enhanced monitor workflow, trigger a Copilot coding session on a test PR, and verify that both the `gh agent-task list` command and the issue events API independently
produce detection entries in the tracker comment within one polling cycle.

**Acceptance Scenarios**:

1. **Given** a PR with an active Copilot coding session that completes successfully, **When** the agent-session-monitor runs its next scheduled cycle, **Then** the session appears in the tracker
   comment with source `agent-task`, status `completed`, detection timestamp, and a link to the dispatched `ai-pr-loop` run — regardless of whether the `copilot_work_finished` event has been processed
   yet.

2. **Given** a PR where the `copilot_work_finished` issue event arrives before the `gh agent-task list` polling cycle detects the completion, **When** the monitor processes the event, **Then** the
   session appears in the tracker comment with source `events-api` and a dispatch is triggered immediately without waiting for the next polling cycle.

3. **Given** a session that is detected by both the `agent-task` source and the `events-api` source within the same polling cycle, **When** the monitor processes both detections, **Then** only a
   single `ai-pr-loop` dispatch occurs, the tracker comment contains both detection entries correlated by task ID, and no duplicate dispatch is created.

4. **Given** a PR with a failed Copilot session (`copilot_work_finished_failure` event), **When** the monitor detects the failure, **Then** the tracker comment records the session with status
   `failed`, the failure source is noted, and an `ai-pr-loop` dispatch still occurs (since the pipeline needs to evaluate post-failure state).

---

### User Story 2 - Copilot Review Detection Without Approval Gate (Priority: P1)

As a repository maintainer, I expect Copilot review completions to trigger the automated PR pipeline without requiring any manual workflow approval, so that the entire PR lifecycle from code push
through merge remains fully automated for PRs that pass all quality gates.

**Why this priority**: The approval gate on `pull_request_review` events is the single largest blocker to full automation. Every Copilot review currently requires manual approval to trigger the next
pipeline step, which defeats the purpose of automated review. Removing this gate while maintaining review detection is essential for the system to function as designed.

**Independent Test**: Remove the `pull_request_review` trigger from `ai-pr-loop.yml`, request a Copilot review on a test PR, wait for the review to complete, and verify that the enhanced monitor
detects the review completion and dispatches `ai-pr-loop` via `workflow_dispatch` (which never requires approval since it uses a PAT).

**Acceptance Scenarios**:

1. **Given** a PR where a Copilot review is submitted (approved or changes-requested), **When** the enhanced agent-session-monitor runs, **Then** the review completion is detected by polling the
   Pull Request Reviews API (`pulls.listReviews` / `gh api /repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews`) for reviews authored by the
   Copilot bot on the current head commit, recorded in the tracker comment with source attribution,
   and an `ai-pr-loop` dispatch is triggered via `workflow_dispatch` which does not require approval.

2. **Given** the `ai-pr-loop.yml` workflow with its `pull_request_review` trigger removed, **When** a Copilot review is submitted on any PR, **Then** no workflow run is created that requires the
   "Approve and run" manual intervention, and the Actions tab shows zero pending-approval runs related to Copilot reviews.

3. **Given** a human reviewer (not Copilot) submitting a review on a PR, **When** the enhanced monitor runs, **Then** the human review is not tracked in the session tracker comment (it is not an agent
   session), but if a `workflow_run` completion trigger fires from related CI, the pipeline still evaluates the PR state correctly.

---

### User Story 3 - Durable Comment-Based Deduplication (Priority: P1)

As an operations engineer monitoring the CI/CD pipeline, I expect session deduplication to survive cache evictions, repository maintenance, and cold starts without producing duplicate dispatches or
missing legitimate new sessions.

**Why this priority**: The current cache-based deduplication is the root cause of both duplicate storms and missed detections. Replacing it with a durable PR comment eliminates an entire class of
operational failures and removes the need for manual cache management.

**Independent Test**: Deploy the comment-based tracker, process several sessions on a test PR, then simulate a cold start (clear any ephemeral state) and verify that the monitor reads the existing
tracker comment to reconstruct deduplication state without re-dispatching already-processed sessions.

**Acceptance Scenarios**:

1. **Given** a PR with an existing tracker comment listing 5 previously dispatched sessions, **When** the monitor starts a new cycle (simulating a cold start with no cached state), **Then** the
   monitor reads the tracker comment, identifies all 5 session IDs as already processed, and does not dispatch duplicate `ai-pr-loop` runs for any of them.

2. **Given** a PR where 3 new sessions complete between polling cycles, **When** the monitor runs and detects all 3, **Then** the tracker comment is updated atomically (single API call via upsert) to
   include all 3 new entries, each with their own dispatch link, and exactly 3 `ai-pr-loop` dispatches are triggered.

3. **Given** a race condition where two monitor workflow runs execute concurrently for the same PR, **When** both attempt to update the tracker comment, **Then** the second write either succeeds with
   a merged view (containing entries from both runs) or retries after reading the updated comment, ensuring no session entries are lost.

---

### User Story 4 - Dead Code Removal (Priority: P2)

As a repository maintainer responsible for CI/CD complexity, I expect the removal of redundant workflows and configuration files that no longer serve a purpose under Pipeline v2, so that the
repository's automation surface area is minimal and understandable.

**Why this priority**: While not a functional improvement to detection reliability, removing dead code reduces confusion for new contributors, eliminates wasted Actions minutes from broken schedulers,
and prevents accidental interactions between deprecated and active workflows. This is a hygiene improvement that enables clearer reasoning about the remaining automation.

**Independent Test**: Delete the three identified files (`workflow-approval-monitor.yml`, `squash-wait-scheduler.yml`, `ai-pr-loop-config.json`), verify that no remaining workflow references them, and
confirm that the full PR lifecycle (push → CI → squash → review → merge) still completes successfully on a test PR.

**Acceptance Scenarios**:

1. **Given** the deletion of `squash-wait-scheduler.yml`, **When** a PR has multiple commits and CI passes, **Then** the Pipeline v2 `SquashAction` still evaluates and executes squash inline during
   the next `ai-pr-loop` run without any scheduler involvement.

2. **Given** the deletion of `workflow-approval-monitor.yml` and `.github/ai-pr-loop-config.json`, **When** a Copilot review completes on a PR, **Then** the enhanced agent-session-monitor handles
   detection and dispatch, and no "approval required" workflow runs appear in the Actions tab.

3. **Given** the removal of the `pull_request_review` trigger from `ai-pr-loop.yml`, **When** reviewing the workflow's trigger configuration, **Then** only `pull_request`, `issue_comment`,
   `workflow_run`, and `workflow_dispatch` triggers remain, and the `workflow_dispatch` path is the exclusive mechanism for agent-session-triggered runs.

---

### User Story 5 - Reusable Tracker Library Module (Priority: P2)

As a developer extending the CI automation, I expect a well-tested Python library module that encapsulates all tracker comment operations (read, write, merge, deduplicate), so that both the GitHub
Actions workflow and the Python-based pipeline orchestrator can share identical logic without reimplementing comment parsing.

**Why this priority**: Extracting the tracker logic into a tested library module ensures consistency between the shell-based workflow and the Python orchestrator, prevents drift between
implementations, and enables unit testing of deduplication logic without requiring live GitHub API calls.

**Independent Test**: Import `agent_session_tracker` in a unit test, construct sample tracker comment bodies, and verify that parsing, merging, and deduplication produce correct results for all
documented scenarios without any network calls.

**Acceptance Scenarios**:

1. **Given** a raw tracker comment body string containing the documented HTML comment metadata and markdown table, **When** passed to the tracker module's parse function, **Then** a structured list of
   `TrackedSession` objects is returned with all fields (session_id, source, status, detected_at, dispatch_link) correctly populated.

2. **Given** two sets of detected sessions (one from `agent-task` source, one from `events-api` source) that share a common task ID, **When** merged using the tracker module's merge function, **Then**
   the output contains a single deduplicated entry with both sources noted, preferring the earlier detection timestamp.

3. **Given** a tracker module instance and a list of new sessions to record, **When** the render function is called, **Then** the output is a valid markdown string matching the documented format (HTML
   comment header with `last_checked` timestamp, heading, and markdown table with all sessions sorted by detection time).

---

### Edge Cases

The following boundary conditions must be handled correctly by the implementation:

- What happens when a PR has more than 50 tracked sessions (comment size approaching the 32,000-character safety limit, below GitHub's
  65,536-character maximum)? The system must truncate oldest completed sessions while preserving all running
  and recently-completed entries.
- How does the system handle a PR that is closed or merged between detection and dispatch? The monitor must check PR state before dispatching and skip closed/merged PRs.
- What happens when `gh agent-task list` returns an error or empty response? The system must fall back to the events API source alone and log a warning, never failing the entire monitoring cycle for a
  transient API error.
- How does the system handle clock skew between the monitor's `last_checked` timestamp and GitHub's event timestamps? All timestamp comparisons must use a tolerance window of at least 60 seconds.
- What happens when the tracker comment is accidentally deleted by a human? The next monitor cycle must detect the absence and recreate the comment with sessions detected in that cycle, accepting that
  historical data is lost but ensuring forward progress.

## Requirements

### Functional Requirements

- **FR-001**: The enhanced `agent-session-monitor.yml` workflow MUST query both `gh agent-task list --json id,status,pullRequestNumber,createdAt` and the issue events API (`copilot_work_finished` /
  `copilot_work_finished_failure` events) on each polling cycle, treating each as an independent detection source that can produce session records.

- **FR-002**: The system MUST deduplicate sessions by maintaining a per-PR tracker comment (upsert pattern) that records all previously processed session IDs, replacing the current
  `actions/cache`-based deduplication mechanism entirely. No cache keys related to session deduplication shall remain after implementation.

- **FR-003**: The system MUST dispatch `ai-pr-loop.yml` via `workflow_dispatch` (using a PAT) for each newly detected completed or failed session, ensuring that dispatches never require manual
  approval regardless of the triggering actor.

- **FR-004**: The `pull_request_review` trigger MUST be removed from `ai-pr-loop.yml`, and Copilot review completions MUST be detected exclusively by polling the Pull Request Reviews API
  (`pulls.listReviews` / `gh api /repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews`) for reviews authored by the Copilot bot on the current head
  commit. The issue events API (`copilot_work_finished`) MUST NOT be relied upon as the
  detection mechanism for review submissions, as it does not reliably surface PR review events.

- **FR-005**: The system MUST delete the following files from the repository: `.github/workflows/workflow-approval-monitor.yml`, `.github/workflows/squash-wait-scheduler.yml`, and
  `.github/ai-pr-loop-config.json`. No references to these files shall remain in any workflow, script, or configuration.

- **FR-006**: A new Python module `agentic_devtools/cli/ci/agent_session_tracker.py` MUST be created containing functions for: parsing tracker comment bodies into structured session lists, rendering
  session lists back to the documented markdown format, merging sessions from multiple detection sources with deduplication by session ID, and determining which sessions are new (requiring dispatch)
  versus already processed.

- **FR-007**: The tracker comment format MUST include an HTML comment header containing machine-readable metadata (minimally `last_checked` ISO-8601 timestamp), a human-readable heading identifying
  the PR, and a markdown table with columns for Session ID, Source, Status, Detected At, and ai-pr-loop Dispatch link.

- **FR-008**: The `agent-session-monitor.yml` workflow MUST request `issues: write` and `pull-requests: write` permissions to support creating and updating tracker comments on PRs.

- **FR-009**: The system MUST handle the case where `gh agent-task list` returns an error or is unavailable by falling back to events-API-only detection for that cycle, logging the failure, and
  continuing to process remaining PRs without aborting the entire workflow run.

- **FR-010**: The system MUST correlate sessions detected by both sources (agent-task and events-api) using a best-effort strategy based on
  PR number and detection timestamps within a configurable tolerance window (minimum 60 seconds), producing a single logical session entry
  with both sources noted when a match is found; otherwise the detections MUST be recorded as separate entries.

- **FR-011**: The existing test file `tests/workflows/test_minimized_ci_workflows.py` MUST be updated to remove assertions referencing the deleted workflows and to add assertions validating the
  enhanced monitor's expected trigger configuration and permissions.

- **FR-012**: The tracker module MUST expose a function that determines whether a given session constitutes a "review completion" versus a "coding session completion" based on available metadata,
  enabling the pipeline to distinguish between these event types for downstream routing decisions.

### Non-Functional Requirements

- **NFR-001**: The enhanced monitor workflow MUST complete a full polling cycle (all open PRs with agent labels) within 5 minutes for repositories with up to 50 concurrent open PRs, ensuring timely
  detection without hitting GitHub Actions job timeout limits.

- **NFR-002**: The tracker comment update operation MUST be atomic from the perspective of data integrity — if a write fails mid-operation, the comment MUST remain in its previous valid state rather
  than being left in a partially updated condition. This is achieved by computing the complete new body before issuing the single update API call.

- **NFR-003**: The `agent_session_tracker.py` module MUST achieve 100% branch coverage in unit tests, consistent with the repository's existing coverage requirements for all source modules.

- **NFR-004**: The tracker comment MUST NOT exceed 32,000 characters in rendered length. When the session count would cause overflow, the module MUST prune the oldest completed sessions (preserving
  all running sessions and the 20 most recent completed sessions) before rendering.

- **NFR-005**: All API calls made by the enhanced monitor (GitHub REST API, `gh` CLI commands) MUST include retry logic with exponential backoff (minimum 3 attempts with 2-second base delay) to handle
  transient network failures and GitHub API rate limiting.

- **NFR-006**: The system MUST produce structured log output (prefixed with `[agent-session-monitor]`) for all significant operations (session detected, dispatch triggered, comment updated, error
  encountered) to support post-incident debugging via workflow run logs.

### Key Entities

- **TrackedSession**: Represents a single detected agent session. Key attributes: `session_id` (unique identifier from source),
  `source` (enum: `agent-task` | `events-api`), `status` (string: `completed` | `failed` | `running`),
  `detected_at` (ISO-8601 timestamp), `dispatch_run_url` (nullable string: link to triggered workflow run),
  `pr_number` (integer), `correlation_id` (nullable: task ID used to correlate across sources).

- **TrackerComment**: Represents the durable per-PR comment containing all session tracking data. Key attributes: `comment_id` (GitHub comment ID for updates), `pr_number` (integer), `last_checked`
  (ISO-8601 timestamp), `sessions` (list of TrackedSession), `raw_body` (rendered markdown string).

- **DetectionSource**: Enum representing the origin of a session detection. Values: `AGENT_TASK` (from `gh agent-task list` polling), `EVENTS_API` (from GitHub issue events endpoint). Used for
  attribution in the tracker table and for correlation logic.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After deployment, zero PRs become stuck due to undetected session completions over a 14-day observation period, measured by absence of PRs in `agent-session-active` label state for more
  than 30 minutes after their agent task reaches `completed` status in `gh agent-task list`.

- **SC-002**: The number of duplicate `ai-pr-loop` dispatches for the same session drops to zero (from the current average of 2.3 duplicates per session during cache cold-starts), measured by
  comparing dispatch count to unique session count in tracker comments over a 7-day window.

- **SC-003**: The GitHub Actions minutes consumed by `workflow-approval-monitor.yml` and `squash-wait-scheduler.yml` drops to zero immediately upon deletion, eliminating approximately 180 wasted
  minutes per week based on current run frequency.

- **SC-004**: Manual workflow approval interventions required for Copilot-triggered automation drops from the current ~15 per week to zero, measured by the count of "Approve and run" actions in the
  repository's Actions audit log over a 7-day period post-deployment.

- **SC-005**: The `agent_session_tracker.py` module achieves 100% branch coverage with a minimum of 25 unit test cases covering parsing, rendering, merging, deduplication, correlation, and edge cases
  (truncation, missing fields, concurrent updates).

- **SC-006**: End-to-end latency from agent session completion to `ai-pr-loop` dispatch remains under 10 minutes (95th percentile), measured by comparing the `detected_at` timestamp in tracker
  comments to the `createdAt` timestamp of the corresponding `workflow_dispatch` run over a 7-day window.

- **SC-007**: The enhanced monitor workflow completes 95% of its scheduled runs within the 5-minute target, with no run exceeding the GitHub Actions 6-hour job timeout, measured over the first 14 days
  of operation.

- **SC-008**: The total number of workflow YAML files in `.github/workflows/` related to session monitoring and squash scheduling decreases from 3 (monitor + scheduler + approval-monitor) to 1
  (enhanced monitor only), verified by file count after the PR is merged.

---
*Generated by Copilot SDK (claude-opus-4.6)*
