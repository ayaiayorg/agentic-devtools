# Feature Specification: Workflow Approval Required Blocks Autonomous AI PR Loop

**Feature Branch**: `speckit/1393/phase-2-clarify`
**Created**: 2026-05-11
**Status**: Draft
**Source Issue**: #1393 (<https://github.com/ayaiayorg/agentic-devtools/issues/1393>)

---

## Overview

The autonomous AI PR loop (review → address → merge) is blocked by GitHub's required manual
approval of workflow runs initiated by bot or first-time contributor accounts. When a PR is
created or updated by a bot author, workflows like **Copilot Review Gate** and **AI PR Loop /
Agentic Repair** require explicit "Approve workflows to run" from a maintainer before executing.
This specification defines approaches to eliminate that manual intervention for trusted automation.

---

## Problem Statement

GitHub enforces a security policy requiring manual workflow approval for runs triggered by
first-time contributors or bot accounts. In the context of the autonomous AI PR loop, this
creates two problems:

1. **Latency**: PRs sit idle until a maintainer notices and approves the pending workflows,
   often for hours or overnight.
2. **Toil**: The approval is purely mechanical for trusted bot accounts — a human is performing
   a gate-keeping action that could be automated safely.

The desired end state is zero manual intervention for workflow approval on PRs authored by
trusted AI/bot accounts, while preserving security for untrusted contributors.

The bot accounts and actors involved in this repository's PR loop are:

**PR authors** (in-scope for auto-approval filtering per FR-007):

- `copilot-swe-agent[bot]` — the primary bot authoring PRs via the SpecKit implementation pipeline
- `github-actions[bot]` — used for automated commits (e.g., lint fixes, release tagging)

**Review/trigger actors** (not subject to auto-approval — they trigger downstream workflows):

- `Copilot` and `copilot-pull-request-reviewer[bot]` — used for code review events that trigger the privileged `ai-pr-loop.yml` workflow

The two affected workflows are:

- `ai-pr-loop-lint.yml` — triggers on `pull_request` events (`synchronize`, `opened`, `reopened`) with read-only permissions; this is the entry point that gets blocked
- `ai-pr-loop.yml` — triggers on `workflow_run` completion of the lint workflow and on `pull_request_review`; this is the downstream privileged workflow that cannot proceed when the lint workflow is
  stuck

---

## User Scenarios & Testing

### User Story 1 — Unblock Lint Workflow for Bots (Priority: P1)

As a repository maintainer relying on the autonomous PR loop, I want the lint workflow
(`ai-pr-loop-lint.yml`) to execute automatically for PRs authored by trusted bot accounts,
so that the AI PR Loop can detect and fix lint issues without manual workflow approval.

**Why this priority**: The lint workflow is the entry point for the entire automation chain.
If it cannot run, no downstream automation (review gate, agentic repair, merge) can proceed.

**Acceptance Scenarios**:

1. Given a PR created by a trusted bot account (specifically `copilot-swe-agent[bot]` or `github-actions[bot]`), when the lint workflow is triggered, then it
   executes without requiring manual approval.
2. Given a PR created by an untrusted external contributor, when the lint workflow is triggered,
   then the existing manual approval requirement remains unchanged.

### User Story 2 — Programmatic Approval API Fallback + Observability (Priority: P2)

As a repository maintainer, I want a programmatic fallback that can approve pending workflow
runs via the GitHub API when the primary solution (collaborator status) is insufficient, so
that the automation loop is never permanently blocked by a missing approval.

**Why this priority**: Even with collaborator-based solutions, edge cases may arise (new bot
accounts, org policy changes) where programmatic approval is needed as a safety net.

**Acceptance Scenarios**:

1. Given a pending workflow run for a trusted bot PR, when the programmatic approval mechanism
   is triggered, then the workflow run is approved via the GitHub REST API within 60 seconds.
2. Given an approval action (manual or programmatic), when it occurs, then an audit log entry
   is created with the actor, timestamp, PR number, and workflow run ID.
3. Given the approval mechanism fails after exhausting the retry limit (NFR-006), when the
   failure is detected, then a PR comment is posted (detailing the failure reason and a link to
   the stuck workflow run) and a structured log entry is emitted for investigation. No external
   alerting channel or auto-created GitHub issue is required (see Q5 clarification).

### User Story 3 — Graceful Degradation via `pull_request_review` Path (Priority: P3)

As a repository maintainer, I want the AI PR Loop to degrade gracefully when workflow approval
is unavailable, falling back to the `pull_request_review` trigger path, so that PRs can still
converge even if the lint-triggered path is blocked.

**Why this priority**: This ensures robustness — if the primary and secondary mechanisms both
fail, the system can still make progress through an alternative trigger.

**Acceptance Scenarios**:

1. Given the lint workflow is stuck awaiting approval for more than the configurable threshold
   (default: 2 minutes, see FR-004), when the AI PR Loop detects this condition, then it
   attempts to proceed via the `pull_request_review` event path.
2. Given the fallback path is used, when the PR eventually converges, then the automation
   logs clearly indicate which path was taken and why.

### User Story 4 — Dispatch Pre-Check Guards Against Stuck Runs (Priority: P1)

As a repository maintainer, I want the AI PR Loop's dispatch-decision step to verify
that the triggering lint workflow run completed successfully before proceeding to patch
application or agentic repair, so that the loop does not waste resources dispatching
repair for a run that never actually ran.

**Why this priority**: Without this guard, the AI PR Loop may dispatch agentic repair
based on a lint run stuck in `action_required` state, leading to wasted CI cycles and
confusing repair attempts against incomplete lint results.

**Acceptance Scenarios**:

1. Given a lint workflow run that is still in `action_required` state (awaiting approval),
   when the AI PR Loop's dispatch-decision step evaluates it, then the loop does NOT
   proceed to patch application or agentic repair dispatch, and logs the skip reason.
2. Given a lint workflow run that completed successfully (status `completed`, conclusion
   `success` or `failure`), when the AI PR Loop's dispatch-decision step evaluates it,
   then the loop proceeds normally to patch application or repair dispatch based on the
   lint results.

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Add trusted bot account as repository collaborator with write access to eliminate first-time-contributor workflow approval gates. The initial trusted bot accounts are: `copilot-swe-agent[bot]` and `github-actions[bot]`. If the GitHub App identity (`copilot-swe-agent[bot]`) cannot be added as a traditional collaborator, use a machine user PAT account as the collaborator and configure the bot to authenticate via that account's token for PR creation. **Credential note:** In this fallback scenario, the machine user's PAT replaces (not supplements) the existing `COPILOT_GITHUB_TOKEN` — the secret slot is reused with the machine user's token, so no additional secret is introduced. This is consistent with NFR-003's scope, which applies to the programmatic approval path (FR-003); the collaborator approach reuses the same single-secret architecture. | P1 |
| FR-002 | Configure repository settings to allow workflows to run for collaborator PRs without manual approval. Specifically, set the "Fork pull request workflows from outside collaborators" policy to "Require approval for first-time contributors" (not "Require approval for all outside collaborators") so that recognized collaborators bypass the gate. | P1 |
| FR-003 | Implement programmatic workflow approval via GitHub REST API (`POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve`) as fallback. **Scope clarification:** Although GitHub's documentation primarily describes this endpoint in the context of fork pull-request workflows, the API applies to *any* workflow run in `action_required` state — including runs triggered by first-time contributors or bot accounts on same-repo PRs when the repository/org policy requires workflow approval. Fork PRs remain out of scope per NFR-004; the approval monitor (FR-004) filters to same-repo trusted-bot PRs only, so this endpoint is never called for fork PR runs. This API call must be authenticated with a token that has `actions:write` scope. The existing `COPILOT_GITHUB_TOKEN` secret requires `actions:write` — if the token's current scopes do not include this permission, it must be updated as part of this implementation. No additional secrets or credentials are needed beyond the existing `COPILOT_GITHUB_TOKEN`. | P2 |
| FR-004 | Create a monitoring mechanism that detects workflow runs stuck in "awaiting approval" state for more than a configurable threshold (default: 2 minutes). The mechanism should poll via `GET /repos/{owner}/{repo}/actions/runs?status=action_required` filtered to runs associated with PRs authored by trusted bot accounts. | P2 |
| FR-005 | Emit structured log entries for all approval actions (manual and programmatic) including actor, timestamp, PR number, run ID, and approval source. Log entries should use JSON format (see example below this table). | P2 |
| FR-006 | Implement `pull_request_review` trigger path as graceful degradation when lint workflow is blocked. This leverages the existing `pull_request_review` trigger in `ai-pr-loop.yml` (lines 30-31) — the degradation mechanism posts a synthetic review event to activate the privileged workflow via the review path instead of the `workflow_run` path. | P3 |
| FR-007 | Add a configurable allow-list of trusted bot account names/IDs eligible for auto-approval. The allow-list should be stored in a repository-level configuration file (`.github/ai-pr-loop-config.json`) with schema: `{"trusted_bot_accounts": ["copilot-swe-agent[bot]", "github-actions[bot]"]}`. Initial entries: `copilot-swe-agent[bot]`, `github-actions[bot]`. | P2 |
| FR-008 | Ensure the approval mechanism is idempotent — re-approving an already-approved run must be a no-op. The implementation should check run status before calling the approve API; if status is not `action_required`, skip the call and log the skip reason. | P2 |
| FR-009 | Integrate approval status checks into the AI PR Loop's decision logic before dispatching agentic repair. Specifically, in the `ai-pr-loop.yml` workflow's dispatch-decision step, add a pre-check that verifies the triggering lint workflow run completed successfully (not stuck in `action_required`) before proceeding to patch application or repair dispatch. | P1 |

**FR-005 log entry format example:**

```json
{
  "event": "workflow_approval",
  "actor": "workflow-approval-monitor",
  "timestamp": "2026-05-11T14:30:00Z",
  "pr_number": 1234,
  "run_id": 56789,
  "source": "manual | programmatic",
  "result": "success | failure"
}
```

---

### Non-Functional Requirements

| ID | Requirement | Category |
|----|-------------|----------|
| NFR-001 | Approval actions must complete within 60 seconds of detection. Measured from the timestamp the monitoring mechanism first observes the `action_required` status to the timestamp the approve API call returns a 2xx response. | Performance |
| NFR-002 | The solution must respect GitHub's existing trust boundary architecture (privileged vs unprivileged workflows). Specifically, the unprivileged `ai-pr-loop-lint.yml` workflow must remain read-only (`contents: read`, `actions: read`) — no secrets or write permissions may be added to it. The programmatic approval must be performed from a separate privileged context (e.g., a scheduled workflow or the existing `ai-pr-loop.yml`). | Security |
| NFR-003 | No credentials beyond the existing `COPILOT_GITHUB_TOKEN` secret should be required for the programmatic path. The minimum required permissions per action are: `actions:write` (workflow run approval — FR-003), `actions:read` (list runs in `action_required` state — FR-004), `contents:write` (push commits for lint auto-fix), `pull-requests:write` (PR comments, approval, merge), `issues:write` (PR comment posting via Issues API), `checks:read` (read check-suite status for dispatch pre-check — FR-009). The approval monitor workflow itself requires only `actions:read` + `actions:write`; the broader scopes (`contents:write`, `pull-requests:write`, `issues:write`) are needed by other components of the AI PR Loop that share the same token. If the token does not currently include `actions:write`, its permissions must be expanded as part of implementing FR-003 — no new secrets need to be created. | Security |
| NFR-004 | The solution must not weaken security for PRs from untrusted external contributors or forks. Fork PRs are already blocked in both workflows (line 44 of `ai-pr-loop-lint.yml`, line 144 of `ai-pr-loop.yml`) — this behavior must be preserved. The allow-list (FR-007) must never include wildcard entries or patterns that could match untrusted accounts. | Security |
| NFR-005 | All approval events must be auditable via GitHub audit log or custom structured logging. GitHub's native audit log captures manual approvals; programmatic approvals via the REST API are also recorded in the audit log. Custom structured logging (FR-005) provides a secondary audit trail in workflow run logs. | Compliance |
| NFR-006 | The fallback mechanism must not create infinite retry loops — a maximum of 3 attempts per PR per SHA. After 3 failed approval attempts for the same `(pr_number, head_sha)` tuple, the mechanism must stop retrying and post a comment on the PR indicating manual intervention is required. | Reliability |

---

## Clarifications

### Session 2026-05-11

- **Q1**: Does the organization have policies that override repository-level collaborator settings for workflow approval? If so, the collaborator approach (FR-001) may be insufficient and the
  programmatic API fallback (FR-003) becomes the primary path. → **A**: Based on codebase analysis, the repository uses a split-token model: the main `ai-pr-loop` job uses the default
  `GITHUB_TOKEN` (scoped via workflow-level `permissions:`), while the `agentic-repair` job uses `COPILOT_GITHUB_TOKEN` (a PAT secret) for `gh` CLI operations and git push. The
  `COPILOT_GITHUB_TOKEN` PAT's permissions may need to be expanded to include `actions:write` for programmatic approval (see FR-003). The safest approach is to implement
  FR-001 (collaborator) as the primary path and FR-003 (programmatic approval) as a guaranteed fallback. If org-level policies block the
  collaborator approach at runtime, the monitoring mechanism (FR-004) will detect the stuck run and the programmatic fallback will activate automatically. No changes to the requirement priorities are
  needed — the dual-path design already accounts for this.

- **Q2**: Should the solution handle fork PRs differently? GitHub's approval requirement for fork PRs is stricter and may not be bypassable via collaborator status alone. → **A**: Fork PRs are
  explicitly out of scope. Both workflows already block fork PRs: `ai-pr-loop-lint.yml` checks `pr.head.repo.full_name !== pr.base.repo.full_name` (line 44) and `ai-pr-loop.yml` does the same
  (line 144). The allow-list (FR-007) applies only to same-repo PRs. Fork PR handling remains unchanged — they continue to require manual approval per GitHub's default security policy.

- **Q3**: Can the bot account (e.g., `copilot-swe-agent[bot]` or the GitHub App identity) be added as a repository collaborator, or does the org restrict collaborator additions to human accounts? →
  **A**: GitHub App bot accounts (like `copilot-swe-agent[bot]`) cannot be directly added as repository collaborators — they authenticate via installation tokens, not user accounts. The recommended
  approach is: (1) attempt to configure the repository's "Actions permissions" setting to allow first-time contributors with approval only for outside collaborators, which may be sufficient since
  GitHub App installations on the same org are not treated as "outside collaborators"; (2) if that is insufficient, create a dedicated machine user account (e.g., `agentic-devtools-bot`) that is
  added as a collaborator, and use its PAT for PR creation instead of the App installation token; (3) the programmatic approval fallback (FR-003) serves as the final safety net regardless of which
  primary path succeeds.

- **Q4**: Where should the programmatic approval mechanism run — as a new scheduled workflow, within the existing `ai-pr-loop.yml`, or as a separate workflow triggered by `workflow_run`? → **A**: The
  programmatic approval should be implemented as a new lightweight scheduled workflow (e.g., `workflow-approval-monitor.yml`) that runs every 2 minutes. This keeps the concern separated from the
  existing `ai-pr-loop.yml` (which already has complex logic). The new workflow should: (1) list runs in `action_required` state, (2) filter to runs associated with trusted bot PRs, (3) approve
  eligible runs via the REST API. This avoids circular dependencies — `ai-pr-loop.yml` cannot approve its own triggering lint run because it only fires after the lint run completes.

- **Q5**: What happens when the maximum retry count (NFR-006, 3 attempts) is exhausted — should the system notify maintainers via a PR comment, a GitHub issue, or an external alerting channel? →
  **A**: The system should post a PR comment as the primary notification mechanism. The comment should include: (1) a clear message that automated workflow approval failed after 3 attempts, (2) the
  specific error or reason for failure, (3) a link to the stuck workflow run, (4) instructions for manual resolution. No external alerting channel is needed at this stage — PR comments are sufficient
  for the team's current workflow. A GitHub issue should NOT be auto-created to avoid issue noise.

---

## Success Criteria

| # | Criterion | Measurement |
|---|-----------|-------------|
| SC-1 | Zero manual workflow approval clicks required across 20 consecutive PR cycles authored by trusted bots | Count of manual approvals in GitHub audit log = 0 |
| SC-2 | 0% false-positive auto-approval rate (no untrusted PRs are auto-approved) | Review all auto-approval events; none should be for non-allow-listed accounts |
| SC-3 | End-to-end PR cycle time (open → merge) reduced by at least 30% compared to current baseline with manual approval | Measure median cycle time before/after across 20 PRs |
| SC-4 | Programmatic approval fallback success rate ≥ 95% when triggered | Count successful API approvals / total attempts |
| SC-5 | All approval actions have corresponding audit entries with required metadata | Verify completeness of audit log entries for sampled PRs |

---

## Relevant Code References

### Core Workflow Files

- [`.github/workflows/ai-pr-loop.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/ai-pr-loop.yml) — Privileged AI PR Loop workflow (triggers on `workflow_run` and
  `pull_request_review`); the main `ai-pr-loop` job uses the default `GITHUB_TOKEN` (scoped via workflow-level `permissions:`);
  the `agentic-repair` job uses `COPILOT_GITHUB_TOKEN` (a PAT secret) for `gh` CLI operations and git push;
  blocks fork PRs at line 144; approves/merges PRs at lines 918-1016
- [`.github/workflows/ai-pr-loop-lint.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/ai-pr-loop-lint.yml) — Unprivileged lint workflow (triggers on `pull_request`
  events); read-only permissions (`contents: read`, `actions: read`); blocks fork PRs at line 44; this is the workflow that gets stuck awaiting approval
- [`.github/workflows/README.md`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/README.md) — Documents the two-workflow trust-boundary split architecture
- [`.github/workflows/synthetic-copilot-review.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/synthetic-copilot-review.yml) — Scheduled synthetic review fallback (runs
  every 30 minutes); relevant as an existing pattern for the `pull_request_review` degradation path (FR-006)
- [`.github/workflows/speckit-implement-trigger.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/speckit-implement-trigger.yml) — References `copilot-swe-agent[bot]` as
  a known bot author for PR detection

### Related Specifications

- [`specs/1359-loop-automated-agentic-handling/spec.md`][spec-1359] — Automated agentic repair specification (downstream consumer)

[spec-1359]: https://github.com/ayaiayorg/agentic-devtools/blob/main/specs/1359-loop-automated-agentic-handling/spec.md

---

*Generated by SpecKit Pipeline (Phase 2/clarify) — expanded from issue #1393*

---
*Generated by Copilot SDK (claude-opus-4.6)*
