# Tasks: Restructure setup-dev-tools into modular .agdt-managed scripts

**Issue**: [#1322](https://github.com/ayaiayorg/agentic-devtools/issues/1322)

## Task Markers

| Marker | Meaning |
|--------|---------|
| `[P]` | Parallelizable — this task has no sequential dependency on the immediately preceding task within its phase and can be worked on concurrently |
| `[USn]` | User Story reference (e.g., `[US1]` = User Story 1) |
| `[FR-nnn]` | Functional Requirement traceability tag |
| `[NFR-nnn]` | Non-Functional Requirement traceability tag |

---

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create package `agentic_devtools/cli/setup/script_generators/` with `__init__.py`
- [ ] T002 [FR-001] [FR-012] Create directory hierarchy `tests/unit/cli/setup/script_generators/` with `__init__.py` files at each level, including all subdirectories referenced by later tasks:
  `required_setup/`, `configured_setup/`, `complete_setup/`, `root_entry_point/`, `legacy_migration/`, `repo_specific/`, `gitignore_updater/`, `atomic_write/`
- [ ] T003 Create utility module `agentic_devtools/cli/setup/script_generators/atomic_write.py` with atomic file write helper (write-to-temp + rename)

---

## Phase 2: Foundational — Blocking Prerequisites

- [ ] T004 Create `agentic_devtools/cli/setup/script_generators/constants.py` defining `ORCHESTRATOR_MARKER = "# AGDT-MANAGED-ORCHESTRATOR"`, tool registry dict, and script filename constants
- [ ] T005 Create `agentic_devtools/cli/setup/script_generators/repo_root.py` with `get_git_repo_root()` helper using `git rev-parse --show-toplevel` (returns `None` in non-git contexts)

---

## Phase 3: User Story 1 — Corrupted Install Self-Repair (P1)

- [ ] T006 [US1] [FR-001] Test `detect_corrupted_artifacts()` — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/required_setup/test_detect_corrupted_artifacts.py`
- [ ] T007 [US1] [FR-002] Test `cleanup_artifacts()` — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/required_setup/test_cleanup_artifacts.py`
- [ ] T008 [US1] [FR-003] Test `install_package()` — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/required_setup/test_install_package.py`
- [ ] T009 [US1] [FR-004] Test `setup_git_hooks()` — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/required_setup/test_setup_git_hooks.py`
- [ ] T010 [US1] [FR-012] Test `generate_required_setup_script()` — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/required_setup/test_generate_required_setup.py`
- [ ] T011 [US1] Implement `agentic_devtools/cli/setup/script_generators/required_setup.py` — `detect_corrupted_artifacts()` scanning site-packages for `~gentic-devtools`, `~gentic_devtools`,
  `.dist-info` without RECORD, and `_editable_impl_agentic_devtools.pth` (FR-001)
- [ ] T012 [US1] Implement `cleanup_artifacts()` in `required_setup.py` — removes all detected corrupted artifacts with permission error handling for read-only site-packages (FR-002)
- [ ] T013 [US1] Implement `install_package()` in `required_setup.py` — runs `sys.executable -m pip install --upgrade agentic-devtools` after cleanup to install latest PyPI version (FR-003)
- [ ] T014 [US1] Implement `setup_git_hooks()` in `required_setup.py` — configures `core.hooksPath` to `.githooks`, creates directory if needed, warns on overwrite (FR-004)
- [ ] T015 [US1] Implement `generate_required_setup_script()` in `required_setup.py` — returns complete stdlib-only script content with `--foreground` flag support (FR-012) handling edge cases:
  read-only site-packages, non-git contexts, multiple orphaned artifacts
- [ ] T016 [US1] [FR-001] [FR-002] [FR-004] Edge-case tests: read-only site-packages, non-git context, multiple orphaned artifacts in
  `tests/unit/cli/setup/script_generators/required_setup/test_edge_cases.py`

---

## Phase 4: User Story 2 — Modular Script Generation via agdt-setup (P1)

- [ ] T017 [US2] [FR-005] Test `generate_configured_setup_script()` — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/configured_setup/test_generate_configured_setup.py`
- [ ] T018 [US2] [FR-005] Test `render_tool_installs()` — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/configured_setup/test_render_tool_installs.py`
- [ ] T019 [P] [US2] Implement `agentic_devtools/cli/setup/script_generators/configured_setup.py` — `generate_configured_setup_script(selected_tools: list[str])` producing stdlib-only script with only
  selected tools (FR-005), idempotent output (NFR-003)
- [ ] T020 [US2] [FR-006] Test `agdt-setup` script-phase output in
  `tests/unit/cli/setup/script_generators/test_setup_integration.py` — FR-006: managed scripts refreshed per run, `setup-dev-tools.py` contains marker
- [ ] T021 [US2] Implement script generation phase in `agentic_devtools/cli/setup/commands.py` — new phase at end of `setup_cmd()` that generates all managed scripts using atomic writes (FR-006,
  FR-015), always overwriting `agentic-devtools-required-setup.py`, `agentic-devtools-configured-setup.py`, `agentic-devtools-complete-setup.py`, and root `setup-dev-tools.py`
- [ ] T022 [US2] Wire tool selection prompts in `agdt-setup` to pass selected tools to `generate_configured_setup_script()` in `agentic_devtools/cli/setup/commands.py`

---

## Phase 5: User Story 3 — Orchestrated Complete Setup (P2)

- [ ] T023 [US3] [FR-009] Test `generate_complete_setup_script()` — failure scenarios in `tests/unit/cli/setup/script_generators/complete_setup/test_generate_complete_setup.py`
- [ ] T024 [US3] [FR-010] Test `generate_root_entry_point()` — failure scenarios in `tests/unit/cli/setup/script_generators/root_entry_point/test_generate_root_entry_point.py`
- [ ] T025 [P] [US3] Implement `agentic_devtools/cli/setup/script_generators/complete_setup.py` — generates orchestrator that calls required then configured with fail-fast (FR-009), `--foreground`
  propagation (FR-011)
- [ ] T026 [P] [US3] Implement `agentic_devtools/cli/setup/script_generators/root_entry_point.py` — generates `setup-dev-tools.py` with `# AGDT-MANAGED-ORCHESTRATOR` marker, fail-fast chain to
  `.agdt/` then repo-specific (FR-010), missing `.agdt/` directory detection with clear error message
- [ ] T027 [US3] [FR-009] [FR-010] Fail-fast chain tests: required-setup failure stops configured-setup, complete-setup failure stops repo-specific in
  `tests/unit/cli/setup/script_generators/test_fail_fast.py`
- [ ] T028 [US3] [FR-010] Edge-case test: missing `.agdt/` directory yields actionable error in `tests/unit/cli/setup/script_generators/root_entry_point/test_missing_agdt_dir.py`

---

## Phase 6: User Story 4 — Backward Compatibility with Existing Repos (P2)

- [ ] T029 [US4] [FR-013] Test `detect_legacy_script()` — failure scenarios in `tests/unit/cli/setup/script_generators/legacy_migration/test_detect_legacy.py`
- [ ] T030 [US4] [FR-013] Test `migrate_legacy_content()` — failure scenarios in `tests/unit/cli/setup/script_generators/legacy_migration/test_migrate_content.py`
- [ ] T031 [US4] Implement `agentic_devtools/cli/setup/script_generators/legacy_migration.py` — `detect_legacy_script()` checking absence of marker (FR-013), `migrate_legacy_content()` moving content
  to `setup-repo-specific-dev-tools.py` with append-below-separator when target exists
- [ ] T032 [US4] Implement `agentic_devtools/cli/setup/script_generators/repo_specific.py` — `generate_repo_specific_stub()` creating initial content with "No repo-specific dev tools configured" log
  message and guidance comment (FR-007, FR-008)
- [ ] T033 [US4] [FR-007] [FR-008] Test repo-specific script preservation (FR-007) and stub initial content (FR-008) in `tests/unit/cli/setup/script_generators/repo_specific/test_never_overwrite.py`
- [ ] T034 [US4] Integrate legacy migration into `agdt-setup` script generation phase in `agentic_devtools/cli/setup/commands.py` — call `detect_legacy_script()` before generating root entry point

---

## Phase 7: User Story 5 — Git Hooks Setup via required-setup (P3)

- [ ] T035 [US5] [FR-004] Test `setup_git_hooks()` in non-git context — expects skip with info message in `tests/unit/cli/setup/script_generators/required_setup/test_setup_git_hooks_non_git.py`
- [ ] T036 [US5] [FR-004] Test `setup_git_hooks()` warning when `core.hooksPath` differs from `.githooks` in
  `tests/unit/cli/setup/script_generators/required_setup/test_setup_git_hooks_overwrite.py`
- [ ] T037 [US5] [FR-004] Verify acceptance gate: confirm T035 + T036 tests pass against T014 code (no new code expected)

---

## Phase 8: .gitignore Update (P2)

- [ ] T038 [P] [FR-014] Test `.gitignore` updater — happy-path and failure scenarios in `tests/unit/cli/setup/script_generators/gitignore_updater/test_update_gitignore.py`
- [ ] T039 [P] [FR-014] Implement `agentic_devtools/cli/setup/script_generators/gitignore_updater.py` — replaces `.agdt/` with `.agdt/*`, adds `!.agdt/agentic-devtools-*.py` negation, idempotent (FR-014)
- [ ] T040 [FR-014] Integrate `.gitignore` updater into `agdt-setup` script generation phase in `agentic_devtools/cli/setup/commands.py`

---

## Phase 9: Polish & Cross-Cutting

- [ ] T041 [FR-015] Integration test for full `agdt-setup` flow with mocked filesystem in `tests/unit/cli/setup/script_generators/test_full_flow_integration.py`
- [ ] T042 [FR-015] Concurrency safety test for atomic-write consistency in `tests/unit/cli/setup/script_generators/atomic_write/test_concurrent_writes.py`
- [ ] T043 [FR-012] [NFR-001] Test that output scripts use only stdlib imports (no agentic-devtools imports) in `tests/unit/cli/setup/script_generators/test_stdlib_only.py`
- [ ] T044 [P] [FR-012] [NFR-001] Test cross-platform path usage — `pathlib.Path` / `os.path` exclusively (NFR-001) in `tests/unit/cli/setup/script_generators/test_cross_platform.py`
- [ ] T045 [P] [FR-011] Add `--foreground` flag to `setup-dev-tools.py` argument parser; propagate to inner scripts —
  see `tests/unit/cli/setup/script_generators/root_entry_point/test_foreground_flag.py`
- [ ] T046 [FR-015] Run `bash scripts/run-pr-checks.sh` to validate full test suite, linting, and formatting pass
- [ ] T047 Update `agentic_devtools/cli/setup/__init__.py` exports if new public API surfaces are needed

---

## Dependency Graph

```text
T001, T002, T003 → T004, T005
T004, T005 → T006–T016 (US1)
T004, T005 → T017–T022 (US2)
T011–T015 → T023–T028 (US3, depends on required-setup existing)
T021 → T029–T034 (US4, depends on setup integration point)
T014 → T035–T037 (US5, depends on git hooks impl)
T004 → T038–T040 (.gitignore)
All US phases → T041–T047 (polish)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
