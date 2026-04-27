# Feature Specification: GitHub App Token for Copilot Review Requests

**Feature Branch**: `speckit/1283/phase-1-specify`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: GitHub issue #1283 — migrate Copilot review request authentication from PAT to GitHub App installation token  
**Source Issue**: #1283 (<https://github.com/ayaiayorg/agentic-devtools/issues/1283>)

## Problem Statement

All SpecKit GitHub Actions workflows that request Copilot code reviews currently authenticate using a personal access token stored in the `COPILOT_GITHUB_TOKEN` secret. This approach is fragile — PATs
expire, are tied to individual user accounts, and require manual rotation. A dedicated GitHub App (`agentic-devtools-copilot-reviewer`) has been installed on the repository with the necessary
permissions. This feature replaces every PAT reference with a short-lived installation token generated at runtime via `actions/create-github-app-token`, then updates all documentation that references
the old secret.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Copilot Review Requested via App Token on Phase PRs (Priority: P1)

As a contributor who merges a SpecKit phase PR, I want the next-phase PR to automatically receive a Copilot review request authenticated through the GitHub App so that the review pipeline works
without depending on a personal access token.

**Why this priority**: This is the core functionality. The `speckit-phase-progression.yml` workflow is the most frequently executed path — it runs on every phase merge and is the primary consumer of
the Copilot review request step. If this breaks, the entire SpecKit pipeline stalls.

**Independent Test**: Trigger phase progression on a test PR by merging a phase-1 PR into `main`. Verify that: (a) the `actions/create-github-app-token` step succeeds, (b) the Copilot review is
requested on the newly created phase-2 PR, and (c) no reference to `COPILOT_GITHUB_TOKEN` appears in the workflow logs.

**Acceptance Scenarios**:

1. **Given** the `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY` secrets are configured on the repository, **When** `speckit-phase-progression.yml` runs and creates a PR, **Then** a short-lived GitHub
   App installation token is generated and used to request a Copilot review on the new PR.
2. **Given** the Copilot reviewer bot is already assigned to the PR, **When** the workflow runs again (idempotency re-trigger), **Then** the workflow skips the review request without error, using the
   App token for the idempotency check.
3. **Given** the `COPILOT_APP_ID` secret is missing or empty, **When** the workflow runs, **Then** the validation step fails with a clear error message naming the missing App credential (not the old
   PAT name).
4. **Given** the App token is generated successfully, **When** the `Generate Phase Artifacts` step runs (which uses `COPILOT_GITHUB_TOKEN` as an env var for the Copilot SDK), **Then** the App token is
   passed as the SDK authentication credential under the same environment variable name expected by the SDK.

---

### User Story 2 — Copilot Review Requested via App Token on Initial Spec PRs (Priority: P1)

As a contributor who labels an issue with `speckit`, I want the initial specification PR to receive a Copilot review request authenticated through the GitHub App so that the same authentication
mechanism is used consistently across all SpecKit entry points.

**Why this priority**: The `speckit-issue-trigger.yml` workflow is the entry point for all new SpecKit issues. It shares the same authentication pattern as phase progression and must be migrated
together to avoid a split-brain configuration.

**Independent Test**: Create a GitHub issue, add the `speckit` label, and verify the resulting phase-1 PR has a Copilot review requested using the App token.

**Acceptance Scenarios**:

1. **Given** App credentials are configured, **When** `speckit-issue-trigger.yml` creates a phase-1 PR, **Then** a GitHub App installation token is generated and used to request a Copilot review.
2. **Given** the generated token is passed to the `Generate Specification` step as `COPILOT_GITHUB_TOKEN`, **When** the Copilot SDK is invoked, **Then** the SDK authenticates successfully using the
   App-generated token.
3. **Given** a workflow failure diagnostic comment is posted on the issue, **When** the comment references troubleshooting steps, **Then** the guidance refers to `COPILOT_APP_ID` /
   `COPILOT_APP_PRIVATE_KEY` (not the old PAT secret name).

---

### User Story 3 — Copilot Review Requested via App Token on Implementation PRs (Priority: P1)

As a contributor whose implementation PR is opened or labeled with `speckit:implementation`, I want the Copilot review request to be authenticated through the GitHub App so that all three Copilot
review request paths use the same mechanism.

**Why this priority**: The `speckit-copilot-review-request.yml` workflow is the dedicated Copilot review path for implementation PRs. It is simpler than the other two workflows but equally critical
for consistent authentication.

**Independent Test**: Open a PR authored by `copilot-swe-agent[bot]` targeting `main`, or add the `speckit:implementation` label to an existing PR, and verify the Copilot review is requested using the
App token.

**Acceptance Scenarios**:

1. **Given** App credentials are configured, **When** `speckit-copilot-review-request.yml` runs for an implementation PR, **Then** a GitHub App installation token is generated at the start of the job
   and used for the idempotency check and review request steps.
2. **Given** the App private key secret is malformed, **When** `actions/create-github-app-token` runs, **Then** the step fails with an error referencing the App configuration (not the old PAT).

---

### User Story 4 — Documentation Reflects New Authentication Method (Priority: P2)

As a new contributor reading the project documentation, I want the `README.md` and `CONTRIBUTING.md` to describe the GitHub App-based authentication so that I know which secrets to configure and do
not waste time creating a fine-grained PAT.

**Why this priority**: Documentation accuracy is essential for onboarding, but incorrect docs do not block existing automated workflows.

**Independent Test**: Search `README.md` and `CONTRIBUTING.md` for `COPILOT_GITHUB_TOKEN`. The string must not appear. Search for `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY` — both must appear in
the "Required Secrets" table.

**Acceptance Scenarios**:

1. **Given** the migration is complete, **When** a contributor reads the "Required Secrets" section in `README.md`, **Then** they see `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY` listed with
   descriptions referencing the GitHub App, and `COPILOT_GITHUB_TOKEN` is absent.
2. **Given** the migration is complete, **When** a contributor reads the "Required Secrets" section in `CONTRIBUTING.md`, **Then** the same App-based secrets are documented consistently with
   `README.md`.

---

### User Story 5 — Removal of Stale PAT Secret (Priority: P3)

As a repository administrator, I want the `COPILOT_GITHUB_TOKEN` Actions secret to be deletable from the repository settings after the migration so that no stale credentials remain.

**Why this priority**: Security hygiene. The old PAT should be removable without breaking any workflow. This is a verification/cleanup step that follows the code changes.

**Independent Test**: Delete the `COPILOT_GITHUB_TOKEN` secret from the repository, trigger all three workflows, and verify they complete successfully using only the App credentials.

**Acceptance Scenarios**:

1. **Given** all workflow files have been updated and `COPILOT_GITHUB_TOKEN` is deleted from repository secrets, **When** any of the three SpecKit workflows runs, **Then** no step references or
   requires `COPILOT_GITHUB_TOKEN`, and all Copilot review requests succeed.

---

### Edge Cases

- **What happens when `actions/create-github-app-token` rate-limits or the GitHub App installation is suspended?** The token generation step must fail with a clear error rather than silently producing
  an empty token. Downstream steps must not run with an empty authentication credential.
- **What happens when the App token expires mid-workflow?** GitHub App installation tokens are valid for 1 hour. The longest SpecKit workflow (phase progression with artifact generation) typically
  completes within minutes. If a workflow run exceeds the token lifetime, the failing step must surface the authentication error clearly.
- **What happens if both `COPILOT_GITHUB_TOKEN` and the App secrets are configured during a transition period?** The workflows must use only the App token path. The old secret must not be referenced
  even if it is still present in the repository.
- **What happens when the workflow runs on a fork PR?** Secrets are not available on fork PRs. The existing behavior (validation step fails, Copilot review is skipped) must be preserved — but the
  error message must reference the App credentials, not the PAT.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Each of the three workflows (`speckit-phase-progression.yml`, `speckit-issue-trigger.yml`, `speckit-copilot-review-request.yml`) MUST generate a GitHub App installation token using
  `actions/create-github-app-token` with `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY` secrets.
- **FR-002**: The generated installation token MUST be used as the `github-token` input for all `actions/github-script` steps that interact with the Copilot review API (idempotency check, review
  request).
- **FR-003**: The generated installation token MUST be passed as the `COPILOT_GITHUB_TOKEN` environment variable to the `Generate Phase Artifacts` and `Generate Specification` steps (for Copilot SDK
  compatibility) in `speckit-phase-progression.yml` and `speckit-issue-trigger.yml`.
- **FR-004**: The "Validate Copilot Token" step in each workflow MUST be replaced with validation that the `actions/create-github-app-token` step produced a non-empty token, or removed entirely if the
  action itself fails on missing credentials.
- **FR-005**: All references to `secrets.COPILOT_GITHUB_TOKEN` MUST be removed from all three workflow files.
- **FR-006**: Diagnostic/troubleshooting messages in workflow error annotations and issue comments MUST reference `COPILOT_APP_ID` and `COPILOT_APP_PRIVATE_KEY` instead of `COPILOT_GITHUB_TOKEN`.
- **FR-007**: `README.md` "Required Secrets" table MUST list `COPILOT_APP_ID` (App ID of the `agentic-devtools-copilot-reviewer` GitHub App) and `COPILOT_APP_PRIVATE_KEY` (PEM private key for the
  GitHub App) instead of `COPILOT_GITHUB_TOKEN`.
- **FR-008**: `CONTRIBUTING.md` "Required Secrets" table MUST be updated identically to FR-007.
- **FR-009**: The `actions/create-github-app-token` step MUST be placed early in each job (before any step that requires the token) and its output MUST be consumed by all subsequent steps that need
  authentication.
- **FR-010**: Existing idempotency guards (skip review request if Copilot is already a reviewer) MUST continue to function identically with the new token. [NEEDS CLARIFICATION: Does the GitHub App
  identity differ from the PAT user identity for the purposes of the `listRequestedReviewers` / `listReviews` API calls? Verify that the App-generated token can read reviewer lists and request
  reviewers.]

### Non-Functional Requirements

- **NFR-001**: Token generation MUST add no more than 10 seconds of wall-clock time to any workflow run. The `actions/create-github-app-token` action typically completes in 2–4 seconds.
- **NFR-002**: Workflow YAML changes MUST be backward-compatible during a transition period — specifically, a workflow re-run on an older commit that still references `COPILOT_GITHUB_TOKEN` must not
  crash in a way that is confusing. This is inherently satisfied because secret references resolve to empty strings when the secret is deleted, and the validation step will produce a clear error.
- **NFR-003**: Error messages MUST be actionable — they must name the exact secret(s) to configure and link to the GitHub App settings or installation page where possible.

### Key Entities

- **GitHub App (`agentic-devtools-copilot-reviewer`)**: The installed App that provides the authentication identity. Key attributes: App ID, private key, installation ID (auto-resolved by the action).
- **Installation Token**: A short-lived (1-hour) token generated per workflow run via `actions/create-github-app-token`. Scoped to the repository's App installation.
- **Copilot Reviewer Bot (`copilot-pull-request-reviewer[bot]`)**: The bot account that performs code reviews. Unchanged by this migration — only the token used to *request* its review changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero references to `COPILOT_GITHUB_TOKEN` exist in any `.github/workflows/*.yml` file after the migration.
- **SC-002**: Zero references to `COPILOT_GITHUB_TOKEN` exist in `README.md` or `CONTRIBUTING.md` after the migration.
- **SC-003**: All three workflows successfully request a Copilot review on a test PR using the App token, verified by the `copilot-pull-request-reviewer[bot]` appearing as a requested reviewer.
- **SC-004**: The `COPILOT_GITHUB_TOKEN` secret can be deleted from the repository without causing any workflow failure.
- **SC-005**: Workflow run duration does not increase by more than 15 seconds compared to the PAT-based baseline (accounting for the token generation step).

---
*Generated by Copilot SDK (claude-opus-4.6)*
