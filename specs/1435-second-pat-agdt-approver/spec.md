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

## Clarifications

### Session 2026-05-15

- Q: Should the secondary approver account be an organization member with a specific role, or is a collaborator with write access sufficient? → A: The approver account must be added as a member of the
  `ayaiayorg` organization with the **Write** role on the `agentic-devtools` repository (or added as a direct collaborator with write access). Organization membership is preferred because it
  simplifies permission auditing, but either approach satisfies the technical requirement — the account needs `pulls: write` on the target repository.
- Q: Is there an existing secondary automation account to use, or does one need to be created as part of this work? → A: A new secondary automation account must be created as part of this work. The
  account should follow the naming convention of the organization (e.g., `ayaiayorg-pr-approver` or similar). Creating the account, generating the PAT, and configuring the repository secret are
  in-scope for this feature.
- Q: Should the approver PAT be a fine-grained token (recommended, scoped to single repo) or a classic token (broader scope but simpler setup)? → A: A fine-grained Personal Access Token is required.
  It must be scoped exclusively to the `ayaiayorg/agentic-devtools` repository with the single permission `Pull requests: Write`. Fine-grained tokens are preferred because they enforce least-privilege
  by design and provide a clear audit trail.
- Q: How should the `AGDT_PR_APPROVER_PAT` be injected into the approval path — via a dedicated workflow step or via the existing Python orchestrator? → A: Use the existing orchestrator
  path: wire `AGDT_PR_APPROVER_PAT` as an environment variable in the "Run AI PR loop orchestrator" step's `env` block in `.github/workflows/ai-pr-loop.yml`, and update
  `agentic_devtools/cli/ci/github_provider.py` so `approve_pr()` reads `AGDT_PR_APPROVER_PAT` (when set) instead of the default `GH_TOKEN`. This keeps the implementation within the existing Python
  orchestrator pattern, avoids adding a separate `actions/github-script@v7` step, and ensures the token is automatically masked in logs by GitHub Actions (all `env` secrets are masked).
- Q: Should the PAT availability check (FR-003) happen as a separate preceding step or as an early-exit guard within the existing approval path? → A: The check should be an early-exit guard within
  `approve_pr()` in `github_provider.py` (not a separate step). This keeps the workflow YAML minimal, avoids adding conditional logic between steps, and matches the existing pattern where safety
  checks are early returns within the same function.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Automated PR Approval Succeeds for Bot-Authored PRs (Priority: P1)

**Implements**: FR-001, FR-004

As an automation workflow, I need to approve pull requests that were authored by the primary bot account, so that the approve-and-merge loop can complete without manual intervention.

**Why this priority**: This is the core problem. Without it, the entire AI PR Loop approval step is non-functional for bot-authored PRs, which is the dominant use case.

**Independent Test**: Trigger the `ai-pr-loop` workflow on a PR authored by the primary bot account. Verify that the orchestrator's `approve_pr()` call succeeds and the approval is attributed
to the secondary approver account.

**Acceptance Scenarios**:

1. **Given** a PR authored by the primary automation account and all checks are passing, **When** the orchestrator executes `approve_pr()`, **Then** the PR receives an `APPROVE` review from the
   secondary approver account (not the PR author).
2. **Given** the `AGDT_PR_APPROVER_PAT` secret is configured in the repository, **When** the orchestrator step runs, **Then** `approve_pr()` in `github_provider.py` authenticates using the approver
   PAT from the `AGDT_PR_APPROVER_PAT` environment variable, not the default `GH_TOKEN`.
3. **Given** the PR head SHA has changed since the merge-check step validated it, **When** `approve_pr()` runs with the approver PAT, **Then** the function aborts approval (existing safety check
   preserved).

---

### User Story 2 — Graceful Degradation When Approver PAT Is Missing (Priority: P2)

**Implements**: FR-003

As a repository maintainer, I need the workflow to fail gracefully if the `AGDT_PR_APPROVER_PAT` secret is not configured, so that I receive clear diagnostics without the workflow crashing or silently
succeeding.

**Why this priority**: Operational safety — misconfigured secrets should produce actionable error messages, not cryptic failures.

**Independent Test**: Remove or leave the `AGDT_PR_APPROVER_PAT` secret unconfigured. Trigger the workflow and confirm `approve_pr()` logs a clear warning and skips approval gracefully.

**Acceptance Scenarios**:

1. **Given** the `AGDT_PR_APPROVER_PAT` secret is not set in the repository, **When** `approve_pr()` executes, **Then** the function logs a structured warning stating the approver PAT is missing and
   skips the approval gracefully (orchestrator continues without approving). The check is performed as an early-exit guard within `approve_pr()` (not a separate workflow step).
2. **Given** the `AGDT_PR_APPROVER_PAT` secret is set but invalid/expired, **When** the approval API call fails with a 401, **Then** `approve_pr()` logs the authentication error clearly and skips
   approval gracefully.

---

### User Story 3 — Token Scope Isolation (Priority: P2)

**Implements**: FR-002, FR-005

As a security-conscious maintainer, I need the `AGDT_PR_APPROVER_PAT` to be used exclusively for PR approval and not leak into other workflow steps, so that the blast radius of a compromised token is
minimized.

**Why this priority**: Principle of least privilege — the approver token should only be accessible to the step that needs it.

**Independent Test**: Inspect the workflow YAML to confirm the approver PAT is only referenced in the orchestrator step's `env` block and in `github_provider.py`'s `approve_pr()`, and nowhere else.

**Acceptance Scenarios**:

1. **Given** the updated workflow file, **When** a reviewer inspects all steps other than the orchestrator step, **Then** no step references `AGDT_PR_APPROVER_PAT`.
2. **Given** the workflow runs end-to-end, **When** non-approval code paths execute (e.g., merge, comment posting), **Then** they continue to use their existing token (`GITHUB_TOKEN` or
   `COPILOT_GITHUB_TOKEN`) unchanged.

---

### User Story 4 — Documentation and Maintainer Guidance (Priority: P3)

**Implements**: FR-006, FR-007

As a new maintainer onboarding to the repository, I need documentation explaining the purpose of the `AGDT_PR_APPROVER_PAT` secret and how to rotate it, so that I can maintain the automation without
tribal knowledge.

**Why this priority**: Long-term maintainability — secrets require documentation for rotation and troubleshooting.

**Independent Test**: A new maintainer can find and follow instructions to create, configure, and rotate the approver PAT without assistance.

**Acceptance Scenarios**:

1. **Given** the repository documentation, **When** a maintainer searches for "AGDT_PR_APPROVER_PAT," **Then** they find an explanation of its purpose, required permissions (fine-grained token scoped
   to `ayaiayorg/agentic-devtools` with `Pull requests: Write`), and rotation procedure.
2. **Given** the workflow YAML, **When** a maintainer reads the orchestrator step, **Then** inline comments explain why a separate token is used (GitHub prevents approving your own PR).

---

### Edge Cases

- What happens when the approver account is the same as the PR author? The approval will fail with GitHub's "cannot approve your own PR" error — this must be treated as a configuration error with a
  clear diagnostic message.
- What happens when the approver account lacks write access to the repository? The API call returns 403 — `approve_pr()` must log this and skip approval gracefully.
- What happens when branch protection requires approval from a CODEOWNERS member and the approver account is not one? The approval succeeds but may not satisfy branch protection — this is out of scope
  for this feature (branch protection rules are a repository configuration concern).
- What happens if the PAT expires mid-workflow run? The API call fails with 401 — the error handling in `approve_pr()` catches this and skips approval gracefully.
- What happens if `AGDT_PR_APPROVER_PAT` is set to an empty string? The environment variable is empty — the early-exit guard in `approve_pr()` must detect this (empty or whitespace-only) and treat
  it the same as a missing secret.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `approve_pr()` function in `agentic_devtools/cli/ci/github_provider.py` MUST authenticate using the `AGDT_PR_APPROVER_PAT` environment variable (when set) for the
  `pulls.createReview` API call, with the secret wired via the `env` block of the "Run AI PR loop orchestrator" step in `.github/workflows/ai-pr-loop.yml`.
- **FR-002**: The `AGDT_PR_APPROVER_PAT` MUST NOT be used by any workflow step other than the orchestrator step that executes PR approval, and MUST NOT be consumed by merge or comment code paths.
- **FR-003**: The `approve_pr()` function MUST include an early-exit guard that validates the approver PAT is available (non-empty) before attempting the approval API call, logging a structured warning
  if it is missing and skipping the approval gracefully (orchestrator continues without approving).
- **FR-004**: The existing SHA-mismatch safety check (abort approval if head SHA changed) MUST be preserved unchanged.
- **FR-005**: The merge step MUST continue to use its existing token (not the approver PAT).
- **FR-006**: Workflow comments MUST document why a separate PAT is required for the approval step.
- **FR-007**: Repository documentation MUST describe the required permissions for the `AGDT_PR_APPROVER_PAT` (fine-grained token scoped to `ayaiayorg/agentic-devtools` with permission `Pull requests:
  Write`).

### Non-Functional Requirements

- **NFR-001**: The change MUST NOT increase workflow execution time — no additional API calls beyond the existing approval flow (the early-exit guard is a string-empty check, not an API call).
- **NFR-002**: The approver PAT MUST be a fine-grained Personal Access Token scoped exclusively to the `ayaiayorg/agentic-devtools` repository with the single permission `Pull requests: Write`.
- **NFR-003**: The secret MUST be masked in workflow logs. Wiring the secret via the `env` block ensures automatic masking by GitHub Actions. The implementation MUST NOT echo,
  interpolate into shell commands, or otherwise expose the token value in logs. The approver account MUST be added as an organization member of `ayaiayorg` with Write access to the `agentic-devtools`
  repository (or as a direct collaborator with write access).

### Key Entities

- **AGDT_PR_APPROVER_PAT**: A fine-grained GitHub Personal Access Token belonging to a secondary automation account, stored as a repository secret, scoped exclusively to `ayaiayorg/agentic-devtools`
  with `Pull requests: Write` permission.
- **Secondary Approver Account**: A dedicated GitHub user account (e.g., `ayaiayorg-pr-approver`) distinct from the primary automation account that authors PRs. This account is the identity under
  which automated approvals appear. It must be created as part of this feature and added as a member of the `ayaiayorg` organization with Write access to the repository.

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

1. ~~[NEEDS CLARIFICATION]~~: **Resolved** — The secondary approver account should be an organization member of `ayaiayorg` with Write access to the `agentic-devtools` repository (preferred), or added
   as a direct collaborator with write access. Organization membership is preferred for audit simplicity.
2. ~~[NEEDS CLARIFICATION]~~: **Resolved** — A new secondary automation account must be created as part of this work (e.g., `ayaiayorg-pr-approver`). Creating the account, generating the fine-grained
   PAT, and configuring the `AGDT_PR_APPROVER_PAT` repository secret are all in-scope.
3. ~~[NEEDS CLARIFICATION]~~: **Resolved** — A fine-grained Personal Access Token is required, scoped exclusively to `ayaiayorg/agentic-devtools` with the single permission `Pull requests: Write`.
   Fine-grained tokens enforce least-privilege and provide clear audit trails.

---
*Generated by Copilot SDK (claude-opus-4.6)*
