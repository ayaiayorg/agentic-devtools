# Tasks: Event-Driven Trigger for AI PR Loop on Agent Session Completion

**Feature Branch**: `speckit/1587/phase-4-tasks`
**Source Issue**: [#1587](https://github.com/ayaiayorg/agentic-devtools/issues/1587)

---

## Phase Mapping: Plan → Tasks

Phases are 1:1 aligned with `plan.md`.

---

## Phase 1: Setup

- [ ] T001 Create feature branch `feature/1587/webhook-event-driven` from `main`
- [ ] T002 Create workflow file scaffold at `.github/workflows/agent-session-monitor.yml` with name, triggers (`on: schedule: - cron: '*/2 * * * *'`,
  `workflow_dispatch`), permissions (`contents: read`, `pull-requests:
  read`, `actions: write`, `issues: read`), and empty job skeleton

---

## Phase 2: Foundational — Cache & Job Structure

- [ ] T003 Add concurrency group `agent-session-monitor` with `cancel-in-progress: false` to the monitor job in `.github/workflows/agent-session-monitor.yml`
- [ ] T004 Add `timeout-minutes: 2` to the monitor job in `.github/workflows/agent-session-monitor.yml`
- [ ] T005 Add cache restore step using `actions/cache/restore@v4` with key `agent-monitor-seen-events-${{ github.run_id }}` and `restore-keys: agent-monitor-seen-events-` targeting
  `.cache/seen-events.json`
- [ ] T006 Add cache save step using `actions/cache/save@v4` with `if: always()` and key `agent-monitor-seen-events-${{ github.run_id }}` targeting `.cache/seen-events.json` (FR-002: deduplication
  persistence via GitHub Actions cache with restore-keys prefix and per-run save key)

---

## Phase 3: User Story 1 — Immediate Post-Agent PR Processing (P1)

- [ ] T007 [US1] Write the main "Scan and dispatch" bash step skeleton in `.github/workflows/agent-session-monitor.yml` setting `GH_TOKEN: ${{ secrets.AGDT_PR_APPROVER_PAT }}`, initializing
  `.cache/seen-events.json` to `[]` if missing, and loading the seen-events array (FR-001: scheduled monitor workflow running `*/2`)
- [ ] T008 [US1] Implement open PR listing via `gh pr list --repo $GITHUB_REPOSITORY --json number,labels,isCrossRepository,updatedAt --limit 500` sorted by `updatedAt` descending in the scan step
  (FR-004: only open, non-fork PRs without `ai-pr-loop-ignore` label)
- [ ] T009 [US1] Implement per-PR event fetching via `gh api /repos/{owner}/{repo}/issues/{pr}/events --paginate` filtering for `copilot_work_finished` and `copilot_work_finished_failure` event types
  (FR-007: handles both successful and failed terminal events)
- [ ] T010 [US1] Implement dispatch logic via `gh workflow run ai-pr-loop.yml --repo "$GITHUB_REPOSITORY" --field pr_number="$pr" --field trigger_reason=agent_session_finished` for new terminal events
  (FR-001: triggers AI PR loop within 120s; FR-003: passes `pr_number` input; FR-005: sets `trigger_reason` to `agent_session_finished`)
- [ ] T011 [US1] Add scan budget enforcement (~110 seconds elapsed time check) to prioritize recently-active PRs and defer remaining to next cycle (NFR-001)

---

## Phase 4: User Story 2 — Idempotent Event Processing (P1)

- [ ] T012 [US2] Implement event ID deduplication check against the loaded seen-events JSON array before dispatching (FR-002: at most one dispatch per unique event ID)
- [ ] T013 [US2] Implement appending dispatched event IDs to seen-events array and pruning to last 500 entries after each cycle (FR-002: bounded cache size)
- [ ] T014 [US2] Add handling for missing/evicted cache — treat as empty set, allow re-dispatch with concurrency group as secondary defense (FR-002 graceful degradation)

---

## Phase 5: User Story 3 — Graceful Coexistence with Existing Triggers (P2)

- [ ] T015 [US3] Verify `ai-pr-loop.yml` is NOT modified — confirm no changes to its trigger configuration or concurrency group expression (FR-006: coexists without modification of existing workflow)
- [ ] T016 [US3] Document in workflow comments that the monitor supplements existing triggers and relies on `ai-pr-loop-{pr_number}` concurrency group in `ai-pr-loop.yml` to serialize concurrent runs
  (FR-006)

---

## Phase 6: User Story 4 — Monitor Workflow Observability (P3)

- [ ] T017 [P] [US4] Implement structured `key=value` log output for each action (`ts=... pr_number=... event_id=... event_type=... action=dispatched|skipped reason=...`) in the scan step (NFR-004)
- [ ] T018 [P] [US4] Add `$GITHUB_STEP_SUMMARY` output with total PRs scanned, events found, dispatches issued, and errors encountered
- [ ] T019 [US4] Implement per-PR error isolation — wrap each PR scan in error handling so one failure does not block others; record scan-error flag for final step
- [ ] T020 [US4] Add final step after cache save that checks scan-error flag and exits non-zero if any PR scan errors occurred (surfaces failure in Actions UI after cache is persisted)

---

## Phase 7: Testing & Validation

- [ ] T021 Add `DRY_RUN` environment variable support — when set, log dispatch commands without executing `gh workflow run`
- [ ] T022 [US2] Create a test fixture `.github/test-fixtures/seen-events-sample.json` with pre-seeded event IDs for deduplication validation in dry-run mode (FR-002)
- [ ] T023 [US2] Validate deduplication by running monitor with `DRY_RUN=true` and pre-seeded seen-events fixture, confirming already-seen events are skipped (FR-002)
- [ ] T024 [US1] Manual happy-path success test — trigger `workflow_dispatch` on `agent-session-monitor.yml` and verify structured logs, cache creation,
  and dispatch behavior for eligible open PRs (FR-004)
- [ ] T025 Integration verification — confirm dispatched `workflow_dispatch` is received by `ai-pr-loop.yml` and PR number is correctly resolved in its concurrency group

---

## Phase 8: Polish & Cross-Cutting

- [ ] T026 [P] Add inline documentation comments in `.github/workflows/agent-session-monitor.yml` explaining design decisions, FR traceability, and relationship to `squash-wait-scheduler.yml`
- [ ] T027 [P] Update `PR_DESCRIPTION.md` or create PR description documenting the feature, referencing #1587
- [ ] T028 Run existing CI checks (`bash scripts/run-pr-checks.sh`) to confirm no regressions introduced
- [ ] T029 Final review — verify all FRs are addressed: FR-001 (cron+dispatch), FR-002 (cache dedup), FR-003 (pr_number field), FR-004 (guard checks), FR-005 (trigger_reason field), FR-006 (no
  ai-pr-loop.yml changes), FR-007 (both terminal event types)

---

## Dependency Graph

```text
T001 → T002 → T003, T004, T005, T006 (parallel)
T005, T006 → T007 → T008 → T009 → T010 → T011
T010 → T012 → T013 → T014
T010 → T015, T016 (parallel)
T007 → T017, T018, T019 (parallel)
T019 → T020
T013 → T021 → T022 → T023
T023 → T024 → T025
T025 → T026, T027 (parallel) → T028 → T029
```

---

## FR Traceability Matrix

| FR | Tasks |
| --- | --- |
| FR-001 | T007, T010 |
| FR-002 | T006, T012, T013, T014, T022, T023 |
| FR-003 | T010 |
| FR-004 | T008, T024 |
| FR-005 | T010 |
| FR-006 | T015, T016 |
| FR-007 | T009 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
