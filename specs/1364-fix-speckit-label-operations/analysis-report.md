# Analysis Report: SpecKit Label Operations Token Fix

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A-01 | Duplication | LOW | T012 (US1), T067 (Phase 8) | T012 tests deduplication of the combined source + phase label list; T067 tests deduplication of the upstream `LABELS_JSON` parsing path (repeated entries within the JSON array itself). Distinct input paths with different dedup scopes | Already differentiated in `tasks.md` — T067 explicitly targets the `LABELS_JSON` parsing path, T012 targets the post-merge combined list. No action needed |
| A-02 | Duplication | LOW | T016 (US1), T050 (US4) | T016 tests the batch-failure fallback trigger at the orchestrator level; T050 verifies per-label call isolation in the fallback path (asserts mock `gh` call count equals label count). Both in test_label_operations.sh but with distinct verification targets | Already differentiated in `tasks.md` — T016 tests the fallback trigger, T050 asserts per-label call isolation. No action needed |
| A-03 | Duplication | MEDIUM | T030 (US1), T062 (Phase 8) | T030 is "integration test: end-to-end _apply_all_labels with mocked gh" and T062 is "integration test: full label flow end-to-end with mocked gh" — T062 adds preflight but largely overlaps T030 | Scoping overlap acknowledged — T062 is a superset of T030. See G-03 for structured analysis. Consider merging T030 into T062 or explicitly differentiating their assertions |
| A-04 | Duplication | MEDIUM | T031 (US1), T064 (Phase 8) | T031 tests "PR creation output still emitted after label operations complete" and T064 tests "PR creation output preserved when label operations fail entirely" — overlapping FR-011 preservation checks | Overlap acknowledged — both verify the same output variables (`pr_url`/`pr_number`) on different paths. See G-04 for structured analysis. Consider consolidating into a parameterized test |
| B-01 | Ambiguity | MEDIUM | Spec: US4 Scenario 3 | "Given the batch label string exceeds any API limits" — no measurable API limit specified. What is the actual limit? GitHub API doesn't document a label count limit for `gh pr edit --add-label` | Either specify a concrete limit (e.g., 100 labels or 65536 chars) or remove Scenario 3 as speculative; no task implements this split logic |
| B-02 | Ambiguity | LOW | Spec: Edge Cases | "What happens when the repository has reached its label limit?" — GitHub does not document a repository label limit. This edge case may be phantom | Verify whether GitHub enforces a label limit; if not, remove or mark as theoretical |
| C-01 | Underspecification | MEDIUM | Spec: US4 Scenario 3, Tasks | US4 Scenario 3 requires "gracefully splits into multiple batch calls" but no task implements batch splitting. T052 only verifies comma-separated construction | Either add a task for batch splitting or downgrade Scenario 3 to a non-functional note |
| C-02 | Underspecification | MEDIUM | Spec: NFR-001, Tasks: T047 | NFR-001 says "60 seconds total" but T047 implements a 45s safety cap. The 15s gap is mentioned in the risk assessment but not codified in spec. No acceptance scenario validates the timeout behavior | Add an acceptance scenario or test task that validates the 45s/60s cap behavior under load |
| D-01 | Constitution | LOW | Spec | No explicit "Out of Scope" section. While edge cases partially serve this role, explicitly listing what is NOT being changed (e.g., non-label PR operations, secret rotation) improves clarity | Add a brief "Out of Scope" section |
| E-01 | Coverage | MEDIUM | Spec: SC-003 | SC-003 ("≥95% recovery from transient failures within retry window") has no direct test task validating the 95% threshold. Tests cover retry mechanics but not statistical success rate | Add a note that SC-003 is validated operationally post-deployment, not via unit test |
| E-02 | Coverage | MEDIUM | Spec: SC-004 | SC-004 ("≤15 seconds under normal conditions") has no test task measuring elapsed time. T047 covers the 45s cap but not the 15s normal-case target | Add a test or acceptance note for the 15s performance target |
| E-03 | Coverage | LOW | Spec: Edge Case — special characters | Edge case "label name contains special characters (colons, spaces, unicode)" is covered by T065 but only for shell quoting. No test validates unicode label names specifically | Extend T065 to include a unicode label name test case |
| F-01 | Inconsistency | MEDIUM | Tasks: T037 line refs vs. Plan: Phase 5 line refs | T037 references 7 locations across lines 577–602. Line 577 is `jq` stderr suppression (not a `gh` command) but is still within FR-003 scope. Plan Phase 5 table lists "583, 584, 595, 596-602, 601, 602" — line 577 appears in tasks but not in plan; lines 596-602 appear in plan but not in tasks | Reconcile line references between plan and tasks to match the actual file. T037 now explicitly distinguishes the 6 `gh` locations from the 1 `jq` location |
| F-02 | Inconsistency | LOW | Tasks: T037 vs. T025 | T037 says "already handled by T025 replacement, verify no residual suppressions remain" — this makes T037 a verification task, not an implementation task, but it's listed under "Implementation" in Phase 4 | T037 remains under Implementation as a verification-after-replacement step. Its scope is now explicitly clarified: 6 `gh` command locations + 1 `jq` location |
| F-03 | Inconsistency | MEDIUM | `specs/1364-fix-speckit-label-operations/test-coverage.json` vs. Tasks | The pre-validated coverage file (`test-coverage.json`) maps FR-003 to T028, T070 and FR-004 to T024-T027, but the Requirements Coverage Matrix in `tasks.md` maps FR-003 to T025, T032, T033, T037 and FR-004 to T006, T011, T034-T036, T038. These are completely disjoint task sets for the same FRs | The pre-validated data in `test-coverage.json` and the `tasks.md` coverage matrix should be reconciled; one set is incorrect |
| F-04 | Inconsistency | HIGH | `specs/1364-fix-speckit-label-operations/test-coverage.json` vs. Tasks | The `test-coverage.json` maps FR-007 to T012, T014, T042-T044, T058 but `tasks.md` maps FR-007 to T015, T016, T022-T024, T048, T050, T052. Similarly FR-009 maps to T048-T052 in JSON but T054-T057, T059-T061 in `tasks.md`. The JSON appears to use shifted/wrong task IDs systematically | The `test-coverage.json` has systematically misaligned task IDs; regenerate from the actual `tasks.md` |
| F-05 | Inconsistency | MEDIUM | Spec: FR-005 vs. Plan Phase 3 | FR-005 says "minimum 2 retries" (i.e., 2 retries = 3 total attempts). Plan says `call_with_retry 3 2` (3 attempts, 2s delay). T039 says "retries on 502 error up to 2 additional times (3 total attempts)." Consistent but the spec's "minimum 2 retries" phrasing is ambiguous — does "minimum" imply more retries are possible? | Clarify FR-005: "exactly 2 retries (3 total attempts)" to remove ambiguity about "minimum" |
| G-01 | Task Dedup | LOW | T016, T050 | T016 tests the fallback trigger at the orchestrator level; T050 verifies per-label call isolation (distinct `gh` call count assertion). Already differentiated in `tasks.md` | No action needed — tasks explicitly differentiate trigger vs. call-count verification |
| G-02 | Task Dedup | LOW | T012, T067 | T012 tests deduplication of the combined source + phase label list; T067 tests deduplication of repeated entries within `LABELS_JSON` input. Already differentiated in `tasks.md` | No action needed — tasks explicitly differentiate combined-list vs. upstream-parsing dedup |
| G-03 | Task Dedup | HIGH | T030, T062 | T030 and T062 are both end-to-end integration tests of `_apply_all_labels` with mocked `gh`. T062 adds preflight but the core scope overlaps heavily | See structured findings below |
| G-04 | Task Dedup | HIGH | T031, T064 | T031 and T064 both verify PR output preservation (FR-011). Same file, same verification target (`pr_url`/`pr_number` emission) | See structured findings below |
| G-05 | Task Dedup | MEDIUM | T052, T053 | T052 "verify _apply_all_labels constructs comma-separated CSV" and T053 "verify individual fallback path logs" are verification-only tasks of code already implemented in T024. Now reclassified under a "Verification" subsection in Phase 6 | Reclassified from Implementation to Verification in `tasks.md` — no further action needed |

### Category G Structured Findings

```json
[
  {
    "id": "G-01",
    "overlap_type": "differentiated",
    "severity": "LOW",
    "task_ids": ["T016", "T050"],
    "dimensions": ["description", "file_path"],
    "rationale": "T016 tests the batch-failure fallback trigger at the orchestrator level without verifying per-label call isolation. T050 explicitly asserts that each label gets its own separate gh pr edit --add-label call (mock gh call count equals label count). Distinct verification targets in the same test file."
  },
  {
    "id": "G-02",
    "overlap_type": "differentiated",
    "severity": "LOW",
    "task_ids": ["T012", "T067"],
    "dimensions": ["description", "file_path"],
    "rationale": "T012 tests deduplication of the combined source + phase label list (post-merge). T067 targets the upstream LABELS_JSON parsing path where repeated entries within the JSON array itself are deduplicated before application. Distinct input paths with different dedup scopes."
  },
  {
    "id": "G-03",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T030", "T062"],
    "dimensions": ["description", "file_path"],
    "rationale": "Both are end-to-end integration tests of `_apply_all_labels` with mocked gh in the same test file. T030: 'end-to-end `_apply_all_labels` with mocked gh — verifies source labels + phase label are all applied via batch call'. T062: 'full label flow end-to-end with mocked gh — PR created, preflight passes, labels created, batch applied'. T062 is a superset."
  },
  {
    "id": "G-04",
    "overlap_type": "overlapping",
    "severity": "HIGH",
    "task_ids": ["T031", "T064"],
    "dimensions": ["description", "file_path"],
    "rationale": "Both verify PR creation output preservation (FR-011) in the same test file. T031: 'PR creation output still emitted after label operations complete'. T064: 'PR creation output preserved when label operations fail entirely'. Same output variables checked, different success/failure paths — could be two cases in one test."
  },
  {
    "id": "G-05",
    "overlap_type": "differentiated",
    "severity": "MEDIUM",
    "task_ids": ["T052", "T053"],
    "dimensions": ["description", "code_section"],
    "rationale": "Both are verification-only tasks for _apply_all_labels (T024). T052 verifies CSV construction, T053 verifies fallback logging. Reclassified from Implementation to Verification in tasks.md — no further action needed."
  }
]
```

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T004, T021, T022, T023, T024, T025 | Well covered |
| FR-002 | ✅ | T026, T027, T028, T029, T069, T070 | Well covered |
| FR-003 | ✅ | T025, T032, T033, T037 | T037 is verification-only |
| FR-004 | ✅ | T006, T011, T034, T035, T036, T038 | Well covered |
| FR-005 | ✅ | T005, T021, T022, T039, T041, T044, T045 | Well covered |
| FR-006 | ✅ | T005, T010, T040, T046 | Well covered |
| FR-007 | ✅ | T015, T016, T022, T023, T024, T048, T050, T052 | Some test overlap (G-01) |
| FR-008 | ✅ | T014, T021, T024, T049 | Well covered |
| FR-009 | ✅ | T054, T055, T056, T057, T059, T060, T061 | Well covered |
| FR-010 | ✅ | T004, T008, T058, T061 | Well covered |
| FR-011 | ✅ | T025, T031, T062, T063, T064 | Some test overlap (G-03, G-04) |
| NFR-001 | ✅ | T047 | Only 45s cap tested, not 15s normal target (SC-004) |
| NFR-002 | ✅ | T006, T011, T034, T035, T036 | Well covered |
| NFR-003 | ✅ | T042, T044, T045 | Well covered |
| NFR-004 | ✅ | T026, T027 | Implicit — uses `secrets.GITHUB_TOKEN` |
| NFR-005 | ✅ | T025, T026, T027 | Well covered |
| SC-001 | ⚠️ | T030, T062 | Operational metric — no post-deployment verification task |
| SC-002 | ✅ | T032, T033 | Covered by stderr visibility tests |
| SC-003 | ⚠️ | — | Statistical metric — no unit test feasible |
| SC-004 | ⚠️ | T047 | Tests 45s cap, not 15s normal target |
| SC-005 | ✅ | T068 | Regression test run |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 16 (11 FR + 5 NFR) |
| Total Tasks | 72 (T001–T072) |
| Coverage % | 100% (all FRs and NFRs have ≥1 task) |
| Ambiguity Count | 2 (B-01, B-02) |
| Requirement Duplication Count (Category A) | 4 (A-01, A-02 LOW; A-03, A-04 MEDIUM) |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 5 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 2 / differentiated: 3 / conflicting: 0 |
| Multi-Task Group Count | 0 (all findings are pairs) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
