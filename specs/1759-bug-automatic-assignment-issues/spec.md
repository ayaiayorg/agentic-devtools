# Feature Specification: Fix Agent Assignment Token in speckit-implement-trigger Workflow

**Feature Branch**: `speckit/1759/phase-2-clarify`  
**Created**: 2026-06-03  
**Status**: Draft  
**Input**: GitHub Issue #1759 — silent failure of Copilot coding agent assignment after phase 5 spec PR merge  
**Source Issue**: #1759 (<https://github.com/ayaiayorg/agentic-devtools/issues/1759>)

## Clarifications

### Session 2026-06-03

- Q: FR-007 states the "Update Labels" step must also use the elevated token, but should the "Post Implementation Triggered Comment" step (line 455+) that also follows the assignment step
  also be updated to use the same elevated token pattern? → A: Yes. All steps in the job that follow the agent assignment step — including "Update Labels" and "Post Implementation Triggered
  Comment" — must use the elevated token pattern (`SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN`) since they operate on the same issue and the `GITHUB_TOKEN` permissions may be insufficient for
  label mutation or commenting in forked-repo scenarios. FR-007 is expanded to cover both steps.

- Q: Should the preflight check be a separate workflow step (its own `- name:` block) or inline logic at the top of the existing `actions/github-script` step? → A: It must be a separate workflow step
  with its own `- name:` block (e.g., `"Validate Agent Assignment Token"`). This keeps concerns separated, makes the failure point unambiguous in the GitHub Actions UI, and allows the assignment
  step's `if:` condition to depend on the preflight step's outcome.

- Q: How should the step verify that the `agent_assignment` was actually applied (FR-004 / edge case about API ignoring the field)? Specifically, should it perform a follow-up GET request to confirm
  assignment, or is validating the PATCH response body sufficient? → A: Validating the PATCH response body is sufficient for the initial fix. The step must check that the response status is 200 and
  that the response body contains a non-null `agent_assignment` field. If the response is 200 but `agent_assignment` is null or absent in the response, the step must emit a `::warning::` annotation
  indicating the assignment may not have taken effect and set `assigned` output to `'false'`. A follow-up GET verification can be added as a future enhancement but is out of scope for this fix.

- Q: The spec references the `github-token` input of `actions/github-script@v7` — should the token be passed via the `github-token` input (which replaces the octokit instance's auth) or via
  an environment variable used inside the script? → A: The token must be passed via the `github-token` input of `actions/github-script@v7`, exactly as done in `speckit-phase-progression.yml`
  (line 552 pattern: `GH_TOKEN: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}`). However, since `actions/github-script` uses `github-token` (not `GH_TOKEN` env var) to
  authenticate the `github` octokit instance, the correct pattern is: `github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}` in the `with:` block.

- Q: NFR-004 constrains the change to the single workflow file, but what if the `permissions` block (currently `issues: write`, `contents: read`, `pull-requests: read`) needs adjustment for the
  PAT-based approach? → A: The `permissions` block does not need adjustment. When a PAT is passed via `github-token`, the PAT's own scopes determine authorization — the workflow `permissions` block
  only constrains the default `GITHUB_TOKEN`. Since the fix explicitly avoids using `GITHUB_TOKEN`, the existing permissions block is irrelevant to the agent assignment step and should remain
  unchanged to avoid unintended side effects.

## Problem Statement

The speckit pipeline is designed as a fully automated specification-to-implementation conveyor: once a phase 5 specification PR merges, the `speckit:needs-implementation` label is applied, triggering
`speckit-implement-trigger.yml` to automatically assign the Copilot coding agent to the originating issue. This automation is a critical link in the pipeline — without it, issues that have completed
the specification phase stall indefinitely, requiring manual intervention from a maintainer to kick off the implementation phase.

Currently, the "Assign Copilot Coding Agent" step in `speckit-implement-trigger.yml` (lines 381–410) uses `actions/github-script@v7`
without specifying a `github-token` input. This causes the step to authenticate with the default `GITHUB_TOKEN` provided by GitHub
Actions. The `GITHUB_TOKEN` is a GitHub Actions–issued, job-scoped token whose permissions are limited to the explicit `permissions`
block declared in the workflow. While the workflow declares `issues: write`, the agent assignment API (`PATCH /repos/{owner}/{repo}/issues/{issue_number}`
with an `agent_assignment` payload) requires elevated permissions that are only available through a Personal Access Token (PAT) with
broader repository and Copilot scopes. The observed symptom is that assignment does not take effect even when the workflow appears to
complete successfully. One plausible failure mode is a 2xx response where the API ignores `agent_assignment` rather than applying it,
which this fix must make observable and validate.

The consequence is significant: every feature that completes the specification pipeline (phases 1 through 5) becomes stranded. The `speckit:needs-implementation` label is applied, the workflow runs,
but the actual Copilot agent assignment never takes effect. A maintainer must then manually discover the stalled issue and trigger implementation, defeating the purpose of the automated pipeline. This
problem has been observed in production and affects all repositories using the speckit workflow automation. The fix must align the agent assignment step with the proven token pattern already used
successfully throughout the pipeline — namely `SPECKIT_PR_TOKEN` with `COPILOT_GITHUB_TOKEN` as fallback — while adding observability so that token misconfiguration is caught early rather than failing
silently.

## User Scenarios & Testing

### User Story 1 - Automatic Agent Assignment After Spec Merge (Priority: P1)

Related Requirements: FR-001, FR-004, FR-005, FR-006, FR-007

As a repository maintainer relying on the speckit automation pipeline, I need the Copilot coding agent to be automatically and reliably assigned to an issue when its phase 5 specification PR merges,
so that the implementation phase begins without any manual intervention.

Today, after a phase 5 PR merges, the `speckit:needs-implementation` label correctly triggers the implementation workflow. However, the agent assignment step silently fails because it authenticates
with an insufficiently privileged token. This means the issue sits idle until someone notices and manually assigns the agent. With the fix, the same PAT that successfully creates PRs and requests
Copilot reviews throughout the pipeline will be used for agent assignment, ensuring the operation succeeds.

**Why this priority**: This is the core bug. Without this fix, the entire automated implementation trigger is non-functional. Every other improvement (logging, preflight checks) is meaningless if the
primary operation cannot succeed.

**Independent Test**: Can be fully tested by merging a phase 5 spec PR and verifying that the originating issue receives a Copilot coding agent assignment with the `speckit.implement` agent and the
configured model (default `claude-opus-4.6`).

**Acceptance Scenarios**:

1. **Given** a repository with `SPECKIT_PR_TOKEN` configured and a phase 5 spec PR that has been approved, **When** the PR merges and `speckit:needs-implementation` is applied to the issue, **Then**
   the `speckit-implement-trigger.yml` workflow assigns the Copilot coding agent to the issue using `SPECKIT_PR_TOKEN` via the `github-token` input of `actions/github-script@v7` and the step completes
   with exit code 0.

2. **Given** a repository where `SPECKIT_PR_TOKEN` is not configured but `COPILOT_GITHUB_TOKEN` is, **When** the implementation trigger workflow runs, **Then** the agent assignment step falls back to
   `COPILOT_GITHUB_TOKEN` and the assignment succeeds.

3. **Given** a repository with both tokens configured and a valid issue number, **When** the agent assignment step executes, **Then** the issue shows the Copilot coding agent assigned with
   `custom_agent: 'speckit.implement'` and the model matching the `COPILOT_MODEL` environment variable.

4. **Given** a successful agent assignment where the API returns HTTP 200, **When** the response body contains a non-null `agent_assignment` field, **Then** the step sets `assigned` output to
   `'true'`. **When** the response body contains a null or absent `agent_assignment` field despite HTTP 200, **Then** the step emits a `::warning::` annotation indicating the assignment may not have
   taken effect and sets `assigned` output to `'false'`.

5. **Given** the `trigger-implementation` job in `.github/workflows/speckit-implement-trigger.yml`, **When** the workflow YAML is inspected after the fix, **Then** the `Update Labels` step and
   `Post Implementation Triggered Comment` step each explicitly set `github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}`.

---

### User Story 2 - Loud Failure on Missing Token (Priority: P2)

Related Requirements: FR-002

As a DevOps engineer configuring the speckit pipeline for a new repository, I need the workflow to fail loudly and with a clear error message if neither `SPECKIT_PR_TOKEN` nor `COPILOT_GITHUB_TOKEN`
is configured, so that I can diagnose setup problems immediately rather than debugging silent failures after deployment.

Currently, if no appropriate PAT is available, the step falls through to `GITHUB_TOKEN`, which lacks the required permissions for
agent assignment. The observed behavior is that the workflow can appear successful while assignment does not take effect; one plausible
explanation is a 2xx response that ignores `agent_assignment`. The fix adds a dedicated preflight validation step that checks token
availability before attempting the assignment, producing an actionable error message that names the required secrets.

**Why this priority**: Observability is second only to correctness. A clear error on misconfiguration prevents hours of debugging and ensures new repository onboarding surfaces problems at setup time,
not during the first real pipeline run.

**Independent Test**: Can be tested by temporarily removing both `SPECKIT_PR_TOKEN` and `COPILOT_GITHUB_TOKEN` secrets from a test repository, triggering the workflow, and verifying it produces an
explicit error annotation naming the missing secrets.

**Acceptance Scenarios**:

1. **Given** a repository where neither `SPECKIT_PR_TOKEN` nor `COPILOT_GITHUB_TOKEN` is configured, **When** the implementation
   trigger workflow reaches the token preflight check step, **Then** the step fails with a `::error::` annotation stating that at
   least one of these secrets must be configured for agent assignment.

2. **Given** a repository where only `SPECKIT_PR_TOKEN` is configured, **When** the preflight check runs, **Then** it passes and logs which token identity will be used (without revealing the token
   value).

---

### User Story 3 - Assignment Identity Logging (Priority: P3)

Related Requirements: FR-003

As a pipeline operator investigating a failed or suspicious agent assignment, I need the workflow to log which token identity was used for the assignment attempt, so that I can correlate the operation
with the correct PAT and verify it has appropriate scopes.

The current implementation provides no visibility into which authentication context was used. Since the step now supports two possible tokens with a fallback chain, operators need to know which one
was selected. The logging must mask the actual token value while clearly identifying whether `SPECKIT_PR_TOKEN` or `COPILOT_GITHUB_TOKEN` was used.

**Why this priority**: This is a quality-of-life improvement for operators. It does not affect whether the assignment succeeds but makes troubleshooting faster when issues arise in the future.

**Independent Test**: Can be tested by running the workflow with both tokens configured and
inspecting the step output for a log line like `"Agent assignment token: SPECKIT_PR_TOKEN (primary)"` or
`"Agent assignment token: COPILOT_GITHUB_TOKEN (fallback)"`.

**Acceptance Scenarios**:

1. **Given** a workflow run where `SPECKIT_PR_TOKEN` is available, **When** the agent assignment step executes, **Then** the step logs `"Agent assignment token: SPECKIT_PR_TOKEN (primary)"` before
   making the API call.

2. **Given** a workflow run where only `COPILOT_GITHUB_TOKEN` is available, **When** the agent
   assignment step executes, **Then** the step logs
   `"Agent assignment token: COPILOT_GITHUB_TOKEN (fallback)"` before making the API call.

---

### Edge Cases

- What happens when the `agent_assignment` API returns a non-2xx status code? The step must treat any non-success response other than 404 as a failure, set `assigned` output to `'false'`, and annotate
  the workflow run with the HTTP status and response body.

- What happens when the issue number is invalid or the issue has been deleted between label application and workflow execution? The step must handle 404 responses gracefully, logging the missing issue
  and skipping further processing without marking the workflow as failed (since this is a race condition, not a configuration error).

- What happens when the token has expired or been revoked between the preflight check and the API call? The step must catch the 401 response, log an actionable error (`"Token authentication failed —
  verify token has not expired"`), and fail the step.

- What happens when `agent_assignment` field is not recognized by the API (e.g., API version change)? The step must verify the response contains evidence the assignment was processed: check that the
  response body contains a non-null `agent_assignment` field when the status is 200. If the field is null or absent despite a 200 status, emit a `::warning::` annotation indicating the assignment may
  not have taken effect and set `assigned` output to `'false'`.

- What happens when the "Update Labels" or "Post Implementation Triggered Comment" steps fail due to token issues? The "Update Labels" step already uses `try/catch` and logs errors non-fatally, while
  "Post Implementation Triggered Comment" currently does not wrap `createComment` and may fail that step if the API call errors. With the elevated token, these steps are expected to succeed, and any
  downstream failure must not mask the success/failure of the primary agent assignment step.

## Requirements

### Functional Requirements

- **FR-001**: The "Assign Copilot Coding Agent" step in `speckit-implement-trigger.yml` MUST authenticate using `secrets.SPECKIT_PR_TOKEN` as the primary token, with `secrets.COPILOT_GITHUB_TOKEN` as
  fallback, via the `github-token` input of `actions/github-script@v7`
  (pattern: `github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}`). The step MUST NOT fall back to the default `GITHUB_TOKEN` under any circumstances.

- **FR-002**: The workflow MUST include a dedicated preflight validation step (separate `- name:` block, e.g., `"Validate Agent Assignment Token"`) that runs before the agent assignment step and fails
  the job with a descriptive `::error::` annotation if neither `SPECKIT_PR_TOKEN`
  nor `COPILOT_GITHUB_TOKEN` is available as a non-empty secret. This step must be a separate workflow step so that failures are unambiguous in the GitHub Actions UI.

- **FR-003**: The agent assignment step MUST log the identity of the token being used (e.g., `"Agent assignment token: SPECKIT_PR_TOKEN (primary)"` or `"Agent assignment token: COPILOT_GITHUB_TOKEN
  (fallback)"`) without revealing any portion of the token value. This
  log line MUST appear before the API call is made.

- **FR-004**: The agent assignment step MUST treat any non-2xx HTTP response from the `PATCH /repos/{owner}/{repo}/issues/{issue_number}` API as a step failure, except for 404 (issue missing/deleted),
  which MUST be handled as a non-fatal skip with a clear log message and `assigned` output set to `'false'`. Additionally, when the response is HTTP 200 but the response body contains a null or absent
  `agent_assignment` field, the step MUST emit a `::warning::` annotation and set `assigned` output to `'false'`.

- **FR-005**: The agent assignment step MUST preserve all existing assignment parameters unchanged: `custom_agent: 'speckit.implement'`, `base_branch: 'main'`, `custom_instructions` referencing the
  discovered spec directory, and `model` from the `COPILOT_MODEL` environment variable.

- **FR-006**: The workflow's existing conditional logic (`steps.discover.outputs.found == 'true' && steps.check-pr.outputs.exists != 'true'`) MUST remain unchanged — the fix is limited to
  authentication and observability, not control flow.

- **FR-007**: The "Update Labels" step and the "Post Implementation Triggered Comment" step that follow the assignment MUST also use the same elevated token pattern
  (`github-token: ${{ secrets.SPECKIT_PR_TOKEN || secrets.COPILOT_GITHUB_TOKEN }}`) to ensure label operations and issue comments after assignment do not silently fail due to
  insufficient `GITHUB_TOKEN` permissions.

### Non-Functional Requirements

- **NFR-001**: The token preflight check MUST add no more than 2 seconds to overall workflow execution time. It is a synchronous validation of environment variable presence, not a network call.

- **NFR-002**: The fix MUST be backward-compatible with repositories that only have `COPILOT_GITHUB_TOKEN` configured (without `SPECKIT_PR_TOKEN`). The fallback chain ensures graceful degradation.

- **NFR-003**: All error messages produced by the preflight and assignment steps MUST follow GitHub Actions annotation format (`::error::message`) so they surface in the workflow run summary UI, not
  just buried in step logs.

- **NFR-004**: The change MUST be confined to `.github/workflows/speckit-implement-trigger.yml`. No other workflow files, agent definitions, or source code should be modified as part of this fix. The
  `permissions` block remains unchanged since PATs carry their own scopes independent of the workflow permissions declaration.

- **NFR-005**: Investigation, remediation, and any subagent-assisted work for this bug MUST include a rubber duck review step to validate reasoning and cross-examine the implementation plan before
  merge.

### Key Entities

- **`SPECKIT_PR_TOKEN`**: A Personal Access Token with repository write permissions and Copilot agent assignment scopes. Primary authentication token for privileged speckit pipeline operations. Passed
  via the `github-token` input of `actions/github-script@v7`.

- **`COPILOT_GITHUB_TOKEN`**: A fallback PAT with similar scopes to `SPECKIT_PR_TOKEN`. Used when the primary token is not configured. Originally provisioned for Copilot SDK authentication. Also
  passed via `github-token` input when used.

- **`agent_assignment` payload**: The API field on the GitHub Issues PATCH endpoint that triggers Copilot coding agent assignment. Requires elevated token permissions beyond what `GITHUB_TOKEN`
  provides. The response body must contain a non-null `agent_assignment` field to confirm successful processing.

- **`github-token` input**: The authentication input of `actions/github-script@v7` that replaces the default `GITHUB_TOKEN` for the octokit instance. This is the mechanism by which the elevated PAT is
  injected into the step.

## Success Criteria

### Measurable Outcomes

- **SC-001**: After the fix is deployed, 100% of phase 5 spec PR merges that trigger `speckit-implement-trigger.yml` result in successful Copilot coding agent assignment (measured over the next 10
  consecutive pipeline runs with valid configuration).

- **SC-002**: When neither `SPECKIT_PR_TOKEN` nor `COPILOT_GITHUB_TOKEN` is configured, the workflow fails within 5 seconds of reaching the preflight step, with a `::error::` annotation visible in the
  GitHub Actions run summary.

- **SC-003**: The workflow run logs for the agent assignment step contain exactly one token-identity log line (either `"Agent assignment token: SPECKIT_PR_TOKEN (primary)"` or `"Agent assignment
  token: COPILOT_GITHUB_TOKEN (fallback)"`) in 100% of
  runs where the step executes.

- **SC-004**: Zero silent failures of agent assignment observed over a 14-day monitoring window post-deployment. A silent failure is defined as: the assignment step reports success but the issue does
  not show an active Copilot agent session.

- **SC-005**: The total execution time of the implementation trigger workflow increases by no more than 3 seconds compared to the pre-fix baseline (accounting for the preflight check and additional
  logging).

---
*Generated by Copilot SDK (claude-opus-4.6)*
