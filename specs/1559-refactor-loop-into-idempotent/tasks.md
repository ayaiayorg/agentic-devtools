# Tasks: Idempotent Action Evaluator for AI PR Loop

## Phase Mapping: Plan → Tasks

Plan phases and task phases do not align 1:1 in this spec. The task plan expands the implementation into more granular execution phases. Use the mapping below when tracing tasks back to `plan.md`.

| Plan phase | Task phases |
| --- | --- |
| Phase 1 | Phase 1 |
| Phase 2 | Phase 2 |
| Phase 3 | Phases 3–4 |
| Phase 4 | Phases 5–7 |
| Phase 5 | Phases 8–10 |

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create package directory `agentic_devtools/cli/ci/pipeline/` with `__init__.py`
- [ ] T002 [US1] Create test package directory `tests/unit/cli/ci/pipeline/` with `__init__.py`, plus `__init__.py` files for `tests/unit/cli/ci/pipeline/models/`,
  `tests/unit/cli/ci/pipeline/snapshot/`, `tests/unit/cli/ci/pipeline/runner/`, `tests/unit/cli/ci/pipeline/session_detector/`,
  `tests/unit/cli/ci/pipeline/actions/`, and `tests/unit/cli/ci/pipeline/summary/`
- [ ] T003 [US1] Create per-action test package subdirectories under `tests/unit/cli/ci/pipeline/actions/`, each with `__init__.py`: `guards/`, `publish/`,
  `request_review/`, `resolve_threads/`, `dispatch_repair/`, `squash/`, `approve/`, `merge/`

## Phase 2: Foundational — Core Types & Infrastructure

- [ ] T004 Define `ActionDecision` enum (`EXECUTE`, `SKIP`, `BLOCKED`, `BLOCKED_BY_GUARD`, `FAILED`) in `agentic_devtools/cli/ci/pipeline/models.py`
- [ ] T005 Define `ActionResult` dataclass (name, decision, preconditions dict, details, error) in `agentic_devtools/cli/ci/pipeline/models.py`
- [ ] T006 Define `PipelineRunSummary` dataclass (results list, snapshot, run_url, timestamp) in `agentic_devtools/cli/ci/pipeline/models.py`
- [ ] T007 [P] (FR-011) Write tests for `ActionDecision`, `ActionResult`, `PipelineRunSummary` in `tests/unit/cli/ci/pipeline/models/`
- [ ] T008 Define `PRStateSnapshot` frozen dataclass (FR-011: head_sha, commit_count, ci_status, review_state, active_session, unresolved_threads, labels, is_draft, mergeable, requested_reviewers,
  approval_on_head) in `agentic_devtools/cli/ci/pipeline/snapshot.py`
- [ ] T009 Define `DerivedState` mutable proxy class with `__getattr__` fallthrough to snapshot (FR-011) in `agentic_devtools/cli/ci/pipeline/snapshot.py`
- [ ] T010 Implement `build_pr_state_snapshot()` function that gathers all PR state in one pass via provider (FR-011) in `agentic_devtools/cli/ci/pipeline/snapshot.py`
- [ ] T011 [P] Write tests for snapshot types and snapshot creation behavior (FR-011) in `tests/unit/cli/ci/pipeline/snapshot/`
- [ ] T012 Define `Action` protocol (name, evaluate, execute) in `agentic_devtools/cli/ci/pipeline/base.py`
- [ ] T013 Implement `run_pipeline()` with try/except per action, guard-blocking logic (FR-001, FR-014, NFR-003), and `::group::`/`::endgroup::` logging (FR-009, NFR-006) in
  `agentic_devtools/cli/ci/pipeline/runner.py`
- [ ] T014 [P] Write tests for `run_pipeline()` covering: happy path normal flow, guard block,
  action exception isolation, structured logging (FR-001, FR-014, NFR-003, FR-009, NFR-006) in
  `tests/unit/cli/ci/pipeline/runner/`
- [ ] T015 Implement `is_copilot_session_active()` using Issues Events API with full pagination and ID-based ordering (FR-003) in `agentic_devtools/cli/ci/pipeline/session_detector.py`
- [ ] T016 [US2] [P] Write tests for `is_copilot_session_active()` covering: happy path active session success, finished session, failure terminal event, no events, out-of-order events in
  `tests/unit/cli/ci/pipeline/session_detector/`

## Phase 3: User Story 1 — Idempotent Pipeline Execution (P1)

- [ ] T017 [US1] Implement `GuardsAction` reusing existing guard functions, returning BLOCKED with reason on failure, fail-closed on exception (FR-001, FR-014) in
  `agentic_devtools/cli/ci/pipeline/actions/guards.py`
- [ ] T018 [US1] [P] Write tests for `GuardsAction` covering: happy path all guards pass, fork block, exclusion label block, exception fail-closed in `tests/unit/cli/ci/pipeline/actions/guards/`
- [ ] T019 [US1] Implement `PublishAction` with precondition `is_draft == True`, skip if not draft, update DerivedState on execute (FR-001, FR-002) in
  `agentic_devtools/cli/ci/pipeline/actions/publish.py`
- [ ] T020 [US1] [P] Write tests for `PublishAction` covering: happy path draft→publish success, already published skip, DerivedState update in `tests/unit/cli/ci/pipeline/actions/publish/`
- [ ] T021 [US1] Implement `RequestReviewAction` with preconditions: not draft (DerivedState), no effective review on HEAD, not already requested (FR-001, FR-002) in
  `agentic_devtools/cli/ci/pipeline/actions/request_review.py`
- [ ] T022 [US1] [P] Write tests for `RequestReviewAction` covering: execute, skip already-reviewed, skip already-requested in `tests/unit/cli/ci/pipeline/actions/request_review/`
- [ ] T023 [US1] Implement `ResolveThreadsAction` with preconditions: no active session, no pending review on HEAD, unresolved threads exist (FR-001, FR-002, FR-004, FR-005) in
  `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`
- [ ] T024 [US1] [P] Write tests for `ResolveThreadsAction` covering: resolve eligible threads, skip when active session, skip when no threads in `tests/unit/cli/ci/pipeline/actions/resolve_threads/`
- [ ] T025 [US1] Implement `DispatchRepairAction` with preconditions: no active session, CI failed OR actionable review, dedup/cycle limits (FR-001, FR-002, FR-013) in
  `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py`
- [ ] T026 [US1] [P] Write tests for `DispatchRepairAction` covering: dispatch on CI failure, skip when limits exceeded, skip when session active in
  `tests/unit/cli/ci/pipeline/actions/dispatch_repair/`
- [ ] T027 [US1] Implement `SquashAction` with preconditions: commits > 1, no active session, CI passing (FR-001, FR-002, FR-006) in `agentic_devtools/cli/ci/pipeline/actions/squash.py`
- [ ] T028 [US1] [P] Write tests for `SquashAction` covering: squash when >1 commit, skip when 1 commit, skip when session active in `tests/unit/cli/ci/pipeline/actions/squash/`
- [ ] T029 [US1] Implement `ApproveAction` with preconditions: no approval on current HEAD SHA, clean Copilot review, CI passing, no unresolved threads (FR-001, FR-002, FR-012) in
  `agentic_devtools/cli/ci/pipeline/actions/approve.py`
- [ ] T030 [US1] [P] Write tests for `ApproveAction` covering: approve when eligible, skip when already approved on HEAD, skip when threads open in `tests/unit/cli/ci/pipeline/actions/approve/`
- [ ] T031 [US1] Implement `MergeAction` with preconditions: approved, CI passing, label present, mergeable, no unresolved threads (FR-001, FR-002, FR-007) in
  `agentic_devtools/cli/ci/pipeline/actions/merge.py`
- [ ] T032 [US1] [P] Write tests for `MergeAction` covering: merge when all conditions met, skip each missing condition individually in `tests/unit/cli/ci/pipeline/actions/merge/`
- [ ] T033 [US1] Write idempotency integration test: run pipeline twice on unchanged state → 0 duplicate API calls (FR-002) in `tests/unit/cli/ci/pipeline/runner/test_idempotency.py`
- [ ] T034 [US1] Write test verifying all 8 actions evaluated regardless of trigger type (FR-001) in `tests/unit/cli/ci/pipeline/runner/test_trigger_agnostic.py`

## Phase 4: User Story 2 — Active Session Detection Replaces Squash-Wait (P1)

- [ ] T035 [US2] Integrate `is_copilot_session_active()` (FR-003) into resolve-threads, dispatch-repair, and squash action preconditions in their respective action files
- [ ] T036 [US2] [P] Write tests verifying actions 4, 5, 6 skip when session active and proceed when session finished (FR-003, FR-005, FR-006) in `tests/unit/cli/ci/pipeline/actions/`
- [ ] T037 [US2] Remove squash-wait state machine: delete `read_squash_wait_marker`, `write_squash_wait_marker`, `delete_squash_wait_marker`, `_build_squash_wait_body`, `SQUASH_WAIT_MARKER_PREFIX`,
  `SQUASH_WAIT_MAX_ATTEMPTS` from `agentic_devtools/cli/ci/guards.py` (FR-010)
- [ ] T038 [US2] Remove `_run_squash_wait_step()` and squash-wait event-branching logic from `agentic_devtools/cli/ci/orchestrator.py` (FR-010)
- [ ] T039 [US2] Delete `tests/unit/cli/ci/guards/test_squash_wait_marker.py` (FR-010)
- [ ] T040 [US2] [P] Write test verifying zero references to squash-wait markers in production code under `agentic_devtools/` (FR-010) in `tests/unit/cli/ci/pipeline/`

## Phase 5: User Story 3 — Thread Resolution on Every Trigger (P1)

- [ ] T041 [US3] Implement SDK verification logic within `ResolveThreadsAction.execute()` for per-comment resolve/keep-open verdicts from prior commits (FR-004) in
  `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`
- [ ] T042 [US3] Ensure resolve-threads checks both active coding session AND pending review on HEAD as skip conditions (FR-005) in `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`
- [ ] T043 [US3] [P] Write tests for `ResolveThreadsAction` happy path success: thread resolution
  executing on all trigger types (`issue_comment`, `workflow_run`, `pull_request_review`) with
  identical results (FR-004, FR-005) in `tests/unit/cli/ci/pipeline/actions/resolve_threads/`
- [ ] T044 [US3] [P] Write test for skip when 0 unresolved threads (FR-004) in `tests/unit/cli/ci/pipeline/actions/resolve_threads/test_skip_no_threads.py`

## Phase 6: User Story 4 — Observability Comment on Every Run (P2)

- [ ] T045 [US4] Implement `render_summary_comment()` generating markdown table from `PipelineRunSummary` with sentinel line, action table, and collapsed state snapshot (FR-008, NFR-002) in
  `agentic_devtools/cli/ci/pipeline/summary.py`
- [ ] T046 [US4] Implement `collapse_prior_summaries()` that finds comments with
  `<!-- agdt:ai-pr-loop-summary -->` sentinel and collapses into `<details>` blocks,
  replacing sentinel with `<!-- agdt:ai-pr-loop-summary-collapsed -->` (FR-008) in
  `agentic_devtools/cli/ci/pipeline/summary_collapse.py`
- [ ] T047 [US4] Implement `post_summary_comment()` that posts new comment and collapses prior ones, with graceful failure handling (FR-008) in `agentic_devtools/cli/ci/pipeline/summary.py`
- [ ] T048 [US4] [P] Write tests for `render_summary_comment()` covering: all actions table, guard-blocked rendering, < 2000 char visible limit (FR-008, NFR-002) in
  `tests/unit/cli/ci/pipeline/summary/`
- [ ] T049 [US4] [P] Write tests for `collapse_prior_summaries()` covering: collapse existing, skip already-collapsed, no prior comments (FR-008) in `tests/unit/cli/ci/pipeline/summary/`
- [ ] T050 [US4] [P] Write test for summary post failure not failing pipeline (NFR-003) in `tests/unit/cli/ci/pipeline/summary/test_post_failure_resilience.py`
- [ ] T051 [US4] Integrate summary posting into `run_pipeline()` return path in `agentic_devtools/cli/ci/pipeline/runner.py`

## Phase 7: User Story 5 — Detailed Workflow Run Logging (P2)

- [ ] T052 [US5] Implement structured logging per action with `::group::`/`::endgroup::`, input data, precondition booleans, and decision reasoning (FR-009, NFR-006) in
  `agentic_devtools/cli/ci/pipeline/runner.py`
- [ ] T053 [US5] Ensure skipped actions log the specific precondition that caused skip with input values (FR-009) in each action's `evaluate()` method
- [ ] T054 [US5] Ensure executed actions log API response status and relevant response data (FR-009) in each action's `execute()` method
- [ ] T055 [US5] [P] Write tests verifying structured log output format for executed, skipped, and failed actions (FR-009, NFR-006) in `tests/unit/cli/ci/pipeline/runner/test_logging.py`

## Phase 8: User Story 6 — Fully Automated Merge (P3)

- [ ] T056 [US6] Implement `ApproveAction` HEAD SHA verification ensuring approval targets current commit not prior (FR-012) in `agentic_devtools/cli/ci/pipeline/actions/approve.py`
- [ ] T057 [US6] Implement `MergeAction` re-validation of "PR still open" before execution to handle external merges (FR-007) in `agentic_devtools/cli/ci/pipeline/actions/merge.py`
- [ ] T058 [US6] Implement cycle/deduplication limit checks within `DispatchRepairAction` preconditions (FR-013) in `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py`
- [ ] T059 [US6] [P] Write end-to-end test: draft → published → reviewed → approved → merged in ≤ 5 triggers (FR-007, FR-012, FR-013) in `tests/unit/cli/ci/pipeline/runner/test_full_lifecycle.py`

## Phase 9: Integration & Migration

- [ ] T060 Create `run_ai_pr_loop_v2()` entry point maintaining same signature as current `run_ai_pr_loop()` in `agentic_devtools/cli/ci/pipeline/command.py`
- [ ] T061 Update `agentic_devtools/cli/ci/commands.py` to call new pipeline entry point
- [ ] T062 Convert `agentic_devtools/cli/ci/orchestrator.py` to thin compatibility shim delegating to pipeline
- [ ] T063 Verify backward compatibility with `EventPayload`, `PRMetadata`, `ReviewInfo` dataclasses (NFR-005, FR-001)
- [ ] T064 Migrate existing tests in `tests/unit/cli/ci/orchestrator/` to cover new pipeline architecture (NFR-004, FR-001)
- [ ] T065 [P] Write concurrent-run detection test: lock held → clean exit with summary note in `tests/unit/cli/ci/pipeline/runner/test_concurrent_lock.py` (FR-001)

## Phase 10: Polish & Cross-Cutting

- [ ] T066 Run full test suite (`agdt-test && agdt-task-wait`) and verify 100% coverage on all
  modified files (NFR-004, FR-001); alternatively run `bash scripts/run-pr-checks.sh` for the
  complete pre-PR check suite
- [ ] T067 Verify zero references to squash-wait markers in all production files under `agentic_devtools/` (FR-010, SC-003)
- [ ] T068 Validate single pipeline run completes < 120 seconds under normal conditions (NFR-001, FR-001)
- [ ] T069 Write integration test: 50 consecutive runs on unchanged state → 0 duplicate API calls (SC-001, FR-002)
- [ ] T070 Write integration test: 3 trigger types produce identical evaluations (SC-002, FR-001)
- [ ] T071 Run `ruff check` and `ruff format` on all new files
- [ ] T072 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 compliance (FR-001)
- [ ] T073 Update module docstrings and inline comments for new pipeline package

## Dependencies

```text
T001 → T002, T003 (directories must exist before files)
T004–T006 → T007 (models before model tests)
T008–T010 → T011 (snapshot before snapshot tests)
T012 → T013 (protocol before runner)
T013 → T014 (runner before runner tests)
T015 → T016 (session detector before its tests)
T008, T009, T012, T013, T015 → T017–T034 (foundation before actions)
T017–T034 → T035–T040 (actions before session integration)
T023–T024 → T041–T044 (resolve-threads action before SDK verification)
T013, T017–T032 → T045–T051 (pipeline before summary)
T013 → T052–T055 (runner before logging)
T029, T031, T025 → T056–T059 (approve/merge/repair before lifecycle)
T017–T051 → T060–T065 (all actions + summary before integration)
T060–T065 → T066–T073 (integration before polish)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
