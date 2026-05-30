# Tasks: Unified Agent Session Monitor with Comment-Based Tracking

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup — Project Scaffolding | Phase 1: Python Tracker Library | Initial scaffolding and validation for tracker work |
| Phase 2: Foundational — Data Models & Core Types | Phase 1: Python Tracker Library | Core tracker models/types before story implementation |
| Phase 3: User Story 1 — Dual-Source Session Detection | Phase 1: Python Tracker Library | US1 tracker parser/renderer/merger implementation and tests |
| Phase 4: User Story 3 — Durable Comment-Based Deduplication | Phase 1: Python Tracker Library | US3 tracker deduplication/truncation implementation and tests |
| Phase 5: User Story 2 — Copilot Review Detection Without Approval Gate | Phase 2: Dead Code Removal | Removes review trigger and adds review detection path |
| Phase 6: User Story 4 — Dead Code Removal | Phase 2: Dead Code Removal | Deletes deprecated workflows/config and updates references/tests |
| Phase 7: User Story 5 — Reusable Tracker Library Module | Phase 1 & Phase 4 | Tracker model-focused tests and library cycle validation |
| Phase 8: Enhanced Workflow Implementation | Phase 3: Enhanced Workflow | Workflow implementation changes for detection/dedup/dispatch |
| Phase 9: Test Updates for Enhanced Workflow | Phase 4: Test Updates | Workflow test updates for new behavior and trigger constraints |
| Phase 10: Polish & Cross-Cutting | Phase 5: Integration Validation | Validation, quality gates, and final cleanup tasks |

## Phase 1: Setup — Project Scaffolding

- [ ] T001 Create sub-package directory `agentic_devtools/cli/ci/tracker/__init__.py` with public API re-exports (FR-006)
- [ ] T002 Create test directory structure `tests/unit/cli/ci/tracker/` with `__init__.py` files at each level (FR-006)
- [ ] T003 Verify existing `cli/ci/models.py` constants (`COPILOT_SESSION_EVENT_*`) and `cli/ci/retry.py` for reuse in tracker (FR-006)

## Phase 2: Foundational — Data Models & Core Types

- [ ] T004 Create `agentic_devtools/cli/ci/tracker/models.py` — Define `DetectionSource` enum with values `AGENT_TASK`, `EVENTS_API`, `REVIEWS_API` (FR-006)
- [ ] T005 Add `TrackedSession` dataclass to `models.py` — fields: `session_id`, `sources` (list of DetectionSource), `status`, `detected_at`, `dispatch_run_url`, `pr_number`, `correlation_id`
  (FR-006)
- [ ] T006 Add `TrackerComment` dataclass to `models.py` — fields: `comment_id`, `pr_number`, `last_checked`, `sessions` (list of TrackedSession), `raw_body` (FR-006, FR-007)

## Phase 3: User Story 1 — Dual-Source Session Detection [P1]

- [ ] T007 [P] [US1] Write failing tests for `parser.py` — `tests/unit/cli/ci/tracker/parser/test_parse_tracker_comment.py` covering valid markdown, empty comment, missing fields, malformed HTML
  header (FR-007)
- [ ] T008 [P] [US1] Write failing tests for `renderer.py` — `tests/unit/cli/ci/tracker/renderer/test_render_tracker_comment.py` covering basic render, multi-source sessions, sorted output, HTML
  comment metadata with `last_checked` (FR-007)
- [ ] T009 [P] [US1] Write failing tests for `merger.py` — `tests/unit/cli/ci/tracker/merger/test_merge_sessions.py` covering deduplication by task ID, timestamp fallback correlation (FR-010)
- [ ] T010 [US1] Create `agentic_devtools/cli/ci/tracker/parser.py` — Implement `parse_tracker_comment(body: str) -> TrackerComment` parsing HTML comment header and markdown table (FR-007)
- [ ] T011 [US1] Create `agentic_devtools/cli/ci/tracker/renderer.py` — Implement `render_tracker_comment(comment: TrackerComment) -> str` producing documented markdown format with HTML comment header
  containing `last_checked` timestamp, heading, and table (FR-007)
- [ ] T012 [US1] Create `agentic_devtools/cli/ci/tracker/merger.py` — Implement `merge_sessions(existing, new_agent_task, new_events_api, new_reviews_api) -> MergeResult` with two-tier correlation:
  exact task ID primary, timestamp-window fallback (FR-010)
- [ ] T013 [US1] Add `determine_new_sessions(existing: list[TrackedSession], merged: list[TrackedSession]) -> list[TrackedSession]` to `merger.py` — Returns sessions requiring dispatch (FR-002)
- [ ] T014 [P] [US1] Write failing tests for parser/renderer round-trip losslessness — `tests/unit/cli/ci/tracker/parser/test_parse_render_roundtrip.py` (FR-007)
- [ ] T015 [US1] Add `is_review_completion(session: TrackedSession) -> bool` function to `merger.py` — Distinguishes review completions from coding sessions based on source metadata (FR-012)
- [ ] T016 [P] [US1] Write tests for `is_review_completion` — `tests/unit/cli/ci/tracker/merger/test_is_review_completion.py` (FR-012)
- [ ] T017 [P] [US1] Write tests for correlation by task ID — `tests/unit/cli/ci/tracker/merger/test_correlate_by_task_id.py` verifying exact ID match as primary strategy (FR-010)
- [ ] T018 [P] [US1] Write tests for correlation by timestamp fallback — `tests/unit/cli/ci/tracker/merger/test_correlate_by_timestamp.py` verifying 60-second tolerance window (FR-010)

## Phase 4: User Story 3 — Durable Comment-Based Deduplication [P1]

- [ ] T019 [P] [US3] Write failing tests for truncation logic — `tests/unit/cli/ci/tracker/renderer/test_truncate_sessions.py` covering 32K char limit, preserving running + 20 most recent completed
  (NFR-004, FR-002)
- [ ] T020 [US3] Implement truncation in `renderer.py` — `truncate_sessions(sessions: list[TrackedSession]) -> list[TrackedSession]` preserving all running sessions and 20 most recent completed when
  rendered body exceeds 32,000 chars (NFR-004)
- [ ] T021 [P] [US3] Write failing tests for `determine_new_sessions` — `tests/unit/cli/ci/tracker/merger/test_determine_new_sessions.py` verifying cold-start reconstruction from existing comment
  (FR-002)
- [ ] T022 [US3] Write tests for concurrent update handling — `tests/unit/cli/ci/tracker/merger/test_concurrent_merge.py` verifying last-writer-wins produces valid state (FR-002)
- [ ] T023 [US3] Update `tracker/__init__.py` to re-export full public API: `parse_tracker_comment`, `render_tracker_comment`, `merge_sessions`, `determine_new_sessions`, `truncate_sessions`,
  `is_review_completion`, `TrackedSession`, `TrackerComment`, `DetectionSource` (FR-006)

## Phase 5: User Story 2 — Copilot Review Detection Without Approval Gate [P1]

- [ ] T024 [US2] Remove `pull_request_review` trigger (lines 8-9) from `.github/workflows/ai-pr-loop.yml` (FR-004)
- [ ] T025 [US2] Remove `github.event_name == 'pull_request_review'` branch from the job `if:` condition in `.github/workflows/ai-pr-loop.yml` (FR-004)
- [ ] T026 [US2] Add Reviews API detection step to `.github/workflows/agent-session-monitor.yml` — Poll `gh api /repos/$OWNER/$REPO/pulls/$PR/reviews` for Copilot bot reviews on current head SHA
  (FR-004)
- [ ] T027 [P] [US2] Write test asserting `pull_request_review` is NOT in `ai-pr-loop.yml` triggers — update `tests/workflows/test_minimized_ci_workflows.py` (FR-004, FR-011)

## Phase 6: User Story 4 — Dead Code Removal [P2]

- [ ] T028 [P] [US4] Delete `.github/workflows/workflow-approval-monitor.yml` (FR-005)
- [ ] T029 [P] [US4] Delete `.github/workflows/squash-wait-scheduler.yml` (FR-005)
- [ ] T030 [P] [US4] Delete `.github/ai-pr-loop-config.json` (FR-005)
- [ ] T031 [US4] Grep repository for references to deleted files and remove all references from workflows, scripts, docs, and configuration (FR-005)
- [ ] T032 [US4] Update `tests/workflows/test_minimized_ci_workflows.py` — Remove `WORKFLOW_APPROVAL_MONITOR` references and assertions for deleted workflows (FR-005, FR-011)
- [ ] T033 [US4] Update `tests/workflows/test_agent_session_monitor.py` — Remove cache-based deduplication assertions and old read-only permission assertions (FR-005, FR-011)

## Phase 7: User Story 5 — Reusable Tracker Library Module [P2]

- [ ] T034 [P] [US5] Write failing tests for `DetectionSource` enum — `tests/unit/cli/ci/tracker/models/test_detectionsource.py` verifying values and string rendering (FR-006)
- [ ] T035 [P] [US5] Write failing tests for `TrackedSession` — `tests/unit/cli/ci/tracker/models/test_trackedsession.py` verifying field defaults, serialization (FR-006)
- [ ] T036 [P] [US5] Write failing tests for `TrackerComment` — `tests/unit/cli/ci/tracker/models/test_trackercomment.py` verifying construction, session list management (FR-006)
- [ ] T037 [US5] Add serialization/deserialization methods to `TrackedSession` and `TrackerComment` in `models.py` for JSON interchange
- [ ] T038 [US5] Write integration-level tests verifying full workflow: parse → merge → determine_new → render cycle — `tests/unit/cli/ci/tracker/test_full_cycle.py` (FR-006)

## Phase 8: Enhanced Workflow Implementation [US1, US2, US3]

- [ ] T039 [US1] Update permissions in `.github/workflows/agent-session-monitor.yml` — Change `issues: read` → `issues: write`, `pull-requests: read` → `pull-requests: write` (FR-008)
- [ ] T040 [US3] Remove session-deduplication `actions/cache` steps from `.github/workflows/agent-session-monitor.yml` — Replace deduplication cache reads/writes with comment-based deduplication;
  preserve any cache steps used for non-deduplication state (e.g., the round-robin cursor persisted by T047) (FR-002)
- [ ] T041 [US1] Add `gh agent-task list` detection step to workflow — Query per-PR with `--json id,status,pullRequestNumber,createdAt` (FR-001)
- [ ] T042 [US1] Add events API detection step to workflow — Query issue events for `copilot_work_finished` / `copilot_work_finished_failure` events (FR-001)
- [ ] T043 [US3] Add tracker comment read/write step — Search PR comments for tracker marker, parse existing, merge new sessions, render, upsert via single API call (FR-002, FR-007)
- [ ] T044 [US1] Implement `workflow_dispatch` trigger for new sessions — Dispatch `ai-pr-loop.yml` via PAT for each newly detected session (FR-003)
- [ ] T045 [US1] Add PR state check before dispatch — Skip closed/merged PRs
- [ ] T046 [US1] Implement graceful fallback — If `gh agent-task list` fails, continue with events-api + reviews-api only, log warning (FR-009)
- [ ] T047 [US3] Implement round-robin batching — Add `AGENT_MONITOR_MAX_PRS_PER_CYCLE` env var (default 50), persist cursor via cache artifact (NFR-001)
- [ ] T048 [US1] Add retry logic with exponential backoff — 3 attempts, 2-second base delay for all API calls (NFR-005)
- [ ] T049 [US1] Add structured logging — `[agent-session-monitor]` prefix for all significant operations (NFR-006)
- [ ] T050 [US1] Increase workflow `timeout-minutes` from 2 to 6

## Phase 9: Test Updates for Enhanced Workflow

- [ ] T051 [US1] Update `tests/workflows/test_agent_session_monitor.py` — Assert `issues: write` and `pull-requests: write` permissions (FR-008, FR-011)
- [ ] T052 [US3] Add test for `AGENT_MONITOR_MAX_PRS_PER_CYCLE` env var presence in workflow — `tests/workflows/test_agent_session_monitor.py` (FR-011)
- [ ] T053 [US1] Add test asserting dual-source detection structure (agent-task + events-api + reviews-api steps) in workflow YAML, including graceful fallback coverage (FR-001, FR-009, FR-011)
- [ ] T054 [US3] Add test asserting no `actions/cache` steps remain in `agent-session-monitor.yml` (FR-002, FR-011)
- [ ] T055 [US2] Add test asserting workflow only has `schedule` and `workflow_dispatch` triggers (no `pull_request_review`) (FR-003, FR-004, FR-011)

## Phase 10: Polish & Cross-Cutting

- [ ] T056 Run full test suite with `agdt-test` and verify 100% branch coverage on `agentic_devtools/cli/ci/tracker/` (NFR-003, SC-005, FR-006)
- [ ] T057 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 compliance for all new test files (FR-006)
- [ ] T058 Run `ruff check` and `ruff format` on all new/modified files
- [ ] T059 Run `mypy` type checking on `agentic_devtools/cli/ci/tracker/`
- [ ] T060 Update `CHANGELOG.md` — Document removed triggers, deleted files, new tracker sub-package, breaking changes
- [ ] T061 Verify no remaining references to deleted files via `grep -r "workflow-approval-monitor\|squash-wait-scheduler\|ai-pr-loop-config" .github/ agentic_devtools/ tests/` (FR-005)
- [ ] T062 Run `bash scripts/targeted-checks.sh` to validate all pre-push checks pass (FR-006)

## Dependencies

```text
T001 → T004, T005, T006
T002 → T007, T008, T009, T014, T016, T017, T018, T019, T021, T034, T035, T036
T004, T005, T006 → T010, T011, T012
T010 → T012, T013, T014
T011 → T012, T014, T020
T012 → T013, T015, T017, T018
T013 → T021, T022
T020 → T023
T023 → T038
T024, T025 → T027
T028, T029, T030 → T031
T031 → T032, T033
T039-T050 → T051-T055
T051-T055 → T056
T056 → T057, T058, T059, T060, T061, T062
```

## FR Traceability Matrix

| FR | Tasks |
|---|---|
| FR-001 | T041, T042, T053 |
| FR-002 | T013, T019, T021, T022, T040, T043, T054 |
| FR-003 | T044, T055 |
| FR-004 | T024, T025, T026, T027, T055 |
| FR-005 | T028, T029, T030, T031, T032, T033, T061 |
| FR-006 | T001, T002, T003, T004, T005, T006, T010, T011, T012, T023, T034, T035, T036, T038, T056, T057, T062 |
| FR-007 | T006, T007, T008, T010, T011, T014, T043 |
| FR-008 | T039, T051 |
| FR-009 | T046, T053 |
| FR-010 | T009, T012, T017, T018 |
| FR-011 | T027, T032, T033, T051, T052, T053, T054, T055 |
| FR-012 | T015, T016 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
