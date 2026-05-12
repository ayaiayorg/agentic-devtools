# Tasks: CI-Provider Abstraction & Workflow Extraction

## Phase Mapping: Plan → Tasks

| Plan Phase | Plan Section | Task Phase(s) | Tasks |
|------------|-------------|---------------|-------|
| Phase 1: Foundation (Provider Interface + Models) | §4.1 | Phase 1 (Setup), Phase 2 (Foundational), Phase 3 (US1) | T001–T016 |
| Phase 2: GitHub Actions Provider | §4.2 | Phase 4 (US2) | T017–T027 |
| Phase 3: Guards Module | §4.3 | Phase 5 (US3, guards portion) | T028–T034 |
| Phase 4: Orchestrator Extraction | §4.4 | Phase 5 (US3, orchestrator portion) | T035–T042 |
| Phase 5: SpecKit Trigger Extraction | §4.5 | Phase 6 (US4) | T043–T046 |
| Phase 6: CLI Entry Points & Comment Templates | §4.6 | Phase 7 (US5) | T047–T059 |
| Phase 7: YAML Minimization & Feature Flag | §4.7 | Phase 7 (US5, YAML tasks) | T055–T059 |
| Phase 8: Latency Benchmark & ADO Provider Stub | §4.8 | Phase 8 (US6), Final Phase | T060–T070 |

## Phase 1: Setup — Package Scaffolding

- [ ] T001 Create package directory and init file `agentic_devtools/cli/ci/__init__.py` (FR-001)
- [ ] T002 Create test directory structure `tests/unit/cli/ci/__init__.py` with all required `__init__.py` files (FR-001)
- [ ] T003 Create test fixtures directory `tests/fixtures/ci_events/` with sample GitHub webhook payloads (`pull_request.json`, `pull_request_review.json`, `issues_labeled.json`) (FR-002, SC-004)
- [ ] T004 Create prompt templates directory `agentic_devtools/prompts/ci/` with `__init__.py` (FR-007)

## Phase 2: Foundational — Exceptions, Models, Retry, Provider ABC

- [ ] T005 Write tests for custom exceptions `tests/unit/cli/ci/exceptions/test_malformedeventerror.py` and `tests/unit/cli/ci/exceptions/test_providerratelimiterror.py` (FR-001, FR-002)
- [ ] T006 Implement `agentic_devtools/cli/ci/exceptions.py` — `MalformedEventError(ValueError)` and `ProviderRateLimitError` with reset-time attribute (FR-001, FR-002)
- [ ] T007 [P] Write tests for `EventPayload` dataclass `tests/unit/cli/ci/models/test_eventpayload.py` — fields: `pr_number`, `head_branch`, `head_sha`, `base_branch`, `action`, `trigger_label`,
  `repository_full_name` (snake_case per codebase convention; JSON mapping layer handles camelCase serialization) (FR-002)
- [ ] T008 [P] Write tests for `PRMetadata`, `CheckRunStatus`, `ReviewInfo` dataclasses `tests/unit/cli/ci/models/test_prmetadata.py`, `tests/unit/cli/ci/models/test_checkrunstatus.py`,
  `tests/unit/cli/ci/models/test_reviewinfo.py` (FR-001, FR-002)
- [ ] T009 Implement `agentic_devtools/cli/ci/models.py` — all dataclasses (`EventPayload`, `PRMetadata`, `CheckRunStatus`, `ReviewInfo`) (FR-001, FR-002)
- [ ] T010 Write tests for retry utility `tests/unit/cli/ci/retry/test_retry_with_backoff.py` (NFR-003) — exponential backoff, jitter, `Retry-After` header honoring, max 5 retries,
  `ProviderRateLimitError` after exhaustion
- [ ] T011 Implement `agentic_devtools/cli/ci/retry.py` — `retry_with_backoff()` decorator/utility (1s initial, 60s cap, 5 max retries, jitter, honors `Retry-After`) (NFR-003)
- [ ] T012 Write tests for `CIPlatformProvider` ABC `tests/unit/cli/ci/provider/test_ciplatformprovider.py` — verify abstract methods, mock concrete implementation satisfies contract (FR-001)
- [ ] T013 Implement `agentic_devtools/cli/ci/provider.py` — `CIPlatformProvider` ABC with all abstract methods: `parse_event`, `get_pr_metadata`, `list_check_runs`, `list_reviews`, `post_comment`,
  `update_comment`, `find_comment`, `approve_pr`, `merge_pr`, `request_reviewer`, `list_pr_files`, `get_check_annotations` (FR-001)

## Phase 3: User Story 1 — CI-Platform Provider Interface [P1]

- [ ] T014 [US1] Write mock provider test `tests/unit/cli/ci/provider/test_mock_provider_contract.py` — verify a mock implementation exercises all ABC method contracts independently (FR-001)
- [ ] T015 [US1] Write ADO stub contract test `tests/unit/cli/ci/provider/test_ado_stub_contract.py` — verify a stubbed ADO provider satisfies the same ABC without orchestration changes (FR-001,
  acceptance scenario 2)
- [ ] T016 [US1] Create reusable `MockCIPlatformProvider` test fixture in `tests/unit/cli/ci/conftest.py` for use across all subsequent test phases (FR-001)

## Phase 4: User Story 2 — GitHub Actions Provider [P1]

- [ ] T017 [US2] Write tests for event parsing `tests/unit/cli/ci/github_provider/test_parse_event.py` — `pull_request`, `pull_request_review`, `issues.labeled` payloads; malformed payload raises
  `MalformedEventError` (FR-002)
- [ ] T018 [US2] [P] Write tests for PR metadata resolution `tests/unit/cli/ci/github_provider/test_get_pr_metadata.py` — verifies same `prNumber`, `headBranch`, `headSha` as inline JS (FR-002,
  acceptance scenario 1)
- [ ] T019 [US2] [P] Write tests for label parsing `tests/unit/cli/ci/github_provider/test_parse_label_event.py` — matches current shell validation output (FR-002, acceptance scenario 2)
- [ ] T020 [US2] [P] Write tests for check runs listing `tests/unit/cli/ci/github_provider/test_list_check_runs.py` (FR-002)
- [ ] T021 [US2] [P] Write tests for reviews listing `tests/unit/cli/ci/github_provider/test_list_reviews.py` (FR-002)
- [ ] T022 [US2] [P] Write tests for comment operations `tests/unit/cli/ci/github_provider/test_post_comment.py`, `tests/unit/cli/ci/github_provider/test_update_comment.py`,
  `tests/unit/cli/ci/github_provider/test_find_comment.py` (FR-002)
- [ ] T023 [US2] [P] Write tests for PR actions `tests/unit/cli/ci/github_provider/test_approve_pr.py`, `tests/unit/cli/ci/github_provider/test_merge_pr.py`,
  `tests/unit/cli/ci/github_provider/test_request_reviewer.py` (FR-002)
- [ ] T024 [US2] [P] Write tests for file listing `tests/unit/cli/ci/github_provider/test_list_pr_files.py` (FR-002)
- [ ] T025 [US2] Implement `agentic_devtools/cli/ci/github_provider.py` — `GitHubActionsProvider(CIPlatformProvider)` with full method implementations using `run_safe` with `shell=False` for
  user-controlled text (FR-002)
- [ ] T026 [US2] Write integration test `tests/unit/cli/ci/github_provider/test_behavioral_equivalence.py` — golden-file comparison against recorded fixtures in `tests/fixtures/ci_events/` (SC-004)
- [ ] T027 [US2] Add retry integration to provider — wrap API calls with `retry_with_backoff`, handle HTTP 429/403 rate limits (NFR-003)

## Phase 5: User Story 3 — PR Loop Orchestrator Extraction [P1]

- [ ] T028 [US3] Write tests for guards module `tests/unit/cli/ci/guards/test_check_privileged_paths.py` — `.github/workflows/`, `.github/actions/`, `.github/scripts/` excluding `*.md` (FR-004
  privileged-path guard)
- [ ] T029 [US3] [P] Write tests for docker guard `tests/unit/cli/ci/guards/test_check_docker_files.py` — `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `.dockerignore`, `Dockerfile.*`
  (FR-004 docker-file guard)
- [ ] T030 [US3] [P] Write tests for deduplication guard `tests/unit/cli/ci/guards/test_check_deduplication.py` — marker comment parsing, dispatch count tracking, max dispatches (FR-004 deduplication
  guard)
- [ ] T031 [US3] [P] Write tests for exclusion labels `tests/unit/cli/ci/guards/test_check_exclusion_labels.py` — `ai-pr-loop-ignore`, `do-not-auto-merge` (FR-004)
- [ ] T032 [US3] [P] Write tests for fork PR guard `tests/unit/cli/ci/guards/test_check_fork_pr.py` (FR-004)
- [ ] T033 [US3] [P] Write tests for cycle limit guard `tests/unit/cli/ci/guards/test_check_cycle_limit.py` (FR-004)
- [ ] T034 [US3] Implement `agentic_devtools/cli/ci/guards.py` — all guard functions: `check_privileged_paths`, `check_docker_files`, `check_deduplication`, `check_exclusion_labels`, `check_fork_pr`,
  `check_cycle_limit` (FR-004)
- [ ] T035 [US3] Write tests for orchestrator state machine `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop.py` — metadata resolution → guards → review evaluation → merge gate → approval → merge
  (FR-003)
- [ ] T036 [US3] [P] Write tests for merge condition evaluation `tests/unit/cli/ci/orchestrator/test_evaluate_merge_readiness.py` — all checks pass + branch up-to-date (FR-004 merge condition)
- [ ] T037 [US3] [P] Write tests for review condition evaluation `tests/unit/cli/ci/orchestrator/test_evaluate_review_condition.py` — required approvals met, no changes-requested outstanding (FR-004
  review condition)
- [ ] T038 [US3] [P] Write tests for PR with no linked issue `tests/unit/cli/ci/orchestrator/test_no_linked_issue.py` — logs warning, surfaces advisory in status comment, does NOT block (FR-003)
- [ ] T039 [US3] Implement `agentic_devtools/cli/ci/orchestrator.py` — `run_ai_pr_loop(provider, event_payload) -> int` state machine (FR-003)
- [ ] T040 [US3] [P] Write tests for patch handler `tests/unit/cli/ci/patch_handler/test_apply_lint_patch.py` (FR-003)
- [ ] T041 [US3] Implement `agentic_devtools/cli/ci/patch_handler.py` — lint patch download, validation, and apply logic (FR-003)
- [ ] T042 [US3] Write orchestrator golden-file integration test `tests/unit/cli/ci/orchestrator/test_golden_file_equivalence.py` — mocked provider, compare API call sequences against expected outputs
  (FR-003, SC-001)

## Phase 6: User Story 4 — SpecKit Trigger Extraction [P2]

- [ ] T043 [US4] Write tests for speckit label validation `tests/unit/cli/ci/speckit_trigger/test_validate_speckit_label.py` — valid label triggers correct phase (FR-006, acceptance scenario 1)
- [ ] T044 [US4] [P] Write tests for deduplication `tests/unit/cli/ci/speckit_trigger/test_deduplication_guard.py` — duplicate trigger skips and logs reason (FR-006, acceptance scenario 2)
- [ ] T045 [US4] [P] Write tests for phase transitions `tests/unit/cli/ci/speckit_trigger/test_phase_transition.py` — all valid phase progressions (FR-006)
- [ ] T046 [US4] Implement `agentic_devtools/cli/ci/speckit_trigger.py` — `process_speckit_label_event(provider, event_payload) -> int` with label validation, idempotency, phase transition (FR-006)

## Phase 7: User Story 5 — YAML Minimization & CLI Entry Points [P2]

- [ ] T047 [US5] Write tests for CLI entry point `tests/unit/cli/ci/commands/test_ai_pr_loop_command.py` — reads `GITHUB_EVENT_PATH`, invokes orchestrator, returns exit code (FR-005)
- [ ] T048 [US5] [P] Write tests for speckit CLI entry point `tests/unit/cli/ci/commands/test_speckit_trigger_command.py` (FR-005)
- [ ] T049 [US5] [P] Write tests for `load_ci_template` helper `tests/unit/prompts/loader/test_load_ci_template.py` — resolves templates from `prompts/ci/` directory (FR-007)
- [ ] T050 [US5] Implement `load_ci_template()` in `agentic_devtools/prompts/loader.py` — loads templates from `prompts/ci/` subdirectory without performing substitution (FR-007)
- [ ] T051 [US5] Create comment templates using `{{variable}}` syntax rendered by `substitute_variables()`: `agentic_devtools/prompts/ci/timeout-comment.md`, `exhausted-comment.md`,
  `merge-failed-comment.md`, `ready-no-merge-comment.md` (FR-007)
- [ ] T052 [US5] Implement `agentic_devtools/cli/ci/commands.py` — `ai_pr_loop_command()` and `speckit_trigger_command()` CLI entry points running synchronously (FR-005)
  > **Note:** These CI-invoked commands run synchronously (not as background tasks) because they are executed by
  > GitHub Actions runners that need the exit code for step status.
  > This is an intentional exception to NFR-004's background-task convention.
- [ ] T053 [US5] Add entry points to `pyproject.toml`: `agdt-ai-pr-loop` and `agdt-speckit-trigger` (FR-005)
- [ ] T054 [US5] Write test for feature flag routing `tests/unit/cli/ci/commands/test_feature_flag.py` — `AGDT_USE_PYTHON_ORCHESTRATOR=1` selects Python path (FR-005)
- [ ] T055 [US5] Minimize `ai-pr-loop.yml` to ≤50 lines: triggers, permissions, env vars, feature flag check, single `agdt-ai-pr-loop` call (FR-008, SC-002, acceptance scenario 1)
- [ ] T056 [US5] Minimize speckit trigger YAML workflows to ≤30 lines each (FR-008)
- [ ] T057 [US5] Write regression test `tests/unit/cli/ci/commands/test_yaml_minimization_guards.py` — assert minimized YAML still enforces the same guards and semantics as original workflows
  (FR-008, acceptance scenario: golden-file comparison of guard behavior pre/post minimization)
- [ ] T058 [US5] Write test for missing CLI binary `tests/unit/cli/ci/commands/test_missing_binary.py` — workflow fails with clear error within 5s (FR-005, acceptance scenario 2)
- [ ] T059 [US5] Write end-to-end smoke test `tests/unit/cli/ci/commands/test_e2e_smoke.py` — feature flag on/off produces identical behavior (SC-004)

## Phase 8: User Story 6 — Azure DevOps Provider [P3]

- [ ] T060 [US6] Write tests for ADO event parsing `tests/unit/cli/ci/ado_provider/test_parse_event.py` — ADO service hook JSON normalized to same `EventPayload` fields (FR-001,
  acceptance scenario 1)
- [ ] T061 [US6] [P] Write tests for ADO PR metadata `tests/unit/cli/ci/ado_provider/test_get_pr_metadata.py` (FR-001)
- [ ] T062 [US6] Implement `agentic_devtools/cli/ci/ado_provider.py` — `AzureDevOpsProvider(CIPlatformProvider)` stub using ADO REST API mocks (SC-003)
- [ ] T063 [US6] Write integration test `tests/unit/cli/ci/ado_provider/test_orchestrator_integration.py` — same orchestrator tests run against ADO provider (SC-003)

## Final Phase: Polish & Cross-Cutting

- [ ] T064 Create `scripts/measure-orchestrator-latency.py` benchmark script — measures Python orchestrator vs baseline, reports delta ≤500ms (NFR-002)
- [ ] T065 Run full test suite and verify 100% coverage on all `agentic_devtools/cli/ci/` modules (NFR-001)
- [ ] T066 Update `pyproject.toml` with any new dependencies required by the CI module
- [ ] T067 Update `.github/copilot-instructions.md` — document new `agdt-ai-pr-loop` and `agdt-speckit-trigger` commands, CI provider architecture
- [ ] T068 Add `agdt-ai-pr-loop` and `agdt-speckit-trigger` to the command mapping table in copilot-instructions
- [ ] T069 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test layout compliance (NFR-001)
- [ ] T070 Run `bash scripts/run-pr-checks.sh` to verify all CI-blocking checks pass (NFR-001)

## Dependencies

| Task | Depends On |
|------|------------|
| T006 | T005 |
| T009 | T007, T008 |
| T011 | T010, T006 |
| T013 | T012, T009, T011 |
| T014 | T013 |
| T015 | T013 |
| T016 | T013 |
| T025 | T017–T024, T013 |
| T026 | T025, T003 |
| T027 | T025, T011 |
| T034 | T028–T033 |
| T039 | T035–T038, T034, T025 |
| T041 | T040 |
| T042 | T039 |
| T046 | T043–T045, T013 |
| T050 | T049 |
| T052 | T047, T048, T039, T046, T050 |
| T053 | T052 |
| T055 | T052, T053 |
| T056 | T052, T053 |
| T057 | T055, T056 |
| T059 | T055, T056 |
| T062 | T060, T061, T013 |
| T063 | T062, T039 |
| T064 | T039 |
| T065 | T059, T063 |
| T069 | T065 |
| T070 | T069 |

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T001, T002, T005, T006, T008, T009, T012, T013, T014, T015, T016, T060, T061 |
| FR-002 | T003, T005, T006, T007, T008, T009, T017, T018, T019, T020, T021, T022, T023, T024, T025, T026 |
| FR-003 | T035, T038, T039, T040, T041, T042 |
| FR-004 | T028, T029, T030, T031, T032, T033, T034, T036, T037 |
| FR-005 | T047, T048, T052, T053, T054, T058 |
| FR-006 | T043, T044, T045, T046 |
| FR-007 | T004, T049, T050, T051 |
| FR-008 | T055, T056, T057 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
