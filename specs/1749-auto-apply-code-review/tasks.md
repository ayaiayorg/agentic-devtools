# Tasks: Auto-apply Code Review Suggestions via GraphQL in AI PR Loop

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create `agentic_devtools/cli/ci/pipeline/exclusion.py` with module docstring and empty file
- [ ] T002 Create `agentic_devtools/cli/ci/pipeline/suggestions.py` with module docstring and empty file
- [ ] T003 Create `agentic_devtools/cli/ci/pipeline/actions/apply_suggestions.py` with module docstring and empty file
- [ ] T004 [P] Create `tests/unit/cli/ci/pipeline/exclusion/__init__.py` directory and init file
- [ ] T005 [P] Create `tests/unit/cli/ci/pipeline/suggestions/__init__.py` directory and init file
- [ ] T006 [P] Create `tests/unit/cli/ci/pipeline/actions/apply_suggestions/__init__.py` directory and init file

---

## Phase 2: Foundational — Core Data Structures & Provider Extension

- [ ] T007 Implement `ExclusionContext` dataclass in `agentic_devtools/cli/ci/pipeline/exclusion.py` with `resolved_comment_ids: set[int]` field (FR-005)
- [ ] T008 [P] Write tests for `ExclusionContext` in `tests/unit/cli/ci/pipeline/exclusion/test_exclusioncontext.py` — construction, empty set, merge behavior
- [ ] T009 Implement `ApplySuggestionsResult` dataclass in `agentic_devtools/cli/ci/pipeline/suggestions.py` with fields: `applied_ids`, `skipped_ids`, `commit_shas`, `error` (FR-002, FR-003)
- [ ] T010 [P] Write tests for `ApplySuggestionsResult` in `tests/unit/cli/ci/pipeline/suggestions/test_applysuggestionsresult.py`
- [ ] T011 Implement `fetch_applicable_suggestions()` in `agentic_devtools/cli/ci/pipeline/suggestions.py` — GraphQL query with pagination, filtering `outdated: false`, unresolved threads only
  (FR-001, FR-004)
- [ ] T012 Write tests for `fetch_applicable_suggestions()` in `tests/unit/cli/ci/pipeline/suggestions/test_fetch_applicable_suggestions.py` — pagination, outdated filtering, empty results
- [ ] T013 Add `fetch_suggestions()` method to `CIPlatformProvider` interface and GitHub provider in `agentic_devtools/cli/ci/github_provider.py` to expose GraphQL suggestion queries
- [ ] T014 [P] Write tests for the new provider method in `tests/unit/cli/ci/github_provider/` covering suggestion node parsing
- [ ] T015 Add runner-scoped context dict to `run_pipeline()` in `agentic_devtools/cli/ci/pipeline/runner.py` that persists across snapshot refresh (pass as param to `execute()` or store on runner)
- [ ] T016 Write tests for runner context persistence across snapshot invalidation in `tests/unit/cli/ci/pipeline/runner/`

---

## Phase 3: User Story 1 — Batch Apply All Autofixable Suggestions (P1)

- [ ] T017 [US1] Write tests for `apply_suggestions_batch()` in `tests/unit/cli/ci/pipeline/suggestions/test_apply_suggestions_batch.py` — success path producing single commit, commit SHA extraction
  (FR-002, FR-008)
- [ ] T018 [US1] Implement `apply_suggestions_batch()` in `agentic_devtools/cli/ci/pipeline/suggestions.py` — single `applySuggestedChanges` mutation call via provider, returns commit SHA; commit
  attributed to bot PAT user (FR-002, FR-008)
- [ ] T019 [US1] Add `apply_suggested_changes()` method to GitHub provider in `agentic_devtools/cli/ci/github_provider.py` wrapping the GraphQL mutation
- [ ] T020 [US1] Write tests for `apply_suggested_changes()` provider method — success, error responses
- [ ] T021 [US1] Write tests for `ApplySuggestionsAction.evaluate()` in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_evaluate.py` — applicable suggestions exist, count ≤ 50 threshold
  (FR-011), zero suggestions → SKIP
- [ ] T022 [US1] Implement `ApplySuggestionsAction.evaluate()` in `agentic_devtools/cli/ci/pipeline/actions/apply_suggestions.py` — checks suggestion count, threshold FR-011, returns EXECUTE or SKIP
- [ ] T023 [US1] Write tests for `ApplySuggestionsAction.execute()` in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_execute.py` — successful batch apply, `invalidates_snapshot=True`
  (FR-012), exclusion context population (FR-005)
- [ ] T024 [US1] Implement `ApplySuggestionsAction.execute()` — calls batch apply, sets `invalidates_snapshot=True` on `ActionResult` (FR-012), populates `ExclusionContext` with parent review comment
  `databaseId` values in runner context (FR-005), commit attributed to bot PAT (FR-008)
- [ ] T025 [US1] Export `ApplySuggestionsAction` in `agentic_devtools/cli/ci/pipeline/actions/__init__.py`
- [ ] T026 [US1] Insert `ApplySuggestionsAction` into pipeline sequence in `agentic_devtools/cli/ci/pipeline/command.py` after `PublishAction` and before `DispatchRepairAction` (FR-009, FR-007)
- [ ] T027 [US1] Write integration test verifying pipeline ordering (Guards → Publish → ApplySuggestions → DispatchRepair → ...) in
  `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_integration.py`

---

## Phase 4: User Story 2 — Graceful Fallback on Partial Application Failure (P1)

- [ ] T028 [US2] Write tests for `apply_suggestions_with_bisection()` in `tests/unit/cli/ci/pipeline/suggestions/test_apply_suggestions_with_bisection.py` — conflict detection, recursive subdivision,
  partial success
- [ ] T029 [US2] Implement `apply_suggestions_with_bisection()` in `agentic_devtools/cli/ci/pipeline/suggestions.py` — recursive bisection with max depth of 4, error classification (conflict vs
  transient vs fatal) (FR-003)
- [ ] T030 [US2] Write tests for retry logic with exponential backoff on transient errors in `tests/unit/cli/ci/pipeline/suggestions/test_retry_logic.py` — uses `retry_with_backoff` defaults (FR-010)
- [ ] T031 [US2] Integrate retry logic (`retry_with_backoff`, `max_retries=5`, `initial_delay=1s`) into mutation calls in `agentic_devtools/cli/ci/pipeline/suggestions.py`; on exhausted retries return
  SKIP not FAILED (FR-010)
- [ ] T032 [US2] Write tests for `execute()` bisection fallback path in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_execute_bisection.py` — partial apply records multiple `commit_shas`
- [ ] T033 [US2] Update `ApplySuggestionsAction.execute()` to invoke bisection fallback when batch fails with conflict error, capturing all commit SHAs (FR-003)
- [ ] T034 [US2] Write test for single conflicting suggestion edge case (bisection degrades to no-op) in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_edge_cases.py`

---

## Phase 5: User Story 3 — Exclusion of Applied Suggestions from Repair Dispatch (P2)

- [ ] T035 [US3] Write tests for `DispatchRepairAction` reading `ExclusionContext` and filtering `review_comments` in `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_exclusion_filtering.py`
- [ ] T036 [US3] Add `runs_after_invalidation = True` attribute to `DispatchRepairAction` in `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` (FR-013)
- [ ] T037 [US3] Modify `DispatchRepairAction.execute()` to read `ExclusionContext` from runner-scoped context and filter excluded comment IDs from `review_comments` list (FR-005, FR-006)
- [ ] T038 [US3] Write test verifying `DispatchRepairAction` returns SKIP when all review comments are excluded and CI is passing (FR-006)
- [ ] T039 [US3] Write test verifying `needs_repair` re-evaluation after exclusion — remaining comments still trigger repair dispatch with correct `repair_type`

---

## Phase 6: User Story 4 — Safety Guards for Privileged Paths and Forks (P2)

- [ ] T040 [US4] Write tests for guard-blocking behavior on fork PRs in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_guards.py`
- [ ] T041 [US4] Write tests for guard-blocking on privileged path PRs (`.github/workflows/`) in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_guards.py`
- [ ] T042 [US4] Verify `ApplySuggestionsAction` placement after `GuardsAction` ensures `BLOCKED_BY_GUARD` propagation (FR-007) — integration test in
  `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_integration.py`

---

## Phase 7: User Story 5 — Summary Comment for Transparency (P3)

- [ ] T043 [US5] Write tests for summary comment formatting in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_summary_comment.py` — all applied, partial with skipped, format validation
- [ ] T044 [US5] Implement summary comment posting in `ApplySuggestionsAction.execute()` in `agentic_devtools/cli/ci/pipeline/actions/apply_suggestions.py` — format: "🔧 **Auto-applied N suggestions**
  in commit `sha`..." with applied/skipped lists
- [ ] T045 [US5] Write test verifying no comment is posted when zero suggestions are applied (SKIP path)

---

## Phase 8: Polish & Cross-Cutting — Integration Tests & Edge Cases

- [ ] T046 Write integration test: all suggestions applied → no repair dispatch (end-to-end pipeline with mocked provider) in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_integration.py`
- [ ] T047 Write integration test: partial apply with bisection → repair dispatched with `ExclusionContext` exclusions
- [ ] T048 Write test: threshold exceeded (>50 suggestions) → SKIP with warning log (FR-011) in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_edge_cases.py`
- [ ] T049 Write test: transient error exhausted after retries → SKIP (not FAILED) in `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_edge_cases.py`
- [ ] T050 Write test: deleted file reference → suggestion excluded as outdated with reason logged in `tests/unit/cli/ci/pipeline/suggestions/test_fetch_applicable_suggestions.py`
- [ ] T051 Write test: bisection producing multiple commits → all SHAs captured in `ApplySuggestionsResult.commit_shas`
- [ ] T052 Write test: concurrent loop deduplication — second instance sees already-resolved suggestions as no-ops
- [ ] T053 Add `apply_suggestions` to `side_effect_actions` set in `_determine_exit_code()` in `agentic_devtools/cli/ci/pipeline/command.py`
- [ ] T054 Validate NFR-003 compliance: verify `ActionResult` fields (`preconditions`, `details`, `decision`) are populated for all action paths
- [ ] T055 Run full test suite with `agdt-test` and verify 100% branch coverage on new modules via `agdt-test-file`
- [ ] T056 Run `bash scripts/targeted-checks.sh` to validate linting, formatting, mypy, and test structure

---

## Dependencies

| Task | Depends On |
|------|-----------|
| T007 | T001 |
| T009 | T002 |
| T011 | T009, T013 |
| T015 | — |
| T017 | T009, T010 |
| T018 | T017, T019 |
| T021 | T011, T012 |
| T022 | T021 |
| T023 | T018, T022 |
| T024 | T023, T015 |
| T025 | T024 |
| T026 | T025 |
| T027 | T026 |
| T028 | T018 |
| T029 | T028 |
| T031 | T030 |
| T033 | T029, T032 |
| T035 | T024 |
| T036 | T035 |
| T037 | T036, T007 |
| T038 | T037 |
| T040 | T026 |
| T043 | T024 |
| T044 | T043 |
| T046 | T026, T037 |
| T047 | T033, T037 |
| T053 | T026 |
| T055 | T054 |
| T056 | T055 |

---

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T011, T012 |
| FR-002 | T009, T017, T018 |
| FR-003 | T028, T029, T033 |
| FR-004 | T011, T012 |
| FR-005 | T007, T008, T023, T024, T035, T037 |
| FR-006 | T037, T038 |
| FR-007 | T026, T042 |
| FR-008 | T017, T018, T024 |
| FR-009 | T026, T027 |
| FR-010 | T030, T031, T049 |
| FR-011 | T021, T022, T048 |
| FR-012 | T023, T024 |
| FR-013 | T036 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
