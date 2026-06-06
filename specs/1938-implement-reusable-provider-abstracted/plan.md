# Implementation Plan: SpecKit Pipeline Retry & Reconciliation Logic

> **Artifact tracking note:** This branch tracks `spec.md`, `plan.md`,
> and `checklists/requirements.md` in this spec directory.
> Optional generated artifacts like `research.md`, `data-model.md`,
> and `quickstart.md` are not tracked here.

## Technical Context

- **Language**: Python 3.10+ (matches existing `agentic_devtools` package)
- **Package location**: `agentic_devtools/cli/ci/reconciliation/` (new subpackage)
- **Provider interface**: `CIPlatformProvider` ABC in `agentic_devtools/cli/ci/provider.py`
- **Existing retry**: `retry_with_backoff` decorator in `agentic_devtools/cli/ci/retry.py` (exponential backoff for transient HTTP errors)
- **GitHub provider**: `GitHubActionsProvider` in `agentic_devtools/cli/ci/github_provider.py` (uses `gh` CLI for API)
- **ADO provider**: `AzureDevOpsProvider` in `agentic_devtools/cli/ci/ado_provider.py` (stub with `NotImplementedError`)
- **Test policy**: 1:1:1 structure under `tests/unit/`, 100% branch coverage required
- **Issue**: [#1938](https://github.com/ayaiayorg/agentic-devtools/issues/1938)

## Research Summary

Detailed research notes informed this plan but are not versioned in this directory. This plan captures the resulting decisions on:

- Method signature design for new `CIPlatformProvider` methods
- Reconciliation entry point architecture (single-run-per-invocation)
- Event context mapping strategy
- Configuration approach (module constants + env var overrides)

## Design Overview

```text
┌─────────────────────────────────────────────────────────┐
│         reconcile() entry point                         │
│  agentic_devtools/cli/ci/reconciliation/engine.py       │
└────────────┬────────────────────────────┬───────────────┘
             │                            │
    ┌────────▼────────┐         ┌────────▼────────────┐
    │  CIPlatformProvider       │  Event Context       │
    │  .list_workflow_runs()    │  Mapper              │
    │  .rerun_workflow()        │  (run → issue/PR)    │
    └────────┬────────┘         └────────┬────────────┘
             │                            │
    ┌────────▼────────┐         ┌────────▼────────────┐
    │  GitHubActions   │         │  Escalation         │
    │  Provider impl   │         │  (post_comment)     │
    └─────────────────┘         └─────────────────────┘
```

**Key design decisions:**

1. Two new non-abstract methods on `CIPlatformProvider` with default `NotImplementedError`
2. Reconciliation engine is provider-agnostic; receives a `CIPlatformProvider` instance
3. Single oldest eligible run processed per invocation (idempotent)
4. Configuration via `config.py` constants overridable by environment variables

## Implementation Phases

### Phase 1: Data Models & Configuration

**Deliverables:**

- `agentic_devtools/cli/ci/reconciliation/__init__.py`
- `agentic_devtools/cli/ci/reconciliation/config.py` — constants + env overrides
- `agentic_devtools/cli/ci/reconciliation/models.py` — `WorkflowRun`, `ReconciliationResult`, `RunEventContext`
- `agentic_devtools/cli/ci/reconciliation/exceptions.py` — `UnmappableContextError`

**Tests:**

- `tests/unit/cli/ci/reconciliation/config/test_*.py`
- `tests/unit/cli/ci/reconciliation/models/test_*.py`
- `tests/unit/cli/ci/reconciliation/exceptions/test_*.py`

### Phase 2: Provider Interface Extension

**Deliverables:**

- Add `list_workflow_runs(workflow_id=..., ...)` and `rerun_workflow(run_id=...)` to `CIPlatformProvider` (non-abstract, default `NotImplementedError`)
- `AzureDevOpsProvider` inherits defaults (no changes needed, already raises `NotImplementedError`)
- Verify existing subclass contracts are unchanged

**Tests:**

- `tests/unit/cli/ci/provider/test_list_workflow_runs.py`
- `tests/unit/cli/ci/provider/test_rerun_workflow.py`
- `tests/unit/cli/ci/ado_provider/test_list_workflow_runs.py`
- `tests/unit/cli/ci/ado_provider/test_rerun_workflow.py`

### Phase 3: GitHub Actions Provider Implementation

**Deliverables:**

- `GitHubActionsProvider.list_workflow_runs()` — calls `gh api` against workflow-scoped runs endpoint (`.../actions/workflows/{workflow_id}/runs`), then filters by conclusion/window/attempts
- `GitHubActionsProvider.rerun_workflow()` — calls `gh api` to trigger re-run all jobs
- Both wrapped with `@retry_with_backoff` for transient failures

**Tests:**

- `tests/unit/cli/ci/github_provider/test_list_workflow_runs.py`
- `tests/unit/cli/ci/github_provider/test_rerun_workflow.py`

### Phase 4: Event Context Mapping

**Deliverables:**

- `agentic_devtools/cli/ci/reconciliation/context_mapper.py` — maps a `WorkflowRun` to issue/PR/branch context
- Parses `event` field (`workflow_dispatch`, `issue_comment`, `pull_request`, `push`)
- Raises `UnmappableContextError` when context cannot be resolved

**Tests:**

- `tests/unit/cli/ci/reconciliation/context_mapper/test_map_run_context.py`
- Tests for each event type + unmappable edge case

### Phase 5: Reconciliation Engine

**Deliverables:**

- `agentic_devtools/cli/ci/reconciliation/engine.py` — `reconcile()` function
  - Calls `provider.list_workflow_runs()` with configured `workflow_id` and filters
  - Selects oldest eligible run
  - If below `MAX_RUN_ATTEMPTS`: calls `provider.rerun_workflow()`
  - If at/above cap: posts escalation via `provider.post_comment()`
  - Returns `ReconciliationResult`

**Tests:**

- `tests/unit/cli/ci/reconciliation/engine/test_reconcile.py` — multiple scenarios

### Phase 6: CLI Command & Integration

**Deliverables:**

- `agentic_devtools/cli/ci/reconciliation/command.py` — CLI entry point `agdt-ci-reconcile`
- Entry point in `pyproject.toml`
- Integration with SpecKit pipeline phase progression (minimal YAML addition)

**Tests:**

- `tests/unit/cli/ci/reconciliation/command/test_reconcile_command.py`

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| GitHub API rate limits during listing + re-run | Medium | Use `retry_with_backoff`; single run per invocation limits calls |
| `run_attempt` field unavailable on older API versions | Low | GitHub Actions API v2022+ always includes it; fail gracefully |
| Breaking existing `CIPlatformProvider` subclasses | High | New methods are non-abstract with default `NotImplementedError` |
| Escalation posted to wrong target | High | `UnmappableContextError` raises explicitly instead of guessing |
| Reconciliation runs concurrently (race condition) | Medium | Single-run-per-invocation + idempotent re-run API mitigates |

## Dependencies

- **Internal**: `agentic_devtools/cli/ci/retry.py` (retry decorator)
- **Internal**: `agentic_devtools/cli/ci/provider.py` (ABC extension)
- **Internal**: `agentic_devtools/cli/ci/github_provider.py` (concrete implementation)
- **Internal**: `agentic_devtools/cli/subprocess_utils.py` (`run_safe` for `gh` CLI calls)
- **External**: GitHub REST API (`/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs`, `/repos/{owner}/{repo}/actions/runs/{run_id}/rerun`)
- **External**: `gh` CLI (authenticated, consistent with existing provider pattern)

---
*Generated by Copilot SDK (claude-opus-4.6)*
