# Tasks: Pin agentic-devtools Version & Guard agdt-setup

## Phase 1: Setup

- [ ] T001 Add `packaging>=21.0` to `[project.dependencies]` in `pyproject.toml` and install with `pip install -e .`
- [ ] T002 Create file `agentic_devtools/cli/setup/version_guard.py` (empty module) and file `agentic_devtools/cli/setup/gitignore_negations.py` (empty module);
  ensure parent directory `agentic_devtools/cli/setup/` exists with `__init__.py`
- [ ] T003 Scaffold the 1:1:1 unit-check directory structure with `__init__.py` for `version_guard` and `gitignore_negations` modules

## Phase 2: Foundational — Version Comparison & Gitignore Helpers

- [ ] T004 [P] Write failing happy-path and edge-case tests for `_fallback_compare(running, pinned) -> int` covering: normal versions, pre-release (`dev`, `rc`,
  `alpha`, `beta`), post-release, local metadata stripping (`+local`), segments with no leading digits, equal versions, padding shorter lists (FR-003, NFR-003 fallback rules)
- [ ] T005 [P] Write failing happy-path and edge-case tests for `compare_versions(running, pinned) -> int` covering: PEP 440 normal/pre-release/dev/post ordering
  via `packaging.version.Version`, fallback path when `packaging` is unavailable (FR-003), returns -1/0/1
- [ ] T006 [P] Write failing happy-path and negative tests for `check_version_guard(git_root, force_old_version) -> str | None` covering: no `project.json` →
  `None` (FR-010), no `agdt_version` key → `None` (FR-010), malformed `agdt_version` → `None` + warning (FR-011), older+no-force → `"block"` + stderr contains running version/required version/upgrade
  cmd/force flag (FR-004, FR-005), older+force → `"force"` + stderr warning about skipped repo files (FR-007, FR-009), equal version → `None` (FR-006), newer version → `None` (FR-006), force flag with
  equal/newer version → `None` silent no-op (US3/AS4)
- [ ] T007 [P] Write failing happy-path and edge-case tests for `ensure_root_gitignore_negations(git_root)` covering: insert negation rules after `.agdt/` line (FR-013), idempotent re-run,
  missing `.gitignore` file, no `.agdt/` rule in file, correct ordering `!.agdt/` then `!.agdt/config/` then `!.agdt/config/project.json`
- [ ] T008 Implement `_fallback_compare(running, pinned) -> int` in `agentic_devtools/cli/setup/version_guard.py` — segment-based comparison per NFR-003 rules (strip `+local`, decompose segments,
  suffix ordering, pad, lexicographic compare, fail-open on error)
- [ ] T009 Implement `compare_versions(running, pinned) -> int` in `agentic_devtools/cli/setup/version_guard.py` — use `packaging.version.Version` with try/except falling back to `_fallback_compare`
  (FR-003); log warning when fallback is used
- [ ] T010 Implement `check_version_guard(git_root, force_old_version) -> str | None` in `agentic_devtools/cli/setup/version_guard.py` — load `project.json` via `load_project_config`, read
  `agdt_version`, handle missing/malformed values (FR-010, FR-011), call `compare_versions`, emit error to stderr with running version + required version + upgrade command + force flag (FR-005), emit
  force-path warning (FR-009), return `"block"` / `"force"` / `None`
- [ ] T011 Implement `ensure_root_gitignore_negations(git_root: Path) -> bool` in `agentic_devtools/cli/setup/gitignore_negations.py` — idempotent insertion of `!.agdt/`, `!.agdt/config/`,
  `!.agdt/config/project.json` after the `.agdt/` ignore rule (FR-013); handle edge cases
- [ ] T012 Phase 2 gate: run unit checks for `version_guard` and `gitignore_negations` modules — all green
- [ ] T013 [P] Write integration test for `ensure_root_gitignore_negations(git_root)` — init temp git repo, write `.gitignore` with `.agdt/`, run helper,
  shell out to `git check-ignore .agdt/config/project.json` to confirm file is NOT ignored (FR-013)

## Phase 3: User Story 1 — Version Pinning on Successful Setup (P1)

- [ ] T014 [US1] Write failing happy-path tests for version pin write inside `_run_file_modifying_steps()`: assert `project.json` gains `agdt_version` matching `__version__` (FR-001, FR-002), assert existing
  keys preserved (FR-012), assert version write is last step (FR-001), assert version updates when newer (FR-006), assert no-op when equal version
- [ ] T015 [US1] Write failing happy-path tests for `ensure_root_gitignore_negations(git_root)` call inside `_run_file_modifying_steps()` after `ensure_agdt_gitignore()` (FR-013)
- [ ] T016 [US1] Add `ensure_root_gitignore_negations(git_root)` call inside `_run_file_modifying_steps()` immediately after existing `ensure_agdt_gitignore()` call in
  `agentic_devtools/cli/setup/commands.py` (FR-013)
- [ ] T017 [US1] Add version pin write as the LAST step inside `_run_file_modifying_steps()` in `agentic_devtools/cli/setup/commands.py`: load config, set `config["agdt_version"] = __version__`, save
  config (FR-001, FR-002, FR-006, FR-012)
- [ ] T018 [US1] Remove or update outdated console guidance in `setup_cmd()` that tells users to manually add `.agdt/` negation rules to root `.gitignore`
- [ ] T019 [US1] US1 gate: confirm all `agdt-setup` command checks pass

## Phase 4: User Story 2 — Block Downgrade on Older Version (P1)

- [ ] T020 [US2] Write failing happy-path and negative tests for version guard integration in `agdt-setup`: older version + no force → `sys.exit(1)` called (FR-004),
  `_run_file_modifying_steps` NOT called, local-only steps NOT called (FR-004 fail-fast), `agdt_version` NOT modified (FR-004 — no mutations occur)
- [ ] T021 [US2] Write failing test: `_get_git_repo_root()` is called BEFORE `check_version_guard()` (verify call ordering)
- [ ] T022 [US2] Move `git_root = _get_git_repo_root()` earlier in `setup_cmd()` — immediately after argparse parsing, before any local-only steps (NFR-001)
- [ ] T023 [US2] Insert version guard call after `git_root` detection in `setup_cmd()`: call `check_version_guard(git_root, args.force_old_version)`, if result is `"block"` → `sys.exit(1)` (FR-004);
  set `skip_repo_steps = (result == "force")`
- [ ] T024 [US2] When `skip_repo_steps` is True, skip call to `_run_file_modifying_steps()` and skip PR workflow invocation; local-only steps still execute (FR-007)
- [ ] T025 [US2] US2 gate: confirm all `agdt-setup` command checks pass

## Phase 5: User Story 3 — Force Override for Local-Only Steps (P2)

- [ ] T026 [US3] Add `--force-old-version` argparse argument to `setup_cmd()` (store_true, default False) in `agentic_devtools/cli/setup/commands.py`
- [ ] T027 [US3] Write failing tests: older + `--force-old-version` → exit 0, local-only steps run (cert prefetch, managed installs, dep check, env persist), `_run_file_modifying_steps()` NOT called
  (FR-007), PR workflow NOT invoked, `agdt_version` NOT modified (FR-008)
- [ ] T028 [US3] Write failing test: equal/newer version + `--force-old-version` → flag silently ignored, `agdt-setup` proceeds normally (US3/AS4)
- [ ] T029 [US3] Write failing tests for flag interactions: `--force-old-version` + `--skip-pr-workflow` both respected independently; `--force-old-version` + `--system-only` both respected
- [ ] T030 [US3] US3 gate: confirm all `agdt-setup` command checks pass

## Phase 6: User Story 4 — Clear Version Mismatch Messaging (P2)

- [ ] T031 [US4] Write failing tests: error message (block path) contains exact running version, exact required version, `python setup-dev-tools.py` command, and `--force-old-version` flag (FR-005)
- [ ] T032 [US4] Write failing tests: warning message (force path) explains local-only steps run but repo changes skipped, states mode is not recommended (FR-009)
- [ ] T033 [US4] Verify messaging implementation in `check_version_guard()` satisfies FR-005 and FR-009 — adjust formatting to match existing `agdt-setup` output style with `✓`/`⚠` emoji prefixes and
  `print(..., file=sys.stderr)` (NFR-002)
- [ ] T034 [US4] US4 gate: confirm all `version_guard` checks pass

## Phase 7: Polish & Cross-Cutting

- [ ] T035 Full suite gate — `agdt-test` + `agdt-task-wait` — all 2000+ pass
- [ ] T036 Structure gate — run the 1:1:1 structural validator — passes with new files
- [ ] T037 Run `bash scripts/run-pr-checks.sh` — all PR checks pass (SC-006)
- [ ] T038 Run `ruff check . && ruff format --check .` — no lint/format issues
- [ ] T039 Verify backward compatibility: repos without `agdt_version` in `project.json` proceed normally (SC-005, FR-010)

---
*Generated by Copilot SDK (claude-opus-4.6)*
