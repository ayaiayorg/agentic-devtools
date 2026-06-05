# Feature Specification: Prevent @agdt.advance-workflow from Re-initiating Workflows

**Feature Branch**: `1914-advance-workflow-no-reinitiate`  
**Created**: 2026-06-05  
**Status**: Draft  
**Input**: User description: "bug: @agdt.advance-workflow agent should not re-initiate workflow when no active workflow found"  
**Source Issue**: #1914 (<https://github.com/ayaiayorg/agentic-devtools/issues/1914>)

## Problem Statement

The `@agdt.advance-workflow` Copilot Chat agent currently exhibits dangerous fallback behavior when it cannot locate an active workflow state. Instead of reporting the failure and exiting cleanly, the
agent autonomously decides to re-initiate the entire workflow by invoking `@agdt.pull-request-review.initiate`. This creates a cascade of unintended side effects that undermine the reliability and
cost-efficiency of the automated review system.

The root cause is a missing guardrail in the agent prompt. The current prompt states that "an active workflow must already be running" as a prerequisite, but it provides no explicit instruction about
what the agent should do when this prerequisite is not met. Large language models, when faced with an unmet prerequisite and no explicit failure instruction, tend to "be helpful" by attempting to
satisfy the prerequisite themselves — in this case, by spawning a new workflow. This is a well-known failure mode in agentic systems where the absence of a prohibition is interpreted as implicit
permission.

The impact of this bug is significant and has already been observed in production. When the advance-workflow agent re-initiates the pull-request-review workflow, it spawns a second
`setup_pull_request_review_async` background task, which starts a second Copilot session. This results in duplicate review comments posted to the same pull request (as observed on PR #28407), wasted
AI credits from running two full reviews instead of one, and confused workflow state where two independent sessions attempt to manage the same review artifacts. The problem is particularly insidious
because it occurs silently — the first session continues running unaware that a duplicate has been spawned, and the user only discovers the issue after seeing double-posted comments or unexpected
state corruption. The related issue #1913 (state directory mismatch) is the most common trigger: the workflow state was written to a different directory than the one the advance-workflow agent checks,
making it appear as though no workflow exists even though one is actively running.

## User Scenarios & Testing

### User Story 1 - Safe Failure on Missing Workflow State (Priority: P1)

As an AI agent operator, when the `@agdt.advance-workflow` agent is invoked but no active workflow state exists in the current state directory, the agent must fail safely with a clear error message
rather than attempting to re-initiate any workflow. This is the core safety behavior that prevents the duplicate session problem.

**Why this priority**: This is the fundamental safety guardrail. Without it, every invocation of advance-workflow in a misaligned state directory risks spawning duplicate workflows, wasting credits,
and corrupting review state. This scenario was directly observed in production and caused the duplicate review comments on PR #28407.

**Independent Test**: Can be tested by invoking `@agdt.advance-workflow` in a workspace where no `state.json` exists or where the workflow state is empty. The test passes if the agent produces an
error message and does NOT invoke any initiate command.

**Acceptance Scenarios**:

1. **Given** the current state directory contains no `state.json` file, **When** the user invokes `@agdt.advance-workflow`, **Then** the agent outputs an error message stating "No active workflow
   found" and does not invoke any other agent or initiate command.
2. **Given** the current state directory contains a `state.json` with no `_workflow` key, **When** the user invokes `@agdt.advance-workflow overview`, **Then** the agent outputs an error message
   indicating no active workflow exists and suggests running `agdt-get-workflow` to verify state.
3. **Given** the current state directory contains a `state.json` with `_workflow.status` set to `"completed"`, **When** the user invokes `@agdt.advance-workflow`, **Then** the agent reports that the
   workflow has already completed and does not attempt to re-initiate or advance.

---

### User Story 2 - Diagnostic Guidance on Failure (Priority: P2)

As an AI agent operator troubleshooting a workflow state mismatch, when advance-workflow fails to find an active workflow, the agent must provide actionable diagnostic guidance so that the operator
can identify whether the issue is a state directory mismatch, a timing problem with a concurrent background task, or a genuinely missing workflow.

**Why this priority**: Clear diagnostics reduce mean-time-to-resolution when the state directory mismatch issue from #1913 occurs. Without guidance, operators resort to trial-and-error or re-running
the entire workflow from scratch, wasting additional time and credits.

**Independent Test**: Can be tested by invoking `@agdt.advance-workflow` with no active workflow and verifying that the output contains specific CLI commands the operator can run to diagnose the
problem.

**Acceptance Scenarios**:

1. **Given** no active workflow is found in the current state directory, **When** the agent reports the failure, **Then** the error message includes the suggestion to run `agdt-get-workflow` to check
   workflow state and `agdt-show` to inspect the current state directory path.
2. **Given** no active workflow is found, **When** the agent reports the failure, **Then** the error message mentions the possibility of a state directory mismatch and references that the workflow may
   have been written to a different worktree's state directory.
3. **Given** the user provides a step name argument (e.g., `@agdt.advance-workflow overview`), **When** no workflow is active, **Then** the error message still includes the requested step name in
   context so the operator knows which advancement was attempted.

---

### User Story 3 - Optional Single Retry for Race Conditions (Priority: P3)

As an AI agent operator in a multi-task environment, when advance-workflow is invoked immediately after a workflow initiation background task has been spawned but before it has written its state, the
agent should optionally retry once after a brief delay to accommodate the race condition where state is in-flight.

**Why this priority**: This addresses a narrow but real race condition in the auto-start flow where VS Code's auto-start task invokes advance-workflow before the initiate task has finished writing
state. While less critical than the safety guardrail (P1), it reduces false-negative failures in a common automated scenario.

**Independent Test**: Can be tested by simulating a delay between workflow initiation and advance-workflow invocation. The test passes if the agent waits briefly and retries once before reporting
failure — without ever falling back to re-initiation.

**Acceptance Scenarios**:

1. **Given** no active workflow is found on the first check, **When** the agent performs a single retry after a brief wait (approximately 3-5 seconds), **Then** if the workflow state appears on retry,
   the agent proceeds with the advancement normally.
2. **Given** no active workflow is found on either the first check or the retry, **When** the retry also fails, **Then** the agent reports the failure with full diagnostics (as per User Story 2) and
   does NOT attempt a third retry or any re-initiation.
3. **Given** the agent is configured to retry, **When** it performs the retry, **Then** the retry is logged to the console so the operator can observe that a timing accommodation was attempted.

---

### Edge Cases

What happens when advance-workflow is invoked while a workflow initiation background task is actively running but has not yet written state? The agent should treat this identically to "no active
workflow found" and apply the retry-then-fail behavior without re-initiating.

How does the system handle a corrupted `state.json` where the `_workflow` key exists but contains invalid or incomplete data (e.g., missing `name` or `step` fields)? The agent should report a
corrupted workflow state error with a suggestion to run `agdt-clear-workflow` and re-initiate manually.

What happens if the user explicitly requests advancement to a step that does not exist in the current workflow's step list? The agent should report an invalid step name error, list the valid steps for
the active workflow, and not modify the workflow state.

## Requirements

### Functional Requirements

- **FR-001**: The `@agdt.advance-workflow` agent prompt MUST contain an explicit prohibition against invoking any workflow initiation command (including but not limited to
  `@agdt.pull-request-review.initiate`, `agdt-initiate-pull-request-review-workflow`, `agdt-initiate-work-on-jira-issue-workflow`, or any other initiate agent/command) when no active workflow is
  found.

- **FR-002**: The agent MUST output a clear, structured error message when no active workflow state is detected, containing at minimum: (a) the phrase "No active workflow found", (b) the state
  directory path that was checked, and (c) a statement that no re-initiation will be attempted.

- **FR-003**: The agent MUST include diagnostic guidance in its failure output, specifically suggesting the commands `agdt-get-workflow` and `agdt-show` as immediate troubleshooting steps the operator
  can run.

- **FR-004**: The agent MUST NOT modify any workflow state, spawn any background tasks, or invoke any other agents when the prerequisite of an active workflow is not met — the only permitted action is
  producing console output describing the failure.

- **FR-005**: The agent MUST recognize a workflow with `status` equal to `"completed"` as an inactive workflow and treat it identically to a missing workflow for the purposes of the prohibition (i.e.,
  do not attempt to re-initiate a completed workflow).

- **FR-006**: The agent prompt MUST include the retry behavior specification: when no workflow is found on the first `agdt-get-workflow` check, the agent MAY wait 3-5 seconds and check once more
  before reporting failure, but MUST NOT retry more than once and MUST NOT fall back to re-initiation regardless of retry outcome.

- **FR-007**: The agent MUST preserve any user-provided step name argument in the error output context, so that when the operator resolves the underlying issue and re-invokes the command, they know
  which step was originally requested.

### Non-Functional Requirements

- **NFR-001**: The agent's failure path (from invocation to error output) MUST complete within 10 seconds when no retry is performed, or within 15 seconds when the single retry is performed, to avoid
  blocking the operator unnecessarily.

- **NFR-002**: The error message format MUST be consistent with other agdt agent error messages — using plain text output to the console without markdown formatting that would be invisible in a
  terminal context.

- **NFR-003**: The fix MUST be implemented entirely within the agent prompt file (`.github/agents/agdt.advance-workflow.agent.md`) without requiring changes to the underlying `agdt-advance-workflow`
  CLI command implementation, ensuring backward compatibility with direct CLI usage.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After the fix is deployed, zero instances of `@agdt.advance-workflow` invoking any workflow initiation command occur over a 30-day observation period across all repositories using the
  agent, as measured by searching Copilot session logs for initiation command invocations originating from advance-workflow contexts.

- **SC-002**: The agent produces a diagnostic error message containing both `agdt-get-workflow` and `agdt-show` command suggestions in 100% of cases where no active workflow is found, as verified by
  automated prompt testing against the updated agent file.

- **SC-003**: The time from advance-workflow invocation to error output is less than 15 seconds in 95% of failure cases (accounting for the optional retry delay), as measured by timestamp analysis of
  agent session logs.

- **SC-004**: Zero duplicate Copilot review sessions are spawned as a result of advance-workflow's failure handling over a 30-day observation period, reducing the duplicate session count from the
  current observed rate (at least 1 incident per week) to zero.

---
*Generated by Copilot SDK (claude-opus-4.6)*
