# Feature Specification: Rename workflow files for clarity: agent-session-monitor → ai-pr-loop-throttler, pr-activity-dispatch → ai-pr-loop-dispatcher

**Feature Branch**: `speckit/1767/phase-1-specify`  
**Created**: 2026-06-04  
**Status**: Draft  
**Input**: GitHub Issue #1767 — Rename workflow files for clarity: agent-session-monitor → ai-pr-loop-throttler, pr-activity-dispatch → ai-pr-loop-dispatcher

**Source Issue**: #1767 (<https://github.com/ayaiayorg/agentic-devtools/issues/1767>)

## Problem Statement

Rename workflow files to better reflect their purpose:

| Current name | New name | Rationale |
|---|---|---|
| `agent-session-monitor.yml` | `ai-pr-loop-throttler.yml` | This workflow throttles/schedules which PRs get ai-pr-loop dispatched — "agent session monitor" is a legacy name that no longer reflects its role |
| `pr-activity-dispatch.yml` | `ai-pr-loop-dispatcher.yml` | This workflow listens for PR events and dispatches the throttler — naming it `ai-pr-loop-dispatcher` makes the relationship clear and won't be invalidated if non-PR triggers are added later |

**Files to update:**
[`.github/workflows/agent-session-monitor.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/agent-session-monitor.yml)
[`.github/workflows/pr-activity-dispatch.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/pr-activity-dispatch.yml)
[`.github/workflows/README.md`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/README.md)
Any references in code, specs, or comments (grep for `agent-session-monitor` and `pr-activity-dispatch`)
Concurrency group names
Structured log prefixes (e.g. `[agent-session-monitor]`)

Also update the `name:` field inside each workflow YAML to exact values
`ai-pr-loop-throttler` and `ai-pr-loop-dispatcher`.

These renames make workflow intent immediately clear in the Actions tab and in repository files, reducing confusion when tracing dispatch flow between the PR event dispatcher and throttling workflow.

## User Scenarios & Testing

### User Story 1 - Primary Workflow (Priority: P1)

As a maintainer, I want the workflow filenames and displayed workflow names to match their responsibilities so I can identify the dispatcher and throttler quickly during triage.

**Acceptance Scenarios**:

1. **Given** the repository workflow directory, **When** I inspect workflow files, **Then**
   `agent-session-monitor.yml` is renamed to `ai-pr-loop-throttler.yml` and
   `pr-activity-dispatch.yml` is renamed to `ai-pr-loop-dispatcher.yml`.
2. **Given** the renamed files, **When** I open each workflow YAML, **Then** the top-level `name:` field matches the new filename purpose (`ai-pr-loop-throttler` and `ai-pr-loop-dispatcher`).

### User Story 2 - Error Recovery (Priority: P1)

As a maintainer, I want all references to old workflow identifiers updated so dispatching, docs, and operational metadata remain consistent after the rename.

**Acceptance Scenarios**:

1. **Given** workflow-to-workflow interactions, **When** dispatch targets are referenced, **Then** they use the new workflow names/files and do not reference the retired names.
2. **Given** repository docs and workflow operational strings (such as concurrency
   groups and structured log prefixes), **When** references include these workflow
   identifiers, **Then** they are updated to the new names.

### User Story 3 - Graceful Degradation (Priority: P2)

As a CI operator, I want workflow behavior preserved after renaming so existing automation still triggers and executes as before.

**Acceptance Scenarios**:

1. **Given** pull request activity that previously triggered the dispatcher/throttler chain, **When** events occur after the rename, **Then** the renamed workflows still trigger on the same events.
2. **Given** existing jobs, permissions, and dispatch payloads, **When** the rename is applied, **Then** behavior remains unchanged apart from updated identifiers.

## Requirements

### Functional Requirements

- **FR-001**: Rename workflow file `.github/workflows/agent-session-monitor.yml` to `.github/workflows/ai-pr-loop-throttler.yml`.
- **FR-002**: Rename workflow file `.github/workflows/pr-activity-dispatch.yml` to `.github/workflows/ai-pr-loop-dispatcher.yml`.
- **FR-003**: Update the `name:` field in each renamed workflow to exact values
  `ai-pr-loop-throttler` and `ai-pr-loop-dispatcher` so GitHub Actions UI names
  match the new intent.
- **FR-004**: Update all affected repository references to the old workflow names
  (including `.github/workflows/README.md`, workflow dispatch targets, concurrency
  groups, and structured log prefixes) to the new names, with affected references
  discovered via case-sensitive repository-wide searches for
  `agent-session-monitor` and `pr-activity-dispatch`, including both file path names
  and file content references.
- **FR-005**: Preserve existing workflow logic (triggers, permissions, jobs, and dispatch payload behavior) with no functional changes beyond identifier renaming.

### Non-Functional Requirements

- **NFR-001**: Renaming must be behavior-preserving: the same events must continue to trigger the same automation flow after the rename.
- **NFR-002**: Naming must be internally consistent across filenames, workflow `name:` values, and operational identifiers to reduce maintenance ambiguity.

## Success Criteria

- **SC-001**: Under `.github/workflows/`, both new files (`ai-pr-loop-throttler.yml` and
  `ai-pr-loop-dispatcher.yml`) exist and both retired files are absent.
- **SC-002**: Case-sensitive repository verification (excluding issue/spec artifacts
  that intentionally document old names) returns zero operational references to
  `agent-session-monitor` or `pr-activity-dispatch` in active workflow/config/docs.
- **SC-003**: `bash scripts/run-pr-checks.sh --full` passes after the rename, including
  workflow integration tests, indicating no functional regression from naming changes.

---
*Generated by Copilot SDK (claude-opus-4.6)*
