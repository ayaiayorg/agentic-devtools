# Tasks: SpecKit Clarification Step — Content-Preserving Augmentation

**Issue**: [#1195](https://github.com/ayaiayorg/agentic-devtools/issues/1195)
**Branch**: `speckit/1195/phase-4-tasks`

---

## Phase 1: Setup

- [ ] T001 Create shell integration test file `.github/scripts/speckit-trigger/test_content_preservation.sh` with test harness boilerplate (shebang, `set -euo pipefail`, temp dir setup/teardown,
  pass/fail counters, `assert_eq`/`assert_contains`/`assert_file_exists` helpers) — follow the pattern in `.github/scripts/speckit-trigger/test_markdownlint_validation.sh`
- [ ] T002 Create test fixture directory `.github/scripts/speckit-trigger/fixtures/content-preservation/` with a sample `spec.md` containing all mandatory sections
  (`## Problem Statement`, `## User Scenarios & Testing`, `## Requirements`, `## Success Criteria`), 15 requirement entries (mix of `FR-###` and `NFR-###`), `## Edge Cases`, and
  `## Clarifications` with an existing session
- [ ] T003 [P] Create test fixture `.github/scripts/speckit-trigger/fixtures/content-preservation/checklists/requirements.md` with 10 Markdown task list items (`- [ ] ...`, `- [x] ...`, and at least
  one `- [X] ...`) across multiple sections

---

## Phase 2: Foundational — Shell Utility Functions

> All functions are added to `.github/scripts/speckit-trigger/generate-spec-from-issue.sh`.
> Tests in `.github/scripts/speckit-trigger/test_content_preservation.sh`.

### Backup & Restore

- [ ] T004 Write shell tests for `create_backup`: creates `.bak` file with correct content; uses `.bak.1`, `.bak.2` suffixes on collision; returns non-zero on write failure (simulate with read-only
  directory); returns backup path on stdout — in `test_content_preservation.sh`
- [ ] T005 Implement `create_backup <filepath>` function in `generate-spec-from-issue.sh` — creates `<filepath>.bak` with `.bak.N` collision avoidance; aborts with OS-level error detail on write
  failure (FR-002); returns backup path on stdout
- [ ] T006 [P] Write shell tests for `restore_from_backup`: restores original from backup; fails with error when backup file is missing — in `test_content_preservation.sh`
- [ ] T007 [P] Implement `restore_from_backup <filepath> <backup_path>` function in `generate-spec-from-issue.sh` — copies backup over the original file (FR-007)

### Counting Functions

- [ ] T008 [P] Write shell tests for `count_requirement_entries`: counts `FR-###` and `NFR-###` entries correctly; returns 0 for file with no requirements; ignores non-requirement bullets, section
  headings, and checklist items — in `test_content_preservation.sh`
- [ ] T009 [P] Implement `count_requirement_entries <filepath>` function in `generate-spec-from-issue.sh` — counts lines matching `^\s*-\s+\*\*(FR|NFR)-[0-9]+\*\*:` pattern using `grep -cE`; returns
  count on stdout
- [ ] T010 [P] Write shell tests for `count_checklist_items`: counts `- [ ]`, `- [x]`, and `- [X]` items; ignores plain bullets `- ...`; returns 0 for empty file — in `test_content_preservation.sh`
- [ ] T011 [P] Implement `count_checklist_items <filepath>` function in `generate-spec-from-issue.sh` — counts lines matching `^- \[([xX]| )\]` pattern; returns count on stdout

### Section Heading Extraction

- [ ] T012 [P] Write shell tests for `extract_section_headings`: extracts `## ...` headings; strips trailing `*(mandatory)*` annotations; trims whitespace; returns one heading per line — in
  `test_content_preservation.sh`
- [ ] T013 [P] Implement `extract_section_headings <filepath>` function in `generate-spec-from-issue.sh` — uses `grep/sed` to extract and normalize `## ...` headings; returns one heading per line on
  stdout

### Structural Validation

- [ ] T014 Write shell tests for `validate_structural_integrity`: passes when all sections retained and counts meet the retention thresholds; fails when mandatory section missing; fails when
  any original section heading missing; fails when requirement count drops below `ceil(0.95 * N)` threshold; passes when original has 0 requirements (skip check); strips `*(mandatory)*`
  annotations before matching; tests both `--type spec` and `--type checklist` modes — in `test_content_preservation.sh`
  - Depends on: T009, T011, T013
- [ ] T015 Implement `validate_structural_integrity <original_file> <candidate_file> [--type spec|checklist]` function in `generate-spec-from-issue.sh` — compares mandatory sections
  (for `--type spec`), all original section headings, requirement retention ≥95% (`--type spec`) or checklist item retention with `retained_count >= original_count` (`--type checklist`, i.e.
  additional checklist items are allowed as long as none of the originals are lost); skips retention check when original count is 0; prints specific failure reasons to stderr (NFR-002); returns
  0 on pass, 1 on fail
  - Depends on: T009, T011, T013

### Safe Write Orchestrator

- [ ] T016 Write shell tests for `safe_write_with_validation`: successful write replaces original with backup retained; failed validation leaves original unchanged with backup intact and
  `<original_file>.tmp` cleaned up; backup write failure aborts without touching original — in `test_content_preservation.sh`
  - Depends on: T005, T015
- [ ] T017 Implement `safe_write_with_validation <original_file> <candidate_content> [--type spec|checklist]` function in `generate-spec-from-issue.sh` — orchestrates: create backup → write
  candidate to `<original_file>.tmp` → validate → on pass: `mv <original_file>.tmp <original_file>` (atomic POSIX rename) → on fail: remove `<original_file>.tmp`, leave original unchanged,
  report errors; returns 0 on success, 1 on validation failure (FR-006, FR-007)
  - Depends on: T005, T007, T015

---

## Phase 3: User Story 1 — Clarification Preserves Complete Specification (P1)

### Pre-flight Checks

- [ ] T018 [US1] Write shell integration test: `run_clarify_phase()` fails with clear error when `spec.md` does not exist (FR-009) — in `test_content_preservation.sh`
- [ ] T019 [US1] [P] Write shell integration test: `run_clarify_phase()` fails with clear error when `spec.md` is empty (0 bytes) (FR-009) — in `test_content_preservation.sh`
- [ ] T020 [US1] Add pre-flight existence and non-empty checks to the top of `run_clarify_phase()` in `generate-spec-from-issue.sh` (FR-009)
  - Depends on: T018, T019

### File Size Warning

- [ ] T021 [US1] Write shell integration test: when `spec.md` is ≥50,000 bytes, a warning is emitted to stderr but processing continues normally (FR-012) — in `test_content_preservation.sh`
- [ ] T022 [US1] Add file size check to `run_clarify_phase()` in `generate-spec-from-issue.sh`: emit warning to stderr when `spec.md` ≥50KB; do not block execution (FR-012)
  - Depends on: T021

### LLM Prompt Augmentation

- [ ] T023 [US1] Augment the LLM clarify prompt in `run_clarify_phase()` with explicit `CRITICAL PRESERVATION RULES` block: output COMPLETE spec with ALL sections intact; do NOT summarize or truncate;
  preserve every `FR-###`/`NFR-###` entry; replace `[NEEDS CLARIFICATION]` markers in-place (FR-001, FR-003, FR-004, FR-011) — in `generate-spec-from-issue.sh`
  - Depends on: T020
- [ ] T024 [US1] Inject the original section heading list and requirement entry count into the LLM prompt as a cross-reference checklist for self-verification — in `generate-spec-from-issue.sh`
  - Depends on: T009, T013, T023

### Integration — Wire `safe_write_with_validation` into `run_clarify_phase()`

- [ ] T025 [US1] Replace the destructive `printf '%s\n' "$result" > "$SPEC_DIR/spec.md"` write (line 1319) with a call to `safe_write_with_validation "$SPEC_DIR/spec.md" "$result" --type spec` in
  `run_clarify_phase()` — in `generate-spec-from-issue.sh`
  - Depends on: T017, T020, T022, T023, T024
- [ ] T026 [US1] Update `append_model_footer` call to run only after successful `safe_write_with_validation` return — in `generate-spec-from-issue.sh`
  - Depends on: T025

### End-to-End Clarify Phase Tests

- [ ] T027 [US1] Write shell integration test: end-to-end `run_clarify_phase()` preserves all section headings and ≥95% of requirement entries from a fixture spec — in `test_content_preservation.sh`
  - Depends on: T025
- [ ] T028 [US1] Write shell integration test: `[NEEDS CLARIFICATION]` markers are replaced in-place within appropriate spec sections (FR-011) — in `test_content_preservation.sh`
  - Depends on: T023

---

## Phase 4: User Story 2 — Pre-Write Backup Prevents Irrecoverable Loss (P1)

- [ ] T029 [US2] Write shell integration test: backup file is created at `spec.md.bak` before any modification occurs during `run_clarify_phase()` — in `test_content_preservation.sh`
  - Depends on: T005, T017
- [ ] T030 [US2] Write shell integration test: when `spec.md.bak` already exists from a previous run, the new backup uses `spec.md.bak.1` (and `spec.md.bak.2` on subsequent collision) — in
  `test_content_preservation.sh`
  - Depends on: T005
- [ ] T031 [US2] Write shell integration test: backup file contains byte-identical content to the original `spec.md` — in `test_content_preservation.sh`
  - Depends on: T005
- [ ] T032 [US2] Write shell integration test: when backup write fails (read-only directory), `run_clarify_phase()` aborts with OS-level error and `spec.md` remains unchanged — in
  `test_content_preservation.sh`
  - Depends on: T005
- [ ] T033 [US2] Write shell integration test: backup file is retained (not deleted) after successful clarification write (FR-010) — in `test_content_preservation.sh`
  - Depends on: T017

---

## Phase 5: User Story 3 — Pre-Commit Structural Validation (P1)

- [ ] T034 [US3] Write shell integration test: truncated LLM response missing `## Requirements` section is rejected; original `spec.md` remains unchanged; backup remains available; clear error message
  identifies the missing section — in `test_content_preservation.sh`
  - Depends on: T015, T017
- [ ] T035 [US3] Write shell integration test: LLM response missing any of the 4 mandatory sections (`## Problem Statement`, `## User Scenarios & Testing`, `## Requirements`, `## Success Criteria`)
  triggers validation failure — in `test_content_preservation.sh`
  - Depends on: T015
- [ ] T036 [US3] Write shell integration test: LLM response retaining fewer than `ceil(0.95 * N)` requirement entries (e.g., 14 of 15) fails validation with count discrepancy reported — in
  `test_content_preservation.sh`
  - Depends on: T015
- [ ] T037 [US3] Write shell integration test: LLM response with 0 original requirements skips retention check and passes validation — in `test_content_preservation.sh`
  - Depends on: T015
- [ ] T038 [US3] Write shell integration test: valid augmented LLM output passes validation, atomically replaces `spec.md`, and `spec.md.tmp` is cleaned up — in `test_content_preservation.sh`
  - Depends on: T017
- [ ] T039 [US3] Write shell integration test: when failure occurs after replacement has begun (simulated post-rename corruption), backup is restored and restoration action is reported (FR-007) — in
  `test_content_preservation.sh`
  - Depends on: T007, T017

---

## Phase 6: User Story 4 — Clarification Audit Trail (P2)

- [ ] T040 [US4] Write shell integration test: `## Clarifications` section is present in `spec.md` after clarify phase completes — in `test_content_preservation.sh`
  - Depends on: T025
- [ ] T041 [US4] Write shell integration test: existing `## Clarifications` section with prior session entries is preserved, and new session subheading is appended — in `test_content_preservation.sh`
  - Depends on: T025
- [ ] T042 [US4] Add post-validation check in `run_clarify_phase()` to verify `## Clarifications` section exists in the final output — in `generate-spec-from-issue.sh`
  - Depends on: T025
- [ ] T043 [US4] Implement fallback logic in `run_clarify_phase()`: if `## Clarifications` is missing after successful write, append a minimal session entry with `### Session YYYY-MM-DD` subheading
  (FR-005) — in `generate-spec-from-issue.sh`
  - Depends on: T042
- [ ] T044 [US4] Add post-write warning to `run_clarify_phase()` that counts any remaining `[NEEDS CLARIFICATION]` markers and logs to stderr — in `generate-spec-from-issue.sh`
  - Depends on: T025

---

## Phase 7: User Story 5 — Checklist Preservation (P2)

### Pre-flight & Backup

- [ ] T045 [US5] Write shell integration test: `run_checklist_phase()` creates a backup of `checklists/requirements.md` before modification when the file already exists — in
  `test_content_preservation.sh`
  - Depends on: T005, T017
- [ ] T046 [US5] Write shell integration test: when `checklists/requirements.md` does not exist (first run), `run_checklist_phase()` creates it without validation (no baseline to compare) — in
  `test_content_preservation.sh`

### Validation

- [ ] T047 [US5] Write shell integration test: checklist validation requires retention of all original Markdown task list items
  (`retained_count >= original_count` for `- [ ]`, `- [x]`, and `- [X]` items); output may add new items, but truncated output is rejected — in
  `test_content_preservation.sh`
  - Depends on: T011, T015
- [ ] T048 [US5] Write shell integration test: existing checklist with 10 items is preserved intact after `run_checklist_phase()` completes — in `test_content_preservation.sh`
  - Depends on: T017

### Implementation

- [ ] T049 [US5] Add conditional pre-flight check to `run_checklist_phase()`: when `checklists/requirements.md` exists, proceed with backup/validation; when missing, skip backup/validation (initial
  creation) — in `generate-spec-from-issue.sh`
  - Depends on: T045, T046
- [ ] T050 [US5] Augment the LLM checklist prompt in `run_checklist_phase()` with preservation instructions for checklist items — in `generate-spec-from-issue.sh`
  - Depends on: T049
- [ ] T051 [US5] Replace the destructive `printf '%s\n' "$result" > "$SPEC_DIR/checklists/requirements.md"` write (line 1395) with conditional `safe_write_with_validation --type checklist` (when file
  exists) or direct write (when creating new) in `run_checklist_phase()` — in `generate-spec-from-issue.sh`
  - Depends on: T017, T049, T050

---

## Phase 8: User Story 6 — Parity Between Interactive and CI Modes (P3)

- [ ] T052 [US6] Document the shared validation contract (mandatory sections, requirement retention threshold, checklist retention policy) as a code comment block in `generate-spec-from-issue.sh`
  above the validation functions, referencing the interactive agent in `.github/agents/speckit.clarify.agent.md` (NFR-004)
  - Depends on: T015
- [ ] T053 [US6] Write shell integration test: CI mode produces output with identical section headings and comparable requirement counts (±1 tolerance) to a reference interactive-mode output fixture —
  in `test_content_preservation.sh`
  - Depends on: T025, T051
- [ ] T054 [US6] Add a shared constants block at the top of the validation functions defining `MANDATORY_SECTIONS`, `REQUIREMENT_RETENTION_THRESHOLD=95`, and `CHECKLIST_RETENTION_THRESHOLD=100` for
  reuse by both modes — in `generate-spec-from-issue.sh`
  - Depends on: T015

---

## Final Phase: Polish & Cross-Cutting

### CI Integration

- [ ] T055 Add a step in `.github/workflows/speckit-phase-progression.yml` to execute `test_content_preservation.sh` as part of the CI pipeline — follow the pattern of existing test steps
  - Depends on: T001, T027, T048
- [ ] T056 [P] Add a step in `.github/workflows/speckit-issue-trigger.yml` to execute `test_content_preservation.sh` in the initial pipeline trigger workflow
  - Depends on: T001

### Compatibility Verification

- [ ] T057 Verify `check-idempotency.sh` phase 2 detection (line 131: `grep -q '## Clarifications'`) is compatible with the always-present `## Clarifications` section — in
  `.github/scripts/speckit-trigger/check-idempotency.sh`
  - Depends on: T043
- [ ] T058 [P] Verify `append_model_footer` and `strip_model_footer` in `generate-spec-from-issue.sh` work correctly with the new `safe_write_with_validation` flow (footer appended after atomic
  rename)
  - Depends on: T026

### Python Unit Tests

- [ ] T059 [P] Write Python unit test verifying the `CRITICAL PRESERVATION RULES` text is present in the clarify prompt template — in `tests/unit/cli/speckit/commands/test_speckit_clarify.py` (extend
  existing test)
  - Depends on: T023
- [ ] T060 [P] Write Python unit test verifying the section heading cross-reference checklist is injected into the clarify prompt — if prompt augmentation is accessible via Python API
  - Depends on: T024

### Validation & Cleanup

- [ ] T061 Run full test suite (`agdt-test && agdt-task-wait`) and fix any regressions introduced by changes
  - Depends on: T026, T043, T051, T054
- [ ] T062 Run `bash .github/scripts/speckit-trigger/test_content_preservation.sh` to verify all shell integration tests pass
  - Depends on: T027, T048, T053
- [ ] T063 Run `python scripts/validate_test_structure.py` to verify 1:1:1 test structure compliance for any new Python test files
  - Depends on: T059, T060
- [ ] T064 Run `bash scripts/run-pr-checks.sh` to verify all CI-blocking checks pass before push
  - Depends on: T061, T062, T063

---

## Dependencies & Execution Order

### Phase Order

- **Phase 1: Setup** must complete first to establish the shell test harness and fixtures used by later shell-script and validation tasks.
- **Phase 2: Foundational — Shell Utility Functions** provides the shared preservation and write-safety primitives that later implementation and verification tasks build on.
- **Later implementation/integration phases** depend on those foundational utilities before updating prompt augmentation, clarification handling, spec writing, and idempotency behavior.
- **Validation & Cleanup** runs last after all implementation and test-authoring work is complete.

### Key Dependency Summary

- `T023` → `T059`: clarify prompt template changes must land before the Python unit test that verifies the `CRITICAL PRESERVATION RULES` text.
- `T024` → `T060`: clarify prompt augmentation/injection work must land before testing the heading cross-reference checklist behavior.
- `T026` → `T058`, `T061`: the safe write flow is a prerequisite for both footer compatibility verification and the final full test suite run.
- `T043` → `T057`, `T061`: clarification-section/idempotency behavior must be updated before compatibility verification and final regression validation.
- `T027`, `T048`, `T053` → `T062`: shell integration validation should only run once fixture, preservation, and end-to-end shell behavior changes are complete.
- `T059`, `T060` → `T063`: Python test structure validation depends on any new Python tests being present.
- `T061`, `T062`, `T063` → `T064`: PR checks are the final gate and should run only after all targeted validation steps pass.

### Parallelization Notes

- Tasks marked **[P]** can run in parallel once their listed prerequisites are satisfied.
- In particular, independent fixture creation, some shell verifications, and the Python unit tests (`T059`, `T060`) can be parallelized after their upstream implementation tasks complete.
- Keep `T061`–`T064` sequential at the end, since they serve as consolidated verification gates.

---
*Generated by Copilot SDK (claude-opus-4.6)*
