# Tasks: Enhanced Diagnostic Logging for Copilot Session Detection (Phase 1)

**Issue**: [#1568](https://github.com/ayaiayorg/agentic-devtools/issues/1568)

---

## Phase Mapping: Plan → Tasks

Phases are 1:1 aligned with `plan.md` (Setup, Foundational, User Story 1, User Story 2, User Story 3, Polish & Cross-Cutting).

---

## Phase 1: Setup

- [ ] T001 Review existing `IssueEvent` model fields to confirm `id`, `event`, `created_at`, `actor_login` availability in `agentic_devtools/cli/ci/models.py`

---

## Phase 2: Foundational — Production Logging Implementation

- [ ] T002 [US1] Add FR-001 total event count `DEBUG` log with `extra={"event_count": ..., "pr_number": ...}` immediately after successful API call in
  `agentic_devtools/cli/ci/pipeline/session_detector.py`
- [ ] T003 [US1] Add FR-002 per-event metadata `DEBUG` log within the existing `latest_start` scan loop, guarded by `logger.isEnabledFor(logging.DEBUG)`, emitting `event_id`, `event_type`,
  `created_at`, `actor_login`, `pr_number` in `extra` in `agentic_devtools/cli/ci/pipeline/session_detector.py`
- [ ] T004 [US2] Add FR-003 decision-path `INFO` log with `extra={"decision_path": "no-events", "pr_number": ...}` to the `latest_start is None` branch in
  `agentic_devtools/cli/ci/pipeline/session_detector.py`
- [ ] T005 [US2] Add FR-003 decision-path `INFO` log with `extra={"decision_path": "has-terminal", "pr_number": ...}` to the `has_terminal` branch in
  `agentic_devtools/cli/ci/pipeline/session_detector.py`
- [ ] T006 [US2] Add FR-003 decision-path `INFO` log with `extra={"decision_path": "active-session", "pr_number": ...}` to the active-session branch in
  `agentic_devtools/cli/ci/pipeline/session_detector.py`
- [ ] T007 [US3] Update FR-004 exception `WARNING` log to include `exc_info=True` and `extra={"decision_path": "exception", "pr_number": ...}` in the `except` block in
  `agentic_devtools/cli/ci/pipeline/session_detector.py`
- [ ] T008 [US2] Verify FR-005 structured parseable format compliance — confirm all new log calls use stdlib `logging` with `extra` kwargs (no new libraries), review final state of
  `agentic_devtools/cli/ci/pipeline/session_detector.py`

---

## Phase 3: User Story 1 — DevOps Debugging Signal (Tests)

- [ ] T009 [US1] Add `caplog` fixture with `DEBUG` level to `test_no_events_returns_false` and assert FR-001 `event_count=0` and FR-003 `decision_path="no-events"` in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`
- [ ] T010 [US1] Add `caplog` assertions to `test_started_with_finished_returns_false` verifying FR-001 event count, FR-002 per-event metadata fields (`event_id`, `event_type`, `created_at`,
  `actor_login`), and FR-003 `decision_path="has-terminal"` in `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`
- [ ] T011 [US1] Add `caplog` assertions to `test_started_without_terminal_returns_true` verifying FR-001 event count, FR-002 per-event metadata, and FR-003 `decision_path="active-session"` in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`
- [ ] T012 [P] [US1] Add `caplog` assertions to `test_started_with_failure_returns_false` verifying FR-002 per-event metadata and FR-003 `decision_path="has-terminal"` in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`
- [ ] T013 [P] [US1] Add `caplog` assertions to `test_multiple_sessions_latest_active` and `test_multiple_sessions_latest_finished` verifying FR-001 event count and FR-002 metadata ordering in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`
- [ ] T014 [US1] Add new test with non-empty `actor_login` fixture to confirm FR-002 `actor_login` field propagation in `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`

---

## Phase 4: User Story 2 — Pipeline Triage Speed (Tests)

- [ ] T015 [US2] Add test asserting FR-005 structured format — every `LogRecord` from a detector invocation has `pr_number` attribute and decision-path records have `decision_path` attribute with
  allowed values in `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`
- [ ] T016 [US2] Add parametrized test covering all four decision paths (`no-events`, `has-terminal`, `active-session`, `exception`) confirming FR-003 exactly one `INFO`-level record with
  `decision_path` in `extra` per invocation in `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`

---

## Phase 5: User Story 3 — On-Call Incident Investigation (Tests)

- [ ] T017 [US3] Update `test_api_failure_returns_true` to assert FR-004 `WARNING` log with `exc_info` set, `decision_path="exception"`, and `pr_number` in `extra` in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`
- [ ] T018 [US3] Add new test for authentication/authorization exception (e.g., `PermissionError`) confirming FR-004 exception diagnostics distinguish auth failures via exception class name in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py`

---

## Phase 6: Polish & Cross-Cutting

- [ ] T019 [US1] Run focused tests via `agdt-test-pattern tests/unit/cli/ci/pipeline/session_detector/ -v` and fix any FR-001/FR-002/FR-003-related failures
- [ ] T020 [US2] Run full test suite via `agdt-test` + `agdt-task-wait` ensuring FR-005 and `session_detector.py` coverage expectations are met
- [ ] T021 [US2] Run `bash scripts/run-pr-checks.sh` to validate ruff, mypy, markdownlint, and full CI parity for FR-005 structured logging changes
- [ ] T022 [US3] Verify NFR-001 compliance — confirm all existing tests pass with unchanged return-value assertions (no behavior changes)

---

## Dependency Graph

```text
T001 → T002 → T003 → T004, T005, T006, T007 → T008
T008 → T009, T010, T011, T012, T013, T014, T015, T016, T017, T018
T009..T018 → T019 → T020 → T021 → T022
```

## Task-to-FR Traceability

| FR | Tasks |
| --- | --- |
| FR-001 | T002, T009, T010, T011, T013 |
| FR-002 | T003, T010, T011, T012, T013, T014 |
| FR-003 | T004, T005, T006, T009, T010, T011, T015, T016 |
| FR-004 | T007, T017, T018 |
| FR-005 | T008, T015 |
| NFR-001 | T022 |
| NFR-002 | T009–T018 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
