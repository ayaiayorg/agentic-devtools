# Tasks: RebaseAction for Stale Single-Commit PRs

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Test scaffolding and shared exception definitions |
| Phase 2: Foundational — Snapshot & Provider Extensions | Phase 1, Phase 2 | Snapshot scope extension plus provider rebase primitives from plan phases 1 and 2 |
| Phase 3: User Story 1 | Phase 3 | `RebaseAction` implementation and core behavior tests |
| Phase 4: User Story 2 | Phase 4 | Pipeline integration and re-validation flow |
| Phase 5: User Story 3 | Phase 4 | Post-rebase review behavior verification |
| Phase 6: User Story 4 | Phase 2 | Rebase conflict-handling test coverage |
| Phase 7: ADO Provider Stub & Integration | Phase 4, Phase 5 | ADO provider stubs plus integration ordering checks |
| Final Phase: Polish & Cross-Cutting | All phases | Final quality gates and regression validation |

## Phase 1: Setup

- [ ] T001 Create test directory structure `tests/unit/cli/ci/pipeline/actions/rebase/__init__.py` and parent `__init__.py` files (supporting FR-001)
- [ ] T002 Create exceptions module `agentic_devtools/cli/ci/pipeline/exceptions.py` with `RebaseConflictError` and `ForceWithLeaseError` exception classes

## Phase 2: Foundational — Snapshot & Provider Extensions

- [ ] T003 Write failing tests for `commits_behind` field on `PRStateSnapshot` verifying FR-001/FR-003 in `tests/unit/cli/ci/pipeline/snapshot/test_prstatesnapshot.py`
- [ ] T004 Add `commits_behind: int = 0` field to `PRStateSnapshot` frozen dataclass in `agentic_devtools/cli/ci/pipeline/snapshot.py` (supports FR-001, FR-003)
- [ ] T005 Write failing tests for `count_commits_behind` method on `CIPlatformProvider` verifying FR-001/FR-003 in `tests/unit/cli/ci/provider/test_count_commits_behind.py`
- [ ] T006 Add `count_commits_behind(pr_number: int, base_branch: str, head_branch: str) -> int` non-abstract method (default returns 0) to `CIPlatformProvider` in
  `agentic_devtools/cli/ci/provider.py`
- [ ] T007 Write failing tests for `GitHubProvider.count_commits_behind` using GitHub compare API verifying FR-001/FR-003 in `tests/unit/cli/ci/github_provider/test_count_commits_behind.py`
- [ ] T008 Implement `count_commits_behind` in `GitHubProvider` using `gh api /repos/{owner}/{repo}/compare/{base}...{head}` → `behind_by` field in `agentic_devtools/cli/ci/github_provider.py`
- [ ] T009 Write failing tests for `commits_behind` population in the `snapshot.py` factory function verifying FR-001/FR-003 in `tests/unit/cli/ci/pipeline/snapshot/test_snapshot_factory.py`
- [ ] T010 Populate `commits_behind` field in `build_pr_state_snapshot()` by calling `provider.count_commits_behind()` in `agentic_devtools/cli/ci/pipeline/snapshot.py`
- [ ] T011 Write failing tests for `rebase_onto_base` abstract method on `CIPlatformProvider` verifying FR-005/FR-006/FR-009 in `tests/unit/cli/ci/provider/test_rebase_onto_base.py`
- [ ] T012 Add `rebase_onto_base(*, pr_number: int, base_branch: str, head_branch: str, head_sha: str) -> None` as abstract method on `CIPlatformProvider` in `agentic_devtools/cli/ci/provider.py`
  (supports FR-005, FR-006, FR-009)
- [ ] T013 Write failing tests for `GitHubProvider.rebase_onto_base` covering success, conflict resolution, abort, and force-push-with-lease failure verifying FR-005/FR-006/FR-009 in
  `tests/unit/cli/ci/github_provider/test_rebase_onto_base.py`
- [ ] T014 Implement `rebase_onto_base` in `GitHubProvider` with fetch, checkout, rebase, `_resolve_rebase_conflicts_via_sdk` on conflict, `git rebase --abort` on failed resolution, and
  `--force-with-lease` push in `agentic_devtools/cli/ci/github_provider.py` (implements FR-005 force-with-lease, FR-006 conflict resolution + abort, FR-009 base branch respect)

## Phase 3: User Story 1 — Single-Commit PR Rebased After Sibling Merge (P1)

- [ ] T015 [US1] Write failing test: `RebaseAction.evaluate()` returns SKIP when `commits_behind == 0` verifying FR-003 skip-when-up-to-date in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T016 [US1] Write failing test: `RebaseAction.evaluate()` returns EXECUTE when `commits_behind > 0` verifying FR-001 dedicated rebase evaluation in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T017 [US1] Write failing test: `RebaseAction.evaluate()` returns SKIP when `derived.repair_dispatched` is True verifying FR-004 deferred decision in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T018 [US1] Write failing test: `RebaseAction.evaluate()` returns SKIP when active copilot session detected verifying FR-004 no_active_session precondition in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T019 [US1] Write failing test: `RebaseAction.evaluate()` includes `no_repair_dispatched` and `no_active_session` keys in preconditions dict verifying FR-004 precondition structure in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T020 [US1] Write failing test: `RebaseAction.execute()` calls `provider.rebase_onto_base()` with correct args including base_branch verifying FR-009 in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T021 [US1] Write failing test: `RebaseAction.execute()` returns `invalidates_snapshot=True` on success verifying FR-002 snapshot invalidation in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T022 [US1] Write failing test: `RebaseAction.execute()` returns BLOCKED on `RebaseConflictError` verifying FR-006 conflict abort in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T023 [US1] Write failing test: `RebaseAction.execute()` returns FAILED on `ForceWithLeaseError` verifying FR-005 lease failure in `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T024 [US1] Write failing test: `RebaseAction` does NOT set `runs_after_invalidation = True` verifying FR-007 invalidation behavior in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T025 [US1] Write failing test: `RebaseAction.name` property returns `"rebase"` in `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py` (supports FR-001)
- [ ] T026 [US1] Write failing test: `RebaseAction.evaluate()` includes commits_behind count in details for logging (NFR-002) in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py` (supports FR-001)
- [ ] T027 [US1] Write failing test: `RebaseAction.execute()` logs PR number prefix in messages (NFR-002) in `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py` (supports FR-002)
- [ ] T028 [US1] Write failing test: `RebaseAction.evaluate()` completes without I/O (NFR-001 pure data access) in `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py` (supports FR-001)
- [ ] T029 [US1] Write failing test: `RebaseAction.execute()` handles generic exceptions gracefully returning FAILED in `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py` (supports FR-005)
- [ ] T030 [US1] Create `RebaseAction` class implementing `Action` protocol in `agentic_devtools/cli/ci/pipeline/actions/rebase.py` with `evaluate()` and `execute()` methods satisfying FR-001 through
  FR-006 and FR-009
- [ ] T031 [US1] Verify all ≥15 test cases pass with 100% branch coverage for `agentic_devtools/cli/ci/pipeline/actions/rebase.py` (supports FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-009)

## Phase 4: User Story 2 — CI Re-validation After Rebase (P1)

- [ ] T032 [US2] Write test: pipeline halts downstream actions after RebaseAction sets `invalidates_snapshot=True` verifying FR-002 CI re-validation in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T033 [US2] Write test: on next iteration after rebase, pipeline evaluates fresh snapshot with new CI status (integration-level) verifying FR-002 fresh CI check in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T034 [P] [US2] Export `RebaseAction` from `agentic_devtools/cli/ci/pipeline/actions/__init__.py`
- [ ] T035 [US2] Insert `RebaseAction()` after `SquashAction()` and before `ResolveThreadsAction()` in action list in `agentic_devtools/cli/ci/pipeline/command.py` implementing FR-007 pipeline
  ordering

## Phase 5: User Story 3 — Re-request Copilot Review After Rebase (P2)

- [ ] T036 [US3] Write test: after rebase invalidates snapshot, `RequestReviewAction.evaluate()` detects stale review on refreshed snapshot and returns EXECUTE verifying FR-008 review re-request in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T037 [US3] Write test: when repository does NOT dismiss stale reviews, existing approval remains valid after rebase (no re-request needed) verifying FR-008 no-op case in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`
- [ ] T038 [US3] Verify `RequestReviewAction` existing logic handles post-rebase review state correctly via `has_approval_on_head` snapshot field — no code changes expected per FR-008

## Phase 6: User Story 4 — Rebase Conflict Handling (P2)

- [ ] T039 [US4] Write test: `rebase_onto_base` attempts SDK conflict resolution before aborting verifying FR-006 resolution attempt in `tests/unit/cli/ci/github_provider/test_rebase_onto_base.py`
- [ ] T040 [US4] Write test: `rebase_onto_base` calls `git rebase --abort` when resolution fails, leaving clean state (NFR-003) and verifying FR-006 abort behavior in
  `tests/unit/cli/ci/github_provider/test_rebase_onto_base.py`
- [ ] T041 [US4] Write test: `rebase_onto_base` does NOT force-push partial state on conflict verifying FR-006 no broken state pushed in `tests/unit/cli/ci/github_provider/test_rebase_onto_base.py`
- [ ] T042 [US4] Write test: `RebaseAction.execute()` returns BLOCKED with diagnostic message when conflict resolution fails verifying FR-006 BLOCKED return in
  `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py`

## Phase 7: ADO Provider Stub & Integration

- [ ] T043 [P] Add `rebase_onto_base` stub raising `NotImplementedError` to `agentic_devtools/cli/ci/ado_provider.py`
- [ ] T044 [P] Add `count_commits_behind` stub returning 0 to `agentic_devtools/cli/ci/ado_provider.py`
- [ ] T045 Write integration test asserting full pipeline action ordering matches FR-007 sequence: Guards → Publish → DispatchRepair → Squash → Rebase → ResolveThreads → RequestReview → Approve →
  Merge in `tests/unit/cli/ci/pipeline/command/test_pipeline_ordering.py`

## Final Phase: Polish & Cross-Cutting

- [ ] T046 [US1] Run full test suite (`agdt-test` + `agdt-task-wait`) and verify 100% branch coverage on new modules (supports FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-009)
- [ ] T047 Run `ruff check` and `ruff format` on all new/modified files
- [ ] T048 Run `mypy` type checking on new/modified files
- [ ] T049 [US1] Run `python scripts/validate_test_structure.py` to verify 1:1:1 compliance (supporting FR-001)
- [ ] T050 [US1] Verify no regressions in existing pipeline action tests (supporting FR-007)

## Dependencies

| Task | Depends On |
|------|-----------|
| T004 | T003 |
| T006 | T005 |
| T008 | T006, T007 |
| T010 | T004, T006, T009 |
| T012 | T002, T011 |
| T014 | T012, T013 |
| T030 | T001, T002, T004, T012, T015–T029 |
| T031 | T030 |
| T035 | T030, T034 |
| T036 | T035 |
| T038 | T036 |
| T039 | T014 |
| T042 | T030 |
| T045 | T035 |
| T046 | T031, T035, T045 |
| T047–T050 | T046 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
