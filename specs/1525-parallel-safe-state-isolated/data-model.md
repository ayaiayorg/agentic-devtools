# Data Model: Parallel-safe State Isolation

## Overview

This feature introduces isolated worker segment files that are reconciled into a
single canonical review state.

## Entities

### StateSegment

- `segment_id` (str): Hyphenated UUID4 string (`str(uuid.uuid4())`)
- `owner_worker_id` (str): Logical worker identifier
- `owner_pid` (int): Process ID used for orphan detection
- `status` (enum): `active` | `completed` | `failed`
- `created_utc` (str): ISO-8601 UTC timestamp
- `completed_utc` (str | null): ISO-8601 UTC timestamp when terminal
- `data` (dict[str, Any]): Worker-local payload

### SegmentStatus

- `active`: Worker in progress
- `completed`: Worker finished successfully
- `failed`: Worker failed or orphan recovery marked terminal

### ReconciliationResult

- `merged_data` (dict[str, Any]): Canonical merged payload
- `record` (ReconciliationRecord): Audit metadata for deterministic merge

### ReconciliationRecord

- `record_id` (str): UUID4 identifier
- `input_segment_ids` (list[str]): Segments reconciled
- `precedence_decisions` (list[PrecedenceDecision]): Conflict outcomes
- `output_path` (str): Canonical target (`reviews/review-state.json`)
- `reconciled_utc` (str): ISO-8601 UTC timestamp
- `canonical_payload_hash` (str): SHA-256 of deterministic JSON payload

### PrecedenceDecision

- `key` (str): Logical field that conflicted
- `winning_segment_id` (str): Selected segment
- `winning_timestamp` (str): Completion timestamp used for ordering
- `losing_segment_ids` (list[str]): Segments that lost precedence
- `reason` (str): `timestamp` or `tiebreaker`

## Storage Layout

- Segments: `.agdt/workflows/{identity}/{worktree_key}/segments/{segment_id}.json`
- Canonical review state: `.agdt/workflows/{identity}/{worktree_key}/reviews/review-state.json`
- Optional reconciliation audit log: under `segments/` (implementation-defined file name)

---
*Generated for issue #1525 plan artifacts.*
