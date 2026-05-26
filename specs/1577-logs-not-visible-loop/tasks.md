# Tasks: AI PR Loop Orchestrator Log Visibility

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase 1 | Scaffolding for `logging_config.py` and the 1:1:1 test package folder |
| Phase 2: Foundational | Phase 1 | Implement `is_github_actions()`, `setup_logging()`, `log_group()` and their unit tests |
| Phase 3: User Story 1 — Visible Orchestrator Logs (P1) | Phase 2 | Wire `setup_logging()` into entry points and update command tests |
| Phase 4: User Story 2 — Expanded Log Groups (P2) | Phase 3–4 | Consolidate group helpers and ensure key INFO logs are outside groups |
| Phase 5: User Story 3 — Configurable Log Verbosity (P3) | Phase 1 | Extend `AGDT_LOG_LEVEL` test coverage |
| Phase 6: Subprocess Output Handling | Phase 5 | Capture and re-emit subprocess stderr via logging |
| Final Phase: Polish & Cross-Cutting | Phase 6 | Validation runs (validate_test_structure, agdt-test, PR checks) |

## Phase 1: Setup

- [ ] T001 Create module file `agentic_devtools/cli/ci/logging_config.py` with module docstring and imports (`logging`, `os`, `sys`, `contextlib`)
- [ ] T002 Create test directory `tests/unit/cli/ci/logging_config/` with `__init__.py`

## Phase 2: Foundational

- [ ] T003 Implement `is_github_actions() -> bool` in `agentic_devtools/cli/ci/logging_config.py` — returns `os.environ.get("GITHUB_ACTIONS") == "true"` (FR-008: controls conditional group annotation
  emission)
- [ ] T004 Write tests for `is_github_actions()` in `tests/unit/cli/ci/logging_config/test_is_github_actions.py` — covers True/False/absent env var cases (FR-008)
- [ ] T005 Implement `setup_logging()` in `agentic_devtools/cli/ci/logging_config.py` — idempotent function that checks `logging.root.handlers`, adds `StreamHandler(sys.stderr)` with format
  `%(asctime)s %(levelname)-8s %(name)s: %(message)s` and `datefmt="%H:%M:%S"`, reads `AGDT_LOG_LEVEL` env var, checks level names, warns on invalid values, defaults to INFO (FR-001: configures
  logging to stderr; FR-002: format string with timestamp/level/module; FR-006: `AGDT_LOG_LEVEL` support)
- [ ] T006 Write tests for `setup_logging()` in `tests/unit/cli/ci/logging_config/test_setup_logging.py` — covers
  success path (handler added, format applied), idempotency, format verification, level override, invalid level warning, stderr output (FR-001, FR-002, FR-006)
- [ ] T007 Implement `log_group(title: str)` context manager in `agentic_devtools/cli/ci/logging_config.py` — emits `::group::{title}` / `::endgroup::` only when `is_github_actions()` is True,
  otherwise no-op; uses `try/finally` for cleanup (FR-005: verbose details inside collapsed groups; FR-008: no annotations outside GitHub Actions)
- [ ] T008 Write tests for `log_group()` in `tests/unit/cli/ci/logging_config/test_log_group.py` — covers emission when GITHUB_ACTIONS=true, no-op otherwise, cleanup on exception (FR-005, FR-008)
- [ ] T009 Export `setup_logging`, `is_github_actions`, `log_group` from `agentic_devtools/cli/ci/logging_config.py` and update `agentic_devtools/cli/ci/__init__.py` if needed

## Phase 3: User Story 1 — Visible Orchestrator Logs (P1)

- [ ] T010 [US1] Wire `setup_logging()` call into `ai_pr_loop_command()` in `agentic_devtools/cli/ci/commands.py` — place after `_python_orchestrator_enabled()` guard, before `gh` CLI check (FR-001:
  entry point configures logging before orchestrator logic)
- [ ] T011 [US1] Wire `setup_logging()` call into `speckit_trigger_command()` in `agentic_devtools/cli/ci/commands.py` — place before command logic (FR-007: speckit entry point uses shared logging
  mechanism)
- [ ] T012 [US1] Update/add tests in `tests/unit/cli/ci/commands/` to verify `setup_logging()` is called at the correct point in `ai_pr_loop_command()` control flow (FR-001)
- [ ] T013 [US1] Update/add tests in `tests/unit/cli/ci/commands/` to verify `setup_logging()` is called at the correct point in
  `speckit_trigger_command()` control flow — covering success path and expected call order (FR-007)

## Phase 4: User Story 2 — Expanded Log Groups (P2)

- [ ] T014 [US2] Replace `_is_github_actions()`, `_log_group()`, `_log_endgroup()` in `agentic_devtools/cli/ci/orchestrator.py` with imports from `logging_config` — convert paired calls to
  `log_group()` context manager usage
- [ ] T015 [US2] Replace `_is_github_actions()`, `_log_group()`, `_log_endgroup()` in `agentic_devtools/cli/ci/pipeline/runner.py` with imports from `logging_config` — convert paired calls to
  `log_group()` context manager usage
- [ ] T016 [US2] Audit `agentic_devtools/cli/ci/guards.py` — verify guard block/allow outcomes are logged at INFO level outside any `log_group()` scope (FR-003: guard outcomes visible without
  expanding groups)
- [ ] T017 [US2] Audit `agentic_devtools/cli/ci/pipeline/actions/*.py` — verify action outcomes (merge, repair dispatch, approval) are logged at INFO level outside `log_group()` scope (FR-004: action
  outcomes visible without expanding groups)
- [ ] T018 [P] [US2] Add/adjust log statements in guards modules where FR-003 is not satisfied — ensure block reasons are `logger.info()` outside groups
- [ ] T019 [P] [US2] Add/adjust log statements in action modules where FR-004 is not satisfied — ensure action outcomes are `logger.info()` outside groups
- [ ] T020 [US2] Ensure verbose payloads (JSON dumps, API responses) in orchestrator/runner are logged at DEBUG level or wrapped in `log_group()` context manager (FR-005: verbose details inside
  collapsed groups)
- [ ] T021 [US2] Update tests in `tests/unit/cli/ci/orchestrator/` that mock removed private functions (`_log_group`, `_log_endgroup`, `_is_github_actions`) to use new import paths (FR-005, FR-008)
- [ ] T022 [US2] Update tests in `tests/unit/cli/ci/pipeline/runner/` that mock removed private functions to use new import paths (FR-005, FR-008)

## Phase 5: User Story 3 — Configurable Log Verbosity (P3)

- [ ] T023 [US3] Add test cases to `tests/unit/cli/ci/logging_config/test_setup_logging.py` covering `AGDT_LOG_LEVEL=DEBUG` enabling debug messages (FR-006)
- [ ] T024 [US3] Add test cases covering `AGDT_LOG_LEVEL=WARNING` suppressing info messages (FR-006)
- [ ] T025 [US3] Add test cases covering invalid `AGDT_LOG_LEVEL` value (e.g., `VERBOSE`) emitting warning and falling back to INFO (FR-006)
- [ ] T026 [US3] Verify at least one known debug-level log statement exists in orchestrator modules (add one in state-transition logic if absent) for SC-005 validation (FR-006)

## Phase 6: Subprocess Output Handling

- [ ] T027 [US1] Audit `agentic_devtools/cli/ci/github_provider.py` subprocess calls — verify `capture_output=True` is used and stderr is not inherited directly
- [ ] T028 [US1] Add `logger.debug("gh stderr: %s", stderr)` on success (returncode 0) and `logger.warning("gh failed (exit %d): %s", code, stderr)` on failure for subprocess calls in
  `github_provider.py`
- [ ] T029 [US1] Write/update tests for subprocess output capture in `tests/unit/cli/ci/github_provider/` — verify stderr re-emission through logging at appropriate levels

## Final Phase: Polish & Cross-Cutting

- [ ] T030 Run `python scripts/validate_test_structure.py` to confirm all new test directories pass 1:1:1 validation
- [ ] T031 Run `agdt-test` full suite — verify 0 regressions (SC-003)
- [ ] T032 Run `bash scripts/run-pr-checks.sh` — verify all CI-blocking checks pass (ruff, mypy, markdownlint, tests)
- [ ] T033 Local validation: run `agdt-ai-pr-loop` with mock event payload — confirm ≥10 formatted log lines on stderr with timestamps and module names (SC-004)
- [ ] T034 Performance validation: time `setup_logging()` across 100 invocations — confirm < 5ms average (SC-006, NFR-001)
- [ ] T035 Verify with `GITHUB_ACTIONS` unset that output contains 0 occurrences of `::group::` or `::endgroup::` (SC-007) (FR-008)

## Dependencies

```text
T001 → T003, T005, T007, T009
T002 → T004, T006, T008
T003 → T004, T007
T005 → T006, T010, T011
T007 → T008, T014, T015
T009 → T010, T011, T014, T015
T010 → T012
T011 → T013
T014 → T021
T015 → T022
T006, T008, T012, T013 → T023, T024, T025
T014, T015, T016, T017 → T020
T018, T019 → T020
All T0xx → T030, T031, T032, T033, T034, T035
```

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T005, T010, T011 |
| FR-002 | T005, T006 |
| FR-003 | T016, T018 |
| FR-004 | T017, T019 |
| FR-005 | T007, T020 |
| FR-006 | T005, T023, T024, T025 |
| FR-007 | T011, T013 |
| FR-008 | T003, T007, T008, T035 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
