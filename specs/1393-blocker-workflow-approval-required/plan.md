# Implementation Plan: Workflow Approval Required Blocks Autonomous AI PR Loop

**Issue**: [#1393](https://github.com/ayaiayorg/agentic-devtools/issues/1393)

---

## 1. Technical Context

- **Stack**: GitHub Actions workflows (YAML + `actions/github-script` JS), GitHub REST API
- **Key files**: `.github/workflows/ai-pr-loop.yml` (privileged), `.github/workflows/ai-pr-loop-lint.yml` (unprivileged, read-only)
- **Trust model**: Two-workflow split — lint runs unprivileged (`contents: read`, `actions: read`); the AI PR Loop runs privileged (`contents: write`, `pull-requests: write`, `actions: write`)
- **Existing patterns**: `synthetic-copilot-review.yml` (scheduled fallback), repair deduplication markers, cycle-count tracking
- **Token model**: `GITHUB_TOKEN` (workflow-scoped) for main job; `COPILOT_GITHUB_TOKEN` (PAT secret) for agentic-repair job

## 2. Research Summary

See [research.md](research.md) for detailed decisions on:

- Collaborator vs. programmatic approval as primary strategy
- Scheduled workflow vs. `workflow_run` for the approval monitor
- Config file format and location for trusted bot allow-list
- Graceful degradation via synthetic review events

**Key decisions**:

1. **Primary path**: Repository settings change (FR-001/FR-002) — zero code if org policy allows
2. **Fallback path**: New scheduled workflow `workflow-approval-monitor.yml` polling every 2 minutes
   (spec default per FR-004; see [Threshold Reconciliation](#threshold-reconciliation) for cron granularity note)
3. **Config file**: `.github/ai-pr-loop-config.json` with `trusted_bot_accounts` array
4. **Dispatch pre-check**: Inline guard in existing `dispatch-decision` step of `ai-pr-loop.yml`

## 3. Design Overview

```text
┌─────────────────────┐
│  PR created by bot  │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ ai-pr-loop-lint.yml triggered       │
│ (pull_request: opened/synchronize)  │
└─────────┬───────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ GitHub evaluates approval policy    │
│ (org + repo settings)               │
├─────────────────────────────────────┤
│ Collaborator? ──YES──► Run starts   │
│       │                             │
│      NO                             │
│       ▼                             │
│ Stuck in action_required            │
└─────────┬───────────────────────────┘
          │ (2 min threshold per FR-004)
          ▼
┌─────────────────────────────────────┐
│ workflow-approval-monitor.yml       │
│ (schedule: every 2 min)             │
│ 1. List runs, filter conclusion=    │
│    action_required client-side      │
│ 2. Filter to trusted bot PRs       │
│ 3. Approve via REST API             │
│ 4. Log structured audit entries     │
│ 5. After 3 failures per SHA: post   │
│    PR comment + stop retrying       │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ ai-pr-loop.yml (dispatch-decision)  │
│ NEW: Pre-check lint run conclusion  │
│ - Skip if conclusion=action_required│
│ - Proceed if success/failure        │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ Fallback: pull_request_review path  │
│ Post synthetic review to trigger    │
│ ai-pr-loop.yml via review trigger   │
└─────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1 — Configuration & Pre-Check Guard (P1) — FR-001, FR-002, FR-009

**Deliverables**: Repository settings documentation, dispatch pre-check guard, config file.

#### Task 1.1: Create `.github/ai-pr-loop-config.json`

- Create config file with `trusted_bot_accounts` allow-list (FR-007)
- Schema: `{"trusted_bot_accounts": ["copilot-swe-agent[bot]", "github-actions[bot]"]}`
- Document the schema in `.github/workflows/README.md`

#### Task 1.2: Document repository settings change (FR-001, FR-002)

- Add a `docs/workflow-approval-settings.md` or section in `.github/workflows/README.md`
- Document the required "Fork pull request workflows" policy setting
- Document collaborator addition steps (or machine-user PAT fallback)
- This is a manual admin action — no code change, just documentation

#### Task 1.3: Add dispatch pre-check guard in `ai-pr-loop.yml` (FR-009)

- In the `dispatch-decision` step (line ~567), add a pre-check before the existing logic
- When triggered by `workflow_run`, fetch the triggering lint run's conclusion
- If `conclusion === 'action_required'`, skip dispatch and log the reason
- If `conclusion` is `success` or `failure`, proceed normally
- Use `context.payload.workflow_run.id` and `context.payload.workflow_run.conclusion`

**Implementation detail for Task 1.3:**

```javascript
// At the top of the dispatch-decision script, after variable declarations:
if (context.eventName === 'workflow_run') {
  const triggeringRun = context.payload.workflow_run;
  if (triggeringRun.conclusion === 'action_required') {
    core.info(`Triggering lint run ${triggeringRun.id} has conclusion action_required — ` +
              `skipping dispatch (workflow approval pending).`);
    return;
  }
  if (triggeringRun.conclusion === null) {
    core.info(`Triggering lint run ${triggeringRun.id} has no conclusion — skipping dispatch.`);
    return;
  }
}
```

### Phase 2 — Approval Monitor Workflow (P2) — FR-003, FR-004, FR-005, FR-007, FR-008

**Deliverables**: New `workflow-approval-monitor.yml`, structured logging, idempotency, retry limits.

#### Task 2.1: Create `.github/workflows/workflow-approval-monitor.yml`

New scheduled workflow with the following structure:

```yaml
name: Workflow Approval Monitor

on:
  schedule:
    - cron: '*/2 * * * *'    # Every 2 minutes (FR-004 default threshold)
  workflow_dispatch: {}       # Manual trigger for testing

permissions:
  actions: write              # Fallback: approve runs via GITHUB_TOKEN if COPILOT_GITHUB_TOKEN is unavailable
  pull-requests: read         # Read PR author (GITHUB_TOKEN)
  issues: write               # Post failure comments (GITHUB_TOKEN)
  contents: read              # Read config file (GITHUB_TOKEN)
  # NOTE: The approve API call (Task 2.1 step 4) primarily uses COPILOT_GITHUB_TOKEN
  # (PAT), not the job's GITHUB_TOKEN. The `actions: write` permission above is
  # retained as a fallback path — if the PAT is unavailable or lacks scope, the
  # job can still approve runs via GITHUB_TOKEN. The remaining permissions
  # (pull-requests, issues, contents) scope GITHUB_TOKEN to the minimum needed
  # for non-approval operations. See Task 2.5 for PAT scope requirements.

concurrency:
  group: workflow-approval-monitor
  cancel-in-progress: true
```

- Single job with `actions/github-script@v7`
- Steps:
  1. Read `.github/ai-pr-loop-config.json` from repo (via `contents` API or checkout)
  2. List workflow runs and filter client-side for `conclusion === 'action_required'`
     (see [API Query Strategy](#api-query-strategy))
  3. For each stuck run, verify the run has been in `action_required` state for at least
     the configured threshold (default: 2 minutes) by comparing `run.run_started_at`
     against the current time — skip runs newer than the threshold to satisfy FR-004's
     age requirement deterministically
  4. Find associated PR and check if author is in trusted list
  5. If eligible: `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve`
  6. Emit structured JSON log entry (FR-005)
  7. Track retry count per `(pr_number, head_sha)` via PR comments with HTML markers

#### Task 2.2: Implement idempotency guard (FR-008)

- Before calling approve API, verify `run.conclusion === 'action_required'`
  (note: `run.status` will be `completed` for runs triggered via
  `workflow_run.types: [completed]`; the approval-gated state is indicated
  by the `conclusion` field)
- If already approved/completed (i.e., `conclusion` is `success` or `failure`), log skip and continue
- Check runs endpoint returns current conclusion — no race condition

#### Task 2.3: Implement retry limit with PR comment notification (NFR-006)

- Use marker comments `<!-- workflow-approval-retry:{sha}:{count} -->` on the PR
- Parse existing marker to get current count
- After 3 failed attempts for same `(pr_number, head_sha)`:
  - Post/update PR comment with failure details, stuck run link, manual instructions
  - Stop retrying for that SHA
- Comment format:

```text
<!-- workflow-approval-retry:{sha}:3 -->
## ⚠️ Workflow Approval Failed

Automated workflow approval failed after 3 attempts for SHA `{sha_short}`.

**Stuck run**: [Run #{run_id}](link)
**Reason**: {error_message}

Please approve the workflow run manually:
1. Go to the [Actions tab](link)
2. Find the pending run and click "Approve and run"
```

#### Task 2.4: Implement structured audit logging (FR-005)

- Each approval action (success or failure) emits a JSON log line via `core.info()`
- Format per FR-005 spec:

```json
{
  "event": "workflow_approval",
  "actor": "workflow-approval-monitor",
  "timestamp": "2026-05-11T14:30:00Z",
  "pr_number": 1234,
  "run_id": 56789,
  "head_sha": "abc1234def5678",
  "source": "programmatic",
  "result": "success",
  "reason": null
}
```

> **Note**: `head_sha` and `reason` are mandatory fields per the audit log schema in
> [data-model.md](data-model.md). `reason` is `null` on success and contains an
> error description on failure/skip.

#### Task 2.5: Document token permissions and least-privilege scope

- The approval monitor workflow authenticates with the `COPILOT_GITHUB_TOKEN` PAT
  (per FR-003 and NFR-003), which requires Actions write permission for the approve
  API call (fine-grained PAT: **Actions → Read and write**; classic PAT: `workflow` scope)
- If the PAT does not currently include this permission, its permissions must be expanded as part of this implementation (per FR-003)
- No additional secrets are needed beyond the existing `COPILOT_GITHUB_TOKEN` (per NFR-003)
- Document this token usage and its required scopes in `.github/workflows/README.md` to prevent future scope creep

> **Spec reconciliation note (Token Strategy):** The original plan proposed using the built-in
> `GITHUB_TOKEN` with `permissions: actions: write` for a cleaner least-privilege separation.
> However, FR-003 and NFR-003 explicitly require using `COPILOT_GITHUB_TOKEN` with Actions write permission
> and prohibit additional secrets. This plan now aligns with the spec. If future testing shows
> `GITHUB_TOKEN` is sufficient for approval (which would be preferable for defense-in-depth),
> the spec should be updated first before changing the implementation approach.

### Phase 3 — Graceful Degradation (P3) — FR-006

**Deliverables**: Fallback via `pull_request_review` trigger path.

#### Task 3.1: Add fallback logic to approval monitor

- If a run has been stuck for > configurable threshold (default 2 min per FR-004) AND approval fails:
  - Post a synthetic review comment to trigger `ai-pr-loop.yml` via its `pull_request_review` path
  - Reuse the pattern from `synthetic-copilot-review.yml` (marker comment, `SPECKIT_PR_TOKEN`)
  - Log which path was taken and why

#### Task 3.2: Add logging breadcrumbs in `ai-pr-loop.yml`

- When triggered via `pull_request_review` while the lint run is stuck, log:
  `"Proceeding via pull_request_review fallback — lint workflow in action_required state"`
- This ensures audit trail shows which path was used

### Phase 4 — Documentation & Testing

#### Task 4.1: Update `.github/workflows/README.md`

- Document the new `workflow-approval-monitor.yml` workflow
- Document the config file schema
- Update the architecture section to include the approval monitor

#### Task 4.2: Add Python integration tests

- Add integration tests under `tests/workflows/` (triggered by `.github/workflows/workflow-tests.yml` via paths-filter) for:
  - Config file schema validation (parse and validate `.github/ai-pr-loop-config.json`)
  - Trusted bot list filtering logic
  - Idempotency (re-approval of already-approved run)
- Note: `workflow-tests.yml` runs `pytest tests/workflows/`, not generic YAML/workflow validation; if YAML schema linting is desired, add a separate CI step

#### Task 4.3: Manual verification checklist

- [ ] Verify repo settings: "Fork pull request workflows" policy
- [ ] Verify `copilot-swe-agent[bot]` PR triggers lint without approval (after settings change)
- [ ] Verify untrusted contributor PRs still require approval
- [ ] Trigger `workflow-approval-monitor.yml` manually via `workflow_dispatch`
- [ ] Verify structured logs appear in workflow run output
- [ ] Verify retry limit comment appears after 3 failures
- [ ] Verify dispatch pre-check blocks repair on `action_required` lint runs

## 5. Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Org policy overrides repo-level collaborator settings | Primary path (FR-001) fails silently | Medium | Approval monitor (FR-003/FR-004) activates as automatic fallback |
| `COPILOT_GITHUB_TOKEN` PAT missing Actions write permission | Monitor cannot approve runs | Low | FR-003 requires expanding the PAT to include Actions write permission; verified during implementation |
| Scheduled workflow frequency (2 min) causes API rate limiting | Delayed approvals | Low | Only lists recent lint workflow runs (lightweight query); GitHub REST API allows 5,000 req/hr for authenticated PAT requests ([docs](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)) |
| False positive: untrusted account name matches allow-list | Security breach | Very Low | Exact string match only; no wildcards (NFR-004); allow-list is repo-admin-controlled |
| `workflow_run` event completes with `conclusion: action_required` | Dispatch-decision wastes resources | Medium | Pre-check guard (FR-009) checks `conclusion` and prevents dispatch on approval-gated runs |
| Monitor approves a run that was intentionally held for human review | Bypasses security gate | Low | Only approves runs from allow-listed bot accounts; untrusted PRs are never touched |

## 6. Dependencies

| Dependency | Type | Status | Notes |
|------------|------|--------|-------|
| GitHub REST API `POST /actions/runs/{id}/approve` | External API | Available | Requires token with Actions write permission; uses `COPILOT_GITHUB_TOKEN` per FR-003/NFR-003 |
| `COPILOT_GITHUB_TOKEN` with Actions write permission | Secret/PAT | Verify | May need permission expansion (fine-grained: Actions → Read and write; classic: `workflow` scope); no additional secrets needed (NFR-003) |
| `SPECKIT_PR_TOKEN` | Secret | Exists | Needed for synthetic review fallback (Phase 3) |
| `copilot-swe-agent[bot]` identity | GitHub App | Exists | Cannot be added as collaborator directly |
| Repository admin access | Manual action | Required | For settings change (FR-001/FR-002) |
| `actions/github-script@v7` | Action | In use | Already used throughout existing workflows |

## Appendix A: Reconciliation Notes

### API Query Strategy

The GitHub REST API `GET /repos/{owner}/{repo}/actions/runs` endpoint accepts a `status`
parameter that filters by **both** status and conclusion values (per the API documentation:
"Returns workflow runs with the check run status or conclusion that you specify"). While
`?status=action_required` is technically a valid filter, there is ambiguity about whether
approval-gated runs consistently appear under this filter across all GitHub plan tiers.

**Recommended implementation approach** (defensive, per reviewer feedback):

1. List recent runs constrained to the lint workflow:
   `GET /repos/{owner}/{repo}/actions/workflows/ai-pr-loop-lint.yml/runs?status=completed`
2. Filter client-side: `run.conclusion === 'action_required'`
3. This avoids reliance on `action_required` as a direct status filter and ensures the
   implementation works regardless of internal GitHub API behavior variations.

**Alternative** (simpler but less proven):

- `GET /repos/{owner}/{repo}/actions/runs?status=action_required` — valid per API docs
  but should be validated against actual approval-gated run states during implementation.

The implementation phase should validate both approaches against a real approval-gated run
and select the one that reliably returns the expected results.

### Threshold Reconciliation

The spec (FR-004, Q4) defines a default threshold of **2 minutes** and references a 2-minute
schedule. This plan aligns with the spec's 2-minute default.

**GitHub Actions cron granularity note:** GitHub Actions supports `*/2` cron syntax, but in
practice scheduled workflows may experience 30-60 second delays due to runner queue times.
A `*/2 * * * *` schedule will fire approximately every 2-3 minutes in practice. This is
acceptable for the FR-004 requirement since the 2-minute threshold refers to the detection
window (time between a run becoming stuck and the monitor noticing it), and the cron schedule
directly controls polling frequency. If the effective interval proves too variable, it can be
reduced to `* * * * *` (every minute) as a configuration change without code modifications.

---
*Generated by Copilot SDK (claude-opus-4.6)*
