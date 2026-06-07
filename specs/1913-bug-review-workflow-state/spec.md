# Feature Specification: bug: PR review workflow state directory mismatch between auto-execute subprocess and VS Code auto-start task

**Feature Branch**: `speckit/1913/phase-2-clarify`  
**Created**: 2026-06-06  
**Status**: Draft  
**Input**: User description: "bug: PR review workflow state directory mismatch between auto-execute subprocess and VS Code auto-start task"  
**Source Issue**: #1913 (<https://github.com/ayaiayorg/agentic-devtools/issues/1913>)

## Clarifications

### Session 2026-06-06

- Q: Should the fix leverage the existing `pinned-state-dir.json` mechanism (introduced by #1180) to ensure the auto-start task resolves the same state directory as auto-execute, or should a new
  mechanism be introduced? → A: The fix should leverage and extend the existing `pinned-state-dir.json` mechanism. The auto-start task already resolves state via `get_state_file_path()`, which
  delegates to `get_state_dir()` and can read a valid pin in the target worktree context. The gap is ensuring the correct pin file exists in the target worktree `.agdt/` directory before
  `agdt-copilot-auto-start` runs, and preserving well-defined fallback behavior when the pin is missing, expired, or invalid.
- Q: Does this fix apply only to the `pull-request-review` workflow, or should it also cover other cross-worktree workflows (e.g., `work-on-jira-issue`, `apply-pr-suggestions`)? → A: The fix should
  apply to all workflows that use worktree auto-setup with auto-execute (`_run_auto_execute_command`). The codebase currently builds `auto_execute_command` for several workflows, including
  `pull-request-review`, `apply-pr-suggestions`, `work-on-jira-issue`, create/update Jira issue flows, and issue-breakdown flows. The reported P1 reproduction is `pull-request-review`, but
  planning should treat the state-resolution contract as cross-workflow and extend `RECOGNIZED_PIN_WORKFLOWS` (or equivalent coverage) where needed.
- Q: What timing guarantees exist between auto-execute completion and the VS Code auto-start task firing? Is there a risk the auto-start task reads state before auto-execute finishes writing? → A: The
  auto-execute subprocess runs synchronously within `_setup_worktree_from_state` and must complete (or timeout) before VS Code opens the worktree and the `runOn:folderOpen` task fires. There is no
  race between auto-execute writing and auto-start reading — the issue is purely about directory resolution, not timing. The pin file write is atomic (`os.replace`), so even if there were a race, the
  auto-start task would either see the pin or not (never a partial write).
- Q: Should the pin file be cleaned up (deleted) after the workflow completes, or left to expire via TTL? → A: Preserve the existing cleanup contract. On normal workflow completion, the pin file
  should still be explicitly deleted when the completing workflow matches, and `agdt-clear-workflow` should continue to delete it unconditionally.
  TTL (default 24 hours) remains a safety net for stale or crashed sessions, and `read_and_validate_pin_file` should continue ignoring expired pins.
- Q: In the auto-start task (`copilot_auto_start_cmd`), should state resolution change from using `get_state_file_path()` after clearing `AGENTIC_DEVTOOLS_STATE_DIR` and `chdir`ing into
  `--worktree-path` to using `get_state_dir()`
  (which consults the pin file), or should a pin-file read be added as an additional resolution step? → A: Keep the current `get_state_file_path()` → `get_state_dir()` resolution path. It already
  consults a valid pin file and falls back to bootstrap/unscoped resolution when no valid pin exists. The fix should focus on writing the pin in the target worktree context before auto-start runs.

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

The reproduction evidence shows that auto-execute and the first VS Code auto-start session resolved different physical state roots. `_run_auto_execute_command` is the point where a canonical
state directory is chosen for the nested run via `AGENTIC_DEVTOOLS_STATE_DIR`, but that choice is process-local unless it is also made discoverable from the target worktree itself.

When VS Code later opens the target worktree and fires the `agdt-copilot-auto-start` task in a fresh terminal, `copilot_auto_start_cmd` explicitly clears
`AGENTIC_DEVTOOLS_STATE_DIR` (and the legacy `AGDT_AI_HELPERS_STATE_DIR`) before `get_state_file_path()` / `get_state_dir()` resolve the state directory from
the target-worktree context alone — consulting `pinned-state-dir.json` first, then
`runtime-bootstrap.json`, then falling back to `_unscoped`.

The gap is that the canonical directory used by auto-execute is not guaranteed to be discoverable from the target worktree at that point. If no valid
`pinned-state-dir.json` exists in the target worktree's `.agdt/` directory, the auto-start task may resolve a different physical directory than the one the subprocess used, making the active
workflow state invisible to the first Copilot session.

## User Scenarios & Testing

### User Story 1 - First auto-start session sees active workflow (Priority: P1)

As a developer using pull-request review workflow auto-setup, I need the first VS Code auto-start Copilot session to load the same workflow state that auto-execute
just created.

**Why this priority**: This is the direct bug reported in #1913 and blocks the default review workflow.

**Independent Test**: Start workflow initiation from a source repo with worktree auto-setup enabled, then run `@agdt.advance-workflow` in the first auto-start session.
Verify it succeeds without manual state repair.

**Related Functional Requirements**: FR-001, FR-003, FR-004, FR-008.

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

**Related Functional Requirements**: FR-001, FR-002, FR-005, FR-006.

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

**Related Functional Requirements**: FR-007.

**Acceptance Scenarios**:

1. **Given** a workflow where source and target context are the same repository, **When** state resolution runs, **Then** behavior matches current successful flows.
2. **Given** no cross-worktree handoff occurs, **When** `@agdt.advance-workflow` is run, **Then** there is no new warning or failure caused by this fix.

### Edge Cases

- Source process exports `AGENTIC_DEVTOOLS_STATE_DIR` pointing at a stale or unrelated repository.
- Target worktree exists but bootstrap metadata is missing or temporarily unavailable.
- Logs can show similar-looking Windows paths with different repository roots (`dfly-platform-management` vs `DFLYP-5279`); resolution must always treat different roots as
  distinct physical directories.
- On case-insensitive filesystems, path normalization must not collapse truly different roots even when path components differ only by case in surrounding segments.
- Pin file exists but is expired (TTL exceeded) — auto-start should fall through to bootstrap-based resolution gracefully.
- Pin file points to a state directory that was deleted — `read_and_validate_pin_file` attempts `mkdir(parents=True, exist_ok=True)`
  on the pinned path and returns the path if the directory can be (re)created; it returns `None` only
  when creation fails (e.g., permission error). A truly moved directory will similarly be re-created at the original
  path.
- Multiple concurrent workflow initiations writing to the same pin file — `os.replace` atomic semantics ensure last-writer-wins without corruption.

## Requirements

### Functional Requirements

- **FR-001**: The workflow initiation flow MUST select one canonical state directory for each review run and use it for both auto-execute and VS Code auto-start
  resolution.
- **FR-002**: If `AGENTIC_DEVTOOLS_STATE_DIR` is inherited from a parent source repository process and conflicts with the target worktree context, initialization MUST
  override or clear that inherited value before state writes occur.
- **FR-003**: The target worktree bootstrap/pin mechanism MUST point to the same canonical state directory chosen during initiation before the first auto-start Copilot
  session begins. Specifically, `_run_auto_execute_command` (or its caller) MUST write a `pinned-state-dir.json` in the target worktree's `.agdt/` directory containing the resolved state path before
  VS Code opens the worktree and the auto-start task fires.
- **FR-004**: State written by auto-execute (including active workflow metadata) MUST be readable by the first `@agdt.advance-workflow` call in the target worktree
  session without manual intervention.
- **FR-005**: Setup logging MUST emit the resolved canonical state directory for both initiation stages so mismatches can be detected and debugged quickly.
- **FR-006**: The implementation MUST prevent per-run prompt/state directory divergence caused by mixed source-repo and worktree-local state roots.
- **FR-007**: The existing state resolution behavior in `copilot_auto_start_cmd` (via `get_state_file_path()`/`get_state_dir()`) MUST be preserved: when
  `{worktree_path}/.agdt/pinned-state-dir.json` is valid, the pinned directory is used before bootstrap-based fallback.
- **FR-008**: The pin file MUST be written to the target worktree's `.agdt/` directory (not the source repository's) so that the auto-start task, which operates in the target worktree context, can
  find it.

### Non-Functional Requirements

- **NFR-001**: The solution MUST preserve backward compatibility for workflows that already resolve to a single repository state directory. When no pin file exists, behavior MUST be identical to the
  current implementation.
- **NFR-002**: The solution MUST behave deterministically on supported platforms (including Windows path semantics) so repeated runs resolve identical state roots
  for the same workflow context.

## Success Criteria

### Measurable Outcomes

- **SC-001**: In the reproduction flow from #1913, the first VS Code auto-start Copilot session can call `@agdt.advance-workflow` without a "no active workflow"
  response.
- **SC-002**: In logs from a workflow run, state path outputs for auto-execute and VS Code auto-start match the same canonical directory.
- **SC-003**: The workflow no longer creates split prompt/state artifacts for the same run due to source-vs-worktree state directory mismatch.
- **SC-004**: Existing single-repository workflows (no cross-worktree handoff) pass all existing tests without modification.

## Related

- #1912 (duplicate sessions — downstream consequence of state mismatch)
- #1180 (original pin-file mechanism for race condition fix — the infrastructure this fix extends)

---
*Generated by Copilot SDK (claude-opus-4.6)*
