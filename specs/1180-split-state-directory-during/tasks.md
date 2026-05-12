# Tasks: Pin File for State Directory Resolution (#1180)

## Phase 1: Setup

- [ ] T001 Add pin file constants to `agentic_devtools/state.py` — define `PIN_FILENAME = "pinned-state-dir.json"`, `RECOGNIZED_PIN_WORKFLOWS = frozenset({"pull-request-review"})`,
  `DEFAULT_PIN_TTL_HOURS = 24`
- [ ] T002 Ensure test directory `tests/unit/state/` exists with `__init__.py` — verify the directory is present (it already exists in the repo); then create the following test files:
  `test_write_pin_file.py`, `test_read_and_validate_pin_file.py`, `test_delete_pin_file.py`, `test_refresh_pin_file_ttl.py` (FR-001, FR-003, FR-010)

## Phase 2: Foundational — Pin File Infrastructure

- [ ] T003 Write failing tests for `write_pin_file()` in `tests/unit/state/test_write_pin_file.py` — cover happy path (absolute path written atomically via `os.replace()`), relative path resolved to
  absolute, `workflow` field set, `created_utc` ISO-8601, `ttl_hours` default 24, atomic write-to-temp-then-rename pattern (FR-001)
- [ ] T004 Write failing tests for `read_and_validate_pin_file()` in `tests/unit/state/test_read_and_validate_pin_file.py` — cover: valid pin honored (FR-001, FR-002), expired TTL ignored with
  `[agdt]` stderr diagnostic (FR-003 check 3), invalid JSON ignored (FR-003 check 5), missing fields ignored (FR-003 check 4), `state_dir` outside repo root rejected (FR-003 check 2), non-existent
  uncreatable path rejected (FR-003 check 1), unrecognized workflow ignored (FR-003 check 4), relative `state_dir` rejected, `workflow` field gating for review-only scope (FR-001)
- [ ] T005 [P] Write failing tests for `delete_pin_file()` in `tests/unit/state/test_delete_pin_file.py` — cover: file exists and is deleted, file absent is silent no-op (FR-001)
- [ ] T006 [P] Write failing tests for `refresh_pin_file_ttl()` in `tests/unit/state/test_refresh_pin_file_ttl.py` — cover: existing valid pin has `created_utc` refreshed (FR-010), non-existent pin is
  no-op, invalid pin is no-op, atomic write used
- [ ] T007 Implement `write_pin_file(state_dir, workflow, ttl_hours=24)` in `agentic_devtools/state.py` — locate `.agdt/` via `_get_git_repo_root()`, resolve `state_dir` to absolute via
  `Path.resolve()`, write JSON atomically using temp-file + `os.replace()` (FR-001), return pin file path
- [ ] T008 Implement `read_and_validate_pin_file(git_root)` in `agentic_devtools/state.py` — read `.agdt/pinned-state-dir.json`, validate JSON parseable (FR-003 check 5), required fields present
  (FR-003 check 4), `workflow` in `RECOGNIZED_PIN_WORKFLOWS` (FR-003 check 4, FR-001), `state_dir` is absolute, `state_dir` inside repo root (FR-003 check 2), `created_utc` + `ttl_hours` not expired
  (FR-003 check 3), `state_dir` exists or creatable (FR-003 check 1), emit `[agdt]` diagnostic to stderr on failure (FR-009), return `Path` or `None`
- [ ] T009 [P] Implement `delete_pin_file(git_root=None)` in `agentic_devtools/state.py` — delete `.agdt/pinned-state-dir.json` if exists, silent no-op if absent
- [ ] T010 [P] Implement `refresh_pin_file_ttl()` in `agentic_devtools/state.py` — read existing pin, update `created_utc` to current UTC, write atomically, no-op if pin absent or invalid (FR-010)
- [ ] T011 Run pin file unit tests green (FR-001, FR-003, FR-009, FR-010) — execute:

  ```bash
  agdt-test-pattern tests/unit/state/test_write_pin_file.py tests/unit/state/test_read_and_validate_pin_file.py tests/unit/state/test_delete_pin_file.py tests/unit/state/test_refresh_pin_file_ttl.py -v
  ```

## Phase 3: User Story 1 — Consistent State Directory During Review Initiation (US1)

- [ ] T012 Write failing tests for modified `get_state_dir()` pin file resolution in `tests/unit/state/test_get_state_dir.py` — cover: pin file honored as step 2 when valid (FR-002 step 2), env
  var still takes priority over pin (FR-002 step 1, FR-006), expired pin falls through to bootstrap (FR-003, FR-007), invalid pin falls through to bootstrap (FR-003, FR-007), no pin file uses existing
  bootstrap chain unchanged (FR-007), diagnostic logging records resolution path with `[agdt]` prefix to stderr (FR-009), pin with `state_dir` that doesn't exist but is creatable succeeds (FR-008)
- [ ] T013 Modify `get_state_dir()` in `agentic_devtools/state.py` to insert pin file check as step 2 in resolution chain — after env var check (FR-002 step 1), call
  `read_and_validate_pin_file(git_root)` (FR-002 step 2), if valid `mkdir` + return pinned `state_dir`, else fall through to bootstrap (FR-002 steps 3-4, FR-007), emit scoped diagnostics to stderr
  with `[agdt]` prefix using module-level `_pin_logged` flag for once-per-process logging (FR-009), validate resolved directory exists or can be created (FR-008)
- [ ] T014 Ensure `get_state_dir()` with env var set bypasses both pin file and bootstrap reads for O(1) performance — verify no file I/O when `AGENTIC_DEVTOOLS_STATE_DIR` is set (NFR-001,
  FR-002 step 1, FR-006)
- [ ] T015 Run modified `get_state_dir()` tests green (FR-002, FR-003, FR-007, FR-008, FR-009) — execute `agdt-test-pattern tests/unit/state/test_get_state_dir.py -v`

## Phase 4: User Story 2 — Environment-Based State Directory Propagation (US2)

- [ ] T016 Write failing tests for `run_in_background()` env var inheritance in `tests/unit/background_tasks/test_run_in_background.py` — mock `subprocess.Popen`, assert `env` dict contains
  `AGENTIC_DEVTOOLS_STATE_DIR` when parent process has it set (FR-005)
- [ ] T017 Verify `run_in_background()` in `agentic_devtools/background_tasks.py` inherits `AGENTIC_DEVTOOLS_STATE_DIR` via `os.environ.copy()` — confirm existing `env = os.environ.copy()`
  pattern naturally propagates the env var (FR-005), add explicit test, no code change expected
- [ ] T018 Write failing test for `setup_pull_request_review()` skipping bootstrap write when env var set in `tests/unit/cli/azure_devops/review_commands/test_setup_pull_request_review.py` —
  verify `set_bootstrap_state()` is NOT called when `AGENTIC_DEVTOOLS_STATE_DIR` is in environment (FR-004)
- [ ] T019 Modify `setup_pull_request_review()` in `agentic_devtools/cli/azure_devops/review_commands.py` — guard `set_bootstrap_state(worktree_key=...)` call with `if not
  os.environ.get("AGENTIC_DEVTOOLS_STATE_DIR"):` (FR-004)
- [ ] T020 Write failing test for `initiate_pull_request_review_workflow()` writing pin file and setting env var in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py` — verify pin file written with correct `workflow` field (FR-001), `AGENTIC_DEVTOOLS_STATE_DIR` set in `os.environ`
  before spawning background tasks (FR-005, FR-001)
- [ ] T021 Modify `initiate_pull_request_review_workflow()` in `agentic_devtools/cli/workflows/commands.py` — after bootstrap scope is set and state dir resolved, call `write_pin_file(state_dir,
  workflow="pull-request-review")` (FR-001), then set `os.environ["AGENTIC_DEVTOOLS_STATE_DIR"] = str(state_dir)` for child process inheritance (FR-001, FR-005)
- [ ] T022 Run propagation tests green (FR-001, FR-004, FR-005) — execute:

  ```bash
  agdt-test-pattern tests/unit/background_tasks/test_run_in_background.py tests/unit/cli/azure_devops/review_commands/test_setup_pull_request_review.py tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py -v
  ```

## Phase 5: User Story 3 — No Duplicate State Directories (US3)

- [ ] T023 Write tests verifying single state directory for Scenario A (both `--pull-request-id` and `--issue-key`) in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py` — assert all state operations resolve to exactly one directory when setup
  background task runs concurrently (FR-001, FR-005)
- [ ] T024 Write tests verifying single state directory for Scenario B (only `--pull-request-id` from existing worktree) in
  `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py` — assert bootstrap modification by setup task does not cause concurrent
  commands to see a different directory (FR-001, FR-004)
- [ ] T025 Run no-duplicate tests green (FR-001, FR-004, FR-005) — execute `agdt-test-pattern tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py -v`

## Phase 6: User Story 4 — Backward Compatibility (US4)

- [ ] T026 Write tests verifying non-review workflows are unaffected in `tests/unit/state/test_get_state_dir.py` — assert `get_state_dir()` without env var or pin file uses existing bootstrap
  chain identically (FR-007, NFR-004)
- [ ] T027 Write tests verifying empty `AGENTIC_DEVTOOLS_STATE_DIR` string treated as unset in `tests/unit/state/test_get_state_dir.py` — assert empty string falls through to bootstrap
  resolution (edge case #2, FR-002)
- [ ] T028 Run backward compatibility tests green (FR-002, FR-007) — execute `agdt-test-pattern tests/unit/state/test_get_state_dir.py -v`

## Phase 7: User Story 5 — Concurrent Workflow Isolation (US5)

- [ ] T029 Write tests verifying worktree-scoped env var isolation in `tests/unit/state/test_get_state_dir.py` — assert two processes with different `AGENTIC_DEVTOOLS_STATE_DIR` values resolve
  to different directories (FR-006)
- [ ] T030 Write tests verifying concurrent pin file overwrite (last writer wins) in `tests/unit/state/test_write_pin_file.py` — assert second `write_pin_file()` atomically overwrites first
  (edge case #9, FR-001)
- [ ] T031 Run isolation tests green (FR-001, FR-006) — execute `agdt-test-pattern tests/unit/state/test_get_state_dir.py tests/unit/state/test_write_pin_file.py -v`

## Phase 8: Pin File Cleanup

- [ ] T032 Write failing tests for pin file cleanup distinguishing unconditional vs conditional deletion in `tests/unit/state/test_clear_workflow_state.py` — assert: (a) `clear_workflow_state()`
  called from `clear_workflow_cmd()` **unconditionally** deletes `.agdt/pinned-state-dir.json` regardless of the pin's `workflow` field (spec C5: `agdt-clear-workflow` is a deliberate reset action);
  (b) workflow-completion cleanup (called internally when a workflow reaches its terminal step) deletes the pin **only** when the pin's `workflow` field matches the completing workflow name; pin
  preserved if `workflow` field differs (FR-001)
- [ ] T033 Implement pin file cleanup in `agentic_devtools/state.py` — add `force_delete` parameter to `clear_workflow_state()`: when `force_delete=True` (used by `clear_workflow_cmd()`),
  unconditionally delete `.agdt/pinned-state-dir.json` if it exists (spec C5); when `force_delete=False` (default, used by workflow-completion handlers), read pin file `workflow` field and delete only
  if it matches the completing workflow name (FR-001). `clear_workflow_cmd()` passes `force_delete=True` to implement the spec's unconditional-delete semantics
- [ ] T034 Write failing test verifying `clear_workflow_cmd()` passes `force_delete=True` to `clear_workflow_state()` in `tests/unit/cli/state/test_clear_workflow_cmd.py` — assert that calling
  `clear_workflow_cmd()` results in `clear_workflow_state(force_delete=True)` being invoked (unconditional pin deletion per spec C5); separately verify that workflow-completion paths call
  `clear_workflow_state()` without `force_delete` (conditional deletion) (FR-001)
- [ ] T035 Write failing test for `advance_workflow_cmd()` refreshing pin TTL in `tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py` — assert
  `refresh_pin_file_ttl()` called after successful advancement (FR-010)
- [ ] T036 Modify `advance_workflow_cmd()` in `agentic_devtools/cli/workflows/__init__.py` — call `refresh_pin_file_ttl()` after successfully advancing the workflow step (FR-010)
- [ ] T037 Run cleanup tests green (FR-001, FR-010) — execute:

  ```bash
  agdt-test-pattern tests/unit/cli/state/test_clear_workflow_cmd.py tests/unit/state/test_clear_workflow_state.py tests/unit/cli/workflows/commands/test_advance_workflow_cmd.py -v
  ```

## Phase 9: Edge Case Coverage

- [ ] T038 [P] Write test for non-existent `AGENTIC_DEVTOOLS_STATE_DIR` directory that can be created in `tests/unit/state/test_get_state_dir.py` — assert directory is created and returned (edge case
  #1, FR-008)
- [ ] T039 [P] Write test for non-existent `AGENTIC_DEVTOOLS_STATE_DIR` directory that cannot be created in `tests/unit/state/test_get_state_dir.py` — assert clear error raised (edge case #1, FR-008)
- [ ] T040 [P] Write test for multiple concurrent background tasks inheriting same env var in `tests/unit/background_tasks/test_run_in_background.py` — assert all spawned subprocesses get identical
  `AGENTIC_DEVTOOLS_STATE_DIR` (edge case #3, FR-005)
- [ ] T041 [P] Write test for manually set `AGENTIC_DEVTOOLS_STATE_DIR` respected over pin file in `tests/unit/state/test_get_state_dir.py` — assert env var takes priority (edge case #4, FR-002)
- [ ] T042 [P] Write test for bootstrap modification having no effect when env var set in `tests/unit/state/test_get_state_dir.py` — assert resolution unchanged despite bootstrap file changes (edge
  case #5, FR-006, NFR-005)
- [ ] T043 [P] Write test for stale pin file after crash expiring via TTL in `tests/unit/state/test_read_and_validate_pin_file.py` — assert expired pin ignored with diagnostic (edge case #7, FR-003)
- [ ] T044 [P] Write test for pin file pointing to deleted directory in `tests/unit/state/test_read_and_validate_pin_file.py` — assert pin ignored, falls through to bootstrap (edge case #8, FR-003)
- [ ] T045 [P] Write test for truncated/corrupt pin file in `tests/unit/state/test_read_and_validate_pin_file.py` — assert ignored with diagnostic (edge case #10, FR-003)

## Phase 10: Polish & Cross-Cutting

- [ ] T046 Run full test suite with coverage via `bash scripts/run-pr-checks.sh`
  (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-009, FR-010) — verify zero regressions, 100% coverage on modified files (NFR-003),
  all existing tests pass without modification
- [ ] T047 Run ruff lint and format checks — execute `ruff check . && ruff format --check .`, fix any violations
- [ ] T048 Verify cross-platform atomic write safety (FR-001) — confirm `os.replace()` usage follows existing `_atomic_write_json` pattern in
  `agentic_devtools/cli/azure_devops/review_state.py` for POSIX and Windows same-volume atomicity (NFR-002)
- [ ] T049 Update `agentic_devtools/state.py` module docstring to document the new pin file resolution step in the priority chain and reference FR-001, FR-002, FR-003

---
*Generated by Copilot SDK (claude-opus-4.6)*
