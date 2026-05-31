# Feature Specification: Consolidate SpecKit Issue Trigger into Phase Progression Pipeline

**Feature Branch**: `speckit/1527/phase-2-clarify`  
**Created**: 2026-05-23  
**Status**: Draft  
**Input**: GitHub Issue #1527 — Consolidate speckit-issue-trigger into speckit-phase-progression pipeline and fix Phase 1 PR token  
**Source Issue**: #1527 (<https://github.com/ayaiayorg/agentic-devtools/issues/1527>)

## Clarifications

### Session 2026-05-23

- Q: When the thin dispatcher triggers `speckit-phase-progression.yml` via `workflow_dispatch`,
  which GitHub token should the dispatcher use for the dispatch API call — `GITHUB_TOKEN`, `SPECKIT_PR_TOKEN`, or `COPILOT_GITHUB_TOKEN`?
  → A: The dispatcher should use `GITHUB_TOKEN` for the `workflow_dispatch` API call itself,
  since `workflow_dispatch` is an internal GitHub Actions trigger (not a PR creation) and does not require human-identity authoring.
  The human-identity token (`SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN`) is only needed in the progression workflow for the PR creation step.
  When using `GITHUB_TOKEN`, the thin dispatcher workflow must explicitly grant `permissions: actions: write`,
  because dispatching another workflow on the same repository requires that permission; without it, the call can fail with HTTP 403.
- Q: Should the `speckit-issue-trigger.yml` dispatcher workflow retain its own concurrency
  group (`speckit-trigger-${{ github.event.issue.number || inputs.issue_number }}`), or
  should it rely solely on the progression workflow's concurrency group
  (`speckit-progression`)? → A: The dispatcher should retain its own concurrency group
  (`speckit-trigger-${{ github.event.issue.number || inputs.issue_number }}`) to serialize
  dispatch attempts for the same issue when the label is rapidly toggled. With
  `cancel-in-progress: false`, duplicate runs can still queue and execute later; they just
  do not overlap. The progression workflow's global `speckit-progression` group handles
  serialization of the actual phase generation work, and downstream idempotency checks make
  queued duplicates safe.
- Q: When `phase=1` is dispatched via `workflow_dispatch`, should the extract step set `merged_pr_url` to an empty string (as it currently does for Phases 2–5 dispatches), and should the "Add Phase
  Complete Label" step be skipped for `workflow_dispatch` events (as currently implemented)? → A: Yes, the existing extract step behavior is correct and should be preserved: `merged_pr_url` is set to
  an empty string for `workflow_dispatch` events (there is no merged PR for Phase 1 initial triggers), and the "Add Phase Complete Label" step already gates on
  `github.event_name != 'workflow_dispatch'`,
  which is the correct behavior since the phase-complete label should only be applied when a phase PR is merged, not when the next phase is dispatched.
- Q: Should the `AGDT_USE_PYTHON_ORCHESTRATOR` environment variable (currently set in `speckit-issue-trigger.yml`) be preserved in the thin dispatcher, removed entirely, or moved to the progression
  workflow? → A: Remove `AGDT_USE_PYTHON_ORCHESTRATOR` entirely. The thin dispatcher does not run any Python orchestration (it only dispatches), and the progression workflow uses shell scripts for
  commit/push/PR logic. This env var was only needed because the current trigger workflow runs `agdt-speckit-trigger` (the Python orchestrator), which is being removed as part of FR-006.
- Q: What should happen to the `agdt-speckit-trigger` CLI entry point in `pyproject.toml` after the Python `_commit_and_push_phase_branch()` and `_create_phase_pull_request()` functions are removed —
  should it be deleted, or should it be retained as a stub that raises an informative error? → A: Retain `agdt-speckit-trigger` as a stub entry point that raises an informative `SystemExit` error
  directing users to use `workflow_dispatch` on `speckit-phase-progression.yml` with `phase=1`. This prevents silent breakage for any downstream scripts or documentation that reference the command,
  and provides a clear migration path. The stub should print a message like:
  `agdt-speckit-trigger has been removed.\nUse workflow_dispatch on speckit-phase-progression.yml with phase=1 and issue_number=N instead.`
  and exit with code 1.

## Problem Statement

The SpecKit workflow system currently uses two separate GitHub Actions pipelines to handle the same logical flow: `speckit-issue-trigger.yml` for Phase 1, and `speckit-phase-progression.yml` for
Phases 2–5. This duplication causes maintenance burden, inconsistent behavior (Phase 1 PRs use `GITHUB_TOKEN` resulting in bot-authored PRs that don't trigger CI or Copilot review), and requires every
enhancement to be manually replicated across both pipelines.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Phase 1 PRs Created with Human Identity Token (Priority: P1)

As a repository maintainer, I want the Phase 1 PR to be created with `SPECKIT_PR_TOKEN` (or `COPILOT_GITHUB_TOKEN`), so that it is authored by a human identity and automatically triggers CI and
Copilot review like Phases 2–5.

**Why this priority**: This is the core bug fix. Without it, Phase 1 PRs remain second-class citizens that require manual workarounds to trigger CI and review.

**Independent Test**: Add the `speckit` label to a test issue and verify the resulting PR is authored by the token-holder identity (not `github-actions[bot]`), and that CI checks and Copilot review
are triggered automatically.

**Mapped Functional Requirements**: FR-002, FR-014

**Acceptance Scenarios**:

1. **Given** a GitHub issue exists without a speckit phase branch, **When** the `speckit` label is added,
   **Then** the Phase 1 PR is created using `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` and the PR author is a human identity (not `github-actions[bot]`).
2. **Given** a Phase 1 PR is created by the consolidated workflow, **When** the PR is opened, **Then** CI checks and Copilot review are triggered automatically (same as Phases 2–5).
3. **Given** the `SPECKIT_PR_TOKEN` secret is not configured, **When** Phase 1 is triggered, **Then** the workflow falls back to `COPILOT_GITHUB_TOKEN` gracefully.
4. **Given** both `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` are unset, **When** Phase 1 preflight runs, **Then** it fails before PR creation with a clear error and MUST NOT fall back to
   `GITHUB_TOKEN`.

---

### User Story 2 - Single Workflow Handles All Phases 1–5 (Priority: P1)

As a repository maintainer, I want all speckit phase logic consolidated into one progression workflow, so that enhancements and bug fixes are implemented once and apply consistently to all phases.

**Why this priority**: Eliminates the root cause of duplication — every future improvement benefits all phases without additional work.

**Independent Test**: Trigger Phase 1 via `workflow_dispatch` on `speckit-phase-progression.yml` with `phase=1` and verify
it produces the full Phase 1 artifact set (`spec.md` plus empty `checklists/` and `contracts/` directories) and PR,
identical to the current `speckit-issue-trigger.yml` output.

**Mapped Functional Requirements**: FR-001, FR-003, FR-011, FR-012, FR-015

**Acceptance Scenarios**:

1. **Given** the `speckit-phase-progression.yml` workflow, **When** dispatched with `issue_number=N` and `phase=1`,
   **Then** the full Phase 1 artifact set (`spec.md`, empty `checklists/` directory, and empty `contracts/` directory)
   is generated, committed, pushed, and a PR is created — `checklists/requirements.md` is NOT included (it is produced
   in Phase 2).
2. **Given** a Phase 1 PR is merged into main, **When** the `speckit-phase-progression.yml` detects the merge, **Then** Phase 2 is triggered (existing progression behavior is preserved).
3. **Given** the consolidated workflow, **When** any of the feature flags (`SPECKIT_CREATE_BRANCH`, `SPECKIT_CREATE_PR`, `SPECKIT_CRITICAL_GATE_MODE`) are set, **Then** they apply equally to Phase 1
   as to Phases 2–5.

---

### User Story 3 - Thin Dispatcher for Label-Based Triggering (Priority: P2)

As a developer, I want label-based triggering to use a thin dispatcher that only forwards to the progression workflow, so that the existing UX is preserved without duplicating business logic.

**Why this priority**: Preserves the existing UX (label-based triggering) while keeping all logic in one place. Less critical than P1 because `workflow_dispatch` already provides manual triggering.

**Independent Test**: Add the `speckit` label to an issue and verify that `speckit-phase-progression.yml` is triggered with the correct inputs, without any spec generation logic in the dispatcher.

**Mapped Functional Requirements**: FR-004, FR-005

**Acceptance Scenarios**:

1. **Given** an issue without a speckit phase, **When** the `speckit` label is added, **Then** the dispatcher triggers `speckit-phase-progression.yml` with `issue_number` and `phase=1`.
2. **Given** the dispatcher is triggered via `workflow_dispatch` with an `issue_number`, **Then** it dispatches to `speckit-phase-progression.yml` with the same parameters.
3. **Given** a non-speckit label is added to an issue, **When** the label event fires, **Then** the dispatcher does not trigger the progression workflow.
4. **Given** the dispatcher uses `GITHUB_TOKEN` for the `workflow_dispatch` API call, **When** the dispatch is successful, **Then** the progression workflow handles PR creation with the human-identity
   token independently.

---

### User Story 4 - Remove Python Orchestrator Commit/Push/PR Logic (Priority: P2)

As a maintainer, I want obsolete Phase 1 commit/push/PR helpers removed from the Python trigger module, so that the consolidated workflow is the single canonical path for these operations.

**Why this priority**: Eliminates dead code and prevents confusion about which implementation is canonical. Dependent on P1 (the consolidated workflow must work first).

**Independent Test**: After removal, verify the `agdt-speckit-trigger` CLI entry point raises an informative error directing users to use `workflow_dispatch` on `speckit-phase-progression.yml`.
Existing unit tests for removed functions are
also removed or updated.

**Mapped Functional Requirements**: FR-006

**Acceptance Scenarios**:

1. **Given** the Python `speckit_trigger.py` module, **When** the refactoring is complete, **Then** `_commit_and_push_phase_branch()` and `_create_phase_pull_request()` functions no longer exist.
2. **Given** the consolidated workflow handles Phase 1, **When** the `agdt-speckit-trigger` entry point is invoked, **Then** it prints an informative message
   (`agdt-speckit-trigger has been removed.\nUse workflow_dispatch on speckit-phase-progression.yml with phase=1 and issue_number=N instead.`) and exits with code 1.
3. **Given** existing tests for the removed functions, **When** the refactoring is complete, **Then** all tests pass (removed tests for removed code, updated tests for remaining code).
4. **Given** the `AGDT_USE_PYTHON_ORCHESTRATOR` environment variable was previously set in the trigger workflow, **When** the thin dispatcher replaces the trigger, **Then**
   `AGDT_USE_PYTHON_ORCHESTRATOR` is no longer set or referenced in either workflow.

---

### User Story 5 - Feature Parity for Phase 1 (Priority: P1)

As a repository maintainer, I want Phase 1 to preserve the same operational behavior as Phases 2–5, so that consolidation does not regress idempotency, labeling, failure handling, or draft-mode
controls.

**Why this priority**: Without feature parity, consolidation introduces regressions. This is part of the core consolidation.

**Independent Test**: Trigger Phase 1 in various scenarios (duplicate branch exists, critical gate fails, workflow fails) and verify each feature works identically to how it works for Phases 2–5.

**Mapped Functional Requirements**: FR-007, FR-008, FR-009, FR-010, FR-013

**Acceptance Scenarios**:

1. **Given** a Phase 1 branch already exists for an issue, **When** Phase 1 is triggered again, **Then** idempotency logic skips PR creation (same as Phases 2–5).
2. **Given** the `SPECKIT_AUTO_MERGE_ALLOWED_LABEL` variable is `'true'`, **When** Phase 1 PR is created successfully, **Then** the `ai-auto-merge-allowed` label is added to the PR.
3. **Given** Phase 1 generation fails, **When** the failure is detected, **Then** a failure comment is posted to the issue and the `speckit:failed` label is applied.
4. **Given** the critical gate fails in `draft` mode, **When** Phase 1 PR is created, **Then** the PR is created as a draft with critical findings noted in the PR body.

---

### User Story 6 - Workflow Documentation Updated (Priority: P3)

As a contributor, I want workflow documentation to describe the consolidated architecture, so that developers can understand and operate the new single-workflow model correctly.

**Why this priority**: Documentation is important but non-blocking for the implementation.

**Independent Test**: Read the updated README and verify it accurately describes the new single-workflow architecture without references to a separate Phase 1 pipeline.

**Acceptance Scenarios**:

1. **Given** the consolidation is complete, **When** a developer reads `.github/workflows/README.md`, **Then** it describes one progression workflow handling Phases 1–5 and a thin dispatcher for label
   events.
2. **Given** the documentation, **When** a developer looks for how to manually trigger Phase 1, **Then** they find instructions for `workflow_dispatch` with `phase=1` on
   `speckit-phase-progression.yml`.

---

### Edge Cases

- What happens when Phase 1 is triggered but `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` are both unconfigured? The workflow should fail with a clear error message rather than silently falling back
  to `GITHUB_TOKEN`.
- What happens if the thin dispatcher fires but `speckit-phase-progression.yml` is already
  running for the same issue (concurrency)? The dispatcher retains its own per-issue
  concurrency group (`speckit-trigger-${{ github.event.issue.number || inputs.issue_number }}`)
  to serialize dispatch attempts (not hard-prevent queued duplicates), while the progression
  workflow's global concurrency group (`speckit-progression`) queues the run (not cancel it,
  as per existing `cancel-in-progress: false`). These are complementary protections, and
  idempotency in progression makes queued duplicates safe.
- What happens if someone manually dispatches `speckit-phase-progression.yml` with `phase=1` for an issue that has no body or title? The generate script should fail gracefully with a clear error.
- How does the `speckit:phase-1` label get applied to the Phase 1 PR created by the progression workflow? The `create-spec-pr.sh` script already handles phase labels via `--phase-number` and
  `--phase-name` arguments.
- What happens if the thin dispatcher's `workflow_dispatch` API call to the progression workflow fails (e.g., rate limit, permissions)? The dispatcher step fails, triggering the existing failure
  handling (failure comment + `speckit:failed` label on the issue).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `speckit-phase-progression.yml` workflow MUST accept `phase=1` (in addition to 2–5) as a valid `workflow_dispatch` input option.
- **FR-002**: Phase 1 execution in the progression workflow MUST use `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` for PR creation (not `GITHUB_TOKEN`).
- **FR-003**: Phase 1 execution MUST use the same commit, push, and PR creation steps as Phases 2–5 (shared shell logic, not Python orchestration).
- **FR-004**: The `speckit-issue-trigger.yml` workflow MUST be reduced to a thin dispatcher that triggers `speckit-phase-progression.yml` via `workflow_dispatch` with `issue_number` and `phase=1`. The
  dispatcher MUST use `GITHUB_TOKEN` for the dispatch API call (not a human-identity token), and the dispatcher workflow MUST grant `permissions: actions: write` so that dispatch call is authorized.
  The `AGDT_USE_PYTHON_ORCHESTRATOR` environment variable MUST be removed from the dispatcher.
- **FR-005**: The thin dispatcher MUST fire only when the `speckit` label (or configured `SPECKIT_TRIGGER_LABEL`) is added to an issue. The dispatcher MUST retain its own per-issue concurrency group
  (`speckit-trigger-${{ github.event.issue.number || inputs.issue_number }}`) to serialize dispatch attempts for the same issue. With `cancel-in-progress: false`, queued duplicates may still run
  sequentially, so progression idempotency requirements (FR-007) MUST keep duplicate dispatches safe.
- **FR-006**: The Python `_commit_and_push_phase_branch()` and `_create_phase_pull_request()` functions in `speckit_trigger.py` MUST be removed. The `agdt-speckit-trigger` CLI entry point MUST be
  retained as a stub that prints an informative migration message and exits with code 1.
- **FR-007**: Phase 1 MUST support idempotency checking (skip if PR already exists for the branch).
- **FR-008**: Phase 1 MUST support the `ai-auto-merge-allowed` label when `SPECKIT_AUTO_MERGE_ALLOWED_LABEL == 'true'`.
- **FR-009**: Phase 1 MUST support failure handling (issue comment + `speckit:failed` label) on error.
- **FR-010**: Phase 1 MUST support critical gate draft mode (`SPECKIT_CRITICAL_GATE_MODE == 'draft'`).
- **FR-011**: The progression workflow's extract step MUST handle `phase=1` by setting `completed_phase=0`, `next_phase=1`, and `next_phase_name=specify`.
- **FR-012**: The `speckit-phase-progression.yml` workflow MUST also trigger when a PR with the `speckit:phase-1` label is merged (to progress to Phase 2) — this is already supported and MUST NOT
  regress.
- **FR-013**: The `speckit:processing` label MUST be added at the start of Phase 1 execution and removed on completion or failure.
- **FR-014**: Phase 1 MUST perform an explicit token preflight check that aborts before commit/push/PR creation when both `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` are missing, and it MUST NOT use
  `GITHUB_TOKEN` as a fallback for PR creation.
- **FR-015**: Phase 1 execution in the consolidated workflow MUST honor `SPECKIT_CREATE_BRANCH`, `SPECKIT_CREATE_PR`, and `SPECKIT_CRITICAL_GATE_MODE` exactly as Phases 2–5.

### Non-Functional Requirements

- **NFR-001**: Phase 1 execution time MUST NOT increase by more than 30 seconds compared to the current implementation (accounting for the additional `workflow_dispatch` hop from the thin dispatcher
  to the progression workflow).
- **NFR-002**: The consolidated workflow MUST maintain the existing concurrency behavior (`cancel-in-progress: false`) to prevent race conditions between phases of the same issue. The thin dispatcher
  MUST retain its own per-issue concurrency group to serialize dispatch attempts.
- **NFR-003**: The thin dispatcher MUST complete (dispatch and exit) within 30 seconds, as it performs no generation logic.
- **NFR-004**: Error messages from the consolidated workflow MUST clearly indicate which phase failed (e.g., "Phase 1 (specify) failed: ...") and provide actionable troubleshooting steps including a
  link to the workflow run logs.

### Key Entities

- **Phase Progression Workflow**: The single canonical workflow (`speckit-phase-progression.yml`) that orchestrates all phases 1–5 of the SpecKit pipeline.
- **Thin Dispatcher**: A minimal workflow (`speckit-issue-trigger.yml`) that converts an `issues:labeled` event into a `workflow_dispatch` call to the progression workflow. Uses `GITHUB_TOKEN` for the
  dispatch API call. Retains its own per-issue concurrency group.
- **Phase 1 (Specify)**: The initial speckit phase that generates `spec.md` from a GitHub issue's title and body. Produces `spec.md` and empty `checklists/` and `contracts/` directories (does NOT
  produce `checklists/requirements.md`, which is a Phase 2 artifact).
- **PR Token**: Either `SPECKIT_PR_TOKEN` or `COPILOT_GITHUB_TOKEN` — a personal access token belonging to a human identity used for PR creation to trigger CI and Copilot review. Resolved with
  `SPECKIT_PR_TOKEN` taking precedence; fallback to `COPILOT_GITHUB_TOKEN`; never falls back to `GITHUB_TOKEN`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Phase 1 PRs are authored by a human identity (token-holder), not `github-actions[bot]`, verified by checking the PR author field.
- **SC-002**: CI checks and Copilot review are automatically triggered on Phase 1 PRs without manual intervention.
- **SC-003**: Zero duplicate logic exists between the dispatcher and the progression workflow — the dispatcher contains only event detection and dispatch invocation (< 30 lines of workflow YAML
  logic).
- **SC-004**: All existing Phase 1 functionality (idempotency, auto-merge label, failure comments, draft mode, label management) works identically when executed through the progression workflow.
- **SC-005**: The Python `speckit_trigger.py` module no longer contains git commit, push, or PR creation logic. The `agdt-speckit-trigger` entry point exists as a stub that exits with code 1 and an
  informative migration message.
- **SC-006**: A single `workflow_dispatch` on `speckit-phase-progression.yml` with `phase=1` and `issue_number=N` produces a complete Phase 1 PR — testable manually by maintainers.
- **SC-007**: All existing tests pass after the consolidation, and workflow documentation accurately reflects the new architecture.

---
*Generated by Copilot SDK (claude-opus-4.6)*
