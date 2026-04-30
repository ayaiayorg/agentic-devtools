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

## User Scenarios & Testing

### User Scenario 1 - Retry on transient Windows file lock (Priority: P1)

A user starts an AI workflow in a Windows worktree, and the executable initially encounters a transient `[WinError 32]` because a file handle
has not yet been released. The command should retry automatically and succeed if the lock clears within the allowed retry window.

**Why this priority**: This is the core failure mode blocking normal workflow execution for Windows users.

**How to test**: Simulate a transient file lock that is released after a short delay and verify the command retries and then completes
successfully without user intervention.

### User Scenario 2 - Preserve actionable diagnostics on persistent failure (Priority: P2)

A user encounters a persistent file access problem that does not clear within the retry budget. The command should fail with clear logging
that explains retries were attempted, why the error was treated as retryable, and what final error caused termination.

**Why this priority**: When retries do not resolve the problem, users and maintainers need enough evidence to diagnose the root cause.

**How to test**: Simulate a lock that remains in place past the retry window and verify the final error output includes retry attempts,
timing details, and the terminating exception.

### User Scenario 3 - Clean interruption during retry loop (Priority: P2)

A user presses Ctrl+C while the command is sleeping between retries. The process should stop promptly, avoid leaving partial state or leaked
handles behind, and surface an interruption outcome rather than masking it as a file access failure.

**Why this priority**: Retry logic must remain safe and controllable during interactive use.

**How to test**: Trigger a retryable failure, interrupt during the backoff delay, and verify the command exits cleanly without additional
retries or corrupted state.

### User Scenario 4 - No regression outside the Windows-specific failure path (Priority: P3)

A user runs the same workflow on a non-Windows platform, or on Windows without file locking contention. The command should behave exactly as
before except for additional internal resilience and logging.

**Why this priority**: The fix must not introduce regressions in unaffected environments.

**How to test**: Run existing success-path coverage on non-Windows and uncontended Windows paths and verify behavior and outputs remain
compatible.

## Requirements

### Functional Requirements

1. The Windows auto-start path must detect transient file access failures consistent with `[WinError 32]` and classify them as retryable.
2. The implementation must handle retryable file access failures using bounded retry logic rather than failing immediately on the first
   occurrence.
3. The retry loop must stop and return success as soon as the protected operation completes successfully.
4. The retry loop must stop and return failure when the maximum retry budget is exhausted.
5. Errors that are not classified as transient file access conflicts must not be retried and must continue to fail immediately.
6. Each retry attempt must emit diagnostic logging that records the attempt number and why the error was considered retryable.
7. Final failure logging must indicate whether retries were attempted and include the terminal exception details.
8. The implementation must release or avoid retaining file and process handles that could contribute to self-inflicted locking during startup
   and cleanup.
9. If the user interrupts the command during retry delay or retry execution, the command must stop retrying and exit through normal
   interruption handling.
10. If the worktree or target file disappears during retries, the command must fail with the appropriate terminal error rather than retrying
   indefinitely.
11. Existing success-path behavior, command-line interface expectations, and state interactions must remain backward compatible outside the
    retryable failure path.

### Non-Functional Requirements

1. The retry strategy must use a bounded timing policy so failures resolve within a predictable and reasonable time window.
2. The fix must preserve backward compatibility for unaffected platforms and for successful runs that never enter retry handling.
3. User-facing output should remain consistent with existing UX patterns, with added diagnostics only where needed for retry visibility and
   failure analysis.
4. Automated test coverage must include transient retry success, retry exhaustion, interrupt handling, and non-Windows or non-retryable
   behavior.

## Success Criteria

1. In automated tests that simulate transient `[WinError 32]` conditions, the command succeeds after one or more retries without manual
   intervention.
2. In automated tests that simulate persistent `[WinError 32]` conditions, the command fails only after the configured retry budget is
   exhausted and reports that retries were attempted.
3. In automated tests that simulate Ctrl+C during retry delay, the command exits promptly and does not continue retrying after interruption.
4. In automated tests for non-retryable errors and non-Windows execution paths, behavior matches pre-fix expectations except for safe
   internal logging improvements.
5. Review of logs and runtime behavior confirms that handle cleanup and retry diagnostics are sufficient to diagnose intermittent Windows
   worktree failures.

## Edge Cases

- Ctrl+C is received while the process is sleeping between retries.
- The worktree, executable, or a referenced file is deleted between retry attempts.
- The command is executed on a non-Windows platform where the Windows-specific retry classification should not alter behavior.
- State file access or other unrelated file contention occurs and must not be incorrectly classified as the targeted transient startup lock
  unless it matches the intended retryable condition.
