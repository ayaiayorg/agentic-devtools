# Tasks: Event-Driven Trigger for AI PR Loop on Agent Session Completion

**Feature Branch**: `speckit/1587/phase-4-tasks`
**Source Issue**: [#1587](https://github.com/ayaiayorg/agentic-devtools/issues/1587)

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
| --- | --- | --- |
| Phase 1: Setup | Phase 1: Core Monitor Workflow | Create the monitor workflow scaffold and baseline trigger/permission structure. |
| Phase 2: Foundational — Cache & Job Structure | Phase 1: Core Monitor Workflow | Establish timeout, cache persistence, and dry-run support used by all stories. |
| Phase 3: User Story 1 — Immediate Post-Agent PR Processing (P1) | Phase 1: Core Monitor Workflow | Add US1 validations and implement PR scanning plus workflow dispatch behavior. |
| Phase 4: User Story 2 — Idempotent Event Processing (P1) | Phase 1: Core Monitor Workflow | Add US2 validations and implement event-id deduplication and cache fallback behavior. |
| Phase 5: User Story 3 — Graceful Coexistence with Existing Triggers (P2) | Phase 2: Guard Checks | Validate and document coexistence with existing trigger paths and shared concurrency. |
| Phase 6: User Story 4 — Monitor Workflow Observability (P3) | Phase 3: Observability & Logging | Implement structured logs, summary output, and error isolation/failure signaling. |
| Phase 7: Testing & Validation | Phase 4: Testing & Validation | Execute cross-story negative and integration validations. |
| Phase 8: Polish & Cross-Cutting | Phase 4: Testing & Validation | Final documentation, full checks, and completion review. |

---

## Phase 1: Setup

- [x] T001 Create feature branch `feature/1587/webhook-event-driven` from `main`
- [x] T002 Create workflow file scaffold at `.github/workflows/agent-session-monitor.yml` with name, triggers (`on: schedule: - cron: '*/5 * * * *'`,
  `workflow_dispatch`), permissions (`contents: read`, `pull-requests:
  read`, `actions: write`, `issues: read`), and empty job skeleton

---

## Phase 2: Foundational — Cache & Job Structure

- [x] T003 Add concurrency group `agent-session-monitor` with `cancel-in-progress: false` to the monitor job in `.github/workflows/agent-session-monitor.yml`
- [x] T004 Add `timeout-minutes: 2` to the monitor job in `.github/workflows/agent-session-monitor.yml`
- [x] T005 Add cache restore step using `actions/cache/restore@v4` with key `agent-monitor-seen-events-${{ github.run_id }}` and `restore-keys: agent-monitor-seen-events-` targeting
  `.cache/seen-events.json`
- [x] T006 Add cache save step using `actions/cache/save@v4` with `if: always()` and key `agent-monitor-seen-events-${{ github.run_id }}` targeting `.cache/seen-events.json` (FR-002: deduplication
  persistence via GitHub Actions cache with restore-keys prefix and per-run save key)
- [x] T007 Add `DRY_RUN` environment variable support — when set, log dispatch commands without executing `gh workflow run`

---

## Phase 3: User Story 1 — Immediate Post-Agent PR Processing (P1)

- [x] T008 [US1] Dry-run test for FR-001 — verify monitor generates a dispatch command for each new terminal event (success path) (FR-001)
- [x] T009 [US1] Dry-run test for FR-003 — verify `--field pr_number` is correctly set in the generated dispatch command (success path) (FR-003)
- [x] T010 [US1] Dry-run test for FR-005 — verify `--field trigger_reason=agent_session_finished` is correctly set in the generated dispatch command (success path) (FR-005)
- [x] T011 [US1] Dry-run test for FR-007 — verify both `copilot_work_finished` and `copilot_work_finished_failure` events trigger dispatch (success path) (FR-007)
- [x] T012 [US1] Manual happy-path success test — trigger `workflow_dispatch` on `agent-session-monitor.yml` and verify structured logs, cache creation,
  and dispatch behavior for eligible open PRs (FR-004)
- [x] T013 [US1] Write the main "Scan and dispatch" bash step skeleton in `.github/workflows/agent-session-monitor.yml` setting `GH_TOKEN: ${{ secrets.AGDT_PR_APPROVER_PAT }}`, initializing
  `.cache/seen-events.json` to `[]` if missing, and loading the seen-events array (FR-001: scheduled monitor workflow running `*/5`)
- [x] T014 [US1] Implement open PR listing via `gh api graphql` fetching PRs in `UPDATED_AT` order in the scan step
  (FR-004: only open, non-fork PRs without `ai-pr-loop-ignore` label)
- [x] T015 [US1] Implement per-PR event fetching via `gh api /repos/{owner}/{repo}/issues/{pr}/events --paginate` filtering for `copilot_work_finished` and `copilot_work_finished_failure` event types
  (FR-007: handles both successful and failed terminal events)
- [x] T016 [US1] Implement dispatch logic via `gh workflow run ai-pr-loop.yml --repo "$GITHUB_REPOSITORY" --field pr_number="$pr" --field trigger_reason=agent_session_finished` for new terminal events
  (FR-001: triggers AI PR loop within 300s; FR-003: passes `pr_number` input; FR-005: sets `trigger_reason` to `agent_session_finished`)
- [x] T017 [US1] Add scan budget enforcement (~90s elapsed time check, reserving ~30s for cache save
  within the 2-minute job timeout) to prioritize recently-active PRs and defer remaining to next cycle (NFR-001)

---

## Phase 4: User Story 2 — Idempotent Event Processing (P1)

- [x] T018 [US2] Create a test fixture `.github/test-fixtures/seen-events-sample.json` with pre-seeded event IDs for deduplication validation in dry-run mode (FR-002)
- [x] T019 [US2] Validate deduplication by running monitor with `DRY_RUN=true` and pre-seeded seen-events fixture, confirming already-seen events are skipped (FR-002)
- [x] T020 [US2] Implement event ID deduplication check against the loaded seen-events JSON array before dispatching (FR-002: at most one dispatch per unique event ID)
- [x] T021 [US2] Implement appending dispatched event IDs to seen-events array and pruning to last 500 entries after each cycle (FR-002: bounded cache size)
- [x] T022 [US2] Add handling for missing/evicted cache — treat as empty set, allow re-dispatch with concurrency group as secondary defense (FR-002 graceful degradation)

---

## Phase 5: User Story 3 — Graceful Coexistence with Existing Triggers (P2)

- [x] T023 [US3] Validate coexistence by exercising an existing `ai-pr-loop.yml` trigger path alongside monitor-issued dispatch and verifying shared
  `ai-pr-loop-{pr_number}` concurrency serializes runs without conflict (FR-006)
- [x] T024 [US3] Document in workflow comments that the monitor supplements existing triggers and relies on `ai-pr-loop-{pr_number}` concurrency group in `ai-pr-loop.yml` to serialize concurrent runs
  (FR-006)

---

## Phase 6: User Story 4 — Monitor Workflow Observability (P3)

- [x] T025 [P] [US4] Implement structured `key=value` log output for each action (`ts=... pr_number=... event_id=... event_type=... action=dispatched|skipped reason=...`) in the scan step (NFR-004)
- [x] T026 [P] [US4] Add `$GITHUB_STEP_SUMMARY` output with total PRs scanned, events found, dispatches issued, and errors encountered
- [x] T027 [US4] Implement per-PR error isolation — wrap each PR scan in error handling so one failure does not block others; record scan-error flag for final step
- [x] T028 [US4] Add final step after cache save that checks scan-error flag and exits non-zero if any PR scan errors occurred (surfaces failure in Actions UI after cache is persisted)

---

## Phase 7: Testing & Validation

- [x] T029 [US1] Negative validation for FR-004 — confirm forked, closed/merged, or `ai-pr-loop-ignore` PRs are skipped, logged with skip reason, and do not issue `workflow_dispatch` commands
- [x] T030 Integration verification — confirm dispatched `workflow_dispatch` is received by `ai-pr-loop.yml` and PR number is correctly resolved in its concurrency group

---

## Phase 8: Polish & Cross-Cutting

- [x] T031 [P] Add inline documentation comments in `.github/workflows/agent-session-monitor.yml` explaining design decisions, FR traceability, and relationship to `squash-wait-scheduler.yml`
- [x] T032 [P] Update `PR_DESCRIPTION.md` or create PR description documenting the feature, referencing #1587
- [x] T033 Run existing CI checks (`bash scripts/run-pr-checks.sh`) to confirm no regressions introduced
- [x] T034 Final review — verify all FRs are addressed and all implementation checklist items are complete

---

## Dependency Graph

```text
T001 → T002 → T003, T004, T005, T006 (parallel)
T005, T006 → T007
T007 → T008, T009, T010, T011, T012 (parallel)
T007 → T013 → T014 → T015 → T016 → T017
T007, T016 → T018 → T019
T016 → T020 → T021 → T022
T016 → T023 → T024
T013 → T025, T026, T027 (parallel)
T027 → T028
T014 → T029
T016, T023 → T030
T030 → T031, T032 (parallel) → T033 → T034
```

---

## FR Traceability Matrix

| FR | Tasks |
| --- | --- |
| FR-001 | T013, T016, T008 |
| FR-002 | T006, T018, T019, T020, T021, T022 |
| FR-003 | T016, T009 |
| FR-004 | T014, T012, T029 |
| FR-005 | T016, T010 |
| FR-006 | T023, T024, T030 |
| FR-007 | T015, T011 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
