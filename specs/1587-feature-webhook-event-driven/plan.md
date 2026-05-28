# Implementation Plan: Event-Driven Trigger for AI PR Loop

## Technical Context

- **Repository**: `ayaiayorg/agentic-devtools`
- **Platform**: GitHub Actions workflows (YAML-based)
- **Existing infrastructure**:
  - `ai-pr-loop.yml` — orchestrator workflow with `workflow_dispatch` input accepting `pr_number` (string) and `trigger_reason` (string)
  - `squash-wait-scheduler.yml` — cron-based (`*/5`) scheduler dispatching via `gh workflow run`
  - `agentic_devtools/cli/ci/` — Python CI module with `github_provider.py` (Issues Events API via `list_pr_issue_events`), `models.py` (event constants), `session_detector.py` (staleness logic)
  - Concurrency group: `ai-pr-loop-${{ ... || github.event.inputs.pr_number || github.run_id }}`
- **Key constants**: `COPILOT_SESSION_EVENT_FINISHED`, `COPILOT_SESSION_EVENT_FINISHED_FAILURE`, `LABEL_SKIP_ENTIRELY = "ai-pr-loop-ignore"`
- **Auth**: `AGDT_PR_APPROVER_PAT` secret for `gh` CLI calls

## Research Summary

See the decisions below for:

- Caching strategy for event deduplication
- Monitor workflow structure (standalone vs. integrated)
- Monitor trigger cadence and dispatch mechanism

All decisions align with the proven `squash-wait-scheduler.yml` pattern.

## Design Overview

```text
┌─────────────────────────────────────────────────────────────┐
│    agent-session-monitor.yml (*/5 cron + workflow_dispatch)    │
├─────────────────────────────────────────────────────────────┤
│  1. Restore seen-events cache (prefix restore)               │
│  2. List open PRs (non-fork, no ignore label)                │
│  3. For each PR:                                             │
│     a. GET /issues/{pr}/events (filter terminal events)     │
│     b. Deduplicate against seen-events set                  │
│     c. Dispatch workflow_dispatch for new terminal events    │
│     d. Append event ID and prune seen-events set to last N   │
│  4. Save updated seen-events cache (per-run key)             │
└─────────────────────────────────────────────────────────────┘
         │
         │ gh workflow run ai-pr-loop.yml
         │   --repo "$GITHUB_REPOSITORY"
         │   --field pr_number="$pr"
         │   --field trigger_reason=agent_session_finished
         ▼
┌─────────────────────────────────────────────────────────────┐
│              ai-pr-loop.yml (existing, UNCHANGED)           │
│  concurrency: ai-pr-loop-${{ github.event.pull_request.    │
│    number || github.event.issue.number ||                  │
│    github.event.workflow_run.pull_requests[0].number ||    │
│    github.event.inputs.pr_number || github.run_id }}       │
│  cancel-in-progress: false                                  │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Core Monitor Workflow (`.github/workflows/agent-session-monitor.yml`)

**Deliverable**: A self-contained GitHub Actions workflow file.

#### Tasks

1. **Create workflow file** with:
   - Triggers:
     - `schedule: - cron: '*/5 * * * *'` (meets the 300-second latency target from FR-001)
     - `workflow_dispatch` (manual trigger)
   - Permissions: `contents: read`, `pull-requests: read`, `actions: write`, `issues: read`
   - Single job `monitor-agent-sessions`, `runs-on: ubuntu-latest`, `timeout-minutes: 2`
   - **Concurrency group**: `agent-session-monitor` with `cancel-in-progress: false` (serializes scheduled runs)

2. **Step: Restore cache** — use `actions/cache/restore@v4` with:
   - `key: agent-monitor-seen-events-${{ github.run_id }}`
   - `restore-keys: agent-monitor-seen-events-`
   - Path: `.cache/seen-events.json`

3. **Step: Scan and dispatch** — bash script that:
   - Sets `GH_TOKEN: ${{ secrets.AGDT_PR_APPROVER_PAT }}` in the step env (matching the existing scheduler pattern)
   - Ensures `.cache/` exists and initializes `.cache/seen-events.json` to `[]` when missing
   - Loads seen-events JSON (or initializes empty array)
   - Lists open PRs via `gh pr list --repo $GITHUB_REPOSITORY --json number,labels,isCrossRepository,updatedAt --limit 500`
   - Sorts PRs by `updatedAt` descending (most recently active first), skips forks via `isCrossRepository`, and excludes PRs labeled `ai-pr-loop-ignore`
   - For each eligible PR, calls `gh api /repos/{owner}/{repo}/issues/{pr}/events --paginate`
   - Filters for `copilot_work_finished` and `copilot_work_finished_failure` events
   - Deduplicates against seen-events set
   - Dispatches via `gh workflow run ai-pr-loop.yml --repo "$GITHUB_REPOSITORY" --field pr_number="$pr" --field trigger_reason=agent_session_finished`
   - Appends processed event IDs to seen-events JSON and prunes the array to the last N IDs (e.g., 500)
   - Enforces a scan budget (stop at 90 seconds) so runtime stays within 2 minutes; remaining PRs are handled in subsequent runs
   - Emits structured logs: `event_id=X pr_number=Y action=dispatched|skipped reason=...`
   - Isolates per-PR scan failures so one PR does not block others, records whether any PR scan
     errors occurred (for example via a step output or error flag file), and completes the step
     without exiting non-zero before cache persistence

4. **Step: Save cache** — use `actions/cache/save@v4` with:
   - `if: always()`
   - `key: agent-monitor-seen-events-${{ github.run_id }}`
   - Path: `.cache/seen-events.json`

5. **Step: Surface partial-cycle failure after cache save** — final bash step that runs after the
   cache save, checks the recorded scan-error flag/output, and exits non-zero if any PR scan
   errors prevented full completion of the cycle.

6. **No additional trigger-emitter integration** — monitor relies on `*/5` schedule + manual
   `workflow_dispatch`; no `repository_dispatch` emitter or external trigger plumbing is required.

7. **Per-PR error isolation with surfaced failure** — isolate each PR scan so one failure does
   not block others, preserve updated deduplication state by always saving the cache, and then
   fail the job in a final step if any PR scan errors prevented full completion of the cycle.

### Phase 2: Guard Checks in Monitor

**Deliverable**: FR-004 compliance — skip ineligible PRs before dispatch.

#### Tasks

1. **Fork detection** — handled by `gh pr list --json isCrossRepository`; skip PRs where `isCrossRepository` is true.
2. **Label filtering** — check for `ai-pr-loop-ignore` in PR labels JSON.
3. **PR state check** — `gh pr list` only returns open PRs by default, satisfying the "currently open" requirement.
4. **Closed/merged race** — if a PR is closed between list and dispatch, the `ai-pr-loop.yml` orchestrator handles this gracefully (existing behavior).

### Phase 3: Observability & Logging

**Deliverable**: NFR-004 structured logging.

#### Tasks

1. **Structured output format** — each action line as `key=value` pairs:

   ```text
   ts=2026-05-27T11:30:00Z pr_number=42 event_id=123456 event_type=copilot_work_finished action=dispatched
   ts=2026-05-27T11:30:00Z pr_number=43 event_id=789012 action=skipped reason=already_seen
   ts=2026-05-27T11:30:01Z pr_number=44 action=skipped reason=label_excluded
   ```

2. **Summary output** — workflow summary via `$GITHUB_STEP_SUMMARY` with total PRs scanned, events found, dispatches issued.
3. **Error logging and exit policy** — API failures are logged with structured context, processing
   continues for other PRs, and the run exits non-zero if any scan failure prevented full cycle
   completion (aligned with the observability acceptance scenario).

### Phase 4: Testing & Validation

**Deliverable**: Confidence in correctness before merge.

#### Tasks

1. **Deduplication validation** — verify correctness via `DRY_RUN` mode (item 3) with a
   pre-seeded `.cache/seen-events.json` fixture; no Python unit tests needed (pure bash
   implementation with no Python code changes).
2. **Manual validation** — trigger `workflow_dispatch` on the monitor to verify it scans and dispatches correctly.
3. **Dry-run mode** — add `DRY_RUN` env var that logs dispatches without executing `gh workflow run`.
4. **Integration verification** — confirm `ai-pr-loop.yml` processes the dispatch correctly (existing `workflow_dispatch` path already handles this).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Cache eviction causes re-dispatch | Medium | Low | Concurrency group (added in Phase 1) serializes runs and reduces overlap; retained seen-event cache reduces duplicate dispatches within the cache window, with occasional re-dispatch after eviction accepted as low impact |
| API rate limiting with many open PRs | Low | Medium | Process PRs by `updatedAt` descending, cap each run to 90s within `timeout-minutes: 2`, and keep per-PR error isolation so one failing PR does not abort the run |
| Monitor overlapping with itself | Low | Low | Concurrency group `agent-session-monitor` with `cancel-in-progress: false` (defined in Phase 1) serializes scheduled runs; `timeout-minutes: 2` as a secondary safeguard |
| `gh workflow run` fails silently | Low | Medium | Check exit code; log failures as `::error::` |
| Cache grows unbounded | Low | Low | Retain only the last N event IDs (e.g., 500) in `.cache/seen-events.json`; use the Phase 1 per-run cache key `agent-monitor-seen-events-${{ github.run_id }}` with restore prefix matching so the restored payload stays bounded without introducing an undefined bucket variable |

## Dependencies

- **External**: GitHub Actions cache (`actions/cache@v4`), GitHub Issues Events API, `gh` CLI
- **Internal**: `ai-pr-loop.yml` `workflow_dispatch` inputs (already exist, no changes needed)
- **Secrets**: `AGDT_PR_APPROVER_PAT` (same as squash-wait-scheduler)
- **No changes to**: `ai-pr-loop.yml`, `orchestrator.py`, `session_detector.py`, or any Python code

---
*Generated by Copilot SDK (claude-opus-4.6)*
