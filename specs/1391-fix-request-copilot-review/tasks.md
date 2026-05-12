# Tasks: Fix request-copilot-review verification instability

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Test directory scaffolding and prerequisite verification |
| Phase 2: Foundational | Phase 1 | `VerificationResult` dataclass and `_is_debug` helper |
| Phase 3: US-1 & US-2 | Phase 2 | Refactor verify helper with backoff and `users` iteration |
| Phase 4: US-3 | Phase 2 | Surface actionable diagnostics (`AGDT_DEBUG`, stderr) |
| Phase 5: US-4 | Phase 3 | Update `request_copilot_review()` caller, preserve JSON keys |
| Phase 6: US-5 | Phase 2 | Graceful degradation when all responses malformed |
| Phase 7: Polish | Phase 4 | Exports, validation, lint, full test suite |

## Phase 1: Setup

- [ ] T001 Verify test directory structure exists with `__init__.py` files at `tests/unit/cli/github/request_copilot_review/` (FR-001, NFR-005)
- [ ] T002 Verify `run_safe` supports `timeout` kwarg by inspecting `agentic_devtools/cli/subprocess_utils.py` (FR-002, NFR-005)

## Phase 2: Foundational

- [ ] T003 Add `VerificationResult` dataclass to `agentic_devtools/cli/github/request_copilot_review.py` with fields: `verified`, `retries`, `elapsed_seconds`, `degraded`, `diagnostics` (FR-008)
- [ ] T004 Add `_is_debug() -> bool` helper to `agentic_devtools/cli/github/request_copilot_review.py` checking `AGDT_DEBUG` env var for truthy values (FR-009)
- [ ] T005 [P] Write tests for `VerificationResult` dataclass at `tests/unit/cli/github/request_copilot_review/test_verificationresult.py` (FR-008)
- [ ] T006 [P] Write tests for `_is_debug` at `tests/unit/cli/github/request_copilot_review/test__is_debug.py` (FR-009)

## Phase 3: US-1 — Verify bot in users array & US-2 — Retry with exponential backoff

- [ ] T007 [US1] Write failing tests for bot-found-on-first-attempt scenario (`verified=True, retries=0`) at `tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py` (FR-001)
- [ ] T008 [US2] Write failing tests for exponential backoff delays `[2, 4, 8, 16]` and early return on success at `tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py`
  (FR-002, FR-003, FR-004)
- [ ] T009 [impl] [US1] [US2] Refactor the reviewer-requested check helper to return `VerificationResult`, implement exponential backoff
  (base=2s, factor=2×, max retries=4), add `timeout=5` to `run_safe()` calls, iterate `users` array for bot login in
  `agentic_devtools/cli/github/request_copilot_review.py` (FR-001, FR-002, FR-003, FR-004, FR-008, NFR-005)
- [ ] T010 [US2] Write tests for bot-found-on-3rd-attempt, all-5-attempts-fail-well-formed, and timeout handling at
  `tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py` (FR-001, FR-002, FR-003, FR-004)
- [ ] T011 [US1] [US2] Verify all US-1 and US-2 tests pass via `agdt-test-pattern tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py -v` (FR-001, FR-002, FR-003, FR-004)

## Phase 4: US-3 — Surface actionable diagnostics

- [ ] T012 [US3] Write failing tests for `AGDT_DEBUG` response shape output (AC-3.2), HTTP status diagnostics (AC-3.3), and final failure stderr message (AC-3.1) at
  `tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py` (FR-005, FR-009)
- [ ] T013 [impl] [US3] Implement debug output in the reviewer-requested check helper: print sorted keys and array lengths when
  `_is_debug()` is true, include HTTP status and body excerpt on non-200, emit final diagnostic to stderr on failure in
  `agentic_devtools/cli/github/request_copilot_review.py` (FR-005, FR-009)
- [ ] T014 [US3] Write tests asserting `diagnostics` dict contains `lastUsersFound`, `lastTeamsFound`, `wellFormedResponseSeen`, `message` at
  `tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py` (FR-005, FR-006)
- [ ] T015 [US3] Verify all US-3 tests pass via `agdt-test-pattern tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py -v` (FR-005, FR-009)

## Phase 5: US-4 — Preserve backward compatibility with JSON output

- [ ] T016 [US4] Write failing tests asserting JSON result contains `prNumber`, `repo`, `requested`, `reviewer`, `verified`, `retries`, plus new `elapsedSeconds` and conditional `diagnostics` at
  `tests/unit/cli/github/request_copilot_review/test_request_copilot_review.py` (FR-006, FR-007)
- [ ] T017 [US4] Update `request_copilot_review()` in `agentic_devtools/cli/github/request_copilot_review.py`:
  replace inline retry loop with single call to the reviewer-requested check helper, destructure `VerificationResult`,
  add `elapsedSeconds` and `diagnostics` fields to JSON result, preserve all existing keys (FR-006, FR-007)
- [ ] T018 [US4] Write test verifying `diagnostics` key is omitted when `verified=True` and present when `verified=False` at
  `tests/unit/cli/github/request_copilot_review/test_request_copilot_review.py` (FR-006)
- [ ] T019 [US4] Write backward compatibility test: all existing JSON keys preserved, no renames or removals at `tests/unit/cli/github/request_copilot_review/test_request_copilot_review.py` (FR-007)
- [ ] T020 [US4] Update mocks in existing tests to handle `VerificationResult` return type at `tests/unit/cli/github/request_copilot_review/test_request_copilot_review.py` (FR-006, FR-007)
- [ ] T021 [US4] Verify all US-4 tests pass via `agdt-test-pattern tests/unit/cli/github/request_copilot_review/test_request_copilot_review.py -v` (FR-006, FR-007)

## Phase 6: US-5 — Graceful degradation

- [ ] T022 [US5] Write failing tests for degraded mode: all responses malformed → `degraded=True`, mixed responses → `degraded=False` at
  `tests/unit/cli/github/request_copilot_review/test__verify_reviewer_requested.py` (FR-010)
- [ ] T023 [impl] [US5] Implement degraded detection in the reviewer-requested check helper: track `well_formed_response_seen`,
  set `degraded=True` only when no attempt returned valid JSON with `users` key in
  `agentic_devtools/cli/github/request_copilot_review.py` (FR-010)
- [ ] T024 [US5] Write test verifying command exits with code 0 on degradation and state keys are set correctly at `tests/unit/cli/github/request_copilot_review/test_request_copilot_review_command.py`
  (FR-010)
- [ ] T025 [US5] Verify all US-5 tests pass via `agdt-test-pattern tests/unit/cli/github/request_copilot_review/ -v` (FR-010)

## Phase 7: Polish & Cross-Cutting

- [ ] T026 Add `VerificationResult` to `agentic_devtools/cli/github/__init__.py` imports and `__all__`
- [ ] T027 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance (FR-008)
- [ ] T028 Run `ruff check --fix . && ruff format .` for lint and format compliance
- [ ] T029 Run full test suite via `agdt-test` + `agdt-task-wait` to confirm no regressions (FR-001)
- [ ] T030 Run `bash scripts/run-pr-checks.sh` to confirm all CI-blocking checks pass

## Dependencies

```text
T001 → T005, T006, T007, T008, T012, T022
T002 → T009
T003 → T005, T007, T008, T009
T004 → T006, T012, T013
T005, T006 → T009
T007, T008 → T009
T009 → T010, T011, T012, T013, T014, T016, T017, T022, T023
T012 → T013
T013 → T014, T015
T016 → T017
T017 → T018, T019, T020, T021
T022 → T023
T023 → T024, T025
T025 → T026, T027, T028, T029, T030
T029 → T030
```

## FR Traceability Matrix

| FR | Tasks |
|---|---|
| FR-001 (iterate `users` array) | T001, T007, T009, T010, T011, T029 |
| FR-002 (exponential backoff) | T002, T008, T009, T010, T011 |
| FR-003 (max 4 retries, 30s cumulative backoff) | T008, T009, T010, T011 |
| FR-004 (early return on success) | T008, T009, T010, T011 |
| FR-005 (stderr diagnostics on failure) | T012, T013, T014, T015 |
| FR-006 (additive JSON fields) | T014, T016, T017, T018, T020, T021 |
| FR-007 (preserve existing JSON keys) | T016, T017, T019, T020, T021 |
| FR-008 (`VerificationResult` dataclass) | T003, T005, T009, T027 |
| FR-009 (`AGDT_DEBUG` output) | T004, T006, T012, T013, T015 |
| FR-010 (graceful degradation) | T022, T023, T024, T025 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
