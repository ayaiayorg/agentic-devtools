# Tasks: Post-Agent Copilot Review Evaluator

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup & Scaffolding | — | Initial scaffolding and CLI registration tasks before implementation phases |
| Phase 2: Foundational — Data Models & Provider Extension | Plan Phase 1 | Review comment model extension and provider API groundwork |
| Phase 3: User Story 1 — PR State Classification | Plan Phase 1 | Classification models and classifier logic |
| Phase 4: User Story 1 (cont.) — Lock Mechanism & Snapshot Builder | Plan Phase 2, Plan Phase 3 | Lock workflow plus snapshot aggregation |
| Phase 5: User Story 2 — Verify-and-Resolve Threads | Plan Phase 4, Plan Phase 5 | Diff heuristic plus verify-and-resolve action path |
| Phase 6: User Story 3 — Synthesize Result Summary | Plan Phase 5 | Sentinel synthesis action path |
| Phase 7: User Story 4 — CLI Entry Point | Plan Phase 6 | CLI command and orchestrator integration |
| Phase 8: User Story 5 — Retry Trigger | Plan Phase 5 | Re-review trigger action |
| Phase 9: User Story 6 — Agentic Fallback | Plan Phase 5 | Agentic fallback action |
| Phase 10: Polish & Cross-Cutting | Plan Phase 7 | End-to-end checks, docs, and final validation |

## Phase 1: Setup & Scaffolding

- [ ] T001 Create evaluator package directory structure with `__init__.py` files at `agentic_devtools/cli/ci/evaluator/__init__.py`
- [ ] T002 [US1] Create test directory structure with `__init__.py` files at `tests/unit/cli/ci/evaluator/` (FR-001)
- [ ] T003 Add `agdt-evaluate-post-agent-state` entry to `COMMAND_MAP` in `agentic_devtools/cli/runner.py`
- [ ] T004 Add `agdt-evaluate-post-agent-state` console script entry point in `pyproject.toml`

## Phase 2: Foundational — Data Models & Provider Extension

- [ ] T005 Extend `ReviewCommentInfo` in `agentic_devtools/cli/ci/models.py` with `start_line: int | None` and `end_line: int | None` fields (FR-008)
- [ ] T006 [US2] [P] Write unit tests for `ReviewCommentInfo` extension at `tests/unit/cli/ci/models/test_reviewcommentinfo.py` (FR-008)
- [ ] T007 Add `get_pr_diff(pr_number) → str` abstract method to `CIPlatformProvider` in `agentic_devtools/cli/ci/provider.py`
- [ ] T008 Implement `get_pr_diff` in `GitHubActionsProvider` at `agentic_devtools/cli/ci/github_provider.py` wrapping `gh pr diff`
- [ ] T009 [US2] [P] Write unit tests for `get_pr_diff` implementation at `tests/unit/cli/ci/github_provider/test_get_pr_diff.py` (FR-008)

## Phase 3: User Story 1 — PR State Classification (P1)

- [ ] T010 [US1] Write unit tests for `PostAgentSnapshot` dataclass at `tests/unit/cli/ci/evaluator/models/test_postagentsnapshot.py` (FR-001)
- [ ] T051 [US1] Write unit tests for `ThreadInfo` dataclass at `tests/unit/cli/ci/evaluator/models/test_threadinfo.py` (FR-001)
- [ ] T052 [US1] Write unit tests for `CommentInfo` dataclass at `tests/unit/cli/ci/evaluator/models/test_commentinfo.py` (FR-001)
- [ ] T011 [US1] Write unit tests for `PostAgentClassification` enum at `tests/unit/cli/ci/evaluator/models/test_postagentclassification.py` (FR-001)
- [ ] T053 [US1] Write unit tests for `PostAgentAction` enum at `tests/unit/cli/ci/evaluator/models/test_postagentaction.py` (FR-001)
- [ ] T012 [US1] Write unit tests for `EvaluationResult` dataclass at `tests/unit/cli/ci/evaluator/models/test_evaluationresult.py`
- [ ] T013 [US1] Implement `PostAgentSnapshot`, `ThreadInfo`, `CommentInfo` frozen dataclasses in `agentic_devtools/cli/ci/evaluator/models.py` (FR-001, FR-003, FR-004, FR-005)
- [ ] T014 [US1] Implement `PostAgentClassification` enum with all six variants in `agentic_devtools/cli/ci/evaluator/models.py` (FR-001)
- [ ] T015 [US1] Implement `PostAgentAction` enum and `EvaluationResult` dataclass in `agentic_devtools/cli/ci/evaluator/models.py`
- [ ] T016 [US1] Write exhaustive unit tests for `classify_post_agent_state()` covering all six classification branches at `tests/unit/cli/ci/evaluator/classifier/test_classify_post_agent_state.py`
  (FR-001, FR-002, FR-003, FR-004, FR-005, FR-014)
- [ ] T017 [US1] Implement `classify_post_agent_state(snapshot) → PostAgentClassification` pure function in `agentic_devtools/cli/ci/evaluator/classifier.py` (FR-001, FR-002, FR-003, FR-004, FR-005,
  FR-014)

## Phase 4: User Story 1 (cont.) — Lock Mechanism & Snapshot Builder

- [ ] T018 [US1] Write unit tests for lock functions at `tests/unit/cli/ci/evaluator/lock/test_acquire_lock.py` (FR-014)
- [ ] T019 [US1] [P] Write unit tests for `release_lock` at `tests/unit/cli/ci/evaluator/lock/test_release_lock.py` (FR-014)
- [ ] T020 [US1] [P] Write unit tests for `check_lock_status` at `tests/unit/cli/ci/evaluator/lock/test_check_lock_status.py` (FR-014)
- [ ] T021 [US1] Implement `acquire_lock()`, `release_lock()`, `check_lock_status()` in `agentic_devtools/cli/ci/evaluator/lock.py` with single-comment invariant (FR-014)
- [ ] T022 [US1] Write unit tests for snapshot assembly logic in `tests/unit/cli/ci/evaluator/snapshot/` (FR-001, FR-002, FR-003, FR-004, FR-005)
- [ ] T023 [US1] Implement `build_snapshot(provider, pr_number) → PostAgentSnapshot` in `agentic_devtools/cli/ci/evaluator/snapshot.py` (FR-001, FR-002, FR-003, FR-004, FR-005)
- [ ] T047 [US1] Add happy-path snapshot-to-classification case for `build_snapshot` in `tests/unit/cli/ci/evaluator/snapshot/test_build_snapshot.py` (FR-001, FR-002, FR-003, FR-004, FR-005, FR-014)

## Phase 5: User Story 2 — Verify-and-Resolve Threads (P1)

- [ ] T024 [US2] Write unit tests for `check_lines_modified()` at `tests/unit/cli/ci/evaluator/diff_heuristic/test_check_lines_modified.py` (FR-008)
- [ ] T025 [US2] [P] Write unit tests for `verify_threads()` at `tests/unit/cli/ci/evaluator/diff_heuristic/test_verify_threads.py` (FR-008)
- [ ] T026 [US2] Implement `check_lines_modified(diff_text, path, start_line, end_line) → bool` in `agentic_devtools/cli/ci/evaluator/diff_heuristic.py` (FR-008)
- [ ] T027 [US2] Implement thread-resolution analysis routine in `agentic_devtools/cli/ci/evaluator/diff_heuristic.py` (FR-008)
- [ ] T028 [US2] Write unit tests for `verify_and_resolve` action handler at `tests/unit/cli/ci/evaluator/actions/test_verify_and_resolve.py` (FR-006, FR-008, FR-009)
- [ ] T029 [US2] Implement thread resolution action handler in `agentic_devtools/cli/ci/evaluator/actions.py` using `resolve_review_threads(comment_ids=...)` (FR-006,
  FR-008, FR-009)
- [ ] T048 [US2] Add happy-path verify-and-resolve case in `tests/unit/cli/ci/evaluator/actions/test_verify_and_resolve.py` (FR-006, FR-008, FR-009)

## Phase 6: User Story 3 — Synthesize Result Summary (P1)

- [ ] T030 [US3] Write unit tests for `synthesize_sentinel` action at `tests/unit/cli/ci/evaluator/actions/test_synthesize_sentinel.py` (FR-007)
- [ ] T031 [US3] Implement `synthesize_sentinel(provider, snapshot) → EvaluationResult` in `agentic_devtools/cli/ci/evaluator/actions.py` posting sentinel marker comment (FR-007)
- [ ] T049 [US3] Add happy-path sentinel synthesis success case in `tests/unit/cli/ci/evaluator/actions/test_synthesize_sentinel.py` (FR-007)

## Phase 7: User Story 4 — CLI Entry Point (P1)

- [ ] T032 [US4] Write unit tests for `evaluate_post_agent_state_command()` at `tests/unit/cli/ci/evaluator/command/test_evaluate_post_agent_state_command.py` (FR-010, FR-011, FR-013)
- [ ] T033 [US4] Implement `evaluate_post_agent_state_command()` in `agentic_devtools/cli/ci/evaluator/command.py` with `--pr`, `--dry-run`, JSON output (FR-010, FR-011, FR-013)
- [ ] T034 [US4] Implement action dispatch map (classification → handler function) in `agentic_devtools/cli/ci/evaluator/actions.py` (FR-006)
- [ ] T035 [US4] Wire `no_action` handler for `complete` and `concurrent_evaluation_skipped` classifications in `agentic_devtools/cli/ci/evaluator/actions.py` (FR-006)
- [ ] T036 [US4] Write unit tests for orchestrator integration at `tests/unit/cli/ci/orchestrator/test_post_agent_evaluator_dispatch.py`
- [ ] T037 [US4] Add post-agent evaluator guard/handler branch in `agentic_devtools/cli/ci/orchestrator.py` `issue_comment` dispatch (FR-010)
- [ ] T050 [US4] Add happy-path CLI command and orchestrator dispatch case in `tests/unit/cli/ci/evaluator/command/test_evaluate_post_agent_state_command.py` (FR-010, FR-011, FR-013)

## Phase 8: User Story 5 — Retry Trigger (P2)

- [ ] T038 [US5] Write unit tests for `trigger_re_review` action at `tests/unit/cli/ci/evaluator/actions/test_trigger_re_review.py` (FR-009)
- [ ] T039 [US5] Implement `trigger_re_review(provider, snapshot) → EvaluationResult` calling `provider.request_reviewer` in `agentic_devtools/cli/ci/evaluator/actions.py` (FR-009)

## Phase 9: User Story 6 — Agentic Fallback (P3)

- [ ] T040 [US6] Write unit tests for `agentic_fallback` action at `tests/unit/cli/ci/evaluator/actions/test_agentic_fallback.py` (FR-012)
- [ ] T041 [US6] Implement `agentic_fallback(provider, snapshot) → EvaluationResult` calling `provider.dispatch_repair` in `agentic_devtools/cli/ci/evaluator/actions.py` (FR-012)

## Phase 10: Polish & Cross-Cutting

- [ ] T042 [US4] Add end-to-end-style snapshot→classify→act case to `tests/unit/cli/ci/evaluator/command/test_evaluate_post_agent_state_command.py` with mocked provider (FR-010, FR-011, FR-013)
- [ ] T043 [P] Update command mapping table in `.github/copilot-instructions.md` with `agdt-evaluate-post-agent-state` documentation
- [ ] T044 [P] Export public API from `agentic_devtools/cli/ci/evaluator/__init__.py`
- [ ] T045 [US4] Run full test suite validation via `agdt-test` and fix any failures (FR-010)
- [ ] T046 Run `bash scripts/run-pr-checks.sh` and fix any lint/format/structure issues

## Dependencies

| Task | Depends On |
|------|-----------|
| T003 | T001 |
| T004 | T001 |
| T006 | T005 |
| T008 | T007 |
| T009 | T008 |
| T013 | T001 |
| T014 | T013 |
| T015 | T014 |
| T016 | T002 |
| T017 | T013, T014, T015, T016 |
| T021 | T018, T019, T020 |
| T022 | T013, T002 |
| T023 | T013, T021, T008 |
| T047 | T023 |
| T026 | T024 |
| T027 | T025, T026 |
| T028 | T002, T013 |
| T029 | T027, T028, T023 |
| T048 | T029 |
| T031 | T030, T013 |
| T049 | T031 |
| T033 | T032, T017, T034 |
| T034 | T029, T031, T035 |
| T035 | T013 |
| T037 | T036, T033 |
| T050 | T037 |
| T039 | T038, T029 |
| T041 | T040 |
| T042 | T033, T039, T041 |
| T043 | T033 |
| T044 | T033 |
| T045 | T042 |
| T046 | T045 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
