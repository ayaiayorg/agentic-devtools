# Implementation Plan: AI PR Loop Review Request Guards and Squash-First Strategy

## Technical Context

- **Language/Runtime**: Python >=3.10, pip-installable package (`agentic-devtools`)
- **Architecture**: Sequential action pipeline (`run_pipeline`) evaluating actions against an immutable `PRStateSnapshot` + mutable `DerivedState`
- **Key Files**:
  - `agentic_devtools/cli/ci/pipeline/snapshot.py` — `PRStateSnapshot`, `DerivedState`, `build_pr_state_snapshot`
  - `agentic_devtools/cli/ci/pipeline/runner.py` — `run_pipeline` (sequential executor)
  - `agentic_devtools/cli/ci/pipeline/command.py` — `run_ai_pr_loop_v2` (v2 entry point, action ordering)
  - `agentic_devtools/cli/ci/pipeline/actions/request_review.py` — `RequestReviewAction`
  - `agentic_devtools/cli/ci/pipeline/actions/squash.py` — `SquashAction`
  - `agentic_devtools/cli/ci/pipeline/actions/merge.py` — `MergeAction`
  - `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` — `DispatchRepairAction`
  - `agentic_devtools/cli/ci/orchestrator.py` — Legacy `run_ai_pr_loop` + `_request_copilot_review_if_needed`
  - `agentic_devtools/cli/ci/guards.py` — `DEDUP_MARKER_PREFIX`, dedup/cycle checks
  - `agentic_devtools/cli/ci/github_provider.py` — `_build_squash_commit_message`, `merge_pr`, `list_review_thread_states`
- **Test Policy**: 1:1:1 structure under `tests/unit/`, 100% coverage, TDD workflow
- **CI**: `scripts/run-pr-checks.sh`, ruff lint/format, mypy, markdownlint

## Research Summary

No separate `research.md` artifact was generated for this feature. Key decisions are inlined here:

1. **Repair-dispatch marker format**: Use a distinct marker comment `<!-- repair-dispatched-sha:{sha} -->` with constant prefix
   `REPAIR_DISPATCH_MARKER_PREFIX = "<!-- repair-dispatched-sha:"` (separate from the existing dedup marker) to avoid ambiguity when reading back markers; parsing extracts the SHA between the prefix and the closing `-->`.
2. **`total_unresolved_threads` fetching strategy**: Add `count_total_unresolved_threads` as an optional capability on
   `CIPlatformProvider` (default implementation returns `0` for providers that don't support review threads). The GitHub implementation reuses the existing `list_review_thread_states` GraphQL call, adding one GraphQL round-trip during snapshot build (budgeted against NFR-001).
3. **`DerivedState` flag initialization**: Both `repair_dispatched` and `snapshot_invalidated` are initialized to `False` at the
   start of `run_pipeline` so downstream actions always find a defined value.
4. **`CommitMessageGenerator` protocol design**: A `CommitMessageGenerator` protocol with a `DeterministicCommitMessageGenerator`
   implementation reuses the existing `_build_squash_commit_message` logic for consistency.
5. **Pipeline action ordering**: `DispatchRepairAction` and `SquashAction` are moved before `RequestReviewAction` so their derived-state flags are visible when `RequestReviewAction.evaluate()` runs.

## Design Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Pipeline Action Sequence (reordered)                                 │
├─────────────────────────────────────────────────────────────────────┤
│ 1. GuardsAction                                                      │
│ 2. PublishAction                                                     │
│ 3. DispatchRepairAction  ← sets derived.repair_dispatched            │
│ 4. SquashAction          ← removes copilot_review_pending blocker   │
│ 5. RequestReviewAction   ← NEW guards: repair, unresolved, snapshot │
│ 6. ResolveThreadsAction                                              │
│ 7. ApproveAction                                                     │
│ 8. MergeAction           ← dynamic strategy: rebase vs squash       │
└─────────────────────────────────────────────────────────────────────┘
```

Key design choices:

- **Reorder actions**: `DispatchRepairAction` and `SquashAction` BEFORE `RequestReviewAction` so their derived state is visible
- **`DerivedState` flags**: `repair_dispatched` and `snapshot_invalidated` initialized at run start in `run_pipeline`
- **`total_unresolved_threads`**: New snapshot field populated via
  `provider.count_total_unresolved_threads(...)`, with provider-specific implementation
  (GitHub can use existing `list_review_thread_states` GraphQL)
- **`REPAIR_DISPATCH_MARKER_PREFIX`**: Distinct constant `"<!-- repair-dispatched-sha:"` written only on actual dispatch
- **`CommitMessageGenerator`**: Protocol with `DeterministicCommitMessageGenerator` class

## Implementation Phases

### Phase 1: Data Model & Snapshot Extensions (Foundation)

**Deliverables:**

1. Add `total_unresolved_threads: int = 0` field to `PRStateSnapshot`
2. Add `count_total_unresolved_threads` helper in `snapshot.py` that calls `provider.count_total_unresolved_threads(...)`
3. Call the new helper in `build_pr_state_snapshot` to populate the field
4. Add `REPAIR_DISPATCH_MARKER_PREFIX = "<!-- repair-dispatched-sha:"` constant in `guards.py`
5. Initialize `derived.set("repair_dispatched", False)` and `derived.set("snapshot_invalidated", False)` at the start of `run_pipeline`

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/snapshot.py`
- `agentic_devtools/cli/ci/guards.py`
- `agentic_devtools/cli/ci/pipeline/runner.py`
- `agentic_devtools/cli/ci/provider.py` (add `count_total_unresolved_threads` abstract method or make it optional)

### Phase 2: DispatchRepairAction — Repair Marker & DerivedState Flag (FR-001, FR-002a)

**Deliverables:**

1. After successful dispatch in `DispatchRepairAction.execute()`, call `derived.set("repair_dispatched", True)`
2. After successful dispatch, write a `REPAIR_DISPATCH_MARKER_PREFIX` comment with HEAD SHA
3. Add provider method `write_repair_dispatch_marker(pr_number, head_sha)` and `read_repair_dispatch_marker(pr_number) -> str | None`

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py`
- `agentic_devtools/cli/ci/github_provider.py`
- `agentic_devtools/cli/ci/provider.py` (optional methods)
- `agentic_devtools/cli/ci/guards.py` (new marker helpers)

### Phase 3: RequestReviewAction — New Guards (FR-001, FR-002, FR-002a, FR-003, FR-006, FR-007, FR-010)

**Deliverables:**

1. Add guard: skip if `derived.repair_dispatched == True` → reason `"repair_dispatched"`
2. Add guard: skip if `snapshot.active_session == True` → reason `"active_session"`
3. Add guard: skip if prior-run repair marker SHA matches current HEAD → reason `"repair_dispatched_prior_run"`
4. Add guard: skip if `snapshot.total_unresolved_threads > 0` → reason `"unresolved_comments"`
5. Add guard: skip if `derived.snapshot_invalidated == True` → reason `"snapshot_invalidated"`
6. Include `"reason"` in ActionResult details for all skip paths

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/actions/request_review.py`

### Phase 4: SquashAction — Remove Pending Review Blocker (FR-005)

**Deliverables:**

1. Remove the `no_pending_review` precondition check from `SquashAction.evaluate()`
2. Keep only `no_active_session` as the session-related blocker

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/actions/squash.py`

### Phase 5: Pipeline Reordering (FR-006, FR-007)

**Deliverables:**

1. Reorder actions in `command.py` so `DispatchRepairAction` and `SquashAction` precede `RequestReviewAction`
2. Update `run_pipeline` so snapshot invalidation sets `derived.set("snapshot_invalidated", True)` and
   `RequestReviewAction` reports `reason="snapshot_invalidated"` (either via evaluation after invalidation or a runner-generated SKIP result).

**New action order:**

```python
actions = [
    GuardsAction(),
    PublishAction(),
    DispatchRepairAction(),
    SquashAction(),
    RequestReviewAction(),
    ResolveThreadsAction(),
    ApproveAction(),
    MergeAction(),
]
```

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/command.py`
- `agentic_devtools/cli/ci/pipeline/runner.py`

### Phase 6: MergeAction — Dynamic Strategy (FR-008, FR-009)

**Deliverables:**

1. Add `CommitMessageGenerator` protocol in new file `agentic_devtools/cli/ci/pipeline/commit_message.py`
2. Implement `DeterministicCommitMessageGenerator` using same logic as `_build_squash_commit_message`
3. Modify `MergeAction.execute()` to select `"squash"` when `snapshot.commit_count > 1`, `"rebase"` otherwise
4. When squash merge, generate commit message via `DeterministicCommitMessageGenerator`
5. Pass commit message to `provider.merge_pr()` (extend signature if needed, or use existing `commit_title`/`commit_message` API params)

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/actions/merge.py`
- `agentic_devtools/cli/ci/pipeline/commit_message.py` (NEW)
- `agentic_devtools/cli/ci/provider.py` (extend `merge_pr` signature)
- `agentic_devtools/cli/ci/github_provider.py` (update `merge_pr` implementation)

### Phase 7: Legacy Orchestrator Alignment (FR-004, NFR-003)

**Deliverables:**

1. Add repair dispatch and unresolved comments checks to `_request_copilot_review_if_needed` in `orchestrator.py`
2. Add repair marker reading before review request in the legacy path
3. Add logging at INFO level for all new guard decisions

**Files modified:**

- `agentic_devtools/cli/ci/orchestrator.py`

### Phase 8: Tests (NFR-004, SC-006, SC-007)

**Deliverables (per 1:1:1 structure):**

| Source change | Test location |
|---|---|
| `snapshot.py` → `total_unresolved_threads` | `tests/unit/cli/ci/pipeline/snapshot/test_prstatesnapshot.py` (extend) |
| `snapshot.py` → `count_total_unresolved_threads` | `tests/unit/cli/ci/pipeline/snapshot/test_count_total_unresolved_threads.py` |
| `runner.py` → derived flag init | `tests/unit/cli/ci/pipeline/runner/test_run_pipeline.py` (extend) |
| `request_review.py` → new guards | `tests/unit/cli/ci/pipeline/actions/request_review/test_requestreviewaction.py` (extend) |
| `squash.py` → removed blocker | `tests/unit/cli/ci/pipeline/actions/squash/test_squashaction.py` (extend) |
| `merge.py` → dynamic strategy | `tests/unit/cli/ci/pipeline/actions/merge/test_mergeaction.py` (extend) |
| `dispatch_repair.py` → derived flag | `tests/unit/cli/ci/pipeline/actions/dispatch_repair/test_dispatchrepairaction.py` (extend) |
| `commit_message.py` → protocol | `tests/unit/cli/ci/pipeline/commit_message/test_deterministiccommitmessagegenerator.py` |
| `command.py` → reordering | `tests/unit/cli/ci/pipeline/command/test_run_ai_pr_loop_v2.py` (extend) |
| `orchestrator.py` → legacy guards | `tests/unit/cli/ci/orchestrator/test_run_ai_pr_loop.py` (extend) |
| `guards.py` → new marker | `tests/unit/cli/ci/guards/test_repair_dispatch_marker.py` |

Each new guard check gets ≥2 test cases (positive: SKIP triggered; negative: guard passes).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pipeline reorder breaks existing test expectations | Medium | Medium | Run full test suite after reorder; update test assertions |
| `list_review_thread_states` GraphQL adds latency | Low | Low | Adds 1 GraphQL call during snapshot build; keep within NFR-001 by reusing this call for `total_unresolved_threads` |
| `total_unresolved_threads` includes bot/stale threads | Medium | Low | Spec explicitly says "all unresolved regardless of author" — this is intentional |
| `merge_pr` signature change breaks ADO provider | Low | Medium | Make `commit_message` param optional with default `None`; ADO provider ignores it |
| Legacy orchestrator diverges from pipeline behavior | Medium | Medium | Phase 7 explicitly mirrors pipeline guards; shared helper functions |

## Dependencies

### Internal

- `CIPlatformProvider` ABC — extending with optional methods
- `DerivedState` — relies on `__getattr__` delegation for new flags
- `run_pipeline` — modifying initialization and flag propagation
- Existing `list_review_thread_states` GraphQL method — reused for `total_unresolved_threads`

### External

- GitHub REST API (`/pulls/{n}/merge` with `commit_title`/`commit_message` params for squash)
- GitHub GraphQL API (review thread resolution status — already used)
- No new third-party dependencies required

---
*Generated by Copilot SDK (claude-opus-4.6)*
