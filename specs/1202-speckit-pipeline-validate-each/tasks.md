# Tasks: SpecKit E.2 Test Coverage Validation

**Issue**: [#1202](https://github.com/ayaiayorg/agentic-devtools/issues/1202)
**Branch**: `speckit/1202/phase-4-tasks`

## Task Markers

- **[P]**: Can run in parallel (different files, no dependencies)
- **[USn]**: Belongs to User Story _n_ (e.g., [US1], [US2])

## Phase 1: Setup

- [ ] T001 Create `agentic_devtools/cli/speckit/pass_e2/` package with `__init__.py`
- [ ] T002 Create `tests/unit/cli/speckit/pass_e2/` directory tree with `__init__.py` files at each level

## Phase 2: Foundational — Data Models & Constants

- [ ] T003 [P] Write RED tests for `constants.py` verifying `TEST_TASK_KEYWORDS` contains all FR-002 keywords, `TEST_TYPE_KEYWORDS` contains all FR-006 type tables, sets are non-empty, no duplicates
  in `tests/unit/cli/speckit/pass_e2/constants/`
  - Depends on: T002
- [ ] T004 [P] Implement `constants.py` with `TEST_TASK_KEYWORDS` list (FR-002/FR-011) and `TEST_TYPE_KEYWORDS` dict (FR-006) as a discoverable single-edit location in
  `agentic_devtools/cli/speckit/pass_e2/constants.py`
  - Depends on: T001, T003
- [ ] T005 [P] Write RED tests for `models.py` — `TestTask`, `FRInfo`, `FRCoverage`, `TestCoverageResult`, `TestCoverageFinding` data classes with field access, equality, serialization in
  `tests/unit/cli/speckit/pass_e2/models/`
  - Depends on: T002
- [ ] T006 [P] Implement `models.py` with all data classes in `agentic_devtools/cli/speckit/pass_e2/models.py`
  - Depends on: T001, T005

## Phase 3: User Story 1 — Detect FRs with No Test Task (P1)

### Spec Parser (FR-001, FR-003)

- [ ] T007 [US1] Write RED tests for `spec_parser.extract_frs_with_priority()` — extract FR identifiers with user-story priority (P1/P2/P3), default to non-P1 when undetermined per FR-001, emit LOW
  finding with key `FR-NNN:priority-ambiguous` in `tests/unit/cli/speckit/pass_e2/spec_parser/`
  - Depends on: T004, T006
- [ ] T008 [US1] Implement `spec_parser.extract_frs_with_priority()` in `agentic_devtools/cli/speckit/pass_e2/spec_parser.py`
  - Depends on: T007
- [ ] T009 [US1] Write RED tests for `spec_parser.parse_user_story_sections()` — positional extraction of user story sections, collecting FR references within each section's text boundary per FR-003
  in `tests/unit/cli/speckit/pass_e2/spec_parser/`
  - Depends on: T004, T006
- [ ] T010 [US1] Implement `spec_parser.parse_user_story_sections()` in `agentic_devtools/cli/speckit/pass_e2/spec_parser.py`
  - Depends on: T009
- [ ] T011 [US1] Write RED tests for `spec_parser.build_us_to_fr_mapping()` — produce `{1: ["FR-001", "FR-003"], 2: ["FR-002"]}` from parsed sections per FR-003 in
  `tests/unit/cli/speckit/pass_e2/spec_parser/`
  - Depends on: T010
- [ ] T012 [US1] Implement `spec_parser.build_us_to_fr_mapping()` in `agentic_devtools/cli/speckit/pass_e2/spec_parser.py`
  - Depends on: T011

### Task Classifier (FR-002, FR-006)

- [ ] T013 [US1] Write RED tests for `task_classifier.is_test_task()` — single-word keyword matching with word boundaries per FR-002, multi-word with hyphen/space normalization, plurals,
  case-insensitive, false-positive avoidance ("contest", "unverified") in `tests/unit/cli/speckit/pass_e2/task_classifier/`
  - Depends on: T004, T006
- [ ] T014 [US1] Implement `task_classifier.is_test_task()` using FR-002 keyword matching semantics in `agentic_devtools/cli/speckit/pass_e2/task_classifier.py`
  - Depends on: T013
- [ ] T015 [US1] Write RED tests for `task_classifier.extract_task_fr_refs()` — explicit FR-NNN references and `[USn]` label extraction from task descriptions in
  `tests/unit/cli/speckit/pass_e2/task_classifier/`
  - Depends on: T004, T006
- [ ] T016 [US1] Implement `task_classifier.extract_task_fr_refs()` in `agentic_devtools/cli/speckit/pass_e2/task_classifier.py`
  - Depends on: T015

### Coverage Mapper (FR-003, FR-004)

- [ ] T017 [US1] Write RED tests for `coverage_mapper.map_test_tasks_to_frs()` — explicit FR refs, US-label mapping via `us_to_fr`, unmapped test tasks, invalid US refs per FR-003 in
  `tests/unit/cli/speckit/pass_e2/coverage_mapper/`
  - Depends on: T012, T016
- [ ] T018 [US1] Implement `coverage_mapper.map_test_tasks_to_frs()` in `agentic_devtools/cli/speckit/pass_e2/coverage_mapper.py`
  - Depends on: T017
- [ ] T019 [US1] Write RED tests for `coverage_mapper.evaluate_coverage()` — FR with zero test tasks → HIGH finding per FR-004, fully covered FR → no finding in
  `tests/unit/cli/speckit/pass_e2/coverage_mapper/`
  - Depends on: T018
- [ ] T020 [US1] Implement `coverage_mapper.evaluate_coverage()` in `agentic_devtools/cli/speckit/pass_e2/coverage_mapper.py`
  - Depends on: T019
- [ ] T021 [US1] Write RED tests for edge cases — empty tasks.md → CRITICAL finding with key `TASK:empty-tasks-file` per FR-009, missing tasks.md → CRITICAL with key `TASK:missing-tasks-file`, FR
  without acceptance scenarios in `tests/unit/cli/speckit/pass_e2/coverage_mapper/`
  - Depends on: T018
- [ ] T022 [US1] Implement edge-case handling in `coverage_mapper.py` for FR-009 (missing/empty tasks.md)
  - Depends on: T021

## Phase 4: User Story 2 — Flag Missing Happy-Path Tests for P1 FRs as CRITICAL (P1)

### Test-Type Classification (FR-006)

- [ ] T023 [US2] Write RED tests for `task_classifier.classify_test_types()` — happy-path, edge-case, negative, integration, e2e, unit, infrastructure keywords per FR-006; multiple types per task;
  hyphen/space normalization in `tests/unit/cli/speckit/pass_e2/task_classifier/`
  - Depends on: T004, T006
- [ ] T024 [US2] Implement `task_classifier.classify_test_types()` in `agentic_devtools/cli/speckit/pass_e2/task_classifier.py`
  - Depends on: T023
- [ ] T025 [US2] Write RED tests for `task_classifier.detect_ambiguous_task()` — tasks with both implementation and test keywords flagged as ambiguous in
  `tests/unit/cli/speckit/pass_e2/task_classifier/`
  - Depends on: T014
- [ ] T026 [US2] Implement `task_classifier.detect_ambiguous_task()` in `agentic_devtools/cli/speckit/pass_e2/task_classifier.py`
  - Depends on: T025

### Task-Scoped Findings

- [ ] T027 [US2] Write RED tests for `coverage_mapper.generate_task_scoped_findings()` — invalid `[USn]` refs → LOW `TASK:invalid-us-ref`, unmapped test tasks → LOW `TASK:unmapped-test-task`,
  ambiguous tasks → LOW `TASK:ambiguous-task` in `tests/unit/cli/speckit/pass_e2/coverage_mapper/`
  - Depends on: T026, T018
- [ ] T028 [US2] Implement `coverage_mapper.generate_task_scoped_findings()` in `agentic_devtools/cli/speckit/pass_e2/coverage_mapper.py`
  - Depends on: T027

### CRITICAL Severity Escalation (FR-005)

- [ ] T029 [US2] Write RED tests for `coverage_mapper.evaluate_coverage()` CRITICAL path — P1 FR with no happy-path test → CRITICAL per FR-005, de-duplication of FR-004+FR-005 → single CRITICAL, P3
  FR with no test → HIGH not CRITICAL in `tests/unit/cli/speckit/pass_e2/coverage_mapper/`
  - Depends on: T024, T020
- [ ] T030 [US2] Implement CRITICAL severity escalation in `coverage_mapper.evaluate_coverage()` for P1 FRs missing happy-path tests per FR-005
  - Depends on: T029

## Phase 5: User Story 3 — Test Coverage Summary in Report (P2)

### Reporter — Summary Table (FR-007)

- [ ] T031 [US3] Write RED tests for `reporter.render_test_coverage_summary()` — table with columns per FR-007: FR identifier, associated user story, test task IDs (or "None"), detected test types,
  coverage status; "N/A" for unknown user story in `tests/unit/cli/speckit/pass_e2/reporter/`
  - Depends on: T030, T028
- [ ] T032 [US3] Implement `reporter.render_test_coverage_summary()` producing the FR-007 Test Coverage Summary table in `agentic_devtools/cli/speckit/pass_e2/reporter.py`
  - Depends on: T031

### Reporter — Findings Rendering (FR-008)

- [ ] T033 [US3] Write RED tests for `reporter.render_findings()` — severity column, Recommendation referencing specific FR and acceptance scenarios (or "N/A" when none exist per FR-008), CRITICAL vs
  HIGH vs LOW distinction, task-scoped findings in "Unmapped Tasks" sub-section in `tests/unit/cli/speckit/pass_e2/reporter/`
  - Depends on: T032
- [ ] T034 [US3] Implement `reporter.render_findings()` with actionable recommendations per FR-008 in `agentic_devtools/cli/speckit/pass_e2/reporter.py`
  - Depends on: T033

## Phase 6: User Story 4 — Actionable Remediation Guidance (P3)

- [ ] T035 [US4] Write RED tests verifying CRITICAL findings for P1 FR missing happy-path include recommendation to re-run `/speckit.tasks` or manually add test task referencing the FR per FR-008 in
  `tests/unit/cli/speckit/pass_e2/reporter/`
  - Depends on: T034
- [ ] T036 [US4] Write RED tests verifying HIGH findings for any FR missing test task include recommendation referencing specific acceptance scenarios from spec per FR-008 in
  `tests/unit/cli/speckit/pass_e2/reporter/`
  - Depends on: T034
- [ ] T037 [US4] Implement remediation recommendation logic in `reporter.render_findings()` ensuring every finding has a non-empty actionable Recommendation per FR-008 in
  `agentic_devtools/cli/speckit/pass_e2/reporter.py`
  - Depends on: T035, T036

## Phase 7: Orchestrator & CLI (FR-010)

- [ ] T038 Write RED tests for `validator.validate_test_coverage()` — end-to-end: spec+tasks input → `TestCoverageResult` with findings, summary, coverage mappings per FR-010 in
  `tests/unit/cli/speckit/pass_e2/validator/`
  - Depends on: T037
- [ ] T039 Implement `validator.validate_test_coverage()` orchestrating the full E.2 pipeline in `agentic_devtools/cli/speckit/pass_e2/validator.py`
  - Depends on: T038
- [ ] T040 Write RED tests for CLI entry point `test_coverage_command()` — JSON output, human-readable output, exit codes (0=clean, 1=findings, 2=fatal) in `tests/unit/cli/speckit/pass_e2/validator/`
  - Depends on: T039
- [ ] T041 Implement CLI entry point in `agentic_devtools/cli/speckit/pass_e2/validator.py`
  - Depends on: T040
- [ ] T042 Add `agdt-speckit-test-coverage` to `COMMAND_MAP` in `agentic_devtools/cli/runner.py` and `[project.scripts]` entry in `pyproject.toml`
  dispatching through `agentic_devtools.cli.runner:run_as_script` (consistent with existing `agdt-speckit-*` entry points)
  - Depends on: T041
- [ ] T043 Add exports in `pass_e2/__init__.py` and `speckit/__init__.py`
  - Depends on: T041
- [ ] T044 Reinstall package and verify `agdt-speckit-test-coverage --help` runs successfully
  - Depends on: T042, T043

## Phase 8: Agent Prompt Integration (FR-010)

- [ ] T045 [P] Update Category E in `.github/agents/speckit.analyze.agent.md` — rename existing coverage check to "E.1 Task Coverage", add "E.2 Test Coverage Validation" sub-pass per FR-010
  - Depends on: T044
- [ ] T046 [P] Update "Load Artifacts" section (Step 2) in `.github/agents/speckit.analyze.agent.md` to include `test-coverage.json` loading
  - Depends on: T044
- [ ] T047 [P] Update "Produce Compact Analysis Report" section (Step 6) in `.github/agents/speckit.analyze.agent.md` to include "Test Coverage Summary" table per FR-007
  - Depends on: T044
- [ ] T048 [P] Update Severity Assignment (Step 5) in `.github/agents/speckit.analyze.agent.md` to document CRITICAL for P1+no-happy-path per FR-005, HIGH for any-FR+no-test-task per FR-004
  - Depends on: T044
- [ ] T049 [P] Update Metrics section in `.github/agents/speckit.analyze.agent.md` to include test-coverage metrics
  - Depends on: T044

## Phase 9: Regression Tests & Fixtures (NFR-003)

- [ ] T050 [P] Create `specs/1202-speckit-pipeline-validate-each/fixtures/sc-001/spec.md` — synthetic spec with P1 FR-001 and no happy-path test task (SC-001)
  - Depends on: T044
- [ ] T051 [P] Create `specs/1202-speckit-pipeline-validate-each/fixtures/sc-001/tasks.md` — implementation tasks + infrastructure tests but no happy-path test for FR-001 (SC-001)
  - Depends on: T050
- [ ] T052 Write parameterized regression test `test_regression_specs_zero_false_positives` per NFR-003 — discovers all `specs/*/` with both `spec.md` and `tasks.md`, runs `validate_test_coverage()`,
  asserts finding keys match `expected-findings.txt` allowlist (set semantics) or zero findings in `tests/unit/cli/speckit/pass_e2/validator/`
  - Depends on: T039, T051
- [ ] T053 Run regression test against all existing specs and create `expected-findings.txt` allowlist files where needed
  - Depends on: T052
- [ ] T054 Write SC-001 test — verify CRITICAL finding for FR-001 missing happy-path test in sc-001 fixture (SC-001, FR-005)
  - Depends on: T051, T052
- [ ] T055 [P] Write SC-003 test — verify Test Coverage Summary table with 3+ FRs includes one row per FR with accurate mapping (SC-003, FR-007)
  - Depends on: T052
- [ ] T056 [P] Write SC-004 test — verify all findings have non-empty actionable Recommendation referencing specific FR (SC-004, FR-008)
  - Depends on: T052
- [ ] T057 [P] Write SC-005 test — verify CRITICAL vs HIGH severity distinction is consistently applied (SC-005, FR-004, FR-005)
  - Depends on: T052

## Phase 10: Pipeline Integration

- [ ] T058 Add `run_test_coverage_validation()` bash function in `generate-spec-from-issue.sh` calling
  `agdt-speckit-test-coverage --spec-file "$SPEC_DIR/spec.md" --tasks-file "$SPEC_DIR/tasks.md" --json` saving output to `$SPEC_DIR/test-coverage.json`
  - Depends on: T044
- [ ] T059 Integrate `run_test_coverage_validation()` in pipeline after `run_fr_validation()` before analysis phase in `generate-spec-from-issue.sh`
  - Depends on: T058
- [ ] T060 Update `run_analyze_phase` in `generate-spec-from-issue.sh` to load `test-coverage.json` into inline LLM prompt context
  - Depends on: T059
- [ ] T061 Write end-to-end smoke test verifying pipeline integration including `test-coverage.json` artifact presence
  - Depends on: T060

## Phase 11: Polish & Cross-Cutting

- [ ] T062 Run full test suite (`agdt-test` + `agdt-task-wait`) and verify all tests pass
  - Depends on: T057, T061
- [ ] T063 Run `bash scripts/run-pr-checks.sh` and fix any failures
  - Depends on: T062
- [ ] T064 Manual verification against SC-001 fixture — confirm CRITICAL finding for FR-001 missing happy-path
  - Depends on: T063
- [ ] T065 Verify backward compatibility — all existing specs produce no new false positives (NFR-003 regression green)
  - Depends on: T063

---
_Generated by Copilot SDK (claude-opus-4.6)_
