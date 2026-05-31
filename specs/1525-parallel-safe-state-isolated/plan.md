# Implementation Plan: Parallel-safe State Isolation for Concurrent Subagent Execution

**Issue**: [#1525](https://github.com/ayaiayorg/agentic-devtools/issues/1525)

## 1. Technical Context

### Technology Stack

- **Language**: Python 3.10+
- **State persistence**: JSON files under `.agdt/workflows/{identity}/{worktree_key}/`
- **Concurrency primitives**: `file_locking.py` (fcntl/msvcrt), `threading`, `concurrent.futures.ThreadPoolExecutor`
- **Existing patterns**: `SubmissionManager` (serial FIFO queue), `submit_reviews` (bounded ThreadPoolExecutor), `background_tasks.py` (subprocess-based)
- **Testing**: pytest with 100% branch coverage requirement, 1:1:1 test structure under `tests/unit/`
- **Linting**: ruff, mypy, markdownlint

### Key Dependencies

- `agentic_devtools/state.py` — core state management (load/save/get/set with dot-notation)
- `agentic_devtools/file_locking.py` — cross-platform file locking (fcntl on Unix, msvcrt on Windows)
- `agentic_devtools/cli/azure_devops/review_state.py` — `ReviewState` load/save with sidecar lock files and atomic writes
- `agentic_devtools/submission_manager.py` — serial FIFO queue (NOT touched by this feature)
- `agentic_devtools/task_state.py` — background task state CRUD

### Architecture Decisions

- Segments stored as **separate JSON files** per worker under `segments/` subdirectory
- Each segment file is **single-writer** (no cross-process locking needed on segments)
- Atomic writes via **temp file + `os.replace()`** for crash safety
- Conflict resolution: **last-writer-wins** by completion timestamp (UTC), lexicographic segment ID tiebreaker
- `SubmissionManager` remains explicitly **out of scope**; `submit_reviews` is wrapped with segment isolation

## 2. Research Summary

Key decisions made:

1. **Segment storage**: Separate JSON files per worker (not namespaced subtree in `state.json`)
2. **Segment ID format**: Hyphenated UUID4 string via `str(uuid.uuid4())` (matches existing `task_state.py` pattern)
3. **Conflict resolution**: Timestamp-based last-writer-wins with lexicographic tiebreaker
4. **Orphan detection**: PID-based liveness check via `os.kill(pid, 0)` on Unix, `OpenProcess` on Windows
5. **Cleanup TTL**: 24 hours after terminal state, matching `background.expiry_hours` default

## 3. Design Overview

### Component Architecture

```text
agentic_devtools/
├── segments/                      # NEW: Segment isolation module
│   ├── __init__.py               # Public API exports
│   ├── models.py                 # StateSegment dataclass, SegmentStatus enum
│   ├── manager.py                # SegmentManager: create, read, complete, fail
│   ├── reconciler.py             # Reconciler: merge segments → canonical result
│   ├── cleanup.py                # Cleanup: TTL-based expiry, orphan detection
│   └── errors.py                 # Custom exceptions
├── state.py                       # MODIFIED: Add segment-aware helpers
└── cli/
    ├── segments/                   # NEW: CLI commands
    │   ├── __init__.py
    │   └── commands.py            # agdt-segments-status, agdt-segments-clean
    └── azure_devops/
        └── file_review_commands.py # MODIFIED: ThreadPoolExecutor workers use segments
```

### Data Flow

```text
1. Orchestrator creates N segments → `.agdt/workflows/{identity}/{worktree_key}/segments/{id}.json` (status: active)
2. Workers write results to their own segment file (single-writer, no lock)
3. Worker completes → segment transitions to completed (atomic write)
4. Orchestrator calls reconciler → reads all completed segments
5. Reconciler merges via precedence rules → writes canonical result to reviews/review-state.json
6. Reconciler emits ReconciliationRecord as audit metadata
7. Cleanup runs → removes segments in terminal state older than 24h
```

## 4. Implementation Phases

### Phase 1: Core Segment Infrastructure (FR-001, FR-002, FR-010)

**Deliverables**: Segment model, manager, atomic I/O

**Files to create**:

- `agentic_devtools/segments/__init__.py`
- `agentic_devtools/segments/models.py`
- `agentic_devtools/segments/manager.py`
- `agentic_devtools/segments/errors.py`

**Tasks**:

1. **Define `SegmentStatus` enum** in `models.py`
   - Values: `active`, `completed`, `failed`
   - Terminal states: `completed`, `failed` (matches `TaskStatus` pattern)

2. **Define `StateSegment` dataclass** in `models.py`
   - Fields: `segment_id` (hyphenated UUID4 string), `owner_worker_id` (str), `owner_pid` (int),
     `created_utc` (ISO-8601), `completed_utc` (ISO-8601 | None),
     `status` (SegmentStatus), `data` (dict[str, Any])
   - `to_dict()` / `from_dict()` serialization (matching existing pattern)

3. **Implement `SegmentManager`** in `manager.py`
   - `create_segment(worker_id: str) -> StateSegment` — allocates segment, writes initial file
   - `get_segments_dir() -> Path` — resolves `{state_dir}/segments/`
   - `read_segment(segment_id: str) -> StateSegment` — reads segment file
   - `write_segment_data(segment_id: str, key: str, value: Any)` — updates data in segment
   - `complete_segment(segment_id: str)` — transitions to completed, sets `completed_utc`
   - `fail_segment(segment_id: str, error: str | None)` — transitions to failed
   - `list_segments(status: SegmentStatus | None = None) -> list[StateSegment]` — lists all/filtered
   - All writes use atomic temp file + `os.replace()` pattern (from `review_state.py`)

4. **Define custom exceptions** in `errors.py`
   - `SegmentError` (base)
   - `SegmentNotFoundError`
   - `SegmentLifecycleError` (invalid state transitions)
   - `ReconciliationError`

**Tests** (1:1:1 under `tests/unit/segments/`):

- `models/test_segmentstatus.py`, `models/test_statesegment.py`
- `manager/test_create_segment.py`, `manager/test_read_segment.py`,
  `manager/test_write_segment_data.py`, `manager/test_complete_segment.py`,
  `manager/test_fail_segment.py`, `manager/test_list_segments.py`
- `errors/test_segmenterror.py`, etc.

---

### Phase 2: Reconciliation Engine (FR-003, FR-004, FR-007, FR-010)

**Deliverables**: Deterministic reconciliation with audit trail

**Files to create**:

- `agentic_devtools/segments/reconciler.py`

**Tasks**:

1. **Define `ReconciliationRecord` dataclass**
   - Fields: `record_id` (UUID4), `input_segment_ids` (list[str]),
     `precedence_decisions` (list[PrecedenceDecision]),
     `output_path` (str), `reconciled_utc` (ISO-8601),
     `canonical_payload_hash` (SHA-256 of deterministic JSON)
   - `PrecedenceDecision`: `key`, `winning_segment_id`, `winning_timestamp`,
     `losing_segment_ids`, `reason` (timestamp | tiebreaker)

2. **Implement `reconcile_segments(segment_ids: list[str]) -> ReconciliationResult`**
   - Loads all specified segments; validates all are in `completed` status
   - Raises `ReconciliationError` for corrupted/missing/non-terminal segments
   - Sorts segments by `(completed_utc, segment_id)` for deterministic ordering
   - Iterates keys across all segments; applies last-writer-wins precedence
   - Produces canonical merged payload (sorted keys, deterministic JSON serialization)
   - Returns `ReconciliationResult` with merged data + `ReconciliationRecord`

3. **Implement `apply_reconciliation(result: ReconciliationResult)`**
   - Writes merged data to `review-state.json` using `read_modify_write_review_state()`
   - Stores `ReconciliationRecord` alongside (e.g., `segments/reconciliation-log.json`)

4. **Idempotency**: Running reconcile on the same inputs must produce
   byte-identical canonical payload (NFR-002)

**Tests**:

- `reconciler/test_reconcile_segments.py` — deterministic output, conflict resolution
- `reconciler/test_apply_reconciliation.py` — review-state.json update
- `reconciler/test_reconciliationrecord.py` — serialization
- `reconciler/test_precedencedecision.py` — precedence rules

---

### Phase 3: Cleanup and Orphan Recovery (FR-009)

**Deliverables**: TTL-based cleanup, orphan detection

**Files to create**:

- `agentic_devtools/segments/cleanup.py`

**Tasks**:

1. **Implement `cleanup_segments(ttl_hours: int = 24) -> CleanupResult`**
   - Scans `segments/` directory for all segment files
   - Identifies terminal segments (`completed`/`failed`) older than TTL
   - Removes expired segment files
   - Returns `CleanupResult` with counts (removed, retained, orphaned)

2. **Implement orphan detection**
   - `_is_owner_alive(pid: int) -> bool` — cross-platform PID liveness check
   - Active segments whose owner PID is dead → transition to `failed`
   - Then normal TTL cleanup applies

3. **Implement `CleanupResult` dataclass**
   - Fields: `removed_count`, `retained_count`, `orphaned_count`,
     `orphan_segment_ids`, `errors`

**Tests**:

- `cleanup/test_cleanup_segments.py` — TTL expiry, active retention
- `cleanup/test_is_owner_alive.py` — PID liveness

---

### Phase 4: CLI Integration (NFR-006)

**Deliverables**: CLI commands for segment management

**Files to create**:

- `agentic_devtools/cli/segments/__init__.py`
- `agentic_devtools/cli/segments/commands.py`

**Files to modify**:

- `pyproject.toml` — add entry points

**Tasks**:

1. **`agdt-segments-status`** — Lists all segments with status/age
2. **`agdt-segments-clean`** — Runs cleanup manually (calls `cleanup_segments()`)
3. **Add entry points** to `pyproject.toml`

**Tests**:

- `tests/unit/cli/segments/commands/test_segments_status_command.py`
- `tests/unit/cli/segments/commands/test_segments_clean_command.py`

---

### Phase 5: ThreadPoolExecutor Integration (FR-005, FR-008)

**Deliverables**: Wrap `submit_reviews` ThreadPoolExecutor workers with segment isolation

**Files to modify**:

- `agentic_devtools/cli/azure_devops/file_review_commands.py` — wrap workers

**Tasks**:

1. **Create segment-aware worker wrapper** for `submit_reviews` ThreadPoolExecutor
   - Before worker execution: `create_segment(worker_id)`
   - Worker writes to segment data instead of shared state
   - After worker completes: `complete_segment()` or `fail_segment()`
   - After all workers finish: reconcile segments, apply to `review-state.json`

2. **Preserve SubmissionManager serial behavior** (FR-005)
   - `SubmissionManager` continues writing directly to `review-state.json` under file lock
   - No segment wrapping for the serial FIFO path

3. **Remove legacy single-lock fallback** in the parallel orchestration path (FR-008)
   - Identify any fallback paths in `submit_reviews` that fall back to locked `state.json` writes
   - Replace with segment-based writes

**Tests**:

- `tests/unit/cli/azure_devops/file_review_commands/test_submit_reviews.py` — update existing
- Integration test: parallel workers produce isolated segments

---

### Phase 6: Shared State Guards (FR-006)

**Deliverables**: Guarded global state access for cross-worker coordination

**Files to modify**:

- `agentic_devtools/state.py` — ensure all parallel-path writes use `save_state_locked()`

**Tasks**:

1. **Audit all `save_state()` calls** in code paths reachable from parallel workers
   - Ensure they use `use_locking=True` or `save_state_locked()`
   - The existing `locked_state_file` context manager already handles this

2. **Add `read_modify_write_state` context manager** to `state.py`
   - Analogous to `read_modify_write_review_state` in `review_state.py`
   - Holds exclusive lock across load → mutate → save cycle

**Tests**:

- `tests/unit/state/test_read_modify_write_state.py`
- Concurrent write simulation test

---

### Phase 7: Logging, Diagnostics, and Performance Validation (NFR-003, NFR-004)

**Deliverables**: Structured logging, performance baseline

**Tasks**:

1. **Add structured logging** throughout segment operations
   - All log entries include `worker_id`, `segment_id`, operation stage
   - Use Python `logging` module with `%(name)s` logger per module

2. **Performance baseline test** (NFR-004)
   - Benchmark serial workflow latency before/after changes
   - Assert ≤5% p95 regression when parallel mode is not active
   - Implemented as a pytest timing test using stdlib clocks (`time.perf_counter()`),
     optionally behind a marker (no new benchmark plugin dependency)

3. **Update copilot-instructions** in `.github/copilot-instructions.md` with segment documentation

**Tests**:

- `tests/unit/segments/manager/test_logging.py` — verify log output contains required fields

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Orphan detection false positives (PID reuse) | Low | Medium | Use PID + creation timestamp comparison; conservative: only transition after grace period |
| Clock skew between workers on same machine | Very Low | Low | Workers run on same machine; use monotonic clock for ordering when possible |
| Segment directory accumulation from crashed workflows | Medium | Low | Automatic cleanup with 24h TTL; `agdt-segments-clean` CLI command |
| Performance regression from segment file I/O | Low | Medium | Segment writes are single-writer (no locking overhead); benchmark validation in CI |
| Breaking existing `submit_reviews` behavior | Medium | High | Phase 5 is isolated; extensive existing tests validate baseline behavior |
| Reconciliation non-determinism from floating-point timestamps | Low | Medium | Use ISO-8601 string comparison (lexicographic); avoid float timestamps |

## 6. Dependencies

### Internal Dependencies

- `agentic_devtools/file_locking.py` — reuse `locked_file` / `locked_state_file` for global state
- `agentic_devtools/state.py` — `get_state_dir()`, `load_state()`, `save_state_locked()`
- `agentic_devtools/cli/azure_devops/review_state.py` — atomic write pattern (`_atomic_write_json`)
- `agentic_devtools/task_state.py` — UUID4 and status enum patterns

### External Dependencies

- None new. All functionality built on Python stdlib (`json`, `os`, `uuid`, `dataclasses`, `concurrent.futures`)

### Phase Dependencies

```text
Phase 1 (Core) ──→ Phase 2 (Reconciliation) ──→ Phase 5 (Integration)
     │                    │
     ├──→ Phase 3 (Cleanup) ──→ Phase 4 (CLI)
     │
     └──→ Phase 6 (Guards) ──→ Phase 7 (Logging/Perf)
```

Phase 1 is the foundation. Phases 2, 3, and 6 can proceed in parallel after Phase 1.
Phase 5 requires Phases 1 and 2. Phase 4 requires Phase 3. Phase 7 is last.

---
*Generated by Copilot SDK (claude-opus-4.6)*
