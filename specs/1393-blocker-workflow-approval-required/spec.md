# Feature Specification: Workflow Approval Required Blocks Autonomous AI PR Loop

**Feature Branch**: `speckit/1393/phase-1-specify`
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

---

## User Scenarios & Testing

### User Story 1 — Unblock Lint Workflow for Bots (Priority: P1)

As a repository maintainer relying on the autonomous PR loop, I want the lint workflow
(`ai-pr-loop-lint.yml`) to execute automatically for PRs authored by trusted bot accounts,
so that the AI PR Loop can detect and fix lint issues without manual workflow approval.

**Why this priority**: The lint workflow is the entry point for the entire automation chain.
If it cannot run, no downstream automation (review gate, agentic repair, merge) can proceed.

**Acceptance Scenarios**:

1. Given a PR created by a trusted bot account, when the lint workflow is triggered, then it
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
3. Given the approval mechanism fails, when the failure is detected, then an alert is raised
   and the failure is logged for investigation.

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

---

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Add trusted bot account as repository collaborator with write access to eliminate first-time-contributor workflow approval gates | P1 |
| FR-002 | Configure repository settings to allow workflows to run for collaborator PRs without manual approval | P1 |
| FR-003 | Implement programmatic workflow approval via GitHub REST API (`POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve`) as fallback | P2 |
| FR-004 | Create a monitoring mechanism that detects workflow runs stuck in "awaiting approval" state for more than a configurable threshold (default: 2 minutes) | P2 |
| FR-005 | Emit structured log entries for all approval actions (manual and programmatic) including actor, timestamp, PR number, run ID, and approval source | P2 |
| FR-006 | Implement `pull_request_review` trigger path as graceful degradation when lint workflow is blocked | P3 |
| FR-007 | Add a configurable allow-list of trusted bot account names/IDs eligible for auto-approval | P2 |
| FR-008 | Ensure the approval mechanism is idempotent — re-approving an already-approved run must be a no-op | P2 |
| FR-009 | Integrate approval status checks into the AI PR Loop's decision logic before dispatching agentic repair | P1 |

---

### Non-Functional Requirements

| ID | Requirement | Category |
|----|-------------|----------|
| NFR-001 | Approval actions must complete within 60 seconds of detection | Performance |
| NFR-002 | The solution must respect GitHub's existing trust boundary architecture (privileged vs unprivileged workflows) | Security |
| NFR-003 | No credentials beyond the existing `COPILOT_GITHUB_TOKEN` secret should be required for the programmatic path | Security |
| NFR-004 | The solution must not weaken security for PRs from untrusted external contributors or forks | Security |
| NFR-005 | All approval events must be auditable via GitHub audit log or custom structured logging | Compliance |
| NFR-006 | The fallback mechanism must not create infinite retry loops — a maximum of 3 attempts per PR per SHA | Reliability |

---

## Clarifications

1. [NEEDS CLARIFICATION] **Org-level permissions**: Does the organization have policies that
   override repository-level collaborator settings for workflow approval? If so, the collaborator
   approach (FR-001) may be insufficient and the programmatic API fallback (FR-003) becomes the
   primary path.

2. [NEEDS CLARIFICATION] **Fork PR policy**: Should the solution handle fork PRs differently?
   GitHub's approval requirement for fork PRs is stricter and may not be bypassable via
   collaborator status alone.

3. [NEEDS CLARIFICATION] **Bot as collaborator feasibility**: Can the bot account (e.g.,
   `copilot[bot]` or the GitHub App identity) be added as a repository collaborator, or does
   the org restrict collaborator additions to human accounts?

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

- [`.github/workflows/ai-pr-loop.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/ai-pr-loop.yml) — Privileged AI PR Loop workflow (triggers on `workflow_run` and `pull_request_review`)
- [`.github/workflows/ai-pr-loop-lint.yml`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/ai-pr-loop-lint.yml) — Unprivileged lint workflow (triggers on `pull_request` events)
- [`.github/workflows/README.md`](https://github.com/ayaiayorg/agentic-devtools/blob/main/.github/workflows/README.md) — Documents the two-workflow trust-boundary split architecture

### Related Specifications

- [`specs/1359-loop-automated-agentic-handling/spec.md`][spec-1359] — Automated agentic repair specification (downstream consumer)

[spec-1359]: https://github.com/ayaiayorg/agentic-devtools/blob/main/specs/1359-loop-automated-agentic-handling/spec.md

---

*Generated by SpecKit Pipeline (Phase 1/specify) — expanded from issue #1393*
