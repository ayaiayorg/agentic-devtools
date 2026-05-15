# Feature Specification: Dedicated PR Approver PAT (AGDT_PR_APPROVER_PAT)

**Feature Branch**: `1435-pr-approver-pat`  
**Created**: 2026-05-15  
**Status**: Draft  
**Input**: GitHub Issue #1435 — Add a second PAT from a different account for PR approvals  
**Source Issue**: #1435 (<https://github.com/ayaiayorg/agentic-devtools/issues/1435>)

---

## Problem Statement

GitHub prevents a user from approving their own pull request. When the AI PR Loop automation creates a PR under one identity and then attempts to approve it with the same identity's token, the
approval fails silently or is rejected by GitHub. A dedicated Personal Access Token (`AGDT_PR_APPROVER_PAT`) from a separate GitHub account must be used exclusively for the PR approval step, enabling
fully automated approve-and-merge flows.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Automated PR Approval Succeeds for Bot-Authored PRs (Priority: P1)

**Implements**: FR-001, FR-004

As an automation workflow, I need to approve pull requests that were authored by the primary bot account, so that the approve-and-merge loop can complete without manual intervention.

**Why this priority**: This is the core problem. Without it, the entire AI PR Loop approval step is non-functional for bot-authored PRs, which is the dominant use case.

**Independent Test**: Trigger the `ai-pr-loop` workflow on a PR authored by the primary bot account. Verify that the "Approve PR" step succeeds and the approval is attributed to the secondary approver
account.

**Acceptance Scenarios**:

1. **Given** a PR authored by the primary automation account and all checks are passing, **When** the "Approve PR" step executes, **Then** the PR receives an `APPROVE` review from the secondary
   approver account (not the PR author).
2. **Given** the `AGDT_PR_APPROVER_PAT` secret is configured in the repository, **When** the "Approve PR" step runs, **Then** the Octokit client authenticates using the approver PAT, not the default
   `GITHUB_TOKEN`.
3. **Given** the PR head SHA has changed since the merge-check step validated it, **When** the "Approve PR" step runs with the approver PAT, **Then** the step aborts approval and outputs
   `approved=false` (existing safety check preserved).

---

### User Story 2 — Graceful Degradation When Approver PAT Is Missing (Priority: P2)

**Implements**: FR-003

As a repository maintainer, I need the workflow to fail gracefully if the `AGDT_PR_APPROVER_PAT` secret is not configured, so that I receive clear diagnostics without the workflow crashing or silently
succeeding.

**Why this priority**: Operational safety — misconfigured secrets should produce actionable error messages, not cryptic failures.

**Independent Test**: Remove or leave the `AGDT_PR_APPROVER_PAT` secret unconfigured. Trigger the workflow and confirm the step emits a clear warning/error and sets `approved=false`.

**Acceptance Scenarios**:

1. **Given** the `AGDT_PR_APPROVER_PAT` secret is not set in the repository, **When** the "Approve PR" step executes, **Then** the step emits a `core.warning` message stating the approver PAT is
   missing and sets output `approved=false`.
2. **Given** the `AGDT_PR_APPROVER_PAT` secret is set but invalid/expired, **When** the approval API call fails with a 401, **Then** the step logs the authentication error clearly and sets output
   `approved=false`.

---

### User Story 3 — Token Scope Isolation (Priority: P2)

**Implements**: FR-002, FR-005

As a security-conscious maintainer, I need the `AGDT_PR_APPROVER_PAT` to be used exclusively for PR approval and not leak into other workflow steps, so that the blast radius of a compromised token is
minimized.

**Why this priority**: Principle of least privilege — the approver token should only be accessible to the step that needs it.

**Independent Test**: Inspect the workflow YAML to confirm the approver PAT is only referenced in the "Approve PR" step's `github-token` input (or scoped `env` block) and nowhere else.

**Acceptance Scenarios**:

1. **Given** the updated workflow file, **When** a reviewer inspects all steps other than "Approve PR," **Then** no step references `AGDT_PR_APPROVER_PAT`.
2. **Given** the workflow runs end-to-end, **When** non-approval steps execute (e.g., merge, comment posting), **Then** they continue to use their existing token (`GITHUB_TOKEN` or
   `COPILOT_GITHUB_TOKEN`) unchanged.

---

### User Story 4 — Documentation and Maintainer Guidance (Priority: P3)

**Implements**: FR-006, FR-007

As a new maintainer onboarding to the repository, I need documentation explaining the purpose of the `AGDT_PR_APPROVER_PAT` secret and how to rotate it, so that I can maintain the automation without
tribal knowledge.

**Why this priority**: Long-term maintainability — secrets require documentation for rotation and troubleshooting.

**Independent Test**: A new maintainer can find and follow instructions to create, configure, and rotate the approver PAT without assistance.

**Acceptance Scenarios**:

1. **Given** the repository documentation, **When** a maintainer searches for "AGDT_PR_APPROVER_PAT," **Then** they find an explanation of its purpose, required permissions, and rotation procedure.
2. **Given** the workflow YAML, **When** a maintainer reads the "Approve PR" step, **Then** inline comments explain why a separate token is used.

---

### Edge Cases

- What happens when the approver account is the same as the PR author? The approval will fail with GitHub's "cannot approve your own PR" error — this must be treated as a configuration error with a
  clear diagnostic message.
- What happens when the approver account lacks write access to the repository? The API call returns 403 — the step must log this and set `approved=false`.
- What happens when branch protection requires approval from a CODEOWNERS member and the approver account is not one? The approval succeeds but may not satisfy branch protection — this is out of scope
  for this feature (branch protection rules are a repository configuration concern).
- What happens if the PAT expires mid-workflow run? The API call fails with 401 — the existing error handling catches this and sets `approved=false`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The "Approve PR" step in `.github/workflows/ai-pr-loop.yml` MUST authenticate using the `AGDT_PR_APPROVER_PAT` secret for the `pulls.createReview` API call.
- **FR-002**: The `AGDT_PR_APPROVER_PAT` MUST NOT be used by any workflow step other than PR approval.
- **FR-003**: The workflow MUST validate that the approver PAT is available before attempting the approval API call, emitting a clear warning if it is missing.
- **FR-004**: The existing SHA-mismatch safety check (abort approval if head SHA changed) MUST be preserved unchanged.
- **FR-005**: The merge step MUST continue to use its existing token (not the approver PAT).
- **FR-006**: Workflow comments MUST document why a separate PAT is required for the approval step.
- **FR-007**: Repository documentation MUST describe the required permissions for the `AGDT_PR_APPROVER_PAT` (minimum: `Pull requests: Write` for fine-grained tokens, or `repo` scope for classic
  tokens).

### Non-Functional Requirements

- **NFR-001**: The change MUST NOT increase workflow execution time (no additional API calls beyond the existing approval flow).
- **NFR-002**: The approver PAT MUST follow the principle of least privilege — only the minimum permissions required for PR approval.
- **NFR-003**: The secret MUST be masked in workflow logs (GitHub Actions masks secrets automatically, but the implementation must not circumvent this by echoing the value). [NEEDS CLARIFICATION:
  Should the approver account be added as a collaborator with write access, or should it be a member of the `ayaiayorg` organization?]

### Key Entities

- **AGDT_PR_APPROVER_PAT**: A GitHub Personal Access Token belonging to a secondary automation account, stored as a repository secret, scoped to PR write operations on `ayaiayorg/agentic-devtools`.
- **Secondary Approver Account**: A GitHub user account distinct from the primary automation account that authors PRs. This account is the identity under which automated approvals appear.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: PRs authored by the primary bot account are successfully approved by the AI PR Loop without manual intervention (0% approval failure rate due to "cannot approve own PR" errors).
- **SC-002**: The approval review in GitHub's PR timeline is attributed to the secondary approver account, not the PR author.
- **SC-003**: No other workflow step is affected by the change — existing merge, comment, and CI behaviors remain identical.
- **SC-004**: When the `AGDT_PR_APPROVER_PAT` secret is missing or invalid, the workflow produces a diagnostic message within the step's log output that names the secret and suggests corrective
  action.

---

## Clarification Items

1. [NEEDS CLARIFICATION]: Should the secondary approver account be an organization member with specific role, or is a collaborator with write access sufficient?
2. [NEEDS CLARIFICATION]: Is there an existing secondary automation account to use, or does one need to be created as part of this work?
3. [NEEDS CLARIFICATION]: Should the approver PAT be a fine-grained token (recommended, scoped to single repo) or a classic token (broader scope but simpler setup)?

---
*Generated by Copilot SDK (claude-opus-4.6)*
