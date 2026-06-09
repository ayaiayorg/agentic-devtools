# Tasks: Fix Stale Prompt File Causes Premature Copilot Session Start (#1746)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Initial repository/code review setup before implementation and tests |
| Phase 2: Foundational — Test Updates (RED) | Phase 1: Write Failing Tests (RED) | Story-aligned failing test updates |
| Phase 3: User Story 1 — Primary Workflow (P1) | Phase 2: Implement Fix (GREEN) | US1 implementation tasks |
| Phase 4: User Story 2 — Error Recovery (P1) | Phase 2: Implement Fix (GREEN) | US2 implementation tasks |
| Phase 5: User Story 3 — Graceful Degradation (P2) | Phase 3: Verify & Refactor | US3 validation task |
| Final Phase: Polish & Cross-Cutting | Phase 4: Run Full Suite & PR Checks | Final validation and commit tasks |

## Phase 1: Setup

- [ ] T001 [US1] Review current implementation in `agentic_devtools/cli/workflows/commands.py` (lines 602–643) and existing tests in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`

## Phase 2: Foundational — Test Updates (RED)

- [ ] T002 [P] [US1] Add happy-path test assertions to
  `test_stale_prompt_file_deleted_before_async_setup` verifying INFO-level `caplog` cleanup signal before background setup (validates FR-001, SC-001) in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
- [ ] T003 [P] [US1] Add happy-path test `test_no_stale_prompt_file_logs_debug` asserting DEBUG-level log when no file exists on first run (validates FR-004, SC-003) in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
- [ ] T004 [P] [US2] Add happy-path/negative test coverage by renaming
  `test_stale_prompt_unlink_error_skips_copilot_session` and asserting `sys.exit(1)` with stderr error message BEFORE `setup_pull_request_review_async` is called
  (validates FR-002, SC-004) in `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
- [ ] T005 [P] [US2] Add happy-path/negative test coverage by renaming
  `test_directory_at_stale_prompt_path_prints_warning` and asserting `sys.exit(1)` with stderr error BEFORE background setup is spawned (validates FR-002) in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`
- [ ] T006 [P] [US3] Add `test_consecutive_reruns_each_clean_stale_file` simulating three re-runs where each run cleans prior stale file ensuring `_wait_for_prompt_file` only sees current-run output
  (validates FR-003, FR-005, SC-002) in `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`

## Phase 3: User Story 1 — Primary Workflow (P1)

- [ ] T007 [US1] Replace `print("WARNING: ...")` with `logging.getLogger(__name__).info()` when stale file is successfully removed (FR-001) in `agentic_devtools/cli/workflows/commands.py`
- [ ] T008 [US1] Add `logging.getLogger(__name__).debug()` call when no stale file exists on first run (FR-004) in `agentic_devtools/cli/workflows/commands.py`
- [ ] T009 [US1] Remove `unlink(missing_ok=True)` and replace with explicit `FileNotFoundError` catch logging at DEBUG level for race-condition traceability (FR-003) in
  `agentic_devtools/cli/workflows/commands.py`

## Phase 4: User Story 2 — Error Recovery (P1)

- [ ] T010 [US2] Move `setup_pull_request_review_async()` call to AFTER the stale-file cleanup block so it is never called when cleanup fails (FR-002, FR-005) in
  `agentic_devtools/cli/workflows/commands.py`
- [ ] T011 [US2] Replace `_stale_prompt_cleared = False` + deferred check pattern with immediate `sys.exit(1)` on `OSError`, printing path, reason, and remediation to stderr (FR-002, SC-004) in
  `agentic_devtools/cli/workflows/commands.py`
- [ ] T012 [US2] Replace directory-at-path `print("WARNING: ...")` with immediate `sys.exit(1)` and stderr error message including path and remediation (FR-002) in
  `agentic_devtools/cli/workflows/commands.py`
- [ ] T013 [US2] Remove the now-unnecessary `_stale_prompt_cleared` flag and its associated post-setup guard block (lines 630–635) in `agentic_devtools/cli/workflows/commands.py`

## Phase 5: User Story 3 — Graceful Degradation (P2)

- [ ] T014 [US3] Verify that cleanup ordering guarantees FR-003 and FR-005: `_wait_for_prompt_file()` only considers prompt files written after the cleanup step by running
  `test_consecutive_reruns_each_clean_stale_file` green in `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py`

## Final Phase: Polish & Cross-Cutting

- [ ] T015 Run focused tests to confirm all updated/new tests pass
  (FR-001, FR-002, FR-003, FR-004, FR-005):
  `agdt-test-pattern tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py -v`
- [ ] T016 Run targeted checks to validate lint, format, type-check, and per-file coverage (FR-001, FR-002, FR-003, FR-004, FR-005): `bash scripts/targeted-checks.sh`
- [ ] T017 Run full test suite (FR-001, FR-002, FR-003, FR-004, FR-005): `agdt-test` + `agdt-task-wait`
- [ ] T018 Commit with `agdt-git-save-work` using message
  `fix([#1746](https://github.com/ayaiayorg/agentic-devtools/issues/1746)): remove stale prompt file before spawning PR review background setup`
  and footer `[#1746](https://github.com/ayaiayorg/agentic-devtools/issues/1746)`

## Dependency Graph

```text
T001 → T002, T003, T004, T005, T006 (parallel)
T002–T006 → T007, T008, T009 (parallel within phase)
T007–T009 → T010 → T011, T012 (parallel) → T013
T013 → T014
T014 → T015 → T016 → T017 → T018
```

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T002, T007 |
| FR-002 | T004, T005, T010, T011, T012 |
| FR-003 | T006, T009, T014 |
| FR-004 | T003, T008 |
| FR-005 | T006, T010, T014 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
