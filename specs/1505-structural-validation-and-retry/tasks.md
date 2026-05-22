# Tasks: Structural Validation and Retry for Phase 1 (Specify)

**Issue**: [#1505](https://github.com/ayaiayorg/agentic-devtools/issues/1505)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase A | Initial scaffolding for the new validation library and test harness |
| Phase 2: Foundational | Phase A, Phase C | Shared constants and dependency contracts required before story delivery |
| Phase 3: User Story 1 — Spec Validation | Phase A, Phase D | Core validation behavior and direct unit/integration coverage |
| Phase 4: User Story 2 — Automatic Retry | Phase B, Phase E | Specify retry orchestration, feedback generation, and retry-path integration tests |
| Phase 5: User Story 3 — Summary/Bullet Detection | Phase A, Phase D | Bullet-ratio validation logic and coverage |
| Phase 6: User Story 4 — Shared Validation Helpers | Phase C, Phase E | Backward-compatible helper extraction and regression checks |
| Phase 7: User Story 5 — Configurable Thresholds | Phase A, Phase D | Threshold override behavior and tests |
| Phase 8: Polish & Cross-Cutting | Phase D, Phase E | Final verification, determinism/performance checks, and regression validation |

## Phase 1: Setup

- [ ] T001 Scaffold `lib/spec-validation.sh` with sourcing guard (`_SPEC_VALIDATION_LIB_LOADED`), file header comment, and empty function stubs at
  `.github/scripts/speckit-trigger/lib/spec-validation.sh`
- [ ] T002 Scaffold test file `.github/scripts/speckit-trigger/test_spec_validation.sh` with test harness (assert_eq, assert_contains, PASS/FAIL counters) following `test_clarify_retry.sh` pattern (FR-001)

## Phase 2: Foundational — Threshold Constants & Shared Helpers

- [ ] T003 Define configurable threshold constants at top of `lib/spec-validation.sh`: `MIN_FUNCTIONAL_REQUIREMENTS=5`, `MIN_USER_STORIES=3`, `MIN_SPEC_BYTES=2048`, `MIN_MEASURABLE_CRITERIA_PCT=50`,
  `MAX_BULLET_LINE_PCT=80`, `SPECIFY_MAX_RETRIES=3` (FR-013, NFR-004)
- [ ] T004 Document dependency contract at top of `lib/spec-validation.sh` listing required functions from sourcing script (`extract_section_headings`, `count_requirement_entries`,
  `MANDATORY_SECTIONS`) matching `lib/clarify-retry.sh` pattern (FR-013, NFR-005)

## Phase 3: User Story 1 — Spec Validation Blocks Underspecified Output (P1)

- [ ] T005 [US1] Write failing test TC02 in `test_spec_validation.sh`: missing mandatory section returns MISSING_SECTIONS failure (FR-002)
- [ ] T006 [P] [US1] Write failing test TC03: spec below 2048 bytes returns BELOW_SIZE_THRESHOLD failure (FR-006)
- [ ] T007 [P] [US1] Write failing test TC04: fewer than 5 FRs returns INSUFFICIENT_REQUIREMENTS failure (FR-003)
- [ ] T008 [P] [US1] Write failing test TC05: fewer than 3 user stories returns INSUFFICIENT_USER_STORIES failure (FR-004)
- [ ] T009 [P] [US1] Write failing test TC06: non-measurable success criteria returns NON_MEASURABLE_CRITERIA failure (FR-005)
- [ ] T010 [P] [US1] Write failing test TC01: valid spec with all checks passing returns 0 (FR-001)
- [ ] T011 [US1] Implement `_check_mandatory_sections <filepath>` in `lib/spec-validation.sh` — verifies all 4 mandatory sections present (FR-002)
- [ ] T012 [US1] Implement `_count_functional_requirements <filepath>` in `lib/spec-validation.sh` — counts `**FR-###**` pattern entries (FR-003)
- [ ] T013 [US1] Implement `_count_user_stories <filepath>` in `lib/spec-validation.sh` — counts headings matching `### User Story` prefix (case-insensitive) with at least one Given/When/Then scenario
  (FR-004)
- [ ] T014 [US1] Implement `_check_measurable_criteria <filepath>` in `lib/spec-validation.sh` — checks ≥50% of `**SC-###**` entries contain number/percentage/quantitative target (FR-005)
- [ ] T015 [US1] Implement byte-size check within the core spec-quality orchestrator — reject specs below `MIN_SPEC_BYTES` on post-processed content (FR-006, FR-012)
- [ ] T016 [US1] Implement core spec-quality orchestrator in `lib/spec-validation.sh` — runs all checks, outputs structured failure categories on stdout, returns 0 on pass / 1 on fail
  (FR-001, FR-012)
- [ ] T017 [US1] Write boundary test TC08: spec with exactly 5 FRs passes the FR check in `test_spec_validation.sh` (FR-003)
- [ ] T018 [US1] Write compound failure test TC09: multiple failures reported together in `test_spec_validation.sh` (FR-002, FR-003, FR-004, FR-005, FR-006)

## Phase 4: User Story 2 — Automatic Retry with Structured Feedback (P1)

- [ ] T019 [US2] Implement `_build_structured_specify_feedback <filepath> <failures>` in `lib/spec-validation.sh` — formats categorized failures into LLM retry prompt section with actual vs. expected
  values (FR-009, NFR-002)
- [ ] T020 [US2] Implement `_run_specify_with_validation()` function in `generate-spec-from-issue.sh` — wraps LLM call + post-processing + validation; returns 0 on pass, 1 on validation fail, 2 on
  operational fail (FR-008, FR-010)
- [ ] T021 [US2] Implement retry loop in `run_single_phase()` specify block (lines ~3382-3396) of `generate-spec-from-issue.sh` — calls `_run_specify_with_validation()` up to `SPECIFY_MAX_RETRIES`
  times, re-prompting with full original prompt + failed output + structured feedback (FR-008, FR-009, FR-012)
- [ ] T022 [US2] Apply identical retry logic to sequential flow specify block (lines ~3528-3539) of `generate-spec-from-issue.sh` by calling shared `_run_specify_with_validation()` (FR-008)
- [ ] T023 [US2] Implement exit-code-1 with stderr error output when all retries exhausted in `generate-spec-from-issue.sh` (FR-011)
- [ ] T024 [US2] Ensure operational failures (return code 2 from `call_llm` wrapper) do NOT decrement retry budget in the retry loop (FR-010)
- [ ] T025 [US2] Add `source "$SCRIPT_DIR/lib/spec-validation.sh"` to library sourcing section (~line 141) of `generate-spec-from-issue.sh` (FR-001)
- [ ] T026 [US2] Write happy-path integration test: mock `call_llm` to return valid output on first attempt → verify no retry fires, retry budget remains untouched, and no exhaustion error path is
  reached before final spec is written to disk in `test_spec_validation.sh` (FR-008, FR-009, FR-010, FR-011, FR-012)
- [ ] T027 [US2] Write integration test: inject one operational `call_llm` failure followed by validation failures to exhaustion → verify operational failure does not decrement retry budget,
  then exit code 1 and stderr contains all failure categories in `test_spec_validation.sh` (FR-010, FR-011)

## Phase 5: User Story 3 — Summary-Only and Bullet-Point Detection (P2)

- [ ] T028 [US3] Write failing test TC07 in `test_spec_validation.sh`: spec with >80% bullet lines returns BULLET_SUMMARY_DETECTED failure (FR-007)
- [ ] T029 [US3] Write failing test: user stories without Given/When/Then acceptance scenarios are not counted (TC11) in `test_spec_validation.sh` (FR-004)
- [ ] T030 [US3] Implement `_check_bullet_ratio <filepath>` in `lib/spec-validation.sh` — computes percentage of non-heading, non-blank lines that are bullet points; fails if > `MAX_BULLET_LINE_PCT`
  (FR-007)
- [ ] T031 [US3] Integrate `_check_bullet_ratio` into `validate_spec_quality` orchestrator in `lib/spec-validation.sh` (FR-007)
- [ ] T032 [US3] Add BULLET_SUMMARY_DETECTED category to `_build_structured_specify_feedback` output format in `lib/spec-validation.sh` (FR-009)

## Phase 6: User Story 4 — Shared Validation Helpers (P2)

- [ ] T033 [US4] Verify `lib/spec-validation.sh` is sourceable by Phase 2 (`lib/clarify-retry.sh`) without side effects — add sourcing guard test in `test_spec_validation.sh` (FR-013)
- [ ] T034 [US4] Confirm existing `test_clarify_retry.sh` passes without modification after `lib/spec-validation.sh` extraction (FR-014)
- [ ] T035 [US4] Confirm existing `test_content_preservation.sh` passes without modification (FR-014)
- [ ] T036 [US4] Add test verifying Phase 2 `validate_structural_integrity` remains independent and produces same results when `lib/spec-validation.sh` is sourced alongside it (FR-014)

## Phase 7: User Story 5 — Configurable Thresholds (P3)

- [ ] T037 [US5] Write test TC12 in `test_spec_validation.sh`: override `MIN_FUNCTIONAL_REQUIREMENTS=10`, validate spec with 7 FRs fails citing minimum of 10 (FR-003, NFR-004)
- [ ] T038 [US5] Write test in `test_spec_validation.sh`: override `MIN_USER_STORIES=5`, validate spec with 3 user stories fails (FR-004)
- [ ] T039 [US5] Verify all threshold constants are overridable by setting them before sourcing `lib/spec-validation.sh` (uses `${VAR:-default}` pattern) in `lib/spec-validation.sh` (FR-003, FR-004)

## Phase 8: Polish & Cross-Cutting

- [ ] T040 Write test TC10 in `test_spec_validation.sh`: user story heading variants (`### User Story 1`, `### User Story: Title`, `### USER STORY N`) all accepted
  via case-insensitive prefix matching (FR-004)
- [ ] T041 Add function header comments (parameters, return codes, stdout/stderr) to all new functions in `lib/spec-validation.sh` (NFR-005)
- [ ] T042 Verify NFR-001: `validate_spec_quality` completes in <1s on a 10KB spec file (FR-001)
- [ ] T043 Verify NFR-003: validation produces deterministic results — same input always yields same output (no timestamps or randomness in logic) (FR-001)
- [ ] T044 Run full existing test suite (`test_clarify_retry.sh`, `test_content_preservation.sh`, `test_critical_gate_remediation.sh`) to confirm zero regressions (FR-014)
- [ ] T045 Verify test file `test_spec_validation.sh` contains at least 10 distinct test cases covering all validation branches (FR-001, FR-012, NFR-006, SC-006)

## Task Dependencies

| Task | Depends On |
|------|-----------|
| T003 | T001 |
| T004 | T001 |
| T005–T010 | T002, T003 |
| T011–T016 | T003, T004 |
| T017–T018 | T016 |
| T019 | T016 |
| T020 | T016, T019, T025 |
| T021–T024 | T020 |
| T025 | T001 |
| T026–T027 | T021 |
| T028–T029 | T002, T003 |
| T030–T032 | T016, T028 |
| T033–T036 | T016, T025 |
| T037–T039 | T003, T016 |
| T040–T045 | T032, T027 |

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T002, T010, T016, T025, T042, T043, T045 |
| FR-002 | T005, T011 |
| FR-003 | T007, T012, T017, T018, T037, T039 |
| FR-004 | T008, T013, T018, T029, T038, T039, T040 |
| FR-005 | T009, T014 |
| FR-006 | T006, T015, T018 |
| FR-007 | T028, T030, T031 |
| FR-008 | T020, T021, T022 |
| FR-009 | T019, T021, T032 |
| FR-010 | T020, T024, T026 |
| FR-011 | T023, T026, T027 |
| FR-012 | T015, T016, T021, T026, T045 |
| FR-013 | T003, T004, T033 |
| FR-014 | T034, T035, T036, T044 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
