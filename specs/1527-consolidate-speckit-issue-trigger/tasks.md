# Tasks: Consolidate SpecKit Issue Trigger into Phase Progression Pipeline

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup & Analysis | Phase A | Verify existing phase-progression behavior before changes |
| Phase 2: Foundational — Extend Progression | Phase A | Extend progression workflow to accept phase=1 (FR-001, FR-002, FR-003) |
| Phase 3: US1 — Phase 1 PRs with Human Identity | Phase A, Phase D | Token validation + test tasks for human-identity PR creation |
| Phase 4: US2 — Single Workflow Handles All Phases | Phase A, Phase B | Unified phases 1–5 + PR trigger verification |
| Phase 5: US3 — Thin Dispatcher | Phase B | Convert issue trigger to thin dispatcher (FR-004, FR-005) |
| Phase 6: US4 — Remove Python Orchestrator | Phase D | Remove Python commit/push/PR logic (FR-006) |
| Phase 7: US5 — Feature Parity for Phase 1 | Phase A, Phase C | Idempotency, auto-merge, failure handling, critical gate for phase 1 |
| Phase 8: US6 — Workflow Documentation | Phase E | Update workflow docs for consolidated architecture |
| Phase 9: Polish & Cross-Cutting | Phase F | Integration testing, full test run, end-to-end validation |

## Phase 1: Setup & Analysis

- [x] T001 Verify existing `speckit-phase-progression.yml` extract step handles `phase=1` correctly (outputs `completed_phase=0`, `next_phase=1`, `next_phase_name=specify`) (FR-001) —
  `.github/workflows/speckit-phase-progression.yml`
- [x] T002 Verify existing "Create Pull Request" step already uses `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` via `GH_TOKEN` env for all phases (FR-002, FR-014) — `.github/workflows/speckit-phase-progression.yml`
- [x] T003 Verify feature flags (`SPECKIT_CREATE_BRANCH`, `SPECKIT_CREATE_PR`, `SPECKIT_CRITICAL_GATE_MODE`) already apply universally (no phase-gating) (FR-015) —
  `.github/workflows/speckit-phase-progression.yml`
- [x] T004 Verify existing `speckit:phase-1` label in PR merge trigger condition for Phase 2 progression (FR-012) — `.github/workflows/speckit-phase-progression.yml` line 45

## Phase 2: Foundational — Extend Progression Workflow for Phase 1

- [x] T005 Add `'1'` to `workflow_dispatch.inputs.phase.options` list (FR-001) — `.github/workflows/speckit-phase-progression.yml` line 16–20
- [x] T006 Update "Validate Tokens" step to require `COPILOT_GITHUB_TOKEN` for Copilot SDK auth and to report whether `SPECKIT_PR_TOKEN` is set (preferred for PR creation);
  MUST NOT fall back to `GITHUB_TOKEN` (FR-002, FR-014) — `.github/workflows/speckit-phase-progression.yml` lines 455–472
- [x] T007 Verify that the "Add Processing Label" step already fires for phase 1 (condition: `next_phase != '0' && next_phase != '6'`) — confirms FR-013 coverage —
  `.github/workflows/speckit-phase-progression.yml` line 172–188
- [x] T008 Verify the "Push Branch" step condition includes phase 1 (not gated on phase number) and respects `SPECKIT_CREATE_BRANCH` (FR-003, FR-015) —
  `.github/workflows/speckit-phase-progression.yml` line 532–536
- [x] T009 Verify the "Check Phase Idempotency" step works for phase 1 (passes `--phase 1` from `next_phase` output) (FR-007) — `.github/workflows/speckit-phase-progression.yml` line 303–310
- [x] T010 Verify the "Add ai-auto-merge-allowed label" step fires for phase 1 (condition: `next_phase != '0' && next_phase != '6'` and `next_phase_name != 'clarify'`) (FR-008) —
  `.github/workflows/speckit-phase-progression.yml` line 602–629

## Phase 3: User Story 1 — Phase 1 PRs Created with Human Identity Token (P1)

- [ ] T011 [US1] Write integration test verifying `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` is used for PR creation step when `phase=1` (not `GITHUB_TOKEN`) — `tests/unit/cli/ci/` (new test)
- [ ] T012 [US1] Write test: when both `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` are unset, token validation fails before PR creation (FR-014) — `tests/unit/cli/ci/` (new test)
- [ ] T013 [US1] Write happy-path test: when `SPECKIT_PR_TOKEN` is unset but `COPILOT_GITHUB_TOKEN` is set, fallback works gracefully (FR-002) — `tests/unit/cli/ci/` (new test)
- [x] T014 [US1] Update the "Validate Tokens" step to add `SPECKIT_PR_TOKEN` to environment and check
  `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` resolution with clear error message (FR-002, FR-014) — `.github/workflows/speckit-phase-progression.yml`

## Phase 4: User Story 2 — Single Workflow Handles All Phases 1–5 (P1)

- [x] T015 [US2] Confirm extract step produces correct outputs for `phase=1` dispatch: `completed_phase=0`, `next_phase=1`, `next_phase_name=specify` (FR-011) —
  `.github/workflows/speckit-phase-progression.yml`
- [ ] T016 [US2] Verify `generate-spec-from-issue.sh` supports `--phase 1` and generates `spec.md` + empty `checklists/` + empty `contracts/` — happy-path success scenario (FR-003) —
  `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`
- [x] T017 [US2] Verify the commit step message format works for phase 1: `spec(specify): Phase 1 artifacts for issue #N` (FR-003) — `.github/workflows/speckit-phase-progression.yml` lines 500–530
- [x] T018 [US2] Verify PR creation step invokes `create-spec-pr.sh` with `--phase-number 1 --phase-name specify` (FR-003) — `.github/workflows/speckit-phase-progression.yml` lines 538–600
- [x] T019 [US2] Verify PR merge of `speckit:phase-1` labeled PR triggers Phase 2 dispatch (FR-012 non-regression) — `.github/workflows/speckit-phase-progression.yml` lines 39–50
- [x] T020 [US2] Confirm `SPECKIT_CREATE_BRANCH`, `SPECKIT_CREATE_PR`, `SPECKIT_CRITICAL_GATE_MODE` apply to phase 1 (FR-015) — `.github/workflows/speckit-phase-progression.yml`

## Phase 5: User Story 3 — Thin Dispatcher for Label-Based Triggering (P2)

- [x] T021 [US3] Replace `speckit-issue-trigger.yml` job body with thin dispatcher: remove Python setup, pip install, `agdt-speckit-trigger` call, and "Add ai-auto-merge-allowed" step (FR-004) —
  `.github/workflows/speckit-issue-trigger.yml`
- [x] T022 [US3] Remove `AGDT_USE_PYTHON_ORCHESTRATOR` env var from dispatcher workflow (FR-004) — `.github/workflows/speckit-issue-trigger.yml` line 11
- [x] T023 [US3] Change permissions to `actions: write, issues: write` (drop `contents: write`, `pull-requests: write`) (FR-004) — `.github/workflows/speckit-issue-trigger.yml` line 8
- [x] T024 [US3] Add dispatch step using `gh api` or `actions/github-script` to POST `workflow_dispatch` to `speckit-phase-progression.yml` with
  `{"ref":"main","inputs":{"issue_number":"N","phase":"1"}}` using `GITHUB_TOKEN` (FR-004) — `.github/workflows/speckit-issue-trigger.yml`
- [x] T025 [US3] Retain per-issue concurrency group `speckit-trigger-${{ github.event.issue.number || inputs.issue_number }}`
  with `cancel-in-progress: false` (FR-005) — `.github/workflows/speckit-issue-trigger.yml` lines 13–15
- [x] T026 [US3] Retain the `speckit` / `SPECKIT_TRIGGER_LABEL` label filter condition (FR-005) — `.github/workflows/speckit-issue-trigger.yml` lines 21–24
- [x] T027 [US3] Keep "Add Processing Label" step in dispatcher (or verify progression handles it) — `.github/workflows/speckit-issue-trigger.yml`
- [x] T028 [US3] Retain failure handling steps (comment + `speckit:failed` label) for dispatch errors (FR-005) — `.github/workflows/speckit-issue-trigger.yml`
- [x] T029 [US3] Verify dispatcher is < 30 lines of workflow logic (excluding failure handling) — `.github/workflows/speckit-issue-trigger.yml`

## Phase 6: User Story 4 — Remove Python Orchestrator Commit/Push/PR Logic (P2)

- [x] T030 [US4] Write test: `speckit_trigger_command()` stub prints migration message and exits with code 1 (FR-006) — `tests/unit/cli/ci/commands/test_speckit_trigger_command.py`
- [x] T031 [US4] Delete `_commit_and_push_phase_branch()` from `speckit_trigger.py` (FR-006) — `agentic_devtools/cli/ci/speckit_trigger.py` lines 238–267
- [x] T032 [US4] Delete `_create_phase_pull_request()` from `speckit_trigger.py` (FR-006) — `agentic_devtools/cli/ci/speckit_trigger.py` lines 270–285
- [x] T033 [US4] Delete `process_speckit_label_event()` and supporting private functions (`_load_issue_context_from_event`, `_set_issue_labels`, `_run_script_with_outputs`, `_parse_key_value_file`,
  `_run_checked`, `_require_repository`, `_IssueContext`) (FR-006) — `agentic_devtools/cli/ci/speckit_trigger.py`
- [x] T034 [US4] Replace `speckit_trigger_command()` in `commands.py` with a stub that prints migration message and exits with code 1 (FR-006) — `agentic_devtools/cli/ci/commands.py` lines 119–180
- [x] T035 [US4] Remove `from agentic_devtools.cli.ci.speckit_trigger import process_speckit_label_event` import from `commands.py` (FR-006) — `agentic_devtools/cli/ci/commands.py` line 24
- [x] T036 [US4] Remove `_python_orchestrator_enabled()` helper or its usage in `speckit_trigger_command()` (FR-006) — `agentic_devtools/cli/ci/commands.py`
- [x] T037 [US4] Update/remove tests for `process_speckit_label_event` (FR-006) — `tests/unit/cli/ci/speckit_trigger/test_process_speckit_label_event.py`
- [x] T038 [US4] Retain `agdt-speckit-trigger` entry point in `pyproject.toml` pointing to stub (FR-006) — `pyproject.toml`
- [ ] T039 [US4] Run full test suite to confirm no regressions — `agdt-test`

## Phase 7: User Story 5 — Feature Parity for Phase 1 (P1)

- [x] T040 [US5] Verify idempotency step skips PR creation when Phase 1 branch already exists (FR-007) — `.github/workflows/speckit-phase-progression.yml` lines 303–362
- [x] T041 [US5] Verify `ai-auto-merge-allowed` label is added for phase 1 (FR-008) — happy-path success when
  `SPECKIT_AUTO_MERGE_ALLOWED_LABEL == 'true'` in `.github/workflows/speckit-phase-progression.yml` lines
  602–629
- [x] T042 [US5] Add failure handling step to progression workflow for phase 1: post failure comment + apply `speckit:failed` label on error (FR-009) —
  `.github/workflows/speckit-phase-progression.yml`
- [x] T043 [US5] Verify critical gate draft mode: when `SPECKIT_CRITICAL_GATE_MODE == 'draft'` and gate fails, PR is created as draft with critical findings (FR-010) —
  `.github/workflows/speckit-phase-progression.yml` lines 552–558
- [x] T044 [US5] Verify `speckit:processing` label is added at start and removed on completion/failure for phase 1 (FR-013) — `.github/workflows/speckit-phase-progression.yml`

## Phase 8: User Story 6 — Workflow Documentation Updated (P3)

- [x] T045 [P] [US6] Update `.github/workflows/README.md` to describe consolidated single-workflow architecture (Phases 1–5) and thin dispatcher for label events
- [x] T046 [P] [US6] Add instructions for manual Phase 1 trigger via `workflow_dispatch` with `phase=1` on `speckit-phase-progression.yml`
- [x] T047 [P] [US6] Remove or update references to `speckit-issue-trigger.yml` as a Phase 1 executor in documentation

## Phase 9: Polish & Cross-Cutting

- [x] T048 Verify the progression workflow's existing failure handling step covers phase 1 (comment + `speckit:failed` label + `speckit:processing` removal) (FR-009) —
  `.github/workflows/speckit-phase-progression.yml`
- [ ] T049 [US2] Run `agdt-test` full test suite and verify all tests pass
- [ ] T050 [US4] Run `bash scripts/targeted-checks.sh` for lint, format, type-check, and coverage validation
- [x] T051 Verify `speckit-issue-trigger.yml` final line count is minimal (< 30 lines of dispatch logic) (FR-004)
- [ ] T052 End-to-end validation: manually dispatch `speckit-phase-progression.yml` with `phase=1` and `issue_number=N` and verify full artifact generation + PR creation (FR-001, FR-003)

## Dependencies

```text
T005 → T006, T014 (phase option must exist before token validation matters)
T005 → T015, T016, T017, T018 (phase 1 must be accepted before verifying generation)
T014 → T012, T013 (token step updated before testing)
T021 → T022, T023, T024, T025, T026, T027, T028, T029 (dispatcher rewrite is sequential)
T030 → T034 (test written before stub implementation — TDD)
T031, T032, T033 → T035, T036 (delete functions before cleaning imports)
T034, T037 → T039 (all code changes done before full test run)
T005, T006, T021, T034 → T048, T049, T050 (all changes complete before cross-cutting validation)
```

## FR Coverage Matrix

| FR | Tasks |
|---|---|
| FR-001 | T001, T005, T052 |
| FR-002 | T002, T006, T013, T014 |
| FR-003 | T008, T016, T017, T018, T052 |
| FR-004 | T021, T022, T023, T024, T051 |
| FR-005 | T025, T026, T028 |
| FR-006 | T030, T031, T032, T033, T034, T035, T036, T037, T038 |
| FR-007 | T009, T040 |
| FR-008 | T010, T041 |
| FR-009 | T042, T048 |
| FR-010 | T043 |
| FR-011 | T015 |
| FR-012 | T004, T019 |
| FR-013 | T007, T044 |
| FR-014 | T002, T006, T012, T014 |
| FR-015 | T003, T008, T020 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
