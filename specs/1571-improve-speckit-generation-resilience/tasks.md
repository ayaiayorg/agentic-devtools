# Tasks: Improve SpecKit Generation Resilience

## Phase Mapping: Plan → Tasks

Phases in this `tasks.md` are 1:1 aligned with the phases defined in `plan.md`.

## Phase 1: Setup & Scaffolding

- [ ] T001 Create feature branch `speckit/1571/phase-1-specify` from `main`
- [ ] T002 Create template file `.github/scripts/speckit-trigger/templates/example-valid-spec.md` with a truncated (~1500 char) reference spec that passes all validation checks (FR-010)
- [ ] T003 Create skeleton block file `.github/scripts/speckit-trigger/templates/specify-skeleton.md` containing all 4 mandatory section headings with `<!-- FILL: ... -->` markers (FR-001)

## Phase 2: Foundational — Blocking Prerequisites

- [ ] T004 Add env var `AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR` documentation to `generate-spec-from-issue.sh` header comment block (NFR-005)
- [ ] T005 Add env var loading and validation for `AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR` (default `0.6`, range 0.0–1.0) in `.github/scripts/speckit-trigger/lib/spec-validation.sh` (NFR-005, FR-004)
- [ ] T006 Implement `_compute_dynamic_thresholds()` function in `.github/scripts/speckit-trigger/lib/spec-validation.sh` — measures `ISSUE_BODY` length, reduces `MIN_SPEC_BYTES` when < 200 chars,
  leaves `MIN_FUNCTIONAL_REQUIREMENTS`/`MIN_USER_STORIES` unchanged (FR-004)
- [ ] T007 Extend `validate_spec_quality()` output format in `.github/scripts/speckit-trigger/lib/spec-validation.sh` to append `| REMEDIATION: <suggestion>` suffix to each failure line (FR-005)
- [ ] T008 Add metrics counter variables (`specify_first_attempt_pass`, `specify_total_retries`, `specify_fallback_used`, `specify_failure_reasons`) initialization in
  `run_specify_phase_with_validation_retries()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (FR-007)

## Phase 3: User Story 1 — Reliable First-Attempt Spec Generation (P1)

- [ ] T009 [US1] Write happy-path test cases in `.github/scripts/speckit-trigger/test_specify_retry.sh` verifying that a normal generated specify prompt includes the mandatory skeleton block and
  preserves all 4 required section headings before validation succeeds (FR-001)
- [ ] T010 [US1] Modify `run_specify_phase()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` to inject the mandatory skeleton block from `templates/specify-skeleton.md` into the
  specify prompt between instructions and template reference (FR-001)
- [ ] T011 [US1] Add explicit prose-to-bullet ratio instruction referencing `MAX_BULLET_LINE_PCT` in the skeleton injection block within `run_specify_phase()` (FR-008)
- [ ] T012 [US1] Update `run_specify_phase_with_feedback()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` to also include the skeleton on retries (FR-001)
- [ ] T013 [P] [US1] Write happy-path test in `.github/scripts/speckit-trigger/test_specify_retry.sh` verifying that a successful prompt includes the bullet percentage instruction so the generated
  spec follows the prose-heavy format on the first attempt (FR-008)
- [ ] T014 [P] [US1] Write happy-path test in `.github/scripts/speckit-trigger/test_spec_validation.sh` verifying `_report_specify_metrics()` emits valid metrics JSON for a successful
  first-attempt generation flow with zero retries and no fallback (FR-007)
- [ ] T015 [US1] Implement `_report_specify_metrics()` function in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` that emits JSON metrics to stderr and `GITHUB_OUTPUT` at end of
  `run_specify_phase_with_validation_retries()` (FR-007)

## Phase 4: User Story 2 — Adaptive Retry with Enriched Feedback (P1)

- [ ] T016 [US2] Write happy-path test cases in `.github/scripts/speckit-trigger/test_specify_retry.sh` verifying that, when validation detects a specific failure category, the retry flow returns
  enriched feedback with the matching remediation suggestion and example content for that category (FR-002)
- [ ] T017 [US2] Extend `_build_structured_specify_feedback()` in `.github/scripts/speckit-trigger/lib/spec-validation.sh` to include per-category remediation suggestions: `MISSING_SECTIONS` → exact
  headings + example, `BELOW_SIZE_THRESHOLD` → expand prose instruction, `INSUFFICIENT_REQUIREMENTS` → FR-### format example, `BULLET_SUMMARY_DETECTED` → prose conversion example (FR-002)
- [ ] T018 [US2] Implement `_get_specify_example_spec()` function in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` that reads and returns the truncated example from
  `templates/example-valid-spec.md` (FR-010)
- [ ] T019 [US2] Modify `run_specify_phase_with_feedback()` to inject the example spec when `specify_retry_count >= 2` using `_get_specify_example_spec()` (FR-010)
- [ ] T020 [P] [US2] Write test in `.github/scripts/speckit-trigger/test_specify_retry.sh` verifying example injection occurs only on retry ≥ 2 (FR-010)
- [ ] T021 [US2] Add post-clarify re-validation call in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` after `run_clarify_phase()` completes — call `validate_spec_quality()` on updated
  `spec.md`, log warning on failure without blocking (FR-009)
- [ ] T022 [P] [US2] Write integration test in `.github/scripts/speckit-trigger/test_specify_retry.sh` verifying re-validation runs after clarify phase (FR-009)

## Phase 5: User Story 3 — Deterministic Fallback on Retry Exhaustion (P2)

- [ ] T023 [US3] Write test cases in `.github/scripts/speckit-trigger/test_spec_validation.sh` for fallback skeleton content correctness: ≥5 FR entries, ≥3 user stories, banner presence, passes
  `validate_spec_quality()` (FR-003, FR-011)
- [ ] T024 [US3] Implement `_generate_fallback_skeleton()` function in `.github/scripts/speckit-trigger/lib/spec-validation.sh` — takes `ISSUE_TITLE`, `ISSUE_BODY`, `ISSUE_NUMBER`, `ISSUE_URL`;
  produces all 4 mandatory sections with issue-derived content; generates ≥5 FR-### entries from keywords; generates ≥3 user stories with Given/When/Then; adds SC-### entries; adds fallback banner and
  enrichment guidance (FR-003, FR-011)
- [ ] T025 [US3] Add self-validation in `_generate_fallback_skeleton()` — call `validate_spec_quality()` on generated skeleton and abort with error if it fails (FR-003)
- [ ] T026 [US3] Integrate fallback into `run_specify_phase_with_validation_retries()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — invoke `_generate_fallback_skeleton()` after
  retry exhaustion instead of returning 1 (FR-003)
- [ ] T027 [P] [US3] Write performance test verifying `_generate_fallback_skeleton()` completes in < 1 second with no network calls (NFR-004)
- [ ] T028 [US3] Update `_report_specify_metrics()` to set `fallback_activated=true` when fallback is triggered (FR-007)

## Phase 6: User Story 4 — Dynamic Threshold Adaptation (P2)

- [ ] T029 [US4] Write test cases in `.github/scripts/speckit-trigger/test_spec_validation.sh` for `_compute_dynamic_thresholds()`: input < 200 chars → reduced `MIN_SPEC_BYTES`; input > 2000 chars →
  no reduction; edge cases (empty body, exactly 200 chars) (FR-004)
- [ ] T030 [US4] Integrate `_compute_dynamic_thresholds()` call at start of `run_specify_phase_with_validation_retries()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` (FR-004)
- [ ] T031 [P] [US4] Write test verifying `AGDT_MIN_SPEC_BYTES_REDUCTION_FACTOR` env var validation rejects values outside 0.0–1.0 range and falls back to default (NFR-005)

## Phase 7: User Story 5 — Granular Actionable Error Feedback (P3)

- [ ] T032 [US5] Write test cases in `.github/scripts/speckit-trigger/test_spec_validation.sh` verifying remediation suffix format `| REMEDIATION: <text>` for each failure category (FR-005)
- [ ] T033 [US5] Add concrete remediation messages for each validation failure in `validate_spec_quality()` in `.github/scripts/speckit-trigger/lib/spec-validation.sh`: missing sections → exact
  heading + entry format, size → expand instruction, bullets → conversion suggestion, requirements → count + format (FR-005)
- [ ] T034 [US5] Update `_build_structured_specify_feedback()` to parse and include `REMEDIATION:` hints from the enriched failure output when building retry prompts (FR-005)
- [ ] T035 [P] [US5] Verify backward compatibility — existing parsers of `validate_spec_quality()` output ignore the new `| REMEDIATION:` suffix (NFR-006)

## Phase 8: User Story 6 — Sanitizer Precision Improvement (P3)

- [ ] T036 [US6] Write contract tests in `.github/scripts/speckit-trigger/test_spec_validation.sh` for BOM marker, leading whitespace, and acknowledgment-line cases (FR-006)
- [ ] T037 [US6] Add BOM marker detection (`\xEF\xBB\xBF`) to `strip_llm_preamble()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` — strip before evaluating first line (FR-006)
- [ ] T038 [US6] Add multi-line preamble detection to `strip_llm_preamble()` — if lines 1–3 are conversational but a subsequent line is a heading, strip only the preamble lines (FR-006)
- [ ] T039 [US6] Improve `_is_valid_md_start()` in `.github/scripts/speckit-trigger/generate-spec-from-issue.sh` to recognize indented headings (up to 3 spaces, per CommonMark) (FR-006)
- [ ] T040 [US6] Suppress the "default prepended" warning in `ensure_heading_start()` when content already starts with a valid heading after whitespace/BOM trimming (FR-006)
- [ ] T041 [P] [US6] Write test verifying that 10 valid specs with various heading formats (BOM, whitespace, no preamble) pass sanitizer without false-positive warnings (FR-006)

## Phase 9: Polish & Cross-Cutting

- [ ] T042 [US6] Run full test suite: `bash .github/scripts/speckit-trigger/test_spec_validation.sh && bash .github/scripts/speckit-trigger/test_specify_retry.sh`
- [ ] T043 [US6] Run `bash scripts/run-pr-checks.sh` to validate no regressions
- [ ] T044 [US6] Verify NFR-001 compliance: confirm retry exponential backoff (2s, 4s) is maintained in `run_specify_phase_with_validation_retries()`
- [ ] T045 [US6] Verify NFR-003 compliance: all new log output uses emoji prefixes and existing formatting conventions
- [ ] T046 [US6] Verify NFR-006 compliance: run existing `test_spec_validation.sh` to confirm backward compatibility with current validation contract
- [ ] T047 Update `generate-spec-from-issue.sh` header documentation to list new env vars and functions

## Dependencies

```text
T001 → T002, T003 (branch before files)
T005 → T006 (env var before function)
T006 → T029, T030 (function before integration/tests)
T007 → T032, T033 (format before specific messages)
T008 → T015 (counters before reporting)
T003 → T010 (skeleton file before injection)
T010 → T012 (specify before feedback variant)
T009 → T010 (test before implementation - TDD)
T016 → T017 (test before implementation - TDD)
T023 → T024 (test before implementation - TDD)
T024 → T025, T026 (function before integration)
T017 → T019 (feedback before example injection)
T002 → T018 (example file before loader)
T018 → T019 (loader before injection in retry)
T026 → T028 (fallback integration before metrics update)
T036 → T037, T038, T039, T040 (tests before implementation - TDD)
T042 → T043 (unit tests before full PR checks)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
