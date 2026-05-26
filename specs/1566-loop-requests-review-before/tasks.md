# Tasks: Gate Review Requests on Unresolved PR Comment Threads

**Feature Branch**: `speckit/1566/phase-2-clarify`
**Source Issue**: [#1566](https://github.com/ayaiayorg/agentic-devtools/issues/1566)

---

## Phase 1: Setup

- [ ] T001 Create test directory `tests/unit/cli/ci/github_provider/test_count_unresolved_review_threads.py` with `__init__.py` files
- [ ] T002 Create test file `tests/unit/cli/ci/orchestrator/test__request_copilot_review_if_needed_unresolved_gate.py` with `__init__.py` files

---

## Phase 2: Foundational — Provider Method

- [ ] T003 Write failing tests for `count_unresolved_review_threads` — zero threads returns 0, all resolved returns 0, mix returns correct count, pagination accumulates, API failure raises exception —
  in `tests/unit/cli/ci/github_provider/test_count_unresolved_review_threads.py` (FR-007: counts ALL threads regardless of author)
- [ ] T004 Add abstract method `count_unresolved_review_threads(self, pr_number: int) -> int` to `CIPlatformProvider` in `agentic_devtools/cli/ci/provider.py` (NFR-001: single fetch interface)
- [ ] T005 Implement `count_unresolved_review_threads` on `GitHubActionsProvider` in `agentic_devtools/cli/ci/github_provider.py` — reuse `_REVIEW_THREADS_QUERY`, paginate, count thread nodes with
  `isResolved=False`, decorate with `@retry_with_backoff()` (NFR-003: no additional timeout semantics)
- [ ] T006 Verify tests from T003 pass (GREEN) for the new provider method

---

## Phase 3: User Story 1 & 3 — Gate Logic (P1)

### Tests

- [ ] T007 [US1] Write failing tests: `unresolved_threads=3` → returns `"awaiting_thread_resolution"` and does NOT call `provider.request_reviewer()` (FR-002), `unresolved_threads=0` → proceeds to
  existing logic, in `tests/unit/cli/ci/orchestrator/test__request_copilot_review_if_needed_unresolved_gate.py`
- [ ] T008 [US3] Write failing tests verifying gate applies identically on all 3 paths: draft-publish (Step 7a), CI-completion, no-effective-review (Step 7b) — each blocks when unresolved threads > 0
  (FR-005)

### Implementation

- [ ] T009 [US1] Add `unresolved_threads: int` parameter to `_request_copilot_review_if_needed` signature in `agentic_devtools/cli/ci/orchestrator.py` (FR-001: first precondition before
  `_get_copilot_review_request_skip_reason`)
- [ ] T010 [US1] Implement gate check inside `_request_copilot_review_if_needed`: if `unresolved_threads != 0` return `"awaiting_thread_resolution"` with logging (FR-003: distinct decision value)
- [ ] T011 [US3] Add `provider.count_unresolved_review_threads(pr_number)` call early in `run_ai_pr_loop` after PR metadata resolution, store result in local variable (FR-001, NFR-001: fetched once,
  passed as parameter)
- [ ] T012 [US3] Pass `unresolved_threads` parameter to all 3 call sites of `_request_copilot_review_if_needed` in `agentic_devtools/cli/ci/orchestrator.py` (FR-005: consistent across all paths)
- [ ] T013 [US1] Verify T007 and T008 tests pass (GREEN)

### Existing Test Updates

- [ ] T014 [US1] [P] Update existing tests in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop.py` to mock `count_unresolved_review_threads` returning 0 (preserve existing behavior)
- [ ] T015 [US1] [P] Update existing tests in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_ready.py` to mock `count_unresolved_review_threads` returning 0
- [ ] T016 [US1] [P] Update existing tests in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_no_issue.py` to mock `count_unresolved_review_threads` returning 0
- [ ] T017 [US1] [P] Update existing tests in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_blocked.py` to mock `count_unresolved_review_threads` returning 0
- [ ] T018 [US1] [P] Update existing tests in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_actionable_checks.py` to mock `count_unresolved_review_threads` returning 0
- [ ] T019 [US1] [P] Update existing tests in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_malformed.py` to mock `count_unresolved_review_threads` returning 0
- [ ] T020 [US1] [P] Update existing tests in `tests/unit/cli/ci/orchestrator/test_squash_wait_flow.py` to mock `count_unresolved_review_threads` returning 0
- [ ] T021 [US1] [P] Update `tests/unit/cli/ci/provider/test_ciplatformprovider.py` to include `count_unresolved_review_threads` in concrete test implementation

---

## Phase 4: User Story 2 — Decision Summary (P2)

### Tests

- [ ] T022 [US2] Write failing tests: decision summary contains `"unresolved_threads": N` when gate blocks, `"unresolved_threads": 0` when gate passes (FR-004), in
  `tests/unit/cli/ci/orchestrator/test__emit_decision_summary.py` or new test file

### Implementation

- [ ] T023 [US2] Add `"unresolved_threads"` field to all decision summary dicts that involve review-request paths in `agentic_devtools/cli/ci/orchestrator.py` — always present as integer, `0` when no
  threads (FR-004, NFR-002: backward-compatible additive field)
- [ ] T024 [US2] Verify T022 tests pass (GREEN)

---

## Phase 5: User Story 4 — Graceful Degradation (P2)

### Tests

- [ ] T025 [US4] Write failing tests: `count_unresolved_review_threads` raises exception → orchestrator sets `unresolved_count = -1`, adds `"unresolved_threads_error": true` to summary, blocks review
  request (FR-006), returns EXIT_SUCCESS (FR-008)
- [ ] T026 [US4] Write failing test: various exception types (network timeout, 500, rate limit) all result in fail-closed behavior

### Implementation

- [ ] T027 [US4] Wrap `provider.count_unresolved_review_threads()` call in try/except in `run_ai_pr_loop` — on exception set `unresolved_count = -1`, `unresolved_threads_error = True`, log warning
  (FR-006)
- [ ] T028 [US4] Include `"unresolved_threads_error": true` in decision summary when API call failed (FR-004, FR-006: sentinel value `-1` with error flag)
- [ ] T029 [US4] Ensure orchestrator returns `EXIT_SUCCESS` (exit code 0) when gate blocks due to API failure (FR-008: loop retries on next trigger)
- [ ] T030 [US4] Verify T025 and T026 tests pass (GREEN)

---

## Phase 6: Polish & Cross-Cutting

### Regression Test

- [ ] T031 Add PR #1545 regression test simulating the exact timeline (2+ unresolved threads, review request attempted) — verify gate blocks in
  `tests/unit/cli/ci/orchestrator/test__request_copilot_review_if_needed_unresolved_gate.py` (SC-003)

### Coverage & Validation

- [ ] T032 Run `agdt-test` full test suite — verify all tests pass and 100% coverage on new code (NFR-004, SC-005)
- [ ] T033 Run `bash scripts/run-pr-checks.sh` — verify ruff, mypy, markdownlint, and all CI checks pass
- [ ] T034 Run `python scripts/validate_test_structure.py` — verify 1:1:1 test structure compliance

---

## Dependency Graph

```text
T001, T002 (parallel setup)
  └─► T003 → T004 → T005 → T006
                              └─► T007, T008 (parallel test writing)
                                    └─► T009 → T010 → T011 → T012 → T013
                                          └─► T014–T021 (parallel mock updates)
                                                └─► T022 → T023 → T024
                                                      └─► T025, T026 → T027 → T028 → T029 → T030
                                                                                              └─► T031 → T032 → T033 → T034
```

---

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T009, T011, T012 |
| FR-002 | T007, T010 |
| FR-003 | T010 |
| FR-004 | T022, T023, T028 |
| FR-005 | T008, T012 |
| FR-006 | T025, T027, T028 |
| FR-007 | T003, T005 |
| FR-008 | T025, T029 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
