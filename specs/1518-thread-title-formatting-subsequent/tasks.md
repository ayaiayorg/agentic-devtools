# Tasks: Thread Title Formatting for Subsequent Review Comments

**Feature Branch**: `speckit/1518/phase-4-tasks`
**Source Issue**: [#1518](https://github.com/ayaiayorg/agentic-devtools/issues/1518)

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase 4: Tests | Adds test directory scaffolding required by test implementation tasks |
| Phase 2: Foundational — Core Rendering Changes | Phase 1: Core Rendering Changes | Introduces rendering and header utility prerequisites used by all story phases |
| Phase 3: User Story 1 — Compact Follow-Up Headers | Phase 1: Core Rendering Changes; Phase 2: Caller Updates; Phase 4: Tests | Delivers compact reply-header behavior for US1 |
| Phase 4: User Story 2 — Format Validation & Repair | Phase 3: Validation & Repair Logic; Phase 4: Tests | Implements demoted-summary validation/repair flow and test coverage for US2 |
| Phase 5: User Story 3 — No Regressions in Activity Logging | Phase 4: Tests | Adds activity-log regression protections for US3 |
| Phase 6: Polish & Cross-Cutting | Phase 5: Integration & Regression Verification | Final end-to-end verification and quality gates |

---

## Phase 1: Setup

- [ ] T001 Create test directory structure with `__init__.py` files for new test modules under `tests/unit/cli/azure_devops/review_templates/` (FR-010)

---

## Phase 2: Foundational — Core Rendering Changes

- [ ] T002 Add `is_subsequent: bool = False` parameter to `render_file_summary()` in `agentic_devtools/cli/azure_devops/review_templates.py` (FR-003)
- [ ] T003 Add `is_subsequent: bool = False` parameter to `render_overall_summary()` in `agentic_devtools/cli/azure_devops/review_templates.py` (FR-003)
- [ ] T004 Implement header selection logic in `render_file_summary()`: when `is_subsequent=True`, emit `### Commit: [<short_hash>](<commit_url>)` instead of `## File Review Summary: {fileName}`, with
  FR-008 fallbacks (FR-001, FR-002, FR-004)
- [ ] T005 Implement header selection logic in `render_overall_summary()`: when `is_subsequent=True`, emit `### Commit: [<short_hash>](<commit_url>)` instead of `## Overall PR Review Summary`, with
  FR-008 fallbacks (FR-001, FR-002, FR-004)
- [ ] T006 Add `rewrite_header_for_subsequent(content: str, commit_hash: str | None, commit_url: str | None) -> str` utility to
  `agentic_devtools/cli/azure_devops/review_templates.py` implementing FR-008 fallback chain
- [ ] T007 Add `validate_comment_header(content: str, is_subsequent: bool) -> bool` to `agentic_devtools/cli/azure_devops/review_templates.py` (FR-005, FR-006)
- [ ] T008 Add `repair_subsequent_header(content: str, review_state: ReviewState) -> str` to `agentic_devtools/cli/azure_devops/review_templates.py` (FR-007, FR-008)

---

## Phase 3: User Story 1 — Compact Follow-Up Headers (P1)

- [ ] T009 [P] [US1] Write happy-path tests for `render_file_summary(is_subsequent=True)` with full commit hash+URL (primary success scenario), plus hash-only and missing-hash fallback variants in
  `tests/unit/cli/azure_devops/review_templates/test_render_file_summary.py` (FR-003, FR-010)
- [ ] T010 [P] [US1] Write happy-path tests for `render_file_summary(is_subsequent=False)` confirming existing `## File Review Summary:` title is unchanged
  (primary backward-compat success scenario) in
  `tests/unit/cli/azure_devops/review_templates/test_render_file_summary.py` (FR-001, FR-010)
- [ ] T011 [P] [US1] Write happy-path tests for `render_overall_summary(is_subsequent=True)` with full commit hash+URL (primary success scenario) and all fallback variants in
  `tests/unit/cli/azure_devops/review_templates/test_render_overall_summary.py` (FR-010)
- [ ] T012 [P] [US1] Write tests for `render_overall_summary(is_subsequent=False)` confirming existing `## Overall PR Review Summary` title is unchanged in
  `tests/unit/cli/azure_devops/review_templates/test_render_overall_summary.py` (FR-001, FR-010)
- [ ] T013 [US1] Write tests for `rewrite_header_for_subsequent()` in `tests/unit/cli/azure_devops/review_templates/test_rewrite_header_for_subsequent.py` covering full-link, hash-only, and unknown
  fallbacks (FR-002, FR-010)
- [ ] T014 [US1] Update `_demote_main_comment()` in `agentic_devtools/cli/azure_devops/review_scaffold.py` to call `rewrite_header_for_subsequent()` on the old content before posting it as a reply
  (FR-002, FR-004)
- [ ] T015 [US1] Verify that non-header body content is preserved unchanged when `is_subsequent=True` in both render functions (FR-004) — add assertion in existing test files
- [ ] T016 [US1] Verify NFR-001 determinism: same inputs to render functions always produce same output — add parametrized test in
  `tests/unit/cli/azure_devops/review_templates/test_render_file_summary.py` (FR-010)

---

## Phase 4: User Story 2 — Format Validation & Repair (P2)

- [ ] T017 [P] [US2] Write tests for `validate_comment_header()` in `tests/unit/cli/azure_devops/review_templates/test_validate_comment_header.py` — top-level valid, subsequent with `## <title>`
  invalid, subsequent with `### Commit:` valid (FR-005, FR-006, FR-010)
- [ ] T018 [P] [US2] Write tests for `repair_subsequent_header()` in `tests/unit/cli/azure_devops/review_templates/test_repair_subsequent_header.py` — full repair, hash-only fallback, unknown fallback
  (FR-007, FR-008, FR-010)
- [ ] T019 [US2] Add eligibility rules in `agentic_devtools/cli/azure_devops/finalization/classification.py` to identify demoted-summary replies in file-summary/overall-summary threads
- [ ] T020 [US2] Integrate `validate_comment_header()` and `repair_subsequent_header()` into `agentic_devtools/cli/azure_devops/finalization/convergence.py` for eligible demoted-summary reply comments
  (FR-007)
- [ ] T021 [US2] Ensure `_compute_file_summary_content()` and `_compute_overall_summary_content()` in convergence remain `is_subsequent=False` for top-level comment expectations (FR-001)
- [ ] T022 [US2] Write integration tests verifying repair sources values from `ReviewState` (not comment content) in
  `tests/unit/cli/azure_devops/review_templates/test_repair_subsequent_header.py` (FR-007, FR-010)

---

## Phase 5: User Story 3 — No Regressions in Activity Logging (P3)

- [ ] T023 [US3] Write regression test verifying `_format_activity_log_entry()` output is byte-for-byte unchanged in `tests/unit/cli/azure_devops/review_scaffold/test_format_activity_log_entry.py`
  (FR-009, FR-010)
- [ ] T024 [US3] Write test confirming `_format_activity_log_entry()` uses `### Review Session —` header (not `### Commit:`) in
  `tests/unit/cli/azure_devops/review_scaffold/test_format_activity_log_entry.py` (FR-009)
- [ ] T025 [US3] Verify no imports or calls to `_format_activity_log_entry()` are modified by the changes — static assertion via grep in CI or code review (FR-009)

---

## Phase 6: Polish & Cross-Cutting

- [ ] T026 Run `agdt-test` + `agdt-task-wait` (background) and verify 0 regressions (FR-010)
- [ ] T027 Run `bash scripts/run-pr-checks.sh` and verify all CI checks pass — this already covers test-structure validation and lint/format checks (FR-010)
- [ ] T028 *(Optional, local iteration only — run before T027)* Run `python scripts/validate_test_structure.py` to catch 1:1:1 structure issues early;
  `scripts/run-pr-checks.sh` also runs this check (FR-010)
- [ ] T029 Verify existing assertions for `## File Review Summary:` in top-level test contexts still pass (backward compatibility) (FR-010)
- [ ] T030 *(Optional, local iteration only — run before T027)* Run `ruff check . && ruff format --check .` to catch lint/format issues early;
  `scripts/run-pr-checks.sh` also runs these checks (FR-010)

---

## Dependency Graph

```text
T001 → T009, T010, T011, T012, T013, T017, T018, T023, T024
T002 → T004
T003 → T005
T004 → T009, T010, T014, T015, T016
T005 → T011, T012
T006 → T013, T014
T007 → T017, T019, T020
T008 → T018, T020, T022
T014 → T026
T019 → T020
T020 → T026
T023, T024 → T025
T026 → T027 → T029
T028 (optional) → T027
T030 (optional) → T027
```

---

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T004, T005, T010, T012, T021 |
| FR-002 | T004, T005, T013, T014 |
| FR-003 | T002, T003, T009 |
| FR-004 | T004, T005, T014, T015 |
| FR-005 | T007, T017 |
| FR-006 | T007, T017 |
| FR-007 | T008, T020, T022 |
| FR-008 | T006, T008, T018 |
| FR-009 | T023, T024, T025 |
| FR-010 | T001, T009, T010, T011, T012, T013, T016, T017, T018, T022, T023, T026, T027, T028, T029, T030 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
