# Tasks: Runner Human-in-the-Loop Pause Detection

## Phase Mapping: Plan → Tasks

Plan and task phases align 1:1 — no mapping table required.

## Phase 1: Setup

- [ ] T001 Create test file scaffold `tests/unit/orchestration/runner/test__is_workflow_paused.py` with `__init__.py` as needed [FR-008]

## Phase 2: Foundational

- [ ] T002 Write failing happy-path and edge-case tests for `_is_workflow_paused` helper covering:
  - status="active" → True
  - status missing → True
  - status="" → True
  - status="completed" → False
  - None input → TypeError
  - non-dict input → TypeError (`tests/unit/orchestration/runner/test__is_workflow_paused.py`) [FR-008]
- [ ] T003 Implement `_is_workflow_paused(result: dict) -> bool` helper in `agentic_devtools/orchestration/runner.py` that:
  - returns `True` when `result.get("status") != "completed"`
  - raises `TypeError` for None/non-dict inputs [FR-001, FR-008]
- [ ] T004 Verify `_is_workflow_paused` tests pass (GREEN phase) [FR-008]

## Phase 3: User Story 1 — Fresh Workflow Pauses at Planning Gate

- [ ] T005 [US1] Write failing happy-path test `test_fresh_run_pauses_at_gate_with_checkpointer` in
  `tests/unit/orchestration/runner/test_run_langchain_workflow.py` — invoke returns
  `{"step": "planning", "status": "active"}` → stderr contains pause message, stdout does NOT contain
  "completed", exit 0 [FR-001, FR-002, FR-006, FR-007]
- [ ] T006 [US1] Write failing test `test_fresh_invocation_exits_1_when_invoke_returns_none` and assert fresh
  invocation state inspection is evaluated before completion reporting — invoke returns `None` → stderr contains
  "unexpected result type", exit 1 [FR-001]
- [ ] T007 [US1] Integrate state inspection into fresh invocation path in `agentic_devtools/orchestration/runner.py`
  (completion-reporting block immediately after `compiled.invoke(...)` in the fresh invocation path): add
  None/type guard → `sys.exit(1)`, call `_is_workflow_paused(result)` → `_print_pause_message`, else print
  completion [FR-001, FR-002, FR-003, FR-007]
- [ ] T008 [US1] Verify fresh-path tests pass and existing `test_fresh_invocation_calls_graph_invoke` still passes [FR-005]

## Phase 4: User Story 2 — Resumed Workflow Uses Same Pause Detection

- [ ] T009 [US2] Write failing happy-path test `test_resume_pauses_when_status_not_completed` in
  `tests/unit/orchestration/runner/test_run_langchain_workflow.py` — resume invoke returns
  `{"step": "commit", "status": "active"}` → stderr contains pause message, exit 0 [FR-004, FR-006]
- [ ] T010 [US2] Write failing happy-path test `test_resume_completes_when_status_completed` — resume invoke returns
  `{"step": "completion", "status": "completed"}` → stdout contains "Workflow completed" [FR-004]
- [ ] T011 [US2] Integrate same state inspection into resume path in `agentic_devtools/orchestration/runner.py` — both paths call `_is_workflow_paused` identically [FR-004]
- [ ] T012 [US2] Verify resume-path tests pass and existing `test_resume_with_existing_checkpoint_invokes_command` still passes [FR-005]

## Phase 5: User Story 3 — Workflow Runs to True Completion

- [ ] T013 [US3] Write happy-path test `test_true_completion_prints_completed_message` verifying invoke returns
  `{"step": "completion", "status": "completed"}` → stdout contains
  `[langchain] Workflow completed: step=completion, status=completed` [FR-003]
- [ ] T014 [US3] Write test `test_intermediate_non_gate_step_treated_as_pause` verifying invoke returns
  `{"step": "initialization", "status": "active"}` → pause message printed (conservative approach)
  [FR-002]
- [ ] T015 [US3] Verify all completion-path tests pass [FR-003]

## Phase 6: User Story 4 — Regression Test Coverage

- [ ] T016 [P] [US4] Add regression test verifying `GraphInterrupt` exception path still calls `_print_pause_message` (backward compat) in
  `tests/unit/orchestration/runner/test_run_langchain_workflow.py` [FR-005]
- [ ] T017 [P] [US4] Add regression test asserting `_is_workflow_paused` is invoked and that a non-completed
  state prints the pause message while suppressing completion output [FR-001]
- [ ] T018 [US4] Run full test suite with `agdt-test` and verify all 2000+ tests pass [FR-005]
- [ ] T019 [US4] Run `bash scripts/targeted-checks.sh` and verify 100% branch coverage on `runner.py` [FR-005]

## Phase 7: User Story 5 — CLI Help Documents Pause/Resume Behavior

- [ ] T020 [US5] Locate argparse setup for `agdt-initiate-work-on-jira-issue-workflow` in
  `agentic_devtools/cli/workflows/commands.py` and add epilog/description text explaining the
  pause/resume lifecycle and the `--resume` flag purpose
- [ ] T021 [US5] Confirm `agdt-initiate-work-on-jira-issue-workflow --help` output includes pause/resume behavior description

## Phase 8: Polish & Cross-Cutting

- [ ] T022 Run `ruff check` and `ruff format` on modified files to ensure lint compliance
- [ ] T023 [US4] Run `agdt-test-pattern tests/unit/orchestration/runner/ -v` and verify runner pause-detection test coverage [FR-005]
- [ ] T024 [US4] Verify SC-005 constraint: net new lines in runner main flow (excluding helper, tests, docs) is fewer than 5 lines [FR-005]
- [ ] T025 [US4] Run full test suite `agdt-test` for final validation of no regressions [FR-005]

## Dependencies

```text
T001 → T002 → T003 → T004
T004 → T005, T006, T007
T007 → T008
T008 → T009, T010, T011
T011 → T012
T012 → T013, T014
T014 → T015
T015 → T016, T017
T017 → T018 → T019
T019 → T020 → T021
T021 → T022 → T023 → T024 → T025
```

## Parallel Execution Examples

- After T004, implement US1 and US2 in parallel tracks (`T005-T008` and `T009-T012`) because they target different invocation modes.
- After T015, run `T016` and `T017` concurrently since both are regression-only test additions.
- In Phase 8, run local linting (`T022`) while preparing coverage validation (`T023`) before final full-suite checks.

## Implementation Strategy

1. Complete setup/foundational helper work first (T001-T004) to lock pause-detection semantics.
2. Deliver fresh-path behavior (US1), then mirror logic on resume path (US2), then complete completion semantics and regressions (US3/US4).
3. Finish with CLI help text updates and cross-cutting quality/coverage checks before final validation.

## FR Traceability Matrix

| FR | Tasks |
| --- | --- |
| FR-001 (inspect state after invoke) | T003, T006, T007, T017 |
| FR-002 (pause when status ≠ completed) | T005, T007, T014 |
| FR-003 (completion only when status = completed) | T007, T013, T015 |
| FR-004 (same logic for fresh + resume paths) | T009, T010, T011 |
| FR-005 (backward compat with GraphInterrupt) | T008, T012, T016, T018, T019, T023, T024, T025 |
| FR-006 (pause message includes issue key + command) | T005, T009 |
| FR-007 (exit code 0 on pause) | T005, T007 |
| FR-008 (helper function encapsulation) | T001, T002, T003, T004 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
