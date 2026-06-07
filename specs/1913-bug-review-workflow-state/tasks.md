# Tasks: Fix PR Review Workflow State Directory Mismatch (#1913)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Branch creation and implementation prep with no direct plan phase equivalent |
| Phase 2: Foundational | Phases 1–2 | Shared pin-workflow recognition and `write_pin_file()` API prerequisites |
| Phase 3: User Story 1 | Phase 3 | Auto-execute pinning work so the first auto-start session sees active workflow state |
| Phase 4: User Story 2 | Phases 4–5 | Canonical-path stabilization via env-override pinning and auto-start diagnostics |
| Phase 5: User Story 3 | Phase 6 | Backward-compatibility and cleanup-contract verification for single-repo workflows |
| Final Phase: Polish & Cross-Cutting | Phases 3–6 | Cross-phase regression, integration, and delivery verification |

## Phase 1: Setup

- [ ] T001 Create feature branch `feature/1913/fix-state-dir-mismatch` from `main`

## Phase 2: Foundational — Expand Recognized Workflows & Pin File API

- [ ] T002 [P] Write failing happy-path tests for expanded `RECOGNIZED_PIN_WORKFLOWS` in `tests/unit/state/test_write_pin_file.py` — verify all 9 workflow names are accepted (FR-003, FR-008)
- [ ] T003 [P] Write failing tests for `target_git_root` parameter in `tests/unit/state/test_write_pin_file.py` — cases: provided+exists, None (default), provided+non-existent (FR-008)
- [ ] T004 Expand `RECOGNIZED_PIN_WORKFLOWS` frozenset in `agentic_devtools/state.py` (L44) to include all 9 cross-worktree workflow names (FR-003, FR-008)
- [ ] T005 Update existing test assertions in `tests/unit/state/test_write_pin_file.py`, `tests/unit/state/test_read_and_validate_pin_file.py`, `tests/unit/state/test_refresh_pin_file_ttl.py` to
  reflect expanded set (FR-003, FR-008)
- [ ] T006 Add `target_git_root: Path | None = None` parameter to `write_pin_file()` in `agentic_devtools/state.py` (L505–564) — when provided and `.is_dir()`, use instead of `_get_git_repo_root()`
  (FR-008)
- [ ] T007 Verify T002 and T003 tests now pass (GREEN) (FR-003, FR-008)

## Phase 3: User Story 1 — First Auto-Start Session Sees Active Workflow (P1)

- [ ] T008 [US1] Write failing tests for `_run_auto_execute_command` pin file write in `tests/unit/cli/workflows/worktree_setup/test__run_auto_execute_command.py` — verify pin written to target
  worktree `.agdt/` (FR-001, FR-003)
- [ ] T009 [US1] Write failing happy-path test verifying pin file content matches resolved `state_dir` (FR-004)
- [ ] T010 [US1] Write failing test verifying pin NOT written when `workflow=None` (backward compat) (FR-007, NFR-001)
- [ ] T011 [US1] Write failing test verifying graceful handling when pin write fails (subprocess still runs) (FR-003, NFR-001)
- [ ] T012 [US1] Add `workflow: str | None = None` parameter to `_run_auto_execute_command()` in `agentic_devtools/cli/workflows/worktree_setup.py` (L2133–2267) (FR-001, FR-003)
- [ ] T013 [US1] After state dir resolution in `_run_auto_execute_command`, call `write_pin_file(state_dir, workflow=workflow, target_git_root=Path(worktree_path))` with try/except guard (FR-003,
  FR-008)
- [ ] T014 [US1] Add diagnostic log `print(f"   Resolved state directory: {state_dir!s}")` after state dir resolution in `_run_auto_execute_command` (FR-005)
- [ ] T015 [US1] Thread `workflow=workflow_name` through call sites at L3436 and L3500 in `setup_worktree_in_background_sync()` in `agentic_devtools/cli/workflows/worktree_setup.py` (FR-001)
- [ ] T016 [US1] Verify T008–T011 tests pass (GREEN) (FR-001, FR-003, FR-004, FR-007)

## Phase 4: User Story 2 — Canonical State Path Remains Stable (P1)

- [ ] T017 [US2] Write failing happy-path test for `env_override` branch pin write in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py` — verify pin written when `AGENTIC_DEVTOOLS_STATE_DIR` is set (FR-002, FR-006)
- [ ] T018 [US2] In `agentic_devtools/cli/workflows/commands.py` L374–385, add `write_pin_file(resolved_state_dir, workflow="pull-request-review")` in the `if env_override:` branch with try/except
  (FR-002, FR-006)
- [ ] T019 [US2] Identify and apply the same `write_pin_file` pattern to other workflow initiation functions in `commands.py` that have `env_override` branches (FR-001, FR-006)
- [ ] T020 [US2] Verify T017 test passes (GREEN) (FR-002, FR-006)
- [ ] T021 [US2] [P] Add diagnostic logging in `agentic_devtools/cli/copilot/auto_start.py` (~L498) — print resolved state path to stderr after `get_state_file_path()` (FR-005, FR-007)
- [ ] T022 [US2] Write happy-path test verifying diagnostic output is emitted in `tests/unit/cli/copilot/auto_start/test_copilot_auto_start_cmd.py` (FR-005, FR-007)

## Phase 5: User Story 3 — Existing Single-Repo Workflows Keep Working (P2)

- [ ] T023 [US3] [P] Write tests in `tests/unit/state/test_write_pin_file.py` verifying `target_git_root=None` preserves existing auto-detect behavior (NFR-001, FR-007)
- [ ] T024 [US3] [P] Write tests in `tests/unit/state/test_clear_workflow_state.py` verifying cleanup with matching workflow deletes pin (FR-007)
- [ ] T025 [US3] [P] Write tests in `tests/unit/state/test_clear_workflow_state.py` verifying cleanup with non-matching workflow does NOT delete pin (FR-007)
- [ ] T026 [US3] [P] Write tests in `tests/unit/state/test_clear_workflow_state.py` verifying `force_delete=True` deletes pin regardless of workflow (FR-007)
- [ ] T027 [US3] Verify all existing state resolution tests pass unchanged — confirm `get_state_dir()` behavior with no pin file is identical to current (NFR-001, FR-007)
- [ ] T028 [US3] Verify T023–T026 tests pass (GREEN) (FR-007, NFR-001)

## Final Phase: Polish & Cross-Cutting

- [ ] T029 Run full test suite with `agdt-test` + `agdt-task-wait` to confirm no regressions (FR-001, FR-004, FR-007, NFR-001)
- [ ] T030 Run `bash scripts/targeted-checks.sh` for lint, format, type-check, and coverage validation
- [ ] T031 Verify FR-001 (single canonical state dir per run) via integration: mock full flow source→auto-execute→auto-start resolving same dir
- [ ] T032 Verify FR-004 (state readable by first `@agdt.advance-workflow`) via test asserting workflow state written by auto-execute is loadable from pin-resolved dir
- [ ] T033 Commit with `agdt-git-save-work` using message
  `fix([#1913](https://github.com/ayaiayorg/agentic-devtools/issues/1913)): resolve state directory mismatch between auto-execute and VS Code auto-start`
  and footer `[#1913](https://github.com/ayaiayorg/agentic-devtools/issues/1913)`

---
*Generated by Copilot SDK (claude-opus-4.6)*
