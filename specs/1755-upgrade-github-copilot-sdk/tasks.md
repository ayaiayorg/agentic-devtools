# Tasks: Upgrade to github-copilot-sdk v1

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
| --- | --- | --- |
| Phase 1: Setup | — | Branch/setup work before implementation tasks begin |
| Phase 2: Foundational — Dependency Constraint | Phase 1: Dependency Constraint Update | Updates the SDK version constraint before code changes |
| Phase 3: User Story 1 — Upgrade dependency and imports | Phase 2: Production Code — Import Path Migration; Phase 3: CI Workflow Updates | Applies the v1 import migration in production code and workflows |
| Phase 4: User Story 2 — Remove compatibility shim | Phase 4: Test Updates | Updates tests to match the v1-only import paths |
| Phase 5: User Story 3 — Keep external contracts stable | Phase 5: Validation | Runs the full-suite validation checkpoint |
| Final Phase: Polish & Cross-Cutting Validation | Phase 5: Validation | Performs cross-cutting verification and final save-work steps |

---

## Phase 1: Setup

- [ ] T001 Create feature branch from `speckit/1755/phase-2-clarify` for implementation work

## Phase 2: Foundational — Dependency Constraint

- [ ] T002 Update `pyproject.toml` `[project.optional-dependencies].copilot-sdk` from `"github-copilot-sdk>=0.1.0,<1.0.0"` to `"github-copilot-sdk>=1.0.0,<2.0.0"`
  - Depends on: T001
  - Satisfies: FR-001, SC-001

- [ ] T003 Reinstall package with updated dependency: `pip install -e ".[dev,copilot-sdk]"`
  - Depends on: T002

## Phase 3: User Story 1 — Upgrade dependency and imports (P1)

### Production code updates (each task replaces the shim AND updates imports in a single edit)

- [ ] T004 [P] [US1] Replace shim block 1 in `agentic_devtools/cli/ci/github_provider.py` (~lines 1496–1509): collapse nested try/except into single `try` with v1 imports
  (`from copilot import CopilotClient` / `from copilot.config import SubprocessConfig` / `from copilot.session import PermissionHandler`) + retained outer `except Exception` graceful degradation
  - Depends on: T003
  - Satisfies: FR-002, FR-003, SC-002, SC-003

- [ ] T005 [P] [US1] Replace shim block 2 in `agentic_devtools/cli/ci/github_provider.py` (~lines 1612–1625): same pattern as T004
  - Depends on: T003
  - Satisfies: FR-002, FR-003, SC-002, SC-003

- [ ] T006 [P] [US1] Replace shim block 3 in `agentic_devtools/cli/ci/github_provider.py` (~lines 2550–2562): same pattern as T004
  - Depends on: T003
  - Satisfies: FR-002, FR-003, SC-002, SC-003

- [ ] T007 [P] [US1] Replace shim block 4 in `agentic_devtools/cli/ci/github_provider.py` (~lines 2677–2687): same pattern as T004
  - Depends on: T003
  - Satisfies: FR-002, FR-003, SC-002, SC-003

- [ ] T008 [P] [US1] Replace shim block in `.github/scripts/speckit-trigger/copilot_generate.py` (~lines 23–55): collapse nested try/except into single `try` with v1 imports + retained outer
  `except Exception` graceful degradation
  - Depends on: T003
  - Satisfies: FR-002, FR-003, SC-002, SC-003

### CI Workflow updates

- [ ] T009 [P] [US1] Update `.github/workflows/ai-pr-loop.yml` (~lines 63–65): change install constraint to `>=1.0.0,<2.0.0` and update smoke-check to
  `from copilot import CopilotClient; from copilot.config import SubprocessConfig; from copilot.session import PermissionHandler`
  - Depends on: T003
  - Satisfies: FR-005

- [ ] T010 [P] [US1] Update `.github/workflows/speckit-phase-progression.yml` (~lines 484–486): same changes as T009
  - Depends on: T003
  - Satisfies: FR-005

## Phase 4: User Story 2 — Remove compatibility shim (P1)

### Test updates (mock targets + fallback test removal)

- [ ] T011 [P] [US2] Update `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`: remove `_build_sdk_modules_no_subprocess_config` helper and
  `test_run_prompt_via_sdk_fallback_import_path_succeeds` test; update remaining mocks to target `copilot.config.SubprocessConfig` via `sys.modules` patching
  - Depends on: T004, T005, T006, T007
  - Satisfies: FR-004, SC-004

- [ ] T012 [P] [US2] Update `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk.py`: remove `_build_sdk_mocks_no_subprocess_config` helper and fallback test; update mocks to
  target `copilot.config` module
  - Depends on: T004, T005, T006, T007
  - Satisfies: FR-004, SC-004

- [ ] T013 [P] [US2] Update `tests/unit/cli/ci/github_provider/test__resolve_conflicted_file_content_via_sdk.py`: remove fallback helper/test; update mocks to target `copilot.config` module
  - Depends on: T004, T005, T006, T007
  - Satisfies: FR-004, SC-004

- [ ] T014 [P] [US2] Update `tests/workflows/test_copilot_generate.py`: update mock targets from `copilot.SubprocessConfig` to `copilot.config.SubprocessConfig`; remove any fallback-path assertions
  - Depends on: T008
  - Satisfies: FR-004, SC-004

## Phase 5: User Story 3 — Keep external contracts stable (P2)

- [ ] T015 [US3] Run `agdt-test` to start the full test suite, then `agdt-task-wait` to wait for completion, and verify all tests pass with v1 SDK installed
  - Depends on: T011, T012, T013, T014
  - Satisfies: NFR-001, NFR-003, SC-004

- [ ] T016 [US3] Run `bash scripts/targeted-checks.sh` (ruff lint/format-check, mypy, test-structure validation, and per-file coverage on changed source files) to confirm checks are clean
  - Depends on: T015
  - Satisfies: NFR-001

## Final Phase: Polish & Cross-Cutting Validation

- [ ] T017 Verify zero remaining legacy import patterns in code/workflow/test paths:
  `grep -r "from copilot import.*SubprocessConfig" agentic_devtools/ .github/workflows/ .github/scripts/ tests/` returns no results
  - Depends on: T004, T005, T006, T007, T008, T009, T010, T011, T012, T013, T014
  - Satisfies: SC-002

- [ ] T018 Verify zero remaining shim blocks: `grep -rn "except.*primary_exc\|except.*first_exc" agentic_devtools/ .github/` returns no results
  - Depends on: T004, T005, T006, T007, T008, T011, T012, T013, T014
  - Satisfies: SC-003

- [ ] T019 Run `python scripts/validate_test_structure.py` to ensure test file structure compliance
  - Depends on: T011, T012, T013, T014

- [ ] T020 Commit and push using `agdt-git-save-work` with conventional commit message referencing #1755
  - Depends on: T015, T016, T017, T018, T019
  - Satisfies: SC-005

## Dependency Graph Summary

```text
T001 → T002 → T003
T003 → T004, T005, T006, T007, T008, T009, T010 (parallel)
T004, T005, T006, T007 → T011, T012, T013 (parallel)
T008 → T014
T011, T012, T013, T014 → T015 → T016
T004, T005, T006, T007, T008, T009, T010, T011, T012, T013, T014 → T017, T018 (parallel)
T011, T012, T013, T014 → T019
T015, T016, T017, T018, T019 → T020
```

## Requirement Traceability

| Requirement | Tasks |
| --- | --- |
| FR-001 (pyproject.toml constraint) | T002 |
| FR-002 (v1 import paths) | T004, T005, T006, T007, T008 |
| FR-003 (remove shim, retain graceful degradation) | T004, T005, T006, T007, T008 |
| FR-004 (test mock updates) | T011, T012, T013, T014 |
| FR-005 (CI workflow updates) | T009, T010 |
| NFR-001 (stable public contracts) | T015, T016 |
| NFR-002 (SDK<1 intentionally dropped) | T002 |
| NFR-003 (100% test pass) | T015 |
| SC-001 | T002 |
| SC-002 | T004–T008, T017 |
| SC-003 | T004–T008, T018 |
| SC-004 | T011–T014, T015 |
| SC-005 | T020 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
