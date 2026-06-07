# Feature Specification: initiate-create-jira-issue-workflow picks up existing issue instead of creating new one

**Source Issue**: #1740 (<https://github.com/ayaiayorg/agentic-devtools/issues/1740>)

## Clarifications

### Session 2026-06-07

- Q: Should `clear_state_for_workflow_initiation()` be modified globally to clear `jira.issue_key`, or should the fix be scoped only to the create-jira-issue workflow? → A: The fix should be scoped to
  the create-jira-issue workflow entry point only. Modifying `clear_state_for_workflow_initiation()` globally could break other workflows (e.g., work-on-jira-issue) that legitimately depend on
  preserving `jira.issue_key` across workflow boundaries. The create-jira-issue command should explicitly clear or ignore `jira.issue_key` when `--issue-key` is not provided.

- Q: When `--issue-key` IS explicitly provided to `agdt-initiate-create-jira-issue-workflow`, should the command still create a new issue or should it resume/attach to the provided key? → A: When
  `--issue-key` is explicitly provided, the command should attach to that existing issue (current behavior preserved). The fix only applies to the no-`--issue-key` path where the fallback to
  `get_value("jira.issue_key")` causes unintentional reuse.

- Q: Should the stale `jira.issue_key` be deleted from state during the create flow, or merely ignored (not read) during resolution? → A: The stale `jira.issue_key` should be explicitly deleted from
  state at the start of the create-jira-issue workflow when `--issue-key` is not provided. This prevents downstream code paths (pre-flight checks, worktree setup) from accidentally reading the stale
  value. Deletion is safer than ignore-only because multiple code paths read `jira.issue_key` from state.

- Q: What logging level and format should be used when stale state is detected and cleared? → A: Emit an informational console message to stderr using
  `print(..., file=sys.stderr)` with a message like:
  `"ℹ️  Cleared stale issue selection state (issue_key/jira.issue_key) from prior workflow — creating fresh issue."` Keep the existing emoji-prefixed
  status-message pattern.

- Q: Should `issue_key` (top-level provider-agnostic key) also be cleared alongside `jira.issue_key` when the create flow detects stale state? → A: Yes. Both `issue_key` and `jira.issue_key` must be
  cleared when the create-jira-issue workflow starts without `--issue-key`. Per the state management documentation, both keys participate in issue resolution priority, and leaving either one could
  cause downstream leakage via `_get_issue_key_from_state()` or `resolve_worktree_key()`.

## Problem Statement

`agdt-initiate-create-jira-issue-workflow` can incorrectly reuse an issue key from prior
workflow state when `--issue-key` is not provided. Instead of creating a new Jira issue,
the workflow resumes against a stale key (for example, `DFLY-2966` from a previous PR
review run). This causes the command to skip issue creation, fail context validation, and
attempt worktree setup for the wrong issue.

This is problematic because users explicitly invoke this workflow to create a new issue.
State leakage breaks that contract, sends work to the wrong ticket, and forces manual
recovery (`agdt-clear-workflow` + `agdt-clear`) before retrying.

**Root cause location**: In `agentic_devtools/cli/workflows/commands.py` at line 1438,
`resolved_issue_key = issue_key or get_value("jira.issue_key")` falls back to state when
`issue_key` is `None`. The upstream `clear_state_for_workflow_initiation()` in
`agentic_devtools/cli/workflows/base.py` intentionally preserves `jira.issue_key` (lines
35–37), so the stale value persists.

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

The fix must be applied in the create-jira-issue workflow entry point (not in
`clear_state_for_workflow_initiation()` which is shared by all workflows). Specifically,
after `_ensure_scoped_bootstrap_and_clear(issue_key)` returns at line 1415, the command
should delete `jira.issue_key` and `issue_key` from state when `issue_key` (the CLI
parameter) is `None`/falsy.

## Expected Behavior

Starting a new `create-jira-issue` workflow should:

1. Clear or ignore stale issue-selection state (especially `jira.issue_key` and `issue_key`)
   when `--issue-key` is not provided, while preserving unrelated context (for example,
   `jira.project_key`) that is intentionally retained.
2. Always call the Jira create API to get a fresh issue number.
3. Never reuse an issue key from a different workflow type.
4. Emit a diagnostic message to stderr when stale issue-selection state is detected and
   cleared, so the user has visibility into the automatic cleanup.

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

1. **Given** create-jira-issue detects stale issue-selection state (`issue_key` and/or
   `jira.issue_key`) while `--issue-key` is absent,
   **When** initiation proceeds,
   **Then** output to stderr includes a message indicating stale issue-selection state was
   cleared (e.g., `"ℹ️  Cleared stale issue selection state (issue_key/jira.issue_key) from
   prior workflow — creating fresh issue."`).

2. **Given** stale state was ignored and a new issue was created,
   **When** downstream setup runs,
   **Then** context validation and setup reference only the newly created issue key.

### User Story 4 - Explicit --issue-key Preserves Existing Behavior (Priority: P1)

As a developer providing `--issue-key` explicitly to `agdt-initiate-create-jira-issue-workflow`,
I want the command to attach to the specified issue (existing behavior) so that intentional
reuse is not broken by the stale-state fix.

**Acceptance Scenarios**:

1. **Given** `--issue-key DFLY-2966` is explicitly passed on the command line,
   **When** the command runs,
   **Then** it uses `DFLY-2966` as the resolved issue key (no clearing, no new creation).

2. **Given** both `--issue-key` and a stale `jira.issue_key` exist in state,
   **When** the command runs,
   **Then** the explicit CLI value takes precedence and no stale-state warning is emitted.

## Requirements

### Functional Requirements

- **FR-001**: When `agdt-initiate-create-jira-issue-workflow` is invoked without an explicit
  `--issue-key`, the system MUST treat the run as a new-issue flow and MUST NOT reuse any
  previously stored issue key from prior workflows.

- **FR-002**: At workflow start (after `_ensure_scoped_bootstrap_and_clear` and before issue
  resolution), the system MUST delete both `jira.issue_key` and `issue_key` from state when
  `--issue-key` is not provided, preventing downstream fallback reads from picking up stale
  values.

- **FR-003**: For create-new-issue runs, the system MUST call Jira issue creation and return
  the newly created issue key.

- **FR-004**: The system MUST proceed with downstream setup (context validation, worktree,
  branch planning) using only the newly created issue key for that run.

- **FR-005**: If stale issue-related state is detected during create-new-issue flow, the
  system MUST log to stderr which issue-selection key(s) were cleared (for `issue_key`,
  `jira.issue_key`, or both), with a message format such as:
  `"ℹ️  Cleared stale issue selection state (issue_key/jira.issue_key) from prior workflow — creating fresh issue."`
  and continue with fresh issue creation without requiring manual `agdt-clear-workflow` or
  `agdt-clear`.

- **FR-006**: When `--issue-key` IS explicitly provided, the system MUST preserve current
  behavior: use the provided key as the resolved issue key without clearing state or
  creating a new issue.

- **FR-007**: The fix MUST NOT modify `clear_state_for_workflow_initiation()` in
  `agentic_devtools/cli/workflows/base.py`. The change must be scoped to the
  create-jira-issue workflow entry point only, to avoid breaking other workflows that depend
  on preserved `jira.issue_key`.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under
  normal network conditions (Jira API latency ≤ 5s).

- **NFR-002**: The implementation must maintain backward compatibility with existing
  interfaces and contracts — no changes to CLI argument signatures, no changes to the
  behavior of other workflow initiation commands.

## Success Criteria

- **SC-001**: Automated tests cover the stale-state scenario where `jira.issue_key` exists
  from a previous workflow and verify that create-jira-issue without `--issue-key` creates
  a different, newly created issue key.

- **SC-002**: Automated tests verify that create-jira-issue without `--issue-key` does not
  emit context mismatch warnings or trigger setup using a stale issue key.

- **SC-003**: Automated tests verify preserved non-issue-selection context (for example,
  `jira.project_key`) remains usable while stale issue-selection state is ignored.

- **SC-004**: Automated tests verify that explicit `--issue-key` still works correctly
  (attaches to specified key, no stale-state warning, no deletion).

- **SC-005**: Automated tests verify both `jira.issue_key` and `issue_key` (top-level) are
  cleared when stale state is detected in the no-`--issue-key` path.

- **SC-006**: All tests follow the 1:1:1 test structure under
  `tests/unit/cli/workflows/commands/` with appropriate symbol naming.

---
*Generated by Copilot SDK (claude-opus-4.6)*
