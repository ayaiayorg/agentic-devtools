# Tasks: Remove active_session Gate from dispatch_repair (#1643)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Test scaffolding prerequisite |
| Phase 2: Foundational — New Session Detector | Plan Phase 1: New Session Detector | Add and validate the `gh agent-task` detector |
| Phase 3: Deprecate Old Detector | Plan Phase 2: Deprecate Old Detector | Deprecate the legacy events-based detector |
| Phase 4: User Story 1 — Remove Session Gate from DispatchRepairAction (P1) | Plan Phase 3: Remove Session Gate from DispatchRepairAction | Remove `dispatch_repair` session awareness and update tests |
| Phase 5: User Story 4 — Update Snapshot Builder (FR-007) | Plan Phase 4: Update Snapshot Builder | Stop populating `active_session` in snapshots |
| Phase 6: User Story 4 — Migrate SquashAction and RequestReviewAction (FR-008) | Plan Phase 5: Migrate SquashAction and RequestReviewAction | Move remaining session-aware actions to the new detector |
| Phase 7: User Story 4 — Update Summary Renderer (FR-008e) | Plan Phase 6: Update Summary Renderer | Render session state as `N/A` |
| Phase 8: Polish & Cross-Cutting | Plan Phase 7: Final Validation | Run final validation and usage checks |

## Phase 1: Setup

- [ ] T001 Create test directory `tests/unit/cli/ci/pipeline/session_detector/` `__init__.py` if missing (scaffolding for new test file)

## Phase 2: Foundational — New Session Detector

- [ ] T002 [US2] Write failing tests for `is_copilot_session_active_via_agent_task()` — running task returns `True` (FR-003, FR-005) in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_via_agent_task.py`
- [ ] T003 [US2] Write failing tests for `is_copilot_session_active_via_agent_task()` — stopped/completed tasks return `False`, empty list returns `False` (FR-003, FR-005) in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_via_agent_task.py`
- [ ] T004 [US2] Write failing tests for `is_copilot_session_active_via_agent_task()` — multiple tasks with mixed status returns `True` (FR-005) in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_via_agent_task.py`
- [ ] T005 [US3] Write failing tests for fail-open behavior — timeout returns `False` + WARNING log (FR-004, NFR-001) in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_via_agent_task.py`
- [ ] T006 [US3] Write failing tests for fail-open behavior — non-zero exit, malformed JSON, missing binary, permission error all return `False` + WARNING log (FR-004) in
  `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_via_agent_task.py`
- [ ] T007 [US2] Implement `is_copilot_session_active_via_agent_task(repo, pr_number, *, timeout_seconds=10)` in `agentic_devtools/cli/ci/pipeline/session_detector.py` — subprocess call to `gh
  agent-task list --repo <repo> --json id,status,pullRequestNumber,createdAt`, parse JSON, filter by `pullRequestNumber == pr_number`, return `True` if any status in
  `{"queued","requested","waiting","in_progress","running"}` (FR-003, FR-005, NFR-001, NFR-002)
- [ ] T008 [US3] Implement fail-open error handling in `is_copilot_session_active_via_agent_task()` — catch all exceptions, log WARNING, return `False`, no retries (FR-004, NFR-004)
- [ ] T009 Verify all T002–T006 tests pass (GREEN phase)

## Phase 3: Deprecate Old Detector

- [ ] T010 [US2] Write test verifying `is_copilot_session_active()` emits `DeprecationWarning` (FR-006) in `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_deprecated.py`
- [ ] T011 [US2] Add `warnings.warn(...)` with `DeprecationWarning` and `stacklevel=2` at top of `is_copilot_session_active()` in `agentic_devtools/cli/ci/pipeline/session_detector.py` (FR-006)
- [ ] T012 Update existing test `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active.py` to expect `DeprecationWarning` (FR-006)

## Phase 4: User Story 1 — Remove Session Gate from DispatchRepairAction (P1)

- [ ] T013 [US1] Write failing test: `DispatchRepairAction.evaluate()` with `active_session=True` and `ci_status="failing"` returns `EXECUTE` (FR-001, FR-002) in
  `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_dispatchrepairaction.py`
- [ ] T014 [US1] Write failing test: `DispatchRepairAction.evaluate()` preconditions dict does NOT contain `no_active_session` key (FR-001) in
  `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_dispatchrepairaction.py`
- [ ] T015 [US1] Write failing test: `DispatchRepairAction.evaluate()` with actionable review and `active_session=True` returns `EXECUTE` (FR-002) in
  `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_dispatchrepairaction.py`
- [ ] T016 [US1] Remove `no_active_session` precondition block (lines 52–60) and update the class docstring to remove active-session
  skip/precondition wording in `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` (FR-001, FR-002)
- [ ] T017 [US1] Update/remove existing test `test_skip_when_active_session` that expects session-gated SKIP behavior in
  `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_dispatchrepairaction.py` (FR-001)
- [ ] T018 [US1] Verify T013–T015 tests pass and no test expects session-gated skip from dispatch_repair (SC-001)

## Phase 5: User Story 4 — Update Snapshot Builder (FR-007)

- [ ] T019 [US4] Write test verifying `build_pr_state_snapshot()` does NOT call `is_copilot_session_active()` and `active_session` defaults to `False` (FR-007) in
  `tests/unit/cli/ci/pipeline/snapshot/test_build_pr_state_snapshot.py`
- [ ] T020 [US4] Remove `from .session_detector import is_copilot_session_active` import from `agentic_devtools/cli/ci/pipeline/snapshot.py` (FR-007)
- [ ] T021 [US4] Remove line 174 (`active_session = is_copilot_session_active(...)`) and `active_session=active_session` from constructor call in `agentic_devtools/cli/ci/pipeline/snapshot.py`
  (FR-007)
- [ ] T022 [US4] Update snapshot builder tests to not mock/expect the old session detector call in `tests/unit/cli/ci/pipeline/snapshot/` (FR-007)
- [ ] T023 [US4] Verify `PRStateSnapshot.active_session` field still exists with default `False` in `agentic_devtools/cli/ci/pipeline/snapshot.py` (FR-007)

## Phase 6: User Story 4 — Migrate SquashAction and RequestReviewAction (FR-008)

- [ ] T024 [P] [US4] Write failing test: `SquashAction.evaluate()` calls `is_copilot_session_active_via_agent_task()` with correct `repo` and `pr_number` instead of reading `snapshot.active_session`
  (FR-008c) in `tests/unit/cli/ci/pipeline/actions/squash/test_squashaction.py`
- [ ] T025 [P] [US4] Write failing test: `RequestReviewAction.evaluate()` calls `is_copilot_session_active_via_agent_task()` with correct `repo` and `pr_number` instead of reading
  `snapshot.active_session` (FR-008d) in `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py`
- [ ] T026 [US4] Write failing test: `SquashAction.evaluate()` SKIPs when new detector returns `True`, proceeds when `False` (FR-008c) in `tests/unit/cli/ci/pipeline/actions/squash/test_squashaction.py`
- [ ] T027 [US4] Write failing test: `RequestReviewAction.evaluate()` SKIPs when new detector returns `True`, proceeds when `False` (FR-008d) in `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py`
- [ ] T028 [US4] In `agentic_devtools/cli/ci/pipeline/actions/squash.py` — import `is_copilot_session_active_via_agent_task`, replace `snapshot.active_session` with direct detector call using
  `snapshot.base_repo_full_name` and `snapshot.pr_number` (FR-008c)
- [ ] T029 [US4] In `agentic_devtools/cli/ci/pipeline/actions/request_review.py` — import `is_copilot_session_active_via_agent_task`, replace `snapshot.active_session` with direct detector call using
  `snapshot.base_repo_full_name` and `snapshot.pr_number` (FR-008d)
- [ ] T030 [US4] Update existing squash tests to mock `is_copilot_session_active_via_agent_task` instead of setting `active_session=True`
  in `tests/unit/cli/ci/pipeline/actions/squash/test_squashaction.py` (FR-008c, SC-006)
- [ ] T031 [US4] Update existing request_review tests to mock `is_copilot_session_active_via_agent_task` instead of setting `active_session=True` in
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-008d, SC-006)
- [ ] T032 Verify T024–T027 tests pass (GREEN phase)

## Phase 7: User Story 4 — Update Summary Renderer (FR-008e)

- [ ] T033 [US4] Write failing test: summary renderer outputs `N/A` for session state instead of `True`/`False` (FR-008e) in `tests/unit/cli/ci/pipeline/summary/test_render_summary_comment.py`
- [ ] T034 [US4] In `agentic_devtools/cli/ci/pipeline/summary.py` line 167, change `str(snapshot.active_session)` to `"N/A"` (FR-008e)
- [ ] T035 [US4] Update existing summary tests in `tests/unit/cli/ci/pipeline/summary/test_render_summary_comment.py` to expect `N/A` for session state (FR-008e)

## Phase 8: Polish & Cross-Cutting

- [ ] T036 Run full test suite with `agdt-test`, then `agdt-task-wait`; verify 0 failures across the suite (SC-005)
- [ ] T037 Run `bash scripts/targeted-checks.sh` — verify formatting, linting, 100% branch coverage on modified files (NFR-003)
- [ ] T038 Run `python scripts/validate_test_structure.py` — verify 1:1:1 test structure compliance
- [ ] T039 Verify no production code imports or calls `is_copilot_session_active()` (only deprecated body remains) — grep for usage (FR-008)
- [ ] T040 Verify `snapshot.active_session` is not read by any action except as unused default (FR-007, FR-008)

## Dependencies

| Task | Depends On |
|------|------------|
| T007 | T002–T006 |
| T008 | T007 |
| T009 | T007, T008 |
| T010 | T009 |
| T011 | T010 |
| T012 | T011 |
| T013 | T009 |
| T016 | T013–T015 |
| T017 | T016 |
| T018 | T016, T017 |
| T019 | T009 |
| T020 | T019 |
| T021 | T020 |
| T022 | T021 |
| T023 | T021 |
| T024 | T009, T018 |
| T025 | T009, T018 |
| T026 | T024 |
| T027 | T025 |
| T028 | T026, T021 |
| T029 | T027, T021 |
| T030 | T028 |
| T031 | T029 |
| T032 | T030, T031 |
| T033 | T032 |
| T034 | T033 |
| T035 | T034 |
| T036 | T035 |
| T037 | T036 |
| T038 | T036 |
| T039 | T036 |
| T040 | T036 |

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T013, T014, T016, T017 |
| FR-002 | T013, T015, T016 |
| FR-003 | T002, T003, T007 |
| FR-004 | T005, T006, T008 |
| FR-005 | T002, T003, T004, T007 |
| FR-006 | T010, T011, T012 |
| FR-007 | T019, T020, T021, T022, T023, T040 |
| FR-008 | T024–T035, T039, T040 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
