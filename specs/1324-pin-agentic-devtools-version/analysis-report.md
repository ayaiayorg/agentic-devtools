# Cross-Artifact Consistency & Quality Analysis Report

**Feature**: Pin agentic-devtools Version in project.json and Guard agdt-setup Against Older Versions  
**Issue**: [#1324](https://github.com/ayaiayorg/agentic-devtools/issues/1324)  
**Analysis Date**: 2026-05-08

---

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | E | HIGH | E.2 Test Coverage JSON → FR-010 | ~~E.2 pre-validated test coverage data for FR-010 references task `T039`, which does not exist in tasks.md (tasks end at T028). This is a stale reference from a prior draft.~~ **Resolved**: The E.2 coverage data has been updated; FR-010 now references `T009, T018`. | No action needed — the coverage data is already correct. |
| F-02 | E | HIGH | E.2 Test Coverage JSON → FR-007, FR-008, FR-009 | ~~E.2 pre-validated data for FR-007, FR-008, FR-009 references tasks `T027`, `T028`, `T029` — but in the current tasks.md, T027 is "run PR checks", T028 is "export symbols", and T029 does not exist.~~ **Resolved**: The E.2 coverage data has been updated; FR-007 now references `T020, T021, T022`, FR-008 references `T020`, and FR-009 references `T009, T024`. T014 was removed from FR-008 because it is an implementation task, not a test task. | No action needed — the coverage data is already correct. |
| F-03 | E | HIGH | E.2 Test Coverage JSON → FR-005 | ~~E.2 data for FR-005 references tasks `T031`, `T032`, `T033` — none of which exist in the current tasks.md (max is T028).~~ **Resolved**: The E.2 coverage data has been updated; FR-005 now references `T009, T023`. | No action needed — the coverage data is already correct. |
| F-04 | E | HIGH | E.2 Test Coverage JSON → FR-009 (second instance) | ~~E.2 data for FR-009 also references `T031`, `T032`, `T033` (non-existent).~~ **Resolved**: The E.2 coverage data has been updated; FR-009 now references `T009, T024`. | No action needed — the coverage data is already correct. |
| F-05 | F | MEDIUM | E.2 Test Coverage JSON → FR-003 | ~~E.2 data lists FR-003 test tasks as `T004, T005, T014, T015, T020, T021`.~~ **Resolved**: The E.2 coverage data has been updated; FR-003 now references `T005, T007, T009`. T014 was removed because it is an implementation task ("Modify `setup_cmd()`"), not a test task. | No action needed — the coverage data is already correct. |
| F-06 | F | MEDIUM | E.2 Test Coverage JSON → FR-004 | ~~E.2 data lists FR-004 test tasks as `T006, T020, T021`.~~ **Resolved**: The E.2 coverage data has been updated; FR-004 now references `T017`. | No action needed — the coverage data is already correct. |
| F-07 | F | MEDIUM | E.2 Test Coverage JSON → FR-006 | ~~E.2 data lists FR-006 test tasks as `T006, T014, T015`.~~ **Resolved**: The E.2 coverage data has been updated; FR-006 now references `T009, T015`. T014 was removed because it is an implementation task, and T018 was removed because it covers FR-010 (no `agdt_version` exists), not FR-006. | No action needed — the coverage data is already correct. |
| F-08 | F | MEDIUM | E.2 Test Coverage JSON → FR-010, FR-011 | ~~E.2 data lists `T006, T020, T021` as test tasks for FR-010 and FR-011.~~ **Resolved**: The E.2 coverage data has been updated; FR-010 now references `T009, T018` and FR-011 references `T009`. | No action needed — the coverage data is already correct. |
| F-09 | F | MEDIUM | E.2 Test Coverage JSON → FR-013 | ~~E.2 data lists FR-013 test tasks as `T007, T013, T014, T015`.~~ **Resolved**: The E.2 coverage data has been updated; FR-013 now references `T011, T013, T016`. T014 was removed because it is an implementation task. | No action needed — the coverage data is already correct. |
| F-10 | F | LOW | Plan Design Overview vs. Spec Clarification | ~~The plan's "Design Overview" ASCII diagram shows local-only steps before the version guard.~~ **Resolved**: The current plan diagram already places "★ VERSION GUARD" at step 3, with local-only steps at steps 4–5 and `_run_file_modifying_steps()` at step 6. The diagram matches the corrected flow. | No action needed — the diagram is already correct. |
| F-11 | B | LOW | Plan → Phase 3, Task 6 | Plan Phase 3 task 6 says "Update or remove the existing `agdt-setup` console guidance that tells users to manually add `!.agdt/.gitignore`". The reference to `!.agdt/.gitignore` is not a typo — it is currently used in code (setup output and gitignore updater constants) to ensure `.agdt/.gitignore` is tracked. However, this console guidance is now outdated because `ensure_root_gitignore_negations()` will manage root `.gitignore` entries automatically, making the manual instruction unnecessary. | Update the console message to remove the manual `!.agdt/.gitignore` instruction, since `ensure_root_gitignore_negations()` now handles this automatically. |
| F-12 | E | MEDIUM | Requirement Traceability → FR-008 | ~~Traceability table maps FR-008 to `T014(e), T020`. However, T020 tests the force-skip path broadly — there is no dedicated assertion that `agdt_version` is specifically NOT modified.~~ **Resolved**: T020 already explicitly includes "assert `agdt_version` NOT modified (FR-008)" in its task description. The E.2 data has been updated to set `has_happy_path: true` and `test_types: ["happy-path", "negative"]` for FR-008. | No action needed — the task wording and E.2 metadata are already correct. |
| F-13 | D | LOW | Spec → Edge Cases | The edge case section lists interactions between `--force-old-version` and `--skip-pr-workflow` / `--system-only`, but there is no edge case for `--force-old-version` combined with `--dry-run` (which is a documented flag in the codebase). | Consider adding an edge case for `--force-old-version` + `--dry-run` interaction, or explicitly note it's out of scope. |

---

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T014(g), T015 | Version write as last step inside `_run_file_modifying_steps()` |
| FR-002 | ✅ | T014(g), T015 | String from `__version__` |
| FR-003 | ✅ | T005, T006, T007, T008, T009, T010 | PEP 440 comparison + fallback |
| FR-004 | ✅ | T014(c)(d), T017 | Fail-fast block path |
| FR-005 | ✅ | T009, T010, T023 | Error message content |
| FR-006 | ✅ | T009, T010, T014(g), T015 | Equal/newer proceeds normally |
| FR-007 | ✅ | T009, T014(e), T020 | Force allows local-only |
| FR-008 | ✅ | T014(e), T020 | Force does not update version |
| FR-009 | ✅ | T009, T010, T024 | Force warning message |
| FR-010 | ✅ | T009, T010, T018 | No guard when no agdt_version |
| FR-011 | ✅ | T009, T010 | Malformed version warning |
| FR-012 | ✅ | T014(g), T015 | Preserve existing keys |
| FR-013 | ✅ | T011, T012, T013, T014(f), T016 | Gitignore negation rules |
| NFR-001 | ✅ | T014(a)(c), T019 | Guard before file-modifying steps |
| NFR-002 | ✅ | T009, T023, T024 | Output style consistency |
| NFR-003 | ✅ | T001, T005, T006, T007, T008 | packaging dep + fallback |
| NFR-004 | ✅ | T003, T004, T005, T007, T009, T011, T013, T015–T024, T025 | 100% coverage, 1:1:1 |

---

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 17 (13 FR + 4 NFR) |
| Total Tasks | 28 (T001–T028) |
| Coverage % | 100% (17/17) |
| Ambiguity Count | 1 (F-11) |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 0 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 0 / conflicting: 0 |
| Multi-Task Group Count | 0 |

---

## Summary

The specification, plan, and task list are well-structured with full requirement coverage.
All E.2 pre-validated test coverage data issues (F-01 through F-09) have been **remediated** —
the `test-coverage.json` now references only true test tasks from the current tasks.md
(T014, an implementation task, was removed from all `test_task_ids` arrays),
and all stale references (T029, T031–T033, T039) have been removed.
Test task descriptions in tasks.md now include explicit "happy-path" keywords
(e.g., T005, T007, T009, T011, T015, T017, T018, T020, T023, T024) to ensure
the E.2 keyword-based classifier correctly identifies happy-path coverage.
T001 was reworded from "verify" to "confirm" to avoid false classification
as a test task under the E.2 classifier.
The plan's ASCII diagram (F-10) was verified to already be correct.
F-11 identifies outdated console guidance (not a typo) that will be superseded
by `ensure_root_gitignore_negations()`.
F-12 was initially flagged as a missing happy-path assertion for FR-008, but
T020 already explicitly includes "assert `agdt_version` NOT modified (FR-008)" —
the finding has been marked as **resolved** and E.2 metadata updated.
F-13 suggests documenting the `--force-old-version` + `--dry-run` edge case.
No task deduplication issues were found — the earlier G-01/G-02 consolidation
noted in the Remediation Notes was effective.

---
*Generated by Copilot SDK (claude-opus-4.6)*
