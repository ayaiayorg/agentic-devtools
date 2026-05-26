# Implementation Plan: Enhanced Diagnostic Logging for Copilot Session Detection (Phase 1)

**Issue**: [#1568](https://github.com/ayaiayorg/agentic-devtools/issues/1568)
**Branch**: `speckit/1568/phase-3-plan`

## Technical Context

- **Language**: Python 3.10+ with `from __future__ import annotations`
- **Logging**: Python stdlib `logging` via `logger = logging.getLogger(__name__)` (already in place)
- **Target file**: `agentic_devtools/cli/ci/pipeline/session_detector.py` (79 lines)
- **Test file**: `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py` (68 lines)
- **Data model**: `IssueEvent` dataclass with fields `id`, `event`, `created_at`, `actor_login`
- **Constraint**: Zero behavior changes — same return values, same control flow, same error handling

## Research Summary

Key decisions:

1. Use `extra={}` kwargs on stdlib `logging` calls (no new dependencies)
2. `DEBUG` for high-volume event metadata, `INFO` for decision-path summary, `WARNING` for exceptions
3. Test assertions use `caplog` fixture inspecting `LogRecord` attributes (e.g., `record.decision_path`, `record.event_count`)

## Design Overview

The implementation adds structured logging instrumentation at four points in the existing function:

```text
is_copilot_session_active(provider, pr_number)
│
├─ [1] try: events = provider.list_pr_issue_events(pr_number)
│   └─ except: WARNING log with exc_info + extra{decision_path, pr_number} → return True
│
├─ [2] DEBUG log: total event count + extra{event_count, pr_number}
│
├─ [3] DEBUG log (loop): per-event metadata + extra{event_id, event_type, created_at, actor_login, pr_number}
│
├─ [4a] if latest_start is None: INFO log + extra{decision_path="no-events", pr_number} → return False
│
├─ [4b] if has_terminal: INFO log + extra{decision_path="has-terminal", pr_number} → return False
│
└─ [4c] else: INFO log + extra{decision_path="active-session", pr_number} → return True
```

No new production files, classes, or imports are introduced. Test updates (Phase 2) add a `logging` import for `caplog` level configuration.

## Implementation Phases

### Phase 1: Add Structured Logging (Production Code)

**Deliverable**: Updated `session_detector.py` with all FR-001 through FR-004 logging.
FR-005 (structured parseable format) is implicitly satisfied — every logging call uses `extra={}` kwargs.

**Tasks**:

1. Add FR-001 (Copilot session event count log) — `DEBUG` level immediately after the `try` block succeeds, before any iteration:

   ```python
   logger.debug(
       "PR #%d: Received %d Copilot session events",
       pr_number, len(events),
       extra={"event_count": len(events), "pr_number": pr_number},
   )
   ```

2. Add FR-002 (per-event metadata) — `DEBUG` level inside a loop over `events`:

   ```python
   for idx, event in enumerate(events):
       logger.debug(
           "PR #%d: Event[%d] type=%s id=%d created_at=%s actor=%s",
           pr_number, idx, event.event, event.id, event.created_at, event.actor_login,
           extra={
               "pr_number": pr_number,
               "event_id": event.id,
               "event_type": event.event,
               "created_at": event.created_at,
               "actor_login": event.actor_login,
           },
       )
   ```

3. Add FR-003 (decision-path markers) — Replace existing `logger.info` calls with structured equivalents containing `extra={"decision_path": "...", "pr_number": ...}` for each of the three
   non-exception branches.

4. Update FR-004 (exception diagnostics) — Enhance the existing `logger.warning` in the `except` block to include `exc_info=True` and `extra={"decision_path": "exception", "pr_number": pr_number}`.

### Phase 2: Update Tests

**Deliverable**: Existing return-value and behavior assertions remain in place; each test is updated to also assert the expected structured log fields emitted by the new logging calls.

**Tasks**:

1. Add `caplog` fixture to each existing test method (pytest's built-in log capture).
2. In tests that assert per-event `DEBUG` logs, raise the capture level for the target logger with
   `caplog.at_level(logging.DEBUG, logger="agentic_devtools.cli.ci.pipeline.session_detector")`
   (or equivalent `caplog.set_level(...)`) before exercising the code under test.
3. For each test, assert the expected `decision_path` value appears as an attribute on the captured `LogRecord` objects (e.g., `record.decision_path`).
4. For payload-bearing tests, assert `event_count` and per-event fields (`event_id`, `event_type`, `created_at`, `actor_login`) are present as `LogRecord` attributes
   (e.g., `record.event_count`, `record.event_id`).
5. For the exception test, assert `exc_info` is set and `decision_path` is `"exception"`.
6. Add a dedicated test for `actor_login` field presence (the existing `IssueEvent` fixtures use the default empty string — add a fixture with a non-empty `actor_login` to confirm it propagates).

### Phase 3: Validate

**Deliverable**: Full test suite passes, coverage maintained at 100% for the target file.

**Tasks**:

1. Run `agdt-test-pattern tests/unit/cli/ci/pipeline/session_detector/ -v` for focused validation
2. Run `agdt-test` + `agdt-task-wait` for full coverage/CI parity
3. Run `bash scripts/run-pr-checks.sh` for full CI validation
4. Verify no ruff/mypy/markdownlint issues

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Logging changes inadvertently alter control flow | Low | High | NFR-001 enforced by keeping all existing tests with unchanged return-value assertions |
| `extra` dict keys conflict with stdlib LogRecord attrs | Low | Medium | Use unique prefixes (`event_id` not `id`); verify no collision with reserved LogRecord attributes |
| Performance impact from per-event DEBUG logging | Very Low | Low | DEBUG-level is typically disabled in production; event payloads are small (< 20 events) |
| Test fragility from asserting on log message text | Medium | Low | Assert on `LogRecord` attributes (e.g., `record.decision_path`), not message strings |

## Dependencies

- **Internal**: `IssueEvent` dataclass (stable, frozen, no changes needed)
- **Internal**: `CIPlatformProvider.list_pr_issue_events` (no interface changes)
- **External**: None — stdlib `logging` only, no new packages

---
*Generated by Copilot SDK (claude-opus-4.6)*
