# Implementation Plan: Gate Review Requests on Unresolved PR Comment Threads

## Technical Context

- **Language/Runtime**: Python 3.10+, pip-installable package (`agentic-devtools`)
- **Key Files**:
  - `agentic_devtools/cli/ci/orchestrator.py` — orchestrator state machine (`run_ai_pr_loop`, `_request_copilot_review_if_needed`)
  - `agentic_devtools/cli/ci/github_provider.py` — `GitHubActionsProvider` with GraphQL thread queries
  - `agentic_devtools/cli/ci/provider.py` — abstract `CIPlatformProvider` base class
- **Testing**: 1:1:1 test structure under `tests/unit/cli/ci/orchestrator/` and `tests/unit/cli/ci/github_provider/`
- **CI**: `bash scripts/run-pr-checks.sh` (pytest + ruff + mypy + markdownlint)
- **Issue**: [#1566](https://github.com/ayaiayorg/agentic-devtools/issues/1566)

## Research Summary

Key design decisions:

- Method placement (new `count_unresolved_review_threads` on `GitHubActionsProvider`)
- Gate position (first precondition inside `_request_copilot_review_if_needed`)
- Parameter passing vs. instance caching (parameter chosen)
- Abstract base class impact (add abstract method to `CIPlatformProvider` for testability)

## Design Overview

```text
run_ai_pr_loop()
  │
  ├─ Step 2: get_pr_metadata(pr_number)
  │
  ├─ NEW: Fetch unresolved thread count (once)
  │    unresolved_count = provider.count_unresolved_review_threads(pr_number)
  │    (on exception → unresolved_count = -1, set error flag)
  │
  ├─ ... guards, CI checks, review evaluation ...
  │
  ├─ Step 7a: _request_copilot_review_if_needed(..., unresolved_threads=count)
  ├─ CI-path: _request_copilot_review_if_needed(..., unresolved_threads=count)
  └─ Step 7b: _request_copilot_review_if_needed(..., unresolved_threads=count)
```

Inside `_request_copilot_review_if_needed`:

```text
def _request_copilot_review_if_needed(..., unresolved_threads: int):
    if unresolved_threads != 0:  # includes -1 sentinel (fail-closed)
        return "awaiting_thread_resolution"
    # ... existing skip_reason logic ...
    # ... request_reviewer() ...
```

## Implementation Phases

### Phase 1: Provider Method (count_unresolved_review_threads)

**Deliverables**:

1. Add `count_unresolved_review_threads(pr_number: int) -> int` to `GitHubActionsProvider`
2. Decorate with `@retry_with_backoff()` (consistent with `list_review_thread_states`)
3. Reuse `_REVIEW_THREADS_QUERY`, paginate, count thread nodes with `isResolved=False`
4. Add abstract method to `CIPlatformProvider` base class for testability
5. Write unit tests: `tests/unit/cli/ci/github_provider/test_count_unresolved_review_threads.py`

**Test cases**:

- Zero threads (empty PR) → returns 0
- All threads resolved → returns 0
- Mix of resolved/unresolved → returns correct count
- Pagination (>100 threads) → accumulates across pages
- API failure → raises exception (caller handles)

### Phase 2: Orchestrator Gate Logic

**Deliverables**:

1. Add `unresolved_threads` parameter to `_request_copilot_review_if_needed` signature
2. Add gate check as first precondition (before `_get_copilot_review_request_skip_reason`)
3. Return `"awaiting_thread_resolution"` when count ≠ 0
4. Log the unresolved count when blocking
5. Write unit tests: `tests/unit/cli/ci/orchestrator/test__request_copilot_review_if_needed.py`

**Test cases**:

- `unresolved_threads=0` → proceeds to existing logic
- `unresolved_threads=3` → returns `"awaiting_thread_resolution"`
- `unresolved_threads=-1` (error sentinel) → returns `"awaiting_thread_resolution"`
- Existing skip reasons still work when `unresolved_threads=0`

### Phase 3: Orchestrator Integration (Fetch + Pass)

**Deliverables**:

1. Call `provider.count_unresolved_review_threads(pr_number)` after PR metadata resolution
2. Wrap in try/except → set `unresolved_count = -1` and `unresolved_threads_error = True` on failure
3. Pass count to all 3 call sites of `_request_copilot_review_if_needed`
4. Add `"unresolved_threads"` field to decision summary on every path
5. Add `"unresolved_threads_error": true` when API failed
6. Update existing tests in `test_run_ai_pr_loop*.py` to mock the new provider method

**Test cases**:

- Gate blocks on all 3 paths (draft-publish, CI-completion, no-review)
- Gate passes → existing behavior unchanged
- API failure → fail-closed, summary contains `-1` and error flag
- Summary always contains `unresolved_threads` field (even on non-review paths)

### Phase 4: Regression Test + Integration Verification

**Deliverables**:

1. Add PR #1545 regression test simulating the exact timeline
2. Verify all 3 call sites independently with unresolved threads
3. Run full test suite, ensure 100% coverage on new code
4. Run `bash scripts/run-pr-checks.sh`

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing tests (new param) | Medium | Medium | All call sites in tests must be updated; use `unresolved_threads=0` as default-safe value |
| GraphQL query performance | Low | Low | Same query already used by `list_review_thread_states`; single fetch per run (NFR-001) |
| Rate limiting on thread fetch | Low | Medium | `@retry_with_backoff()` handles transient failures; fail-closed on exhaustion |
| Mock updates across many test files | Medium | Low | Systematic grep + update; mock returns 0 for unrelated tests |

## Dependencies

- **Internal**: `_REVIEW_THREADS_QUERY` (existing), `@retry_with_backoff()` decorator, `_gh_api` helper
- **External**: GitHub GraphQL API (`PullRequestReviewThread.isResolved` field)
- **Test infra**: Existing mock patterns in `tests/unit/cli/ci/orchestrator/` and `tests/unit/cli/ci/github_provider/`

---
*Generated by Copilot SDK (claude-opus-4.6)*
