# Feature Specification: initiate-create-jira-issue-workflow picks up existing issue instead of creating new one

> ⚠️ **FALLBACK SKELETON** — This specification was generated via deterministic fallback after all LLM retry attempts were exhausted. It requires manual enrichment. Review each section and replace
> placeholder content with detailed, issue-specific information.

**Source Issue**: #1740 (<https://github.com/ayaiayorg/agentic-devtools/issues/1740>)

## Problem Statement

`agdt-initiate-create-jira-issue-workflow` can incorrectly reuse an issue key from prior
workflow state when `--issue-key` is not provided. Instead of creating a new Jira issue,
the workflow resumes against a stale key (for example, `DFLY-2966` from a previous PR
review run). This causes the command to skip issue creation, fail context validation, and
attempt worktree setup for the wrong issue.

This is problematic because users explicitly invoke this workflow to create a new issue.
State leakage breaks that contract, sends work to the wrong ticket, and forces manual
recovery (`agdt-clear-workflow` + `agdt-clear`) before retrying.

## Steps to Reproduce

1. Run a pull request review workflow on issue DFLY-2966 (e.g., `agdt-initiate-pull-request-review-workflow`)
2. Complete or exit that workflow
3. Shortly after, run: `agdt-initiate-create-jira-issue-workflow --project-key DFLY --issue-type Story --user-request <content>`
4. Observe it returns DFLY-2966 (the issue from the PREVIOUS workflow) instead of creating a new one
5. The command warns: 'Not in the correct context for issue DFLY-2966' and tries to set up a worktree for the stale issue
6. Run `agdt-clear-workflow` and `agdt-clear` to reset state
7. Retry the same command — now it correctly creates DFLY-3006 (new issue)

## Root Cause Hypothesis

`clear_state_for_workflow_initiation()` intentionally preserves context keys including
`jira.issue_key`, while `initiate_create_jira_issue_workflow()` resolves
`resolved_issue_key = issue_key or get_value("jira.issue_key")`. As a result, runs
without `--issue-key` can still inherit a stale key from prior workflows and take the
"existing issue" path instead of always creating a fresh issue.

## Expected Behavior

Starting a new `create-jira-issue` workflow should:

1. Clear or ignore stale issue-selection state (especially `jira.issue_key`) when
   `--issue-key` is not provided, while preserving unrelated context (for example,
   `jira.project_key`) that is intentionally retained.
2. Always call the Jira create API to get a fresh issue number.
3. Never reuse an issue key from a different workflow type.

## Actual Behavior

When the command runs without `--issue-key`, it may return a previously used key from state
instead of creating a new Jira issue. In the reproduced case, it returned `DFLY-2966`
(created in a prior PR review workflow) and then logged a context warning like
"Not in the correct context for issue DFLY-2966". It then attempted worktree/setup flow
for that stale issue, which is incorrect for a create-new-issue invocation.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a developer running `agdt-initiate-create-jira-issue-workflow` without `--issue-key`,
I want the command to ignore stale issue keys from previous workflows and always create a
fresh Jira issue so that each run starts from clean intent and correct context.

**Acceptance Scenarios**:

1. **Given** workflow state contains an old issue key from another workflow type,
   **When** I run `agdt-initiate-create-jira-issue-workflow` without `--issue-key`,
   **Then** the command creates a new Jira issue and does not reuse the stale key.

2. **Given** an old issue key exists in local state and I provide valid create arguments,
   **When** the command executes,
   **Then** the resulting issue key differs from the stale key and maps to a newly created issue.

3. **Given** stale workflow state exists,
   **When** the command starts a create flow,
   **Then** it does not emit context mismatch warnings for the stale key or run setup for that stale issue.

### User Story 2 - Cross-Workflow State Isolation (Priority: P1)

As a developer switching between workflow types (for example PR review then create issue),
I want create-jira-issue initiation to be isolated from stale issue-selection state so that
each workflow uses only the context appropriate for that workflow.

**Acceptance Scenarios**:

1. **Given** a prior workflow stored `jira.issue_key` in state,
   **When** I initiate create-jira-issue without `--issue-key`,
   **Then** the command does not use the prior key and creates a new issue.

2. **Given** preserved context keys such as `jira.project_key`,
   **When** create-jira-issue starts without `--issue-key`,
   **Then** preserved non-issue-selection context can still be used while stale issue key is ignored.

### User Story 3 - Observable Stale-State Handling (Priority: P2)

As a developer diagnosing workflow behavior, I want explicit signals when stale issue state
is ignored so that I can trust the command created a new issue intentionally and avoid manual
state-reset commands.

**Acceptance Scenarios**:

1. **Given** create-jira-issue detects stale `jira.issue_key` while `--issue-key` is absent,
   **When** initiation proceeds,
   **Then** output/logging makes clear that stale issue-selection state was ignored/reset.

2. **Given** stale state was ignored and a new issue was created,
   **When** downstream setup runs,
   **Then** context validation and setup reference only the newly created issue key.

## Requirements

### Functional Requirements

- **FR-001**: When `agdt-initiate-create-jira-issue-workflow` is invoked without an explicit
  `--issue-key`, the system MUST treat the run as a new-issue flow and MUST NOT reuse any
  previously stored issue key from prior workflows.

- **FR-002**: At workflow start, the system MUST clear or ignore stale issue-related state
  that can influence issue selection, including values persisted by other workflow types.

- **FR-003**: For create-new-issue runs, the system MUST call Jira issue creation and return
  the newly created issue key.

- **FR-004**: The system MUST proceed with downstream setup (context validation, worktree,
  branch planning) using only the newly created issue key for that run.

- **FR-005**: If stale issue-related state is detected during create-new-issue flow, the
  system MUST log that stale state was ignored/reset and continue with fresh issue creation
  without requiring manual `agdt-clear-workflow` or `agdt-clear`.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

- **SC-001**: Automated tests cover the stale-state scenario where `jira.issue_key` exists
  from a previous workflow and verify that create-jira-issue without `--issue-key` creates
  a different, newly created issue key.

- **SC-002**: Automated tests verify that create-jira-issue without `--issue-key` does not
  emit context mismatch warnings or trigger setup using a stale issue key.

- **SC-003**: Automated tests verify preserved non-issue-selection context (for example,
  `jira.project_key`) remains usable while stale issue-selection state is ignored.

---
*Generated via fallback skeleton — manual enrichment required*

---
*Generated by Copilot SDK (claude-opus-4.6)*
