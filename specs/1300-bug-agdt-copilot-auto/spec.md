# Spec: [Bug] agdt-copilot-auto-start.exe intermittently fails in Windows worktree due to file access error ([WinError 32])

**Source Issue**: #1300

## Problem Statement

`agdt-copilot-auto-start.exe` intermittently fails in Windows worktree environments with `[WinError 32]`, indicating that a required file is
still in use by another process. This causes auto-start workflows to fail even though the underlying operation may have succeeded moments
later if retried.

The issue appears during worktree-oriented flows where process startup, file access, and cleanup timing are sensitive on Windows. The current
behavior is not resilient to transient file locks, and failures do not consistently provide enough diagnostic detail to distinguish a
short-lived lock from a persistent error.

The goal of this change is to make the Windows auto-start path robust against transient file access conflicts without changing expected
behavior on successful runs or on non-Windows platforms.

## Clarifications

### Session 2026-05-03

- Q: Which specific call site(s) in `auto_start.py` should the retry logic wrap — only the `subprocess.run` invocation in `copilot_auto_start_cmd` that launches the Copilot CLI, or also
  state-file operations such as `_mark_run_triggered` and `_read_model_from_state`? → A: The retry logic should wrap the `subprocess.run` call in `copilot_auto_start_cmd` and its surrounding
  `OSError` handler, since `[WinError 32]` during process launch is the reported failure mode. State-file operations already use `locked_state_file` with their own retry/timeout and should not be
  double-wrapped.
- Q: What concrete retry budget should be used — how many attempts, what backoff strategy, and what maximum wall-clock time? → A: Use exponential backoff starting at 0.5 s, doubling each attempt,
  capped at 4 s per delay, with a maximum of 5 retry attempts (6 total tries). This gives a worst-case cumulative backoff delay of 11.5 s (0.5 + 1 + 2 + 4 + 4) plus subprocess execution
  overhead, which is short enough to avoid stalling interactive workflows but long enough to outlast typical Windows antivirus and indexer locks.
- Q: Should the retry be gated on `sys.platform == "win32"` so non-Windows platforms never enter the retry loop, or should the classification function simply never match non-Windows `OSError`
  instances? → A: The retry classification function should check the `winerror` attribute of the `OSError` (attribute value `32` for `ERROR_SHARING_VIOLATION`). On non-Windows platforms, `OSError`
  instances lack the `winerror` attribute, so the classifier naturally returns `False` and the error falls through to the existing immediate-failure path. No platform gate is needed.
- Q: Should the retry constants (max attempts, initial delay, backoff factor, max delay) be configurable via state keys or environment variables, or hard-coded? → A: Hard-code the constants as
  module-level values with clear names (e.g., `_RETRY_MAX_ATTEMPTS = 5`, `_RETRY_INITIAL_DELAY_S = 0.5`, `_RETRY_BACKOFF_FACTOR = 2.0`, `_RETRY_MAX_DELAY_S = 4.0`). This avoids adding configuration
  surface area for a narrow bug fix. If tunability is needed later, the named constants make it a one-line change to read from state or environment.
- Q: What happens if `[WinError 32]` occurs during the best-effort cleanup phase (`_cleanup_auto_start_task`) after a successful Copilot session — should that also be retried? → A: No. The
  cleanup phase is already best-effort and non-fatal. A `[WinError 32]` during cleanup should be logged as a warning (consistent with the existing cleanup pattern) but must not trigger the retry loop
  or change the exit code from 0.

## User Scenarios & Testing

### User Scenario 1 - Retry on transient Windows file lock (Priority: P1)

A user starts an AI workflow in a Windows worktree, and the executable initially encounters a transient `[WinError 32]` because a file handle
has not yet been released. The command should retry automatically and succeed if the lock clears within the allowed retry window.

**Why this priority**: This is the core failure mode blocking normal workflow execution for Windows users.

**How to test**: Simulate a transient file lock that is released after a short delay and verify the command retries and then completes
successfully without user intervention. Specifically, mock `subprocess.run` to raise `OSError` with `winerror=32` for the first N calls (1 ≤ N ≤ 5), then succeed on attempt N+1. Assert the function
returns exit code 0, that exactly N+1 total calls were made, and that retry log messages include attempt numbers and delay durations.

### User Scenario 2 - Preserve actionable diagnostics on persistent failure (Priority: P2)

A user encounters a persistent file access problem that does not clear within the retry budget. The command should fail with clear logging
that explains retries were attempted, why the error was treated as retryable, and what final error caused termination.

**Why this priority**: When retries do not resolve the problem, users and maintainers need enough evidence to diagnose the root cause.

**How to test**: Simulate a lock that remains in place past the retry window (mock `subprocess.run` to always raise `OSError` with `winerror=32` for all 6 tries) and verify the final error output
includes the number of retries attempted (5), cumulative backoff time spent, and the terminating exception message. Assert exit code is 1 and `_unmark_run_triggered` was called.

### User Scenario 3 - Clean interruption during retry loop (Priority: P2)

A user presses Ctrl+C while the command is sleeping between retries. The process should stop promptly, avoid leaving partial state or leaked
handles behind, and surface an interruption outcome rather than masking it as a file access failure.

**Why this priority**: Retry logic must remain safe and controllable during interactive use.

**How to test**: Trigger a retryable failure, raise `KeyboardInterrupt` during the `time.sleep` backoff delay, and verify the command exits with code 130, calls `_unmark_run_triggered`, and does not
attempt further retries.

### User Scenario 4 - No regression outside the Windows-specific failure path (Priority: P3)

A user runs the same workflow on a non-Windows platform, or on Windows without file locking contention. The command should behave exactly as
before except for additional internal resilience and logging.

**Why this priority**: The fix must not introduce regressions in unaffected environments.

**How to test**: Run existing success-path coverage on non-Windows and uncontended Windows paths and verify behavior and outputs remain
compatible. Specifically, assert that an `OSError` without a `winerror` attribute (or with a non-32 `winerror` value) is not classified as retryable and fails immediately on the first occurrence.

## Requirements

### Functional Requirements

1. The Windows auto-start path must detect transient file access failures consistent with `[WinError 32]` (`ERROR_SHARING_VIOLATION`) by inspecting the `winerror` attribute of the `OSError` instance.
   Only `winerror == 32` is classified as retryable.
2. The implementation must handle retryable file access failures using bounded retry logic rather than failing immediately on the first
   occurrence. The retry wraps the `subprocess.run` call site in `copilot_auto_start_cmd`.
3. The retry loop must stop and return success as soon as the protected operation completes successfully.
4. The retry loop must stop and return failure when the maximum retry budget is exhausted (5 retries, 6 total tries, approximately 11.5 s of cumulative backoff delay plus execution overhead).
5. Errors that are not classified as transient file access conflicts (i.e., `OSError` without `winerror == 32`, `FileNotFoundError`, or any non-`OSError` exception) must not be retried and must
   continue to fail immediately.
6. Each retry attempt must emit diagnostic logging to stderr that records the attempt number (e.g., "retry 2/5"), the backoff delay before the next attempt, and the `winerror` code confirming the
   error was classified as retryable.
7. Final failure logging must indicate that retries were attempted, the number of retries made (5 at maximum), the total number of tries (6 at maximum), and include the terminal exception details.
8. The implementation must release or avoid retaining file and process handles that could contribute to self-inflicted locking during startup
   and cleanup. Specifically, no new file handles should be opened or held open across retry iterations.
9. If the user interrupts the command during retry delay or retry execution, the command must stop retrying, call `_unmark_run_triggered`, and exit with code 130 through normal `KeyboardInterrupt`
   handling.
10. If the worktree or target file disappears during retries (i.e., the error changes from `winerror=32` to `FileNotFoundError` or the worktree directory no longer exists), the command must fail with
    the appropriate terminal error rather than retrying
    indefinitely.
11. Existing success-path behavior, command-line interface expectations, and state interactions must remain backward compatible outside the
    retryable failure path.
12. Retry constants must be defined as named module-level values (`_RETRY_MAX_ATTEMPTS = 5`, `_RETRY_INITIAL_DELAY_S = 0.5`, `_RETRY_BACKOFF_FACTOR = 2.0`, `_RETRY_MAX_DELAY_S = 4.0`) for
    maintainability.
13. The best-effort cleanup phase (`_cleanup_auto_start_task`) must not use retry logic. A `[WinError 32]` during cleanup is logged as a warning and does not affect the exit code.

### Non-Functional Requirements

1. The retry strategy must use exponential backoff starting at 0.5 s, doubling each attempt, capped at 4 s per delay, with a maximum of 5 retries (6 total tries), yielding approximately 11.5 s of
   cumulative backoff delay (0.5 + 1 + 2 + 4 + 4) plus subprocess execution overhead.
2. The fix must preserve backward compatibility for unaffected platforms and for successful runs that never enter retry handling. On non-Windows platforms, the `winerror` attribute is absent from
   `OSError` instances, so the classifier returns `False` and no retry is attempted.
3. User-facing output should remain consistent with existing UX patterns. Retry diagnostic messages must use the existing `agdt-copilot-auto-start:` prefix and print to stderr, matching the style of
   other diagnostic messages in the module.
4. Automated test coverage must include: (a) transient retry success after 1, 2, and N failures; (b) retry exhaustion after max attempts; (c) `KeyboardInterrupt` during backoff sleep; (d)
   non-retryable `OSError` (no `winerror` attribute or `winerror != 32`); (e) error type change mid-retry (e.g., `winerror=32` → `FileNotFoundError`). All tests must follow the 1:1:1 test structure
   under `tests/unit/cli/copilot/auto_start/`.

## Success Criteria

1. In automated tests that simulate transient `[WinError 32]` conditions (by mocking `subprocess.run` to raise `OSError(winerror=32)` then succeed), the command succeeds after one or more retries
   without manual
   intervention.
2. In automated tests that simulate persistent `[WinError 32]` conditions (all 6 attempts raise `OSError(winerror=32)`), the command fails only after the configured retry budget is
   exhausted (5 retries) and reports that retries were attempted.
3. In automated tests that simulate Ctrl+C during retry delay (by raising `KeyboardInterrupt` from a mocked `time.sleep`), the command exits with code 130 and does not continue retrying after
   interruption.
4. In automated tests for non-retryable errors (e.g., `OSError` with `winerror=5` or without `winerror`) and non-Windows execution paths, behavior matches pre-fix expectations except for safe
   internal logging improvements.
5. Review of logs and runtime behavior confirms that handle cleanup and retry diagnostics are sufficient to diagnose intermittent Windows
   worktree failures. Specifically, each retry log line includes the attempt number, delay, and winerror code.

## Edge Cases

- Ctrl+C is received while the process is sleeping between retries. Expected: exit code 130, `_unmark_run_triggered` called, no further retries.
- The worktree, executable, or a referenced file is deleted between retry attempts. Expected: the changed error type (`FileNotFoundError` or missing-directory check) is detected and the command fails
  immediately with a targeted message instead of continuing to retry.
- The command is executed on a non-Windows platform where the Windows-specific retry classification should not alter behavior. Expected: `OSError` instances lack the `winerror` attribute, so the
  classifier returns `False` and the error is raised immediately.
- State file access or other unrelated file contention occurs and must not be incorrectly classified as the targeted transient startup lock
  unless it matches the intended retryable condition. Expected: only `OSError` with `winerror == 32` raised from the `subprocess.run` call site triggers retry; state-file locking uses its own
  `locked_state_file` mechanism.
- The `[WinError 32]` error occurs on every attempt up to and including the 6th (final) try. Expected: the command exhausts the retry budget, logs a summary of all attempts, calls
  `_unmark_run_triggered`, and exits with code 1.
- Two concurrent auto-start processes both enter the retry loop for the same worktree. Expected: the existing `_mark_run_triggered` / `_is_run_triggered` deduplication guard prevents duplicate
  sessions; the retry loop operates after the mark check, so only one process retries.

---
*Generated by Copilot SDK (claude-opus-4.6)*
