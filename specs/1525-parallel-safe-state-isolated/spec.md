# Feature Specification: Parallel-safe state isolation for concurrent subagent execution

**Feature Branch**: `speckit/1525/phase-2-clarify`  
**Created**: 2026-05-22  
**Clarified**: 2026-05-23  
**Status**: Draft  
**Input**: User description: "Parallel-safe state: isolated state segments for concurrent subagent execution"  
**Source Issue**: #1525 (<https://github.com/ayaiayorg/agentic-devtools/issues/1525>)

## Clarifications

### Session 2026-05-23

- **Q:** What is the physical representation of a "state segment" — a separate
  JSON file per worker, a namespaced subtree within the existing `state.json`,
  or an in-memory dict flushed on completion?
  **A:** A separate JSON file per worker stored under a `segments/`
  subdirectory within the workflow state directory (for example,
  `.agdt/workflows/{identity}/{worktree_key}/segments/{segment_id}.json`).
  This avoids contention on canonical state-file locks (e.g.
  `reviews/review-state.json` and `state.json`) during parallel writes and aligns
  with the existing per-worktree isolation model.
- **Q:** What are the conflict-resolution precedence rules when two segments
  write to the same logical key (FR-004)?
  **A:** Last-writer-wins based on segment completion timestamp (UTC). When
  timestamps are identical, lexicographic ordering of the segment ID breaks the
  tie deterministically. The reconciliation record logs the precedence
  decision for auditability.
- **Q:** What quantitative threshold defines "not materially regress serial
  workflow latency" (NFR-004)?
  **A:** Serial workflow latency MUST NOT increase by more than 5% (p95)
  compared to the pre-change baseline when parallel mode is not active. This
  accounts for the additional segment file I/O overhead in serial fallback
  paths.
- **Q:** What is the default TTL/expiry for stale segments before cleanup
  removes them (FR-009)?
  **A:** 24 hours after the segment reaches a terminal lifecycle state
  (`completed` or `failed`). `active` segments are not eligible while
  their owning worker/session is still live. If recovery detects an orphaned
  active segment whose owner is no longer live, the segment MUST transition to
  `failed` before cleanup applies the normal terminal-state TTL. This matches
  the existing `background.expiry_hours` default of 24.
- **Q:** How does segment isolation interact with the existing
  `SubmissionManager` serial FIFO queue and `submit_reviews`
  ThreadPoolExecutor?
  **A:** `submit_reviews` and `SubmissionManager` retain their existing
  execution models (bounded ThreadPoolExecutor and serial FIFO respectively).
  Segment isolation wraps each ThreadPoolExecutor worker's state writes into a
  per-worker segment file. The serial FIFO queue in `SubmissionManager`
  already avoids contention and does NOT use segments — it continues writing
  directly to `review-state.json` under file lock. FR-008 removes the legacy
  single-lock fallback only for the new parallel orchestration path, not for
  `SubmissionManager`.

## Problem Statement

Concurrent subagent runs can write to overlapping state locations and create
race conditions, mixed state, or accidental cross-talk between parallel
operations. This feature defines isolated state segments and reconciliation
rules so parallel agents can run safely without breaking existing workflows.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Isolated parallel file review state (Priority: P1)

As an AI reviewer, I want each parallel file-review worker to use an isolated
state segment so that one worker cannot overwrite another worker's progress.

**Why this priority**: Preventing state corruption is the core blocker for safe
parallel execution.

**Related FRs**: FR-001, FR-002

**Independent Test**: Run multiple workers on different files in parallel and
verify each worker writes only to its own scoped state segment.

**Acceptance Scenarios**:

1. **Given** two workers reviewing different files, **When** both persist state,
   **Then** no keys from worker A appear in worker B's segment.
2. **Given** one worker fails mid-run, **When** the other worker completes,
   **Then** the successful worker's state remains valid and complete.

---

### User Story 2 - Deterministic reconciliation of parallel outputs (Priority: P1)

As a workflow engine, I want deterministic reconciliation of isolated state
segments so final results are stable and reproducible.

**Why this priority**: Parallel work is only useful if merged outcomes are
predictable.

**Related FRs**: FR-003, FR-004, FR-010

**Independent Test**: Reconcile the same set of segment outputs repeatedly and
verify byte-equivalent canonical merged state payload; verify reconciliation
metadata records are either excluded from that payload or normalized so
run-variant fields do not affect determinism checks.

**Acceptance Scenarios**:

1. **Given** three completed segments, **When** reconciliation runs,
   **Then** the canonical merged state payload is byte-identical across
   repeated runs for identical inputs.
2. **Given** conflicting writes to the same logical field, **When**
   reconciliation applies precedence rules (last-writer-wins by completion
   timestamp, with lexicographic segment ID as tiebreaker), **Then** the
   selected value is consistent with documented ordering.

---

### User Story 3 - Existing batch command compatibility without legacy fallback (Priority: P2)

As a maintainer, I want existing batch commands (for example
`submit_reviews`) to continue working with their current execution model while
remaining compatible with isolated state so rollout does not break current
automation.

**Why this priority**: Compatibility reduces migration risk.

**Related FRs**: FR-005, FR-008

**Independent Test**: Run `submit_reviews` in normal mode (bounded internal
thread-level parallelism) and dry-run mode (sequential), and compare outputs
before and after the change.

**Acceptance Scenarios**:

1. **Given** `submit_reviews` running in normal mode with its existing internal
   worker parallelism, **When** isolated state is enabled, **Then** behavior and
   output match the pre-change baseline.
2. **Given** `submit_reviews` running in dry-run mode, **When** isolated state
   is enabled, **Then** behavior and output match the pre-change baseline.

---

### User Story 4 - Safe handling of global state access (Priority: P2)

As an agent, I want guarded access to global/shared state so parallel tasks
cannot corrupt cross-workflow metadata.

**Why this priority**: Shared state integrity is required for reliable
operations.

**Related FRs**: FR-006, FR-007

**Independent Test**: Simulate concurrent readers/writers on shared metadata and
verify no partial writes or malformed JSON are produced.

**Acceptance Scenarios**:

1. **Given** concurrent updates to shared metadata, **When** writes occur,
   **Then** readers always see a valid, parseable state document.
2. **Given** a write collision, **When** retry/serialization logic runs,
   **Then** update order is deterministic and no data is dropped silently.

---

### User Story 5 - Cleanup of isolated state segments (Priority: P3)

As a maintainer, I want cleanup of isolated state segments so old worker data
does not accumulate and interfere with later runs.

**Why this priority**: Cleanup is important but lower urgency than core
isolation and deterministic reconciliation.

**Related FRs**: FR-009, FR-010

**Independent Test**: Create expired and active isolated segments, run cleanup,
and confirm only expired/unused segments are removed.

**Acceptance Scenarios**:

1. **Given** isolated state exists from earlier runs, **When** cleanup executes,
   **Then** active segments are retained and expired/unused segments are removed.
2. **Given** obsolete isolated segments (terminal state older than 24 hours),
   **When** cleanup runs, **Then** only expired/unused segments are removed.

---

### Edge Cases

- Worker process crash during segment write, leaving an orphaned `active`
  segment that recovery must transition to `failed` before cleanup.
- Two workers targeting the same file or logical key.
- Reconciliation input contains one corrupted segment.
- Partial cleanup interrupted mid-operation.
- Clock skew affecting TTL/expiry decisions.
- Re-run after previous failed parallel attempt.
- Concurrent startup and teardown of the same workflow scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allocate a unique state segment per parallel worker, stored as a separate JSON file under `segments/{segment_id}.json` within the resolved workflow state
  directory (e.g. `.agdt/workflows/{identity}/{worktree_key}/segments/{segment_id}.json`).
- **FR-002**: System MUST persist worker outputs without cross-segment key
  leakage.
- **FR-003**: System MUST reconcile completed segments into a single canonical
  result deterministically.
- **FR-004**: System MUST define and enforce conflict-resolution precedence for
  overlapping logical writes using last-writer-wins by segment completion
  timestamp (UTC), with lexicographic segment ID as deterministic tiebreaker
  when timestamps are identical.
- **FR-005**: System MUST preserve existing serial workflow behavior when
  parallel mode is not used. The `SubmissionManager` serial FIFO queue and
  `submit_reviews` ThreadPoolExecutor retain their current execution models
  unchanged.
- **FR-006**: System MUST guard shared/global metadata writes (the main
  `state.json`) to avoid malformed or partial state, using the existing
  `file_locking.py` infrastructure.
- **FR-007**: System MUST surface reconciliation failures with
  actionable error output.
- **FR-008**: System MUST remove or disable legacy single-lock fallback paths
  that reintroduce shared-state contention in the new parallel orchestration
  path. This does NOT apply to `SubmissionManager` which already serializes
  writes via its FIFO queue.
- **FR-009**: System MUST implement safe cleanup rules for stale isolated
  segments, removing segments that have been in a terminal lifecycle state
  (completed or failed) for longer than 24 hours. Orphaned `active` segments
  whose owner worker/session is no longer live MUST be transitioned to
  `failed` before TTL-based cleanup is evaluated.
- **FR-010**: System MUST emit audit-friendly metadata indicating segment origin,
  lifecycle state, and reconciliation result, while keeping deterministic
  reconciliation checks scoped to the canonical merged state payload (or using
  normalized metadata fields when included).

### Non-Functional Requirements

- **NFR-001**: State operations MUST remain safe under concurrent execution.
- **NFR-002**: Reconciliation MUST be idempotent for identical inputs.
- **NFR-003**: Logging/diagnostics MUST clearly identify worker and segment IDs.
- **NFR-004**: Parallel isolation MUST NOT increase serial workflow latency by
  more than 5% (p95) compared to the pre-change baseline when parallel mode is
  not active.
- **NFR-005**: Failure handling MUST favor data integrity over partial success.
- **NFR-006**: The design MUST remain compatible with existing CLI automation
  patterns (`agdt-*` commands, background task system, `agdt-set`/`agdt-get`).
- **NFR-007**: The solution MUST avoid introducing repository-wide state
  coupling between independent workflows.

### Key Entities *(include if feature involves data)*

- **State Segment**: Worker-scoped JSON file stored at
  `segments/{segment_id}.json` with unique segment ID (UUID4), owner worker ID,
  creation timestamp (UTC), completion timestamp (UTC, set on terminal
  transition), and lifecycle status (`active` | `completed` | `failed`).
- **Reconciliation Record**: Metadata for one merge pass, including input
  segment IDs, precedence decisions (with timestamps and tiebreaker rationale),
  and final output reference path.
- **Shared Metadata Store**: The existing `state.json` file, requiring guarded
  access via `file_locking.py` for cross-worker coordination. Segment files
  themselves do not require cross-process locking since each is owned by exactly
  one worker, but segment writes MUST be atomic (for example, temp file +
  rename) so readers never observe partially written JSON.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In parallel test runs with at least 10 workers, zero cross-segment
  key leakage is observed.
- **SC-002**: Re-running reconciliation on identical inputs yields identical
  output in 100% of sampled runs.
- **SC-003**: Existing serial workflows show no functional regressions in
  baseline validation runs.
- **SC-004**: Corrupted segment injection tests fail safely without producing a
  partially merged canonical state.
- **SC-005**: Cleanup removes only expired/unused segments with zero false
  deletions in validation scenarios.
- **SC-006**: Diagnostic output for failures includes worker ID, segment ID, and
  operation stage in all sampled failure cases.

---
*Generated by Copilot SDK (claude-opus-4.6)*
