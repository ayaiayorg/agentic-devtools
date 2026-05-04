# Cross-Artifact Consistency & Quality Analysis

**Feature**: GitHub App Token for Copilot Review Requests (#1283)
**Analysis Date**: 2026-05-04

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | Duplication | LOW | T008, T014, T019, T026, T028 | T008/T014/T019 each verify zero `secrets.COPILOT_GITHUB_TOKEN` in their respective workflow file; T026 re-runs the same grep across all workflows; T028 extends to full repo. Three layers of the same verification. | Consolidate per-workflow removal verification into T026/T028; keep T008/T014/T019 as "remove references" tasks without redundant grep verification steps. |
| F-02 | Duplication | LOW | FR-004, Edge Case (empty token) | FR-004 requires validation that the token is non-empty; the edge case section independently states "must fail with a clear error rather than silently producing an empty token." Same constraint stated twice. | No action needed — edge case reinforces FR-004. Note for implementers that these are the same control. |
| F-03 | Ambiguity | MEDIUM | NFR-001, SC-005 | NFR-001 says "no more than 10 seconds" for token generation; SC-005 allows 15 seconds total including "CI measurement variance." No measurement methodology specified — how is baseline established? Single run? Average of N runs? | Define measurement methodology: e.g., "median of 5 consecutive runs on the same runner type compared to median of 5 PAT-based runs." |
| F-04 | Ambiguity | LOW | Edge Case — token expiry | "The longest SpecKit workflow typically completes within minutes" — no concrete upper bound. If a workflow takes 50+ minutes (e.g., large spec generation), the 1-hour token lifetime becomes relevant. | Add a concrete expected maximum workflow duration or document that token refresh is out of scope with a stated assumption (e.g., "all workflows complete within 30 minutes"). |
| F-05 | Underspecification | MEDIUM | Tasks, NFR-001 | NFR-001 (≤10s token generation) has no task to measure or validate it. SC-005 (≤15s total) similarly has no measurement task. Phase 5 verification only covers grep checks and functional tests. | Add a task to measure token generation step duration in the verification phase and compare against NFR-001/SC-005 thresholds. |
| F-06 | Underspecification | MEDIUM | Edge Case — permissions error | Edge case states "the step must fail and the error annotation must suggest checking App permissions" but no task implements custom error handling for 403 responses from the reviewer request API. | Either add a task to implement 403 error handling with permission guidance, or document that native GitHub Actions error output is sufficient and no custom handling is needed. |
| F-07 | Underspecification | LOW | T029 | "Update test assertions/mocks in `tests/workflows/test_copilot_generate.py`" — no specifics on what assertions change. If the test file doesn't exist or has no PAT-related assertions, the task is a no-op. | T001 (audit) should inventory test file references; T029 should be conditional on T001 findings. |
| F-08 | Underspecification | LOW | T030 | "Check `.github/ISSUE_TEMPLATE/speckit-test.md` for any `COPILOT_GITHUB_TOKEN` references and update if found" — task is speculative. | Fold into T001 audit; only create a separate task if references are found. |
| F-09 | Constitution Alignment | LOW | Spec | No explicit "Out of Scope" section. The spec implicitly scopes by listing only what changes, but an explicit exclusion list (e.g., "Copilot SDK changes are out of scope", "GitHub App creation is out of scope") would reduce ambiguity. | Add a brief "Out of Scope" section listing excluded items. |
| F-10 | Inconsistency | MEDIUM | Plan Phase 4 vs Tasks Phase 8 | Plan "Phase 4 — Test & Peripheral File Updates" maps to Tasks "Phase 8: Polish & Cross-Cutting." Phase numbering and naming differ between plan and tasks, making cross-referencing harder. | Align phase numbers and names between plan and tasks, or add an explicit mapping table. |
| F-11 | Inconsistency | LOW | Plan Phase 2 vs Tasks Phase 6 | Plan "Phase 2 — Script & Template Updates" covers `copilot_generate.py`, `generate-spec-from-issue.sh`, `failed.md`. Tasks place these in Phase 6 under US4 (Documentation). Scripts are not documentation — they are code. | Recategorize T023/T024 as code changes (not documentation) or rename the tasks phase to "Documentation & Script Updates." |
| F-12 | Inconsistency | LOW | Plan 1.2 conditional gate vs Tasks | Plan specifies the exact `if:` conditional gate for `speckit-issue-trigger.yml` (`steps.validate-label.outputs.label_matches == 'true' && steps.idempotency.outputs.skipped != 'true'`), but T010 only says "preserving existing `if:` conditional gate" without specifying it. | Acceptable — tasks reference plan for detail. No action needed unless tasks are consumed independently. |
| F-13 | Task Dedup | HIGH | T008, T026, T028 | T008 verifies zero `secrets.COPILOT_GITHUB_TOKEN` in `speckit-phase-progression.yml`; T026 runs the same grep across all `.github/` workflows (superset); T028 extends to full repo (superset of T026). Single dimension overlap: description. | Keep T026+T028 as final verification; simplify T008/T014/T019 to "remove references" without independent grep verification. |
| F-14 | Task Dedup | HIGH | T014, T026, T028 | Same pattern as F-13 for `speckit-issue-trigger.yml`. T014's verification is a subset of T026/T028. | Same recommendation as F-13. |
| F-15 | Task Dedup | HIGH | T019, T026, T028 | Same pattern as F-13 for `speckit-copilot-review-request.yml`. T019's verification is a subset of T026/T028. | Same recommendation as F-13. |
| F-16 | Task Dedup | HIGH | T009, T015, T020 | All three tasks verify idempotency guard logic with App token across different workflow files. Same description intent (verify idempotency), but different file targets. Single dimension: description. | Acceptable — different files justify separate tasks. Consider a single cross-workflow idempotency verification task if manual testing is used. |
| F-17 | Task Dedup | CRITICAL | T031, T033 | T031 verifies consistent `app_token` step id and output reference across all workflows (FR-009). T033 verifies step placement is before all token-consuming steps (also FR-009). Both target the same three files checking FR-009 compliance. Two dimensions: description + file_path. | Merge T031 and T033 into a single FR-009 compliance verification task covering both step id consistency and placement order. |

### Category G Structured Findings

[
{"id":"F-13","overlap_type":"overlapping","severity":"HIGH",
"task_ids":["T008","T026","T028"],"dimensions":["description"],
"rationale":"T008 verifies zero secrets.COPILOT_GITHUB_TOKEN in speckit-phase-progression.yml. T026 runs identical grep across all workflows (superset). T028 extends to full repo."},
{"id":"F-14","overlap_type":"overlapping","severity":"HIGH",
"task_ids":["T014","T026","T028"],"dimensions":["description"],
"rationale":"T014 verifies zero secrets.COPILOT_GITHUB_TOKEN in speckit-issue-trigger.yml. T026 covers all workflows (superset). T028 covers full repo. Same pattern as F-13."},
{"id":"F-15","overlap_type":"overlapping","severity":"HIGH",
"task_ids":["T019","T026","T028"],"dimensions":["description"],
"rationale":"T019 verifies zero secrets.COPILOT_GITHUB_TOKEN in speckit-copilot-review-request.yml. T026 and T028 are supersets. Same pattern as F-13/F-14."},
{"id":"F-16","overlap_type":"overlapping","severity":"HIGH",
"task_ids":["T009","T015","T020"],"dimensions":["description"],
"rationale":"All three verify idempotency guard logic with App token across different workflow files. Same intent, different file targets."},
{"id":"F-17","overlap_type":"overlapping","severity":"CRITICAL",
"task_ids":["T031","T033"],"dimensions":["description","file_path"],
"rationale":"T031 verifies consistent app_token step id/output reference across workflows (FR-009). T033 verifies step placement in same files. Complementary FR-009 checks."}
]

## Coverage Summary Tables

### Requirement Coverage (FR + NFR)

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T003, T004, T010, T016 | Fully covered across all 3 workflows |
| FR-002 | ✅ | T005, T006, T011, T012, T017, T018 | Fully covered |
| FR-003 | ✅ | T005, T011 | Covered for both workflows that need SDK env-var |
| FR-004 | ✅ | T004, T010, T016 | Validation replacement covered |
| FR-005 | ✅ | T001, T008, T014, T019, T026, T028 | Audit + per-workflow + cross-repo verification |
| FR-006 | ✅ | T007, T013, T023, T024, T025, T032 | Error messages updated across workflows, scripts, templates |
| FR-007 | ✅ | T021 | README update |
| FR-008 | ✅ | T022 | CONTRIBUTING update |
| FR-009 | ✅ | T003, T031, T033 | Pattern definition + cross-workflow verification |
| FR-010 | ✅ | T009, T015, T020 | Idempotency verified per workflow |
| NFR-001 | ❌ | — | No measurement/validation task (see F-05) |
| NFR-002 | ⚠️ | — | Inherently satisfied per clarification; no explicit task needed |
| NFR-003 | ✅ | T032 | Error message actionability verified |

### Success Criteria Coverage (SC)

| Criterion Key | Has Task? | Task IDs | Notes |
|---------------|-----------|----------|-------|
| SC-001 | ✅ | T026 | Grep verification |
| SC-002 | ✅ | T027 | Doc grep verification |
| SC-003 | ⚠️ | — | Listed in Plan Phase 5 step 3 but no numbered task |
| SC-004 | ⚠️ | — | Listed in Plan Phase 5 step 4 but no numbered task |
| SC-005 | ❌ | — | No measurement task (see F-05) |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements (FR + NFR) | 13 (10 FR + 3 NFR) |
| Requirement Coverage % (FR + NFR only) | 85% (11/13 have tasks) |
| Total Success Criteria (SC) | 5 |
| SC Coverage % | 40% (2/5 have tasks; SC-003/SC-004 in plan but untasked) |
| Total Tasks | 33 |
| Ambiguity Count | 2 (F-03, F-04) |
| Requirement Duplication Count | 2 (F-01, F-02) |
| Critical Issues Count | 1 |
| Task Deduplication Finding Count | 5 |
| Task Dedup by Type | duplicate: 0 / overlapping: 5 / conflicting: 0 |
| Multi-Task Group Count | 4 (F-13/F-14/F-15/F-16 each involve 3 tasks; F-17 involves 2) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
