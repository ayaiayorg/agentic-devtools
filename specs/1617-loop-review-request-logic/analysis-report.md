# Analysis Report: AI PR Loop Review Request Guards and Squash-First Review Strategy

## Findings Table

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-01 | F | HIGH | FR-006, Plan Phase 5, `runner.py:107-120` | **Snapshot invalidation mechanism conflict**: FR-006 requires `RequestReviewAction` to check `derived.snapshot_invalidated`, but the existing `run_pipeline` runner halts ALL subsequent actions via local `snapshot_invalidated_by` variable. If `SquashAction` precedes `RequestReviewAction` in the reordered pipeline, the runner's halt mechanism will auto-SKIP `RequestReviewAction` before it can evaluate its own guard. Plan Phase 5 proposes both mechanisms simultaneously without clarifying whether the existing halt is removed, modified, or coexists with the derived flag. | Clarify whether `run_pipeline`'s existing halt-on-invalidation behavior is preserved (making FR-006's guard redundant) or replaced by the `DerivedState` flag approach. If both coexist, document which mechanism produces the `reason="snapshot_invalidated"` output required by FR-010. |
| F-02 | F | MEDIUM | FR-010, `orchestrator.py:1191`, spec | **Terminology drift: "reason" vs "decision"**: FR-010 requires `"reason"` field in decision summary JSON (e.g., `"reason": "repair_active"`). Legacy orchestrator uses `summary["decision"]` key (line 1191: `summary["decision"] = "repair_dispatched"`). The pipeline path uses `ActionResult.details` string. Neither matches the specified `"reason"` field name. | Standardize the field name. Either update FR-010 to use `"decision"` (matching legacy) or specify that the pipeline path introduces `"reason"` as a new field in ActionResult (clarify schema). |
| F-03 | B | MEDIUM | FR-009 | **Ambiguous "stubbed behind an interface"**: FR-009 says the `CommitMessageGenerator` protocol SHOULD be stubbed for future SDK integration but implementation uses deterministic fallback exclusively. "Stubbed" is vague — does this mean a factory method, a config-driven selection, or just the protocol existing? | Replace "stubbed" with concrete requirement: "The `CommitMessageGenerator` protocol MUST be defined as a runtime_checkable Protocol; no SDK implementation class is required in this phase." |
| F-04 | C | MEDIUM | NFR-001, FR-003, Plan Phase 1 | **Underspecified API call budget for `total_unresolved_threads`**: NFR-001 allows max 1 additional API call, but the plan notes `list_review_thread_states` "may paginate (1+ GraphQL requests) on PRs with many threads." Spec does not define behavior when the thread count query exceeds 1 API call (fail? truncate? ignore budget?). | Add explicit edge case: "If the GraphQL query for `total_unresolved_threads` requires pagination beyond 1 request, the implementation MAY fetch only the first page and use its count (conservative overcount is acceptable)." |
| F-05 | F | MEDIUM | Plan Phase 5, `command.py:87-95` | **Current action order differs from plan's "before" state**: Plan states "`RequestReviewAction` runs earlier" than `DispatchRepairAction`/`SquashAction`. Actual current order is: Guards→Publish→**RequestReview**→ResolveThreads→**DispatchRepair**→**Squash**→Approve→Merge. The plan's proposed reorder is correct but the current pipeline also has `ResolveThreads` between RequestReview and DispatchRepair, which the plan's new order moves AFTER RequestReview. This ResolveThreads repositioning is not discussed. | Document explicitly that `ResolveThreadsAction` is also being repositioned (from position 4 to position 6) and confirm this has no semantic impact on the new guard logic. |
| F-06 | C | LOW | Edge Cases, FR-011 | **Stale repair timeout not specified**: Edge case mentions "existing squash-wait timeout mechanism" for stale repairs but does not specify what timeout value applies or where it is configured. The repair-dispatch marker has no TTL. | Add a clarifying note: either specify a TTL on the repair-dispatch marker or explicitly state that no timeout exists (repair suppression persists until HEAD changes or marker is manually cleared). |
| F-07 | B | LOW | SC-009 | **"p95" latency target without measurement method**: SC-009 requires `RequestReviewAction.evaluate()` to remain under 500ms (p95) but does not specify how this is measured (unit test timing? production telemetry? CI benchmark?). | Clarify measurement: "Verified via unit test execution time assertions OR production telemetry when available." |
| F-08 | D | LOW | Spec | **No explicit "Out of Scope" section**: The spec mentions items that are out of scope (SDK integration, non-deterministic commit messages) inline but lacks a consolidated "Out of Scope" section. This is a common constitution-mandated section for feature specs. | Add a brief "## Out of Scope" section consolidating the deferred items (Copilot SDK commit messages, non-GitHub providers, thread resolution automation). |

## Coverage Summary Table

| Requirement Key | Has Task? | Task IDs | Notes |
|----------------|-----------|----------|-------|
| FR-001 | ✅ | T013, T017, T020, T022, T050, T052 | Well covered with tests and implementation |
| FR-002 | ✅ | T003, T014, T015, T018, T019, T021, T023, T024 | Well covered |
| FR-003 | ✅ | T025, T026, T027, T028, T029, T051, T053 | Well covered |
| FR-004 | ✅ | T050, T051, T052, T053 | Legacy path alignment |
| FR-005 | ✅ | T037, T038, T039 | Concise and sufficient |
| FR-006 | ✅ | T030, T031, T033, T034, T035, T036, T059 | Well covered (but see F-01 re: mechanism conflict) |
| FR-007 | ✅ | T032, T035, T036 | Covered as fallback path |
| FR-008 | ✅ | T041, T042, T043, T047, T048, T049 | Well covered including None fallback |
| FR-009 | ✅ | T002, T040, T044, T045, T046, T049 | Protocol + implementation |
| FR-010 | ✅ | T016, T022, T023, T024, T029, T035, T055, T057, T058 | Broad coverage across all skip reasons |
| FR-011 | ✅ | T015, T018, T021, T024 | Cross-run marker path |
| NFR-001 | ✅ | T008 (implicit) | Covered by snapshot build integration |
| NFR-002 | ✅ | T054 | Explicit logging task |
| NFR-003 | ✅ | T050-T053 | Legacy orchestrator alignment |
| NFR-004 | ✅ | T013-T019, T025-T028, T030-T033, T037-T038, T040-T044, T050-T051 | Extensive TDD tasks |

## Metrics

| Metric | Value |
|--------|-------|
| Total Requirements | 15 (11 FR + 4 NFR) |
| Total Tasks | 59 |
| Coverage % | 100% |
| Ambiguity Count | 2 (F-03, F-07) |
| Requirement Duplication Count (Category A) | 0 |
| Critical Issues Count | 0 |
| Task Deduplication Finding Count | 0 |
| Task Deduplication by Type | duplicate: 0 / overlapping: 0 / conflicting: 0 |
| Multi-Task Group Count | 0 |

## Next Actions

- Resolve **F-01** and **F-02** before implementation to prevent conflicting guard semantics and decision payload mismatches.
- Clarify **F-03**, **F-04**, and **F-05** in spec/plan text to remove ambiguity and align ordering assumptions.
- Optionally address low-severity findings (**F-06** to **F-08**) for stronger operability and spec hygiene.

Would you like me to suggest concrete remediation edits for the top findings (F-01 through F-05)?

---
*Generated by Copilot SDK (claude-opus-4.6)*
