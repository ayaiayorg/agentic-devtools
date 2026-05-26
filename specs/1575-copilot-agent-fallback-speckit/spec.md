# Feature Specification: Copilot Agent Fallback on SpecKit Generation Failures

**Feature Branch**: `speckit/1575/phase-2-clarify`  
**Created**: 2026-05-26  
**Status**: Draft  
**Input**: User description: "Add automatic Copilot coding agent fallback when SpecKit LLM pipeline fails structural validation"  
**Source Issue**: #1575 (<https://github.com/ayaiayorg/agentic-devtools/issues/1575>)

---

## Clarifications

### Session 2026-05-26

- Q: Where exactly does the fallback logic execute — within the Python orchestrator (`agdt-speckit-trigger` / `process_speckit_label_event`) or as a separate workflow step after the orchestrator step
  fails? → A: The fallback logic executes as a new composite action (or `actions/github-script` block) in a **dedicated workflow step** that runs after the main orchestrator step fails
  (`if: failure()`). It reads a machine-readable failure signature emitted by the orchestrator step via `$GITHUB_OUTPUT` or a workspace file to distinguish structural validation failures from
  infrastructure errors; free-form logs are used only for observability/debugging, not classification. This keeps the fallback decoupled from the orchestrator internals and allows it to be shared
  between both workflow files.

- Q: How is "at least one existing successful spec as a format example" (FR-003) selected and provided to the agent? → A: The fallback logic uses a hardcoded reference to the `specs/` directory in the
  repository (e.g., `specs/1505-structural-validation-and-retry/spec.md`) as a known-good example. The reference is included as a file path instruction in the problem statement (e.g., "Use
  `specs/1505-structural-validation-and-retry/spec.md` as a structural reference"). A repository variable `SPECKIT_REFERENCE_SPEC_PATH` may optionally override the default reference path.

- Q: How is the agent task ID/URL persisted for the follow-up mechanisms described in FR-012 (polling job and PR-creation trigger)? → A: The agent task ID and URL are persisted in a **machine-readable
  marker comment** posted on the issue (e.g., `<!-- speckit:agent-fallback task_id=<id> task_url=<url> issue=<number> phase=<N> -->`). The follow-up PR-creation workflow detects terminal success by
  matching the `speckit/` branch pattern on `pull_request` events with `types: [opened]` (or webhook payloads where `action` is `opened`). The follow-up polling job is a scheduled workflow
  (`workflow_dispatch` or `schedule`) that scans issues with the `speckit:agent-fallback` label, extracts task IDs from the marker comments, queries the Coding Agent API for terminal status, and
  removes `speckit:processing` on terminal failure states.

- Q: What is the expected response schema from the Copilot Coding Agent API (`POST /repos/{owner}/{repo}/copilot/coding-agent/tasks`) that the implementation must handle? → A: Based on the GitHub
  Copilot Coding Agent API, the response is a JSON object containing at minimum `{ "id": "<task-id>", "url": "<task-url>", "status": "queued" }`. The implementation must extract `id` and `url` for
  persistence and observability. Non-2xx responses or missing `id`/`url` fields trigger the graceful degradation path (FR-011).

- Q: Should the initial implementation cover all 5 phases equally, or is a phased rollout (Phase 1 first, then Phases 2–5) acceptable given the different workflow architectures? → A: The
  implementation MUST cover all 5 phases from the start (FR-010 is non-negotiable). However, the shared composite action/script accepts a `phase` input parameter, and each workflow passes the
  appropriate phase context. Phase 1 uses `speckit-issue-trigger.yml`; Phases 2–5 use `speckit-phase-progression.yml`. Both invoke the same reusable fallback logic.

---

## Problem Statement

When the SpecKit pipeline fails to generate a valid specification due to LLM structural validation errors (missing sections, insufficient requirements/user stories, etc.), the process halts with a
`speckit:failed` label and requires manual intervention. This was observed on issue #1569 where the LLM output failed validation after exhausting all 3 retries:

```text
[Specify] Validation failed — all 3 retries exhausted
Error: Specify phase failed structural validation after 3 attempts.
Failures:
  MISSING_SECTIONS: ## Problem Statement, ## User Scenarios & Testing, ## Requirements, ## Success Criteria
  INSUFFICIENT_REQUIREMENTS: found=2, minimum=5
  INSUFFICIENT_USER_STORIES: found=0, minimum=3
  MISSING_SUCCESS_CRITERIA: found=0, minimum=1
```

The manual recovery path — asking the Copilot coding agent to generate the spec — succeeded on the first attempt. This demonstrates that the coding agent is a reliable fallback when the direct LLM
pipeline produces structurally invalid output.

Currently, the only recovery path is manual: a human must notice the `speckit:failed` label, read the error details, then manually trigger a Copilot coding agent task with the appropriate context.
This creates unnecessary delay (hours to days depending on when someone notices) and defeats the purpose of an automated spec-driven pipeline.

The desired behavior is that upon detecting a structural validation failure (as distinct from infrastructure, auth, or rate-limit errors), the workflow automatically triggers a Copilot coding agent
task with the full issue context, validation error details, and reference examples, then labels the issue for observability. This eliminates the manual recovery step while preserving the existing
failure handling for non-recoverable errors.

---

## User Scenarios & Testing

### User Story 1 - Automatic Agent Fallback on Structural Validation Failure (Priority: P1)

As a developer who has created a GitHub issue and triggered the SpecKit pipeline, I want the system to automatically invoke the Copilot coding agent when the LLM pipeline fails structural validation,
so that I receive a spec PR without manual intervention and without waiting for someone to notice the failure.

**Covers**: FR-001, FR-002, FR-003, FR-004, FR-009, FR-010

**Why this priority**: This is the core value proposition. Without this, the entire feature has no effect and failures continue to require manual intervention. Every other story builds on this
automatic trigger working correctly.

**Independent Test**: Can be fully tested by simulating a structural validation failure in the SpecKit pipeline (e.g., mock the LLM to return insufficient output) and verifying that a Copilot coding
agent task is created via the API with appropriate problem statement content.

**Acceptance Scenarios**:

1. **Given** the SpecKit LLM pipeline has failed with a structural validation error (e.g., `MISSING_SECTIONS`, `INSUFFICIENT_REQUIREMENTS`) after exhausting retries, **When** the failure handler
   executes in `speckit-issue-trigger.yml`, **Then** a Copilot coding agent task is created via the API with a problem statement containing the original issue title, issue body, phase identifier,
   validation errors, and at least one reference to an existing successful spec (default: `specs/1505-structural-validation-and-retry/spec.md`, overridable via `SPECKIT_REFERENCE_SPEC_PATH` repository
   variable).

2. **Given** the SpecKit LLM pipeline has failed with a structural validation error in `speckit-phase-progression.yml` (Phases 2–5), **When** the failure handler executes, **Then** a Copilot coding
   agent task is created with the same contextual information adapted for the specific phase that failed.

3. **Given** the SpecKit LLM pipeline has failed with an infrastructure error (e.g., authentication failure, rate limit, network timeout), **When** the failure handler executes, **Then** NO agent
   fallback is triggered and the existing failure handling (comment + `speckit:failed` label) proceeds unchanged.

4. **Given** the `SPECKIT_AGENT_FALLBACK` repository variable is set to `false`, **When** any structural validation failure occurs, **Then** NO agent fallback is triggered and the existing failure
   handling proceeds unchanged.

---

### User Story 2 - Observability via Labels and Comments (Priority: P2)

As a repository maintainer monitoring the SpecKit pipeline, I want the issue to be labeled with `speckit:agent-fallback` and a comment posted with the agent task URL, so that I can track which issues
required the fallback path and monitor the agent's progress.

**Covers**: FR-005, FR-006, FR-007, FR-012

**Why this priority**: Observability is essential for understanding pipeline health and debugging issues, but is secondary to the fallback actually working. Without visibility, operators cannot
distinguish between "pipeline succeeded normally" and "pipeline failed but agent recovered."

**Independent Test**: Can be tested by triggering the agent fallback and verifying that the issue receives the `speckit:agent-fallback` label and a comment containing a valid task URL.

**Acceptance Scenarios**:

1. **Given** a structural validation failure has triggered the agent fallback successfully, **When** the agent task is created, **Then** the issue receives a `speckit:agent-fallback` label AND retains
   (or also receives) the `speckit:processing` label to indicate work is still in progress. The `speckit:processing` label MUST remain present for the full duration of the agent's asynchronous run
   and MUST NOT be removed merely because fallback determination is complete or because the agent task was created successfully; agent task creation is a non-terminal state. To make removal
   implementable, the fallback workflow MUST persist the agent task ID/URL and source issue number via a machine-readable marker comment on the issue
   (format: `<!-- speckit:agent-fallback task_id=<id> task_url=<url> issue=<number> phase=<N> -->`), and the system MUST use both of the following follow-up mechanisms: (a) an event-driven workflow
   triggered on `pull_request` creation for the corresponding `speckit/...` branch that treats PR creation as a terminal success outcome and removes `speckit:processing`; and (b) a follow-up polling
   job/workflow that queries the agent task API using the persisted task ID until it reaches a terminal non-PR state (for example `failed`, `cancelled`, or equivalent), at which point it removes
   `speckit:processing`. If the workflow explicitly concludes the fallback with no further asynchronous agent work remaining, that workflow run MUST also remove `speckit:processing`. Until one of
   those explicitly observed terminal outcomes occurs, the label MUST remain present.

2. **Given** a structural validation failure has triggered the agent fallback successfully, **When** the agent task is created, **Then** a comment is posted on the issue containing: the agent task
   URL, a brief explanation that the LLM pipeline failed and the agent was invoked as fallback, and the validation errors that triggered the fallback.

3. **Given** the agent fallback was triggered (and `speckit:failed` may have been applied by a previous failed run), **When** the issue labels are inspected, **Then** `speckit:failed` is removed (if
   it was present) and is NOT present in the final label set, but `speckit:agent-fallback` IS present.

---

### User Story 3 - Idempotent Fallback (No Duplicate Agent Tasks) (Priority: P2)

As the automation system, I must not create duplicate agent tasks if the workflow is re-run or if a fallback is already in progress, so that there are no conflicting PRs or wasted compute resources.

**Covers**: FR-008, FR-013

**Why this priority**: Without idempotency, manual workflow re-runs or race conditions could spawn multiple competing agent tasks generating conflicting PRs for the same spec. This must be addressed
alongside the core trigger to avoid production chaos.

**Independent Test**: Can be tested by simulating a scenario where an agent task PR already exists on the expected branch (e.g., `speckit/{issue_number}/phase-1-specify`) and verifying that no new
agent task is created.

**Acceptance Scenarios**:

1. **Given** an open PR already exists on the expected SpecKit branch (e.g., `speckit/1569/phase-1-specify`), **When** the agent fallback would normally trigger, **Then** the fallback is skipped and a
   comment is posted noting that an existing PR/task was found.

2. **Given** the workflow is manually re-run after the agent fallback already triggered successfully, **When** the failure handler executes again, **Then** no new agent task is created and the
   existing task/PR is referenced in any posted comment.

---

### User Story 4 - Graceful Degradation When Agent API Fails (Priority: P3)

As the automation system, I must handle the case where the Copilot Coding Agent API is unavailable or returns an error, so that the issue still receives proper failure labeling and a useful comment
rather than an unhandled exception.

**Covers**: FR-011

**Why this priority**: API availability cannot be guaranteed. While rare, a failure in the fallback path should not mask the original failure or leave the issue in an inconsistent state.

**Independent Test**: Can be tested by mocking the Copilot Coding Agent API to return a 500/503 error and verifying that the system falls through to the standard failure handling with an additional
note about the fallback failure.

**Acceptance Scenarios**:

1. **Given** a structural validation failure triggers the agent fallback, **When** the Copilot Coding Agent API returns a non-2xx response or the response JSON is missing required fields (`id`,
   `url`), **Then** the issue receives the `speckit:failed` label
   (standard failure path), and the failure comment includes a note that the agent fallback was attempted but failed, with the API error details.

2. **Given** a structural validation failure triggers the agent fallback, **When** the API request times out or a network error occurs, **Then** the same graceful degradation applies —
   `speckit:failed` label and enhanced failure comment.

---

### Edge Cases

- What happens if the LLM produced partial valid output but failed validation? → The agent fallback starts fresh with the original issue context; partial LLM output is not passed to the agent to avoid
  confusing it.
- What if `COPILOT_GITHUB_TOKEN` lacks the required scopes for the Coding Agent API? → Treated as an API failure (graceful degradation — standard failure handling with enhanced comment noting the
  permission issue).
- What if the structural validation error signature changes in future SpecKit versions? → The detection logic should use a well-defined set of error markers that is maintained alongside the validation
  code. Error signatures are defined as constants in the shared fallback action/script, co-located with or importing from `.github/scripts/speckit-trigger/lib/spec-validation.sh`'s error categories.
- What happens if the issue body exceeds 48KB? → The problem statement sent to the agent should be truncated or summarized to stay within API limits while preserving essential context.
  If truncation is used, the final UTF-8 encoded issue-body portion MUST be no more than 49,152 bytes total, including any appended `[truncated]` marker; implementations should therefore reserve
  space for the marker within that byte budget rather than appending it after preserving 48KB of original content.
- What if the Coding Agent API response is missing `id` or `url` fields? → Treated identically to a non-2xx response — graceful degradation to standard failure handling with a comment noting the
  malformed API response.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST detect structural validation failures from machine-readable validation signatures explicitly surfaced by the failing workflow step (for both workflows) before it exits non-zero.
  The upstream step MUST emit signatures via `$GITHUB_OUTPUT` (for example `validation_errors`) or a workspace file (for example `validation-errors.json`) containing known markers
  (`MISSING_SECTIONS`, `INSUFFICIENT_REQUIREMENTS`, `INSUFFICIENT_USER_STORIES`, `MISSING_SUCCESS_CRITERIA`, and any other structural validators defined in the SpecKit pipeline). Detection runs in a
  dedicated workflow step that executes after the main orchestrator step fails (`if: failure()`).

- **FR-002**: System MUST NOT trigger the agent fallback for non-structural failures including but not limited to: authentication errors, rate limiting, network timeouts, missing secrets, and Python
  import/dependency errors. The distinction is made by checking for the presence of known structural error signatures in step output; absence of these signatures means the failure is non-structural.

- **FR-003**: System MUST construct a problem statement for the Copilot coding agent containing: the original issue title, the original issue body, the phase being generated (1–5), the specific
  validation errors encountered, and a reference to at least one existing successful spec as a format example (default: `specs/1505-structural-validation-and-retry/spec.md`, overridable via
  `SPECKIT_REFERENCE_SPEC_PATH` repository variable). For the original issue body portion only, implementations MUST enforce a maximum size of 48KB, defined as 49,152 bytes after UTF-8 encoding;
  this limit does not apply to the rest of the constructed problem statement or the overall Coding Agent API request payload. If truncation is required, implementations MUST truncate only at Unicode
  character boundaries, append the literal marker `[truncated]`, and ensure the final UTF-8 encoded issue-body portion including that marker is at most 49,152 bytes.

- **FR-004**: System MUST call the Copilot Coding Agent API (`POST /repos/{owner}/{repo}/copilot/coding-agent/tasks`) with the constructed problem statement using the `COPILOT_GITHUB_TOKEN` secret.
  The expected response schema is `{ "id": "<task-id>", "url": "<task-url>", "status": "queued" }`.

- **FR-005**: System MUST add the `speckit:agent-fallback` label to the issue when the agent fallback is triggered successfully.

- **FR-006**: System MUST post a comment on the issue containing the agent task URL when the fallback is triggered successfully. The comment MUST include a machine-readable marker in the format
  `<!-- speckit:agent-fallback task_id=<id> task_url=<url> issue=<number> phase=<N> -->` for use by the idempotency guard (FR-013) and follow-up polling job (FR-012).

- **FR-007**: System MUST remove the `speckit:failed` label (if present from a previous failed run) AND MUST NOT add it when the agent fallback is triggered successfully (recovery is in progress).

- **FR-008**: System MUST check for existing open PRs on the expected SpecKit branch before creating a new agent task as one idempotency guard. If an existing open PR is found, the system MUST NOT
  create a new agent task and MUST post a comment on the issue indicating that fallback was skipped due to the existing open PR, including a link to the found PR and, when available, the associated
  existing agent task URL.

- **FR-009**: System MUST be disableable via the `SPECKIT_AGENT_FALLBACK` repository variable — when set to `"false"`, the fallback is skipped entirely and the standard failure handling applies.

- **FR-010**: System MUST work in both `speckit-issue-trigger.yml` (Phase 1) and `speckit-phase-progression.yml` (Phases 2–5) workflows with appropriate phase context in each. The shared fallback
  logic accepts a `phase` input parameter passed by each workflow.

- **FR-011**: System MUST fall through to standard failure handling (comment + `speckit:failed` label) when the Copilot Coding Agent API is unavailable, returns a non-2xx response, or returns a
  response missing required `id`/`url` fields.

- **FR-012**: System MUST keep the `speckit:processing` label for the full
  duration of the fallback flow, including while any Copilot Coding Agent
  task is running asynchronously, and MUST remove it only when a terminal
  outcome is reached — such as a PR being created (detected in GitHub Actions via `on: pull_request` with `types: [opened]`, then
  validated in-step to ensure the PR head branch matches the `speckit/`
  pattern using `github.event.pull_request.head.ref` or `github.head_ref`,
  consistent with the existing headRef validation pattern in
  `.github/workflows/speckit-phase-progression.yml`), the agent task failing
  (detected via scheduled polling job querying the Coding Agent API using
  the task ID from the marker comment), the fallback being explicitly
  concluded without continuing agent execution, or standard failure
  handling being executed because fallback did not start.

- **FR-013**: System MUST also detect whether a fallback agent task is already active or was previously created for the same issue/phase before opening a new task, even when no PR exists yet. This
  detection MUST use the machine-readable marker comment (`<!-- speckit:agent-fallback task_id=... -->`) as the durable correlation mechanism. If an
  existing in-progress or previously created fallback task is found, the system MUST NOT create a duplicate task and MUST post or update an issue comment indicating that fallback was skipped
  because an agent task is already in progress, including the existing agent task URL when available.

### Non-Functional Requirements

- **NFR-001**: The agent fallback step MUST complete within 30 seconds (API call + label/comment operations), not including the agent task execution itself which runs asynchronously.

- **NFR-002**: The failure detection logic MUST be maintainable — validation error signatures should be defined as constants or a well-documented pattern in the shared fallback action/script,
  co-located with or referencing the same categories defined in `.github/scripts/speckit-trigger/lib/spec-validation.sh`. No scattered magic strings.

- **NFR-003**: The fallback MUST NOT introduce new secrets or tokens — it MUST reuse the existing `COPILOT_GITHUB_TOKEN` already available in both workflows.

- **NFR-004**: The problem statement MUST stay within the Copilot Coding Agent API payload size limits (truncating issue body at 48KB with a `[truncated]` marker while preserving the issue title,
  phase, validation errors, and reference spec path in full).

- **NFR-005**: The fallback logic MUST be implemented as a reusable `actions/github-script` block or a shared composite action to avoid code duplication between the two workflows. Target: fewer than
  50 lines of workflow-specific code per workflow file, with all shared logic in the reusable component.

### Key Entities

- **Structural Validation Failure**: A pipeline failure caused by the LLM producing output that does not meet the structural requirements (missing sections, insufficient items). Distinguished from
  infrastructure failures by the presence of specific error signatures (`MISSING_SECTIONS`, `INSUFFICIENT_REQUIREMENTS`, `INSUFFICIENT_USER_STORIES`, `MISSING_SUCCESS_CRITERIA`) in step output. These
  signatures are defined in `.github/scripts/speckit-trigger/lib/spec-validation.sh` and referenced by the fallback detection logic.

- **Agent Task**: An asynchronous Copilot coding agent execution triggered via the REST API (`POST /repos/{owner}/{repo}/copilot/coding-agent/tasks`). Returns a JSON response with `id`, `url`, and
  `status` fields. Creates a PR on the expected SpecKit branch when successful. Identified by a task URL returned from the
  API and persisted in a machine-readable issue comment marker.

- **Problem Statement**: The context document sent to the Copilot coding agent containing issue context, error details, phase information, and example references. Serves as the agent's "prompt" for
  generating the spec. Subject to a 48KB truncation limit on the issue body portion.

- **Machine-Readable Marker Comment**: An HTML comment embedded in a GitHub issue comment with the format `<!-- speckit:agent-fallback task_id=<id> task_url=<url> issue=<number> phase=<N> -->`. Used
  for idempotency detection (FR-013) and follow-up polling (FR-012).

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of recoverable structural validation failures that previously required manual intervention are automatically handed off by the fallback within 1 pipeline run — zero human actions
  needed to create the agent task and apply the expected label/comment state for recoverable failures.

- **SC-002**: 0 duplicate agent tasks are created for the same issue/phase combination across any number of workflow re-runs, verified by the idempotency guard returning a skip result on repeated
  invocations.

- **SC-003**: 100% of agent fallback invocations result in either a successful agent task creation with proper labeling/commenting, or graceful degradation to the standard failure path with enhanced
  error messaging — no invocations leave the issue in an unlabeled or uncommented state.

- **SC-004**: The `speckit:agent-fallback` label is applied within 30 seconds of structural failure detection in 100% of successful fallback triggers, providing real-time observability for operators
  filtering issues by this label.

- **SC-005**: 0% false positive rate for fallback invocation — non-structural failures (auth, infra, rate limits) never trigger the agent fallback, validated by testing at least 5 distinct
  non-structural error patterns.

- **SC-006**: The fallback is operational in both workflows covering all 5 SpecKit phases, with fewer than 50 lines of duplicated code between the two workflow files (shared via reusable action or
  inline function).

---
*Generated by Copilot SDK (claude-opus-4.6)*
