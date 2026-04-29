# Specification Analysis Report — Pass G: Code Reference Cross-Referencing

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | Duplication | LOW | spec.md FR-005, FR-008 | FR-005 specifies "best fuzzy candidate scores below 0.75" as the invalid threshold; FR-008 independently specifies "minimum normalized similarity score of 0.75 to surface a candidate." These express the same threshold from complementary angles. | Acceptable overlap — both reinforce the 0.75 constant. No consolidation needed, but add a cross-reference note in FR-005 pointing to FR-008. |
| F-02 | Duplication | LOW | spec.md Edge Case 5, FR-006 | Edge Case 5 re-lists a subset of new-symbol intent markers already defined in FR-006 and the Clarifications section. Partial redundancy. | Simplify Edge Case 5 to reference FR-006 rather than repeating the marker list. |
| F-03 | Duplication | LOW | spec.md Clarifications (first Q/A) vs FR-006 | The clarification answer for the first Q/A entry duplicates the exact marker list that FR-006 defines. | Reference FR-006 from clarifications or vice versa; keep canonical list in one location only. |
| F-04 | Ambiguity | MEDIUM | plan.md §3 Data Flow | "when enough evidence exists" is used to qualify classification output but has no measurable definition. | Replace with concrete condition (e.g., "when a recognized intent marker is detected per FR-006 or an exact/fuzzy match is found per FR-007/FR-008"). |
| F-05 | Ambiguity | LOW | spec.md FR-011 | "otherwise non-editable files according to repository conventions" is open-ended. Only `.gitignore` patterns, `_version.py`, and `__pycache__` are concretely named. | Either enumerate the complete convention set or state that the `PROTECTED_FILE_PATTERNS` constant is the exhaustive list for the initial release. |
| F-06 | Ambiguity | MEDIUM | plan.md §3 Agent Integration bullet 3 | "Finding IDs that continue to use the existing sequential analyze-report contract (`F-01`, `F-02`, …), including for Pass G output" — ambiguous whether Pass G findings share the global `F-XX` sequence or get a `G-XX` prefix. The spec says "Pass G section" (FR-012) while the plan says "sequential finding ID contract." | Clarify explicitly: do Pass G findings use `G-01, G-02…` or continue the global `F-XX` numbering? The agent prompt currently uses category-initial prefixes (A1, B1, etc.), which conflicts with `F-XX`. |
| F-07 | Underspecification | MEDIUM | spec.md US4 AC3 | "A reference format the extractor cannot classify" — no examples given of what unclassifiable formats look like, making it hard to write precise test fixtures. | Add 1–2 concrete examples of unclassifiable reference formats (e.g., bare prose mention of a concept without backticks, ambiguous English words). |
| F-08 | Underspecification | MEDIUM | plan.md Phase 3 | Plan states "Defer bare-text pattern matching initially" but does not define the boundary between what counts as bare-text vs. backtick-quoted for edge cases like nested backticks or backtick-quoted strings inside code fences. | Specify behavior for nested/escaped backticks and backtick references inside code fences. |
| F-09 | Underspecification | MEDIUM | spec.md FR-002, plan.md §2b | CLI entry point extraction from `pyproject.toml` is specified, but the plan's `tomllib` fallback for Python 3.10 uses a "minimal line-based parser via regex." No spec defines what happens if the TOML section is malformed or missing. | Add a graceful-degradation clause: if `[project.scripts]` parsing fails, skip CLI entry points with a warning (consistent with NFR-005). |
| F-10 | Underspecification | LOW | tasks.md T047 | T047 says "orchestrate full pipeline" but does not specify error-handling behavior when individual pipeline stages fail (e.g., inventory build fails, plan file missing). | Specify that `cross_ref_command()` should follow NFR-005 graceful degradation — emit partial results rather than crash. |
| F-11 | Coverage Gaps | MEDIUM | spec.md NFR-001 | NFR-001 (Determinism) is covered by T022 and T032 (unit-level deterministic sort) and T054 (integration test). However, none of these tasks explicitly assert ordering **stability across runs** — they verify sorted output but not that repeated executions produce identical order for equal-score items. | Add explicit stability assertions to T022 or T032 (run twice, compare output order) to confirm determinism is not just correct sorting but also repeatable ordering. |
| F-12 | Coverage Gaps | MEDIUM | spec.md NFR-004 | NFR-004 (Report compatibility) has no dedicated task asserting backward-compatible schema. T041/T042 test report output format but don't explicitly validate that existing A–F consumers still parse correctly with Pass G appended. | Add a test scenario in T041 or T042 that feeds Pass G output to the existing report parser/gate to verify no breakage. |
| F-13 | Coverage Gaps | LOW | spec.md NFR-005 | NFR-005 (Graceful degradation) is covered implicitly by T024 (unparseable file skip) and T039 (SKIPPED classification) but has no single integration-level test that forces multiple failure modes simultaneously. | Consider adding an integration scenario that combines unparseable Python file + missing `pyproject.toml` + unclassifiable reference to validate end-to-end graceful degradation. |
| F-14 | Inconsistency | HIGH | plan.md §3 vs agent prompt | Plan says finding IDs use `F-01, F-02, …` sequential format. The existing agent prompt (`.github/agents/speckit.analyze.agent.md` line 143) uses category-initial prefixes (`A1`, `B1`, etc.). These are incompatible numbering schemes. T052 must reconcile this. | Decide on one scheme. The established pipeline/report convention is `F-XX` (global sequential numbering with category recorded in the Category column). Either align the agent prompt to emit `F-XX` IDs directly, or document that the agent prompt's category-initial format (`A1`, `B1`, etc.) is internal working notation that gets renumbered to `F-XX` in the final report output. Update plan §3 to state which approach is taken. |
| F-15 | Inconsistency | MEDIUM | plan.md §4 Phase 2b vs spec.md FR-002 | Plan says "Parse `.py` files using `ast.parse()` with error recovery (skip unparseable files)" but spec FR-002 says "The inventory interface MUST be designed so additional language extractors can be added without modifying Pass G core logic." The plan's `inventory.py` delegates to extractors, but `build_inventory` also directly handles `git ls-files` and `PROTECTED_FILE_PATTERNS` — the boundary between inventory and extractor responsibilities could be clearer. | Add a sentence to the plan clarifying that `build_inventory()` owns file discovery and filtering, while extractors own only AST/symbol parsing. |
| F-16 | Inconsistency | LOW | tasks.md T024 | T024 is marked `[P]` (can run in parallel — different files, no dependencies) AND `[US1]`, but its dependency chain says "Depends on: T020" (extractor base). A task with an explicit dependency on another task contradicts the `[P]` marker's "no dependencies" semantics. Meanwhile T019 (the test for the base class) is not marked `[P]`. The `[P]` marker usage is inconsistent across the task list. | Standardize `[P]` marker meaning per the template definition ("can run in parallel — different files, no dependencies"). Remove `[P]` from T024 since it has a dependency on T020, or remove the dependency declaration if T024 is truly parallelizable. |
| F-17 | Inconsistency | MEDIUM | spec.md US2 AC1 vs plan.md Phase 4b | US2 AC1 says "similarity score is ≥ 0.75 for at least one candidate" to include suggestions. Plan Phase 4b says "Filter candidates by `SUGGESTION_THRESHOLD` (≥ 0.75)." Semantically aligned, but the plan also says "Sort candidates deterministically by `(score desc, symbol_name, file_path, kind)`" while the spec does not mention sorting requirements for candidate presentation. | Add candidate sort-order requirement to spec FR-010 or NFR-001 to close the gap between spec and plan. |
| F-18 | Inconsistency | LOW | tasks.md T048 vs plan.md Phase 7 | T048 says "add `cross_ref_command` export as `speckit_cross_ref`" — the naming convention differs from `validate_frs_command` → `speckit_validate_frs`. Plan says `cross_ref_command()` as the function name. Confirm the export alias follows the established `speckit_<name>` pattern. | Ensure T048 exports as `speckit_cross_ref` (matching `speckit_validate_frs` pattern). The plan and task already align on this; just verify during implementation. |

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T013, T014, T026, T027, T028 | Fully covered |
| FR-002 | ✅ | T019, T020, T021, T022, T023, T024, T025, T059 | Fully covered |
| FR-003 | ✅ | T015, T029, T030, T039, T040 | Fully covered |
| FR-004 | ✅ | T014, T026, T028 | Fully covered |
| FR-005 | ✅ | T029, T030, T035 | Fully covered |
| FR-006 | ✅ | T008, T009, T012, T036, T037, T038 | Fully covered |
| FR-007 | ✅ | T013, T022, T023, T024, T025, T027, T031, T034, T058 | Fully covered |
| FR-008 | ✅ | T004, T012, T016, T032, T034, T035 | Fully covered |
| FR-009 | ✅ | T005, T006, T012, T033, T034, T035 | Fully covered |
| FR-010 | ✅ | T006, T012, T032, T033, T034, T039 | Fully covered |
| FR-011 | ✅ | T010, T012, T021, T023, T057 | Fully covered |
| FR-012 | ✅ | T041, T042, T043, T044, T047, T052, T053 | Fully covered |
| FR-013 | ✅ | T017, T029, T041, T042, T043, T045, T047 | Fully covered |
| FR-014 | ✅ | T017, T041, T043, T045 | Fully covered |
| FR-015 | ✅ | T015, T026, T029, T039, T042, T056 | Fully covered |
| FR-016 | ✅ | T029, T045, T046 | Fully covered |
| NFR-001 | ✅ | T022, T032, T054 | Unit + integration; see F-11 |
| NFR-002 | ✅ | T007, T012, T041, T047, T055 | Fully covered |
| NFR-003 | ✅ | T032, T034 | Implicit via `difflib` usage; no `rapidfuzz` tasks exist (correct) |
| NFR-004 | ⚠️ | T041, T042, T043, T052 | No explicit backward-compat validation task; see F-12 |
| NFR-005 | ✅ | T024, T039, T040 | Implicit graceful degradation; see F-13 |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 21 (16 FR + 5 NFR) |
| Total Tasks | 62 (T001–T062) |
| Full Coverage % | 95.2% (20/21 requirements with all tasks explicitly covering them; NFR-004 partially covered) |
| Ambiguity Count | 3 (F-04, F-05, F-06) |
| Duplication Count | 3 (F-01, F-02, F-03) |
| Critical Issues Count | 0 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
