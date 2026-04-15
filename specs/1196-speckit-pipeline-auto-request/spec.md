# Feature Specification: SpecKit Pipeline — Auto-Request Copilot Review After PR Creation

**Feature Branch**: `1196-speckit-pipeline-auto-request`
**Created**: 2026-04-15
**Status**: Draft
**Input**: GitHub Issue #1196 — SpecKit pipeline PRs fail the Copilot Review Gate because no Copilot review is requested after PR creation
**Source Issue**: #1196 (<https://github.com/ayaiayorg/agentic-devtools/issues/1196>)

## Problem Statement

The SpecKit pipeline creates pull requests at three distinct points in its lifecycle —
Phase 1 (specify) via `speckit-issue-trigger.yml`, Phases 2–5 (clarify, plan, tasks, analyze) via `speckit-phase-progression.yml`,
and implementation PRs via `speckit-implement-trigger.yml`.
None of these paths request a review from `copilot-pull-request-reviewer[bot]` after PR creation.
The repository has a required CI check (`Copilot Review ✅` in `copilot-review-gate.yml`) that fails when no Copilot review exists
for the latest commit.
This causes every SpecKit PR to fail CI initially and block auto-merge, requiring manual intervention to request the review.

## Scope

**In scope:**

- Requesting Copilot review after PR creation in the two SpecKit workflow files
  (`speckit-issue-trigger.yml` and `speckit-phase-progression.yml`)
- Optional Copilot review request in `create-spec-pr.sh` (the shared PR creation script)
- Handling the implementation trigger path (`speckit-implement-trigger.yml`)
  where the Copilot coding agent creates the PR asynchronously
- Configurable opt-out via repository variable

**Out of scope:**

- Polling/waiting for the Copilot review to complete within the pipeline
  (handled by existing `copilot-review-gate.yml` re-run mechanism and `gh pr merge --auto`)
- Modifying the `copilot-review-gate.yml` check itself
- Modifying the `agdt-gh-request-copilot-review` CLI command
- Changes to the non-SpecKit PR creation paths (Azure DevOps workflows, manual PRs)

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Copilot Review Auto-Requested for Spec Phase PRs (Priority: P1)

As a developer using the SpecKit pipeline, when a spec phase PR (Phases 1–5) is created by the pipeline,
a Copilot code review is automatically requested so the `Copilot Review ✅` CI check can pass without manual intervention.

**Why this priority**: This is the core problem described in the issue.
Both `speckit-issue-trigger.yml` (Phase 1) and `speckit-phase-progression.yml` (Phases 2–5) use `create-spec-pr.sh` to create PRs.
Without this, every SpecKit PR fails CI and blocks auto-merge, defeating the purpose of pipeline automation.

**Independent Test**: Can be fully tested by labeling an issue with `speckit` to trigger Phase 1,
then observing that the resulting PR has `copilot-pull-request-reviewer[bot]` listed as a requested reviewer
and the Copilot Review Gate check eventually passes.

**Acceptance Scenarios**:

1. **Given** a GitHub issue is labeled with `speckit` and the SpecKit issue-trigger workflow creates a Phase 1 PR,
   **When** the PR creation step completes successfully,
   **Then** the workflow requests a review from `copilot-pull-request-reviewer[bot]` on the newly created PR,
   and the request is verified by checking the PR's requested reviewers list.

2. **Given** a SpecKit phase PR is merged and the phase-progression workflow creates the next-phase PR (e.g., Phase 2),
   **When** the PR creation step completes successfully,
   **Then** the workflow requests a review from `copilot-pull-request-reviewer[bot]` on the newly created PR.

3. **Given** the PR creation step fails (e.g., `create-spec-pr.sh` outputs an empty `pr_number`),
   **When** the review-request step evaluates its condition,
   **Then** the review request step is skipped and the workflow continues to post its issue comment without error.

4. **Given** a SpecKit PR is created and Copilot review is requested,
   **When** the Copilot reviewer bot completes its review with zero comments,
   **Then** the `Copilot Review ✅` check passes and auto-merge (if configured) proceeds without manual intervention.

---

### User Story 2 — Copilot Review Auto-Requested for Implementation PRs (Priority: P2)

As a developer using the SpecKit pipeline, when the Copilot coding agent creates an implementation PR,
a Copilot code review is automatically requested so the implementation PR also passes the review gate CI check.

**Why this priority**: Implementation PRs are created asynchronously by the Copilot coding agent
(not by `create-spec-pr.sh`), so the integration point is different and more complex.
The `speckit-implement-trigger.yml` workflow assigns the agent but does not directly create the PR — the agent does.
A mechanism is needed to detect when the implementation PR appears and request the review.

**Independent Test**: Can be tested by labeling an issue with `speckit:needs-implementation`,
waiting for the Copilot coding agent to open the implementation PR,
then verifying that `copilot-pull-request-reviewer[bot]` is listed as a requested reviewer.

**Acceptance Scenarios**:

1. **Given** the `speckit-implement-trigger.yml` workflow assigns the Copilot coding agent to an issue,
   **When** the agent creates an implementation PR
   (detectable by the `speckit:implementation` label or `copilot-swe-agent[bot]` author),
   **Then** a Copilot code review is requested on that PR.

2. **Given** the Copilot coding agent has not yet created the implementation PR,
   **When** the implement-trigger workflow completes the agent assignment step,
   **Then** the workflow does not fail or block — the review request is deferred to when the PR actually exists.

3. **Given** an implementation PR already exists for the issue (idempotency check passes),
   **When** the implement-trigger workflow runs,
   **Then** the workflow skips agent assignment and idempotently requests or verifies the Copilot reviewer on the existing PR so the review gate can pass without manual intervention.

---

### User Story 3 — Configurable Opt-Out (Priority: P3)

As a repository administrator, I can disable the automatic Copilot review request for SpecKit PRs
via a repository variable, so I can control this behavior in environments where Copilot review is not available or not desired.

**Why this priority**: The default behavior should be to request the review (solving the issue),
but providing a configuration escape hatch follows the existing SpecKit pattern of
repository-variable-based configuration
(e.g., `SPECKIT_CREATE_PR`, `SPECKIT_CREATE_BRANCH`, `SPECKIT_AUTO_MERGE_PHASES`).

**Independent Test**: Can be tested by setting the repository variable to disable the feature,
triggering a SpecKit PR, and confirming no review is requested.

**Acceptance Scenarios**:

1. **Given** the repository variable `SPECKIT_REQUEST_COPILOT_REVIEW` is set to `false`,
   **When** a SpecKit PR is created,
   **Then** the Copilot review request step is skipped.

2. **Given** the repository variable `SPECKIT_REQUEST_COPILOT_REVIEW` is not set (default),
   **When** a SpecKit PR is created,
   **Then** the Copilot review is requested (opt-out by default).

3. **Given** the repository variable `SPECKIT_REQUEST_COPILOT_REVIEW` is set to `true`,
   **When** a SpecKit PR is created,
   **Then** the Copilot review is requested.

---

### Edge Cases

- What happens when the `gh api` call to request the reviewer fails (e.g., rate limit, permissions)?
  The step should use `continue-on-error: true` and log a warning —
  a failed review request must not fail the entire SpecKit workflow.
- What happens when the Copilot reviewer bot is not available in the repository (e.g., organization policy)?
  The request should fail gracefully with a warning.
- What happens when the PR is created as a draft?
  Copilot review can still be requested on draft PRs — no special handling needed.
- What happens when `create-spec-pr.sh` is called but `SPECKIT_CREATE_PR` is `false`?
  No PR is created, so no review request should be made —
  the step condition must check for a non-empty `pr_number`.
- What happens during a re-run of the workflow after the PR already exists?
  The review request is idempotent —
  requesting a reviewer that is already requested is a no-op in the GitHub API.
- What happens for the implementation PR path if the Copilot coding agent pushes multiple commits before completing?
  The `copilot-review-gate.yml` check runs on `synchronize` events, so each push triggers a new check.
  The initial review request covers the PR — Copilot re-reviews automatically on new pushes
  once it is a requested reviewer.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST request a review from `copilot-pull-request-reviewer[bot]`
  after successfully creating a SpecKit Phase 1 PR in the `speckit-issue-trigger.yml` workflow.
- **FR-002**: The system MUST request a review from `copilot-pull-request-reviewer[bot]`
  after successfully creating a SpecKit Phase 2–5 PR in the `speckit-phase-progression.yml` workflow.
- **FR-003**: The review request step MUST be conditional on a non-empty `pr_number` output
  from the PR creation step.
- **FR-004**: The review request step MUST use `continue-on-error: true` so that a failed review request
  does not fail the entire SpecKit workflow.
- **FR-005**: The review request step MUST log the outcome (success or failure)
  to the workflow output for debugging.
- **FR-006**: The system MUST support disabling the review request via the `SPECKIT_REQUEST_COPILOT_REVIEW`
  repository variable (set to `false` to disable; unset or `true` to enable).
- **FR-007**: The system MUST provide a mechanism for requesting Copilot review on implementation PRs
  created by the Copilot coding agent.
  [NEEDS CLARIFICATION: Should this be a separate workflow triggered by PR creation events
  with the `speckit:implementation` label, or should it be embedded in the `speckit.implement` agent instructions?]
- **FR-008**: The review request MUST use the GitHub REST API endpoint
  `POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers`
  with the reviewer login `copilot-pull-request-reviewer[bot]`,
  consistent with the existing `agdt-gh-request-copilot-review` implementation.
- **FR-009**: The review request step MUST be placed after PR creation and label application.
  If an issue comment step is present, the review request step SHOULD run before it.

### Non-Functional Requirements

- **NFR-001**: The review request step MUST complete within 30 seconds (single API call + optional verification GET).
  It MUST NOT poll or wait for the review to complete —
  that is handled by the existing `copilot-review-gate.yml` and `gh pr merge --auto` mechanisms.
- **NFR-002**: The review request MUST be idempotent — re-running the workflow when a review has already been requested
  MUST NOT produce errors or duplicate review requests.
- **NFR-003**: The implementation MUST be consistent with existing SpecKit workflow patterns:
  use `actions/github-script@v7` for GitHub API calls,
  respect the same `if:` condition patterns used by adjacent steps,
  and follow the existing `continue-on-error` / warning-logging patterns.
- **NFR-004**: For the phase/spec PR workflows, the implementation MUST NOT require additional permissions
  beyond what those workflows already have; existing `pull-requests: write` permission is sufficient
  for requesting reviewers on that path. For implementation PRs, `speckit-implement-trigger.yml`
  currently has only `pull-requests: read`, so that path requires either a permission update
  to `pull-requests: write` or a separate workflow/mechanism that performs the review request
  with the necessary permissions.

### Key Entities

- **SpecKit PR**: A pull request created by the SpecKit pipeline,
  identifiable by `speckit:phase-N` or `speckit:spec` labels. Created by `create-spec-pr.sh`.
- **Implementation PR**: A pull request created by the Copilot coding agent
  after being assigned via `speckit-implement-trigger.yml`.
  Identifiable by `speckit:implementation` label or `copilot-swe-agent[bot]` author.
- **Copilot Reviewer Bot**: The `copilot-pull-request-reviewer[bot]` GitHub user
  that performs automated code reviews when requested.
- **Copilot Review Gate**: The required CI check (`Copilot Review ✅`) defined in `copilot-review-gate.yml`
  that fails when no Copilot review exists for the latest commit.
- **Repository Variable `SPECKIT_REQUEST_COPILOT_REVIEW`**: Controls whether the auto-request behavior
  is enabled (default: enabled).

## Clarifications Needed

1. **[NEEDS CLARIFICATION]** For implementation PRs created by the Copilot coding agent:
   should the review request be triggered by a new/modified GitHub Actions workflow
   listening for PR events with the `speckit:implementation` label,
   or should it be added as an instruction in the `speckit.implement` agent definition
   (telling the agent to run `agdt-gh-request-copilot-review` after creating its PR)?
2. **[NEEDS CLARIFICATION]** Should the pipeline issue comment (e.g., "Phase 1 Completed") be updated
   to mention that a Copilot review has been requested,
   providing visibility into the automated review status?

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of SpecKit spec-phase PRs (Phases 1–5) have `copilot-pull-request-reviewer[bot]`
  as a requested reviewer within 30 seconds of PR creation, without manual intervention.
- **SC-002**: The `Copilot Review ✅` CI check passes on SpecKit PRs without requiring manual review requests —
  eliminating the failure mode described in issue #1196.
- **SC-003**: Auto-merge (when configured via `SPECKIT_AUTO_MERGE_PHASES`) proceeds unblocked
  for SpecKit phase PRs where the Copilot review finds zero issues.
- **SC-004**: Zero SpecKit workflow failures caused by the review request step —
  all API errors are handled gracefully with `continue-on-error` and warning logs.
- **SC-005**: The feature is fully backward-compatible —
  repositories without the `SPECKIT_REQUEST_COPILOT_REVIEW` variable see the new behavior enabled by default;
  repositories that set it to `false` retain the prior (no auto-request) behavior.

---
*Generated by Copilot SDK (claude-opus-4.6)*
