# Tasks: Prevent Duplicate Copilot Sessions During PR Review Workflow

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Test scaffolding and preflight verification |
| Phase 2: Foundational — Process Liveness Utility | Phase 1: Session Mutex Guard | PID liveness utility needed by mutex checks |
| Phase 3: User Story 4 — Session Mutex | Phase 1: Session Mutex Guard | Core mutex implementation and coverage tasks |
| Phase 4: User Story 2 — State Directory Alignment | Phase 2: State Directory Alignment | State dir alignment implementation and tests |
| Phase 5: User Story 1 — Grace Period Polling in Auto-Start | Phase 3: Grace Period Polling in Auto-Start | Grace-period and auto-start marker behavior |
| Phase 6: User Story 3 — Advance-Workflow Guard | Phase 4: Advance-Workflow Guard | No-state/cleared/completed guard behavior |
| Phase 7: User Story 3 (cont.) — Agent Prompt Hardening | Phase 5: Agent Prompt Hardening | Agent prompt guardrails to prevent re-initiation |
| Phase 8: User Story 1 (cont.) — End-to-End Single Session Guarantee | Phase 6: End-to-End Single Session Guarantee | End-to-end single-session enforcement checks |
| Final Phase: Polish & Cross-Cutting | Phases 1-6 | Final docs and validation across all phases |

## Phase 1: Setup

- [ ] T001 Create `tests/unit/cli/workflows/__init__/` directory and add `__init__.py` init file for advance_workflow_cmd tests
- [ ] T002 Verify existing `tests/unit/cli/copilot/session/__init__.py` and `tests/unit/cli/copilot/auto_start/__init__.py` are present

## Phase 2: Foundational — Process Liveness Utility

- [ ] T003 Write failing tests for `_is_process_alive()` in `tests/unit/cli/copilot/session/test__is_process_alive.py` covering Unix alive, Unix dead, Unix permission error, Windows alive (mock
  ctypes), Windows dead (mock ctypes), and invalid PID input (FR-004)
- [ ] T004 Implement `_is_process_alive(pid: int) -> bool` in `agentic_devtools/cli/copilot/session.py` using `os.kill(pid, 0)` on Unix and `ctypes` `kernel32.OpenProcess`/`CloseHandle` on Windows
  (FR-004)
- [ ] T005 Run `agdt-test-pattern "tests/unit/cli/copilot/session/"` for quick validation, then verify 100% branch coverage for `agentic_devtools/cli/copilot/session.py` via `bash scripts/targeted-checks.sh`

## Phase 3: User Story 4 — Session Mutex (P2, but foundational for US1)

- [ ] T006 [US4] Write failing tests for `_check_session_mutex()` in `tests/unit/cli/copilot/session/test__check_session_mutex.py` covering: no PID in state (allow), live PID blocks, stale PID clears
  and allows, unparseable PID clears and allows, active auto-start marker blocks, stale marker allows, FileLockError fails closed (FR-001, FR-004, FR-008)
- [ ] T007 [US4] Implement `_check_session_mutex(requested_mode: str) -> dict[str, Any] | None` in `agentic_devtools/cli/copilot/session.py` using `read_modify_write_state()` with PID liveness check
  and auto-start marker evaluation (FR-001, FR-004, FR-008)
- [ ] T008 [US4] Integrate `_check_session_mutex()` call at top of `start_copilot_session()` — return no-op `CopilotSessionResult` when mutex blocks (FR-001, FR-005)
- [ ] T009 [US4] Write tests verifying `start_copilot_session()` returns no-op result when mutex is active in `tests/unit/cli/copilot/session/test_start_copilot_session.py` (extend or create) (FR-005)
- [ ] T010 [US4] Run `agdt-test-pattern "tests/unit/cli/copilot/session/"` for quick validation,
  then validate coverage for `agentic_devtools/cli/copilot/session.py` via `bash scripts/targeted-checks.sh` (FR-001)

## Phase 4: User Story 2 — State Directory Alignment (P1)

- [ ] T011 [P] [US2] Write/extend tests in `tests/unit/cli/workflows/worktree_setup/test__run_auto_execute_command.py` asserting `AGENTIC_DEVTOOLS_STATE_DIR` env var is set to target worktree's
  resolved state path before subprocess invocation (FR-002)
- [ ] T012 [P] [US2] Harden `_run_auto_execute_command()` in `agentic_devtools/cli/workflows/worktree_setup.py` to ensure `AGENTIC_DEVTOOLS_STATE_DIR` is set correctly for cross-repo scenarios
  (FR-002)
- [ ] T013 [US2] Add edge-case test: target worktree without `runtime-bootstrap.json` falls back to `_unscoped` path and both contexts still resolve identically (FR-002)
- [ ] T014 [US2] Run targeted checks for `agentic_devtools/cli/workflows/worktree_setup.py`

## Phase 5: User Story 1 — Grace Period Polling in Auto-Start (P1)

- [ ] T015 [US1] Write failing tests for `_wait_for_workflow_state()` in `tests/unit/cli/copilot/auto_start/test__wait_for_workflow_state.py` covering: state found immediately, state found after
  retries, timeout expires, corrupt JSON retry, FileNotFoundError retry, FileLockError retry (FR-007)
- [ ] T016 [US1] Implement `_wait_for_workflow_state(state_file_path, timeout, interval) -> bool` in `agentic_devtools/cli/copilot/auto_start.py` with polling loop and graceful error handling (FR-007)
- [ ] T017 [US1] Add constants `_GRACE_PERIOD_INTERVAL_S = 2.0` and `_GRACE_PERIOD_TIMEOUT_S = 10.0` in `agentic_devtools/cli/copilot/auto_start.py` (FR-007)
- [ ] T018 [US1] Integrate grace period call in `copilot_auto_start_cmd()` after state file path resolution; exit non-zero with descriptive stderr message if timeout expires (FR-007)
- [ ] T019 [US1] Add CLI args `--grace-period-timeout` and `--grace-period-interval` to `copilot_auto_start_cmd()` argparser (FR-007)
- [ ] T020 [US1] Implement auto-start session marker lifecycle: write `copilot.auto_start_session_marker` before Copilot launch, clear on all exit paths in `agentic_devtools/cli/copilot/auto_start.py`
  (FR-001)
- [ ] T021 [US1] Extend `tests/unit/cli/copilot/auto_start/test_copilot_auto_start_cmd.py` with tests for grace period integration, marker write/clear, and non-zero exit on timeout (FR-007)
- [ ] T022 [US1] Run `agdt-test-pattern "tests/unit/cli/copilot/auto_start/"` for quick validation,
  then validate coverage for `agentic_devtools/cli/copilot/auto_start.py` via `bash scripts/targeted-checks.sh` (FR-007)

## Phase 6: User Story 3 — Advance-Workflow Guard (P1)

- [ ] T023 [P] [US3] Create `tests/unit/cli/workflows/__init__/test_advance_workflow_cmd.py` with tests for: empty/missing state file → "No workflow state found", state file with no workflow key →
  "Workflow state was cleared", completed workflow → "Workflow is already completed", active workflow → advances normally (FR-003)
- [ ] T024 [US3] Enhance error handling in `advance_workflow_cmd()` in `agentic_devtools/cli/workflows/__init__.py` with richer diagnostics distinguishing no-state, cleared, and completed scenarios
  (FR-003)
- [ ] T025 [US3] Verify `advance_workflow_cmd()` exits non-zero and does NOT trigger any workflow initiation logic as fallback (FR-003)
- [ ] T026 [US3] Retire or redirect legacy tests in `tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py` to avoid duplicate coverage (FR-003)
- [ ] T027 [US3] Run targeted checks for `agentic_devtools/cli/workflows/__init__.py`

## Phase 7: User Story 3 (cont.) — Agent Prompt Hardening (P1)

- [ ] T028 [P] [US3] Update `.github/agents/agdt.copilot-auto-start.agent.md` with explicit no-reinitiation guardrails and prerequisite that active workflow MUST already exist (FR-006)
- [ ] T029 [P] [US3] Update `.github/agents/agdt.advance-workflow.agent.md` with explicit rule to NEVER fall back to initiating a new workflow on error, and troubleshooting guidance (FR-006)
- [ ] T036 [US3] Add manual regression test task verifying both agent prompts do not re-initiate workflow when no active state exists (FR-006)

## Phase 8: User Story 1 (cont.) — End-to-End Single Session Guarantee

- [ ] T030 [US1] Write integration-style test verifying that calling `start_copilot_session()` twice with the same worktree state results in only one session (second call returns no-op) in
  `tests/unit/cli/copilot/session/test__check_session_mutex.py` (FR-001)
- [ ] T031 [US1] Write test verifying `agdt-copilot-auto-start` invokes `_check_session_mutex()` guard (either directly or via `start_copilot_session()`) in
  `tests/unit/cli/copilot/auto_start/test_copilot_auto_start_cmd.py` (FR-001)

## Final Phase: Polish & Cross-Cutting

- [ ] T032 Update `scripts/agentic_devtools/copilot-instructions.md` to document new state keys (`copilot.auto_start_session_marker`) and session mutex behavior
- [ ] T033 Run full test suite with `agdt-test` and `agdt-task-wait` — verify zero regressions
- [ ] T034 Run `bash scripts/targeted-checks.sh` — verify lint, format, mypy, and coverage pass
- [ ] T035 Run `python scripts/validate_test_structure.py` — verify 1:1:1 test structure compliance

---
*Generated by Copilot SDK (claude-opus-4.6)*
