# Tasks: CI-Provider Abstraction & Workflow Extraction

**Feature**: Extract workflow logic from YAML to agentic-devtools library with CI-provider abstraction
**Issue**: #1400
**Spec**: `specs/1400-extract-workflow-logic-yaml/spec.md`
**Plan**: `specs/1400-extract-workflow-logic-yaml/plan.md`

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase 1: Foundation §4.1 | Project scaffolding (T001–T004) |
| Phase 2: Foundational | Phase 1: Foundation §4.1 | Exceptions, models, retry, provider ABC (T005–T014) |
| Phase 3: US1 | Phase 1: Foundation §4.1, Phase 8: Latency Benchmark & ADO Provider Stub §4.8 | CI-platform provider interface validation (T015–T016) |
| Phase 4: US2 | Phase 2: GitHub Actions Provider §4.2 | GitHub Actions provider implementation (T017–T028) |
| Phase 5: US3 | Phase 3: Guards §4.3, Phase 4: Orchestrator §4.4 | Guards, orchestrator, patch handler (T029–T043) |
| Phase 6: US4 | Phase 5: SpecKit Trigger §4.5 | SpecKit trigger extraction (T044–T047) |
| Phase 7: US5 | Phase 6: CLI Entry Points §4.6, Phase 7: YAML Minimization §4.7 | CLI entry points, templates, YAML minimization (T048–T060) |
| Phase 8: US6 | Phase 8: Latency Benchmark & ADO Provider Stub §4.8 | Azure DevOps provider stub deliverables (T061–T063) |
| Phase 9: Polish | Phase 8: Latency Benchmark & ADO Provider Stub §4.8 | Latency benchmark, cross-cutting concerns, final validation (T064–T074) |

---

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create package directory `agentic_devtools/cli/ci/` with `__init__.py`
- [ ] T002 Create test directory tree `tests/unit/cli/ci/` with `__init__.py` files for all subdirectories (`exceptions/`, `models/`, `retry/`, `provider/`, `github_provider/`, `guards/`,
  `orchestrator/`, `patch_handler/`, `speckit_trigger/`, `commands/`, `ado_provider/`)
- [ ] T003 Create test fixtures directory `tests/fixtures/ci_events/` with placeholder `README.md` documenting fixture format (data-only directory, no `__init__.py` —
  consistent with existing fixture directories like `tests/e2e_smoke/fixtures/`)
- [ ] T004 Create prompt template directory `agentic_devtools/prompts/ci/` with `__init__.py`

---

## Phase 2: Foundational — Exceptions, Models, Retry, Provider ABC

- [ ] T005 Write failing tests for `MalformedEventError` and `ProviderRateLimitError` in `tests/unit/cli/ci/exceptions/test_malformedeventerror.py` and
  `tests/unit/cli/ci/exceptions/test_providerratelimiterror.py`
- [ ] T006 Implement `agentic_devtools/cli/ci/exceptions.py` — `MalformedEventError(ValueError)` with descriptive message fields, `ProviderRateLimitError` with remaining reset time attribute
- [ ] T007 [P] Write failing tests for `EventPayload` dataclass in `tests/unit/cli/ci/models/test_eventpayload.py` — validate fields: `pr_number`, `head_branch`, `head_sha`, `base_branch`, `action`,
  `trigger_label`, `repository_full_name` (snake_case per codebase convention; JSON mapping layer handles camelCase serialization)
- [ ] T008 [P] Write failing tests for `PRMetadata`, `CheckRunStatus`, `ReviewInfo` dataclasses in `tests/unit/cli/ci/models/test_prmetadata.py`, `tests/unit/cli/ci/models/test_checkrunstatus.py`,
  `tests/unit/cli/ci/models/test_reviewinfo.py`
- [ ] T009 Implement `agentic_devtools/cli/ci/models.py` — all dataclasses (`EventPayload`, `PRMetadata`, `CheckRunStatus`, `ReviewInfo`) to make T007 and T008 pass
- [ ] T010 Write failing tests for retry utility in `tests/unit/cli/ci/retry/test_retry_with_backoff.py` — cover exponential backoff (1s initial, 60s cap), jitter, max 5 retries, `Retry-After` header
  honoring (HTTP 429/403), `ProviderRateLimitError` after exhaustion
- [ ] T011 Implement `agentic_devtools/cli/ci/retry.py` — `retry_with_backoff()` decorator/function to make T010 pass
- [ ] T012 Write failing tests for `CIPlatformProvider` ABC in `tests/unit/cli/ci/provider/test_ciplatformprovider.py` — verify all abstract methods are defined (including
  `parse_event(raw_payload: dict, event_name: str)` signature matching plan §4.1), verify a mock concrete implementation satisfies the contract structurally AND behaviorally (exercise each method with
  mock data and assert expected call signatures/return types)
- [ ] T013 Implement `agentic_devtools/cli/ci/provider.py` — `CIPlatformProvider` ABC with all abstract methods: `parse_event(raw_payload, event_name)`, `get_pr_metadata`, `list_check_runs`,
  `list_reviews`, `post_comment`, `update_comment`, `find_comment`, `approve_pr`, `merge_pr`, `request_reviewer`, `list_pr_files`, `get_check_annotations` to make T012 pass
- [ ] T014 Export Phase 2 public API from `agentic_devtools/cli/ci/__init__.py` — re-export `CIPlatformProvider`, all models, all exceptions (partial; final reconciliation in T073)

---

## Phase 3: User Story 1 — CI-Platform Provider Interface Validation [US1]

- [ ] T015 [US1] Write integration test in `tests/unit/cli/ci/provider/test_ciplatformprovider_integration.py` verifying that a stub Azure DevOps provider class compiles and satisfies the same ABC
  contract without changes to orchestration code (acceptance scenario 2)
- [ ] T016 [US1] Implement stub `_StubAdoProvider` in the test file from T015 to make the test green — validates extensibility of the ABC

---

## Phase 4: User Story 2 — GitHub Actions Provider [US2]

- [ ] T017 [US2] Create recorded webhook payload fixtures in `tests/fixtures/ci_events/`: `pull_request_opened.json`, `pull_request_synchronize.json`, `pull_request_review_submitted.json`,
  `issues_labeled.json`, `workflow_run_completed.json`
- [ ] T018 [US2] Write failing tests for `GitHubActionsProvider.parse_event(raw_payload, event_name)` in `tests/unit/cli/ci/github_provider/test_parse_event.py` — valid
  `pull_request_review` payload with matching `event_name` returns correct `pr_number`, `head_branch`, `head_sha`; malformed payload raises `MalformedEventError`;
  mismatched `event_name` (e.g., `"issues"` with a `pull_request` payload) raises `MalformedEventError`
- [ ] T019 [US2] Write failing tests for `GitHubActionsProvider.parse_event(raw_payload, event_name)` label event in `tests/unit/cli/ci/github_provider/test_parse_event_label.py` — `event_name="issues"`
  with `action="labeled"` payload returns correct `trigger_label` matching current shell validation (snake_case field; JSON mapping layer handles camelCase input)
- [ ] T020 [US2] [P] Write failing tests for `GitHubActionsProvider.get_pr_metadata()` in `tests/unit/cli/ci/github_provider/test_get_pr_metadata.py` — mock `run_safe` calls, verify return type
- [ ] T021 [US2] [P] Write failing tests for `GitHubActionsProvider.list_check_runs()` in `tests/unit/cli/ci/github_provider/test_list_check_runs.py`
- [ ] T022 [US2] [P] Write failing tests for `GitHubActionsProvider.list_reviews()` in `tests/unit/cli/ci/github_provider/test_list_reviews.py`
- [ ] T023 [US2] [P] Write failing tests for `GitHubActionsProvider.post_comment()` and `update_comment()` in `tests/unit/cli/ci/github_provider/test_post_comment.py` and
  `tests/unit/cli/ci/github_provider/test_update_comment.py`
- [ ] T024 [US2] [P] Write failing tests for `GitHubActionsProvider.find_comment()` in `tests/unit/cli/ci/github_provider/test_find_comment.py` — returns `(comment_id, comment_body)` tuple or `None`
- [ ] T025 [US2] [P] Write failing tests for `GitHubActionsProvider.approve_pr()`, `merge_pr()`, `request_reviewer()` in `tests/unit/cli/ci/github_provider/test_approve_pr.py`,
  `tests/unit/cli/ci/github_provider/test_merge_pr.py`, `tests/unit/cli/ci/github_provider/test_request_reviewer.py`
- [ ] T026 [US2] [P] Write failing tests for `GitHubActionsProvider.list_pr_files()` and `get_check_annotations()` in `tests/unit/cli/ci/github_provider/test_list_pr_files.py` and
  `tests/unit/cli/ci/github_provider/test_get_check_annotations.py`
- [ ] T027 [US2] Write failing test for retry integration in `tests/unit/cli/ci/github_provider/test_retry_integration.py` — verify provider methods use `retry_with_backoff`, honor rate limits, raise
  `ProviderRateLimitError` after 5 retries
- [ ] T028 [US2] Implement `agentic_devtools/cli/ci/github_provider.py` — full `GitHubActionsProvider` class using `run_safe` with `shell=False` for all user-controlled text, `gh` CLI for API calls,
  retry decorator from `retry.py`, pagination via `--paginate` — make T018–T027 pass

---

## Phase 5: User Story 3 — PR Loop Orchestrator Extraction [US3]

### Guards (Phase 3 in plan, prerequisite for orchestrator)

- [ ] T029 [US3] Write failing tests for `check_privileged_paths()` in `tests/unit/cli/ci/guards/test_check_privileged_paths.py` — `.github/workflows/`, `.github/actions/`, `.github/scripts/` trigger
  guard; `*.md` files excluded
- [ ] T030 [US3] Write failing tests for `check_docker_files()` in `tests/unit/cli/ci/guards/test_check_docker_files.py` — `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `.dockerignore`,
  `Dockerfile.*` trigger guard
- [ ] T031 [US3] Write failing tests for `check_deduplication()` in `tests/unit/cli/ci/guards/test_check_deduplication.py` — marker comment `<!-- repair-dispatch:<sha>:<count> -->` parsing, increment,
  max dispatch limit (default 3)
- [ ] T032 [US3] [P] Write failing tests for `check_exclusion_labels()` in `tests/unit/cli/ci/guards/test_check_exclusion_labels.py` — `ai-pr-loop-ignore` skips entirely, `do-not-auto-merge` sets flag
- [ ] T033 [US3] [P] Write failing tests for `check_fork_pr()` in `tests/unit/cli/ci/guards/test_check_fork_pr.py` — head repo differs from base repo
- [ ] T034 [US3] [P] Write failing tests for `check_cycle_limit()` in `tests/unit/cli/ci/guards/test_check_cycle_limit.py` — `<!-- ai-pr-loop-cycle-tracker -->` comment, default 50 max
- [ ] T035 [US3] Implement `agentic_devtools/cli/ci/guards.py` — all guard functions to make T029–T034 pass

### Orchestrator

- [ ] T036 [US3] Write failing tests for `run_ai_pr_loop()` state machine in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop.py` — mock provider, verify: metadata resolution → guards → review
  evaluation → dispatch decision → merge gate → approval → merge sequence
- [ ] T037 [US3] Write failing test for orchestrator with PR in "ready for review" state in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_ready.py` — verify same API call sequence as current
  YAML (acceptance scenario 1)
- [ ] T038 [US3] Write failing test for orchestrator with failing CI checks in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_blocked.py` — verify merge blocked + correct status comment posted
  (acceptance scenario 2)
- [ ] T039 [US3] Write failing test for malformed event handling in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_malformed.py` — `MalformedEventError` caught, structured JSON error to stderr,
  non-zero exit code
- [ ] T040 [US3] Write failing test for PR with no linked issue in `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop_no_issue.py` — warning logged, processing continues, advisory in status comment
- [ ] T041 [US3] Implement `agentic_devtools/cli/ci/orchestrator.py` — `run_ai_pr_loop(provider, event_payload) -> int` state machine to make T036–T040 pass

### Patch Handler

- [ ] T042 [US3] Write failing tests for lint patch handling in `tests/unit/cli/ci/patch_handler/test_apply_lint_patch.py` — download, validation, apply logic
- [ ] T043 [US3] Implement `agentic_devtools/cli/ci/patch_handler.py` — lint patch download, validation, and apply logic to make T042 pass

---

## Phase 6: User Story 4 — SpecKit Trigger Extraction [US4]

- [ ] T044 [US4] Write failing tests for `process_speckit_label_event()` in `tests/unit/cli/ci/speckit_trigger/test_process_speckit_label_event.py` — valid label triggers correct speckit phase
  (acceptance scenario 1)
- [ ] T045 [US4] Write failing test for duplicate trigger deduplication in `tests/unit/cli/ci/speckit_trigger/test_process_speckit_label_event_dedup.py` — duplicate event skipped with logged reason
  (acceptance scenario 2)
- [ ] T046 [US4] Write failing tests for label validation and phase transition edge cases in `tests/unit/cli/ci/speckit_trigger/test_label_validation.py`
- [ ] T047 [US4] Implement `agentic_devtools/cli/ci/speckit_trigger.py` — `process_speckit_label_event(provider, event_payload) -> int` with label validation, idempotency, phase transitions to make
  T044–T046 pass

---

## Phase 7: User Story 5 — CLI Entry Points, Templates & YAML Minimization [US5]

### CLI Entry Points & Comment Templates

- [ ] T048 [US5] Create comment template files: `agentic_devtools/prompts/ci/timeout-comment.md`, `exhausted-comment.md`, `merge-failed-comment.md`, `ready-no-merge-comment.md` using `{{variable}}`
  syntax
- [ ] T049 [US5] Write failing tests for `load_ci_template()` in `tests/unit/prompts/loader/test_load_ci_template.py` — loads raw template from `prompts/ci/` directory without substitution
- [ ] T050 [US5] Implement `load_ci_template()` in `agentic_devtools/prompts/loader.py` — resolves templates from `prompts/ci/` subdirectory, returns raw string, callers invoke
  `substitute_variables()` separately (FR-007)
- [ ] T051 [US5] Write failing tests for `ai_pr_loop_command()` CLI entry point in `tests/unit/cli/ci/commands/test_ai_pr_loop_command.py` — reads `GITHUB_EVENT_PATH` and `GITHUB_EVENT_NAME`,
  constructs provider, invokes orchestrator
- [ ] T052 [US5] Write failing tests for `speckit_trigger_command()` CLI entry point in `tests/unit/cli/ci/commands/test_speckit_trigger_command.py`
- [ ] T053 [US5] Write failing test for missing `gh` CLI dependency in `tests/unit/cli/ci/commands/test_ai_pr_loop_command_missing_dep.py` — when `gh` is not found on PATH,
  `ai_pr_loop_command()` fails with a clear error message within 5s (internal dependency check; see T074 for the spec US5 acceptance scenario 2 — missing `agdt-ai-pr-loop` binary)
- [ ] T054 [US5] Implement `agentic_devtools/cli/ci/commands.py` — `ai_pr_loop_command()` and `speckit_trigger_command()` CLI entry points to make T051–T053 pass
- [ ] T055 [US5] Add CLI entry points to `pyproject.toml` under `[project.scripts]`: `agdt-ai-pr-loop` and `agdt-speckit-trigger` following existing `agdt-*` naming convention (NFR-004)
- [ ] T056 [US5] Reinstall package (`pip install -e .`) and verify entry points are callable

### YAML Minimization & Feature Flag

- [ ] T057 [US5] Write failing test for feature flag routing in `tests/unit/cli/ci/commands/test_feature_flag.py` — `AGDT_USE_PYTHON_ORCHESTRATOR=1` selects Python path; unset/0 selects legacy JS path
- [ ] T058 [US5] Implement feature flag logic in `agentic_devtools/cli/ci/commands.py` — `AGDT_USE_PYTHON_ORCHESTRATOR` env var selects execution path, synchronous execution (not background task)
- [ ] T059 [US5] Create minimized `ai-pr-loop.yml` (≤50 lines) — triggers, permissions, env vars, single `agdt-ai-pr-loop` call with feature flag gate (SC-002, FR-008)
- [ ] T060 [US5] Create minimized speckit trigger workflow YAML (≤30 lines each) — triggers, permissions, single `agdt-speckit-trigger` call (FR-008)

---

## Phase 8: User Story 6 — Azure DevOps Provider Stub [US6]

- [ ] T061 [US6] Write failing tests for `AzureDevOpsProvider` stub in `tests/unit/cli/ci/ado_provider/test_azuredevopsprovider.py` — verify it satisfies `CIPlatformProvider` ABC, `parse_event()`
  returns `EventPayload` with correct fields (acceptance scenario 1)
- [ ] T062 [US6] Implement `agentic_devtools/cli/ci/ado_provider.py` — stub `AzureDevOpsProvider` with `NotImplementedError` on action methods, basic `parse_event()` for ADO service hook JSON format
  to make T061 pass
- [ ] T063 [US6] Write integration test verifying the same orchestrator tests run against the ADO provider stub without orchestration code changes (SC-003)

---

## Phase 9: Polish & Cross-Cutting

### Latency Benchmark

- [ ] T064 Create `scripts/measure-orchestrator-latency.py` — benchmark script measuring orchestrator entry-point latency using `time.perf_counter()`, averages over 10 runs with fixture payloads,
  reports delta vs baseline (NFR-002)

### End-to-End & Integration

- [ ] T065 Write end-to-end smoke tests comparing old YAML path vs new Python path outputs using golden-file fixtures under `tests/fixtures/ci_events/` covering `pull_request`, `pull_request_review`,
  `issues` with `action="labeled"`, `workflow_run` event types (SC-004)
- [ ] T066 Write integration test verifying all comment templates render correctly via `substitute_variables()` with representative variable dicts (FR-007)
- [ ] T067 Verify minimized `ai-pr-loop.yml` line count ≤50 and speckit YAMLs ≤30 lines each (FR-008, SC-002)

### Coverage & Validation

- [ ] T068 Run full test suite (`agdt-test` + `agdt-task-wait`) and verify 100% coverage for all modules under `agentic_devtools/cli/ci/` (NFR-001)
- [ ] T069 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test layout compliance for all new test files
- [ ] T070 Run `bash scripts/run-pr-checks.sh` — all checks must pass before push

### Documentation

- [ ] T071 Update `.github/copilot-instructions.md` — add CI module section documenting `agdt-ai-pr-loop`, `agdt-speckit-trigger` commands, provider abstraction, and feature flag
- [ ] T072 Update `pyproject.toml` package metadata if needed — ensure `cli.ci` subpackage is included in package discovery
- [ ] T073 Reconcile `agentic_devtools/cli/ci/__init__.py` exports — verify all public symbols from Phases 2–8 are re-exported and importable from the package root
  (final reconciliation of T014's partial export; see F-05)

### Missing Binary E2E

- [ ] T074 [US5] Write integration test validating that when `agdt-ai-pr-loop` is not installed (binary missing from PATH), the minimized YAML workflow fails with a non-zero exit code and a clear
  "command not found" error message within 5s (spec US5 acceptance scenario 2; complements T053 which covers the internal `gh` dependency failure mode)

---

## Dependency Graph

```text
T001–T004 (setup, sequential)
    │
    ▼
T005–T006 (exceptions)
    │
    ├──► T007–T009 (models, parallelizable after exceptions)
    ├──► T010–T011 (retry, parallelizable after exceptions)
    │
    ▼
T012–T014 (provider ABC, depends on models + exceptions)
    │
    ├──► T015–T016 [US1] (ABC validation, after provider)
    │
    ├──► T017–T028 [US2] (GitHub provider, after provider ABC + retry)
    │    │
    │    ├──► T029–T035 [US3] (guards, parallel with provider impl)
    │    │    │
    │    │    ▼
    │    └──► T036–T041 [US3] (orchestrator, after provider + guards)
    │              │
    │              ├──► T042–T043 [US3] (patch handler, after orchestrator)
    │              │
    │    T044–T047 [US4] (speckit trigger, parallel with orchestrator)
    │              │
    │              ▼
    │         T048–T060 [US5] (CLI + templates + YAML, after orchestrator + speckit)
    │              │
    │              ▼
    │         T061–T063 [US6] (ADO stub, after provider ABC)
    │
    ▼
T064–T073 (polish, after all implementation phases)
T074 (missing binary E2E, after T055 + T059)
```

---

## Requirements Traceability

| Requirement | Tasks |
|---|---|
| FR-001 (CIPlatformProvider ABC) | T012, T013, T014 |
| FR-002 (GitHub Actions provider) | T017–T028 |
| FR-003 (Orchestrator extraction) | T036–T041 |
| FR-004 (Safety guards preserved) | T029–T035 |
| FR-005 (CLI entry point) | T051, T052, T053, T054, T055, T074 |
| FR-006 (SpecKit trigger extraction) | T044–T047 |
| FR-007 (substitute_variables for templates) | T048–T050, T066 |
| FR-008 (YAML minimization) | T059, T060, T067 |
| FR-009 (Lint patch handling) | T042, T043 |
| NFR-001 (100% coverage) | T068 |
| NFR-002 (≤500ms latency delta) | T064 |
| NFR-003 (Retry/backoff) | T010, T011, T027 |
| NFR-004 (agdt-* naming) | T055 |
| SC-001 (All inline JS covered by tests) | T036–T040, T065 |
| SC-002 (≤50 lines YAML) | T059, T067 |
| SC-003 (New provider without orchestrator changes) | T063 |
| SC-004 (Golden-file E2E verification) | T017, T065 |
| Edge: Malformed event | T005, T006, T018, T039 |
| Edge: Rate limits | T010, T011, T027 |
| Edge: No linked issue | T040 |
| Migration: Feature flag | T057, T058 |
| Migration: Parallel operation | T059 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
