# Tasks: SpecKit Checklist Validation (`agdt-speckit-validate-checklists`)

## Phase 1: Setup & Scaffolding

- [ ] T001 Create module file `agentic_devtools/cli/speckit/validate_checklists.py` with module docstring and `from __future__ import annotations`
- [ ] T002 Create test directory `tests/unit/cli/speckit/validate_checklists/` with `__init__.py` files at each level

## Phase 2: Foundational — Data Types

- [ ] T003 Define `FileClassification` enum (`valid`, `deficient`, `prose_only`) in `agentic_devtools/cli/speckit/validate_checklists.py` — used by FR-006, FR-007, FR-008 classification rules
- [ ] T004 Define `Severity` enum (`NONE`, `LOW`, `MEDIUM`) in `agentic_devtools/cli/speckit/validate_checklists.py` — used by FR-009, FR-010 severity assignment
- [ ] T005 Define `FileResult` dataclass (path, checkbox_count, classification, severity, explanation, remediated, retries_used) in `agentic_devtools/cli/speckit/validate_checklists.py` — supports
  FR-013 per-file result fields
- [ ] T006 Define `AggregateResult` dataclass (files: list[FileResult], passed: bool, to_json()) in `agentic_devtools/cli/speckit/validate_checklists.py` — supports FR-014 aggregate pass/fail
- [ ] T007 Define `RemediationResult` dataclass (remediated, retries_used, file_result) in `agentic_devtools/cli/speckit/validate_checklists.py` — supports FR-017 remediation metadata

## Phase 3: User Story 1 — Detection (P1) [US1]

- [ ] T008 [US1] Write tests for `count_checkboxes()` covering basic `- [ ]`, `- [x]`, `- [X]`, `* [ ]`, `* [x]`, `* [X]` patterns (FR-004) in
  `tests/unit/cli/speckit/validate_checklists/test_count_checkboxes.py`
- [ ] T009 [P] [US1] Write tests for `count_checkboxes()` covering indented/nested checkbox items counted regardless of leading whitespace (FR-004) in
  `tests/unit/cli/speckit/validate_checklists/test_count_checkboxes.py`
- [ ] T010 [P] [US1] Write tests for `count_checkboxes()` covering backtick fenced code block exclusion per CommonMark outermost-boundary rules (FR-005) in
  `tests/unit/cli/speckit/validate_checklists/test_count_checkboxes.py`
- [ ] T011 [P] [US1] Write tests for `count_checkboxes()` covering tilde `~~~` fenced code block exclusion with fence length matching (FR-005) in
  `tests/unit/cli/speckit/validate_checklists/test_count_checkboxes.py`
- [ ] T012 [P] [US1] Write tests for `count_checkboxes()` covering nested fenced blocks (outermost boundary), mixed content, empty/whitespace-only content in
  `tests/unit/cli/speckit/validate_checklists/test_count_checkboxes.py`
- [ ] T013 [US1] Implement `count_checkboxes(content: str) -> int` state-machine parser in `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-004 (checkbox counting with all marker
  types) and FR-005 (fenced code block exclusion for both ``` and ~~~)
  - Depends on: T008–T012
- [ ] T014 [US1] Write tests for `classify_file()` covering prose_only/0 items (FR-006, FR-009), deficient/1-2 items (FR-007, FR-010), valid/≥min_items (FR-008), and custom min_items in
  `tests/unit/cli/speckit/validate_checklists/test_classify_file.py`
- [ ] T015 [US1] Implement `classify_file(checkbox_count: int, min_items: int) -> tuple[FileClassification, Severity]` in `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-006
  (prose-only at 0), FR-007 (deficient below min), FR-008 (valid at/above min), FR-009 (MEDIUM severity for prose-only), FR-010 (LOW severity for deficient)
  - Depends on: T014
- [ ] T016 [US1] Write tests for `validate_file()` covering valid/deficient/prose-only files, file-not-found, and encoding edge cases in
  `tests/unit/cli/speckit/validate_checklists/test_validate_file.py`
- [ ] T017 [US1] Implement `validate_file(path: str, min_items: int) -> FileResult` in `agentic_devtools/cli/speckit/validate_checklists.py` — reads file, calls count_checkboxes + classify_file,
  builds FileResult with explanation field (FR-013)
  - Depends on: T013, T015, T016

## Phase 4: User Story 2 — Analysis Reporting (P1) [US2]

- [ ] T018 [US2] Write tests for `_print_human_output()` verifying per-file summary lines include path, checkbox_count, classification, severity, explanation, and aggregate line (FR-012, FR-013) in
  `tests/unit/cli/speckit/validate_checklists/test__print_human_output.py`
- [ ] T019 [US2] Implement `_print_human_output(result: AggregateResult) -> None` in `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-012 (distinguishes prose-only MEDIUM from
  deficient LOW) and FR-013 (per-file explanation)
  - Depends on: T018
- [ ] T020 [P] [US2] Write tests for `AggregateResult.to_json()` verifying JSON output includes per-file explanation, remediated flag, retries_used (FR-013) in
  `tests/unit/cli/speckit/validate_checklists/test_aggregateresult.py`
- [ ] T021 [US2] Implement JSON output mode in `AggregateResult.to_json()` in `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-013 structured output with all required fields
  - Depends on: T020

## Phase 5: User Story 3 — Pipeline Blocking (P2) [US3]

- [ ] T022 [US3] Write tests for `validate_checklists()` orchestrator covering single-file pass/fail, multi-file mixed results (FR-014), empty file list warning (FR-020), and aggregate pass/fail
  (FR-011) in `tests/unit/cli/speckit/validate_checklists/test_validate_checklists.py`
- [ ] T023 [US3] Implement `validate_checklists(paths: list[str], min_items: int, *, retry: bool = False, max_retries: int = 2) -> AggregateResult` in
  `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-011 (pipeline fails when any file below min), FR-014 (multi-file aggregate), FR-020 (empty list warning with pass)
  - Depends on: T017, T022
- [ ] T024 [US3] Write tests for `_resolve_paths()` covering glob expansion, dedup, explicit missing file exits with code 1, glob zero-match warning (FR-020), multi-directory collision abort (FR-001),
  3-digit Source Issue marker guard (FR-001), non-default SPEC_BASE_PATH (FR-001) in `tests/unit/cli/speckit/validate_checklists/test__resolve_paths.py`
- [ ] T025 [US3] Implement `_resolve_paths(patterns: list[str], issue_number: int | None = None) -> list[str]` in `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-001 (pipeline
  discovery via glob with collision detection and 3-digit guard), FR-002 (validates all *.md in resolved directory), FR-003 (standalone accepts explicit paths/globs)
  - Depends on: T024
- [ ] T026 [US3] Write tests for `validate_checklists_command()` covering basic invocation, `--min-items` override (FR-018), `--json` output, non-zero exit on failure (FR-015), exit 0 on pass, glob
  zero-match warning, pipeline-mode default path resolution (FR-001, FR-002) in `tests/unit/cli/speckit/validate_checklists/test_validate_checklists_command.py`
- [ ] T027 [US3] Implement `validate_checklists_command(argv: list[str] | None = None) -> None` argparse CLI in `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-015 (non-zero exit
  on failure), FR-018 (`--min-items` configurable threshold), FR-019 (exposed as `agdt-speckit-validate-checklists`)
  - Depends on: T023, T025, T026

## Phase 6: User Story 4 — LLM Re-prompting (P3) [US4]

- [ ] T028 [US4] Write tests for `remediate_file()` covering success on 1st retry, success on 2nd retry, exhausted retries, missing sidecar prompt fallback (FR-016, FR-017) in
  `tests/unit/cli/speckit/validate_checklists/test_remediate_file.py`
- [ ] T029 [US4] Implement `remediate_file(path: str, min_items: int, max_retries: int = 2) -> RemediationResult` in `agentic_devtools/cli/speckit/validate_checklists.py` — satisfies FR-016 (disabled
  by default, enabled via --retry) and FR-017 (max 2 retries per invalid file, staged remediation pattern)
  - Depends on: T017, T028
- [ ] T030 [US4] Integrate retry into `validate_checklists()` orchestrator: when `retry=True` and file is invalid, call `remediate_file()` and update FileResult with remediated/retries_used metadata
  (FR-017) in `agentic_devtools/cli/speckit/validate_checklists.py`
  - Depends on: T023, T029
- [ ] T031 [US4] Add sidecar prompt persistence (`.generation-prompt-{stem}.md`) to SpecKit pipeline checklist generation step and add the broader gitignore rule
  `**/checklists/.generation-prompt-*.md` (note: the narrower `specs/*/checklists/.generation-prompt-*.md` pattern already exists in `.gitignore`)
  - Depends on: T029

## Phase 7: User Story 5 — Standalone CLI (P3) [US5]

- [ ] T032 [US5] Export `speckit_validate_checklists` alias in `agentic_devtools/cli/speckit/__init__.py` — wiring for FR-019 entry point
- [ ] T033 [US5] Register `"agdt-speckit-validate-checklists"` in `COMMAND_MAP` in `agentic_devtools/cli/runner.py` — wiring for FR-019 entry point
- [ ] T034 [US5] Register `agdt-speckit-validate-checklists = "agentic_devtools.cli.runner:run_as_script"` entry point in `pyproject.toml` — completes FR-019 (standalone CLI entry point with
  `agdt-speckit-*` naming)
- [ ] T035 [US5] Run `pip install -e .` and smoke test `agdt-speckit-validate-checklists --help` to verify CLI is callable (FR-019)
  - Depends on: T027, T032, T033, T034

## Phase 8: Pipeline Integration [US3]

- [ ] T036 [US3] Add `agdt-speckit-validate-checklists` as a pipeline stage in SpecKit orchestration (after checklist generation, before completion) — satisfies FR-001 (pipeline discovery), FR-002
  (validates all *.md in directory), FR-011 (pipeline fails on deficient files)
  - Depends on: T035
- [ ] T037 [US3] Write integration test verifying end-to-end pipeline invocation propagates pass/fail status correctly with exit codes 0 (pass / zero-match warning) and 1
  (blocking failure / collision abort) in `tests/unit/cli/speckit/validate_checklists/test_validate_checklists_command.py`
  - Depends on: T036

## Phase 9: Polish & Cross-Cutting

- [ ] T038 Run `bash scripts/run-pr-checks.sh` — verify all CI-blocking checks pass (test structure validation, pytest, ruff, markdownlint, mypy)
  - Depends on: T037
- [ ] T039 Update `agentic_devtools/copilot-instructions.md` to document the new `agdt-speckit-validate-checklists` command in the SpecKit CLI commands section
  - Depends on: T035
- [ ] T040 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 test structure compliance for all new test files under `tests/unit/cli/speckit/validate_checklists/`
  - Depends on: T038

## Dependency Summary

| Task | Depends On |
|------|-----------|
| T008–T012 | T001, T002, T003–T007 |
| T013 | T008–T012 |
| T014 | T003, T004 |
| T015 | T014 |
| T016 | T005, T013, T015 |
| T017 | T013, T015, T016 |
| T018–T021 | T005, T006 |
| T022–T023 | T017 |
| T024–T025 | T001 |
| T026–T027 | T023, T025 |
| T028–T030 | T017, T023 |
| T031 | T029 |
| T032–T034 | T027 |
| T035 | T027, T032–T034 |
| T036–T037 | T035 |
| T038 | T037 |
| T039 | T035 |
| T040 | T038 |

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T024, T025, T026, T036 |
| FR-002 | T025, T026, T036 |
| FR-003 | T025 |
| FR-004 | T008, T009, T013 |
| FR-005 | T010, T011, T012, T013 |
| FR-006 | T014, T015 |
| FR-007 | T014, T015 |
| FR-008 | T014, T015 |
| FR-009 | T014, T015 |
| FR-010 | T014, T015 |
| FR-011 | T022, T023, T036 |
| FR-012 | T018, T019 |
| FR-013 | T005, T017, T018, T019, T020, T021 |
| FR-014 | T006, T022, T023 |
| FR-015 | T026, T027 |
| FR-016 | T028, T029 |
| FR-017 | T007, T028, T029, T030 |
| FR-018 | T026, T027 |
| FR-019 | T032, T033, T034, T035 |
| FR-020 | T022, T023, T024, T025 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
