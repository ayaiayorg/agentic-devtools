# Feature Specification: create-jira-issue workflow: no Copilot session started after placeholder creation and worktree setup

**Source Issue**: #1741 (<https://github.com/ayaiayorg/agentic-devtools/issues/1741>)

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
2. **Given** automatic continuation cannot be started, **When** the workflow
   completes, **Then** the user receives an explicit failure/next-step message
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
   automatically in the same way as the `--issue-key` path.

## Requirements

### Functional Requirements

- **FR-001**: When `agdt-initiate-create-jira-issue-workflow` is run without
  `--issue-key`, the workflow MUST invoke the same auto-setup continuation
  mechanism used by the issue-key path after placeholder issue creation and
  worktree setup.

- **FR-002**: After VS Code opens the new worktree, the workflow MUST
  automatically start continuation in that window by starting a Copilot session
  and/or triggering an equivalent `runOn: folderOpen` task.

- **FR-003**: Automatic continuation MUST display the next workflow guidance by invoking `@agdt.get-next-workflow-prompt` in the newly opened worktree context, without requiring manual command entry.

- **FR-004**: Success output MUST be truthful: it MUST only claim automatic Copilot/session continuation when that continuation has actually been initiated.

- **FR-005**: If automatic continuation cannot be initiated, the workflow MUST emit an explicit actionable failure/degraded message describing the exact manual continuation command to run in the new worktree.

### Non-Functional Requirements

- **NFR-001**: The implementation must complete all operations within 120 seconds under normal conditions.

- **NFR-002**: The implementation must maintain backward compatibility with existing interfaces and contracts.

## Success Criteria

- **SC-001**: In placeholder-creation runs (no `--issue-key`), 100% of
  successful setups open the worktree and automatically display next-step
  workflow guidance in that new VS Code window without manual copy/paste.

- **SC-002**: The user-visible success message for create-jira-issue setup has zero observed mismatches between "automatic continuation started" claims and actual continuation behavior.

- **SC-003**: Placeholder-creation and issue-key paths produce equivalent continuation UX: both paths automatically surface `@agdt.get-next-workflow-prompt` guidance after the worktree window opens.
