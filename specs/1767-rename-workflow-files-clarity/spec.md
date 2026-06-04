# Feature Specification: Rename workflow files for clarity: agent-session-monitor → ai-pr-loop-throttler, pr-activity-dispatch → ai-pr-loop-dispatcher

**Feature Branch**: `speckit/1767/phase-1-specify`  
**Created**: 2026-06-04  
**Status**: Draft  
**Input**: GitHub Issue #1767 — Rename workflow files for clarity: agent-session-monitor → ai-pr-loop-throttler, pr-activity-dispatch → ai-pr-loop-dispatcher

**Source Issue**: #1767 (<https://github.com/ayaiayorg/agentic-devtools/issues/1767>)

## Clarifications

### Session 2026-06-04

- Q: Should the test file `tests/workflows/test_agent_session_monitor.py` be renamed to `test_ai_pr_loop_throttler.py`, and should assertions within it that check for old identifiers (e.g., asserting
  `"agent-session-monitor" in content`) be updated to assert the new names? → A: Yes. The test file must be renamed to `test_ai_pr_loop_throttler.py` and all assertions within it must reference the
  new workflow filename and identifiers (`ai-pr-loop-throttler`). Similarly, assertions in `test_ai_pr_loop_redispatch.py` that reference `agent-session-monitor` must be updated to
  `ai-pr-loop-throttler`.
- Q: The `ai-pr-loop-redispatch.yml` workflow contains operational references (API endpoint paths, `gh workflow run` commands, log strings) that use `agent-session-monitor`. Should these be updated to
  `ai-pr-loop-throttler` as part of this rename? → A: Yes. All operational references in `ai-pr-loop-redispatch.yml` — including the workflow run API path, `gh workflow run` target, and echo/log
  strings — must use the new name `ai-pr-loop-throttler.yml` / `ai-pr-loop-throttler`.
- Q: The file `agentic_devtools/cli/ci/guards.py` contains a reference to `agent-session-monitor` in what appears to be a docstring/comment describing behavior. Should code/docstring references in
  Python source also be updated? → A: Yes. All references in Python source code (including docstrings, comments, and string literals) must be updated to the new workflow name to maintain consistency,
  unless they appear in historical changelog or issue-tracking artifacts.
- Q: Should the concurrency group in the dispatcher workflow change from `pr-activity-dispatch` to `ai-pr-loop-dispatcher` to maintain the convention that concurrency group names match workflow
  filenames? → A: Yes. The concurrency group must be renamed from `pr-activity-dispatch` to `ai-pr-loop-dispatcher` to maintain the naming convention and satisfy NFR-002 (internal consistency).
- Q: Spec/plan files under `specs/` (e.g., `specs/1587-*`, `specs/1659-*`) contain references to old workflow names as historical documentation. Should these be updated or excluded from the rename
  scope? → A: Excluded. Historical spec/plan/task artifacts that document prior architecture decisions are intentionally excluded from renaming. They serve as audit trail. Only active operational
  files (workflows, source code, tests, README) are in scope. SC-002 already accounts for this exclusion.

## Problem Statement

Rename workflow files to better reflect their purpose:

| Current name | New name | Rationale |
|---|---|---|
| `agent-session-monitor.yml` | `ai-pr-loop-throttler.yml` | This workflow throttles/schedules which PRs get ai-pr-loop dispatched — "agent session monitor" is a legacy name that no longer reflects its role |
| `pr-activity-dispatch.yml` | `ai-pr-loop-dispatcher.yml` | This workflow listens for PR events and dispatches the throttler — naming it `ai-pr-loop-dispatcher` makes the relationship clear and won't be invalidated if non-PR triggers are added later |

**Files to update:**

- [`.github/workflows/agent-session-monitor.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/agent-session-monitor.yml) → rename to `ai-pr-loop-throttler.yml`
- [`.github/workflows/pr-activity-dispatch.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/pr-activity-dispatch.yml) → rename to `ai-pr-loop-dispatcher.yml`
- [`.github/workflows/README.md`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/README.md)
- [`.github/workflows/ai-pr-loop-redispatch.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/ai-pr-loop-redispatch.yml) — operational references to
  `agent-session-monitor` in API paths, `gh workflow run` commands, and log strings
- `agentic_devtools/cli/ci/guards.py` — docstring/comment reference to `agent-session-monitor`
- `tests/workflows/test_agent_session_monitor.py` — rename file to `test_ai_pr_loop_throttler.py` and update assertions
- `tests/workflows/test_ai_pr_loop_redispatch.py` — update assertions referencing old name
- Concurrency group names (specifically `pr-activity-dispatch` → `ai-pr-loop-dispatcher`)
- Structured log prefixes (e.g., `[agent-session-monitor]` → `[ai-pr-loop-throttler]`)
- Any other references discovered via case-sensitive grep (excluding historical spec artifacts under `specs/`)

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

1. **Given** workflow-to-workflow interactions (including `ai-pr-loop-redispatch.yml` dispatching the throttler), **When** dispatch targets are referenced, **Then** they use the new workflow
   names/files and do not reference the retired names.
2. **Given** repository docs, workflow operational strings (such as concurrency groups and structured log prefixes), Python source docstrings, and test assertions, **When** references include these
   workflow identifiers, **Then** they are updated to the new names.
3. **Given** the test file `tests/workflows/test_agent_session_monitor.py`, **When** the rename is applied, **Then** it is renamed to `tests/workflows/test_ai_pr_loop_throttler.py` with all internal
   assertions updated.

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
  (including `.github/workflows/README.md`, `.github/workflows/ai-pr-loop-redispatch.yml`,
  `agentic_devtools/cli/ci/guards.py`, `tests/workflows/test_agent_session_monitor.py`,
  `tests/workflows/test_ai_pr_loop_redispatch.py`, workflow dispatch targets, concurrency
  groups, and structured log prefixes) to the new names, with affected references
  discovered via case-sensitive repository-wide searches for
  `agent-session-monitor` and `pr-activity-dispatch`, including both file path names
  and file content references. Historical spec/plan artifacts under `specs/` are
  explicitly excluded from the rename scope.
- **FR-005**: Preserve existing workflow logic (triggers, permissions, jobs, and dispatch payload behavior) with no functional changes beyond identifier renaming.
- **FR-006**: Rename test file `tests/workflows/test_agent_session_monitor.py` to `tests/workflows/test_ai_pr_loop_throttler.py` and update all assertions within it to validate the new workflow
  filename and identifiers.
- **FR-007**: Update the concurrency group in `ai-pr-loop-dispatcher.yml` from `pr-activity-dispatch` to `ai-pr-loop-dispatcher`.

### Non-Functional Requirements

- **NFR-001**: Renaming must be behavior-preserving: the same events must continue to trigger the same automation flow after the rename. Verified by `bash scripts/run-pr-checks.sh --full` passing with
  zero test failures.
- **NFR-002**: Naming must be internally consistent across filenames, workflow `name:` values, concurrency groups, `gh workflow run` targets, API endpoint paths, log prefixes, test assertions, and
  docstrings — zero stale references in operational code after rename.

## Success Criteria

- **SC-001**: Under `.github/workflows/`, both new files (`ai-pr-loop-throttler.yml` and
  `ai-pr-loop-dispatcher.yml`) exist and both retired files are absent.
- **SC-002**: Case-sensitive repository verification (excluding issue/spec artifacts under `specs/`
  that intentionally document old names) returns zero operational references to
  `agent-session-monitor` or `pr-activity-dispatch` in active workflow/config/docs/source/tests.
- **SC-003**: `bash scripts/run-pr-checks.sh --full` passes after the rename, including
  workflow integration tests, indicating no functional regression from naming changes.
- **SC-004**: The concurrency group in the dispatcher workflow reads `ai-pr-loop-dispatcher`.
- **SC-005**: All `gh workflow run` and API path references in `ai-pr-loop-redispatch.yml` target `ai-pr-loop-throttler.yml`.

---
*Generated by Copilot SDK (claude-opus-4.6)*
