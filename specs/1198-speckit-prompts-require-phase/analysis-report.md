# Cross-Artifact Consistency & Quality Analysis

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | A. Duplication | LOW | Tasks T005+T009, T008+T010 | T009 explicitly says "Mirror the `### Phase Mapping` subsection (rule statement per FR-001, example table per FR-010, edge-case note per FR-004)" — duplicating the same content described in T005–T007 but for a different file. T010 mirrors T008. This is intentional (two files) but the task descriptions are near-duplicate in phrasing. | Acceptable — different target files. No consolidation needed. |
| F-02 | A. Duplication | LOW | Spec FR-001, FR-009 | FR-001 mandates the Phase Mapping instruction in generation prompts; FR-009 mandates it "in both the GitHub agent file and the CLI command template." FR-009 partially restates FR-001's scope with added dual-path specificity. | Keep both — FR-009 adds the dual-path constraint. Note overlap in traceability docs. |
| F-03 | B. Ambiguity | MEDIUM | Spec US1 SC-001 | "100% of `tasks.md` files generated… include a Phase Mapping table" — no measurement method specified. LLM output is non-deterministic; how is 100% verified? Sample size, repeated runs, or single-run verification? | Define a concrete verification method (e.g., "verified by manual inspection of 3 representative spec/plan pairs" or "verified by `/speckit.analyze` passing clean"). |
| F-04 | B. Ambiguity | MEDIUM | Spec SC-002 | "zero false negatives" — not testable without a defined test corpus. How many test cases constitute completeness? | Specify a minimum test corpus (e.g., "against the 3 historical PRs #1009, #1177, #1178 plus 2 synthetic edge cases"). |
| F-05 | C. Underspecification | MEDIUM | Spec Edge Cases | Edge case "plan uses sub-phases (1a, 1b, 1c)" is documented but no acceptance scenario covers it. No task explicitly handles sub-phase formatting in the example table. | Add a sub-phase example row in the template example table (T003) or in the generation prompt example (T006). |
| F-06 | C. Underspecification | LOW | Tasks T001 | "Verify you are on the correct working branch" — no action if verification fails. No acceptance criteria for what "correct" means beyond issue #1198. | Add: "If not on the correct branch, check out `1198-speckit-phase-mapping-enforcement` or the active feature branch." |
| F-07 | E. Coverage Gaps | MEDIUM | NFR-001 | NFR-001 (≤500 token budget) is covered by T018 but only as a `wc -w` estimation. No task validates actual token count with a tokenizer. | Acceptable given the estimation approach documented in the plan's risk assessment. Note the approximation in T018 description. |
| F-08 | E. Coverage Gaps | LOW | NFR-002 | NFR-002 (table format consistency with existing tables) has no explicit verification task. | Add a brief check in T015 or T017 to confirm table format matches existing `tasks.md` pipe-table conventions. |
| F-09 | F. Inconsistency | MEDIUM | Plan Phase 1 vs Tasks Phase 1 | Plan Phase 1 is "Template Update" (substantive work). Tasks Phase 1 is "Setup" (single branch-verification task T001). The Phase Mapping table in tasks.md maps Tasks Phase 2 → Plan Phase 1, which is correct, but the Plan's "Phase 1" label could confuse readers scanning both documents. | No action needed — the Phase Mapping table in tasks.md correctly documents this. This is exactly the scenario the feature addresses. |
| F-10 | F. Inconsistency | LOW | Plan Phase 2 tasks vs Tasks Phase 3 | Plan Phase 2 lists two numbered tasks (agent file + CLI template). Tasks Phase 3 expands this into 6 granular tasks (T005–T010). The granularity difference is expected but the plan's task numbering ("1. In `.github/agents/…`", "2. In `.specify/templates/…`") doesn't map to task IDs. | Consider adding task ID cross-references in the plan for traceability, or accept the granularity difference as by-design. |
| F-11 | G. Task Deduplication | HIGH | T005, T009 | T005 adds `### Phase Mapping` subsection to `.github/agents/speckit.tasks.agent.md`; T009 mirrors the same subsection to `.specify/templates/commands/tasks.md`. Same description intent, different files. Single-dimension match (description). | No merge needed — different target files. Correctly parallel tasks. |
| F-12 | G. Task Deduplication | HIGH | T008, T010 | T008 adds bullet in step 4 of Outline in agent file; T010 adds same bullet in step 4 of Outline in CLI template. Same description intent, different files. Single-dimension match (description). | No merge needed — mirrors FR-009 dual-path requirement. |
| F-13 | G. Task Deduplication | HIGH | T011, T002+T003+T004 | T011 is a verification task for work done in T002–T004. Description overlaps significantly. Same file but file overlap is inherent to verification (not counted as separate dimension). Single-dimension match (description). | Acceptable — T011 is a QA gate, not duplicate work. Consider merging T011 into Phase 7 polish if verification overhead is a concern. |
| F-14 | G. Task Deduplication | HIGH | T014, T005+T006+T007+T008+T009+T010 | T014 verifies work done in T005–T010. Description overlaps but file overlap is inherent to verification (not counted). Single-dimension match (description). | Same pattern as F-13 — acceptable as QA gate. |

### Category G Structured Findings

[
  {
    "id": "F-11",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T005", "T009"],
    "dimensions": ["description"],
    "rationale": "Both add Phase Mapping subsection (rule, example, edge-case note). Identical intent, different target files (agent vs CLI). Single-dimension overlap."
  },
  {
    "id": "F-12",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T008", "T010"],
    "dimensions": ["description"],
    "rationale": "Both add Outline step 4 bullet requiring Phase Mapping table. Identical intent, different files. Single-dimension overlap."
  },
  {
    "id": "F-13",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T011", "T002", "T003", "T004"],
    "dimensions": ["description"],
    "rationale": "T011 verifies T002-T004 on tasks-template.md. File overlap inherent to verification, not counted. Single-dimension overlap."
  },
  {
    "id": "F-14",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T014", "T005", "T006", "T007", "T008", "T009", "T010"],
    "dimensions": ["description"],
    "rationale": "T014 verifies T005-T010 across both prompt files. File overlap inherent to verification, not counted. Single-dimension overlap."
  }
]

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T005, T008, T009, T010 | Covered in both agent and CLI paths |
| FR-002 | ✅ | T003, T011 | Table columns defined in template |
| FR-003 | ✅ | T002, T011 | Placement requirement covered |
| FR-004 | ✅ | T007, T009 | Edge-case note for verbatim headings |
| FR-005 | ✅ | T002, T004, T011 | Unconditional placeholder + guidance comment |
| FR-006 | ✅ | T012 | Missing table detection rule |
| FR-007 | ✅ | T012 | HIGH severity classification |
| FR-008 | ✅ | T013 | Stale reference detection, MEDIUM severity |
| FR-009 | ✅ | T005, T008, T009, T010, T014, T017 | Dual-path consistency verified |
| FR-010 | ✅ | T006, T009, T014 | Example table in both paths |
| NFR-001 | ✅ | T018 | Token budget estimation via `wc -w` |
| NFR-002 | ⚠️ | T015 (implicit) | No explicit verification task; implicitly covered by markdownlint |
| NFR-003 | ✅ | T015, T016 | Markdownlint + full PR checks |
| SC-001 | ⚠️ | T005–T010 | Implementation covered; measurement method unspecified (see F-03) |
| SC-002 | ⚠️ | T012, T013 | Rules added; test corpus undefined (see F-04) |
| SC-003 | ⚠️ | — | Outcome metric; no explicit regression test task |
| SC-004 | ✅ | T016 | PR checks script |
| SC-005 | ✅ | T019 | Explicit verification task |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements (FR + NFR) | 13 (10 FR + 3 NFR) |
| Total Tasks | 19 (T001–T019) |
| Requirement Coverage % (FR + NFR only) | 92% (12/13 requirements have explicit tasks; NFR-002 lacks dedicated task) |
| Total Success Criteria | 5 (SC-001–SC-005) |
| SC Coverage % | 40% (2/5 fully covered; SC-001, SC-002 partial, SC-003 lacks dedicated task) |
| Ambiguity Count | 2 (F-03, F-04) |
| Requirement Duplication Count (Category A) | 2 (F-01, F-02) |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 4 |
| Task Deduplication by Type | 0 duplicate / 4 overlapping / 0 conflicting |
| Multi-Task Group Count | 2 (F-13 with 4 tasks, F-14 with 7 tasks) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
