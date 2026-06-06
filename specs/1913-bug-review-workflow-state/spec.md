# Feature Specification: bug: PR review workflow state directory mismatch between auto-execute subprocess and VS Code auto-start task

**Feature Branch**: `speckit/1913/phase-1-specify`  
**Created**: 2026-06-06  
**Status**: Draft  
**Input**: User description: "bug: PR review workflow state directory mismatch between auto-execute subprocess and VS Code auto-start task"  
**Source Issue**: #1913 (<https://github.com/ayaiayorg/agentic-devtools/issues/1913>)

## Problem Statement

During `agdt-initiate-pull-request-review-workflow` with worktree auto-setup, the auto-execute subprocess (`--skip-copilot-session`) writes workflow state to one directory,
while the VS Code auto-start task resolves a different state directory.

As a result, the first Copilot session started by the auto-start task reports no active workflow when it calls `@agdt.advance-workflow`, even though the auto-execute
subprocess wrote workflow state seconds earlier.

## Evidence

### Worktree setup log excerpt

```text
auto-execute command:
  agdt-initiate-pull-request-review-workflow --pull-request-id 28407 --issue-key DFLYP-5279 --skip-copilot-session

prompt written to:
  C:\repos\DFLYP-5279\.agdt\workflows\ama\DFLYP-5279\temp-pull-request-review-initiate-prompt.md
```

### Prompt directory mismatch across invocations

```text
First invocation (auto-execute) wrote prompts to:
pull-request-review/9d874581184b/

Second invocation wrote prompts to:
pull-request-review/bc736c129eff/
```

### State directory mismatch

```text
Auto-execute state path:
C:\repos\dfly-platform-management\.agdt\workflows\ama\DFLYP-5279\

VS Code session resolved state path:
C:\repos\DFLYP-5279\.agdt\workflows\ama\DFLYP-5279\
```

## Root Cause

The auto-execute command inherits `AGENTIC_DEVTOOLS_STATE_DIR` from the source repository process, so it writes workflow state (stored under `_workflow` in `state.json`)
into the source repository state path instead of the target worktree path.

When VS Code starts in the target worktree, state resolution follows the target worktree bootstrap context (for example `runtime-bootstrap.json`) and resolves to the
worktree-local `.agdt` directory instead.

Because these are different physical directories, workflow state written by auto-execute is not visible to the first Copilot session in the worktree.

## User Scenarios & Testing

### User Story 1 - First auto-start session sees active workflow (Priority: P1)

As a developer using pull-request review workflow auto-setup, I need the first VS Code auto-start Copilot session to load the same workflow state that auto-execute
just created.

**Why this priority**: This is the direct bug reported in #1913 and blocks the default review workflow.

**Independent Test**: Start workflow initiation from a source repo with worktree auto-setup enabled, then run `@agdt.advance-workflow` in the first auto-start session.
Verify it succeeds without manual state repair.

**Acceptance Scenarios**:

1. **Given** auto-execute runs from a source repository and writes workflow state, **When** the first Copilot session starts in the target worktree, **Then** the
   session resolves the same state directory and reads the active workflow.
2. **Given** no manual commands are run between auto-execute completion and VS Code auto-start, **When** `@agdt.advance-workflow` is called, **Then** it does not return
   "no active workflow".

---

### User Story 2 - Canonical state path remains stable per workflow run (Priority: P1)

As an automation maintainer, I need both initialization steps to use a single canonical state path so the workflow does not fork into separate prompt/state directories.

**Why this priority**: Divergent directories cause duplicate sessions and downstream workflow inconsistencies.

**Independent Test**: Trigger the same review initiation flow and verify logs from both setup stages reference one canonical state directory and one prompt-root identity
for that run.

**Acceptance Scenarios**:

1. **Given** `agdt-initiate-pull-request-review-workflow` performs multiple internal setup calls, **When** prompt/state paths are recorded, **Then** the paths remain
   consistent across calls for that run.
2. **Given** the source process has `AGENTIC_DEVTOOLS_STATE_DIR` set to a different repo path, **When** the target workflow starts, **Then** state resolution is pinned
   or overridden to the canonical target path for the run.

---

### User Story 3 - Existing single-repo workflows keep working (Priority: P2)

As an existing user, I need workflows that do not involve source→worktree handoff to continue working without behavior changes.

**Why this priority**: The fix must not regress stable workflows while resolving the cross-directory mismatch bug.

**Independent Test**: Run a standard workflow that already uses one repository context and confirm state resolution and workflow progression are unchanged.

**Acceptance Scenarios**:

1. **Given** a workflow where source and target context are the same repository, **When** state resolution runs, **Then** behavior matches current successful flows.
2. **Given** no cross-worktree handoff occurs, **When** `@agdt.advance-workflow` is run, **Then** there is no new warning or failure caused by this fix.

### Edge Cases

- Source process exports `AGENTIC_DEVTOOLS_STATE_DIR` pointing at a stale or unrelated repository.
- Target worktree exists but bootstrap metadata is missing or temporarily unavailable.
- Logs can show similar-looking Windows paths with different repository roots (`dfly-platform-management` vs `DFLYP-5279`); resolution must always treat different roots as
  distinct physical directories.
- On case-insensitive filesystems, path normalization must not collapse truly different roots even when path components differ only by case in surrounding segments.

## Requirements

### Functional Requirements

- **FR-001**: The workflow initiation flow MUST select one canonical state directory for each review run and use it for both auto-execute and VS Code auto-start
  resolution.
- **FR-002**: If `AGENTIC_DEVTOOLS_STATE_DIR` is inherited from a parent source repository process and conflicts with the target worktree context, initialization MUST
  override or clear that inherited value before state writes occur.
- **FR-003**: The target worktree bootstrap/pin mechanism MUST point to the same canonical state directory chosen during initiation before the first auto-start Copilot
  session begins.
- **FR-004**: State written by auto-execute (including active workflow metadata) MUST be readable by the first `@agdt.advance-workflow` call in the target worktree
  session without manual intervention.
- **FR-005**: Setup logging MUST emit the resolved canonical state directory for both initiation stages so mismatches can be detected and debugged quickly.
- **FR-006**: The implementation MUST prevent per-run prompt/state directory divergence caused by mixed source-repo and worktree-local state roots.

### Non-Functional Requirements

- **NFR-001**: The solution MUST preserve backward compatibility for workflows that already resolve to a single repository state directory.
- **NFR-002**: The solution MUST behave deterministically on supported platforms (including Windows path handling) so repeated runs resolve identical state roots for the
  same workflow context.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In the reproduction flow from #1913, the first VS Code auto-start Copilot session can call `@agdt.advance-workflow` without a "no active workflow"
  response.
- **SC-002**: In logs from a workflow run, state path outputs for auto-execute and VS Code auto-start match the same canonical directory.
- **SC-003**: The workflow no longer creates split prompt/state artifacts for the same run due to source-vs-worktree state directory mismatch.

## Related

- #1912 (duplicate sessions — downstream consequence of state mismatch)
