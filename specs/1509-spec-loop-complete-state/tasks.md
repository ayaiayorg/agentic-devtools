# Tasks: ai-pr-loop Complete Should State — Event-Driven PR Lifecycle Automation

**Issue**: [#1509](https://github.com/ayaiayorg/agentic-devtools/issues/1509)

---

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup & Configuration | — | Scaffolding (no direct plan equivalent) |
| Phase 2: Foundational | — | Shared retry infrastructure (no direct plan equivalent) |
| Phase 3: User Story 2 | Plan Phase 1 | Rebase merge strategy (FR-003) |
| Phase 4: User Story 3 | Plan Phase 3 | Enriched conflict resolution context (FR-004, FR-005, FR-006) |
| Phase 5: User Story 1 | Plan Phase 5 | SDK-based thread evaluation (FR-001, FR-002) |
| Phase 6: User Story 5 | Plan Phase 2 | Commit message enrichment (FR-009, FR-010) |
| Phase 7: User Story 4 | Plan Phase 4 | Post-conflict test validation (FR-007, FR-008) |
| Phase 8: User Story 6 | Plan Phase 6 | Copilot review re-trigger verification (FR-011) |
| Phase 9: User Story 7 | Plan Phase 7 | Workflow approval monitor (FR-012, FR-013) |
| Phase 10: Polish & Cross-Cutting | — | Validation and documentation |

---

## Phase 1: Setup & Configuration

- [ ] T001 Create `.github/ai-pr-loop-config.json` with `trusted_bots` allow-list schema and initial entries
- [ ] T002 Add `agdt-workflow-approval-monitor` entry point to `pyproject.toml` under `[project.scripts]`
- [ ] T003 Create `agentic_devtools/cli/ci/thread_evaluator.py` module skeleton with `ThreadVerdict` enum (`ADDRESSED`, `NOT_ADDRESSED`, `AMBIGUOUS`)
- [ ] T004 Create `agentic_devtools/cli/ci/workflow_approval_monitor.py` module skeleton with function stubs

---

## Phase 2: Foundational — Retry & Shared Infrastructure

- [ ] T005 Verify `agentic_devtools/cli/ci/retry.py` `retry_with_backoff` supports base 2s / max 16s exponential backoff per NFR-006 (FR-014); add configuration parameters if missing
- [ ] T006 Write unit test `tests/unit/cli/ci/retry/test_retry_with_backoff_exponential.py` confirming happy-path 3 retries with exponential backoff per FR-014
- [ ] T007 [P] Create helper `_get_three_way_context(file_path)` in `agentic_devtools/cli/ci/github_provider.py` extracting `:1:`, `:2:`, `:3:` content via `git show` (FR-004)
- [ ] T008 [P] Create helper `_get_file_commit_messages(file_path, base_branch, head_branch)` in `agentic_devtools/cli/ci/github_provider.py` (FR-005)
- [ ] T009 [P] Create helper `_get_file_type_hint(file_path)` in `agentic_devtools/cli/ci/github_provider.py` returning resolution hints by extension (FR-006)

---

## Phase 3: User Story 2 — Rebase Merge Strategy (P1)

- [ ] T010 [US2] Write unit test `tests/unit/cli/ci/orchestrator/test_merge_rebase_strategy.py` verifying `merge_pr()` is called with strategy `"rebase"` (FR-003)
- [ ] T011 [US2] Write unit test `tests/unit/cli/ci/orchestrator/test_merge_rebase_guard.py` verifying squash re-trigger when `commit_count > 1` (FR-003)
- [ ] T012 [US2] Modify Step 9 merge handling in `agentic_devtools/cli/ci/orchestrator.py` to call `merge_pr(…, strategy="rebase")` instead of `"squash"` (FR-003)
- [ ] T013 [US2] Add pre-merge guard in `agentic_devtools/cli/ci/orchestrator.py` calling `count_commits_above_merge_base()` and re-triggering squash if count > 1 (FR-003)
- [ ] T014 [US2] Update `merge_pr()` in `agentic_devtools/cli/ci/github_provider.py` to pass `--rebase` to the GitHub merge API (FR-003)
- [ ] T015 [US2] Write happy-path integration test `tests/unit/cli/ci/github_provider/test_merge_pr_rebase.py` verifying rebase merge produces identical commit message on target branch (FR-003)

---

## Phase 4: User Story 3 — Enriched Conflict Resolution Context (P1)

- [ ] T016 [US3] Write unit test `tests/unit/cli/ci/github_provider/test__get_three_way_context.py` verifying extraction of `:1:`, `:2:`, `:3:` stages (FR-004)
- [ ] T017 [US3] Write unit test `tests/unit/cli/ci/github_provider/test__get_file_commit_messages.py` verifying commit messages from both branches (FR-005)
- [ ] T018 [US3] Write unit test `tests/unit/cli/ci/github_provider/test__get_file_type_hint.py` verifying JSON/Markdown/Code hints (FR-006)
- [ ] T019 [US3] Modify `_resolve_conflicted_file_content_via_sdk()` in `agentic_devtools/cli/ci/github_provider.py` to accept and include three-way context in prompt (FR-004)
- [ ] T020 [US3] Modify `_resolve_conflicted_file_content_via_sdk()` to include commit messages from both branches in prompt (FR-005)
- [ ] T021 [US3] Modify `_resolve_conflicted_file_content_via_sdk()` to include file-type-specific resolution hints in prompt (FR-006)
- [ ] T022 [US3] Update `_resolve_rebase_conflicts_via_sdk()` to gather three-way context, commit messages, and hints, passing them to the resolution method
- [ ] T023 [US3] Write happy-path integration test `tests/unit/cli/ci/github_provider/test__resolve_conflicted_enriched.py` verifying full enriched prompt assembly (FR-004, FR-005, FR-006)

---

## Phase 5: User Story 1 — SDK-Based Thread Evaluation (P1)

- [ ] T024 [US1] Write happy-path unit test `tests/unit/cli/ci/thread_evaluator/test_evaluate_thread.py` verifying `ADDRESSED`/`NOT_ADDRESSED` verdicts (FR-001)
- [ ] T025 [US1] Write happy-path unit test `tests/unit/cli/ci/thread_evaluator/test_evaluate_thread_timeout.py` covering pre-timeout success and 30s unresolved timeout behavior (FR-002, NFR-001)
- [ ] T026 [US1] Write unit test `tests/unit/cli/ci/thread_evaluator/test_evaluate_thread_ambiguous.py` verifying `AMBIGUOUS` leaves thread unresolved immediately without retry (FR-002)
- [ ] T027 [US1] Implement `evaluate_thread(comment_body, file_diff, agent_response) → ThreadVerdict` in `agentic_devtools/cli/ci/thread_evaluator.py` with 30s timeout (FR-001, FR-002, NFR-001)
- [ ] T028 [US1] Add SDK prompt construction in `evaluate_thread()` including comment body, file diff, and agent response context (FR-001)
- [ ] T029 [US1] Add structured verdict parsing logic handling `ADDRESSED`, `NOT_ADDRESSED`, `AMBIGUOUS`, and unparseable responses (FR-002)
- [ ] T030 [US1] Add retry with exponential backoff (3 retries, base 2s, max 16s) to SDK calls in thread evaluator per FR-014, NFR-006
- [ ] T031 [US1] Modify `finalize_post_repair()` in `agentic_devtools/cli/ci/github_provider.py` to call `evaluate_thread()` for each comment before resolving (FR-001)
- [ ] T032 [US1] Update `finalize_post_repair()` to only resolve threads with `ADDRESSED` verdict; leave `NOT_ADDRESSED`/`AMBIGUOUS` open (FR-002)
- [ ] T033 [US1] Add logging of raw SDK response for `AMBIGUOUS` verdicts in `finalize_post_repair()` (FR-002)
- [ ] T034 [US1] Write integration test `tests/unit/cli/ci/github_provider/test_finalize_post_repair_conditional_resolve.py` verifying conditional resolution flow (FR-001, FR-002)

---

## Phase 6: User Story 5 — Richer Commit Message Generation (P2)

- [ ] T035 [US5] Write unit test `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk_enriched.py` verifying diff stat and convention content in prompt (FR-009, FR-010)
- [ ] T036 [US5] Modify `_generate_commit_message_via_sdk()` in `agentic_devtools/cli/ci/github_provider.py` to accept `diff_stat` parameter and include in prompt (FR-009)
- [ ] T037 [US5] Modify `_generate_commit_message_via_sdk()` to accept `commit_convention` parameter and include in prompt when non-empty (FR-010)
- [ ] T038 [US5] Update `_squash_and_force_push()` to run `git diff --stat origin/{base_branch}..HEAD` and pass result to commit message generation (FR-009)
- [ ] T039 [US5] Update `_squash_and_force_push()` to read `COMMIT_CONVENTION.md` content (empty string if missing) and pass to commit message generation (FR-010)
- [ ] T040 [US5] Write test verifying graceful fallback when `COMMIT_CONVENTION.md` does not exist (FR-010)

---

## Phase 7: User Story 4 — Post-Conflict Test Validation (P2)

- [ ] T041 [US4] Write unit test `tests/unit/cli/ci/github_provider/test__run_post_conflict_tests.py` verifying pass/fail/timeout behavior (FR-007, FR-008)
- [ ] T042 [US4] Write unit test `tests/unit/cli/ci/github_provider/test_squash_and_force_push_test_failure.py` verifying rebase abort on test failure (FR-008)
- [ ] T043 [US4] Create `_run_post_conflict_tests(timeout_seconds=300)` method in `agentic_devtools/cli/ci/github_provider.py` running full test suite (FR-007, NFR-002)
- [ ] T044 [US4] Integrate `_run_post_conflict_tests()` into `_squash_and_force_push()` after successful conflict resolution and before force-push (FR-007)
- [ ] T045 [US4] Implement rebase abort logic (`git rebase --abort`) and PR warning comment on post-resolution validation failure (FR-008)
- [ ] T046 [US4] Implement 5-minute timeout with graceful degradation (proceed with force-push, log warning) per NFR-002
- [ ] T047 [US4] Add `post_conflict_test_command` config option (default: `scripts/run-pr-checks.sh`) to provider configuration (FR-007)

---

## Phase 8: User Story 6 — Copilot Review Re-Trigger Verification (P2)

- [ ] T048 [US6] Write unit test `tests/unit/cli/ci/github_provider/test__verify_copilot_review_triggered.py` covering both success and fallback paths (FR-011)
- [ ] T049 [US6] Create `_verify_copilot_review_triggered(pr_number, poll_interval=10, initial_timeout=60, total_timeout=120)` in `agentic_devtools/cli/ci/github_provider.py` (FR-011, NFR-003)
- [ ] T050 [US6] Implement first polling window (0–60s): poll `get_copilot_review_status()` every 10s (FR-011)
- [ ] T051 [US6] Implement fallback: call `request_copilot_review()` explicitly after 60s timeout (FR-011)
- [ ] T052 [US6] Implement second polling window (60–120s): poll again every 10s after fallback request (FR-011, NFR-003)
- [ ] T053 [US6] Implement 120s total timeout: post warning comment on PR and exit iteration (FR-011)
- [ ] T054 [US6] Add retry with exponential backoff to `request_copilot_review()` call per FR-014
- [ ] T055 [US6] Integrate `_verify_copilot_review_triggered()` into `squash_post_repair()` after force-push completes (FR-011)

---

## Phase 9: User Story 7 — Workflow Approval Monitor (P3)

- [ ] T056 [US7] Write unit test `tests/unit/cli/ci/workflow_approval_monitor/test_load_trusted_bots.py` (FR-013)
- [ ] T057 [US7] Write unit test `tests/unit/cli/ci/workflow_approval_monitor/test_find_action_required_runs.py` (FR-012)
- [ ] T058 [US7] Write unit test `tests/unit/cli/ci/workflow_approval_monitor/test_approve_run.py` verifying 3 retries with exponential backoff (FR-012, FR-014)
- [ ] T059 [US7] Write unit test `tests/unit/cli/ci/workflow_approval_monitor/test_monitor_command.py` verifying end-to-end flow (FR-012, FR-013)
- [ ] T060 [US7] Implement `load_trusted_bots(config_path)` reading `.github/ai-pr-loop-config.json` (FR-013)
- [ ] T061 [US7] Implement `find_action_required_runs(owner, repo)` querying GitHub Actions API for stuck runs (FR-012)
- [ ] T062 [US7] Implement `approve_run(owner, repo, run_id)` with POST approval and 3 retries with exponential backoff (FR-012, FR-014, NFR-006)
- [ ] T063 [US7] Implement `monitor_command()` CLI entry point orchestrating the full approval flow (FR-012, FR-013)
- [ ] T064 [US7] Create `.github/workflows/workflow-approval-monitor.yml` with `schedule` (every 5 min cron) and `workflow_dispatch` triggers (FR-012, NFR-004)
- [ ] T065 [US7] Wire `monitor_command` to `agdt-workflow-approval-monitor` entry point in `pyproject.toml` (FR-012)
- [ ] T066 [US7] Write test verifying only `action_required` runs are processed (skip `completed`/`in_progress`) (FR-012)
- [ ] T067 [US7] Write test verifying non-trusted actors are skipped (FR-013)

---

## Phase 10: Polish & Cross-Cutting

- [ ] T068 [P] Add `__init__.py` files for all new test directories under `tests/unit/cli/ci/thread_evaluator/` and `tests/unit/cli/ci/workflow_approval_monitor/` (FR-001, FR-012)
- [ ] T069 Run `python scripts/validate_test_structure.py` to confirm 1:1:1 compliance (FR-001)
- [ ] T070 Run `bash scripts/run-pr-checks.sh` to verify full suite passes with all changes (FR-001)
- [ ] T071 Update `.github/copilot-instructions.md` or relevant docs to document new `agdt-workflow-approval-monitor` command
- [ ] T072 Verify NFR-008 budget: thread evaluation + conflict enrichment + commit enrichment adds ≤120s worst-case (audit timeouts and parallelism) (FR-001, FR-004, FR-009)

---

## Dependency Graph

```text
T001 ─────────────────────────────────────────────────────────────→ T060
T002 ─────────────────────────────────────────────────────────────→ T065
T003 → T024–T034
T004 → T056–T067
T005 → T006 → T030, T054, T062
T007 → T016 → T019, T022
T008 → T017 → T020, T022
T009 → T018 → T021, T022
T010–T011 → T012–T014 → T015
T016–T018 → T019–T023
T024–T026 → T027–T034
T035 → T036–T040
T041–T042 → T043–T047 (depends on T022 for conflict resolution integration)
T048 → T049–T055 (depends on T012–T014 for rebase flow)
T056–T059 → T060–T067
T068 → T069 → T070
```

---

## FR Coverage Matrix

| FR | Tasks |
|----|-------|
| FR-001 | T024, T027, T028, T031 |
| FR-002 | T025, T026, T027, T029, T032, T033 |
| FR-003 | T010, T011, T012, T013, T014 |
| FR-004 | T007, T016, T019 |
| FR-005 | T008, T017, T020 |
| FR-006 | T009, T018, T021 |
| FR-007 | T041, T043, T044 |
| FR-008 | T042, T045 |
| FR-009 | T035, T036, T038 |
| FR-010 | T035, T037, T039, T040 |
| FR-011 | T048, T049, T050, T051, T052, T053, T055 |
| FR-012 | T057, T058, T061, T062, T063, T064, T065, T066 |
| FR-013 | T056, T059, T060, T063, T067 |
| FR-014 | T005, T006, T030, T054, T058, T062 |

---
*Generated by Copilot SDK (claude-opus-4.6)*
