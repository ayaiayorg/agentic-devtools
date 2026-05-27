# Tasks: AI PR Loop Review Request Guards and Squash-First Review Strategy

**Feature**: #1617  
**Spec Branch**: `speckit/1617/phase-1-specify`

## Phase Mapping: Plan → Tasks

| Plan Phase (`plan.md`) | Tasks Phase (`tasks.md`) |
|---|---|
| Phase 1: Data Model & Snapshot Extensions (Foundation) | Phase 1: Setup & Scaffolding + Phase 2: Foundational — Data Model & Snapshot Extensions |
| Phase 2: DispatchRepairAction — Repair Marker & DerivedState Flag | Phase 3: User Story 1 — Review Request Blocked During Active Repair |
| Phase 3: RequestReviewAction — New Guards | Phase 3: User Story 1 + Phase 4: User Story 2 + Phase 5: User Story 3 |
| Phase 4: SquashAction — Remove Pending Review Blocker | Phase 6: User Story 4 — Squash Not Blocked by Pending Review |
| Phase 5: Pipeline Reordering | Phase 5: User Story 3 — Squash-First Review Trigger for Multi-Commit PRs |
| Phase 6: MergeAction — Dynamic Strategy | Phase 7: User Story 5 — Squash Merge for Multi-Commit PRs at Merge Time |
| Phase 7: Legacy Orchestrator Alignment | Phase 8: Legacy Orchestrator Alignment |
| Phase 8: Tests | Phase 9: Polish & Cross-Cutting |

## Phase 1: Setup & Scaffolding

- [ ] T001 Create `agentic_devtools/cli/ci/pipeline/commit_message.py` with module docstring and imports
- [ ] T002 Create `tests/unit/cli/ci/pipeline/commit_message/__init__.py` (FR-009)
- [ ] T003 Create `tests/unit/cli/ci/guards/` directory with `__init__.py` (if not exists) (FR-002)

## Phase 2: Foundational — Data Model & Snapshot Extensions

- [ ] T004 Add `total_unresolved_threads: int = 0` field to `PRStateSnapshot` in `agentic_devtools/cli/ci/pipeline/snapshot.py` (preserves existing `unresolved_threads` semantics)
- [ ] T005 Add `REPAIR_DISPATCH_MARKER_PREFIX = "<!-- repair-dispatched-sha:"` constant to `agentic_devtools/cli/ci/guards.py` (distinct from existing `DEDUP_MARKER_PREFIX`)
- [ ] T006 Add `count_total_unresolved_threads` optional method to `CIPlatformProvider` in `agentic_devtools/cli/ci/provider.py` (default returns 0)
- [ ] T007 Implement `count_total_unresolved_threads` in `agentic_devtools/cli/ci/github_provider.py` reusing `list_review_thread_states` GraphQL
- [ ] T008 Call `count_total_unresolved_threads` in `build_pr_state_snapshot` in `agentic_devtools/cli/ci/pipeline/snapshot.py` to populate `total_unresolved_threads`
- [ ] T009 Initialize `derived.set("repair_dispatched", False)` and `derived.set("snapshot_invalidated", False)` at start of `run_pipeline` in `agentic_devtools/cli/ci/pipeline/runner.py`
- [ ] T010 Add repair-dispatch marker read/write helpers (`write_repair_dispatch_marker`, `read_repair_dispatch_marker`) to `agentic_devtools/cli/ci/guards.py`
- [ ] T011 Add `write_repair_dispatch_marker` and `read_repair_dispatch_marker` to `CIPlatformProvider` (optional abstract methods) in `agentic_devtools/cli/ci/provider.py`
- [ ] T012 Implement marker read/write in `agentic_devtools/cli/ci/github_provider.py` using PR comments with `REPAIR_DISPATCH_MARKER_PREFIX`

## Phase 3: User Story 1 — Review Request Blocked During Active Repair (P1)

### Tests (RED)

- [ ] T013 [P] [US1] Write test: `RequestReviewAction` returns SKIP with reason `"repair_dispatched"` when `derived.repair_dispatched == True` —
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-001)
- [ ] T014 [P] [US1] Write test: `RequestReviewAction` returns SKIP with reason `"active_session"` when `snapshot.active_session == True` —
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-002)
- [ ] T015 [P] [US1] Write test: `RequestReviewAction` returns SKIP with reason `"repair_dispatched_prior_run"` when repair marker SHA matches HEAD —
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-002, FR-002a)
- [ ] T016 [P] [US1] Write test: `RequestReviewAction` returns EXECUTE when no repair active and all guards pass — `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-010)
- [ ] T017 [P] [US1] Write test: `DispatchRepairAction.execute()` sets `derived.repair_dispatched = True` after successful dispatch —
  `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_dispatchrepairaction.py` (FR-001)
- [ ] T018 [P] [US1] Write test: `DispatchRepairAction.execute()` writes repair-dispatch marker with HEAD SHA — `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_dispatchrepairaction.py`
  (FR-002, FR-002a)
- [ ] T019 [P] [US1] Write test: repair-dispatch marker helpers parse and write correct format — `tests/unit/cli/ci/guards/test_repair_dispatch_marker.py` (FR-002)

### Implementation (GREEN)

- [ ] T020 [US1] Add `derived.set("repair_dispatched", True)` in `DispatchRepairAction.execute()` after successful dispatch — `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` (FR-001)
- [ ] T021 [US1] Write repair-dispatch marker in `DispatchRepairAction.execute()` after successful dispatch — `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` (FR-002, FR-002a)
- [ ] T022 [US1] Add guard in `RequestReviewAction.evaluate()`: skip if `derived.repair_dispatched == True` with reason `"repair_dispatched"` —
  `agentic_devtools/cli/ci/pipeline/actions/request_review.py` (FR-001, FR-010)
- [ ] T023 [US1] Add guard in `RequestReviewAction.evaluate()`: skip if `snapshot.active_session == True` with reason `"active_session"` — `agentic_devtools/cli/ci/pipeline/actions/request_review.py`
  (FR-002, FR-010)
- [ ] T024 [US1] Add guard in `RequestReviewAction.evaluate()`: read repair-dispatch marker, skip if SHA matches HEAD with reason `"repair_dispatched_prior_run"` —
  `agentic_devtools/cli/ci/pipeline/actions/request_review.py` (FR-002, FR-002a, FR-010)

## Phase 4: User Story 2 — Review Request Blocked When Unresolved Comments Exist (P1)

### Tests (RED)

- [ ] T025 [P] [US2] Write test: `RequestReviewAction` returns SKIP with reason `"unresolved_comments"` when `snapshot.total_unresolved_threads > 0` —
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-003)
- [ ] T026 [P] [US2] Write test: `RequestReviewAction` returns EXECUTE when `total_unresolved_threads == 0` (no blocking) —
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-003)
- [ ] T027 [P] [US2] Write test: `build_pr_state_snapshot` populates `total_unresolved_threads` from provider — `tests/unit/cli/ci/pipeline/snapshot/test_prstatesnapshot.py` (FR-003)
- [ ] T028 [P] [US2] Write test: `count_total_unresolved_threads` returns count from provider — `tests/unit/cli/ci/pipeline/snapshot/test_count_total_unresolved_threads.py` (FR-003)

### Implementation (GREEN)

- [ ] T029 [US2] Add guard in `RequestReviewAction.evaluate()`: skip if `snapshot.total_unresolved_threads > 0` with reason `"unresolved_comments"` —
  `agentic_devtools/cli/ci/pipeline/actions/request_review.py` (FR-003, FR-010)

## Phase 5: User Story 3 — Squash-First Review Trigger for Multi-Commit PRs (P2)

### Tests (RED)

- [ ] T030 [P] [US3] Write test: pipeline runner sets `derived.snapshot_invalidated = True` when action returns `invalidates_snapshot=True` — `tests/unit/cli/ci/pipeline/runner/test_run_pipeline.py`
  (FR-006)
- [ ] T031 [P] [US3] Write test: `RequestReviewAction` returns SKIP with reason `"snapshot_invalidated"` when `derived.snapshot_invalidated == True` —
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-006)
- [ ] T032 [P] [US3] Write test: `RequestReviewAction` returns EXECUTE (fallback) when `SquashAction` is skipped and `derived.snapshot_invalidated == False` —
  `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (FR-007)
- [ ] T033 [P] [US3] Write test: action ordering in `command.py` has `DispatchRepairAction` and `SquashAction` before `RequestReviewAction` —
  `tests/unit/cli/ci/pipeline/command/test_run_ai_pr_loop_v2.py` (FR-006, FR-007)

### Implementation (GREEN)

- [ ] T034 [US3] Update `run_pipeline` to set `derived.set("snapshot_invalidated", True)` when any action returns `invalidates_snapshot=True` — `agentic_devtools/cli/ci/pipeline/runner.py` (FR-006)
- [ ] T035 [US3] Add guard in `RequestReviewAction.evaluate()`: skip if `derived.snapshot_invalidated == True` with reason `"snapshot_invalidated"` —
  `agentic_devtools/cli/ci/pipeline/actions/request_review.py` (FR-006, FR-007, FR-010)
- [ ] T036 [US3] Reorder actions in `run_ai_pr_loop_v2`: move `DispatchRepairAction` and `SquashAction` before `RequestReviewAction` — `agentic_devtools/cli/ci/pipeline/command.py` (FR-006, FR-007)

## Phase 6: User Story 4 — Squash Not Blocked by Pending Review (P2)

### Tests (RED)

- [ ] T037 [P] [US4] Write test: `SquashAction.evaluate()` returns EXECUTE when `copilot_review_pending=True` and `active_session=False` —
  `tests/unit/cli/ci/pipeline/actions/squash/test_squashaction.py` (FR-005)
- [ ] T038 [P] [US4] Write test: `SquashAction.evaluate()` returns SKIP only when `active_session=True` — `tests/unit/cli/ci/pipeline/actions/squash/test_squashaction.py` (FR-005)

### Implementation (GREEN)

- [ ] T039 [US4] Remove `no_pending_review` precondition check from `SquashAction.evaluate()` — `agentic_devtools/cli/ci/pipeline/actions/squash.py` (FR-005)

## Phase 7: User Story 5 — Squash Merge for Multi-Commit PRs at Merge Time (P2)

### Tests (RED)

- [ ] T040 [P] [US5] Write test: `DeterministicCommitMessageGenerator.generate()` builds message from commit subjects —
  `tests/unit/cli/ci/pipeline/commit_message/test_deterministiccommitmessagegenerator.py` (FR-009)
- [ ] T041 [P] [US5] Write test: `MergeAction.execute()` calls `merge_pr` with `"squash"` when `commit_count > 1` — `tests/unit/cli/ci/pipeline/actions/merge/test_mergeaction.py` (FR-008)
- [ ] T042 [P] [US5] Write test: `MergeAction.execute()` calls `merge_pr` with `"rebase"` when `commit_count == 1` — `tests/unit/cli/ci/pipeline/actions/merge/test_mergeaction.py` (FR-008)
- [ ] T043 [P] [US5] Write test: `MergeAction.execute()` falls back to `"rebase"` when `commit_count` is `None` — `tests/unit/cli/ci/pipeline/actions/merge/test_mergeaction.py` (FR-008)
- [ ] T044 [P] [US5] Write test: `CommitMessageGenerator` protocol is satisfied by `DeterministicCommitMessageGenerator` —
  `tests/unit/cli/ci/pipeline/commit_message/test_deterministiccommitmessagegenerator.py` (FR-009)

### Implementation (GREEN)

- [ ] T045 [US5] Implement `CommitMessageGenerator` protocol in `agentic_devtools/cli/ci/pipeline/commit_message.py` (FR-009)
- [ ] T046 [US5] Implement `DeterministicCommitMessageGenerator` using existing `_build_squash_commit_message` logic — `agentic_devtools/cli/ci/pipeline/commit_message.py` (FR-009)
- [ ] T047 [US5] Extend `merge_pr` signature in `CIPlatformProvider` to accept optional `commit_message` param — `agentic_devtools/cli/ci/provider.py` (FR-008)
- [ ] T048 [US5] Update `merge_pr` implementation in `agentic_devtools/cli/ci/github_provider.py` to pass `commit_title`/`commit_message` for squash merges (FR-008)
- [ ] T049 [US5] Modify `MergeAction.execute()` to select strategy based on `snapshot.commit_count` and generate commit message for squash — `agentic_devtools/cli/ci/pipeline/actions/merge.py`
  (FR-008, FR-009)

## Phase 8: Legacy Orchestrator Alignment

### Tests (RED)

- [ ] T050 [P] [US1] Write test: `_request_copilot_review_if_needed` returns skip reason when repair dispatched — `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop.py` (FR-004)
- [ ] T051 [P] [US2] Write test: `_request_copilot_review_if_needed` returns skip reason when unresolved comments exist — `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop.py` (FR-004)

### Implementation (GREEN)

- [ ] T052 [US1] Add repair-dispatch check to `_request_copilot_review_if_needed` in `agentic_devtools/cli/ci/orchestrator.py` (FR-004)
- [ ] T053 [US2] Add unresolved comments check to `_request_copilot_review_if_needed` in `agentic_devtools/cli/ci/orchestrator.py` (FR-004)
- [ ] T054 Add INFO-level structured logging for all new guard decisions in `orchestrator.py` (NFR-002)

## Phase 9: Polish & Cross-Cutting

- [ ] T055 Run full test suite (`agdt-test`) and verify 0 regressions (SC-006) (FR-010)
- [ ] T056 Run `ruff check` and `ruff format` on all modified files
- [ ] T057 Run `bash scripts/run-pr-checks.sh` to validate all CI checks pass (FR-010)
- [ ] T058 Verify 100% branch coverage for all new guard logic (SC-007) (FR-010)
- [ ] T059 Verify action ordering in pipeline summary output matches design (`DispatchRepair` → `Squash` → `RequestReview`) (FR-006, FR-007)

## Dependency Graph

```text
T001-T003 → T004-T012 (setup before foundation)
T004-T012 → T013-T029 (foundation before US1/US2 impl)
T009 → T030-T036 (DerivedState init before snapshot_invalidated tests)
T036 → T037-T039 (reorder before squash blocker removal to avoid test conflicts)
T045-T046 → T049 (protocol before MergeAction uses it)
T047-T048 → T049 (provider signature before MergeAction calls it)
T020-T024 → T050,T052 (pipeline guards before legacy alignment)
T029 → T051,T053 (pipeline guard before legacy alignment)
T013-T054 → T055-T059 (all impl before polish)
```

## FR Traceability Matrix

| FR | Tasks |
|---|---|
| FR-001 | T013, T017, T020, T022, T050, T052 |
| FR-002 | T003, T014, T015, T018, T019, T021, T023, T024 |
| FR-002a | T015, T018, T021, T024 |
| FR-003 | T025, T026, T027, T028, T029, T051, T053 |
| FR-004 | T050, T051, T052, T053 |
| FR-005 | T037, T038, T039 |
| FR-006 | T030, T031, T033, T034, T035, T036, T059 |
| FR-007 | T032, T035, T036 |
| FR-008 | T041, T042, T043, T047, T048, T049 |
| FR-009 | T002, T040, T044, T045, T046, T049 |
| FR-010 | T016, T022, T023, T024, T029, T035, T055, T057, T058 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
