# Feature Specification: SpecKit Label Operations Token Fix

**Feature Branch**: `speckit/1364/phase-2-clarify`  
**Created**: 2026-05-07  
**Status**: Draft  
**Input**: GitHub Issue #1364 — label operations fail silently in create-spec-pr.sh due to token permission mismatch  
**Source Issue**: #1364 (<https://github.com/ayaiayorg/agentic-devtools/issues/1364>)

## Clarifications

### Session 2026-05-08

- Q: Should the `LABEL_TOKEN` environment variable be introduced as a new name in the workflow YAML `env:` block, or should the script simply accept a second token parameter alongside `GH_TOKEN`?
  The spec says "expose as a distinct environment variable" but doesn't clarify whether this is a new workflow-level env var or a script-level convention. → A: `LABEL_TOKEN` is a workflow-level `env:`
  variable set on the "Create Pull Request" step in both `speckit-issue-trigger.yml` and `speckit-phase-progression.yml`, mapped to `${{ secrets.GITHUB_TOKEN }}`. The script reads it from the
  environment; no new CLI parameter is added.
- Q: FR-007 requires batch label application via `gh pr edit --add-label`, but User Story 1 Scenario 3 requires auto-creating missing labels first (`gh label create --force`). Since `gh label create`
  is per-label, should label creation remain per-label while only the final `gh pr edit --add-label` call is batched? → A: Yes. Label creation (`gh label create --force`) remains per-label in a loop
  (it has no batch API). Only the application step (`gh pr edit --add-label`) is batched into a single comma-separated call. FR-008 already specifies this sequence: ensure all labels exist first, then
  batch-apply.
- Q: FR-009 specifies a "best-effort preflight check" of token permissions, but does not specify the API call to use. What endpoint should the preflight check call to validate `issues: write` scope? →
  A: The preflight check calls `gh label list --limit 1` using the effective token (i.e., `LABEL_TOKEN` if set, otherwise `GH_TOKEN` after the FR-010 fallback has been applied). This requires label
  read access. If the call succeeds, the token is valid for at least label read. If it fails with 401/403, the script logs a diagnostic and exits. If the preflight fails due to a transient or
  network error (timeout, DNS failure, HTTP 5xx), the script logs a warning and proceeds with label operations (matching FR-009(b) — avoids blocking on intermittent infrastructure issues). An unset
  `LABEL_TOKEN` does not cause a preflight failure — the fallback token is used instead. This is best-effort — it cannot distinguish `issues: read` from `issues: write` without attempting a write,
  so the primary protection remains the error logging in FR-003/FR-004.
- Q: The retry specification (FR-005) says "minimum 2 retries" and NFR-003 says "2s, 4s" backoff. Should the retry apply to both `gh label create` and `gh pr edit --add-label`, or only to the batch
  `gh pr edit` call? → A: Retry applies to both `gh label create` (per-label) and `gh pr edit --add-label` (batch). Any label API call that returns a transient HTTP error (429, 500, 502, 503, 504) is
  retried. Both operations use the same retry logic.
- Q: What should happen when batch `gh pr edit --add-label` fails for the entire batch (e.g., one invalid label causes the whole call to fail)? FR-007 says batch, but User Story 4 Scenario 2 says
  "fall back to applying remaining valid labels individually." How is the invalid label identified from the batch error? → A: If the batch `gh pr edit --add-label` call fails, the script falls back to
  applying each label individually via separate `gh pr edit --add-label` calls. The invalid label is identified by which individual call fails. The batch error message from `gh` does not reliably
  identify which specific label caused the failure, so individual fallback is the only reliable approach.

## Problem Statement

All label operations in the SpecKit pipeline fail silently during PR creation across all phases (1–5).
The root cause is a token permission mismatch: the script uses `GH_TOKEN`
(set to `SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN` — a PAT/App token configured for PR creation)
for label operations that require `issues: write` scope.
The `GITHUB_TOKEN` with proper permissions (declared at job level as `permissions: issues: write` in both workflow files)
is never passed to the script.
Additionally, all errors are suppressed via `2>/dev/null`, making failures invisible to operators.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Labels Applied Successfully to SpecKit PRs (Priority: P1)

**Covers**: FR-001, FR-002, FR-007, FR-008, FR-011

As a developer triggering a SpecKit workflow, I want labels from my source issue and the phase-specific label to be automatically applied to the created PR, so that PRs are correctly categorized and
discoverable through label filters.

**Why this priority**: This is the core defect. Without functioning labels, SpecKit PRs cannot be filtered, tracked, or routed through automated label-based workflows (e.g., board columns,
notification rules). Every SpecKit PR is affected.

**Independent Test**: Trigger a SpecKit issue workflow (any phase) and verify the resulting PR has the expected labels: source issue labels (e.g., `enhancement`) plus the phase label (e.g.,
`speckit:phase-4`).

**Acceptance Scenarios**:

1. **Given** a SpecKit issue with labels `["enhancement", "speckit:processing"]` triggers phase 4, **When** the `create-spec-pr.sh` script creates the PR, **Then** the PR has labels `enhancement`,
   `speckit:processing`, and `speckit:phase-4`.
2. **Given** a SpecKit issue triggers the issue-trigger workflow (no phase number), **When** the script creates the PR, **Then** the PR has the `speckit:spec` label plus all source issue labels.
3. **Given** a label does not yet exist in the repository, **When** the script attempts to apply it, **Then** the label is created (via `gh label create --force` using the effective token — i.e.,
   `LABEL_TOKEN` if set, otherwise `GH_TOKEN` per FR-010) with appropriate defaults and applied to the PR.
4. **Given** a label already exists in the repository, **When** the script attempts to apply it, **Then** the existing label is reused (not duplicated) and applied to the PR.

---

### User Story 2 - Actionable Error Diagnostics for Label Failures (Priority: P1)

**Covers**: FR-003, FR-004

As a workflow operator, I want label failures to produce clear, actionable error messages in the workflow logs, so that I can diagnose and resolve token permission issues without guessing.

**Why this priority**: Silent failures waste significant debugging time. The current `2>/dev/null` suppression means operators only discover the problem by manually checking PR labels after the
workflow completes. This is equally critical as the fix itself because without diagnostics, future regressions go undetected.

**Independent Test**: Deliberately misconfigure the label token by setting `permissions: issues: read` (instead of `issues: write`) in the workflow YAML
and verify the workflow log contains a specific error message identifying the permission failure.

**Acceptance Scenarios**:

1. **Given** the label token lacks `issues: write` permission, **When** the script attempts label operations, **Then** the error output includes the HTTP status code and a message indicating a
   permission issue.
2. **Given** the label token is valid, **When** a label operation fails for any other reason (e.g., invalid label name), **Then** the error output includes the specific API error message.
3. **Given** a preflight token validation is performed, **When** the token lacks required permissions, **Then** the script exits early with a clear diagnostic message before attempting any label
   operations.

---

### User Story 3 - Resilient Label Application with Retry (Priority: P2)

**Covers**: FR-005, FR-006

As a workflow operator, I want transient API failures (rate limits, 502 errors) to be automatically retried, so that intermittent infrastructure issues do not permanently prevent label application.

**Why this priority**: Transient failures are a common reality with GitHub's API. While less critical than the token fix itself, retry logic prevents label loss due to temporary conditions that
resolve within seconds.

**Independent Test**: Simulate a transient failure (e.g., mock a 502 response on first attempt) and verify the retry mechanism succeeds on subsequent attempt.

**Acceptance Scenarios**:

1. **Given** a label API call returns a 502 error, **When** the retry mechanism activates, **Then** the call is retried up to 2 additional times with exponential backoff (minimum 2 seconds between
   attempts).
2. **Given** a label API call returns a 403 (permission denied), **When** the retry mechanism evaluates the error, **Then** no retry is attempted (non-transient errors are not retried).
3. **Given** all retry attempts are exhausted, **When** the final attempt fails, **Then** the failure is logged with all attempt details and the script continues with remaining labels.

---

### User Story 4 - Batch Label Application (Priority: P2)

**Covers**: FR-007, FR-008

As a workflow operator, I want labels to be applied in a single API call where possible, so that label operations are faster, more atomic, and less prone to partial-failure states.

**Why this priority**: Batching reduces API calls, minimizes the window for partial failures, and is a straightforward optimization. It complements the retry logic by reducing the number of operations
that could fail.

**Independent Test**: Trigger a workflow with 3+ labels on the source issue and verify all labels are applied in a single `gh pr edit --add-label` call (observable via reduced API call count in logs).

**Acceptance Scenarios**:

1. **Given** a PR needs labels `["enhancement", "speckit:processing", "speckit:phase-4"]`, **When** labels are applied, **Then** a single
   `gh pr edit --add-label "enhancement,speckit:processing,speckit:phase-4"` call is made.
2. **Given** one label in the batch does not exist and cannot be created, **When** batch application fails, **Then** the script falls back to applying each label individually via separate `gh pr edit
   --add-label` calls, logging which specific label(s) failed.
3. **Given** the batch label string exceeds any API limits, **When** the script builds the label list, **Then** it gracefully splits into multiple batch calls.

---

### User Story 5 - Early Token Permission Validation (Priority: P3)

**Covers**: FR-009, FR-010

As a workflow operator, I want the script to validate token permissions before attempting any label operations, so that permission issues are caught immediately with a clear message rather than
discovered through multiple individual failures.

**Why this priority**: This is a defense-in-depth measure. The primary fix (correct token) eliminates the immediate problem, and error logging (P1) catches future issues. Preflight validation adds
early detection but is less critical than the operational fixes.

**Independent Test**: Run the script in a workflow configured with **no** `issues` permission (i.e., the token cannot access the Issues/Labels API at all) and verify the preflight check
(`gh label list --limit 1`) detects the failure and logs a clear error before any label operations are attempted. Note: the preflight **cannot** distinguish `issues: read` from `issues: write`
because `gh label list` is a read operation; insufficient write permission is caught during actual label create/apply operations via FR-004 error logging.

**Acceptance Scenarios**:

1. **Given** the label token has valid permissions, **When** the preflight check runs (via `gh label list --limit 1` using the effective token per FR-009/FR-010), **Then** it passes silently
   and label operations proceed.
2. **Given** the label token lacks any label API access (e.g., no `issues` permission), **When** the preflight check runs, **Then** the script logs a clear error and exits with a non-zero code.
   Note: if the token has `issues: read` but not `issues: write`, the preflight will pass; the missing write permission is caught during actual label create/apply operations via FR-003/FR-004 logging.
3. **Given** the preflight API call itself fails (network error), **When** evaluated, **Then** the script logs a warning but continues (to avoid blocking on transient preflight failures).

---

### Edge Cases

- What happens when `LABELS_JSON` contains duplicate labels? → Deduplication before application (via `jq -r '.[]' | sort -u`).
- What happens when a label name contains special characters (colons, spaces, unicode)? → Proper quoting and URL-encoding must be preserved. The `gh` CLI handles encoding internally; the script must
  ensure labels are properly quoted in shell arguments.
- What happens when `LABEL_TOKEN` environment variable is empty or unset? → Fall back to `GH_TOKEN` with a logged warning (FR-010). The preflight check (FR-009)
  then runs using the effective token (`GH_TOKEN` in this case), so an unset `LABEL_TOKEN` does **not** cause the preflight to exit — the fallback is resolved first. Warning text:
  `"Warning: LABEL_TOKEN not set, falling back to GH_TOKEN — label operations may fail if this token lacks issues: write permission."`
- What happens when the repository has reached its label limit? → Log the API error and continue with remaining operations.
- What happens when `gh pr edit` succeeds for some labels but the PR was deleted between calls? → Log the error and exit gracefully.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST use the **effective label token** (`LABEL_TOKEN` if set, otherwise `GH_TOKEN` after the FR-010 fallback) for all label-related API calls (`gh label create`,
  `gh pr edit --add-label`). Permission enforcement is handled by FR-009 (preflight detection of missing access) and FR-003/FR-004 (error logging when write operations fail).
  Non-label operations (e.g., `gh pr create`) MUST remain unaffected and continue using `GH_TOKEN` directly.
- **FR-002**: The system MUST expose the label token as a distinct environment variable (`LABEL_TOKEN`) in both `speckit-issue-trigger.yml` and `speckit-phase-progression.yml` workflow files, mapped
  to `${{ secrets.GITHUB_TOKEN }}` in the "Create Pull Request" step's `env:` block.
- **FR-003**: The system MUST NOT suppress stderr output from label API calls via `2>/dev/null`. All existing `2>/dev/null` redirections on `gh label create` and `gh pr edit --add-label` calls must be
  removed.
- **FR-004**: The system MUST log the specific API error message when any label operation fails. Error output must include the operation attempted, the HTTP status code (when available), and a
  suggested remediation action per NFR-002.
- **FR-005**: The system MUST retry transient failures (HTTP 429, 500, 502, 503, 504) with exponential backoff, minimum 2 retries. Retry applies to both `gh label create` (per-label) and `gh pr edit
  --add-label` (batch) calls.
- **FR-006**: The system MUST NOT retry non-transient failures (HTTP 401, 403, 404, 422).
- **FR-007**: The system MUST batch label application into a single `gh pr edit --add-label` call, with all labels comma-separated. If the batch call fails, the system MUST fall back to individual `gh
  pr edit --add-label` calls per label.
- **FR-008**: The system MUST ensure all labels exist (via per-label `gh label create --force` calls using the effective token per FR-009/FR-010) before attempting batch application.
- **FR-009**: The system MUST attempt a best-effort preflight check of the label token's permissions before performing label operations (via `gh label list --limit 1` using the **effective
  token** — i.e., `LABEL_TOKEN` if set, otherwise `GH_TOKEN` after the FR-010 fallback has been applied). The preflight runs *after* token resolution (FR-010), so an unset `LABEL_TOKEN` does not
  cause a preflight failure; the fallback token is used instead.
  - **(a)** If the preflight check fails with an **auth/permission error** (HTTP 401 or 403), the system MUST log a clear error and **exit with a non-zero code** — this indicates the effective
    token lacks label API access entirely, and proceeding would cause every subsequent label operation to fail.
  - **(b)** If the preflight check fails with a **transient/network error** (e.g., timeout, DNS failure, HTTP 5xx), the system MUST log a warning and **proceed** with label operations to avoid
    blocking on intermittent infrastructure issues.
  - The preflight cannot distinguish `issues: read` from `issues: write` without attempting a write; primary protection for missing write permission is FR-003/FR-004 error logging.
- **FR-010**: The system MUST fall back to `GH_TOKEN` if `LABEL_TOKEN` is not set, with a logged warning indicating potential permission issues. Warning text:
  `"Warning: LABEL_TOKEN not set, falling back to GH_TOKEN — label operations may fail if this token lacks issues: write permission."`
- **FR-011**: The system MUST preserve all existing SpecKit workflow functionality (PR creation, branch management, artifact linking) unchanged. The `GH_TOKEN` used for `gh pr create` is not modified;
  only label operations use `LABEL_TOKEN`.

### Non-Functional Requirements

- **NFR-001**: Label operations MUST complete within 60 seconds total (including retries) to avoid workflow timeout pressure.
- **NFR-002**: Error messages MUST include: the operation attempted, the HTTP status code (when available), and a suggested remediation action. Common remediation examples:
  403 → "Ensure `LABEL_TOKEN` uses `GITHUB_TOKEN` with `permissions: issues: write`"; 404 → "Verify the repository and PR number are correct";
  422 → "Check that the label name is valid and not a duplicate".
- **NFR-003**: The retry backoff MUST use a minimum 2-second initial delay with exponential growth (2s, 4s) to respect GitHub API rate limits.
- **NFR-004**: The fix MUST NOT require changes to repository secret configuration (i.e., must use the already-available `GITHUB_TOKEN` which is automatically provided by GitHub Actions with the
  permissions declared at job level).
- **NFR-005**: The script MUST remain compatible with both `speckit-issue-trigger.yml` and `speckit-phase-progression.yml` without divergent logic. Both workflows call the same `create-spec-pr.sh`
  script; the fix is entirely within the script and the workflow `env:` blocks.

### Key Entities

- **Label Token (`LABEL_TOKEN`)**: A GitHub token with `issues: write` scope, sourced from the workflow's `GITHUB_TOKEN` (the automatic token provided by GitHub Actions, scoped by the job-level
  `permissions:` declaration), used exclusively for label API operations (`gh label create`, `gh pr edit --add-label`).
- **GH_TOKEN**: The existing PR creation token (`SPECKIT_PR_TOKEN || COPILOT_GITHUB_TOKEN`), unchanged in its current role for `gh pr create`.
  This token may lack `issues: write` scope, which is why label operations use `LABEL_TOKEN` instead.
- **Label Set**: The combined collection of source issue labels (from `LABELS_JSON`) plus the phase-specific SpecKit label (e.g., `speckit:phase-4` or `speckit:spec`) to be applied to the PR. Labels
  are deduplicated before application.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of SpecKit PRs created after the fix have all expected labels applied (source issue labels + phase label), verified by post-creation label check in workflow logs.
- **SC-002**: Zero silent label failures — every label operation failure produces at least one line of diagnostic output in the workflow log.
- **SC-003**: Transient failures (502, rate limit) are recovered from in ≥95% of cases within the retry window.
- **SC-004**: Total label operation time (creation + application + retries) adds ≤15 seconds to the PR creation step under normal conditions.
- **SC-005**: All existing SpecKit integration tests and workflows continue to pass without modification beyond the affected files (`create-spec-pr.sh`, `speckit-issue-trigger.yml`,
  `speckit-phase-progression.yml`).

---
*Generated by Copilot SDK (claude-opus-4.6)*
