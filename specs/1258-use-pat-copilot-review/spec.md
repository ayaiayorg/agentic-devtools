# Feature Specification: Use PAT for Copilot Review Request in SpecKit Workflows

**Feature Branch**: `1258-copilot-review-pat`
**Created**: 2026-04-22
**Status**: Draft
**Input**: GitHub Issue #1258 — SpecKit workflows fail to request Copilot review because `actions/github-script@v7` defaults to `GITHUB_TOKEN`, which lacks permission to add
`copilot-pull-request-reviewer` as a reviewer.
**Source Issue**: #1258 (<https://github.com/ayaiayorg/agentic-devtools/issues/1258>)

## Problem Statement

Three SpecKit GitHub Actions workflows contain a "Request Copilot Review" step that calls the GitHub REST API to add `copilot-pull-request-reviewer` as a reviewer on newly created pull requests. These
steps use `actions/github-script@v7` without an explicit `github-token` input, meaning they authenticate with the workflow-level `GITHUB_TOKEN`. This machine token is not recognized as a repository
collaborator with Copilot access, so the API responds with:

> Reviews may only be requested from collaborators. One or more of the users or teams you specified is not a collaborator of the ayaiayorg/agentic-devtools repository.

The steps are marked `continue-on-error: true`, so the workflow does not fail outright, but Copilot never reviews the PR — defeating a key quality gate in the SpecKit pipeline.

### Affected Workflows

| Workflow File | Step Name | Lines |
|---|---|---|
| `speckit-phase-progression.yml` | Request Copilot Review | 553–617 |
| `speckit-issue-trigger.yml` | Request Copilot Review | 339–405 |
| `speckit-copilot-review-request.yml` | Request Copilot Review | 98–144 |

### Existing PAT Infrastructure

The repository already has a `COPILOT_GITHUB_TOKEN` secret, validated and used in both `speckit-phase-progression.yml` (line 457) and `speckit-issue-trigger.yml` (line 235) for Copilot-powered
artifact generation. This secret is a candidate for reuse.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Copilot Review Is Automatically Requested on Phase-Progression PRs (Priority: P1)

As a repository maintainer relying on the SpecKit phase-progression pipeline, I want Copilot code review to be automatically requested when a spec PR is created during phase progression, so that every
generated spec PR receives automated review feedback without manual intervention.

**Why this priority**: This is the exact failure reported in #1258. Phase progression is the most frequently triggered SpecKit workflow and produces the majority of spec PRs. Without this fix, every
phase-progression PR silently misses Copilot review.

**Independent Test**: Trigger a phase-progression run (via PR merge or `workflow_dispatch`), confirm the "Request Copilot Review" step succeeds, and verify `copilot-pull-request-reviewer` appears as a
requested reviewer on the resulting PR.

**Acceptance Scenarios**:

1. **Given** a SpecKit phase-progression workflow run that creates a PR, **When** the "Request Copilot Review" step executes, **Then** the step authenticates with a PAT that has collaborator-level
   access, requests `copilot-pull-request-reviewer` as a reviewer, and the step output `copilot_review_requested` is `'true'`.

2. **Given** a SpecKit phase-progression workflow run where Copilot review was already requested on the PR, **When** the "Request Copilot Review" step executes, **Then** the step detects the existing
   reviewer (either via the idempotency check or a 422 response) and succeeds without error.

3. **Given** a SpecKit phase-progression workflow run where the PAT secret is not configured, **When** the workflow starts, **Then** the existing "Validate Copilot Token" step fails the workflow early
   with a clear error message, before the review-request step is reached.

---

### User Story 2 — Copilot Review Is Automatically Requested on Issue-Trigger PRs (Priority: P1)

As a repository maintainer, I want Copilot code review to be automatically requested when a spec PR is created by the issue-trigger workflow (Phase 1), so that initial spec PRs also receive automated
review feedback.

**Why this priority**: The issue-trigger workflow creates the first spec PR for every new issue. It has the same authentication defect as the phase-progression workflow and is equally critical.

**Independent Test**: Apply the `speckit:spec-needed` label to an issue, confirm the "Request Copilot Review" step succeeds, and verify `copilot-pull-request-reviewer` appears on the resulting PR.

**Acceptance Scenarios**:

1. **Given** a SpecKit issue-trigger workflow run that creates a PR, **When** the "Request Copilot Review" step executes, **Then** the step authenticates with a PAT that has sufficient permissions,
   and `copilot-pull-request-reviewer` is successfully added as a reviewer.

2. **Given** the PAT secret is missing or empty, **When** the workflow's "Validate Copilot Token" step runs, **Then** the workflow fails with a descriptive error before reaching the review-request
   step.

---

### User Story 3 — Copilot Review Is Automatically Requested on Implementation PRs (Priority: P1)

As a repository maintainer, I want Copilot code review to be automatically requested when an implementation PR is opened by the Copilot coding agent or when the `speckit:implementation` label is
applied, so that implementation PRs also receive automated Copilot review.

**Why this priority**: The `speckit-copilot-review-request.yml` workflow has the identical token defect. Unlike the other two workflows, it does not currently validate the PAT upfront and does not use
`COPILOT_GITHUB_TOKEN` elsewhere, but it needs the same fix for consistency and correctness.

**Independent Test**: Open a PR authored by `copilot-swe-agent[bot]` (or apply the `speckit:implementation` label to an existing PR), confirm the "Request Copilot Review" step succeeds, and verify
`copilot-pull-request-reviewer` appears as a requested reviewer.

**Acceptance Scenarios**:

1. **Given** a PR opened by `copilot-swe-agent[bot]` or labeled `speckit:implementation`, **When** the `speckit-copilot-review-request` workflow's "Request Copilot Review" step executes, **Then** it
   authenticates with a PAT and successfully requests `copilot-pull-request-reviewer`.

2. **Given** the idempotency check determines Copilot review is already requested or a review already exists, **When** the "Request Copilot Review" step is skipped, **Then** no error occurs and the
   workflow proceeds normally.

---

### User Story 4 — Consistent Token Usage Across All Copilot Review Steps (Priority: P2)

As a workflow maintainer, I want all "Request Copilot Review" steps across all SpecKit workflows to use the same authentication mechanism (the same PAT secret), so that token management is centralized
and there is a single secret to rotate or update.

**Why this priority**: Consistency reduces maintenance burden and eliminates the risk of one workflow being fixed while another is missed. This story is P2 because it is an architectural quality goal
rather than a user-facing defect.

**Independent Test**: Audit all three workflow files and confirm that every `actions/github-script@v7` step responsible for requesting Copilot review specifies the same `github-token` input
referencing the same secret name.

**Acceptance Scenarios**:

1. **Given** the three SpecKit workflow files, **When** a maintainer reviews the "Request Copilot Review" steps, **Then** all three use the identical secret reference for `github-token`.

2. **Given** the chosen PAT secret is rotated or replaced, **When** the new secret is saved in repository settings, **Then** all three workflows pick up the change without requiring individual edits.

---

### User Story 5 — Graceful Degradation When PAT Lacks Permissions (Priority: P3)

As a workflow operator, I want the "Request Copilot Review" steps to degrade gracefully (warning, not failure) if the PAT is valid but lacks the specific permission to request Copilot as a reviewer,
so that the rest of the workflow (PR creation, labeling, issue commenting) is not disrupted.

**Why this priority**: The existing `continue-on-error: true` already provides this behavior. This story ensures it is preserved and not accidentally removed during the fix.

**Independent Test**: Temporarily configure a PAT with `repo` scope but without Copilot access, trigger a workflow, and confirm the step emits a warning but the workflow completes successfully.

**Acceptance Scenarios**:

1. **Given** the PAT secret is configured but lacks permission to request Copilot review, **When** the review-request API call fails, **Then** the step logs a warning, sets `copilot_review_requested`
   to `'false'`, and the workflow continues to subsequent steps (e.g., auto-merge, issue comments).

---

### Edge Cases

- What happens when `COPILOT_GITHUB_TOKEN` is configured but has expired or been revoked? The API call should fail with an authentication error; `continue-on-error: true` ensures the workflow
  continues, and the warning message should be surfaced in the step logs.
- What happens when the same PAT is used for both artifact generation and review requesting, and rate limits are approached? Both uses are low-frequency (once per workflow run), so rate limiting is
  not a practical concern; however, the step's existing error handling will capture any 403 rate-limit responses.
- What happens if `copilot-pull-request-reviewer` is disabled at the organization or repository level? The API returns a collaborator error; the existing catch block handles this and emits a warning.
  No behavioral change is needed.
- What happens if the "Create Pull Request" step also needs the PAT? The issue notes that the Create PR step uses `secrets.GITHUB_TOKEN` and currently works. Changing the Create PR step's token is out
  of scope for this issue but should be evaluated separately if PR creation also encounters permission issues.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The "Request Copilot Review" step in `speckit-phase-progression.yml` MUST authenticate with a Personal Access Token (PAT) that has permission to request `copilot-pull-request-reviewer`
  as a reviewer, rather than the default `GITHUB_TOKEN`.

- **FR-002**: The "Request Copilot Review" step in `speckit-issue-trigger.yml` MUST authenticate with the same PAT as FR-001.

- **FR-003**: The "Request Copilot Review" step in `speckit-copilot-review-request.yml` MUST authenticate with the same PAT as FR-001.

- **FR-004**: All three "Request Copilot Review" steps MUST reference the same repository secret name for the PAT, ensuring centralized token management.

- **FR-005**: The existing idempotency logic (checking whether Copilot review is already requested or a review already exists) MUST be preserved without behavioral changes.

- **FR-006**: The existing error handling (422 "already requested" detection, `continue-on-error: true`, warning logging) MUST be preserved without behavioral changes.

- **FR-007**: The `speckit-copilot-review-request.yml` workflow SHOULD add a token validation step (consistent with the validation steps already present in the other two workflows) to fail fast when
  the secret is not configured. [NEEDS CLARIFICATION: Should the copilot-review-request workflow fail the entire job if the PAT is missing, or should it degrade gracefully since it only performs
  review requesting?]

- **FR-008**: The PAT used MUST belong to a user account that is a collaborator on the repository and has Copilot access enabled.

### Non-Functional Requirements

- **NFR-001**: The change MUST NOT introduce any new workflow steps that add latency beyond the existing API call overhead (sub-second per request).

- **NFR-002**: The change MUST NOT alter the workflow's behavior for any step other than "Request Copilot Review" (and optionally, adding a token validation step to
  `speckit-copilot-review-request.yml`).

- **NFR-003**: The change MUST be backward-compatible — if a repository fork does not have the PAT secret configured, the workflow MUST either fail fast at validation or degrade gracefully at the
  review-request step, matching current behavior patterns.

- **NFR-004**: The secret name used MUST follow existing repository conventions. The existing `COPILOT_GITHUB_TOKEN` secret is the preferred candidate unless a separate secret with more restrictive
  scope is warranted.

### Key Entities

- **`COPILOT_GITHUB_TOKEN`**: An existing repository secret containing a Personal Access Token. Currently used for Copilot-powered artifact generation. Candidate for reuse in review-request steps.
- **`copilot-pull-request-reviewer`**: The GitHub login used to request Copilot code review. Resolved by GitHub to `copilot-pull-request-reviewer[bot]` when listed as a reviewer.
- **`github-token` input**: The `actions/github-script@v7` input that overrides the default `GITHUB_TOKEN` for Octokit API calls within the script block.

## Clarifications Needed

1. [NEEDS CLARIFICATION: **Secret reuse vs. dedicated secret** — Should the existing `COPILOT_GITHUB_TOKEN` (used for artifact generation) be reused for review requesting, or should a separate secret
   (e.g., `COPILOT_REVIEW_PAT`) be created with minimal scopes? Reuse is simpler; a dedicated secret follows least-privilege.]

2. [NEEDS CLARIFICATION: **`speckit-copilot-review-request.yml` validation** — Should this workflow add a "Validate Copilot Token" step matching the other two workflows, or is the `continue-on-error`
   pattern sufficient given that this workflow's sole purpose is requesting review?]

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After the fix, 100% of SpecKit-generated PRs (across all three workflow triggers) have `copilot-pull-request-reviewer` listed as a requested reviewer or an existing Copilot review,
  verified by inspecting the next 5 workflow runs after deployment.

- **SC-002**: The "Request Copilot Review" step in all three workflows completes with `copilot_review_requested == 'true'` (not a warning/fallback) when the PAT is correctly configured, verified in
  the GitHub Actions step logs.

- **SC-003**: Zero regressions in other workflow steps — PR creation, branch pushing, artifact generation, auto-merge, and issue commenting all continue to function identically, verified by a full
  end-to-end SpecKit workflow run.

- **SC-004**: The warning `"Reviews may only be requested from collaborators"` no longer appears in any SpecKit workflow run logs after the fix is deployed.

---
*Generated by Copilot SDK (claude-opus-4.6)*
