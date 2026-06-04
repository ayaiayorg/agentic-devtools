# Implementation Plan: Auto-apply Code Review Suggestions via GraphQL

## Technical Context

**Stack**: Python 3.10+, `gh` CLI for GitHub API access, GitHub GraphQL API v4, existing idempotent pipeline runner architecture.

**Key dependencies**:

- `agentic_devtools.cli.ci.pipeline` — action protocol, runner, models
- `agentic_devtools.cli.ci.github_provider` — `_gh_api()` helper, `list_review_comments()`
- `agentic_devtools.cli.ci.retry` — `retry_with_backoff` decorator, `RetryableError`
- `agentic_devtools.cli.ci.guards` — existing guard functions

**Architecture decisions**:

- New action follows the `Action` protocol (`evaluate()` + `execute()`)
- Positioned between `PublishAction` and `DispatchRepairAction` in the sequence (after `GuardsAction`)
- Uses `invalidates_snapshot = True` to trigger snapshot refresh for downstream actions
- Passes exclusion data via runner-scoped context that survives snapshot refresh
- GraphQL calls routed through `CIPlatformProvider` methods (provider-backed GitHub GraphQL helper)

## Research Summary

See [research.md](research.md) and [checklists/requirements.md](checklists/requirements.md) for detailed decisions on:

- GraphQL mutation API shape and error handling
- Bisection fallback strategy
- Exclusion context propagation mechanism
- Retry policy alignment with existing patterns

## Design Overview

```text
┌─────────────┐    ┌─────────────┐    ┌───────────────────────┐    ┌─────────────────────┐
│ GuardsAction│───▶│PublishAction│───▶│ ApplySuggestionsAction │───▶│ DispatchRepairAction│
└─────────────┘    └─────────────┘    └───────────────────────┘    └─────────────────────┘
                                           │                              │
                                           │ invalidates_snapshot=True     │ runs_after_invalidation=True
                                           │                              │ reads runner context
                                           ▼                              ▼
                                    ┌─────────────┐              ┌─────────────┐
                                    │ GitHub GQL  │              │ Refreshed   │
                                    │ via provider│              │ Snapshot    │
                                    └─────────────┘              └─────────────┘
```

**Planned implementation files (future phase work, not this planning PR)**:

1. `agentic_devtools/cli/ci/pipeline/actions/apply_suggestions.py` — Action class
2. `agentic_devtools/cli/ci/pipeline/suggestions.py` — GraphQL query/mutation logic, bisection, result types
3. `agentic_devtools/cli/ci/pipeline/exclusion.py` — `ExclusionContext` dataclass
4. `agentic_devtools/cli/ci/pipeline/context.py` — runner-scoped pipeline context helpers

**Modified files**:

1. `agentic_devtools/cli/ci/pipeline/actions/__init__.py` — export new action
2. `agentic_devtools/cli/ci/pipeline/command.py` — insert action in sequence
3. `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` — read `ExclusionContext`, filter comments, add `runs_after_invalidation = True`
4. `agentic_devtools/cli/ci/pipeline/runner.py` — persist runner-scoped context across snapshot refresh
5. `agentic_devtools/cli/ci/github_provider.py` + provider interface — expose GraphQL-backed suggestion operations

## Implementation Phases

### Phase 1: Core Data Structures & GraphQL Layer (FR-001, FR-004, FR-005)

**Deliverables**:

- `ExclusionContext` dataclass in `exclusion.py`
- `ApplySuggestionsResult` dataclass in `suggestions.py`
- GraphQL query to fetch `SuggestedChange` nodes with pagination
- Filtering logic (exclude `outdated: true`, unresolved threads only)
- Unit tests for all new types and query parsing

**Files**:

| File | Action |
|------|--------|
| `agentic_devtools/cli/ci/pipeline/exclusion.py` | Create |
| `agentic_devtools/cli/ci/pipeline/suggestions.py` | Create |
| `tests/unit/cli/ci/pipeline/exclusion/` | Create (tests) |
| `tests/unit/cli/ci/pipeline/suggestions/` | Create (tests) |

### Phase 2: GraphQL Mutation & Bisection Fallback (FR-002, FR-003, FR-010)

**Deliverables**:

- `apply_suggestions_batch()` function — single `applySuggestedChanges` mutation call
- `apply_suggestions_with_bisection()` — recursive bisection on conflict errors
- Retry logic with exponential backoff aligned to existing defaults (`max_retries=5`, `initial_delay=1s`)
- Error classification (conflict vs transient vs fatal)
- Unit tests with mocked GraphQL responses

**Files**:

| File | Action |
|------|--------|
| `agentic_devtools/cli/ci/pipeline/suggestions.py` | Extend |
| `tests/unit/cli/ci/pipeline/suggestions/test_apply_suggestions_batch.py` | Create |
| `tests/unit/cli/ci/pipeline/suggestions/test_apply_suggestions_with_bisection.py` | Create |

### Phase 3: Action Class Implementation (FR-006, FR-007, FR-009, FR-011, FR-012)

**Deliverables**:

- `ApplySuggestionsAction` class implementing `Action` protocol
- `evaluate()`: checks applicable suggestions exist, count ≤ 50, guards not blocked
- `execute()`: calls batch apply, falls back to bisection, sets `invalidates_snapshot`
- Populate `ExclusionContext` in runner-scoped context
- Pipeline sequence insertion (after `PublishAction`, before `DispatchRepairAction`)
- Integration with existing guard-blocking mechanism (positioned after `GuardsAction`)

**Files**:

| File | Action |
|------|--------|
| `agentic_devtools/cli/ci/pipeline/actions/apply_suggestions.py` | Create |
| `agentic_devtools/cli/ci/pipeline/actions/__init__.py` | Modify |
| `agentic_devtools/cli/ci/pipeline/command.py` | Modify |
| `tests/unit/cli/ci/pipeline/actions/apply_suggestions/` | Create (tests) |

### Phase 4: DispatchRepairAction Integration (FR-005, FR-006, FR-013)

**Deliverables**:

- Add `runs_after_invalidation = True` to `DispatchRepairAction`
- Read `ExclusionContext` from runner-scoped context in `execute()`
- Filter `review_comments` list to exclude applied comment IDs
- Re-evaluate `needs_repair` after exclusion (if no comments remain + CI passing → SKIP)
- Unit tests for exclusion filtering

**Files**:

| File | Action |
|------|--------|
| `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` | Modify |
| `tests/unit/cli/ci/pipeline/actions/dispatch_repair/` | Add tests |

### Phase 5: Summary Comment (P3 — User Story 5)

**Deliverables**:

- Post PR comment after successful application with applied/skipped lists
- Format: "🔧 **Auto-applied N suggestions** in commit `sha`..."
- Conditional: only posted when ≥1 suggestion was applied

**Files**:

| File | Action |
|------|--------|
| `agentic_devtools/cli/ci/pipeline/actions/apply_suggestions.py` | Extend |
| `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_summary_comment.py` | Create |

### Phase 6: Integration Testing & Edge Cases

**Deliverables**:

- End-to-end tests with mocked provider covering:
  - All suggestions applied → no repair dispatch
  - Partial apply with bisection → repair dispatched with exclusions
  - Zero applicable suggestions → SKIP
  - Threshold exceeded (>50) → SKIP with warning
  - Fork PR → SKIP (guard-blocked)
  - Transient error exhausted → SKIP (not FAILED)
  - Single conflicting suggestion → graceful no-op
  - Bisection producing multiple commits → all SHAs captured

**Files**:

| File | Action |
|------|--------|
| `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_edge_cases.py` | Create |
| `tests/unit/cli/ci/pipeline/actions/apply_suggestions/test_integration.py` | Create |

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GraphQL mutation API changes or undocumented error codes | High | Low | Pin to known schema, handle unknown errors as conflicts, log raw responses |
| Bisection causes excessive API calls on large conflict sets | Medium | Medium | Cap recursion depth at 4 levels (min subset = 3 suggestions), abort with partial result |
| Race condition: human pushes while action runs | Medium | Low | `invalidates_snapshot` forces rerun; mutation idempotent for already-resolved |
| Snapshot refresh fails after invalidation | High | Low | Existing runner handles this with FAILED result and `exec_failed_by` halt |
| `SquashAction` interaction: multiple bisection commits confuse squash | Low | Medium | Already handled: SquashAction squashes when `commit_count > 1` on next run |

## Dependencies

**External**:

- GitHub GraphQL API `applySuggestedChanges` mutation availability
- `gh` CLI v2.x installed in CI runner
- `GH_TOKEN` with `contents:write` permission for the PR branch

**Internal**:

- `CIPlatformProvider` base class + GitHub provider GraphQL helper methods
- `run_safe()` utility for subprocess execution
- `retry_with_backoff` decorator from `agentic_devtools.cli.ci.retry`
- Pipeline runner's `invalidates_snapshot` / `runs_after_invalidation` mechanism

---
*Generated by Copilot SDK (claude-opus-4.6)*
