# Tasks: PR Review Scaffolding 403 Cross-Identity Thread Recovery

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Task scaffolding and initial structure |
| Phase 2: Foundational — Identity Detection & Caching | Phase 1: Identity Detection & Caching | Identity snapshot, cache, comparator |
| Phase 3: Review State Schema Extension | Phase 2: Review State Schema Extension | Add `crossIdentity` field with backward compatibility |
| Phase 4: Recovery-Time Ownership Tagging | Phase 3: Recovery-Time Ownership Tagging | Detect/tag ownership during recovery |
| Phase 5: Reply-Based Update Path | Phase 4: Reply-Based Update Path | Reply fallback + idempotency |
| Phase 6: 403-Aware PATCH with Fallback | Phase 5: 403-Aware PATCH with Fallback | Catch 403 and isolate batch failures |
| Phase 7: Batch Timeout | Phase 6: Batch Isolation & Timeout | Enforce batch timeout and partial reporting |
| Phase 8: Graceful Degradation | Phase 7: Graceful Degradation | Blocked-thread reporting and local state preservation |
| Phase 9 + Final Phase | Phase 8: Integration & Regression | Edge-case + integration validation |

## Phase 1: Setup

- [ ] T001 Create feature branch `1915-review-scaffolding-403-cross` and verify dev environment
  (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)
- [ ] T002 Create test directory structure under `tests/unit/cli/azure_devops/{finalization/identity,review_state,review_scaffold,helpers,status_cascade}/` with `__init__.py` files
  (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)

## Phase 2: Foundational — Identity Detection & Caching

- [ ] T003 Write failing happy-path tests for `resolve_pat_identity_snapshot()` returning `{id, uniqueName, displayName}` in `tests/unit/cli/azure_devops/finalization/identity/test_resolve_pat_identity_snapshot.py`
  (FR-007)
- [ ] T004 Write failing tests for `IdentityCache.get_or_fetch()` ensuring single fetch per session in `tests/unit/cli/azure_devops/finalization/identity/test_identity_cache.py` (FR-007)
- [ ] T005 Write failing tests for `is_cross_identity()` comparator (primary: `author.id` vs cached `id`, fallback: `uniqueName`) in
  `tests/unit/cli/azure_devops/finalization/identity/test_is_cross_identity.py` (FR-006)
- [ ] T006 Implement `resolve_pat_identity_snapshot()` in `agentic_devtools/cli/azure_devops/finalization/identity.py` that returns full identity dict `{id, uniqueName, displayName}` without breaking
  existing `resolve_pat_identity()` contract (FR-007)
- [ ] T007 Implement `IdentityCache` class with `get_or_fetch()` in `agentic_devtools/cli/azure_devops/finalization/identity.py` — caches snapshot for session lifetime, returns `None` on failure with
  warning (FR-007)
- [ ] T008 Implement `is_cross_identity(comment_author, cached_identity)` comparator in `agentic_devtools/cli/azure_devops/finalization/identity.py` — primary: `author.id` vs `cached.id`, fallback:
  `author.uniqueName` vs `cached.uniqueName` (FR-006)
- [ ] T009 Write failing test for identity-fetch failure graceful degradation (returns None, logs warning) in `tests/unit/cli/azure_devops/finalization/identity/test_identity_cache.py` (FR-006)
- [ ] T010 Verify all Phase 2 tests pass with `agdt-test-pattern tests/unit/cli/azure_devops/finalization/identity/` (FR-006, FR-007)

## Phase 3: Review State Schema Extension

- [ ] T011 [P] Write failing tests for `FileEntry.crossIdentity` field serialization/deserialization (with and without field present) in
  `tests/unit/cli/azure_devops/review_state/test_fileentry_cross_identity.py` (FR-006)
- [ ] T012 [P] Add `crossIdentity: bool = False` field to `FileEntry` dataclass in `agentic_devtools/cli/azure_devops/review_state.py` with backward-compatible `from_dict()` handling (FR-006)
- [ ] T013 Verify schema extension tests pass and existing review_state tests still pass (FR-006)

## Phase 4: User Story Implementation — Recovery-Time Ownership Tagging (US1)

- [ ] T014 [US1] Write failing tests for `_try_recover_state_from_pr_threads` cross-identity tagging in `tests/unit/cli/azure_devops/review_scaffold/test_recover_cross_identity_tagging.py` — given
  threads authored by another identity, verify `crossIdentity=True` set on FileEntry (FR-001, FR-006)
- [ ] T015 [US1] Write failing happy-path tests for duplicate-thread selection logic: prefer current-identity thread, else lowest thread_id in
  `tests/unit/cli/azure_devops/review_scaffold/test_duplicate_thread_selection.py` (FR-004)
- [ ] T016 [US1] Write failing test for identity-fetch failure during recovery — fallback to no tagging, log warning in `tests/unit/cli/azure_devops/review_scaffold/test_recover_identity_failure.py`
  (FR-006)
- [ ] T017 [US1] Modify `_try_recover_state_from_pr_threads` in `agentic_devtools/cli/azure_devops/review_scaffold.py` to instantiate `IdentityCache` and call `is_cross_identity()` on each recovered
  thread's `comments[0].author` (FR-001, FR-006)
- [ ] T018 [US1] Implement duplicate-thread selection in `_try_recover_state_from_pr_threads`: prefer current-identity thread, else lowest thread_id; log ignored duplicates in activity log (FR-004)
- [ ] T019 [US1] Handle identity-fetch failure in recovery: skip tagging, log warning, allow 403-based detection later (FR-006)
- [ ] T020 [US1] Verify all recovery-tagging tests pass with `agdt-test-pattern tests/unit/cli/azure_devops/review_scaffold/` (FR-001, FR-004, FR-006)

## Phase 5: User Story Implementation — Reply-Based Update Path (US1)

- [ ] T021 [US1] Write failing happy-path tests for cross-identity reply posting with full scaffold content and correct markers in `tests/unit/cli/azure_devops/review_scaffold/test_cross_identity_reply.py`
  (FR-002)
- [ ] T022 [US1] Write failing tests for reply idempotency — skip if matching marker reply already exists in `tests/unit/cli/azure_devops/review_scaffold/test_reply_idempotency.py` (FR-002)
- [ ] T023 [US1] Implement reply-based update function (reusing existing `_post_reply` or shared helper) that posts full scaffold content prefixed with
  `<!-- agdt-review:v1 type:{thread_type} mode:cross-identity-update -->` and `**[Updated by {current_identity}]**` in
  `agentic_devtools/cli/azure_devops/review_scaffold.py` (FR-002)
- [ ] T024 [US1] Implement idempotency check: before posting reply, scan existing thread replies for matching cross-identity-update marker; skip if found (FR-002)
- [ ] T025 [US1] Return structured result from reply path: `{"method": "reply", "thread_id": ..., "success": True/False}` (FR-002)
- [ ] T026 [US1] Verify reply path tests pass (FR-002)

## Phase 6: User Story Implementation — 403-Aware PATCH with Fallback (US1, US2)

- [ ] T027 [US1] Write failing tests for `CrossIdentityForbiddenError` exception class in `tests/unit/cli/azure_devops/helpers/test_cross_identity_forbidden_error.py` (FR-003)
- [ ] T028 [US1] Create `CrossIdentityForbiddenError(requests.exceptions.HTTPError)` in `agentic_devtools/cli/azure_devops/helpers.py` (FR-003)
- [ ] T029 [US1] Write failing tests for `patch_comment` catching 403 and raising `CrossIdentityForbiddenError` in `tests/unit/cli/azure_devops/helpers/test_patch_comment_403.py` (FR-003)
- [ ] T030 [US1] Modify `patch_comment` in `agentic_devtools/cli/azure_devops/helpers.py` to catch HTTP 403 and raise `CrossIdentityForbiddenError` instead of generic HTTPError (FR-003)
- [ ] T031 [US1] Write failing tests for `_patch_comment_content` fallback: catch `CrossIdentityForbiddenError`, invoke reply path in
  `tests/unit/cli/azure_devops/review_scaffold/test_patch_content_fallback.py` (FR-002, FR-003)
- [ ] T032 [US1] Modify `_patch_comment_content` and file-summary PATCH call sites in `agentic_devtools/cli/azure_devops/review_scaffold.py` to catch `CrossIdentityForbiddenError` and invoke
  reply-based update from Phase 5 (FR-002, FR-003)
- [ ] T033 [US1] Write failing tests for proactive skip: if `FileEntry.crossIdentity=True`, bypass PATCH and go directly to reply path in
  `tests/unit/cli/azure_devops/review_scaffold/test_proactive_skip.py` (FR-002)
- [ ] T034 [US1] Implement proactive PATCH skip in submission paths: if `crossIdentity=True` on FileEntry, use reply path directly without attempting PATCH (FR-002)
- [ ] T035 [US2] Write failing tests for `execute_cascade` per-thread error isolation: one 403 does not abort batch in `tests/unit/cli/azure_devops/status_cascade/test_cascade_isolation.py` (FR-003)
- [ ] T036 [US2] Modify `execute_cascade` in `agentic_devtools/cli/azure_devops/status_cascade.py` to wrap each operation in try/except, accumulate per-thread results (FR-003)
- [ ] T037 [US2] Create `CascadeResult` dataclass with `succeeded`, `fallen_back`, `blocked` lists in `agentic_devtools/cli/azure_devops/status_cascade.py` (FR-003)
- [ ] T038 [US2] Update `execute_cascade` return type to `CascadeResult` and update all callers (FR-003)
- [ ] T039 [US1] If reply also returns 403, record thread as "blocked" and continue batch in `agentic_devtools/cli/azure_devops/review_scaffold.py` (FR-005)
- [ ] T040 Verify all 403-fallback tests pass (FR-002, FR-003, FR-005)

## Phase 7: User Story Implementation — Batch Timeout (US2)

- [ ] T041 [US2] Write failing tests for 120s batch timeout enforcement in `execute_cascade` in `tests/unit/cli/azure_devops/status_cascade/test_cascade_timeout.py`
 (FR-003)
- [ ] T042 [US2] Add batch-level `time.monotonic()` tracking in `execute_cascade` with configurable timeout from state key `review.scaffold.cascade_timeout_seconds` (default 120); skip remaining on
  timeout (NFR-001)
- [ ] T043 [US2] Add `skipped_timeout` category to `CascadeResult` and include applied timeout value
- [ ] T044 [US2] Write failing test for partial success reporting: batch result shows 4 succeeded + 1 fallback in `tests/unit/cli/azure_devops/status_cascade/test_partial_success_report.py` (FR-003)
- [ ] T045 [US2] Verify timeout and partial success tests pass (FR-003)

## Phase 8: User Story Implementation — Graceful Degradation (US3)

- [ ] T046 [US3] Write failing tests for blocked-thread activity-log reply in `tests/unit/cli/azure_devops/review_scaffold/test_blocked_activity_log.py` — verify reply to activity-log thread with
  thread IDs, file paths, reason (FR-005)
- [ ] T047 [US3] Implement: after batch completes, collect all "blocked" entries and post structured reply to activity-log thread in `agentic_devtools/cli/azure_devops/review_scaffold.py` (FR-005)
- [ ] T048 [US3] Write failing tests for local review-state update on blocked threads in `tests/unit/cli/azure_devops/review_scaffold/test_blocked_local_state.py` (FR-005)
- [ ] T049 [US3] Implement: for each blocked file, update `review-state.json` local file status directly without calling Azure DevOps mark-reviewed API (FR-005)
- [ ] T050 [US3] Write failing test for edge case: both PATCH and reply forbidden for one thread, other threads still complete in
  `tests/unit/cli/azure_devops/review_scaffold/test_mixed_blocked_batch.py` (FR-003, FR-005)
- [ ] T051 [US3] Verify graceful degradation tests pass (FR-003, FR-005)

## Phase 9: User Story Implementation — Edge Cases

- [ ] T052 [P] [US2] Write failing test for deleted thread after recovery (HTTP 404 on update) — reported as skipped in `tests/unit/cli/azure_devops/review_scaffold/test_deleted_thread.py` (FR-003)
- [ ] T053 [P] [US2] Implement 404 handling in submission: report thread as skipped/not found, continue batch (FR-003)
- [ ] T054 [P] [US1] Write failing test for thread selection with duplicate markers from multiple identities in `tests/unit/cli/azure_devops/review_scaffold/test_duplicate_markers_multi_identity.py`
  (FR-004)
- [ ] T055 [P] [US1] Verify duplicate marker thread selection: prefer current-identity, else lowest thread_id, log ignored duplicates (FR-004)

## Final Phase: Polish & Cross-Cutting

- [ ] T056 [P] Integration happy-path test: full recovery → submit cycle with mixed-ownership threads (mocked API) in `tests/unit/cli/azure_devops/review_scaffold/test_integration_mixed_ownership.py`
 (FR-001, FR-002, FR-003, FR-006)
- [ ] T057 [P] Integration test: identity-fetch failure → 403-based fallback detection in `tests/unit/cli/azure_devops/review_scaffold/test_integration_identity_failure.py`
  (FR-003, FR-006, FR-007)
- [ ] T058 [P] Integration test: duplicate threads → correct selection logic in `tests/unit/cli/azure_devops/review_scaffold/test_integration_duplicate_threads.py` (FR-004)
- [ ] T059 Run full test suite with `agdt-test` and verify 0 regressions
  (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)
- [ ] T060 Run `bash scripts/targeted-checks.sh` for lint/format/mypy/coverage validation
- [ ] T061 Verify backward compatibility: existing `review-state.json` without `crossIdentity` field still loads correctly (FR-006, NFR-002)
- [ ] T062 Verify `patch_comment` existing callers still catch the new exception via `requests.exceptions.HTTPError` base class (FR-003, NFR-002)
- [ ] T063 Run `python scripts/validate_test_structure.py` to confirm test structure compliance
  (FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007)
- [ ] T064 Commit with `agdt-git-save-work` using message:
  `feat([#1915](https://github.com/ayaiayorg/agentic-devtools/issues/1915)): handle cross-identity 403 on PR review scaffolding thread recovery`
  and footer `[#1915](https://github.com/ayaiayorg/agentic-devtools/issues/1915)`

## Dependency Graph

```text
T001 → T002 → T003-T005 (parallel) → T006-T008 (parallel) → T009 → T010
T011-T012 (parallel, after T002) → T013
T010 + T013 → T014-T016 (parallel) → T017-T019 → T020
T020 → T021-T022 (parallel) → T023-T025 → T026
T026 → T027-T029 (parallel) → T030 → T031 → T032-T034 → T035-T038 → T039-T040
T040 → T041-T043 → T044-T045
T045 → T046 → T047 → T048-T050 → T051
T051 → T052-T055 (parallel)
T055 → T056-T058 (parallel) → T059-T064 (sequential)
```

## FR Coverage Matrix

_Note: This matrix lists the primary implementation tasks per FR for readability; comprehensive FR/task linkage is captured in task tags above and `test-coverage.json`._

| FR | Tasks |
|----|-------|
| FR-001 | T014, T017 |
| FR-002 | T021-T025, T031-T034 |
| FR-003 | T027-T032, T035-T040, T044, T050, T052-T053 |
| FR-004 | T015, T018, T054-T055 |
| FR-005 | T039, T046-T051 |
| FR-006 | T005, T008, T011-T012, T014, T016-T019 |
| FR-007 | T003-T004, T006-T007, T009 |

---
_Generated by Copilot SDK (claude-opus-4.6)_
