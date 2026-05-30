# Implementation Plan: Remove active_session Gate from dispatch_repair

## Technical Context

- **Language/Framework**: Python 3.x, CLI package (`agentic-devtools`)
- **Key files**:
  - `agentic_devtools/cli/ci/pipeline/session_detector.py` — current events-based session detection
  - `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` — `DispatchRepairAction`
  - `agentic_devtools/cli/ci/pipeline/actions/squash.py` — `SquashAction`
  - `agentic_devtools/cli/ci/pipeline/actions/request_review.py` — `RequestReviewAction`
  - `agentic_devtools/cli/ci/pipeline/snapshot.py` — `PRStateSnapshot` + `build_pr_state_snapshot()`
  - `agentic_devtools/cli/ci/pipeline/summary.py` — summary renderer
- **Test structure**: 1:1:1 policy under `tests/unit/cli/ci/pipeline/`
- **External tools**: `gh` CLI (already required), specifically `gh agent-task list`
- **Coverage requirement**: 100% branch coverage on all modified/new code

## Research Summary

See [research.md](research.md) for decisions on:

- `gh agent-task list` JSON schema and field selection
- Active status values (authoritative set)
- Fail-open vs fail-closed design rationale
- Subprocess invocation pattern (no SDK dependency)

## Design Overview

```text
┌──────────────────────────────────────────────────────────┐
│ build_pr_state_snapshot()                                │
│  - REMOVES call to is_copilot_session_active()           │
│  - active_session field defaults to False (unused)       │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────┐  ┌──────────────────────────────┐
│ DispatchRepairAction     │  │ SquashAction / RequestReview  │
│  - REMOVES session gate  │  │  - REPLACES snapshot read     │
│  - No session awareness  │  │    with direct detector call  │
└──────────────────────────┘  └──────────────────────────────┘
                                        │
                              ┌──────────▼───────────────────┐
                              │ is_copilot_session_active_    │
                              │   via_agent_task()            │
                              │ - subprocess: gh agent-task   │
                              │   list --json ...             │
                              │ - Fail-open (False on error)  │
                              │ - 10s timeout, no retries     │
                              └──────────────────────────────┘
```

## Implementation Phases

### Phase 1: New Session Detector (FR-003, FR-004, FR-005)

**Deliverable**: New `is_copilot_session_active_via_agent_task()` function with full test coverage.

**Tasks**:

1. Add `is_copilot_session_active_via_agent_task(repo, pr_number, *, timeout_seconds=10)` to `session_detector.py`
2. Implement subprocess call to `gh agent-task list --repo <repo> --json id,status,pullRequestNumber,createdAt`
3. Parse JSON, filter tasks by `pullRequestNumber == pr_number`
4. Return `True` if any matching task has status in `{"queued", "requested", "waiting", "in_progress", "running"}`
5. Catch all exceptions (subprocess errors, JSON parse, timeout, missing binary) → return `False` + WARNING log
6. Create test file `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_via_agent_task.py`
7. Test cases: running task → True, stopped → False, empty list → False, multiple tasks with mixed status → True, timeout → False, non-zero exit → False, malformed JSON → False, missing binary →
   False, permission error → False

### Phase 2: Deprecate Old Detector (FR-006)

**Deliverable**: Old `is_copilot_session_active()` emits `DeprecationWarning`.

**Tasks**:

1. Add `warnings.warn(...)` with `DeprecationWarning` and `stacklevel=2` at the top of `is_copilot_session_active()`
2. Update existing test to expect the deprecation warning
3. Create test `tests/unit/cli/ci/pipeline/session_detector/test_is_copilot_session_active_deprecated.py` verifying the warning

### Phase 3: Remove Session Gate from DispatchRepairAction (FR-001, FR-002)

**Deliverable**: `dispatch_repair` evaluates without any session awareness.

**Tasks**:

1. Remove lines 52–60 from `dispatch_repair.py` (the `no_active_session` precondition block)
2. Update existing tests:
   - `test_skip_when_active_session` → remove or convert to test that `active_session=True` does NOT cause skip
   - Add test confirming `no_active_session` key is absent from preconditions
   - Confirm execute when `ci_status="failing"` regardless of `active_session`
3. Verify `evaluate()` only SKIPs for: no repair needed, CI pending

### Phase 4: Update Snapshot Builder (FR-007)

**Deliverable**: `build_pr_state_snapshot()` no longer calls `is_copilot_session_active()`.

**Tasks**:

1. Remove `from .session_detector import is_copilot_session_active` import from `snapshot.py`
2. Remove line 174 (`active_session = is_copilot_session_active(provider, pr_number)`)
3. Remove `active_session=active_session` from the constructor call (field defaults to `False`)
4. Update snapshot builder tests to not mock/expect the session detector call
5. Verify `PRStateSnapshot.active_session` field still exists with default `False`

### Phase 5: Migrate SquashAction and RequestReviewAction (FR-008)

**Deliverable**: Both actions call new detector directly instead of reading `snapshot.active_session`.

**Tasks**:

1. In `squash.py`:
   - Add import of `is_copilot_session_active_via_agent_task`
   - Replace `snapshot.active_session` read with `is_copilot_session_active_via_agent_task(snapshot.base_repo_full_name, snapshot.pr_number)`
   - Update `evaluate` signature or add `repo`/`pr_number` access via snapshot fields
2. In `request_review.py`:
   - Same pattern as squash
3. Update tests in `test_squashaction.py`:
   - Mock `is_copilot_session_active_via_agent_task` instead of setting `active_session=True`
   - Verify function is called with correct `repo` and `pr_number`
4. Update tests in `test_requestreviewaction.py`:
   - Same pattern as squash tests

### Phase 6: Update Summary Renderer (FR-008e)

**Deliverable**: Summary shows `N/A` for session state.

**Tasks**:

1. In `summary.py` line 167, change `str(snapshot.active_session)` to `"N/A"`
2. Update summary renderer tests to expect `N/A` instead of `True`/`False`

### Phase 7: Final Validation

**Tasks**:

1. Run `agdt-test` (full suite) — verify 0 failures
2. Run `bash scripts/targeted-checks.sh` — verify formatting, linting, coverage
3. Verify no production code imports or calls `is_copilot_session_active()` (only the deprecated function body remains)
4. Run `python scripts/validate_test_structure.py` — verify test structure compliance

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| `gh agent-task list` JSON schema changes | Detector returns wrong results | Low | Pin expected fields in `--json` flag; fail-open means worst case is false-negative |
| `gh agent-task` subcommand not available (old CLI) | Detector always returns False | Medium | Fail-open by design; log warning for operator visibility |
| Tests rely on `snapshot.active_session=True` causing SKIP in dispatch_repair | Tests break during Phase 3 | High | Update tests in same commit as code change |
| SquashAction/RequestReviewAction subprocess call adds latency to pipeline loop | Slower loop iterations | Low | 10s timeout bounds worst case; subprocess is fast when `gh` is healthy |
| Removing session gate causes repair storms (many comments posted rapidly) | Excessive comments on PR | Low | Existing dedup + cycle limit guards prevent this (already tested) |

## Dependencies

- **External**: `gh` CLI with `agent-task` subcommand support (GitHub CLI ≥ version TBD)
- **Internal**: `PRStateSnapshot.base_repo_full_name` field (already exists, populated by snapshot builder)
- **No new pip dependencies** (uses stdlib `subprocess`, `json`, `logging`)

---
*Generated by Copilot SDK (claude-opus-4.6)*
