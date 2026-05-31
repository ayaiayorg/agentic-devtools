# Tasks: Parallel-safe State Isolation for Concurrent Subagent Execution

**Issue**: [#1525](https://github.com/ayaiayorg/agentic-devtools/issues/1525)

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | — | Project scaffolding — no direct plan equivalent |
| Phase 2: Foundational | Plan Phase 1 (Core Segment Infrastructure) | Core errors, models, and manager primitives |
| Phase 3: User Story 1 | Plan Phase 1 (Core Segment Infrastructure) | Isolation tests for FR-001/FR-002 |
| Phase 4: User Story 2 | Plan Phase 2 (Reconciliation Engine) | Deterministic reconciliation for FR-003/FR-004/FR-007/FR-010 |
| Phase 5: User Story 3 | Plan Phase 5 (ThreadPoolExecutor Integration) | Batch command compatibility FR-005/FR-008 |
| Phase 6: User Story 4 | Plan Phase 6 (Shared State Guards) | Global state guards FR-006/FR-007 |
| Phase 7: User Story 5 | Plan Phases 3–4 (Cleanup + CLI Integration) | Cleanup, orphan recovery, and CLI commands FR-009 |
| Phase 8: Polish | Plan Phase 7 (Logging, Diagnostics, Performance) | Cross-cutting NFR-003/NFR-004 |

---

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create package directory `agentic_devtools/segments/` with `__init__.py`
- [ ] T002 Create CLI package directory `agentic_devtools/cli/segments/` with `__init__.py`
- [ ] T003 Create tests directory tree `tests/unit/segments/models/` with `__init__.py` at each level
- [ ] T004 Create tests directory tree `tests/unit/segments/manager/` with `__init__.py` at each level
- [ ] T005 Create tests directory tree `tests/unit/segments/reconciler/` with `__init__.py` at each level
- [ ] T006 Create tests directory tree `tests/unit/segments/cleanup/` with `__init__.py` at each level
- [ ] T007 Create tests directory tree `tests/unit/segments/errors/` with `__init__.py` at each level
- [ ] T008 Create tests directory tree `tests/unit/cli/segments/commands/` with `__init__.py` at each level

---

## Phase 2: Foundational — Core Segment Primitives

### Errors Module

- [ ] T009 Write failing tests for `SegmentError`, `SegmentNotFoundError`, `SegmentLifecycleError`, `ReconciliationError` in `tests/unit/segments/errors/test_segmenterror.py`,
  `test_segmentnotfounderror.py`, `test_segmentlifecycleerror.py`, `test_reconciliationerror.py`
  - Depends on: T007
- [ ] T010 [P] Implement custom exceptions in `agentic_devtools/segments/errors.py` — `SegmentError` (base), `SegmentNotFoundError`, `SegmentLifecycleError`, `ReconciliationError`
  - Depends on: T009

### Models Module

- [ ] T011 Write failing tests for `SegmentStatus` enum in `tests/unit/segments/models/test_segmentstatus.py` — test values (`active`, `completed`, `failed`), terminal state property
  - Depends on: T003
- [ ] T012 Write failing tests for `StateSegment` dataclass in `tests/unit/segments/models/test_statesegment.py` — test construction, `to_dict()`, `from_dict()`, round-trip serialization, field
  defaults
  - Depends on: T003
- [ ] T013 [P] Implement `SegmentStatus` enum in `agentic_devtools/segments/models.py` — values: `active`, `completed`, `failed`
  - Depends on: T011
- [ ] T014 Implement `StateSegment` dataclass in `agentic_devtools/segments/models.py` — fields: `segment_id`, `owner_worker_id`, `owner_pid`, `created_utc`, `completed_utc`, `status`, `data`;
  methods: `to_dict()`, `from_dict()`
  - Depends on: T012, T013

### Manager Module

- [ ] T015 Write failing test for `get_segments_dir()` in `tests/unit/segments/manager/test_get_segments_dir.py`
  - Depends on: T004
- [ ] T016 Write failing test for `create_segment()` in `tests/unit/segments/manager/test_create_segment.py` — test file creation, UUID4 ID, initial `active` status, atomic write
  - Depends on: T004
- [ ] T017 Write failing test for `read_segment()` in `tests/unit/segments/manager/test_read_segment.py` — test read, missing file raises `SegmentNotFoundError`
  - Depends on: T004
- [ ] T018 Write failing test for `write_segment_data()` in `tests/unit/segments/manager/test_write_segment_data.py` — test key/value update, atomic write
  - Depends on: T004
- [ ] T019 Write failing test for `complete_segment()` in `tests/unit/segments/manager/test_complete_segment.py` — test transition to `completed`, sets `completed_utc`, rejects non-active segments
  - Depends on: T004
- [ ] T020 Write failing test for `fail_segment()` in `tests/unit/segments/manager/test_fail_segment.py` — test transition to `failed`, optional error message, rejects non-active segments
  - Depends on: T004
- [ ] T021 Write failing test for `list_segments()` in `tests/unit/segments/manager/test_list_segments.py` — test all/filtered listing, empty directory
  - Depends on: T004
- [ ] T022 Implement `get_segments_dir()` in `agentic_devtools/segments/manager.py` — resolves `{state_dir}/segments/`, creates directory if missing
  - Depends on: T015, T014, T010
- [ ] T023 Implement `create_segment()` in `agentic_devtools/segments/manager.py` — allocates UUID4 segment ID, writes initial JSON file atomically (temp file + `os.replace()`)
  - Depends on: T016, T022
- [ ] T024 [P] Implement `read_segment()` in `agentic_devtools/segments/manager.py` — reads and deserializes segment file, raises `SegmentNotFoundError` on missing
  - Depends on: T017, T022
- [ ] T025 Implement `write_segment_data()` in `agentic_devtools/segments/manager.py` — reads segment, updates `data` dict, writes atomically
  - Depends on: T018, T024
- [ ] T026 [P] Implement `complete_segment()` in `agentic_devtools/segments/manager.py` — enforces `active` status, transitions to `completed`, sets `completed_utc`
  - Depends on: T019, T024
- [ ] T027 [P] Implement `fail_segment()` in `agentic_devtools/segments/manager.py` — enforces `active` status, transitions to `failed`, stores optional error
  - Depends on: T020, T024
- [ ] T028 Implement `list_segments()` in `agentic_devtools/segments/manager.py` — scans `segments/` directory, optional status filter
  - Depends on: T021, T024

### Public API Exports

- [ ] T029 Export public API from `agentic_devtools/segments/__init__.py` — re-export key classes and functions from `models`, `manager`, `errors`
  - Depends on: T010, T014, T028

---

## Phase 3: User Story 1 — Isolated Parallel File Review State (P1)

- [ ] T030 [US1] Write failing test for cross-segment isolation in `tests/unit/segments/manager/test_create_segment.py` — two concurrent workers each create segments, verify no key leakage between
  segment files
  - Depends on: T029
- [ ] T031 [US1] Write failing test for worker failure isolation in `tests/unit/segments/manager/test_fail_segment.py` — one worker fails, other worker's segment remains valid and complete
  - Depends on: T029
- [ ] T032 [US1] Verify happy-path: `create_segment` + `write_segment_data` + `complete_segment` produce isolated per-worker segment files — green tests from T030, T031
  - Depends on: T030, T031
- [ ] T033 [US1] Write failing parallel integration test in `tests/unit/segments/manager/test_write_segment_data.py` — simulate 10+ concurrent workers writing to separate segments, assert zero
  cross-segment key leakage (SC-001)
  - Depends on: T032
- [ ] T034 [US1] Verify parallel integration test passes (green) — confirms FR-001, FR-002
  - Depends on: T033

---

## Phase 4: User Story 2 — Deterministic Reconciliation (P1)

### Reconciliation Record Models

- [ ] T035 [US2] Write failing test for `PrecedenceDecision` dataclass in `tests/unit/segments/reconciler/test_precedencedecision.py` — construction, serialization, `reason` values (`timestamp`,
  `tiebreaker`)
  - Depends on: T005
- [ ] T036 [US2] Write failing test for `ReconciliationRecord` dataclass in `tests/unit/segments/reconciler/test_reconciliationrecord.py` — construction, `to_dict()`, `from_dict()`, SHA-256 hash field
  - Depends on: T005
- [ ] T037 [US2] [P] Implement `PrecedenceDecision` dataclass in `agentic_devtools/segments/reconciler.py`
  - Depends on: T035
- [ ] T038 [US2] Implement `ReconciliationRecord` and `ReconciliationResult` dataclasses in `agentic_devtools/segments/reconciler.py`
  - Depends on: T036, T037

### Reconciliation Engine

- [ ] T039 [US2] Write failing test for `reconcile_segments()` happy-path in `tests/unit/segments/reconciler/test_reconcile_segments.py` — deterministic output, conflict resolution via
  last-writer-wins, lexicographic tiebreaker (FR-003, FR-004, FR-010)
  - Depends on: T005, T029
- [ ] T040 [US2] Write failing test for `reconcile_segments()` idempotency in `tests/unit/segments/reconciler/test_reconcile_segments.py` — same inputs yield byte-identical canonical payload (NFR-002,
  SC-002)
  - Depends on: T039
- [ ] T041 [US2] Write failing negative test for corrupted segment handling in `tests/unit/segments/reconciler/test_reconcile_segments.py` — raises `ReconciliationError` with actionable message,
  no partial merged state produced (FR-007, SC-004)
  - Depends on: T039
- [ ] T042 [US2] Implement `reconcile_segments()` in `agentic_devtools/segments/reconciler.py` — load completed segments, sort by `(completed_utc, segment_id)`, apply last-writer-wins, produce
  canonical JSON with sorted keys, compute SHA-256 hash
  - Depends on: T039, T040, T041, T038
- [ ] T043 [US2] Write failing test for `apply_reconciliation()` in `tests/unit/segments/reconciler/test_apply_reconciliation.py` — writes merged data to target path, stores `ReconciliationRecord` to
  `segments/reconciliation-log.json`
  - Depends on: T005
- [ ] T044 [US2] Implement `apply_reconciliation()` in `agentic_devtools/segments/reconciler.py` — writes merged data using atomic write pattern, appends record to audit log
  - Depends on: T043, T042
- [ ] T045 [US2] Export reconciler public API from `agentic_devtools/segments/__init__.py`
  - Depends on: T044

---

## Phase 5: User Story 3 — Existing Batch Command Compatibility (P2)

- [ ] T046 [US3] Write failing test for `submit_reviews` normal mode baseline in `tests/unit/cli/azure_devops/file_review_commands/test_submit_reviews.py` — verify ThreadPoolExecutor workers produce
  correct results with segment isolation enabled (FR-005)
  - Depends on: T045
- [ ] T047 [US3] Write failing test for `submit_reviews` dry-run mode baseline in `tests/unit/cli/azure_devops/file_review_commands/test_submit_reviews.py` — verify dry-run output unchanged after
  segment integration
  - Depends on: T045
- [ ] T048 [US3] Write failing test verifying `SubmissionManager` serial FIFO path is unchanged — no segment wrapping, direct `review-state.json` writes under file lock (FR-005)
  - Depends on: T045
- [ ] T049 [US3] Create segment-aware worker wrapper for `submit_reviews` ThreadPoolExecutor in `agentic_devtools/cli/azure_devops/file_review_commands.py` — create segment before worker, write to
  segment data, complete/fail segment after worker, reconcile after all workers finish (FR-008)
  - Depends on: T046, T047, T048
- [ ] T050 [US3] Remove legacy single-lock fallback paths in the parallel orchestration path of `submit_reviews` in `agentic_devtools/cli/azure_devops/file_review_commands.py` — replace with
  segment-based writes (FR-008)
  - Depends on: T049
- [ ] T051 [US3] Verify all `submit_reviews` tests pass (green) — confirms FR-005, FR-008
  - Depends on: T050

---

## Phase 6: User Story 4 — Safe Handling of Global State Access (P2)

- [ ] T052 [US4] Write failing test for `read_modify_write_state` context manager in `tests/unit/state/test_read_modify_write_state.py` — holds exclusive lock across load → mutate → save cycle
  (FR-006)
  - Depends on: T001
- [ ] T053 [US4] Write failing concurrent write simulation test in `tests/unit/state/test_read_modify_write_state.py` — concurrent readers/writers produce valid parseable state, no data dropped
  (SC-006)
  - Depends on: T052
- [ ] T054 [US4] Implement `read_modify_write_state` context manager in `agentic_devtools/state.py` — analogous to `read_modify_write_review_state`, holds exclusive lock via `locked_state_file`
  - Depends on: T052, T053
- [ ] T055 [US4] Audit all `save_state()` calls reachable from parallel worker code paths in `agentic_devtools/` — ensure they use `use_locking=True` or `save_state_locked()` or the new
  `read_modify_write_state` (FR-006)
  - Depends on: T054
- [ ] T056 [US4] Write failing test for deterministic update ordering under write collision in `tests/unit/state/test_read_modify_write_state.py` — retry/serialization produces deterministic order, no
  silent data drop
  - Depends on: T054
- [ ] T057 [US4] Verify all global state guard tests pass (green) — confirms FR-006, FR-007
  - Depends on: T055, T056

---

## Phase 7: User Story 5 — Cleanup of Isolated State Segments (P3)

### Cleanup Module

- [ ] T058 [US5] Write failing test for `cleanup_segments()` in `tests/unit/segments/cleanup/test_cleanup_segments.py` — TTL expiry removes terminal segments older than 24h, retains active segments
  (FR-009, SC-005)
  - Depends on: T006, T029
- [ ] T059 [US5] Write failing test for active segment retention in `tests/unit/segments/cleanup/test_cleanup_segments.py` — active segments are never removed regardless of age
  - Depends on: T058
- [ ] T060 [US5] Write failing test for orphan detection in `tests/unit/segments/cleanup/test_is_owner_alive.py` — cross-platform PID liveness check, dead owner transitions segment to `failed`
  (FR-009)
  - Depends on: T006
- [ ] T061 [US5] Write failing test for `CleanupResult` dataclass in `tests/unit/segments/cleanup/test_cleanupresult.py` — fields: `removed_count`, `retained_count`, `orphaned_count`,
  `orphan_segment_ids`, `errors`
  - Depends on: T006
- [ ] T062 [US5] [P] Implement `CleanupResult` dataclass in `agentic_devtools/segments/cleanup.py`
  - Depends on: T061
- [ ] T063 [US5] Implement `_is_owner_alive()` in `agentic_devtools/segments/cleanup.py` — cross-platform PID liveness via `os.kill(pid, 0)` on Unix, `ctypes.windll.kernel32.OpenProcess` on Windows
  - Depends on: T060
- [ ] T064 [US5] Implement `cleanup_segments()` in `agentic_devtools/segments/cleanup.py` — scan segments dir, identify terminal segments past TTL, transition orphaned active segments to `failed`,
  remove expired files, return `CleanupResult`
  - Depends on: T058, T059, T062, T063
- [ ] T065 [US5] Export cleanup public API from `agentic_devtools/segments/__init__.py`
  - Depends on: T064

### CLI Commands

- [ ] T066 [US5] Write failing test for `segments_status_command()` in `tests/unit/cli/segments/commands/test_segments_status_command.py` — lists all segments with status and age
  - Depends on: T008
- [ ] T067 [US5] Write failing test for `segments_clean_command()` in `tests/unit/cli/segments/commands/test_segments_clean_command.py` — calls `cleanup_segments()`, prints summary
  - Depends on: T008
- [ ] T068 [US5] Implement `segments_status_command()` in `agentic_devtools/cli/segments/commands.py`
  - Depends on: T066, T065
- [ ] T069 [US5] Implement `segments_clean_command()` in `agentic_devtools/cli/segments/commands.py`
  - Depends on: T067, T065
- [ ] T070 [US5] Export CLI commands from `agentic_devtools/cli/segments/__init__.py`
  - Depends on: T068, T069
- [ ] T071 [US5] Add `agdt-segments-status` and `agdt-segments-clean` entry points to `pyproject.toml`
  - Depends on: T070
- [ ] T072 [US5] Reinstall package (`pip install -e .`) and verify CLI entry points work
  - Depends on: T071

---

## Phase 8: Polish & Cross-Cutting

### Logging & Diagnostics (NFR-003)

- [ ] T073 Write failing test for structured logging in `tests/unit/segments/manager/test_logging.py` — verify log output includes `worker_id`, `segment_id`, operation stage (NFR-003, SC-006)
  - Depends on: T029
- [ ] T074 Add structured logging throughout `agentic_devtools/segments/manager.py`, `reconciler.py`, `cleanup.py` using Python `logging` module with per-module loggers
  - Depends on: T073
- [ ] T075 [P] Add structured logging to `agentic_devtools/cli/azure_devops/file_review_commands.py` segment integration path — include `worker_id` and `segment_id` in all log entries
  - Depends on: T051, T074

### Performance Validation (NFR-004)

- [ ] T076 Write performance baseline test — benchmark serial workflow latency before/after changes using `time.perf_counter()`, assert ≤5% p95 regression when parallel mode is not active (NFR-004)
  - Depends on: T057, T051

### Documentation

- [ ] T077 [P] Update `agentic_devtools/segments/__init__.py` module docstring with public API summary
  - Depends on: T065, T045
- [ ] T078 [P] Update copilot-instructions with segment documentation — add segments module to package structure table, add `agdt-segments-status` and `agdt-segments-clean` to CLI commands table,
  document segment storage layout
  - Depends on: T072

### Final Validation

- [ ] T079 Run full test suite (`agdt-test && agdt-task-wait`) — verify zero regressions, 100% branch coverage on new files (SC-001 through SC-006)
  - Depends on: T076, T078
- [ ] T080 Run `python scripts/validate_test_structure.py` — verify 1:1:1 test structure compliance for all new test files
  - Depends on: T079
- [ ] T081 Run targeted checks (`bash scripts/targeted-checks.sh`) — ruff format, ruff check, mypy, markdownlint, per-file coverage
  - Depends on: T080

---

## Dependency Summary

```text
Phase 1 (T001–T008) ──→ Phase 2 (T009–T029) ──→ Phase 3/US1 (T030–T034)
                                                ├──→ Phase 4/US2 (T035–T045)
                                                ├──→ Phase 6/US4 (T052–T057)
                                                └──→ Phase 7/US5 (T058–T072)
Phase 4 + Phase 2 ──→ Phase 5/US3 (T046–T051)
Phase 5 + Phase 6 ──→ Phase 8 (T073–T081)
```

## Story–Task Mapping

| Story | Tasks | FR Coverage |
|---|---|---|
| US1 — Isolated parallel file review state | T030–T034 | FR-001, FR-002 |
| US2 — Deterministic reconciliation | T035–T045 | FR-003, FR-004, FR-007, FR-010 |
| US3 — Batch command compatibility | T046–T051 | FR-005, FR-008 |
| US4 — Safe global state access | T052–T057 | FR-006, FR-007 |
| US5 — Cleanup of isolated segments | T058–T072 | FR-009, FR-010 |
| Setup (no story) | T001–T008 | — |
| Foundational (no story) | T009–T029 | — |
| Polish (no story) | T073–T081 | NFR-003, NFR-004 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
