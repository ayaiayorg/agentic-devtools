# Tasks: Shared Review Threads Across Identities (#1517)

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Scaffolding/module wiring not explicitly called out as a plan phase |
| Phase 2: Foundational — Data Model Extensions | Phase 1: Data Model Extension | Add optional author-tracking fields + serialization/back-compat |
| Phase 3: User Story 4 — Deterministic Thread Classification and Matching | Phase 2: Thread Discovery and Matching Logic | Deterministic discovery + matching helpers |
| Phase 4–6: User Stories 1–3 — Thread Reuse | Phases 3–4 | Reuse-reply idempotency + scaffold integration (activity/overall/file) |
| Phase 7: User Story 5 — Backward-Compatible Behavior | Phases 4–5 | Legacy handling + state sync + finalization compatibility |
| Phase 8: Logging, Dry-Run, and Finalization Compatibility | Phases 5–6 | Logging/dry-run output + finalization verification |
| Phase 9: Polish & Cross-Cutting | — | Full suite + PR checks + lint/format/structure validation |

---

## Phase 1: Setup

- [ ] T001 Create module file `agentic_devtools/cli/azure_devops/thread_reuse.py` with module docstring and imports
- [ ] T002 [US4] Create test directory `tests/unit/cli/azure_devops/thread_reuse/` with `__init__.py`
- [ ] T003 Add `thread_reuse` exports to `agentic_devtools/cli/azure_devops/__init__.py`

## Phase 2: Foundational — Data Model Extensions

- [ ] T004 [P] Write failing test `tests/unit/cli/azure_devops/review_state/test_overallsummary.py` for `originalAuthorId` serialization round-trip (None and populated) (FR-005)
- [ ] T005 [P] Write failing test `tests/unit/cli/azure_devops/review_state/test_fileentry.py` for `originalAuthorId` serialization round-trip (None and populated) (FR-005)
- [ ] T006 [P] Write failing test `tests/unit/cli/azure_devops/review_state/test_reviewstate.py` for `activityLogOriginalAuthorId` serialization round-trip (None and populated) (FR-008)
- [ ] T007 Add `originalAuthorId: str | None = None` field to `OverallSummary` dataclass in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T008 Update `OverallSummary.to_dict()` to serialize `originalAuthorId` only when not None in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T009 Update `OverallSummary.from_dict()` to deserialize `originalAuthorId` (default None) in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T010 Add `originalAuthorId: str | None = None` field to `FileEntry` dataclass in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T011 Update `FileEntry.to_dict()` to serialize `originalAuthorId` only when not None in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T012 Update `FileEntry.from_dict()` to deserialize `originalAuthorId` (default None) in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T013 Add `activityLogOriginalAuthorId: str | None = None` field to `ReviewState` dataclass in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T014 Update `ReviewState.to_dict()` to serialize `activityLogOriginalAuthorId` only when not None in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T015 Update `ReviewState.from_dict()` to deserialize `activityLogOriginalAuthorId` (default None) in `agentic_devtools/cli/azure_devops/review_state.py`
- [ ] T016 Run tests to verify data model extensions pass (green): `agdt-test-pattern tests/unit/cli/azure_devops/review_state/ -v` (FR-005, FR-008)

## Phase 3: User Story 4 — Deterministic Thread Classification and Matching (FR-004)

- [ ] T017 [US4] Write failing test `tests/unit/cli/azure_devops/thread_reuse/test_threadmatch.py` for `ThreadMatch` dataclass construction and fields
- [ ] T018 [US4] Write failing test `tests/unit/cli/azure_devops/thread_reuse/test_threaddiscoveryresult.py` for `ThreadDiscoveryResult` dataclass construction
- [ ] T019 Implement `ThreadMatch` dataclass (`thread_id`, `comment_id`, `original_author_id`, `is_resolved`) in `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T020 Implement `ThreadDiscoveryResult` dataclass (`activity_log`, `overall_summary`, `file_summaries`) in `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T021 Write failing test `tests/unit/cli/azure_devops/thread_reuse/test__resolve_single_match.py` for deterministic selection: prefer active over resolved, then lowest thread ID (FR-004)
- [ ] T022 Implement `_resolve_single_match(candidates)` → `ThreadMatch | None` with deterministic selection logic in `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T023 Write failing test `tests/unit/cli/azure_devops/thread_reuse/test__match_file_summary.py` for file path matching using `normalize_file_path()` equality (FR-004)
- [ ] T024 Implement `_match_file_summary(candidates, target_path)` → `ThreadMatch | None` using `normalize_file_path()` in `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T025 Write failing test `tests/unit/cli/azure_devops/thread_reuse/test_discover_reusable_threads.py` for full discovery flow: classification by marker (no author filtering), matching all three
  types (FR-004)
- [ ] T026 Implement `discover_reusable_threads(threads, target_files)` → `ThreadDiscoveryResult` using `classify_agdt_threads()` and `parse_marker()` in
  `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T027 Write test for edge case: duplicate candidates for same type resolved deterministically (FR-004)
- [ ] T028 Write test for edge case: only resolved threads available — reuses earliest resolved match (FR-004)
- [ ] T029 Write test for edge case: deleted/renamed file does not cross-match via normalized path (FR-004)
- [ ] T030 [US4] Run tests to verify discovery module passes:
  `agdt-test-pattern tests/unit/cli/azure_devops/thread_reuse/ -v`

## Phase 4: User Story 1 — Reuse Review Activity Log Thread Across Identities (FR-001, FR-006)

- [ ] T031 Write failing test `tests/unit/cli/azure_devops/thread_reuse/test__post_reuse_reply.py` for reuse-reply posting with correlation marker (FR-006)
- [ ] T032 Write failing test `tests/unit/cli/azure_devops/thread_reuse/test__has_reuse_reply.py` for idempotency detection (FR-006, NFR-003)
- [ ] T033 Define reuse correlation marker format `<!-- agdt-reuse:v1 session:{session_id} type:{type} -->` as constant in `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T034 Implement `_has_reuse_reply(thread_comments, session_id, marker_type)` helper in `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T035 Implement `_post_reuse_reply(requests_module, headers, threads_url, thread_id, content, session_id, marker_type)` with idempotency check in
  `agentic_devtools/cli/azure_devops/thread_reuse.py`
- [ ] T036 Write failing happy-path test for activity-log reuse: existing thread from identity A reused by identity B via reply (FR-001, FR-006)
- [ ] T037 Write failing test for activity-log creation: no existing thread results in one new thread (FR-001)
- [ ] T038 Modify `_fresh_scaffold()` in `agentic_devtools/cli/azure_devops/review_scaffold.py` to call `discover_reusable_threads()` before creating activity-log thread (FR-001)
- [ ] T039 Implement activity-log reuse logic: if match found → post reuse reply and populate `activityLogOriginalAuthorId`; else create new (FR-001, FR-006)
- [ ] T040 [US1] Run activity-log reuse tests to verify green:
  `agdt-test-pattern tests/unit/cli/azure_devops/thread_reuse/test__post_reuse_reply.py`
  `agdt-test-pattern tests/unit/cli/azure_devops/review_scaffold/test__fresh_scaffold.py -v`

## Phase 5: User Story 2 — Reuse Overall PR Review Summary Thread Across Identities (FR-002, FR-005, FR-006)

- [ ] T041 Write failing happy-path test for overall-summary reuse: existing thread from different identity reused by posting reply (FR-002, FR-006)
- [ ] T042 Write failing test for overall-summary creation: no existing thread results in one new thread (FR-002)
- [ ] T043 Write failing happy-path test for `originalAuthorId` persistence on `OverallSummary` when thread is reused (FR-005)
- [ ] T044 Modify `_fresh_scaffold()` overall-summary creation to use discovery result: reuse (post reply) or create new (FR-002, FR-006)
- [ ] T045 Populate `OverallSummary.originalAuthorId` from `ThreadMatch.original_author_id` when reusing (FR-005)
- [ ] T046 [US2] Run overall-summary reuse tests:
  `agdt-test-pattern tests/unit/cli/azure_devops/review_scaffold/test__fresh_scaffold.py -v`

## Phase 6: User Story 3 — Reuse File Review Summary Threads Across Identities (FR-003, FR-005, FR-006)

- [ ] T047 Write failing happy-path test for file-summary reuse: existing file thread from different identity reused for same normalized path (FR-003, FR-006)
- [ ] T048 Write failing test for file-summary creation: no existing thread for file results in one new thread (FR-003)
- [ ] T049 Write failing test for `originalAuthorId` persistence on `FileEntry` when file thread is reused (FR-005)
- [ ] T050 Modify `_fresh_scaffold()` per-file thread creation to use discovery result: reuse (post reply) or create new (FR-003, FR-006)
- [ ] T051 Populate `FileEntry.originalAuthorId` from `ThreadMatch.original_author_id` when reusing (FR-005)
- [ ] T052 Ensure per-file scaffold reuse/create loop creates missing file-summary
  threads exactly once while preserving reusable normalized-path matches (FR-003,
  FR-007)
- [ ] T053 [US3] Run file-summary reuse tests:
  `agdt-test-pattern tests/unit/cli/azure_devops/review_scaffold/ -v`

## Phase 7: User Story 5 — Backward-Compatible Behavior (FR-007, FR-008)

- [ ] T054 Write failing test for legacy state deserialization: state without `originalAuthorId` fields loads successfully with None defaults (FR-008)
- [ ] T055 Write failing test for mixed scenario: some thread types reused, missing types created exactly once (FR-007)
- [ ] T056 Write failing test for `originalAuthorId` population on first access of legacy thread entries (FR-008)
- [ ] T057 Implement backward-compatible handling: legacy entries treated as valid, `originalAuthorId` populated on first encounter (FR-008)
- [ ] T058 Update `sync_review_state_from_threads()` in `agentic_devtools/cli/azure_devops/review_state.py` to populate `originalAuthorId` on first encounter (FR-005, FR-008)
- [ ] T059 Write test for partially migrated PR: existing threads reused and only missing ones created (FR-007)
- [ ] T060 [US5] Run backward-compatibility tests:
  `agdt-test-pattern tests/unit/cli/azure_devops/review_state/ -v`

## Phase 8: Logging, Dry-Run, and Finalization Compatibility

- [ ] T061 [P] Write failing test `tests/unit/cli/azure_devops/thread_reuse/test_reuse_logging.py` for structured log output per reuse decision (FR-006, NFR-002)
- [ ] T062 [P] Write failing test `tests/unit/cli/azure_devops/review_scaffold/test__print_dry_run_plan.py` for dry-run output including reuse decisions (FR-007)
- [ ] T063 Implement structured log emission in discovery/scaffold integration: thread type, thread ID, action (reused/created), original author ID (NFR-002)
- [ ] T064 Update `_print_dry_run_plan()` in `agentic_devtools/cli/azure_devops/review_scaffold.py` to report planned reuse vs creation decisions
- [ ] T065 Write test verifying `finalization/classification.py` uses author filtering only for edit-permission scoping (not for reuse matching) (FR-007)
- [ ] T066 Write integration-level test: cross-identity reuse followed by finalization operates correctly (FR-007)
- [ ] T067 Run finalization and dry-run tests: `agdt-test-pattern tests/unit/cli/azure_devops/ -v` (FR-007)

## Phase 9: Polish & Cross-Cutting

- [ ] T068 Write test for NFR-003 idempotency: repeated execution with same session produces zero additional reuse replies (FR-006, NFR-003)
- [ ] T069 Write test for deactivated identity thread reuse: marker-based matching still works regardless of author status (FR-004)
- [ ] T070 [US5] Run full test suite: `agdt-test` + `agdt-task-wait`
- [ ] T071 Run PR checks: `bash scripts/run-pr-checks.sh --full`
- [ ] T072 Run `ruff check --fix . && ruff format .` to fix any lint/format issues
- [ ] T073 [US5] Run `python scripts/validate_test_structure.py` to validate 1:1:1 test structure

## Dependencies

| Task | Depends On |
|------|-----------|
| T004–T006 | T002 |
| T007–T015 | T004–T006 (tests written first per TDD) |
| T016 | T007–T015 |
| T017–T018 | T002 |
| T019–T020 | T017–T018 |
| T021 | T019 |
| T022 | T021 |
| T023 | T019 |
| T024 | T023 |
| T025 | T022, T024 |
| T026 | T025 |
| T027–T029 | T026 |
| T030 | T027–T029 |
| T031–T032 | T026 |
| T033–T035 | T031–T032 |
| T036–T037 | T035 |
| T038–T039 | T036–T037 |
| T040 | T038–T039 |
| T041–T043 | T040 |
| T044–T045 | T041–T043 |
| T046 | T044–T045 |
| T047–T049 | T046 |
| T050–T052 | T047–T049 |
| T053 | T050–T052 |
| T054–T056 | T053 |
| T057–T059 | T054–T056 |
| T060 | T057–T059 |
| T061–T062 | T060 |
| T063–T066 | T061–T062 |
| T067 | T063–T066 |
| T068–T069 | T067 |
| T070 | T068–T069 |
| T071–T073 | T070 |

## FR Traceability Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T036, T037, T038, T039 |
| FR-002 | T041, T042, T044 |
| FR-003 | T047, T048, T050, T052 |
| FR-004 | T021, T022, T023, T024, T025, T026, T027, T028, T029 |
| FR-005 | T043, T045, T049, T051, T058 |
| FR-006 | T031, T035, T036, T039, T041, T044, T047, T050 |
| FR-007 | T052, T055, T059 |
| FR-008 | T054, T056, T057, T058 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
