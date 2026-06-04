# Cross-Artifact Consistency & Quality Analysis Report

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | E | HIGH | FR-001 | FR-001 has no dedicated test task — T012 tests `fetch_applicable_suggestions()` but lacks explicit FR-001 tag | Add `(FR-001)` reference to T012 or create a dedicated test task for the GraphQL query filtering behavior |
| F-02 | E | HIGH | FR-003 | FR-003 (bisection fallback) has no tagged test task — T028 tests the function but lacks FR-003 tag in test task title | Add `(FR-003)` to T028's description to establish traceability |
| F-03 | E | HIGH | FR-004 | FR-004 (outdated exclusion) has no tagged test task — T012 covers filtering but lacks explicit FR-004 reference | Add `(FR-004)` to T012 or T050 to establish explicit test coverage |
| F-04 | E | HIGH | FR-009 | FR-009 (pipeline positioning) lacks a dedicated test task — T027 tests ordering but doesn't reference FR-009 | Add `(FR-009)` to T027's description |
| F-05 | E | HIGH | FR-013 | FR-013 (`runs_after_invalidation`) lacks a tagged test task — T036 implements it but no test validates the attribute | Add a test in `tests/unit/cli/ci/pipeline/actions/dispatch_repair/` verifying the attribute is set |
| F-06 | F | MEDIUM | Plan Phase 2 vs FR-010 | Plan states `max_retries=5, initial_delay=1s` but FR-010 spec says "up to 2 retries with exponential backoff, starting at 1 second" — contradictory retry counts | Align plan to spec (2 retries) or update FR-010 to match existing `retry_with_backoff` defaults (5 retries) |
| F-07 | F | MEDIUM | T031 vs FR-010 | T031 references `max_retries=5` while FR-010 specifies "up to 2 retries" — task contradicts the requirement | Resolve retry count discrepancy; update T031 or FR-010 |
| F-08 | C | MEDIUM | NFR-001 | "complete within 30 seconds" excludes "network latency variance" — unmeasurable exclusion makes the criterion untestable in practice | Define latency budget or specify measurement conditions (e.g., "mock network, local execution") |
| F-09 | C | MEDIUM | NFR-004 | Pagination requirement lacks specification of page size or cursor strategy | Add page size (e.g., 100 per page) and cursor field name to the requirement |
| F-10 | B | LOW | SC-006 | "at least 60% of originally valid suggestions" — threshold is arbitrary without justification | Document rationale or link to empirical data |
| F-11 | D | LOW | Spec | No explicit "Out of Scope" section listing deferred items (per-repo config, manual squash) | Add an "Out of Scope" section consolidating deferred items |
| F-12 | E | LOW | NFR-001, NFR-002, NFR-003, NFR-004 | NFR requirements have no explicit task coverage — only NFR-003 is addressed by T054 | Add tasks or notes confirming NFRs are validated by existing patterns (logging, timing, pagination) |
| F-13 | G | HIGH | T027, T042, T046 | Integration tests for pipeline ordering overlap — T027 verifies sequence, T042 verifies guard propagation in same sequence, T046 tests end-to-end pipeline — all in same test file | Consolidate into distinct test methods within a single integration test file; ensure non-redundant assertions |
| F-14 | G | HIGH | T040, T041 | Guard-blocking tests for fork PRs and privileged paths target same test file `test_guards.py` with overlapping setup logic | Acceptable if tests cover distinct scenarios; confirm no redundant assertions |

### Category G Structured Findings

[
  {
    "id": "F-13",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T027", "T042", "T046"],
    "dimensions": ["file_path"],
    "rationale": "All three tasks update the same integration-test file for sequence-related behavior. They overlap on file_path, but each task asserts a different behavior."
  },
  {
    "id": "F-14",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T040", "T041"],
    "dimensions": ["file_path"],
    "rationale": "Both tasks target the same guard-test file. They overlap on file_path, but one covers fork PRs and the other covers privileged paths."
  }
]

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | Yes | T011, T012 | No tagged test task (traceability gap) |
| FR-002 | Yes | T009, T017, T018 | Covered with happy-path test |
| FR-003 | Yes | T028, T029, T033 | No tagged test task (traceability gap) |
| FR-004 | Yes | T011, T012 | No tagged test task (traceability gap) |
| FR-005 | Yes | T007, T008, T023, T024, T035, T037 | Covered |
| FR-006 | Yes | T037, T038 | Covered |
| FR-007 | Yes | T026, T042 | Covered (integration test) |
| FR-008 | Yes | T017, T018, T024 | Covered with happy-path test |
| FR-009 | Yes | T026, T027 | No tagged test task (traceability gap) |
| FR-010 | Yes | T030, T031, T049 | Covered; retry count inconsistency (see F-06, F-07) |
| FR-011 | Yes | T021, T022, T048 | Covered |
| FR-012 | Yes | T023, T024 | Covered |
| FR-013 | Yes | T036 | No tagged test task (traceability gap) |
| NFR-001 | No | — | No explicit task; assumed validated by action timing |
| NFR-002 | No | — | No explicit task; covered by code review convention |
| NFR-003 | Partial | T054 | T054 validates ActionResult compliance |
| NFR-004 | No | — | Pagination tested implicitly in T012 |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 17 (13 FR + 4 NFR) |
| Total Tasks | 56 |
| Coverage % (FR only) | 100% (13/13 have implementation tasks) |
| Coverage % (FR with tagged tests) | 62% (8/13 per validator) |
| Ambiguity Count | 1 |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 2 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 2 / conflicting: 0 |
| Multi-Task Group Count | 2 (F-13 involves 3 tasks; F-14 involves 2 tasks) |

## Next Actions

1. Resolve FR-010 retry count inconsistency across `spec.md`, `plan.md`, and `tasks.md` (F-06, F-07).
2. Add explicit test-traceability tags or dedicated test tasks for FR-001/003/004/009/013 (F-01 through F-05).
3. Clarify NFR measurability and pagination specifics, and capture missing NFR task traceability (F-08, F-09, F-12).

Would you like me to suggest concrete remediation edits for these findings?

---
*Generated by Copilot SDK (claude-opus-4.6)*
