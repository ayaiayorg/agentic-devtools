# Tasks: SpecKit Pipeline Retry & Reconciliation Logic

**Issue**: [#1938](https://github.com/ayaiayorg/agentic-devtools/issues/1938)

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
| --- | --- | --- |
| Phase 1: Setup | — | Package scaffolding to prepare implementation files and test structure |
| Phase 2: Foundational | Phase 1: Data Models & Configuration | Core data/config/exception prerequisites |
| Phase 3: User Story 1 — Primary Retry Workflow | Phase 2: Provider Interface Extension; Phase 3: GitHub Actions Provider Implementation; Phase 5: Reconciliation Engine | User story delivery spanning provider and engine work |
| Phase 4: User Story 2 — Context-Aware Status Reporting | Phase 4: Event Context Mapping; Phase 5: Reconciliation Engine | Context mapping plus engine integration for status reporting |
| Phase 5: User Story 3 — Provider-Abstraction Fallback | Phase 2: Provider Interface Extension; Phase 5: Reconciliation Engine | ADO fallback behavior and provider abstraction verification |
| Phase 6: CLI Command & Entry Point | Phase 6: CLI Command & Integration | CLI command and entry-point integration |
| Phase 7: Polish & Cross-Cutting | Phase 6: CLI Command & Integration | Final verification and package exposure updates |

---

## Phase 1: Setup — Package Scaffolding

- [ ] T001 Create package init file `agentic_devtools/cli/ci/reconciliation/__init__.py` with public API exports
- [ ] T002 Create `tests/unit/cli/ci/reconciliation/__init__.py` and all necessary nested `__init__.py` files for test structure (FR-001)

---

## Phase 2: Foundational — Data Models, Configuration & Exceptions

- [ ] T003 [P] Write tests for configuration constants and env var overrides in `tests/unit/cli/ci/reconciliation/config/test_max_run_attempts.py` and
  `tests/unit/cli/ci/reconciliation/config/test_reconciliation_window_hours.py` (FR-001)
- [ ] T004 [P] Implement `agentic_devtools/cli/ci/reconciliation/config.py` with `MAX_RUN_ATTEMPTS` (default 3, env `AGDT_MAX_RUN_ATTEMPTS`) and `RECONCILIATION_WINDOW_HOURS` (default 24, env
  `AGDT_RECONCILIATION_WINDOW_HOURS`) (FR-001)
- [ ] T005 [P] Write tests for `WorkflowRun` dataclass in `tests/unit/cli/ci/reconciliation/models/test_workflowrun.py` (FR-001)
- [ ] T006 [P] Write tests for `ReconciliationResult` dataclass in `tests/unit/cli/ci/reconciliation/models/test_reconciliationresult.py` (FR-001)
- [ ] T007 [P] Write tests for `RunEventContext` dataclass in `tests/unit/cli/ci/reconciliation/models/test_runeventcontext.py` (FR-001)
- [ ] T008 Implement `agentic_devtools/cli/ci/reconciliation/models.py` with `WorkflowRun`, `ReconciliationResult`, and `RunEventContext` dataclasses (FR-001)
- [ ] T009 [P] Write tests for `UnmappableContextError` in `tests/unit/cli/ci/reconciliation/exceptions/test_unmappablecontexterror.py` (FR-001)
- [ ] T010 Implement `agentic_devtools/cli/ci/reconciliation/exceptions.py` with `UnmappableContextError` exception class (FR-001)

---

## Phase 3: User Story 1 — Primary Retry Workflow (P1)

### Provider Interface Extension (FR-002)

- [ ] T011 [US1] Write happy-path tests for `CIPlatformProvider.list_workflow_runs()` default behavior raising `NotImplementedError` in `tests/unit/cli/ci/provider/test_list_workflow_runs.py` (FR-002)
- [ ] T012 [US1] Write tests for `CIPlatformProvider.rerun_workflow()` default raising `NotImplementedError` in `tests/unit/cli/ci/provider/test_rerun_workflow.py` (FR-002)
- [ ] T013 [US1] Add non-abstract `list_workflow_runs(workflow_id: str, ...)` method to `CIPlatformProvider` in `agentic_devtools/cli/ci/provider.py` with default `NotImplementedError` (FR-002,
  NFR-002)
- [ ] T014 [US1] Add non-abstract `rerun_workflow(run_id: int)` method to `CIPlatformProvider` in `agentic_devtools/cli/ci/provider.py` with default `NotImplementedError` (FR-002, NFR-002)

### GitHub Actions Provider Implementation (FR-003)

- [ ] T015 [US1] Write tests for `GitHubActionsProvider.list_workflow_runs()` in `tests/unit/cli/ci/github_provider/test_list_workflow_runs.py` covering conclusion filtering, window filtering, and
  attempt cap (FR-003)
- [ ] T016 [US1] Write tests for `GitHubActionsProvider.rerun_workflow()` in `tests/unit/cli/ci/github_provider/test_rerun_workflow.py` covering success, transient failure retry, and auth error
  (FR-003)
- [ ] T017 [US1] Implement `GitHubActionsProvider.list_workflow_runs()` in `agentic_devtools/cli/ci/github_provider.py` — calls `gh api` for workflow runs, filters by conclusion/window/attempts,
  wrapped with `@retry_with_backoff` (FR-003)
- [ ] T018 [US1] Implement `GitHubActionsProvider.rerun_workflow()` in `agentic_devtools/cli/ci/github_provider.py` — calls `gh api` to trigger re-run all jobs, wrapped with `@retry_with_backoff`
  (FR-003)

### Reconciliation Engine (FR-001, FR-005)

- [ ] T019 [US1] Write tests for `reconcile()` in `tests/unit/cli/ci/reconciliation/engine/test_reconcile.py` — scenarios: oldest run retried, no eligible runs, non-retriable conclusions ignored,
  single run per invocation (FR-001, FR-005)
- [ ] T020 [US1] Write tests for escalation path in `tests/unit/cli/ci/reconciliation/engine/test_reconcile.py` — scenario: run at MAX_RUN_ATTEMPTS posts escalation via existing devtools helpers
  (FR-006)
- [ ] T021 [US1] Implement `reconcile()` function in `agentic_devtools/cli/ci/reconciliation/engine.py` — selects oldest eligible run, calls `provider.rerun_workflow()` or posts escalation, returns
  `ReconciliationResult` (FR-001, FR-005)
- [ ] T022 [US1] Write tests for edge case: API error during rerun surfaces without falsely recording success in `tests/unit/cli/ci/reconciliation/engine/test_reconcile.py` (FR-001, FR-005)

---

## Phase 4: User Story 2 — Context-Aware Status Reporting (P1)

### Event Context Mapping

- [ ] T023 [US2] Write happy-path tests for `map_run_context()` with `issue_comment` event in `tests/unit/cli/ci/reconciliation/context_mapper/test_map_run_context.py` (FR-006)
- [ ] T024 [US2] Write tests for `map_run_context()` with `pull_request` event in `tests/unit/cli/ci/reconciliation/context_mapper/test_map_run_context.py` (FR-006)
- [ ] T025 [US2] Write tests for `map_run_context()` with `push` (branch) event in `tests/unit/cli/ci/reconciliation/context_mapper/test_map_run_context.py` (FR-006)
- [ ] T026 [US2] Write tests for `map_run_context()` raising `UnmappableContextError` when context cannot be resolved in `tests/unit/cli/ci/reconciliation/context_mapper/test_map_run_context.py`
  (FR-006)
- [ ] T027 [US2] Implement `map_run_context()` in `agentic_devtools/cli/ci/reconciliation/context_mapper.py` — parses `event` field (`workflow_dispatch`, `issue_comment`, `pull_request`, `push`) to
  resolve target
- [ ] T028 [US2] Write tests for escalation posting to correct target (issue/PR/branch) in `tests/unit/cli/ci/reconciliation/engine/test_reconcile.py` — verifies signal uses existing devtools helpers
  and correct target (FR-006)
- [ ] T029 [US2] Integrate context mapper into `reconcile()` in `agentic_devtools/cli/ci/reconciliation/engine.py` — use mapped context for status feedback posting via existing devtools helpers
  (FR-006)

---

## Phase 5: User Story 3 — Provider-Abstraction Fallback (P2)

- [ ] T030 [US3] Write tests for `AzureDevOpsProvider.list_workflow_runs()` raising `NotImplementedError` in `tests/unit/cli/ci/ado_provider/test_list_workflow_runs.py` (FR-004)
- [ ] T031 [US3] Write tests for `AzureDevOpsProvider.rerun_workflow()` raising `NotImplementedError` in `tests/unit/cli/ci/ado_provider/test_rerun_workflow.py` (FR-004)
- [ ] T032 [US3] Verify `AzureDevOpsProvider` inherits default `NotImplementedError` from `CIPlatformProvider` — no code changes needed in `agentic_devtools/cli/ci/ado_provider.py`, only test
  confirmation (FR-004)
- [ ] T033 [US3] Write integration-style test verifying `reconcile()` raises `NotImplementedError` when invoked with `AzureDevOpsProvider` in
  `tests/unit/cli/ci/reconciliation/engine/test_reconcile.py` (FR-004)

---

## Phase 6: CLI Command & Entry Point (FR-005)

- [ ] T034 [US1] Write tests for `reconcile_command()` CLI entry point in `tests/unit/cli/ci/reconciliation/command/test_reconcile_command.py` — args parsing, provider instantiation, output formatting
  (FR-005)
- [ ] T035 [US1] Implement `agentic_devtools/cli/ci/reconciliation/command.py` — CLI entry point `agdt-ci-reconcile` that instantiates provider and calls `reconcile()` (FR-005)
- [ ] T036 [US1] Add `agdt-ci-reconcile` entry point to `pyproject.toml` under `[project.scripts]`
- [ ] T037 [US1] Reinstall package with `pip install -e .` and verify `agdt-ci-reconcile --help` works (FR-005)

---

## Phase 7: Polish & Cross-Cutting

- [ ] T038 Update `agentic_devtools/cli/ci/reconciliation/__init__.py` exports to expose public API (`reconcile`, `WorkflowRun`, `ReconciliationResult`, `RunEventContext`, config constants)
- [ ] T039 Run `agdt-test` full suite to verify no regressions and 100% branch coverage on new files (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006)
- [ ] T040 Run `bash scripts/targeted-checks.sh` to validate ruff format, ruff check, mypy, and test structure (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006)
- [ ] T041 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006)
- [ ] T042 Update `agentic_devtools/cli/ci/__init__.py` if needed to expose reconciliation subpackage

---

## Dependency Graph

```text
T001, T002 → T003–T010 (parallel within phase)
T008, T010 → T011–T014 (provider interface needs models)
T013, T014 → T015–T018 (GitHub impl needs interface methods)
T017, T018 → T019–T022 (engine needs provider impl for integration)
T008, T010 → T023–T029 (context mapper needs models/exceptions)
T027 → T029 (engine integration needs mapper)
T013, T014 → T030–T033 (ADO tests need interface methods)
T021 → T034–T037 (CLI needs engine)
T037 → T038–T042 (polish after all impl)
```

## FR Coverage Matrix

| FR | Tasks |
| --- | --- |
| FR-001 | T004, T008, T010, T019–T022 |
| FR-002 | T011–T014 |
| FR-003 | T015–T018 |
| FR-004 | T030–T033 |
| FR-005 | T019–T022, T034–T037 |
| FR-006 | T020, T023–T029 |
| NFR-001 | Covered by engine timeout behavior in T021 |
| NFR-002 | T013, T014 (non-abstract defaults) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
