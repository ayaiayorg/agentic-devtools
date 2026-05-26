# Spec: Enhanced Diagnostic Logging for Copilot Session Detection False Positives (Phase 1)

**Feature Branch**: `copilot/create-phase-1-specification-issue-1568`
**Created**: 2026-05-26
**Status**: Draft
**Input**: User description: "Bug: Copilot active session detection always returns True — blocks resolve_threads, dispatch_repair, and squash on all open PRs"
**Source Issue**: #1568 (<https://github.com/ayaiayorg/agentic-devtools/issues/1568>)

---

## Problem Statement

The `is_copilot_session_active` helper in
`agentic_devtools/cli/ci/pipeline/session_detector.py` is currently producing
false positives, returning `True` for pull requests that do not have an active
Copilot session. In production this behavior has blocked at least 8 open PRs
from progressing through the CI pipeline because downstream steps treat the
session as already active and stop normal automation.

Phase 1 intentionally focuses on observability, not behavior changes. The
immediate goal is to generate enough high-fidelity diagnostic evidence from
real workflow runs to isolate why the detector enters the active path when no
active session should exist. Without this logging foundation, code fixes in
later phases would be speculative and risky.

## Scope

This specification covers logging-only changes for Phase 1. It does **not**
change decision logic, API contracts, return values, or control flow in
`is_copilot_session_active`. It also does not include remediation logic,
heuristics, or fallback rule updates. Any behavior fix is deferred to a later
phase after log evidence confirms the true failure mechanism.

## User Scenarios & Testing

### User Story 1 — DevOps debugging signal (Priority: P1)

As a DevOps engineer, I want complete event diagnostics emitted whenever
Copilot session detection runs, so that I can determine whether false
positives come from malformed API payloads, stale events, or incorrect event
interpretation.

**Acceptance Scenarios**

- **Given** `is_copilot_session_active` is invoked with an empty event payload,
  **When** the detector runs,
  **Then** logs include event count of 0, no event metadata entries, and
  decision path `no-events`.
- **Given** `is_copilot_session_active` is invoked with an event payload
  containing a `copilot_work_started` event followed by a terminal event
  (finished or failure) with a higher ID,
  **When** the detector runs,
  **Then** logs include event count, per-event metadata (type, id, timestamp),
  and decision path `has-terminal`.
- **Given** `is_copilot_session_active` is invoked with an active-like event
  payload,
  **When** the detector runs,
  **Then** logs include event count, per-event metadata, and decision path
  `active-session`.

### User Story 2 — Pipeline triage speed (Priority: P1)

As a pipeline maintainer, I want structured machine-parseable logs for every
detector branch, so that I can quickly filter and correlate failures across
multiple blocked PR runs without manual log interpretation.

**Acceptance Scenarios**

- **Given** any detector invocation completes,
  **When** the emitted log records are collected,
  **Then** each record can be parsed as structured key-value output containing
  a stable `decision_path` field with one of: `exception`, `no-events`,
  `has-terminal`, `active-session`.
- **Given** multiple PR runs produce false positives,
  **When** a maintainer filters CI logs by the `decision_path` field,
  **Then** all matching entries are returned without brittle text parsing.

### User Story 3 — On-call incident investigation (Priority: P2)

As a member of the on-call rotation, I want full exception diagnostics in the
fail-closed path, so that I can distinguish genuine API/transport failures from
logic-related false positives during incident response.

**Acceptance Scenarios**

- **Given** the detector encounters an API transport error (e.g., timeout,
  connection refused) during the upstream `list_pr_issue_events` call,
  **When** it falls into the exception/fail-closed path,
  **Then** logs include exception class name, message text, and traceback
  context.
- **Given** the detector encounters an API authentication or authorization
  error during the upstream `list_pr_issue_events` call,
  **When** it falls into the exception/fail-closed path,
  **Then** logs include the same exception diagnostics, allowing operators to
  distinguish auth failures from connectivity issues.

> **Note:** The current exception boundary only covers the upstream
> `provider.list_pr_issue_events(pr_number)` call. Downstream parsing or
> iteration errors are not caught by the existing try/except and would
> propagate as unhandled exceptions. Expanding the exception boundary is
> explicitly out of scope for Phase 1 (see NFR-001).

## Requirements

The following requirements define Phase 1 behavior and are intentionally
limited to diagnostic logging.

- **FR-001**: **Total event count logging** — Each invocation of
  `is_copilot_session_active` MUST log the total number of Copilot
  session-related events returned by the upstream API call. This count must be
  emitted before branch selection so operators can compare branch outcomes
  against source data volume.

- **FR-002**: **Event metadata logging** — The detector MUST log all observed
  event records with at least event type, event identifier, and event timestamp
  fields. The logging output should preserve ordering from the source payload
  so investigators can reconstruct sequence-dependent interpretation.

- **FR-003**: **Explicit decision-path logging** — The detector MUST emit a
  single canonical decision marker indicating which branch was taken:
  `exception`, `no-events`, `has-terminal`, or `active-session`. This marker
  must be present exactly once per invocation to support deterministic
  filtering in CI logs.

- **FR-004**: **Full fail-closed exception diagnostics** — When the detector
  falls into the exception/fail-closed path, logs MUST include full exception
  details, including exception class name, message text, and traceback context.
  This requirement is necessary to separate transport/auth failures from parse
  or logic failures.

- **FR-005**: **Structured parseable format** — All new diagnostics MUST use a
  structured log format (for example stable key-value or JSON-style fields) so
  they can be consumed by log processing and post-run analysis scripts without
  brittle text parsing.

- **NFR-001**: **No behavior changes in Phase 1** — Logging additions MUST NOT
  alter control flow, return values, error handling semantics, or
  timing-sensitive behavior of `is_copilot_session_active`. The function's
  current decision outcomes remain unchanged while observability is added.

- **NFR-002**: **Coverage of all code paths** — Test updates MUST verify that
  each code path (`exception`, `no-events`, `has-terminal`, `active-session`)
  emits the expected structured diagnostics, including required fields defined
  above.

## Affected Files

The expected implementation surface for this phase is limited to:

- `agentic_devtools/cli/ci/pipeline/session_detector.py`
- Existing tests that cover `is_copilot_session_active` under `tests/unit/cli/ci/pipeline/...`

No other production modules are required for Phase 1 specification compliance.

## Success Criteria

- **SC-001**: In CI and local test runs, 100% of `is_copilot_session_active`
  invocations emit a structured decision-path field with one of the four
  allowed values.
- **SC-002**: For payload-bearing runs, logs always include total event count
  and per-event metadata (type, id, timestamp), with zero missing required
  fields across validated fixtures.
- **SC-003**: Exception-path tests confirm full exception diagnostics are
  present (class, message, traceback context) in 100% of forced-failure
  scenarios.
- **SC-004**: Existing functional behavior remains unchanged: all pre-existing
  detector tests continue to pass with identical return-value expectations.
- **SC-005**: Debugging readiness improves for the blocked-PR incident:
  maintainers can identify which branch produced false positives from log
  output alone, without adding temporary instrumentation.
