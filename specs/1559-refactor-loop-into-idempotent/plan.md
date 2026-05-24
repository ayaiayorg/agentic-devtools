# Implementation Plan: Idempotent Action Evaluator for AI PR Loop

## 1. Technical Context

**Stack**: Python 3.10+ package compatibility (runs in Python 3.11+ GitHub Actions environment), `gh` CLI for GitHub API, GitHub Actions CI  
**Key files**:

- `agentic_devtools/cli/ci/orchestrator.py` (1789 lines) — current event-branching orchestrator
- `agentic_devtools/cli/ci/guards.py` (453 lines) — guard checks + squash-wait state machine
- `agentic_devtools/cli/ci/provider.py` — `CIPlatformProvider` ABC
- `agentic_devtools/cli/ci/github_provider.py` — GitHub implementation
- `agentic_devtools/cli/ci/models.py` — shared dataclasses (`EventPayload`, `PRMetadata`, etc.)
- `agentic_devtools/cli/ci/evaluator/` — post-agent evaluator (lock, snapshot, classifier, actions)

**Architecture decision**: Replace the 1789-line event-branching `run_ai_pr_loop()` function with a sequential pipeline of 8 action evaluators, each self-contained with precondition checks and
idempotent execution.

## 2. Research Summary

See [research.md](research.md) for detailed decisions on:

- Pipeline architecture pattern (sequential evaluator chain vs. DAG)
- Active session detection strategy (Issues Events API pagination)
- Summary comment management (sentinel-based collapse)
- DerivedState pattern (proxy with snapshot fallthrough)

## 3. Design Overview

```text
┌──────────────────────────────────────────────────────┐
│                  run_ai_pr_loop()                      │
│                                                        │
│  1. Build PRStateSnapshot (immutable)                  │
│  2. Create DerivedState (mutable proxy)                │
│  3. Acquire evaluator lock                             │
│  4. Execute pipeline:                                  │
│     ┌─────────────────────────────────────────────┐   │
│     │  Action 1: Guards                            │   │
│     │  Action 2: Publish                           │   │
│     │  Action 3: Request Review                    │   │
│     │  Action 4: Resolve Threads                   │   │
│     │  Action 5: Dispatch Repair                   │   │
│     │  Action 6: Squash                            │   │
│     │  Action 7: Approve                           │   │
│     │  Action 8: Merge                             │   │
│     └─────────────────────────────────────────────┘   │
│  5. Build PipelineRunSummary                           │
│  6. Post/collapse summary comment                      │
│  7. Release lock                                       │
└──────────────────────────────────────────────────────┘
```

Each action implements a common interface:

```python
class Action(Protocol):
    name: str
    def evaluate(self, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult: ...
    def execute(self, provider: CIPlatformProvider, snapshot: PRStateSnapshot, derived: DerivedState) -> ActionResult: ...
```

The pipeline wraps each action in try/except. Guards (action 1) failing blocks actions 2–8.

## 4. Implementation Phases

### Phase 1: Data Models & Pipeline Framework (Foundation)

**Deliverables**: New module `agentic_devtools/cli/ci/pipeline/` with core types.

**Tasks**:

1. Create `agentic_devtools/cli/ci/pipeline/__init__.py`
2. Create `agentic_devtools/cli/ci/pipeline/models.py`:
   - `ActionDecision` enum: `EXECUTE`, `SKIP`, `BLOCKED`, `BLOCKED_BY_GUARD`
   - `ActionResult` dataclass: `name`, `decision`, `preconditions` (dict[str, bool]), `details` (str), `error` (Optional[str])
   - `PipelineRunSummary` dataclass: `results` (list[ActionResult]), `snapshot` (PRStateSnapshot), `run_url` (str)
3. Create `agentic_devtools/cli/ci/pipeline/snapshot.py`:
   - `PRStateSnapshot` frozen dataclass (head_sha, commit_count, ci_status, review_state, active_session, unresolved_threads, labels, is_draft, mergeable, requested_reviewers, etc.)
   - `DerivedState` class with `__getattr__` fallthrough to snapshot
   - `build_pr_state_snapshot()` function that gathers all state in one pass
4. Create `agentic_devtools/cli/ci/pipeline/runner.py`:
   - `run_pipeline()` function: iterates actions, wraps in try/except, handles guard-blocks
   - Emits `::group::`/`::endgroup::` per action
   - Returns `PipelineRunSummary`
5. Create `agentic_devtools/cli/ci/pipeline/session_detector.py`:
   - `is_copilot_session_active()` using Issues Events API with ID ordering
   - Replaces entire squash-wait state machine
6. Write tests for all new modules under `tests/unit/cli/ci/pipeline/`

### Phase 2: Implement Actions 1–4

**Deliverables**: Guards, Publish, Request-Review, Resolve-Threads actions.

**Tasks**:

1. Create `agentic_devtools/cli/ci/pipeline/actions/__init__.py`
2. Create `agentic_devtools/cli/ci/pipeline/actions/guards.py`:
   - Reuses existing `check_fork_pr`, `check_exclusion_labels`, `check_privileged_paths`, `check_docker_files`, `check_deduplication`, `check_cycle_limit`
   - Returns `BLOCKED` with reason on any guard failure
   - Exception → fail closed as `BLOCKED`
3. Create `agentic_devtools/cli/ci/pipeline/actions/publish.py`:
   - Preconditions: `is_draft == True`
   - Skip if not draft
   - Execute: squash_before_publish + publish_pr
   - Updates `DerivedState.is_draft = False`
4. Create `agentic_devtools/cli/ci/pipeline/actions/request_review.py`:
   - Preconditions: not draft (via DerivedState), no effective Copilot review on HEAD, Copilot not already requested
   - Execute: `provider.request_reviewer()`
5. Create `agentic_devtools/cli/ci/pipeline/actions/resolve_threads.py`:
   - Preconditions: no active Copilot session, no pending Copilot review on HEAD, unresolved threads exist from prior commit
   - Execute: SDK verification + resolve per thread
6. Write comprehensive tests for each action

### Phase 3: Implement Actions 5–8

**Deliverables**: Dispatch-Repair, Squash, Approve, Merge actions.

**Tasks**:

1. Create `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py`:
   - Preconditions: no active session, CI failed OR actionable Copilot review exists, dedup/cycle limits not exceeded
   - Execute: `provider.dispatch_repair()`
2. Create `agentic_devtools/cli/ci/pipeline/actions/squash.py`:
   - Preconditions: commits_above_merge_base > 1, no active session (coding or review), CI passing
   - Execute: `provider.squash_post_repair()`
3. Create `agentic_devtools/cli/ci/pipeline/actions/approve.py`:
   - Preconditions: no existing approval on current HEAD SHA, Copilot review is clean, CI passing, no unresolved threads
   - Execute: `provider.approve_pr()`
4. Create `agentic_devtools/cli/ci/pipeline/actions/merge.py`:
   - Preconditions: approved, CI passing, `ai-auto-merge-allowed` label, mergeable, no unresolved threads
   - Execute: `provider.merge_pr()`
5. Write comprehensive tests for each action

### Phase 4: Summary Comment System

**Deliverables**: PR summary comment posting with collapse mechanism.

**Tasks**:

1. Create `agentic_devtools/cli/ci/pipeline/summary.py`:
   - `render_summary_comment()` — generates markdown table from `PipelineRunSummary`
   - Sentinel: `<!-- agdt:ai-pr-loop-summary -->`
   - Collapsed sentinel: `<!-- agdt:ai-pr-loop-summary-collapsed -->`
   - `<details>` block for state snapshot
   - Enforce < 2000 chars visible portion
2. Create `agentic_devtools/cli/ci/pipeline/summary_collapse.py`:
   - `collapse_prior_summaries()` — finds and edits prior summary comments
   - Provider-agnostic path uses existing `provider.find_comment()` + `provider.update_comment()`
   - Optional GitHub-only enhancement may use `GitHubProvider.list_issue_comments()` via capability detection (`getattr`) to collapse legacy duplicates
3. Integrate into `run_pipeline()`: post summary after all actions complete
4. Write tests

### Phase 5: Integration & Migration

**Deliverables**: New entry point replaces old orchestrator, squash-wait removal.

**Tasks**:

1. Create `agentic_devtools/cli/ci/pipeline/command.py`:
   - New `run_ai_pr_loop_v2()` that builds snapshot → runs pipeline → posts summary
   - Maintains same function signature as current `run_ai_pr_loop()` for drop-in replacement
2. Update `agentic_devtools/cli/ci/commands.py` to call the new pipeline
3. Remove squash-wait code from `guards.py`:
   - Delete `read_squash_wait_marker`, `write_squash_wait_marker`, `delete_squash_wait_marker`
   - Delete `_build_squash_wait_body`, `SQUASH_WAIT_MARKER_PREFIX`, `SQUASH_WAIT_MAX_ATTEMPTS`
4. Remove `_run_squash_wait_step()` and event-branching logic from `orchestrator.py`
5. Keep `orchestrator.py` as a thin compatibility shim (or delete if no external references)
6. Migrate tests: update `tests/unit/cli/ci/orchestrator/` to cover new pipeline
7. Delete `tests/unit/cli/ci/guards/test_squash_wait_marker.py`
8. Run full test suite, verify 100% coverage on modified files

### Phase 6: Validation & Hardening

**Deliverables**: Integration tests, edge case handling, performance validation.

**Tasks**:

1. Add integration test: 50 consecutive runs on unchanged state → 0 duplicate API calls
2. Add integration test: 3 trigger types produce identical action evaluations
3. Add integration test: draft → merged in ≤ 5 triggers
4. Verify NFR-001: single run < 120s under normal conditions
5. Add concurrent-run detection (existing lock mechanism gates pipeline)
6. Add re-validation of "PR still open" before merge execution
7. Final cleanup: ensure zero references to squash-wait in production code

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Regression in existing PR automation during migration | Medium | High | Keep old `run_ai_pr_loop` as fallback behind feature flag during rollout |
| Active session detection false negatives (API pagination issues) | Low | Medium | Full pagination with ID-based ordering; log all events for debugging |
| Summary comment exceeds GitHub size limit | Low | Low | Enforce < 2000 char visible; collapse state into `<details>` |
| Concurrent runs cause race conditions | Medium | Medium | Existing lock mechanism gates entire pipeline; clean exit on lock failure |
| Provider capability mismatch across platforms | Low | Medium | Keep `CIPlatformProvider` unchanged; treat GitHub extras (`count_commits_above_merge_base`, optional summary-duplicate collapse) as capability-detected via `getattr` with safe fallbacks |

## 6. Dependencies

**Internal**:

- `CIPlatformProvider` ABC (no new abstract methods; pipeline uses existing interface)
- `GitHubProvider.list_pr_issue_events()` (already implemented)
- `GitHubProvider.count_commits_above_merge_base()` (GitHub capability, invoked via `getattr` fallback)
- `GitHubProvider.list_issue_comments()` (optional GitHub capability for legacy summary-duplicate collapse)
- Evaluator lock mechanism (reuse as-is)
- Existing guard functions (reuse, don't modify)

**External**:

- GitHub Issues Events API (for session detection)
- GitHub Actions `::group::` log annotations
- `gh` CLI for all API interactions

---
*Generated by Copilot SDK (claude-opus-4.6)*
