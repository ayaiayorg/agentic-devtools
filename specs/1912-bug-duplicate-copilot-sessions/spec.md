# Feature Specification: Prevent Duplicate Copilot Sessions During PR Review Workflow

**Feature Branch**: `1912-prevent-duplicate-copilot-sessions`  
**Created**: 2026-06-05  
**Status**: Draft  
**Source Issue**: #1912 (<https://github.com/ayaiayorg/agentic-devtools/issues/1912>)

## Problem Statement

When the PR review workflow is initiated from a different repository context (e.g., running `agdt-initiate-pull-request-review-workflow` from `dfly-platform-management` targeting a worktree at
`C:\repos\DFLYP-5279`), the system creates two independent Copilot sessions that both perform the full review workflow in parallel. This results in duplicate approval comments posted to the pull
request, duplicate review thread scaffolding with differing commit hashes, wasted API calls and AI credits, and a confusing PR comment history that undermines the credibility of automated reviews.

The root cause is a three-part race condition involving state directory resolution, timing, and fallback behavior. First, the auto-execute command (which runs with `--skip-copilot-session`) writes
workflow state to a state directory resolved via the originating repository's bootstrap configuration. Second, the VS Code auto-start task fires approximately 46 seconds after VS Code opens in the new
worktree, where it resolves to a potentially different state directory because the worktree's own bootstrap may scope differently. Third, when the auto-start task's agent calls
`@agdt.advance-workflow` and finds no active workflow (because it is looking in the wrong state directory), it falls back to calling `@agdt.pull-request-review.initiate`, which re-initiates the entire
workflow from scratch — this time without `--skip-copilot-session`, spawning a second background task and a second Copilot session.

This problem affects all developers who use the cross-repository PR review initiation pattern, which is the standard workflow for reviewing PRs in service repositories from a central management
worktree. The impact is not merely cosmetic: duplicate reviews consume double the AI credits, post conflicting approval states, and can trigger downstream automation (such as auto-merge) based on a
review that was performed against a stale or incorrect commit hash. Evidence of this problem was observed on 2026-06-04 with two log files (`copilot_session_20260604T134459_97.log` and
`copilot_session_20260604T134703_32.log`) showing sessions with PIDs 9296 and 30408 running simultaneously against PR #28407.

## User Scenarios & Testing

### User Story 1 - Single Session Guarantee for Cross-Repo Review Initiation (Priority: P1)

As a developer initiating a PR review from a different repository context, I expect that exactly one Copilot session is started for the target worktree, regardless of timing between the auto-execute
command and the VS Code auto-start task. The system must ensure that when VS Code opens and fires the auto-start task, it finds the workflow state that was already written by the auto-execute phase,
preventing any re-initiation.

**Why this priority**: This is the core bug fix. Without this guarantee, every cross-repo review initiation is vulnerable to the duplicate session race condition, causing wasted resources and
confusing PR comments.

**Independent Test**: Can be fully tested by initiating a PR review from a secondary repository, observing that only one Copilot session PID appears in the background task logs, and verifying that
only one set of review thread scaffolding is created on the PR.

**Acceptance Scenarios**:

1. **Given** a developer runs `agdt-initiate-pull-request-review-workflow --pull-request-id 28407 --issue-key DFLYP-5279` from the `dfly-platform-management` repo, **When** the auto-execute command
   completes and VS Code opens with the auto-start task, **Then** only one Copilot session is started (verified by a single `copilot.pid` in state and a single session log file).

2. **Given** the auto-execute command has written workflow state with `--skip-copilot-session`, **When** the VS Code auto-start task fires 30–60 seconds later in the target worktree, **Then** the
   auto-start task's agent finds the active workflow state and advances it (rather than re-initiating).

3. **Given** a Copilot session is already running for the target worktree (verified by `copilot.pid` in state and process liveness check), **When** any command attempts to start a second Copilot
   session for the same worktree, **Then** the second session is blocked and an informational message is emitted explaining that a session is already active.

---

### User Story 2 - State Directory Alignment Between Auto-Execute and Auto-Start (Priority: P1)

As the system performing automated worktree setup, I must ensure that the auto-execute command and the VS Code auto-start task resolve to the identical state directory so that workflow state written
by one is visible to the other. This alignment must work regardless of which repository the initiation command was originally run from.

**Why this priority**: State directory misalignment is the fundamental cause of the duplicate session bug. If both phases resolve to the same directory, the auto-start task will always find the active
workflow.

**Independent Test**: Can be tested by running the auto-execute command, then separately resolving the state directory from within the target worktree context, and asserting both paths are identical.

**Acceptance Scenarios**:

1. **Given** the auto-execute command runs in the context of repo A but targets a worktree for repo B, **When** it writes workflow state, **Then** the state is written to the state directory scoped to
   repo B's worktree (not repo A's).

2. **Given** the VS Code auto-start task runs inside the target worktree, **When** it resolves the state directory via `get_state_dir()`, **Then** it resolves to the same path that the auto-execute
   command wrote to.

3. **Given** a `.agdt/runtime-bootstrap.json` exists in the target worktree, **When** state directory resolution occurs from either the auto-execute or auto-start context, **Then** both resolve
   identically using the worktree's own bootstrap configuration.

---

### User Story 3 - Advance-Workflow Guard Against Re-Initiation (Priority: P1)

As an AI agent running inside a Copilot session, when I call `@agdt.advance-workflow` and no active workflow is found, I must NOT fall back to re-initiating the workflow. Instead, I should report a
clear error and wait for the workflow state to become available or for human intervention.

**Why this priority**: Even if the state directory alignment is fixed, defensive behavior in the advance-workflow agent prevents catastrophic re-initiation in any edge case where state is temporarily
unavailable.

**Independent Test**: Can be tested by calling `agdt-advance-workflow` with an empty or missing workflow state file, and verifying the command exits with an error code and descriptive message rather
than triggering a new workflow initiation.

**Acceptance Scenarios**:

1. **Given** no active workflow exists in the current state directory, **When** the agent calls `@agdt.advance-workflow pull-request-overview`, **Then** the command exits with a non-zero exit code and
   prints a message such as "No active workflow found. Do not re-initiate — check state directory resolution."

2. **Given** the advance-workflow command fails due to missing workflow state, **When** the Copilot agent receives this error, **Then** the agent does NOT call `@agdt.pull-request-review.initiate` as
   a fallback — it reports the issue and waits.

3. **Given** a workflow was previously active but has been cleared, **When** advance-workflow is called, **Then** the error message distinguishes between "no workflow ever started" and "workflow was
   cleared" to aid debugging.

---

### User Story 4 - Session Mutex with Process Liveness Verification (Priority: P2)

As the system managing Copilot sessions, I must implement a mutex mechanism that prevents concurrent sessions for the same worktree/workflow combination. The mutex must verify process liveness (not
just the presence of a PID in state) to avoid deadlocking on stale PIDs from crashed sessions.

**Why this priority**: The mutex is a safety net that catches duplicate session attempts even when the root cause (state misalignment) has been fixed. It provides defense-in-depth.

**Independent Test**: Can be tested by writing a fake `copilot.pid` to state, then attempting to start a new session. If the PID is dead, the session should start normally (clearing the stale PID). If
the PID is alive, the session should be blocked.

**Acceptance Scenarios**:

1. **Given** `copilot.pid` in state contains a PID that corresponds to a running process, **When** a new Copilot session start is attempted for the same worktree, **Then** the start is blocked and a
   warning is emitted with the existing session's PID and start time.

2. **Given** `copilot.pid` in state contains a PID that no longer corresponds to a running process (stale), **When** a new Copilot session start is attempted, **Then** the stale PID is cleared from
   state and the new session starts normally.

3. **Given** no `copilot.pid` exists in state, **When** a new Copilot session is started, **Then** the session starts normally and writes its PID to `copilot.pid` in state.

---

### Edge Cases

- What happens when the auto-execute command crashes mid-write of workflow state, leaving a partially written `state.json`? The auto-start task should detect the corrupted state and report an error
  rather than re-initiating.
- How does the system handle the case where VS Code's auto-start task fires before the auto-execute command has completed (extremely fast VS Code startup)? A brief retry/wait mechanism should be
  employed.
- What happens on Windows when the PID stored in state belongs to a recycled process (different application reusing the same PID)? The liveness check should verify the process name or command line
  matches the expected Copilot session pattern.
- What happens if the user manually kills the Copilot session and wants to restart? The user should be able to explicitly clear the mutex via `agdt-delete copilot.pid` (or by removing the
  `copilot.pid` state key directly).

## Requirements

### Functional Requirements

- **FR-001**: The system MUST implement a session mutex that checks for an existing live Copilot session (via `copilot.pid` state key and OS-level process liveness verification) before starting any
  new Copilot session for the same worktree. If a live session exists, the new session start MUST be blocked and an informational message MUST be emitted to stderr.

- **FR-002**: The system MUST ensure that the auto-execute command (running with `--skip-copilot-session` in the originating repo context) writes workflow state to the state directory scoped to the
  TARGET worktree — not the originating repository's state directory. This means `get_state_dir()` must be called with the target worktree path as context during auto-execute.

- **FR-003**: The `agdt-advance-workflow` command MUST exit with a non-zero exit code and a descriptive error message when no active workflow is found in the current state directory. It MUST NOT
  trigger any workflow initiation logic as a fallback. The error message must include guidance for the agent (e.g., "Check state directory resolution — do not re-initiate").

- **FR-004**: The session mutex MUST perform process liveness verification by checking whether the stored PID corresponds to a running process. If the stored PID is stale (process no longer running),
  the system MUST clear the stale `copilot.pid` from state and allow the new session to proceed.

- **FR-005**: The system MUST write `copilot.pid` to the target worktree's state directory (not the originating repo's state directory) immediately upon starting a Copilot session, ensuring that
  subsequent session start attempts from the same worktree context will find the mutex.

- **FR-006**: The `@agdt.copilot-auto-start` agent prompt MUST include explicit instructions to NEVER re-initiate a workflow if `@agdt.advance-workflow` fails. The agent must report the error and
  await human intervention or state resolution.

- **FR-007**: The system MUST support a grace period (configurable, default 10 seconds) during which the auto-start task retries state directory resolution before concluding that no workflow exists.
  This accounts for the timing gap between auto-execute completion and VS Code auto-start task execution.

- **FR-008**: When the session mutex blocks a session start, the system MUST log the blocking event (including the existing session's PID, start time, and session ID) to enable post-incident
  debugging.

### Non-Functional Requirements

- **NFR-001**: The session mutex check (PID lookup and liveness verification) MUST complete within 500 milliseconds on both Windows and Linux/macOS to avoid delaying normal session startup.

- **NFR-002**: The state directory alignment fix MUST maintain backward compatibility with existing single-repo workflows where the originating repo and target worktree are the same repository. No
  behavioral change should be observed for the common case.

- **NFR-003**: All error messages emitted by the advance-workflow guard and session mutex MUST be actionable — they must tell the agent or user what to do next (e.g., "Run `agdt-show` to verify state
  directory" or "Clear stale session with `agdt-delete copilot.pid`").

- **NFR-004**: The fix MUST NOT introduce additional external dependencies. Process liveness checking must use Python standard library facilities and built-in OS capabilities invoked through them
  (`os.kill(pid, 0)` on Unix, `ctypes` or `subprocess` with built-in `tasklist` on Windows).

### Key Entities

- **Session Mutex**: A logical lock represented by the `copilot.pid` state key combined with OS-level process liveness verification. Scoped to a single worktree's state directory.
- **State Directory**: The resolved path `.agdt/workflows/{identity}/{worktree_key}/` where workflow state and session metadata are persisted. Must be deterministic given a worktree path.
- **Auto-Execute Context**: The execution phase that runs inside the originating repo but targets a different worktree. Must write state to the target worktree's state directory.
- **Auto-Start Context**: The execution phase that runs inside the target worktree via VS Code's `task.json` `folderOpen` trigger. Must find state in its own worktree's state directory.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After the fix is deployed, zero duplicate Copilot sessions are observed across 20 consecutive cross-repo PR review initiations (measured by counting unique `copilot.pid` values written
  per workflow instance).

- **SC-002**: The auto-start task successfully finds the workflow state written by the auto-execute command in 100% of test runs where the auto-execute completed before VS Code opened (no false "no
  active workflow" errors).

- **SC-003**: The session mutex correctly blocks duplicate session starts within 500ms in 100% of test cases where a live session already exists (measured by unit tests with mock process tables).

- **SC-004**: The advance-workflow guard correctly returns a non-zero exit code (without re-initiating) in 100% of test cases where no active workflow exists (measured by unit tests and integration
  tests).

- **SC-005**: The grace period retry mechanism resolves timing-related state visibility issues, reducing "no active workflow found" false negatives to fewer than 1% of cross-repo initiations (measured
  over 50 test runs with simulated 30–60 second delays).

- **SC-006**: No regression in single-repo workflow initiation — existing tests for `agdt-initiate-pull-request-review-workflow` within the same repo continue to pass with zero behavioral changes
  (measured by full test suite execution).

---
*Generated by Copilot SDK (claude-opus-4.6)*
