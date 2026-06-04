# Implementation Plan: RebaseAction for Stale Single-Commit PRs

## Technical Context

- **Language/Runtime**: Python 3.11+, pip-installable package `agentic_devtools`
- **Architecture**: Pipeline-based action sequencing (`Action` protocol with `evaluate` + `execute` methods)
- **Key Files**:
  - `agentic_devtools/cli/ci/pipeline/actions/` — action modules
  - `agentic_devtools/cli/ci/pipeline/snapshot.py` — `PRStateSnapshot` frozen dataclass + `build_pr_state_snapshot()`
  - `agentic_devtools/cli/ci/pipeline/runner.py` — sequential runner with invalidation semantics
  - `agentic_devtools/cli/ci/pipeline/command.py` — action list assembly
  - `agentic_devtools/cli/ci/provider.py` — `CIPlatformProvider` ABC
  - `agentic_devtools/cli/ci/github_provider.py` — concrete GitHub implementation
- **Testing**: 1:1:1 structure under `tests/unit/`, 100% branch coverage required, `agdt-test-*` commands
- **Existing Patterns**: `SquashAction` is the closest analog — same precondition pattern, same `invalidates_snapshot` behavior

## Research Summary

See [research.md](research.md) for detailed decisions on:

1. **`commits_behind` population strategy** — GitHub compare API in `build_pr_state_snapshot()`
2. **Provider method design** — new `rebase_onto_base()` method on `CIPlatformProvider`
3. **Pipeline ordering** — after Squash, before ResolveThreads (adjusting current order)
4. **Conflict resolution reuse** — existing `_resolve_rebase_conflicts_via_sdk` from squash path

## Design Overview

```text
Pipeline Action Sequence (new):
Guards → Publish → DispatchRepair → ResolveThreads → Squash → Rebase → RequestReview → Approve → Merge
                                                                  ↑ NEW
```

**Note**: The spec says "after Squash, before ResolveThreads" but the current ordering is `DispatchRepair → ResolveThreads → Squash`. The spec's intent is clear: Rebase goes after Squash (so squash's
internal rebase runs first for multi-commit PRs) and before RequestReview. The correct new ordering is:

```text
Guards → Publish → DispatchRepair → ResolveThreads → Squash → Rebase → RequestReview → Approve → Merge
```

**RebaseAction** is a thin action that:

- `evaluate()`: Pure data-driven — checks `snapshot.commits_behind`, repair/session preconditions
- `execute()`: Calls `provider.rebase_onto_base(...)` which encapsulates fetch + rebase + conflict-resolution + force-push-with-lease

**Snapshot extension**: `PRStateSnapshot` gains `commits_behind: int = 0`, populated via GitHub compare API during `build_pr_state_snapshot()`.

**Provider extension**: `CIPlatformProvider` ABC gains abstract method `rebase_onto_base()`; `GitHubProvider` implements it using existing git primitives.

## Implementation Phases

### Phase 1: Snapshot Extension (`commits_behind` field)

**Deliverables:**

1. Add `commits_behind: int = 0` field to `PRStateSnapshot`
2. Add `_count_commits_behind()` helper in `snapshot.py` (calls provider's compare API)
3. Populate `commits_behind` in `build_pr_state_snapshot()` after commit count
4. Add `count_commits_behind` method to `CIPlatformProvider` ABC (non-abstract, default returns 0)
5. Implement `count_commits_behind` in `GitHubProvider` using `gh api /repos/{owner}/{repo}/compare/{base}...{head}` → `behind_by` field

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/snapshot.py`
- `agentic_devtools/cli/ci/provider.py`
- `agentic_devtools/cli/ci/github_provider.py`

**Tests:**

- `tests/unit/cli/ci/pipeline/snapshot/test_prstatesnapshot.py` (new field)
- `tests/unit/cli/ci/pipeline/snapshot/test_build_pr_state_snapshot.py` (commits_behind population)
- `tests/unit/cli/ci/github_provider/test_count_commits_behind.py`

---

### Phase 2: Provider Method (`rebase_onto_base`)

**Deliverables:**

1. Add `rebase_onto_base(*, pr_number, base_branch, head_branch, head_sha) -> None` as abstract method on `CIPlatformProvider`
2. Implement in `GitHubProvider`:
   - `git fetch origin {base_branch} {head_branch}`
   - `git checkout {head_branch}`
   - `git rebase origin/{base_branch}`
   - On conflict: attempt `_resolve_rebase_conflicts_via_sdk`, else `git rebase --abort` + raise
   - `git push --force-with-lease origin HEAD:{head_branch}`
3. Define custom exceptions: `RebaseConflictError`, `ForceWithLeaseError`

**Files modified:**

- `agentic_devtools/cli/ci/provider.py`
- `agentic_devtools/cli/ci/github_provider.py`

**Files created:**

- `agentic_devtools/cli/ci/pipeline/exceptions.py` (or add to existing models)

**Tests:**

- `tests/unit/cli/ci/github_provider/test_rebase_onto_base.py`

---

### Phase 3: RebaseAction Implementation

**Deliverables:**

1. Create `agentic_devtools/cli/ci/pipeline/actions/rebase.py` with `RebaseAction` class
2. `evaluate()`:
   - Check `commits_behind > 0` → SKIP if 0
   - Check `no_repair_dispatched` → SKIP if repair dispatched
   - Check `no_active_session` → SKIP if active session
   - Return EXECUTE with details showing commits behind count
3. `execute()`:
   - Call `provider.rebase_onto_base(...)`
   - On `RebaseConflictError` → return BLOCKED
   - On `ForceWithLeaseError` → return FAILED
   - On success → return EXECUTE with `invalidates_snapshot=True`
4. Does NOT set `runs_after_invalidation = True`

**Files created:**

- `agentic_devtools/cli/ci/pipeline/actions/rebase.py`

**Tests:**

- `tests/unit/cli/ci/pipeline/actions/rebase/test_rebaseaction.py` (≥15 test cases)

---

### Phase 4: Pipeline Integration

**Deliverables:**

1. Import `RebaseAction` in `command.py`
2. Insert `RebaseAction()` after `SquashAction()` in the actions list
3. Verify existing tests still pass (no regressions)

**Files modified:**

- `agentic_devtools/cli/ci/pipeline/command.py`
- `agentic_devtools/cli/ci/pipeline/actions/__init__.py` (export)

**Tests:**

- Integration-level test asserting pipeline order
- Verify `run_pipeline` handles Rebase correctly with snapshot invalidation

---

### Phase 5: ADO Provider Stub

**Deliverables:**

1. Add `rebase_onto_base` stub to `ado_provider.py` (raise `NotImplementedError`)
2. Add `count_commits_behind` stub to `ado_provider.py` (return 0)

**Files modified:**

- `agentic_devtools/cli/ci/ado_provider.py`

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Double-rebase when Squash already rebased | Low | Medium | RebaseAction evaluates on *refreshed* snapshot next iteration; `commits_behind == 0` after Squash's internal rebase |
| `--force-with-lease` failure in race condition | Medium | Low | Return FAILED, retry next iteration — designed into the protocol |
| GitHub compare API rate limits | Low | Low | Same rate limits as existing `list_check_runs`; single call per snapshot build |
| Conflict resolution SDK not available | Medium | Medium | Graceful degradation: abort rebase, return BLOCKED, manual intervention |
| Existing tests assume no `commits_behind` field | Low | Low | Default value is 0, frozen dataclass is backward-compatible |

## Dependencies

**Internal:**

- `_resolve_rebase_conflicts_via_sdk` helper in `github_provider.py` (reuse existing)
- `is_copilot_session_active_via_agent_task` from `session_detector.py`
- `DerivedState.repair_dispatched` attribute pattern from `SquashAction`

**External:**

- GitHub Compare API (`GET /repos/{owner}/{repo}/compare/{base}...{head}`) — returns `behind_by`
- `git` CLI (fetch, rebase, push) — already used by squash path
- SDK conflict resolver (optional, graceful degradation)

---
*Generated by Copilot SDK (claude-opus-4.6)*
