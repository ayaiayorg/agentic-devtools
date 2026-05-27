# Tasks: Copilot Agent Fallback on SpecKit Generation Failures

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|-------------|---------------|-------------|
| Phase 1: Setup & Scaffolding | (pre-requisite scaffolding, not a plan phase) | Repository and configuration prerequisites needed before implementation work begins. |
| Phase 2: Foundational — Upstream Signal Emission | Phase 1: Upstream Signal Emission | Establishes the upstream validation failure signals consumed by fallback logic. |
| Phase 3: User Story 1 — Automatic Agent Fallback | Phase 2: Shared Fallback Module + Phase 3: Workflow Integration | Implements the core automatic coding-agent fallback flow and integrates it into workflows. |
| Phase 4: User Story 2 — Observability via Labels and Comments | Phase 5: Follow-up Workflows (partial) | Adds labels and issue comments so fallback activity is visible to users and maintainers. |
| Phase 5: User Story 3 — Idempotent Fallback | Phase 4: Idempotency Guards | Prevents duplicate fallback task creation when workflows are retried or rerun. |
| Phase 6: User Story 4 — Graceful Degradation | Phase 2: Shared Fallback Module (degradation subset) | Ensures fallback failures degrade safely without breaking the primary workflow experience. |
| Phase 7: Polish & Cross-Cutting | Phase 6: Testing & Validation | Covers final validation, cleanup, and cross-cutting quality work across all stories. |

## Phase 1: Setup & Scaffolding

- [ ] T001 Create the `speckit:agent-fallback` label in the repository if it does not already exist
- [ ] T002 Add `SPECKIT_AGENT_FALLBACK` repository variable documentation to `.github/README.md` or equivalent
- [ ] T003 Add `SPECKIT_REFERENCE_SPEC_PATH` repository variable documentation alongside T002

## Phase 2: Foundational — Upstream Signal Emission

- [ ] T004 Modify `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` to emit `validation_errors` to `$GITHUB_OUTPUT` on structural validation failure (FR-001). Output format:
  semicolon-delimited `CATEGORY: detail` pairs. Ensure non-structural failures (auth, network, import errors) do NOT emit these markers (FR-002)
- [ ] T005 [P] Modify `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` to write `validation-errors.json` workspace file as fallback signal alongside `$GITHUB_OUTPUT` (FR-001)
- [ ] T006 Add `id: generate` (or equivalent step id) to the orchestrator step in both workflow files to enable `steps.generate.outputs.validation_errors` access

## Phase 3: User Story 1 — Automatic Agent Fallback (P1)

### Tests

- [ ] T007 [US1] Write happy-path unit tests for `detectStructuralFailure()` function: verify known structural signatures are detected and parsed from step outputs or fallback file (FR-001),
  and verify nominal non-structural failures are ignored without emitting fallback state (FR-002).
  File: `.github/scripts/speckit-trigger/__tests__/agent-fallback.test.js`
- [ ] T008 [US1] [P] Write happy-path unit tests for `buildProblemStatement()` function: verify issue title, body, phase, validation errors, and reference spec path are included in the
  success/nominal output (FR-003); verify truncation to 49,152 bytes with `[truncated]` marker within the 49,152-byte budget
- [ ] T009 [US1] [P] Write happy-path unit tests for `triggerCodingAgent()` function: verify correct API endpoint
  `POST /repos/{owner}/{repo}/copilot/coding-agent/tasks` is called with problem statement (FR-004); verify successful response parsing of `{id, url, status}`
- [ ] T010 [US1] [P] Write unit tests for kill-switch: verify the happy-path/success case runs fallback when `SPECKIT_AGENT_FALLBACK` is enabled or unset, and verify fallback is skipped
  entirely when `SPECKIT_AGENT_FALLBACK` is `"false"` (FR-009)
- [ ] T011 [US1] [P] Write happy-path unit tests verifying the module works with both phase 1 context and phases 2–5 context in nominal execution (FR-010)

### Implementation — Shared Module

- [ ] T012 [US1] Create `.github/scripts/speckit-trigger/agent-fallback.js` with exported `run()` function and `STRUCTURAL_ERROR_SIGNATURES` constants co-located with `spec-validation.sh` categories
  (FR-001, FR-002)
- [ ] T013 [US1] Implement `detectStructuralFailure(stepOutputs, workspaceFile)` — reads `validation_errors` from step outputs or falls back to `validation-errors.json`; returns structured error array
  or null for non-structural failures (FR-001, FR-002)
- [ ] T014 [US1] Implement `buildProblemStatement(issueTitle, issueBody, phase, validationErrors, referenceSpecPath)` — constructs agent prompt with 48KB UTF-8 truncation on issue body portion only,
  appends `[truncated]` marker within 49,152 byte budget (FR-003)
- [ ] T015 [US1] Implement `triggerCodingAgent(octokit, owner, repo, problemStatement, token)` — calls
  `POST /repos/{owner}/{repo}/copilot/coding-agent/tasks`, ensures the response includes `id` and `url` fields (FR-004)
- [ ] T016 [US1] Implement kill-switch check: read `SPECKIT_AGENT_FALLBACK` variable, skip fallback when `"false"` (FR-009)
- [ ] T017 [US1] Implement phase parameter acceptance so module handles all 5 phases with appropriate context (FR-010)

### Workflow Integration

- [ ] T018 [US1] Add "Agent Fallback" step to `.github/workflows/speckit-issue-trigger.yml` with `if: failure()`, loading `agent-fallback.js` via `actions/github-script@v7`, passing phase=1 (FR-010)
- [ ] T019 [US1] [P] Add "Agent Fallback" step to `.github/workflows/speckit-phase-progression.yml` with `if: failure()`, loading `agent-fallback.js` via `actions/github-script@v7`, passing dynamic
  phase (FR-010)
- [ ] T020 [US1] Modify existing "Handle Failure" step condition in both workflows to `if: failure() && steps.agent-fallback.outputs.triggered != 'true'` so standard failure only runs when fallback
  did NOT trigger

### Graceful Degradation

- [ ] T021 [US1] [P] Write unit tests for graceful degradation: verify non-2xx API response, missing `id`/`url` fields, and network timeout all fall through to standard failure handling (FR-011)
- [ ] T022 [US1] Implement graceful degradation in `triggerCodingAgent()`: on non-2xx response, missing `id`/`url`, or network error, set `outputs.triggered = 'false'` and log enhanced error details
  for the failure comment (FR-011)

## Phase 4: User Story 2 — Observability via Labels and Comments (P2)

### Tests

- [ ] T023 [US2] Write unit tests for `applyLabelsAndComment()`: verify `speckit:agent-fallback` label is added (FR-005), comment with task URL and marker is posted (FR-006), and `speckit:failed` is
  removed if present (FR-007)
- [ ] T024 [US2] [P] Write unit tests verifying the marker comment format `<!-- speckit:agent-fallback task_id=<id> task_url=<url> issue=<number> phase=<N> -->` is correct (FR-006)
- [ ] T025 [US2] [P] Write unit tests verifying `speckit:processing` label is NOT removed by the fallback step itself (FR-012 — it remains until terminal outcome)

### Implementation

- [ ] T026 [US2] Implement `applyLabelsAndComment(octokit, owner, repo, issueNumber, taskId, taskUrl, phase, validationErrors)` — adds `speckit:agent-fallback` label (FR-005), posts comment with task
  URL and machine-readable marker (FR-006), removes `speckit:failed` if present (FR-007)
- [ ] T027 [US2] Ensure fallback step does NOT remove `speckit:processing` label — label persists for async agent duration (FR-012)

### Follow-up Cleanup Workflow (FR-012)

- [ ] T028 [US2] Create `.github/workflows/speckit-agent-fallback-cleanup.yml` — Job 1: trigger on `pull_request [opened]`, validate head branch matches `speckit/*/phase-*` pattern, find linked issue,
  remove `speckit:processing` (FR-012)
- [ ] T029 [US2] Add Job 2 to cleanup workflow: `schedule` (every 15 min) + `workflow_dispatch` trigger, scan issues with `speckit:agent-fallback` label, parse marker comments for task IDs, query
  Coding Agent API for terminal status, remove `speckit:processing` on terminal failure (FR-012)
- [ ] T030 [US2] [P] Write tests for cleanup workflow logic: verify PR branch pattern matching, marker comment parsing, and label removal on terminal outcomes

## Phase 5: User Story 3 — Idempotent Fallback (P2)

### Tests

- [ ] T031 [US3] Write unit tests for `checkIdempotency()`: verify existing open PR on expected branch blocks new task creation (FR-008)
- [ ] T032 [US3] [P] Write unit tests for marker comment detection: verify existing `<!-- speckit:agent-fallback task_id=... -->` comment blocks duplicate task creation (FR-013)
- [ ] T033 [US3] [P] Write unit tests verifying skip comment is posted with link to existing PR/task when idempotency guard triggers

### Implementation

- [ ] T034 [US3] Implement `checkIdempotency(octokit, owner, repo, issueNumber, expectedBranch, phase)` — check for existing open PR on expected `speckit/{issue}/phase-{N}-{name}` branch (FR-008)
- [ ] T035 [US3] Extend `checkIdempotency()` to parse issue comments for existing marker comment `<!-- speckit:agent-fallback task_id=... issue=<N> phase=<N> -->` (FR-013)
- [ ] T036 [US3] Post skip comment with link to existing PR/task URL when idempotency guard fires (FR-008, FR-013)

## Phase 6: User Story 4 — Graceful Degradation (P3)

### Tests

- [ ] T037 [US4] Write unit tests verifying API 500/503 responses result in `speckit:failed` label + enhanced failure comment noting fallback attempt (FR-011)
- [ ] T038 [US4] [P] Write unit tests verifying network timeout results in same graceful degradation behavior (FR-011)
- [ ] T039 [US4] [P] Write unit tests verifying malformed API response (missing `id`/`url`) triggers graceful degradation (FR-011)

### Implementation

- [ ] T040 [US4] Implement enhanced failure comment template that includes fallback attempt details and API error information when graceful degradation triggers (FR-011)
- [ ] T041 [US4] Ensure `outputs.triggered` is set to `'false'` on all degradation paths so standard failure handler executes (FR-011)

## Phase 7: Polish & Cross-Cutting

- [ ] T042 [US1] Add integration test: simulate structural validation failure end-to-end via `workflow_dispatch` and verify agent task creation + labels + comments (FR-001, FR-004, FR-005, FR-006)
- [ ] T043 [US1] [P] Add integration test: verify kill-switch (`SPECKIT_AGENT_FALLBACK=false`) prevents all fallback behavior (FR-009)
- [ ] T044 [US1] [P] Add integration test: verify non-structural failure (mock auth error) does NOT trigger fallback (FR-002)
- [ ] T045 [US3] [P] Add integration test: verify idempotency — re-run after successful fallback creates no duplicate task (FR-008, FR-013)
- [ ] T046 [US4] [P] Add integration test: verify graceful degradation on mocked API failure (FR-011)
- [ ] T047 [US1] Measure workflow-specific code lines per workflow file and confirm fewer than 50 lines (NFR-005)
- [ ] T048 [US1] Refactor workflow code if any workflow file exceeds 50 lines of workflow-specific code (NFR-005)
- [ ] T049 [P] Add workflow step timeout to keep fallback completion within 30 seconds (NFR-001)
- [ ] T050 [US1] Update PR description documenting SC-001 through SC-006 compliance outcomes
- [ ] T051 Run full linting and validation: `bash scripts/run-pr-checks.sh`

---

## Dependency Graph

```text
T004, T005, T006 → T012 (signal emission before module can consume it)
T012 → T013, T014, T015, T016, T017 (module scaffold before functions)
T013, T014, T015, T016, T017 → T018, T019, T020 (module complete before wiring)
T026, T027 → T028, T029 (label logic before cleanup workflow)
T034, T035 → T036 (idempotency checks before skip comment)
T018, T019, T020, T022, T026, T034, T035, T036, T040 → T042–T046 (all impl before integration tests)
T042–T049 → T050, T051 (validation before final PR)
```

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T004, T005, T007, T012, T013, T042, T043, T044, T045, T046 |
| FR-002 | T004, T007, T012, T013, T042, T043, T044, T045, T046 |
| FR-003 | T008, T014 |
| FR-004 | T009, T015, T042, T043, T044, T045, T046 |
| FR-005 | T023, T026, T042, T043, T044, T045, T046 |
| FR-006 | T024, T026, T042, T043, T044, T045, T046 |
| FR-007 | T023, T026 |
| FR-008 | T031, T034, T036, T042, T043, T044, T045, T046 |
| FR-009 | T010, T016, T042, T043, T044, T045, T046 |
| FR-010 | T011, T017, T018, T019 |
| FR-011 | T021, T022, T037, T038, T039, T040, T041, T042, T043, T044, T045, T046 |
| FR-012 | T025, T027, T028, T029, T030 |
| FR-013 | T032, T035, T036, T042, T043, T044, T045, T046 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
