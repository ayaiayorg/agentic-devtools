# Implementation Plan: Unified Agent Session Monitor with Comment-Based Tracking

## Technical Context

**Stack**: Python 3.11+, GitHub Actions (YAML), `gh` CLI, GitHub REST/GraphQL API  
**Package**: `agentic_devtools` — pip-installable CLI with sub-package pattern under `cli/ci/`  
**Testing**: pytest, 100% branch coverage required, 1:1:1 test structure under `tests/unit/`  
**CI**: GitHub Actions with `*/5` cron schedule, PAT-based `workflow_dispatch`  
**Key Dependencies**: `gh` CLI (agent-task, API calls), `pyyaml` (workflow parsing in tests), `dataclasses`

## Research Summary

See [research.md](research.md) for detailed decisions on:

- Comment-based deduplication vs cache-based (decision: PR comments with upsert)
- Correlation strategy (decision: task-ID-first, timestamp fallback)
- Round-robin batching cursor storage (decision: workflow-level artifact/env, not per-PR)
- Tracker comment format (decision: HTML comment metadata + markdown table)

## Design Overview

```text
┌─────────────────────────────────────────────────────────┐
│         agent-session-monitor.yml (enhanced)            │
│  schedule: */5 * * * *                                  │
│  permissions: issues:write, pull-requests:write         │
├─────────────────────────────────────────────────────────┤
│  1. Load round-robin cursor (cache artifact)            │
│  2. List open PRs → batch by AGENT_MONITOR_MAX_PRS     │
│  3. For each PR in batch:                               │
│     a. Query gh agent-task list (source: agent-task)    │
│     b. Query issues events API (source: events-api)     │
│     c. Query PR Reviews API (source: reviews-api)       │
│     d. Read existing tracker comment (parse)            │
│     e. Merge new sessions (deduplicate by task ID)      │
│     f. Dispatch ai-pr-loop for new sessions             │
│     g. Render & upsert tracker comment                  │
│  4. Save updated cursor                                 │
└─────────────────────────────────────────────────────────┘
         │                                    │
         │ workflow_dispatch                   │
         ▼                                    ▼
┌─────────────────┐         ┌────────────────────────────┐
│  ai-pr-loop.yml │         │ agentic_devtools/cli/ci/   │
│  (trigger removed│         │   tracker/ (Python lib)    │
│   pull_request_  │         │   ├── models.py            │
│   review)        │         │   ├── parser.py            │
│                  │         │   ├── renderer.py          │
│                  │         │   └── merger.py            │
└─────────────────┘         └────────────────────────────┘
```

## Implementation Phases

### Phase 1: Python Tracker Library (`agentic_devtools/cli/ci/tracker/`)

**Deliverables**: Fully tested sub-package with models, parser, renderer, merger

#### Tasks

1. **Create `tracker/models.py`** — Define `TrackedSession`, `TrackerComment`, `DetectionSource` enum
2. **Create `tracker/renderer.py`** — Render `TrackerComment` → markdown string (HTML comment header + table)
3. **Create `tracker/parser.py`** — Parse markdown string → `TrackerComment` (inverse of renderer)
4. **Create `tracker/merger.py`** — Merge sessions from multiple sources, deduplicate by task ID (primary) then timestamp (fallback), determine new vs already-processed sessions
5. **Create `tracker/__init__.py`** — Re-export public API
6. **Write unit tests** — ≥25 test cases covering all edge cases (truncation at 32K chars, missing fields, concurrent updates, round-trip parse/render, correlation logic)

#### Acceptance

- 100% branch coverage on all tracker modules
- Parser/renderer round-trip is lossless for all valid inputs
- Merger correctly correlates by task ID (primary) and timestamp (fallback)
- Truncation preserves running sessions + 20 most recent completed

---

### Phase 2: Dead Code Removal

**Deliverables**: Remove 3 files, clean references

#### Tasks

1. **Delete `.github/workflows/workflow-approval-monitor.yml`**
2. **Delete `.github/workflows/squash-wait-scheduler.yml`**
3. **Delete `.github/ai-pr-loop-config.json`**
4. **Remove `pull_request_review` trigger from `ai-pr-loop.yml`** — Remove lines 8-9 (`pull_request_review: types: [submitted]`) and the entire `github.event_name == 'pull_request_review'` branch from
   the `if:` condition (lines 45-48)
5. **Grep for references** to deleted files and remove (workflow comments, docs, etc.)
6. **Update test files** — Remove assertions in `test_minimized_ci_workflows.py` referencing `WORKFLOW_APPROVAL_MONITOR`, update `test_agent_session_monitor.py` to reflect new permissions

---

### Phase 3: Enhanced Workflow (`agent-session-monitor.yml`)

**Deliverables**: Rewritten workflow with dual-source detection, comment-based dedup, review polling, round-robin batching

#### Tasks

1. **Update permissions** — Change `issues: read` → `issues: write`, `pull-requests: read` → `pull-requests: write`
2. **Remove `actions/cache` steps** — Delete restore/save cache steps entirely
3. **Add `gh agent-task list` detection** — Query per-PR with `--json id,status,pullRequestNumber,createdAt`
4. **Add Reviews API polling** — Query `gh api /repos/$OWNER/$REPO/pulls/$PR/reviews` for Copilot bot reviews on current head SHA
5. **Add tracker comment read/write** — Search PR comments for tracker marker, parse existing, merge new, render, upsert
6. **Implement round-robin batching** — Use `AGENT_MONITOR_MAX_PRS_PER_CYCLE` env var (default 50), persist cursor via cache artifact
7. **Add retry logic** — Exponential backoff (3 attempts, 2s base) for all API calls
8. **Add structured logging** — `[agent-session-monitor]` prefix for all log lines
9. **Implement graceful fallback** — If `gh agent-task list` fails, continue with events-api + reviews-api only
10. **Check PR state before dispatch** — Skip closed/merged PRs
11. **Increase `timeout-minutes`** — From 2 to 6 (to accommodate larger batches with retries)

---

### Phase 4: Test Updates

**Deliverables**: Updated workflow tests reflecting new architecture

#### Tasks

1. **Update `tests/workflows/test_agent_session_monitor.py`**:
   - Remove `test_has_required_permissions` assertion for `issues: read` → assert `issues: write`
   - Remove `test_has_required_permissions` assertion for `pull-requests: read` → assert `pull-requests: write`
   - Remove any cache-related assertions
   - Add test for tracker comment format expectation
   - Add test for `AGENT_MONITOR_MAX_PRS_PER_CYCLE` env var presence
   - Add test for dual-source detection logic (agent-task + events-api + reviews-api)
2. **Update `tests/workflows/test_minimized_ci_workflows.py`**:
   - Remove `WORKFLOW_APPROVAL_MONITOR` reference and any test that asserts its existence
   - Remove `pull_request_review` trigger assertion from ai-pr-loop tests
   - Add assertion that `pull_request_review` is NOT in ai-pr-loop triggers
3. **Add tracker sub-package unit tests** under `tests/unit/cli/ci/tracker/`:
   - `test_trackedsession.py`, `test_trackercomment.py`, `test_detectionsource.py`
   - `test_parse_tracker_comment.py`, `test_render_tracker_comment.py`
   - `test_merge_sessions.py`, `test_deduplicate_sessions.py`
   - `test_correlate_by_task_id.py`, `test_correlate_by_timestamp.py`
   - `test_truncate_sessions.py`, `test_determine_new_sessions.py`
   - `test_is_review_completion.py`

---

### Phase 5: Integration Validation

**Deliverables**: End-to-end verification, documentation update

#### Tasks

1. **Manual integration test** — Trigger workflow on test PR with known agent sessions
2. **Verify dispatch** — Confirm `ai-pr-loop` receives `workflow_dispatch` without approval gate
3. **Verify dedup** — Run monitor twice, confirm no duplicate dispatches
4. **Update `CHANGELOG.md`** — Document breaking changes (removed triggers, deleted files)
5. **Update workflow comments** — Ensure FR traceability comments reference new FR numbers

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `gh agent-task list` unavailable in some environments | Medium | Medium | Graceful fallback to events-api only (FR-009) |
| Tracker comment accidentally deleted | Low | Low | Auto-recreate on next cycle; accept history loss |
| Rate limiting with many open PRs | Medium | High | Round-robin batching, configurable batch size (NFR-001) |
| Race condition on concurrent comment updates | Low | Medium | Atomic compute-then-write pattern; last-writer-wins is acceptable |
| Removing `pull_request_review` trigger breaks existing flows | Low | High | Reviews API polling provides equivalent detection without approval gate |

## Dependencies

**Internal**:

- `agentic_devtools/cli/ci/models.py` — Existing `COPILOT_SESSION_EVENT_*` constants
- `agentic_devtools/cli/ci/pipeline/session_detector.py` — Existing detection patterns (reference, not dependency)
- `agentic_devtools/cli/ci/guards.py` — `LABEL_SKIP_ENTIRELY` constant for PR filtering

**External**:

- `gh` CLI ≥ 2.40 (for `agent-task list` subcommand)
- GitHub REST API v3 (issues events, PR reviews, comments)
- GitHub GraphQL API (PR listing with pagination)
- `AGDT_PR_APPROVER_PAT` secret (for `workflow_dispatch` without approval)

---
*Generated by Copilot SDK (claude-opus-4.6)*
