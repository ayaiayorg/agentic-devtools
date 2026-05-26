# Tasks: Remove Active Session Precondition from ResolveThreadsAction

## Phase Mapping: Plan → Tasks

Plan phases map 1:1 to the task phases in this document:

- Phase 1 (Setup) → Phase 1: Setup
- Phase 2 (Foundational) → Phase 2: Foundational
- Phase 3 (User Story 1) → Phase 3: User Story 1 — Thread Resolution Proceeds When Session Is Active (P1)
- Phase 4 (User Story 2) → Phase 4: User Story 2 — Remaining Preconditions Are Still Enforced (P1)
- Phase 5 (User Story 3) → Phase 5: User Story 3 — FR-005 in Spec 1559 Updated (P2)

## Phase 1: Setup

- [ ] T001 Read and understand the current `ResolveThreadsAction` implementation in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`
- [ ] T002 Read the existing test suite in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py` (FR-001)
- [ ] T003 Read FR-005, US2 scenario 1, and US3 scenario 2 in `specs/1559-refactor-loop-into-idempotent/spec.md`

## Phase 2: Foundational

- [ ] T004 Verify baseline tests pass by running `agdt-test-pattern tests/unit/cli/ci/pipeline/actions/resolve_threads/ -v` (FR-001)

## Phase 3: User Story 1 — Thread Resolution Proceeds When Session Is Active (P1)

- [ ] T005 [US1] RED: Rename `test_skip_when_active_session` to `test_execute_when_active_session` and assert `ActionDecision.EXECUTE` with `ci_status="passing"`, `copilot_review_pending=False`, and
  `unresolved_threads>0` when `active_session=True` (FR-001) in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`
- [ ] T006 [US1] RED: Add `test_no_active_session_key_in_preconditions` asserting `"no_active_session"` key is absent from `result.preconditions` for any `evaluate()` call in
  `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py` (FR-001)
- [ ] T007 [US1] GREEN: Remove lines 33–41 (the `no_active_session` precondition block) from `evaluate()` in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py` (implements FR-001)
- [ ] T008 [US1] GREEN: Update class docstring to remove "No active Copilot coding session" from Preconditions list, keeping "No pending Copilot review on HEAD" and "Unresolved threads exist from
  prior commits" (FR-006) in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`
- [ ] T009 [US1] Verify `test_execute_when_active_session` and `test_no_active_session_key_in_preconditions` pass by running `agdt-test-pattern tests/unit/cli/ci/pipeline/actions/resolve_threads/ -v` (FR-001)

## Phase 4: User Story 2 — Remaining Preconditions Are Still Enforced (P1)

- [ ] T010 [P] [US2] Add `test_skip_when_active_session_and_ci_failing` asserting `ActionDecision.SKIP` with `"ci_passing": False` when `active_session=True` and `ci_status="failing"` (FR-002) in
  `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`
- [ ] T011 [P] [US2] Add `test_skip_when_active_session_and_pending_review` asserting `ActionDecision.SKIP` with `"no_pending_review": False` when `active_session=True` and
  `copilot_review_pending=True` (FR-003) in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`
- [ ] T012 [P] [US2] Add `test_skip_when_active_session_and_no_threads` asserting `ActionDecision.SKIP` with `"has_unresolved_threads": False` when `active_session=True` and `unresolved_threads=0`
  (FR-004) in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`
- [ ] T013 [US2] Verify all remaining-precondition tests pass by running `agdt-test-pattern tests/unit/cli/ci/pipeline/actions/resolve_threads/ -v` (FR-002, FR-003, FR-004)

## Phase 5: User Story 3 — FR-005 in Spec 1559 Updated (P2)

- [ ] T014 [US3] Reword FR-005 in `specs/1559-refactor-loop-into-idempotent/spec.md` (line 246) to state only squash and dispatch-repair MUST NOT execute when session active; thread resolution is not
  session-gated (FR-007)
- [ ] T015 [US3] Update User Story 2 acceptance scenario 1 (lines 93–94) in `specs/1559-refactor-loop-into-idempotent/spec.md` to remove "resolve-threads" from skipped actions list, leaving only
  "dispatch-repair and squash" (FR-007)
- [ ] T016 [US3] Rewrite User Story 3 acceptance scenario 2 (line 121) in `specs/1559-refactor-loop-into-idempotent/spec.md` to state thread resolution proceeds regardless of session state (FR-007)

## Phase 6: User Story 4 — Tests Updated for Coverage (P2)

- [ ] T017 [US4] Add `test_skip_when_no_prior_reviews_race_condition` asserting `ActionDecision.SKIP` in `execute()` when `prior_reviews` is empty (snapshot with `unresolved_threads>0` but no matching
  reviews) to cover the race-condition branch (FR-005) in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py`
- [ ] T018 [US4] Add `test_execute_handles_exception_in_finalize` asserting `ActionDecision.FAILED` when `provider.finalize_post_repair` raises an exception to cover the exception handler branch in
  `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_resolvethreadsaction.py` (FR-005)
- [ ] T019 [US4] Run coverage check:

  ```bash
  agdt-test-pattern tests/unit/cli/ci/pipeline/actions/resolve_threads/ -o addopts= --cov=agentic_devtools.cli.ci.pipeline.actions.resolve_threads --cov-report=term-missing --cov-fail-under=100
  ```

## Phase 7: Polish & Cross-Cutting

- [ ] T020 Run full suite with `agdt-test` and `agdt-task-wait` to verify no regressions (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)
- [ ] T021 Run `bash scripts/run-pr-checks.sh` to verify all PR checks pass (lint, format, markdownlint, mypy) (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)
- [ ] T022 Verify squash and dispatch-repair coverage files are NOT modified by inspecting `git diff --name-only` (FR-007)

## Dependencies

```text
T004 → T005, T006
T005, T006 → T007, T008
T007, T008 → T009
T009 → T010, T011, T012
T010, T011, T012 → T013
T013 → T017, T018
T009 → T014, T015, T016
T017, T018 → T019
T019 → T020
T016 → T020
T020 → T021
T021 → T022
```

## FR Traceability Matrix

| FR | Task(s) |
| --- | --- |
| FR-001 | T005, T007 |
| FR-002 | T010 |
| FR-003 | T011 |
| FR-004 | T012 |
| FR-005 | T017 |
| FR-006 | T008 |
| FR-007 | T014, T015, T016 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
