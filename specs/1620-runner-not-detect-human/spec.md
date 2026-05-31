# Feature Specification: Runner Human-in-the-Loop Pause Detection

**Feature Branch**: `speckit/1620/phase-1-specify`  
**Created**: 2026-05-31  
**Status**: Draft  
**Input**: GitHub Issue #1620 — Runner does not detect human-in-the-loop pause with LangGraph  
**Source Issue**: #1620 (<https://github.com/ayaiayorg/agentic-devtools/issues/1620>)

## Problem Statement

The LangGraph workflow runner in `agentic_devtools/orchestration/runner.py` currently
relies exclusively on catching a `GraphInterrupt` exception to detect when a workflow
has paused at a human-in-the-loop gate node (currently `planning_gate_node`; additional
gate nodes may be added in the future). This detection strategy is incomplete because
when a persistent checkpointer (e.g., `SqliteSaver`) is attached
to the compiled graph, LangGraph's `invoke()` method does not raise `GraphInterrupt`. Instead, it returns the current state dictionary with the workflow halted at the interrupt point. The runner then
falls through to the completion reporting path and prints `[langchain] Workflow completed: step=planning, status=active`, which is factually incorrect — the workflow has not completed, it is paused
waiting for human intervention.

This misleading output has a direct negative impact on the user experience. Users who see "Workflow completed" naturally assume the workflow has finished its work and may not realize they need to
provide input or run a resume command. They may interpret the situation as a bug, file support requests, or abandon the workflow altogether. The problem is particularly insidious because the runner
works correctly in the exception-based path (no checkpointer, or certain LangGraph versions that do raise the exception), creating inconsistent behavior depending on configuration — a situation that
is difficult to debug and erodes trust in the tool.

The fix requires the runner to inspect the returned state after `invoke()` completes
normally (no exception raised) and determine whether the workflow is truly complete or
merely paused. With a persistent checkpointer, an interrupt can return the last
completed step (e.g., `step="planning"`) while `status` remains `"active"`.
This means the runner should not rely on the gate node name being present in `step`; instead it should use `status` (and optionally other state signals) to distinguish pause vs. completion.
The runner must call `_print_pause_message` in the paused case and reserve the completion
message for true terminal states only.

## User Scenarios & Testing

### User Story 1 - Fresh Workflow Pauses at Planning Gate (Priority: P1)

An AI agent or developer starts a fresh work-on-jira-issue workflow using the LangGraph engine with a persistent checkpointer. The workflow progresses through initiate, setup, and planning nodes, then
reaches `planning_gate_node` which calls `interrupt()` to wait for human approval. The user expects to see a clear pause message with resume instructions, not a misleading completion message.

**Why this priority**: This is the primary failure mode described in the issue. Every user who runs the workflow with a checkpointer encounters this bug on their first run. Without fixing this, the
entire human-in-the-loop UX is broken — users cannot understand what the system is waiting for.

**Independent Test**: Can be fully tested by invoking the runner with a checkpointer-backed graph that pauses at `planning_gate_node` and verifying that stdout/stderr output contains the pause message
and does NOT contain the completion message. Delivers immediate value by making the most common workflow path behave correctly.

**Acceptance Scenarios**:

1. **Given** a compiled LangGraph with a persistent checkpointer and a workflow that
   reaches `planning_gate_node`, **When** the runner calls `invoke()` and receives a
   state with `status != "completed"`, **Then** the runner prints the pause message to
   stderr with resume instructions including the issue key, and does NOT print the
   "Workflow completed" message.

2. **Given** a compiled LangGraph with a persistent checkpointer, **When** the workflow
   pauses at `planning_gate_node` and `invoke()` returns state `{"step": "planning",
   "status": "active"}`, **Then** the runner's exit code is 0 (not an error) and the
   pause message includes the exact command to resume, for example:
   `agdt-initiate-work-on-jira-issue-workflow --issue-key <KEY> --engine langchain --resume`

3. **Given** a compiled LangGraph WITHOUT a checkpointer where `invoke()` raises `GraphInterrupt`, **When** the exception is caught, **Then** the existing exception-based pause detection continues to
   work identically (backward compatibility preserved).

---

### User Story 2 - Resumed Workflow Uses the Same Pause Detection Logic (Priority: P1)

A user resumes a previously interrupted workflow run using `--resume`. The runner
should apply the same post-`invoke()` state inspection to the resume path, so that if
the resumed invocation returns a non-terminal state (`status != "completed"`), it
prints the pause message instead of the misleading "Workflow completed" message.

**Why this priority**: The resume path (`compiled.invoke(Command(resume=...))`)
currently shares the same completion reporting code as the fresh-run path, so it can
misreport pauses in the same way (including for any future human-in-the-loop gates
added later).

**Independent Test**: Can be tested by stubbing/mocking `compiled.invoke` in resume
mode to return a non-completed state (or by building a minimal test graph with an
interrupt after resume) and verifying the pause message appears.

**Acceptance Scenarios**:

1. **Given** a resumed workflow invocation where `invoke(Command(resume=...))` returns
   a state with `status != "completed"`, **Then** the runner prints the pause message
   (not the completion message) and exits with code 0.

2. **Given** a resumed workflow invocation where `invoke(Command(resume=...))` returns
   `{"step": "completion", "status": "completed"}`, **Then** the runner prints
   `[langchain] Workflow completed: step=completion, status=completed` to stdout.

---

### User Story 3 - Workflow Runs to True Completion (Priority: P1)

A user has resumed through all gate nodes and the workflow runs all the way through commit, pull request, and completion nodes. The workflow reaches the terminal `completion_node` and the status is
set to `"completed"`. The user expects to see the legitimate "Workflow completed" message confirming their work is done.

**Why this priority**: Without this story, a naive fix might suppress the completion message entirely. This story ensures that the completion message still appears for genuinely finished workflows,
maintaining the UX contract for the happy path.

**Independent Test**: Can be tested by mocking all nodes to pass through without interrupts and verifying that the final output contains the "Workflow completed" message with `status=completed`.

**Acceptance Scenarios**:

1. **Given** a workflow that has passed through all nodes including the final `completion_node`, **When** `invoke()` returns state `{"step": "completion", "status": "completed"}`, **Then** the runner
   prints `[langchain] Workflow completed: step=completion, status=completed` to stdout.

2. **Given** a workflow in any intermediate non-gate step where status is not `"completed"` but the step is not a gate node, **When** `invoke()` returns unexpectedly, **Then** the runner treats this
   as a pause condition (conservative approach — a paused workflow is recoverable; a falsely-completed one is not).

---

### User Story 4 - Regression Test Coverage (Priority: P2)

A developer working on the orchestration module needs confidence that future changes to the runner or graph structure do not reintroduce the misleading completion message. Automated regression tests
must cover both the fresh-run and resume-run paths for pause detection, as well as the true-completion path.

**Why this priority**: Tests prevent regression and document the intended behavior. They are essential for long-term maintainability but do not directly fix the user-facing bug — they protect the fix
once it is in place.

**Independent Test**: Can be verified by running the test suite (`agdt-test-pattern tests/unit/orchestration/runner/`) and confirming all new pause-detection tests pass.

**Acceptance Scenarios**:

1. **Given** the test suite includes cases for state-based pause detection (fresh run at
   planning gate, resumed invocation returning a non-completed state, and true
   completion), **When** `agdt-test` and `bash scripts/targeted-checks.sh` are run,
   **Then** all new tests pass and branch coverage of the pause/completion decision
   logic is verified.

2. **Given** a developer modifies the runner to remove the state inspection logic, **When** the test suite runs, **Then** at least one test fails, preventing the regression from being merged.

---

### User Story 5 - CLI Help Documents Pause/Resume Behavior (Priority: P3)

A user unfamiliar with the human-in-the-loop workflow reads the CLI help output or user documentation to understand what happens when a workflow pauses and how to resume it. The documentation clearly
explains the pause/resume lifecycle.

**Why this priority**: Documentation improves discoverability and reduces support burden, but the primary fix (correct output messages) already contains resume instructions inline. This story adds
supplementary discovery paths.

**Independent Test**: Can be verified by running `agdt-initiate-work-on-jira-issue-workflow --help` and confirming that the help text mentions the pause/resume behavior and the `--resume` flag's
purpose.

**Acceptance Scenarios**:

1. **Given** a user runs `agdt-initiate-work-on-jira-issue-workflow --help`, **When** they read the output, **Then** it includes a description of the human-in-the-loop pause behavior and how
   `--resume` is used to continue after providing input.

---

### Edge Cases

- What happens when the returned state has no `status` key at all (e.g., due to a node failing to set it)? The runner should treat a missing or empty status as a non-completion and print the pause
  message rather than the completion message, since a missing status is never a valid terminal state.

- What happens when a new gate node is added to the graph in the future? The detection logic should not hardcode gate node names but instead rely on the `status` field value, making it
  forward-compatible with new interrupt points.

- What happens if `invoke()` returns `None` or an unexpected type? The runner should treat this as an error condition, print a diagnostic message to stderr, and exit with a non-zero code.

- What happens when the checkpointer database is corrupted or locked? This is outside the scope of this feature — the existing error handling for `invoke()` exceptions applies.

## Requirements

### Functional Requirements

- **FR-001**: The runner MUST inspect the state dictionary returned by `invoke()` after a normal (non-exception) return to determine whether the workflow has truly completed or has paused at a
  human-in-the-loop gate node.

- **FR-002**: The runner MUST print the pause message (via `_print_pause_message`) whenever the returned state's `status` field is not equal to `"completed"`, regardless of which specific gate node
  caused the pause. This ensures forward compatibility with future gate nodes without requiring code changes to the detection logic.

- **FR-003**: The runner MUST print the "Workflow completed" message ONLY when the returned state's `status` field equals `"completed"`, confirming true terminal completion of the workflow.

- **FR-004**: The runner MUST apply the same state-inspection logic to both the fresh invocation path (`compiled.invoke(initial_state, ...)`) and the resume invocation path
  (`compiled.invoke(Command(resume=...), ...)`), ensuring consistent behavior regardless of how the workflow was entered.

- **FR-005**: The runner MUST preserve backward compatibility with the existing `GraphInterrupt` exception-based detection. Both detection mechanisms (exception-based and state-inspection-based) must
  coexist, with the exception handler taking precedence when a `GraphInterrupt` is raised.

- **FR-006**: The pause message printed by the runner MUST include the issue key and the complete CLI command needed to resume the workflow, matching the existing `_print_pause_message` output format.

- **FR-007**: The runner MUST exit with code 0 when a pause is detected (not an error condition), matching the existing behavior when `GraphInterrupt` is caught.

### Non-Functional Requirements

- **NFR-001**: The state inspection logic MUST add negligible latency (< 1ms) to the runner's post-invocation processing, as it involves only dictionary key lookups on an already-in-memory state
  object.

- **NFR-002**: The runner's output format for pause and completion messages MUST remain consistent with the existing format established by `_print_pause_message` and the current completion print
  statement, preserving parseability for any downstream tools or scripts that consume runner output.

- **NFR-003**: The implementation MUST achieve 100% branch coverage in unit tests, consistent with the project's existing coverage requirements enforced by the targeted checks runner (`bash scripts/targeted-checks.sh`).

- **NFR-004**: The fix MUST NOT introduce any new dependencies or require changes to the LangGraph library version, relying solely on state dictionary inspection that is version-agnostic.

### Key Entities

- **WorkOnIssueState**: The TypedDict state schema containing `step`, `status`, and other workflow fields. The `status` field is the primary discriminator for pause vs. completion detection. Terminal
  value is `"completed"`; any other value (including `"active"`, empty string, or missing) indicates non-completion.

- **Gate Nodes**: Nodes that call `interrupt()` to pause execution (currently `planning_gate_node`). These nodes set or preserve `status` as non-`"completed"` while the workflow is waiting for human input.

## Success Criteria

### Measurable Outcomes

- **SC-001**: 100% of workflow runs that pause at a gate node with a persistent
  checkpointer print the pause message (not the completion message), verified by
  automated tests covering the `planning_gate_node` interrupt point.
- **SC-002**: 100% of workflow runs that reach true terminal completion (status = "completed") continue to print the "Workflow completed" message, verified by at least 2 automated test cases (fresh
  run to completion, resumed run to completion).

- **SC-003**: 0 regression test failures introduced by the change, verified by running the full test suite (`agdt-test`) with all 2000+ existing tests passing.

- **SC-004**: 100% branch coverage of the new pause/completion decision logic in `runner.py`, verified by `bash scripts/targeted-checks.sh`.

- **SC-005**: The pause detection logic adds fewer than 5 lines of net new code to the runner (excluding tests and documentation), ensuring the fix is minimal and surgical.

- **SC-006**: At least 3 new regression test cases are added covering: (a) fresh run
  pausing at a gate with a checkpointer, (b) resumed invocation returning a
  non-completed state (pause detected on the resume path), and (c) true completion
  printing the correct message.

---
*Generated by Copilot SDK (claude-opus-4.6)*
