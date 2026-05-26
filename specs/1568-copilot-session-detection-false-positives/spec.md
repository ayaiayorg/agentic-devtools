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

## Clarifications

### Session 2026-05-26

- Q: What Python logging level should the new structured diagnostic records use — `DEBUG`, `INFO`, or `WARNING`? The spec says "structured diagnostics" but does not specify severity. → A: Use `DEBUG`
  for the per-event metadata and total event count (high-volume, detailed), `INFO` for the final decision-path summary record (one per invocation, always useful), and `WARNING` for exception-path
  diagnostics (as already used). This avoids flooding production logs while ensuring decision-path records are always visible at the default `INFO` threshold.

- Q: Should the structured log format be Python stdlib `logging` with `extra` fields (compatible with existing infrastructure), or a separate JSON blob written to stdout? → A: Use Python stdlib
  `logging` with `extra` keyword arguments on each log call. The existing `logger = logging.getLogger(__name__)` is already in place. Structured formatters (e.g., `python-json-logger`) can be attached
  externally without code changes. This maintains consistency with all other modules in the codebase.

- Q: Should the `pr_number` be included in every structured diagnostic record, or only in the decision-path summary? Multiple PRs may be processed in a single pipeline run. → A: Include `pr_number` in
  every structured diagnostic record emitted by the function. This ensures log entries are self-contained and filterable per-PR without requiring correlation by timestamp proximity.

- Q: What identifier should be logged for events — the numeric `id` field, or a combination of `id` and `created_at`? The `IssueEvent` model has `id`, `event`, `created_at`, and `actor_login`. → A:
  Log all available fields from the `IssueEvent` model: `id`, `event`, `created_at`, and `actor_login`. Since Phase 1 is diagnostic, capturing every available attribute maximizes investigative value
  with negligible cost (these are small payloads, typically < 20 events per PR).

- Q: Should a `no-start-events` decision path be distinguished from `no-events`? Currently the code returns `False` both when the event list is empty and when there are events but none are
  `copilot_work_started`. The spec only lists `no-events` for both cases. → A: Keep a single `no-events` decision path for Phase 1, matching the case where `latest_start is None` (covers both truly
  empty payloads and payloads with no `copilot_work_started` events). The total event count log (FR-001) already distinguishes these two sub-cases — a count of 0 means no API events at all, while a
  count > 0 with `no-events` decision means events existed but none were session-start events. A finer split can be introduced in Phase 2 if logs show it's needed.

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
  **Then** logs include event count, per-event metadata (type, id, timestamp,
  actor_login), and decision path `has-terminal`.
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
  `has-terminal`, `active-session`, and a `pr_number` field identifying the PR.
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
  session-related events returned by the upstream API call at `DEBUG` level.
  This count must be emitted before branch selection so operators can compare
  branch outcomes against source data volume. The log record MUST include
  `pr_number` in `extra` for structured filtering.

- **FR-002**: **Event metadata logging** — The detector MUST log all observed
  event records at `DEBUG` level with all available `IssueEvent` fields: `id`,
  `event`, `created_at`, and `actor_login`. The logging output should preserve
  ordering from the source payload so investigators can reconstruct
  sequence-dependent interpretation. Each event log record MUST include
  `pr_number` in `extra`.

- **FR-003**: **Explicit decision-path logging** — The detector MUST emit a
  single canonical decision marker at `INFO` level indicating which branch was
  taken: `exception`, `no-events`, `has-terminal`, or `active-session`. This
  marker must be present exactly once per invocation to support deterministic
  filtering in CI logs. The log record MUST include both `decision_path` and
  `pr_number` in `extra`.

- **FR-004**: **Full fail-closed exception diagnostics** — When the detector
  falls into the exception/fail-closed path, logs MUST include full exception
  details at `WARNING` level, including exception class name, message text, and
  traceback context (via `exc_info=True`). This requirement is necessary to
  separate transport/auth failures from parse or logic failures. The log record
  MUST include `pr_number` in `extra`.

- **FR-005**: **Structured parseable format** — All new diagnostics MUST use
  Python stdlib `logging` with structured `extra` keyword arguments (e.g.,
  `extra={"decision_path": "...", "pr_number": ..., "event_count": ...}`) so
  they can be consumed by structured log formatters (such as
  `python-json-logger`) and post-run analysis scripts without brittle text
  parsing. No additional logging libraries are introduced.

- **NFR-001**: **No behavior changes in Phase 1** — Logging additions MUST NOT
  alter control flow, return values, error handling semantics, or
  timing-sensitive behavior of `is_copilot_session_active`. The function's
  current decision outcomes remain unchanged while observability is added.

- **NFR-002**: **Coverage of all code paths** — Test updates MUST verify that
  each code path (`exception`, `no-events`, `has-terminal`, `active-session`)
  emits the expected structured diagnostics, including required fields defined
  above. Tests MUST assert on the `extra` dict contents of captured log records.

## Affected Files

The expected implementation surface for this phase is limited to:

- `agentic_devtools/cli/ci/pipeline/session_detector.py`
- Existing tests that cover `is_copilot_session_active` under `tests/unit/cli/ci/pipeline/session_detector/`

No other production modules are required for Phase 1 specification compliance.

## Success Criteria

- **SC-001**: In CI and local test runs, 100% of `is_copilot_session_active`
  invocations emit a structured decision-path field (via `extra`) with one of
  the four allowed values.
- **SC-002**: For payload-bearing runs, logs always include total event count
  and per-event metadata (`id`, `event`, `created_at`, `actor_login`), with
  zero missing required fields across validated fixtures.
- **SC-003**: Exception-path tests confirm full exception diagnostics are
  present (class, message, traceback context via `exc_info`) in 100% of
  forced-failure scenarios.
- **SC-004**: Existing functional behavior remains unchanged: all pre-existing
  detector tests continue to pass with identical return-value expectations.
- **SC-005**: Debugging readiness improves for the blocked-PR incident:
  maintainers can identify which branch produced false positives from log
  output alone (filtering by `decision_path` and `pr_number` in structured
  extra fields), without adding temporary instrumentation.

---
*Generated by Copilot SDK (claude-opus-4.6)*
