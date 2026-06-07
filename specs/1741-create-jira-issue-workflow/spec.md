# Feature Specification: create-jira-issue workflow: no Copilot session started after placeholder creation and worktree setup

**Source Issue**: #1741 (<https://github.com/ayaiayorg/agentic-devtools/issues/1741>)

## Clarifications

### Session 2026-06-07

- Q: Should the placeholder-creation path reuse `perform_auto_setup()` (which handles `runOn: folderOpen` injection and re-invokes the command in the new worktree) or should
  `create_placeholder_and_setup_worktree()` be extended to call `_start_copilot_session_for_create_jira_issue()` directly after worktree setup? → A: The placeholder-creation path should call
  `perform_auto_setup()` with the newly created issue key after placeholder creation succeeds. This reuses the proven auto-setup → `runOn: folderOpen` → Copilot session pipeline and keeps the two
  paths architecturally consistent.
- Q: What should happen if `perform_auto_setup()` itself fails after the placeholder issue was already created successfully (partial failure scenario)? → A: The command should print the created issue
  key, emit an explicit manual continuation command (e.g., `agdt-initiate-create-jira-issue-workflow --issue-key <KEY>`), and exit with code 1. The placeholder issue must NOT be rolled back since it
  already exists in Jira.
- Q: Should the `_format_auto_setup_success_message()` output remain unchanged when continuation actually succeeds, or should it be gated behind confirmation that the `runOn: folderOpen` task was
  injected? → A: The success message must only be printed after `perform_auto_setup()` returns `True`, confirming that the background auto-setup task was successfully started. Injection/execution of
  the `runOn: folderOpen` task is confirmed by background-task completion output (`agdt-task-log` / `agdt-task-wait`). If `perform_auto_setup()` returns `False`, a degraded message with manual
  instructions must be printed instead (satisfying FR-004 and FR-005).
- Q: Should the existing `create_placeholder_and_setup_worktree()` function be deprecated/removed or retained as a lower-level utility that no longer opens VS Code or prints continuation prompts? → A:
  Retain `create_placeholder_and_setup_worktree()` as a lower-level utility that creates the issue and worktree but does NOT open VS Code or print the auto-setup success message. The caller
  (`initiate_create_jira_issue_workflow`) will be responsible for calling `perform_auto_setup()` after receiving the issue key. This preserves the function's reusability for other callers while fixing
  the handoff gap.
- Q: Does the 120-second NFR-001 budget apply to the total wall-clock time from command invocation through Copilot session start confirmation, or only through worktree creation and VS Code launch? →
  A: The 120-second budget applies from command invocation through successful completion of the background setup task launched by `perform_auto_setup()` (including worktree creation, VS Code launch,
  and `runOn: folderOpen` task injection). The actual Copilot session startup in the new VS Code window happens asynchronously and is not included in this budget.

## Problem Statement

When `agdt-initiate-create-jira-issue-workflow` is run without `--issue-key`,
the command successfully creates a placeholder Jira issue and opens the new
worktree in VS Code, but the workflow does not continue automatically.

The terminal reports that "A Copilot session will start automatically in the VS
Code integrated terminal.", yet no Copilot session starts and no
`runOn: folderOpen` task displays the next workflow guidance. Users are left in
a blank editor window and must manually find and run a continuation command.
This breaks the expected end-to-end handoff and creates inconsistent behavior
compared to issue-key flows that do continue automatically.

**Root Cause**: The no-issue-key path calls `create_placeholder_and_setup_worktree()` which creates the worktree and opens VS Code directly, but does NOT call `perform_auto_setup()` (which handles
`runOn: folderOpen` task injection and Copilot session startup). The issue-key path correctly uses `perform_auto_setup()` for continuation. The fix is to align the no-issue-key path to call
`perform_auto_setup()` with the newly created issue key after placeholder creation succeeds.

## Steps to Reproduce

1. From the main repo (not in a worktree), run:

   ```text
   agdt-initiate-create-jira-issue-workflow --project-key DFLY --issue-type Story --user-request "I need a story to cover..."
   ```

2. The command creates a placeholder issue (e.g., DFLY-3006) and sets up a worktree at `C:\repos\DFLY-3006`
3. VS Code opens with the worktree workspace
4. Observe: **no Copilot session is started** — the user is left at a blank VS Code window with no workflow guidance

## Expected Behavior

After the worktree is created and VS Code is opened, a Copilot session should start automatically (or a VS Code `runOn: folderOpen` task should fire) that hands off to `@agdt.get-next-workflow-prompt`
to display the create-jira-issue workflow instructions. This is what the success message promises: "A Copilot session will start automatically in the VS Code integrated terminal."

The continuation should behave identically to running this manually inside the worktree:

```text
agdt-initiate-update-jira-issue-workflow --issue-key DFLY-3006 --user-request "<original user request>"
```

Or equivalently:

```text
agdt-initiate-create-jira-issue-workflow --issue-key DFLY-3006 --user-request "<original user request>"
```

## Actual Behavior

- The placeholder Jira issue is created successfully.
- The worktree is created successfully.
- VS Code opens on the new worktree.
- **No Copilot session starts and no `folderOpen` continuation task runs.**
- The success message claims automatic continuation, but the user must manually copy and run the continuation command from prior terminal output.

**Technical Detail**: `create_placeholder_and_setup_worktree()` calls `setup_worktree_environment(open_vscode=True)` and `get_worktree_continuation_prompt()` but never invokes `perform_auto_setup()`,
which accepts a caller-constructed `auto_execute_command` (built by the workflow command to re-invoke itself with `--issue-key`) and passes it to the background setup task; that background task executes
`auto_execute_command` in the worktree before VS Code opens, then injects `.vscode/tasks.json` with `"runOn": "folderOpen"` to run `agdt-copilot-auto-start` when VS Code opens the worktree.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a developer creating a new Jira issue from the main repo (no `--issue-key`),
I want the workflow to continue automatically after VS Code opens the new
worktree so I can immediately see and execute the next guided step without
manual command copy/paste.

**Acceptance Scenarios**:

1. **Given** `agdt-initiate-create-jira-issue-workflow` is run without
   `--issue-key`, **When** placeholder creation and worktree setup complete,
   **Then** opening the worktree triggers automatic continuation in that
   window (Copilot session and/or `runOn: folderOpen` task).
2. **Given** the new worktree window is opened, **When** continuation runs,
   **Then** the user is shown guidance sourced from
   `@agdt.get-next-workflow-prompt` without requiring manual terminal input.

### User Story 2 - Error Recovery (Priority: P1)

As a developer who sees the workflow success message, I want the message to match actual behavior so I can trust that continuation has started in the newly opened worktree.

**Acceptance Scenarios**:

1. **Given** the workflow reports successful setup, **When** the worktree
   opens, **Then** either the Copilot session starts or an equivalent
   folder-open continuation is visibly executed in that window.
2. **Given** automatic continuation cannot be started (e.g., `perform_auto_setup()` returns `False`), **When** the workflow
   completes, **Then** the user receives an explicit failure/next-step message
   containing the manual continuation command (e.g., `agdt-initiate-create-jira-issue-workflow --issue-key <KEY> --user-request "..."`)
   instead of a misleading "Copilot session will start automatically" success
   statement.

### User Story 3 - Graceful Degradation (Priority: P2)

As a developer using either the existing-issue path (`--issue-key`) or
placeholder-creation path (no `--issue-key`), I want both paths to provide the
same automatic continuation experience after worktree open.

**Acceptance Scenarios**:

1. **Given** I run with `--issue-key`, **When** the worktree opens, **Then**
   continuation guidance appears automatically in the new window.
2. **Given** I run without `--issue-key` and a placeholder is created,
   **When** the worktree opens, **Then** continuation guidance appears
   automatically in the same way as the `--issue-key` path (via `perform_auto_setup()` → `runOn: folderOpen` → Copilot session).

## Requirements

### Functional Requirements

- **FR-001**: When `agdt-initiate-create-jira-issue-workflow` is run without
  `--issue-key`, the workflow MUST call `perform_auto_setup()` with the newly created placeholder issue key after `create_placeholder_and_setup_worktree()` returns the issue key. This invokes the same
  auto-setup continuation mechanism (worktree creation, `.vscode/tasks.json` injection with `runOn: folderOpen`, auto-execute command construction) used by the issue-key path.

- **FR-002**: The continuation sequence MUST preserve current auto-setup contracts: any workflow re-invocation for context hydration runs via `auto_execute_command` before VS Code opens, and after
  VS Code opens the new worktree, continuation starts in that window via the injected `runOn: folderOpen` task that starts the Copilot workflow session (with
  `_start_copilot_session_for_workflow` fallback behavior), matching the existing issue-key path behavior.

- **FR-003**: Automatic continuation MUST display the next workflow guidance by invoking `@agdt.get-next-workflow-prompt` in the newly opened worktree context, without requiring manual command entry.

- **FR-004**: Success output MUST be truthful: `_format_auto_setup_success_message()` MUST only be printed when `perform_auto_setup()` returns `True`, confirming that the background auto-setup task
  started successfully (not that `runOn: folderOpen` injection has already completed).

- **FR-005**: If `perform_auto_setup()` returns `False` after the placeholder issue was created successfully, the workflow MUST emit an explicit actionable degraded message containing: (a) the created
  issue key, (b) the exact manual continuation command to run from the current terminal (re-attempting auto-setup and continuation, e.g.,
  `agdt-initiate-create-jira-issue-workflow --issue-key DFLY-3006 --user-request "..."`), and (c) exit with code 1.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all setup operations (from command invocation through background setup task completion, including placeholder creation, worktree setup, VS Code launch,
  and `runOn: folderOpen` task injection) within 120 seconds under normal conditions. The actual Copilot session startup in the new VS Code window is asynchronous and excluded from this budget.

- **NFR-002**: The implementation must maintain backward compatibility for existing CLI/workflow interfaces and contracts while intentionally changing helper internals. Specifically:
  (a) `create_placeholder_and_setup_worktree()` remains available as a lower-level utility and never opens VS Code or prints the auto-setup success message, (b) the `--issue-key` path behavior is
  unchanged, (c) all existing CLI parameters continue to work.

## Success Criteria

- **SC-001**: In placeholder-creation runs (no `--issue-key`), 100% of
  successful setups open the worktree and automatically display next-step
  workflow guidance in that new VS Code window without manual copy/paste.

- **SC-002**: The user-visible success message for create-jira-issue setup has zero observed mismatches between "automatic continuation started" claims and actual continuation behavior.

- **SC-003**: Placeholder-creation and issue-key paths produce equivalent continuation UX: both paths automatically surface `@agdt.get-next-workflow-prompt` guidance after the worktree window opens
  via the same `perform_auto_setup()` → `runOn: folderOpen` → Copilot session pipeline.

---
*Generated by Copilot SDK (claude-opus-4.6)*
