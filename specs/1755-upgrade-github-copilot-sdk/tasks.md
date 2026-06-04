# Tasks: Upgrade to github-copilot-sdk v1

## Phase 1: Setup

- [ ] T001 Create implementation branch from `speckit/1755/phase-2-clarify`

## Phase 2: Foundational — Dependency Constraint Update

- [ ] T002 [FR-001] Update `pyproject.toml` `[project.optional-dependencies].copilot-sdk` from `"github-copilot-sdk>=0.1.0,<1.0.0"` to `"github-copilot-sdk>=1.0.0,<2.0.0"` — `pyproject.toml`
- [ ] T003 Reinstall package with updated constraint: `pip install -e ".[copilot-sdk,dev]"`

## Phase 3: User Story 1 — Upgrade dependency and imports (P1)

### Tests (Red)

- [ ] T004 [P] [US1] Write assertion test verifying `from copilot.config import SubprocessConfig` is the only SubprocessConfig import pattern in production code —
  `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk.py`
- [ ] T005 [P] [US1] Write assertion test verifying no combined `from copilot import CopilotClient, SubprocessConfig` pattern exists in production code

### Production Code Updates

- [ ] T006 [US1] [FR-002] Update import block at lines ~1496–1509 in `agentic_devtools/cli/ci/github_provider.py` — replace shim with direct v1 imports: `from copilot import CopilotClient` / `from
  copilot.config import SubprocessConfig` / `from copilot.session import PermissionHandler`
- [ ] T007 [US1] [FR-002] Update import block at lines ~1612–1625 in `agentic_devtools/cli/ci/github_provider.py` — same v1 import pattern
- [ ] T008 [US1] [FR-002] Update import block at lines ~2550–2562 in `agentic_devtools/cli/ci/github_provider.py` — same v1 import pattern
- [ ] T009 [US1] [FR-002] Update import block at lines ~2677–2687 in `agentic_devtools/cli/ci/github_provider.py` — same v1 import pattern
- [ ] T010 [US1] [FR-002] Update import block in `.github/scripts/speckit-trigger/copilot_generate.py` — replace combined import with `from copilot import CopilotClient` / `from copilot.config import
  SubprocessConfig` / `from copilot.session import PermissionHandler`
- [ ] T011 [US1] [FR-005] Update `.github/workflows/ai-pr-loop.yml` — change install constraint to `>=1.0.0,<2.0.0` and smoke-check to `from copilot import CopilotClient; from copilot.config import
  SubprocessConfig; from copilot.session import PermissionHandler`
- [ ] T012 [US1] [FR-005] Update `.github/workflows/speckit-phase-progression.yml` — same install constraint and smoke-check changes

### Test Updates for v1 Mocks

- [ ] T013 [P] [US1] [FR-004] Update `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk.py` — change mock targets from `copilot.SubprocessConfig` to
  `copilot.config.SubprocessConfig`, update `sys.modules` patching to include `copilot.config` module
- [ ] T014 [P] [US1] [FR-004] Update `tests/unit/cli/ci/github_provider/test__resolve_conflicted_file_content_via_sdk.py` — same mock target migration
- [ ] T015 [P] [US1] [FR-004] Update `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` — update mock targets to `copilot.config.SubprocessConfig`
- [ ] T016 [P] [US1] [FR-004] Update `tests/workflows/test_copilot_generate.py` — update mock targets from `copilot.SubprocessConfig` to `copilot.config.SubprocessConfig`

## Phase 4: User Story 2 — Remove compatibility shim (P1)

### Tests (Red)

- [ ] T017 [US2] Write assertion test verifying no `try/except ImportError` shim blocks for SubprocessConfig path differences exist in codebase

### Shim Removal — Production Code

- [ ] T018 [US2] [FR-003] Remove nested `try/except` fallback shim at lines ~1496–1509 in `agentic_devtools/cli/ci/github_provider.py` — retain only outer `except Exception` graceful degradation
- [ ] T019 [US2] [FR-003] Remove nested `try/except` fallback shim at lines ~1612–1625 in `agentic_devtools/cli/ci/github_provider.py` — retain outer graceful degradation
- [ ] T020 [US2] [FR-003] Remove nested `try/except` fallback shim at lines ~2550–2562 in `agentic_devtools/cli/ci/github_provider.py` — retain outer graceful degradation
- [ ] T021 [US2] [FR-003] Remove nested `try/except` fallback shim at lines ~2677–2687 in `agentic_devtools/cli/ci/github_provider.py` — retain outer graceful degradation
- [ ] T022 [US2] [FR-003] Remove import shim in `.github/scripts/speckit-trigger/copilot_generate.py` — retain outer `except Exception` graceful degradation only

### Shim Removal — Test Code

- [ ] T023 [P] [US2] [FR-004] Remove `_build_sdk_modules_no_subprocess_config` helper and `test_run_prompt_via_sdk_fallback_import_path_succeeds` test from
  `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py`
- [ ] T024 [P] [US2] [FR-004] Remove `_build_sdk_mocks_no_subprocess_config` helper and fallback test from `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk.py`
- [ ] T025 [P] [US2] [FR-004] Remove fallback helper and fallback test from `tests/unit/cli/ci/github_provider/test__resolve_conflicted_file_content_via_sdk.py`
- [ ] T026 [P] [US2] [FR-004] Remove any fallback-path assertions from `tests/workflows/test_copilot_generate.py`

## Phase 5: User Story 3 — Keep external contracts stable (P2)

- [ ] T027 [US3] Verify no changes to CLI entry points or state key contracts — review `pyproject.toml` `[project.scripts]` section unchanged
- [ ] T028 [US3] Run full test suite (`agdt-test` + `agdt-task-wait`) confirming all existing tests pass with v1 SDK

## Phase 6: Polish & Cross-Cutting — Validation

- [ ] T029 Run `grep -r "from copilot import.*SubprocessConfig" agentic_devtools/ .github/` — verify zero results (SC-002)
- [ ] T030 Run `grep -rn "except.*primary_exc\|except.*first_exc" agentic_devtools/ .github/` — verify zero shim blocks remain (SC-003)
- [ ] T031 Run `bash scripts/targeted-checks.sh` — ruff format, ruff check, mypy, markdownlint all pass
- [ ] T032 Run full test suite with coverage (`agdt-test` + `agdt-task-wait`) — 100% relevant tests pass (SC-004)
- [ ] T033 Commit and push via `agdt-git-save-work`

## Dependencies

```text
T001 → T002 → T003
T003 → T006, T007, T008, T009, T010, T011, T012
T006–T012 → T018–T022 (shim removal after v1 imports in place)
T018–T022 → T023–T026 (test shim removal after production shim removal)
T013–T016 can run in parallel after T003
T023–T026 can run in parallel with each other
T027–T028 → T029–T032 → T033
```

## FR Traceability Matrix

| FR | Tasks |
| --- | --- |
| FR-001 | T002 |
| FR-002 | T006, T007, T008, T009, T010 |
| FR-003 | T018, T019, T020, T021, T022 |
| FR-004 | T013, T014, T015, T016, T023, T024, T025, T026 |
| FR-005 | T011, T012 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
