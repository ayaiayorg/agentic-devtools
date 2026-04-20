# Feature Specification: SpecKit Pipeline — Auto-Request Copilot Review After PR Creation

**Feature Branch**: `1196-speckit-pipeline-auto-request`
**Created**: 2026-04-15
**Status**: Draft
**Input**: GitHub Issue #1196 — SpecKit pipeline PRs fail the Copilot Review Gate because no Copilot review is requested after PR creation
**Source Issue**: #1196 (<https://github.com/ayaiayorg/agentic-devtools/issues/1196>)

## Overview

The SpecKit pipeline should automatically request a GitHub Copilot review after a
pull request is created by the automation flow. This should work for both spec
PRs and implementation PRs created by the pipeline, without requiring the agent
to remember a manual follow-up step.

The behavior must be implemented in GitHub Actions workflow automation, remain
consistent with existing repository workflow patterns, and provide visible status
feedback in the related issue comments when the review request succeeds or fails.

## Problem Statement

Today, automated pull request creation can complete without reliably requesting
Copilot review. That creates an inconsistent review experience, makes
implementation PRs easier to miss, and leaves issue comments without a clear
signal about whether the review request happened.

## Goals

- Automatically request Copilot review for pipeline-created pull requests.
- Support both spec PRs and implementation PRs.
- Keep the implementation inside repository workflows rather than agent-side instructions.
- Surface success or failure of the review request in existing issue comments.
- Align the implementation with existing workflow conventions already used in the repository.

## Non-Goals

- Reworking `create-spec-pr.sh` to perform reviewer requests directly.
- Adding a custom retry loop for Copilot reviewer requests.
- Replacing existing gate or recovery mechanisms.
- Changing unrelated workflow behavior outside the PR review request scope.

## Clarifications

### Session 2026-04-15

- Q: What mechanism should be used for implementation PRs in FR-007?
  → A: Use a new `speckit-copilot-review-request.yml` workflow triggered on `pull_request` events
  for `opened` and `labeled`; do not rely on agent instructions.
- Q: Should issue comments show whether the Copilot review request succeeded or failed?
  → A: Yes. Append a status line such as `🤖 Copilot review requested` or
  `⚠️ Copilot review request failed` to the existing comment flow.
- Q: Should this be implemented in `create-spec-pr.sh` or in workflow YAML? → A: Workflow YAML only. `create-spec-pr.sh` is out of scope for this feature.
- Q: Should the GitHub API call use `github-script` or `gh api`? → A: Use `actions/github-script@v7` with `github.rest.pulls.requestReviewers()` to match existing workflows.
- Q: Should the workflow retry failed review requests automatically?
  → A: No. Use `continue-on-error: true` and `core.warning()` so failure is visible while recovery remains
  handled by the existing gate mechanism.

## User Stories

### US-001: Auto-request Copilot review for a spec PR

As a maintainer, I want a Copilot review to be requested automatically when the pipeline creates a spec PR so that the PR enters the expected review flow without manual intervention.

### US-002: Auto-request Copilot review for an implementation PR

As a maintainer, I want a Copilot review to be requested automatically when the pipeline creates an implementation PR so that implementation work receives the same review coverage as spec work.

### US-003: Visible status in issue comments

As a maintainer, I want the issue comment trail to indicate whether the Copilot review request succeeded or failed so that I can understand pipeline status without opening the PR workflow logs first.

## Functional Requirements

### FR-001: Trigger after PR creation

The pipeline shall trigger Copilot review request automation after a pull request has been created by the SpecKit workflow.

### FR-002: Reviewer request target

The automation shall request GitHub Copilot as a reviewer for the created pull request.

### FR-003: Spec PR support

The automation shall support spec PRs created by the existing SpecKit pipeline.

### FR-004: Implementation PR support

The automation shall support implementation PRs created by the existing SpecKit pipeline.

### FR-005: Workflow-based implementation

The feature shall be implemented in GitHub Actions workflow YAML and not by adding reviewer-request logic to `create-spec-pr.sh`.

### FR-006: Existing comment flow integration

The automation shall update the existing issue-comment flow to expose the result of the Copilot reviewer request.

### FR-007: Implementation PR mechanism

Implementation PR Copilot review requests shall be handled by a dedicated `speckit-copilot-review-request.yml` workflow triggered on `pull_request` events of type `opened` and `labeled`.

### FR-008: GitHub API mechanism

The workflow shall request reviewers using `actions/github-script@v7` and `github.rest.pulls.requestReviewers()`.

### FR-009: Failure handling

If the reviewer request fails, the workflow shall continue execution, emit a warning, and leave recovery to the existing gate mechanism rather than implementing an inline retry loop.

### FR-010: Issue comment status updates

The issue comment output shall append one clear status line indicating either:

- `🤖 Copilot review requested`, or
- `⚠️ Copilot review request failed`

## Non-Functional Requirements

### NFR-001: Consistency

The solution should follow the same GitHub Actions implementation style already used by existing repository workflows.

### NFR-002: Minimal scope change

The solution should add the smallest workflow changes necessary to enable automatic review requests without broad refactoring.

### NFR-003: Standardized action usage

The solution should standardize on `actions/github-script@v7` rather than mixing workflow implementations between `github-script` and `gh api`.

### NFR-004: Least-privilege permissions

The new review-request workflow shall declare only the permissions it needs and shall not require unrelated permission changes to `speckit-implement-trigger.yml`.

### NFR-005: Observability

The workflow should make success and failure understandable from normal issue-comment output and workflow logs.

## Acceptance Criteria

### AC-001

Given a spec PR is created by the pipeline, when the PR creation flow completes, then GitHub Copilot is requested as a reviewer automatically.

### AC-002

Given an implementation PR is opened by the pipeline, when the `pull_request`
event of type `opened` is received, then the repository runs
`speckit-copilot-review-request.yml` and requests GitHub Copilot as a reviewer.

### AC-003

Given an implementation PR later receives the label required by the pipeline
flow, when the `pull_request` event of type `labeled` is received, then the
repository runs `speckit-copilot-review-request.yml` and requests GitHub
Copilot as a reviewer if not already requested.

### AC-004

Given the workflow performs the reviewer request, when the API call is made, then it uses `actions/github-script@v7` with `github.rest.pulls.requestReviewers()`.

### AC-005

Given the reviewer request succeeds, when the issue comment is updated, then the comment includes the appended line `🤖 Copilot review requested`.

### AC-006

Given the reviewer request fails, when the workflow handles the failure, then the job continues, emits a warning, and the issue comment includes the appended line `⚠️ Copilot review request failed`.

### AC-007

Given the feature is implemented, when the repository changes are reviewed, then reviewer-request logic exists in workflow YAML and not in `create-spec-pr.sh`.

### AC-008

Given the new workflow is introduced, when permissions are evaluated, then they are scoped to the new workflow and do not require unrelated changes to `speckit-implement-trigger.yml`.

## Success Criteria

- **SC-001:** Spec PRs created by the pipeline receive an automatic Copilot reviewer request.
- **SC-002:** Implementation PRs created by the pipeline receive an automatic Copilot reviewer request.
- **SC-003:** The repository uses a single, consistent API mechanism for reviewer requests based on `actions/github-script@v7`.
- **SC-004:** Failures are visible to maintainers without blocking the broader workflow unexpectedly.
- **SC-005:** Issue comments clearly reflect whether the reviewer request succeeded or failed.
- **SC-006:** Implementation PR reviewer coverage is achieved within 60 seconds of the relevant `pull_request` `opened` or `labeled` event under normal GitHub Actions execution conditions.

## Edge Cases

- If the reviewer request is attempted for a PR that already has Copilot requested, the workflow should avoid producing misleading duplicate-status messaging.
- If the workflow is triggered by `labeled` after `opened` already requested the reviewer successfully, the workflow should remain safe and not break the pipeline.
- If a reviewer request fails because of transient GitHub API issues, the workflow should log a warning, continue execution, and rely on the existing gate mechanism for follow-up handling.
- If issue comment updates run after a failed reviewer request, the failure status line should still be appended so the outcome is visible.
- If the workflow runs for an implementation PR before all expected labels are present, the behavior should remain safe and re-triggerable via the supported `labeled` event.
- If permissions are insufficient in the new workflow, the failure should be observable from the workflow warning and issue comment status rather than silently ignored.

## Notes

- This spec intentionally keeps the logic in GitHub Actions workflows.
- This spec intentionally removes `create-spec-pr.sh` from implementation scope for reviewer-request behavior.
- The clarified decisions above are normative and are already reflected in the requirements, acceptance criteria, success criteria, and edge cases.
