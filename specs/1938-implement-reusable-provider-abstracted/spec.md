# Feature Specification: Implement reusable, provider-abstracted SpecKit pipeline retry & reconciliation logic (library feature)

**Feature Branch**: `speckit/1938/phase-1-specify`  
**Created**: 2026-06-05  
**Status**: Draft  

**Source Issue**: #1938 (<https://github.com/ayaiayorg/agentic-devtools/issues/1938>)

## Clarifications

### Session 2026-06-05

- Q: The spec refers to the interface as `CIProvider`, but the existing codebase uses `CIPlatformProvider` (in `agentic_devtools/cli/ci/provider.py`). Which name should be used? → A: The existing
  `CIPlatformProvider` ABC is the correct interface. New retry/reconciliation methods (with default `NotImplementedError` implementations) will be added to `CIPlatformProvider`. All references to
  "CIProvider" in this spec refer to `CIPlatformProvider`.
- Q: What is the default value for `MAX_RUN_ATTEMPTS` and the recent-run cutoff window, and where should they be configured? → A: `MAX_RUN_ATTEMPTS` defaults to `3`. The recent-run cutoff window
  defaults to `24 hours`. Both are configurable via module-level constants in a new `agentic_devtools/cli/ci/reconciliation/config.py` file, overridable by environment variables
  (`AGDT_MAX_RUN_ATTEMPTS`, `AGDT_RECONCILIATION_WINDOW_HOURS`).
- Q: How is "run attempts" counted — does it mean the number of times `re-run all jobs` has been triggered for a specific workflow run ID, or the total number of runs for the same triggering event? →
  A: It counts the `run_attempt` field on a GitHub Actions workflow run object (i.e., how many times that specific run ID has been re-run). The GitHub REST API exposes this as `run_attempt` on the
  workflow run resource.
- Q: Should the reconciliation step process only the single oldest eligible run per invocation, or should it batch-process all eligible runs? → A: It processes only the single oldest eligible run per
  invocation. This keeps each invocation idempotent and predictable. If multiple runs need retrying, the reconciliation step will be invoked again on the next pipeline cycle.
- Q: The existing `retry.py` implements exponential backoff for transient API failures. Should the new reconciliation logic reuse that decorator for its own API calls (listing runs, triggering
  re-runs, posting comments)? → A: Yes. The new reconciliation logic should wrap its GitHub API calls with the existing `retry_with_backoff` decorator from `agentic_devtools/cli/ci/retry.py` to handle
  transient HTTP failures. The reconciliation retry (re-running a workflow) is a separate, higher-level concept from the API-call retry.

## Problem Statement

### Background

Workflow runs for the SpecKit pipeline (and potentially other agentic devtools flows) sometimes get cancelled, fail, or time out due to transient runner, API, or infra errors. There is currently no
robust, systematic, *reusable* retry/reconciliation mechanism implemented in the `agentic-devtools` library, so each retry strategy is ad hoc and not shareable across CI providers.

### Solution Requirements

**Generalized Retry/Reconciliation Library**

- Implement the reconciliation, retry, and failure escalation core logic inside the `agentic-devtools` library itself so it is reusable and testable
- Abstract all pipeline/re-run querying & triggering logic *behind the existing* `CIPlatformProvider` interface (defined in `agentic_devtools/cli/ci/provider.py`)
- Implement the GitHub Actions backend logic for:
  - Listing recent completed workflow runs for the target workflow
  - Filtering runs by the retriable conclusions set (`cancelled`, `failure`, `timed_out`, `startup_failure`)
  - Filtering runs by `MAX_RUN_ATTEMPTS` (default: 3, configurable via `AGDT_MAX_RUN_ATTEMPTS` env var) and a configurable recent-run cutoff window (default: 24 hours, configurable via
    `AGDT_RECONCILIATION_WINDOW_HOURS` env var) so only runs created on or after that cutoff are considered
  - Executing `re-run all jobs` for a given run via REST API
  - Parsing event context (issue/PR/branch mapping) for status feedback and reporting
  - Posting escalation comments via GitHub API
- For Azure DevOps (ADO) `AzureDevOpsProvider`, stub out the retry/reconciliation interface with a `NotImplementedError` (Python equivalent of the issue's `NotImplementedException` wording)
- Make sure any format or mapping logic (e.g., run → issue) is abstracted for CI-agnostic use

**Workflow Structure**

- Engineer the solution to run as a step *within* the SpecKit pipeline (ideally as part of phase progression)
- It should require minimal workflow YAML dependencies—the logic should be almost entirely library-level and testable
- All signal posting (comments, labels) should leverage the existing devtools clients/helpers

**SpecKit-Compatible**

- Design the issue, helper functions and docs so the workflow can be specked out by SpecKit, with full artifact generation for requirements, plan, and testing steps

The implementation of this feature will improve the overall system reliability and reduce the operational burden on development teams. Without this change, the existing workarounds will continue to
consume developer time and introduce potential for human error.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a developer working with the SpecKit pipeline, I expect the reusable, provider-abstracted retry & reconciliation feature to correctly retry failed, cancelled, or timed-out workflow runs without
requiring manual intervention.

**Why this priority**: Retrying the oldest eligible failed run is the core value of the feature. Without this behavior, the library does not solve the operational problem described in the source
issue.

**Independent Test**: Can be tested by supplying completed GitHub Actions runs with a mix of retriable and non-retriable conclusions, then verifying the reconciliation entry point selects the oldest
eligible run below `MAX_RUN_ATTEMPTS` (default: 3) or escalates instead of rerunning when the cap is reached. Only the single oldest eligible run is processed per invocation.

**Acceptance Scenarios**:

1. **Given** one or more completed GitHub Actions runs for the SpecKit workflow with conclusion `failure`,
   `cancelled`, `timed_out`, or `startup_failure`, and those runs are still within the configured recent-run cutoff
   window (default: 24 hours) and below `MAX_RUN_ATTEMPTS` (default: 3, measured by the run's `run_attempt` field), **When** the reconciliation step executes, **Then** it selects the oldest
   eligible run and triggers `re-run all jobs` through the `CIPlatformProvider` abstraction.

2. **Given** the oldest eligible retriable run has already reached `MAX_RUN_ATTEMPTS` (its `run_attempt` field equals or exceeds the configured cap), **When** the reconciliation
   step evaluates the run history, **Then** it does not trigger another rerun and instead posts an escalation signal
   tied to the related issue, pull request, or branch context.

### User Story 2 - Context-Aware Status Reporting (Priority: P1)

As a developer monitoring a retried pipeline, I expect the reconciliation logic to preserve issue, pull request, or branch context so rerun status and escalation signals are posted against the correct
target.

**Why this priority**: A retry without correct context mapping can hide failures or notify the wrong target, which makes the automation unsafe to operate. Accurate status feedback is required for the
retry mechanism to be actionable in real workflows.

**Independent Test**: Can be tested by providing completed runs from issue-triggered, PR-triggered, and branch-triggered workflows, then verifying the provider abstraction resolves the correct status
reporting target before posting rerun updates or escalation comments.

**Acceptance Scenarios**:

1. **Given** a completed retriable GitHub Actions run created from an issue comment, **When** the reconciliation step prepares status feedback, **Then** it maps the run back to that issue and uses the
   existing devtools helpers to post the retry or escalation update there.

2. **Given** a completed retriable GitHub Actions run created from a pull request or branch workflow, **When** the reconciliation step posts feedback, **Then** it resolves the matching pull request or
   branch context and does not emit the signal to an unrelated target.

### User Story 3 - Provider-Abstraction Fallback (Priority: P2)

As a maintainer extending retry support to multiple CI systems, I expect non-GitHub providers to expose the same reconciliation interface even when concrete retry behavior has not been implemented
yet.

**Why this priority**: Provider abstraction is necessary for the feature to remain reusable beyond GitHub Actions. Shipping an explicit ADO stub keeps the interface stable while preventing silent
partial implementations.

**Independent Test**: Can be tested by invoking the retry/reconciliation entry point through the ADO `AzureDevOpsProvider` implementation and verifying it raises `NotImplementedError` while the
GitHub Actions provider (`GitHubActionsProvider`) continues to handle eligible completed runs.

**Acceptance Scenarios**:

1. **Given** the reconciliation library is invoked through the `AzureDevOpsProvider` (the Azure DevOps `CIPlatformProvider` implementation), **When** retry handling is requested, **Then** the provider
   exposes the same interface as GitHub Actions and
   raises `NotImplementedError` until an ADO implementation is added.

### Edge Cases

- No completed workflow runs fall within the configured recent-run cutoff window (default: 24 hours), so the reconciliation step MUST exit without triggering a rerun or escalation comment and MUST
  return a structured result indicating "no eligible runs found".
- A completed workflow run has a non-retriable conclusion such as `success`, `skipped`, or `action_required`, so the run MUST be ignored even if it is the oldest run returned by the provider.
- The oldest retriable run is eligible for retry, but its event context cannot be mapped to an issue, pull request, or branch target, so the library MUST surface a deterministic error (raising a
  specific exception type) rather than posting feedback to the wrong destination.
- The provider can query recent runs but receives an authorization or API error while triggering `re-run all jobs` or posting an escalation comment, so the failure MUST be surfaced without falsely
  recording the rerun or escalation as successful. Transient HTTP errors (429, 5xx) are retried via the existing `retry_with_backoff` decorator before surfacing the failure.
- Only the single oldest eligible run is processed per invocation; if multiple eligible runs exist, subsequent runs are deferred to the next reconciliation cycle.

## Requirements

### Functional Requirements

- **FR-001**: The system MUST implement retry/reconciliation core logic inside the `agentic-devtools` library (under `agentic_devtools/cli/ci/reconciliation/`) so it is reusable and independently
  testable.

- **FR-002**: The system MUST abstract all pipeline re-run querying and triggering logic behind the existing `CIPlatformProvider` interface (in `agentic_devtools/cli/ci/provider.py`), ensuring
  CI-agnostic use. New non-abstract methods with default `NotImplementedError` implementations added: `list_workflow_runs()` and `rerun_workflow()`.

- **FR-003**: The `GitHubActionsProvider` backend MUST support:
  - Listing recent workflow runs filtered by retriable conclusions (`cancelled`, `failure`, `timed_out`, `startup_failure`)
  - Filtering runs by a configurable `MAX_RUN_ATTEMPTS` cap (default: 3, using the run's `run_attempt` field) and time window (default: 24 hours)
  - Executing `re-run all jobs` for a given run via the GitHub REST API
  - Parsing event context (issue/PR/branch mapping) for status feedback and reporting
  - Posting escalation comments via the GitHub API using existing devtools helpers
  - Wrapping API calls with the existing `retry_with_backoff` decorator for transient failure resilience

- **FR-004**: The `AzureDevOpsProvider` implementation MUST stub out the retry/reconciliation interface methods (`list_workflow_runs`, `rerun_workflow`) and raise `NotImplementedError` until a full
  implementation is added.

- **FR-005**: The reconciliation step MUST run as part of the SpecKit pipeline phase progression and MUST minimize workflow YAML dependencies—logic should reside almost entirely at the library level.
  Only a single oldest eligible run is processed per invocation.

- **FR-006**: All signal posting (comments, labels) MUST leverage the existing devtools clients/helpers rather than introduce new direct API calls in workflow YAML.

### Non-Functional Requirements

- **NFR-001**: The implementation MUST complete all operations (listing runs, triggering rerun or posting escalation, posting status feedback) within 120 seconds under normal network conditions,
  excluding time spent in `retry_with_backoff` waits for transient failures.

- **NFR-002**: The implementation MUST maintain backward compatibility with existing `CIPlatformProvider` interfaces and contracts. New methods MUST be non-abstract with default `NotImplementedError`
  implementations to avoid requiring existing subclasses to override them.

## Success Criteria

- **SC-001**: For one or more GitHub Actions runs with conclusion `cancelled`, `failure`, `timed_out`, or
  `startup_failure` that are within the configured recent-run cutoff window (default: 24 hours) and below `MAX_RUN_ATTEMPTS` (default: 3, measured by `run_attempt`), the library
  selects the oldest eligible run and invokes `re-run all jobs` through the `CIPlatformProvider` abstraction.

- **SC-002**: When the oldest eligible retriable run has reached `MAX_RUN_ATTEMPTS`, the library skips rerun,
  records the run as exhausted, and posts an escalation comment through the existing devtools helpers.

- **SC-003**: The reconciliation entry point remains CI-provider-agnostic: `GitHubActionsProvider` supplies the concrete
  retry/reconciliation behavior via `CIPlatformProvider`, while the `AzureDevOpsProvider` implementation exposes the same interface and raises
  `NotImplementedError` until implemented.

---
*Generated by Copilot SDK (claude-opus-4.6)*
