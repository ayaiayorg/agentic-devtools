# Tasks: Workflow Approval Required Blocks Autonomous AI PR Loop

**Issue**: [#1393](https://github.com/ayaiayorg/agentic-devtools/issues/1393)

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup | Phase 1 (Task 1.1) | Config file creation from plan Phase 1 |
| Phase 2: Foundational | Phase 1 (Task 1.2), Phase 2 (Task 2.5) | Documentation prerequisites split from plan Phases 1 and 2 |
| Phase 3: US1 & US4 | Phase 1 (Task 1.3) | Dispatch pre-check guard from plan Phase 1 |
| Phase 4: US2 | Phase 2 (Tasks 2.1–2.4) | Approval monitor workflow from plan Phase 2 |
| Phase 5: US3 | Phase 3 (Tasks 3.1–3.2) | Graceful degradation from plan Phase 3 |
| Phase 6: Polish | Phase 4 (Tasks 4.1–4.3) | Documentation, testing, and verification from plan Phase 4 |

---

## Phase 1: Setup — Project Scaffolding & Configuration

- [ ] T001 Create `.github/ai-pr-loop-config.json` with `trusted_bot_accounts` allow-list containing `copilot-swe-agent[bot]` and `github-actions[bot]` (FR-007)

---

## Phase 2: Foundational — Documentation & Token Prerequisites

- [ ] T002 Document repository settings change (FR-001/FR-002) in `.github/workflows/README.md` — add section for "Fork pull request workflows" policy and collaborator setup instructions
- [ ] T003 Document `COPILOT_GITHUB_TOKEN` PAT scope requirements in `.github/workflows/README.md` —
  fine-grained PAT: "Actions: Read and write" permission; classic PAT: `workflow` scope (FR-003, NFR-003, Task 2.5)
- [ ] T028 Update existing PAT validation/error message in `.github/workflows/ai-pr-loop.yml` to reflect the new permission requirements when they change (FR-003)

---

## Phase 3: User Story 1 & 4 — Dispatch Pre-Check Guard (P1)

### US1: Unblock Lint Workflow for Bots / US4: Dispatch Pre-Check Guards

- [ ] T004 [US4] Add dispatch pre-check guard in `.github/workflows/ai-pr-loop.yml` `dispatch-decision` step — when `context.eventName === 'workflow_run'`,
  check `context.payload.workflow_run.conclusion`; skip dispatch if `action_required` or `null` and log the skip reason (FR-009)
- [ ] T005 [US1] Add inline comments in `.github/workflows/ai-pr-loop-lint.yml` documenting that collaborator status (FR-001) eliminates the approval gate
  for trusted bots — no code change to this read-only workflow

---

## Phase 4: User Story 2 — Programmatic Approval Monitor (P2)

### US2: Programmatic Approval API Fallback + Observability

- [ ] T006 [US2] Create `.github/workflows/workflow-approval-monitor.yml` scaffold with the following trigger structure,
  permissions (`actions: write`, `pull-requests: read`, `issues: write`, `contents: read`), concurrency group, single job with `actions/github-script@v7`
  (Note: GitHub Actions scheduled workflows have a ~5-minute minimum effective interval; `*/5` matches this platform constraint)

  ```yaml
  on:
    schedule:
      - cron: '*/5 * * * *'
    workflow_dispatch:
  ```

- [ ] T007 [US2] Implement config file loading step in `workflow-approval-monitor.yml` — read `.github/ai-pr-loop-config.json` via GitHub Contents API,
  parse JSON, extract `trusted_bot_accounts` array, abort with error log if file missing or invalid
- [ ] T008 [US2] Implement workflow run listing and filtering in `workflow-approval-monitor.yml` —
  primary approach (per plan Appendix A): `GET /repos/{owner}/{repo}/actions/workflows/ai-pr-loop-lint.yml/runs?status=completed`,
  filter client-side for `run.conclusion === 'action_required'`; filtered to runs associated with
  PRs authored by trusted bot accounts, skip runs newer than 2-minute threshold using `run.run_started_at` (FR-004)
- [ ] T029 [US2] Validate API query strategy during implementation — test primary approach
  (`status=completed` + client-side `conclusion` filter) against a real approval-gated run;
  if unreliable, fall back to `GET /repos/{owner}/{repo}/actions/runs?status=action_required` (plan Appendix A)
- [ ] T009 [US2] Implement PR author eligibility check in `workflow-approval-monitor.yml` — for each stuck run, resolve associated PR number
  from `run.pull_requests[0].number`, fetch PR details via `GET /repos/{owner}/{repo}/pulls/{pull_number}`, confirm `pr.user.login` (case-insensitive)
  is in `trusted_bot_accounts`, confirm same-repo (not fork) via `head.repo.full_name === base.repo.full_name`
- [ ] T010 [US2] Implement idempotency guard in `workflow-approval-monitor.yml` — before calling approve API,
  re-check `run.conclusion === 'action_required'`; if already approved/completed, log skip reason and continue (FR-008)
- [ ] T011 [US2] Implement approve API call in `workflow-approval-monitor.yml` — `POST /repos/{owner}/{repo}/actions/runs/{run_id}/approve`
  using `COPILOT_GITHUB_TOKEN`, handle 201 (success), 403 (permission denied), 404/409 (not approvable) responses (FR-003)
- [ ] T012 [US2] Implement structured audit logging in `workflow-approval-monitor.yml` — emit JSON log entry via `core.info()` for each approval
  action (success, failure, skip) with fields: `event`, `actor`, `timestamp`, `pr_number`, `run_id`, `head_sha`, `source`, `result`, `reason` (FR-005)
- [ ] T013 [US2] Implement retry tracking via PR comment markers in `workflow-approval-monitor.yml` —
  parse `<!-- workflow-approval-retry:{sha}:{count} -->` from existing PR comments, increment count on each attempt,
  stop after 3 failures per `(pr_number, head_sha)` (NFR-006)
- [ ] T014 [US2] Implement failure notification PR comment in `workflow-approval-monitor.yml` — after 3 failed attempts, post/update PR comment
  with failure details, stuck run link, and manual resolution instructions (NFR-006)

---

## Phase 5: User Story 3 — Graceful Degradation (P3)

### US3: Graceful Degradation via `pull_request_review` Path

- [ ] T015 [US3] Add fallback logic to `workflow-approval-monitor.yml` — when approval fails and run has been stuck beyond threshold,
  post synthetic review event to trigger `ai-pr-loop.yml` via `pull_request_review` path, reusing `SPECKIT_PR_TOKEN`
  and `<!-- synthetic-copilot-review -->` marker pattern from `synthetic-copilot-review.yml` (FR-006)
- [ ] T016 [US3] Add logging breadcrumb in `.github/workflows/ai-pr-loop.yml` — in trigger guards step, when triggered via `pull_request_review`
  while a lint run is in `action_required` state, log `"Proceeding via pull_request_review fallback — lint workflow in action_required state"`

---

## Phase 6: Polish & Cross-Cutting

- [ ] T017 Update `.github/workflows/README.md` — add documentation section for `workflow-approval-monitor.yml` (purpose, schedule, permissions,
  config file schema, retry behavior, graceful degradation)
- [ ] T018 Update `.github/workflows/README.md` — update `ai-pr-loop.yml` documentation to describe the new dispatch pre-check guard (FR-009)
  and `action_required` handling
- [ ] T019 [US2] Add JSON schema validation test for `.github/ai-pr-loop-config.json` in `tests/workflows/test_ai_pr_loop_config.py` —
  validate structure, non-empty array, no wildcards, string entries (FR-007)
- [ ] T020 [US2] Add unit test for trusted bot account filtering logic in `tests/workflows/test_trusted_bot_filtering.py` —
  test successful approval for trusted bot collaborator PRs (happy path), test case-insensitive matching, fork rejection, non-listed account rejection (FR-001, FR-002, FR-007)
- [ ] T021 [US2] Add unit test for idempotency logic in `tests/workflows/test_approval_idempotency.py` —
  test skip when conclusion is not `action_required`, test proceed when `action_required` (FR-008)
- [ ] T022 Create manual acceptance checklist in PR description — confirm repo settings, bot PR lint execution,
  untrusted contributor approval requirement, `workflow_dispatch` trigger, structured logs, retry limit comment, dispatch pre-check behavior
- [ ] T023 [US2] Add unit test for approve API call handling in `tests/workflows/test_approve_api.py` —
  test 201 success response, 403 permission denied, 404/409 not approvable responses (FR-003)
- [ ] T024 [US2] Add unit test for monitoring mechanism threshold in `tests/workflows/test_monitor_threshold.py` —
  test detection of runs stuck longer than 2-minute threshold, test skip of runs newer than threshold (FR-004)
- [ ] T025 [US2] Add unit test for structured audit logging in `tests/workflows/test_audit_logging.py` —
  test JSON log entry format and required fields for success, failure, and skip actions (FR-005)
- [ ] T026 [US3] Add unit test for graceful degradation fallback in `tests/workflows/test_graceful_degradation.py` —
  test synthetic review event posting when approval fails, test `pull_request_review` fallback path activation (FR-006)
- [ ] T027 [US4] Add unit test for dispatch pre-check guard in `tests/workflows/test_dispatch_precheck.py` —
  test skip when conclusion is `action_required` or `null`, test proceed when conclusion is `success` or `failure` (FR-009)

### Dependencies

```text
T028 depends on T003 (PAT documentation before validation update)
T007 depends on T001 (config file must exist before monitor reads it)
T007, T008, T029, T009, T010, T011, T012, T013, T014 depend on T006 (scaffold before logic)
T029 depends on T008 (listing implemented before strategy validation)
T009, T010, T011 depend on T008 (run listing before filtering/approval)
T010, T011 depend on T009 (author verification before approval call)
T012 depends on T011 (approval call before audit logging of result)
T014 depends on T013 (retry tracking before failure notification)
T016 depends on T004 (pre-check guard exists before adding fallback breadcrumb)
T015 depends on T006..T014 (monitor workflow complete before adding fallback)
T019, T020, T021, T023, T024, T025, T026, T027 are parallelizable (independent test files)
```

---
*Generated by Copilot SDK (claude-opus-4.6)*
