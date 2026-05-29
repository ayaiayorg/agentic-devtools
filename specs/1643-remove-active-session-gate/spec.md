# Feature Specification: Remove active_session gate from dispatch_repair and use gh agent-task for reliable session detection

**Feature Branch**: `speckit/1643/phase-1-specify`  
**Created**: 2026-05-28  
**Status**: Draft  
**Input**: User description: "Remove active_session gate from dispatch_repair and use gh agent-task for reliable session detection"  
**Source Issue**: #1643 (<https://github.com/ayaiayorg/agentic-devtools/issues/1643>)

## Problem Statement

The `DispatchRepairAction` in the CI automation loop currently enforces a `no_active_session` precondition that checks whether a GitHub Copilot coding session is running before dispatching repair
comments to a pull request. This precondition relies on `is_copilot_session_active()` in `agentic_devtools/cli/ci/pipeline/session_detector.py`,
which infers session state from GitHub Issues Events API timeline entries
(`copilot_work_started`, `copilot_work_finished`, `copilot_work_finished_failure`). The inference is fundamentally unreliable: terminal events can be delayed or missing entirely, the API call itself
can fail, and the 1-hour staleness timeout is far too generous for sessions that typically complete within minutes. The net effect is that the automation loop frequently produces
`skip (preconditions: {'no_active_session': False})` log entries even when no Copilot session is actually running, blocking all CI repair indefinitely until the stale event ages out.

The problem is compounded by the fail-closed design of the current detector. When the Issues Events API call raises an exception — whether due to rate limiting, network issues, or permissions errors —
`is_copilot_session_active()` returns `True`, treating the unknown state as "active." This means any transient API failure blocks the entire repair pipeline. In practice, teams have observed PRs stuck
in a "needs repair but won't dispatch" state for hours because a single failed API call triggered the fail-closed path, and no subsequent retry mechanism exists to re-evaluate.

Furthermore, the session gate on `dispatch_repair` is architecturally unnecessary. The repair mechanism works by posting an `@copilot` comment on the PR. If a Copilot session is already active, that
comment steers the active session toward the repair work. If no session is active, the comment triggers a new session. Either outcome is desirable and correct — the comment is idempotent with respect
to session lifecycle. Unlike actions that may still need to consider session state, `dispatch_repair` does not need session awareness because it behaves correctly whether a Copilot session is already
running or must be started by the comment. Therefore, removing the session gate from `dispatch_repair` eliminates a class of false-positive blocks without introducing any harmful behavior.

## User Scenarios & Testing

### User Story 1 - CI Repair Dispatches Without Session Gate (Priority: P1)

As an automation operator relying on the PR merge manager loop, I need the `dispatch_repair` action to evaluate and execute based solely on whether CI is failing or a Copilot review is actionable,
without being blocked by unreliable session detection. This ensures that when my PR has failing checks or unresolved review comments, a repair comment is always dispatched promptly, regardless of
whether the session detector thinks a Copilot session might be running.

**Why this priority**: This is the core behavioral change requested in the issue. Without it, the entire automation loop can stall indefinitely due to false-positive session detection, requiring
manual intervention to unblock PRs. It directly addresses the most common failure mode observed in production.

**Independent Test**: Can be fully tested by running the `DispatchRepairAction.evaluate()` method with a `PRStateSnapshot` where `active_session=True` and `ci_status="failing"`, and verifying the
action returns `EXECUTE` rather than `SKIP`. Delivers immediate value by unblocking all repair dispatches that were previously gated.

**Acceptance Scenarios**:

1. **Given** a PR with `ci_status="failing"` and `active_session=True` in the state snapshot, **When** `DispatchRepairAction.evaluate()` is called, **Then** the result decision is
   `ActionDecision.EXECUTE` and the preconditions dict does not contain a `no_active_session` key.
2. **Given** a PR with `ci_status="failing"` and `active_session=False` in the state snapshot, **When** `DispatchRepairAction.evaluate()` is called, **Then** the result decision is
   `ActionDecision.EXECUTE` (same behavior as scenario 1, confirming session state is irrelevant).
3. **Given** a PR with `ci_status="passing"` and no actionable Copilot review, **When** `DispatchRepairAction.evaluate()` is called, **Then** the result decision is `ActionDecision.SKIP` with details
   indicating no repair is needed, regardless of `active_session` value.
4. **Given** a PR with an actionable Copilot review and `active_session=True`, **When** `DispatchRepairAction.evaluate()` is called, **Then** the result decision is `ActionDecision.EXECUTE` because
   the review needs addressing and the session gate no longer applies.

---

### User Story 2 - Reliable Session Detection via gh agent-task (Priority: P2)

As a developer maintaining session-aware CI logic, I need a reliable session detector that queries `gh agent-task list` for authoritative session state
instead of inferring it from timeline events. This ensures session-aware decisions rely on accurate running/stopped status rather than a heuristic guess that can
produce both false positives and false negatives.

**Why this priority**: While the dispatch_repair gate removal (P1) eliminates the most common failure mode, session-aware checks still require accurate detection. Without replacing the
detector, these checks continue to suffer from unreliable heuristics. This story provides infrastructure for future session-aware actions.

**Independent Test**: Can be tested by mocking the `gh agent-task list` subprocess call and verifying that the new detector correctly interprets "running" and "stopped" states from the JSON output.
Also testable by simulating API failures and confirming fail-open behavior.

**Acceptance Scenarios**:

1. **Given** `gh agent-task list` returns a task with status "running" for the current PR, **When** the new session detector is invoked, **Then** it returns `True` (session is active).
2. **Given** `gh agent-task list` returns tasks all with status "stopped" or "completed" for the current PR, **When** the new session detector is invoked, **Then** it returns `False` (no active
   session).
3. **Given** `gh agent-task list` returns an empty list for the current PR, **When** the new session detector is invoked, **Then** it returns `False` (no session has ever run).
4. **Given** the `gh agent-task list` command fails (non-zero exit code,
   timeout, or permission error), **When** the new session detector is
   invoked, **Then** it returns `False` (fail-open) and logs a warning
   indicating the failure reason.

---

### User Story 3 - Fail-Open Default for Session Detection (Priority: P2)

As an automation operator, I need the session detection system to default to "no active session" when it cannot determine session state, so that transient API failures or network issues do not block
the automation loop. A false negative (dispatching while a session runs) is harmless because the `@copilot` comment simply steers the existing session. A false positive (blocking dispatch) breaks the
automation loop entirely.

**Why this priority**: This is a direct safety improvement that prevents the most egregious failure mode — indefinite blocking due to API errors. It pairs with P2 story 2 as a foundational design
principle for the new detector.

**Independent Test**: Can be tested by forcing the session detection mechanism to encounter various error conditions (network timeout, HTTP 403, malformed JSON response, command not found) and
verifying that each case returns `False` with appropriate warning logs.

**Acceptance Scenarios**:

1. **Given** the `gh` CLI is not installed or not in PATH, **When** the session detector attempts to check session state, **Then** it returns `False` and logs a warning message including the specific
   error encountered.
2. **Given** the GitHub API returns HTTP 403 (rate limited or insufficient permissions), **When** the session detector is invoked, **Then** it returns `False` and logs a warning with the HTTP status
   code.
3. **Given** the `gh agent-task list` command returns malformed JSON that cannot be parsed, **When** the session detector processes the output, **Then** it returns `False` and logs a warning including
   the parse error details.

---

### Edge Cases

- What happens when multiple Copilot sessions are listed by `gh agent-task list` for the same PR? The detector should consider the session active if ANY task has a
  non-terminal/active status as defined in FR-005.
- How does the system handle the `gh` CLI being available but `agent-task` subcommand not being recognized (older CLI version)? The detector should treat this as a command failure, log a warning, and
  return `False` (fail-open).
- What happens when `dispatch_repair` executes and posts a comment while a session IS actually running? The `@copilot` comment steers the active session — this is the expected and desired behavior,
  not an error condition.
- What happens if `gh agent-task list` returns a session with status "running" but the session has been running for an unusually long time (e.g., 6+ hours)? The new detector should still report it as
  active — staleness heuristics should not be applied to authoritative status from `gh agent-task`. If the session is truly stuck, that is a GitHub platform issue, not something the automation should
  second-guess.

## Requirements

### Functional Requirements

- **FR-001**: The `DispatchRepairAction.evaluate()` method MUST NOT check, reference, or use the `active_session` field from `PRStateSnapshot` when determining whether to dispatch a repair. The
  `no_active_session` precondition key MUST be completely removed from the preconditions dictionary returned in any `ActionResult` from this action.

- **FR-002**: The `DispatchRepairAction.evaluate()` method MUST return `ActionDecision.EXECUTE` when either `ci_status` is `"failing"` OR the Copilot review is actionable, regardless of the value of
  `snapshot.active_session`. Within `evaluate()`, the only conditions that should cause a `SKIP` decision are: (a) no repair is needed (CI passing and no actionable review), or (b) CI is still
  pending. This requirement applies only to the decision produced by `evaluate()` and does not prohibit intentional `SKIP` outcomes from `execute()` guard logic such as deduplication or cycle-limit
  protection.

- **FR-003**: The system MUST provide a new session detection function that invokes `gh agent-task list` (with appropriate repository context) and parses the JSON output to
  determine whether any Copilot coding session is currently in an active/non-terminal state (as defined in FR-005) for the given PR. This function replaces
  `is_copilot_session_active()` for all callers that still need session awareness. The detector
  MUST treat `gh agent-task list` as the authoritative source and MUST invoke it with explicit JSON field selection sufficient for detection, including `--json id,status,pullRequestNumber,createdAt`.
  The detector MUST expect each JSON task entry to be an object containing at least: an `id` string, a `status` string, a top-level integer field `pullRequestNumber`, and a `createdAt` timestamp
  string. A task entry is associated with the target PR if and only if `task.pullRequestNumber == pr_number`. The implementation and tests MUST use this mapping rule explicitly. A follow-up
  `gh agent-task view <id>` call MUST NOT be required for normal detection logic; `gh agent-task list` output alone MUST be sufficient. If a future CLI version omits PR linkage from list output
  and an implementation chooses to attempt `gh agent-task view <id>` as a compatibility fallback, that fallback is optional and any failure in the fallback path MUST still result in `False` in
  accordance with FR-004.

- **FR-004**: The new session detection function MUST return `False` (no active session) when any error occurs during execution, including but not limited to: subprocess execution failure, non-zero
  exit code from `gh`, JSON parse errors, network timeouts, missing `gh` CLI binary, and unrecognized subcommand errors. Each failure case MUST be logged at WARNING level with sufficient detail to
  diagnose the issue.

- **FR-005**: The new session detection function MUST return `True` (active session) if and only if the parsed output from `gh agent-task list` contains at least one task entry that both
  (a) is associated with the target PR according to FR-003 and (b) has a `status` value indicating a non-terminal/active state. For this specification, recognized active values are `"queued"`,
  `"requested"`, `"waiting"`, `"in_progress"`, and `"running"`; any other status value MUST be treated as not active unless this spec is updated to name additional values explicitly.

- **FR-006**: The old `is_copilot_session_active()` function in `agentic_devtools/cli/ci/pipeline/session_detector.py` MUST be deprecated or removed. If retained for backward compatibility, it MUST
  be marked with a deprecation warning directing callers to the new detector. No production code path should invoke the old function after migration is complete.

- **FR-007**: The `PRStateSnapshot` model MAY retain the `active_session` field for backward compatibility, but the field MUST NOT be populated by the events-based heuristic in the production
  snapshot-building path. In particular, the state-building logic in `pipeline/snapshot.py` used by `DispatchRepairAction` MUST stop computing or assigning `active_session` from
  `is_copilot_session_active()` or any other events-based heuristic. `DispatchRepairAction` MUST treat `snapshot.active_session` as unused compatibility data and MUST NOT read it.

- **FR-008**: The migration scope MUST include all production call sites that currently depend on events-based session detection or on `PRStateSnapshot.active_session`. At minimum, this includes
  (a) the snapshot builder in `pipeline/snapshot.py`, and (b) any production action/module that currently reads `snapshot.active_session` or calls `is_copilot_session_active()`. Each such
  caller MUST be updated either to remove session gating entirely (for `DispatchRepairAction`) or to invoke the new `gh agent-task` detector directly at the point of use. The implementation and
  tests MUST verify that no production path continues to rely on a snapshot-populated `active_session` value derived from the events heuristic.

### Non-Functional Requirements

- **NFR-001**: The new session detector MUST complete within 10 seconds under normal conditions. If `gh agent-task list` does not return within 10 seconds, the subprocess MUST be terminated and the
  detector MUST return `False` (fail-open timeout).

- **NFR-002**: The new session detector MUST NOT introduce any new external dependencies beyond the `gh` CLI (which is already a required tool in the environment). It MUST use `subprocess` for
  invocation rather than importing any GitHub SDK library.

- **NFR-003**: All changes MUST maintain 100% unit test coverage for modified and new code, consistent with the repository's existing coverage requirements. Tests MUST cover all error paths
  (subprocess failure, JSON parse error, timeout, missing binary) to verify fail-open behavior.

- **NFR-004**: Log output from the session detector MUST follow the existing logging patterns in the `agentic_devtools.cli.ci` module — using the module-level `logger` with appropriate levels (DEBUG
  for routine checks, WARNING for errors, INFO for state transitions).

## Success Criteria

### Measurable Outcomes

- **SC-001**: After implementation, the `DispatchRepairAction` MUST never produce a `SKIP` result with reason containing "active session" or "no_active_session" — verified by running the full test
  suite and confirming zero test cases expect session-gated skip behavior from dispatch_repair. Target: 0 occurrences of session-gated skips in dispatch_repair across all test scenarios.

- **SC-002**: The new `gh agent-task`-based session detector MUST return the
  expected boolean result for a defined fixture set of mocked `gh agent-task
  list` outputs (including running, stopped/completed, empty, and error
  cases) when `gh` is available and responsive. Verification method: deterministic
  unit/integration tests over those fixtures. Target: 100% of defined fixture
  scenarios return the expected boolean value.

- **SC-003**: Under API/CLI failure conditions (simulated via mocked subprocess errors), the new session detector MUST return `False` in 100% of error cases — verified by unit tests covering at least
  5 distinct failure modes (timeout, non-zero exit, malformed JSON, missing binary, permission error). Target: 5 out of 5 failure modes return `False`.

- **SC-004**: The time from CI failure detection to repair dispatch MUST decrease by eliminating the session-gate delay. In the previous behavior, a false-positive session detection could block
  dispatch for up to 3600 seconds (the staleness timeout). After implementation, the maximum delay introduced by session detection for dispatch_repair is 0 seconds (no gate exists). Target: 0 seconds
  of session-related delay for dispatch_repair.

- **SC-005**: All existing tests in the CI automation module MUST continue to pass after the changes, with no regressions introduced. Target: 0 test failures in the `tests/unit/cli/ci/` directory
  after implementation.

---
*Generated by Copilot SDK (claude-opus-4.6)*
