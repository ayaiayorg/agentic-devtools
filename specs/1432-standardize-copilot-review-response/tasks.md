# Tasks: Standardize Copilot Review PR Response Process

## Phase Mapping: Plan → Tasks

| Tasks Phase | Plan Phase(s) | Description |
|---|---|---|
| Phase 1: Setup & Scaffolding | — | Project scaffolding and test directory creation (no direct plan equivalent) |
| Phase 2: Foundational | Phase 6: Orchestrator Integration | Data models and shared utilities needed by all modules |
| Phase 3: US1 — Automated AI Session Trigger | Plan Phases 1, 2, 3 | Template rendering (Plan P1), trigger posting + dedup (Plan P2), result polling (Plan P3) |
| Phase 4: US2 — Automatic Thread Resolution | Plan Phase 4 | Thread resolution orchestration |
| Phase 5: US3 — Commit Squash | Plan Phase 5 | Commit squash and force-push with message generation |
| Phase 6: US4 — Template-Driven Formatting | Plan Phase 1 (refinement) | Detailed template content verification |
| Phase 7: US5 — Platform-Agnostic Code | Cross-cutting | Verifies provider abstraction usage across all modules |
| Phase 8: US6 — Deduplication | Plan Phase 2 (refinement) | Cycle boundary detection for dedup markers |
| Phase 9: Orchestrator Integration | Plan Phase 6 | Extends orchestrator state machine with new response path |
| Final Phase: Polish | Plan Phase 7 | Integration tests, validation, and documentation |

## Phase 1: Setup & Scaffolding

- [ ] T001 Create `agentic_devtools/prompts/ci/pr_review_process.md` template file with `@copilot` prefix, `{{suppressed_comments}}` placeholder, and `{{check_links}}` section
  (no dedup marker — the renderer handles marker injection)
- [ ] T002 Create `agentic_devtools/prompts/ci/ci_review_process.md` template file with `@copilot` prefix and `{{check_links}}` with failing check run URLs and logs
  (no dedup marker — the renderer handles marker injection)
- [ ] T003 Create `agentic_devtools/cli/ci/templates.py` module with `select_template()` and `render_trigger_comment()` functions
- [ ] T004 Create `agentic_devtools/cli/ci/trigger.py` module with `post_trigger_comment()` and `is_duplicate_trigger()` functions
- [ ] T005 Create `agentic_devtools/cli/ci/result_poller.py` module with `poll_for_result_comment()`, `post_result_comment()`, and `post_timeout_failure()` functions
- [ ] T006 Create `agentic_devtools/cli/ci/thread_resolver.py` module with `resolve_copilot_review_threads()` function
- [ ] T007 Create `agentic_devtools/cli/ci/squash.py` module with `squash_and_force_push()`, `generate_commit_message()`, and `_local_fallback_message()` functions
- [ ] T008 Create test directory structure with `__init__.py` files for `tests/unit/cli/ci/templates/`, `tests/unit/cli/ci/trigger/`, `tests/unit/cli/ci/result_poller/`,
  `tests/unit/cli/ci/thread_resolver/`, `tests/unit/cli/ci/squash/`, `tests/unit/cli/ci/models/`, `tests/unit/cli/ci/retry/`, `tests/unit/cli/ci/github_provider/`

## Phase 2: Foundational — Data Models & Shared Utilities

- [ ] T009 Add `CopilotReviewContext` dataclass to `agentic_devtools/cli/ci/models.py` with fields: `review_id`, `pr_number`, `head_sha`, `suppressed_comments`, `check_run_urls`,
  `repository_full_name`
- [ ] T010 Add constants to `agentic_devtools/cli/ci/models.py`: `TRIGGER_MARKER_PREFIX = "<!-- copilot-trigger:"`, `RESULT_SENTINEL = "<!-- copilot-agent-result -->"`, `RESULT_AUTHOR =
  "github-actions[bot]"`, `POLL_INTERVAL_SECONDS = 30`, `POLL_TIMEOUT_SECONDS = 900`
- [ ] T011 Create `tests/unit/cli/ci/models/test_copilotreviewcontext.py` for `CopilotReviewContext` dataclass validation
- [ ] T012 Export new modules from `agentic_devtools/cli/ci/__init__.py`: `templates`, `trigger`, `result_poller`, `thread_resolver`, `squash`
- [ ] T013 Add `list_review_comments(pr_number: int, review_id: int) -> list[ReviewComment]` abstract method to `CIPlatformProvider` in `agentic_devtools/cli/ci/provider.py` —
  returns comment bodies for a specific review (needed by T060 for `{{suppressed_comments}}` population)
- [ ] T014 Add `ReviewComment` dataclass to `agentic_devtools/cli/ci/models.py` with fields: `id`, `body`, `path`, `line`, `author`
- [ ] T015 Create `tests/unit/cli/ci/models/test_reviewcomment.py` for `ReviewComment` dataclass validation
- [ ] T016 Add `get_workflow_run_status(run_id: int) -> WorkflowRunStatus` abstract method to `CIPlatformProvider` — returns current status of a CI workflow run
  (needed by `await_copilot_session()` in T040)
- [ ] T017 Add `get_workflow_run_logs(run_id: int, job_name: str) -> str` abstract method to `CIPlatformProvider` — returns log output for a specific job in a workflow run
  (needed by `await_copilot_session()` in T040 to extract session output)
- [ ] T018 Add `WorkflowRunStatus` dataclass to `agentic_devtools/cli/ci/models.py` with fields: `run_id`, `status`, `conclusion`, `jobs` (list of job summaries)
- [ ] T019 Create `tests/unit/cli/ci/models/test_workflowrunstatus.py` for `WorkflowRunStatus` dataclass validation
- [ ] T020 Implement `list_review_comments()`, `get_workflow_run_status()`, and `get_workflow_run_logs()` in `GitHubActionsProvider` (`agentic_devtools/cli/ci/github_provider.py`)
- [ ] T021 Create `tests/unit/cli/ci/github_provider/test_list_review_comments.py` for `GitHubActionsProvider.list_review_comments()` method validation
- [ ] T022 Create `tests/unit/cli/ci/github_provider/test_get_workflow_run_status.py` for `GitHubActionsProvider.get_workflow_run_status()` method validation
- [ ] T023 Create `tests/unit/cli/ci/github_provider/test_get_workflow_run_logs.py` for `GitHubActionsProvider.get_workflow_run_logs()` method validation
- [ ] T024 Add `NotImplementedError` stubs for `list_review_comments()`, `get_workflow_run_status()`, and `get_workflow_run_logs()` in `AzureDevOpsProvider`
  (`agentic_devtools/cli/ci/ado_provider.py`) to keep the concrete subclass instantiable

## Phase 3: User Story 1 — Automated AI Session Trigger (P1)

- [ ] T025 [US1] Write tests `tests/unit/cli/ci/templates/test_select_template.py` — verify `pr_review_process.md` selected when suppressed comments exist (FR-003, FR-015), `ci_review_process.md`
  selected when no suppressed comments (FR-004, FR-015)
- [ ] T026 [P] [US1] Write tests `tests/unit/cli/ci/templates/test_render_trigger_comment.py` — verify rendered output starts with `@copilot` (FR-006), includes check links (FR-005), includes dedup
  marker after prefix line
- [ ] T027 [US1] Implement `select_template()` in `agentic_devtools/cli/ci/templates.py` — load template via `agentic_devtools.prompts.loader.load_ci_template()` based on presence of suppressed
  comments (FR-003, FR-004, FR-015)
- [ ] T028 [US1] Implement `render_trigger_comment()` in `agentic_devtools/cli/ci/templates.py` — substitute variables, ensure `@copilot` at start (FR-006),
  **solely responsible** for injecting the `<!-- copilot-trigger:REVIEW_ID -->` dedup marker after the prefix line (templates must NOT contain this marker),
  include failing check links and logs (FR-005)
- [ ] T029 [US1] Write tests `tests/unit/cli/ci/trigger/test_is_duplicate_trigger.py` — verify detection of `<!-- copilot-trigger:REVIEW_ID -->` marker (FR-012)
- [ ] T030 [US1] Write tests `tests/unit/cli/ci/trigger/test_post_trigger_comment.py` — verify comment posted only when both Copilot review AND checks completed (FR-001, FR-002), verify dedup prevents
  duplicate for same review cycle (FR-012), verify PAT authentication used
- [ ] T031 [US1] Implement `is_duplicate_trigger()` in `agentic_devtools/cli/ci/trigger.py` — search existing PR comments for `<!-- copilot-trigger:REVIEW_ID -->` marker using provider's
  `find_comment()` (FR-012)
- [ ] T032 [US1] Implement `post_trigger_comment()` in `agentic_devtools/cli/ci/trigger.py` — enforce both conditions (FR-001, FR-002), call `is_duplicate_trigger()` (FR-012), render comment via
  templates, ensure `@copilot` at start (FR-006), post via PAT-authenticated provider
- [ ] T033 [US1] Write tests `tests/unit/cli/ci/result_poller/test_poll_for_result_comment.py` — verify 30s polling interval, 15min timeout, detection by `<!-- copilot-agent-result -->` sentinel
  (FR-014), secondary check for `github-actions[bot]` author (FR-014)
- [ ] T034 [US1] Write tests `tests/unit/cli/ci/result_poller/test_post_timeout_failure.py` — verify failure comment includes polling duration, review ID, workflow run link (FR-016), posted via
  GITHUB_TOKEN, exits non-zero
- [ ] T035 [US1] Implement `poll_for_result_comment()` in `agentic_devtools/cli/ci/result_poller.py` — poll PR comments at 30s intervals for 15min max, filter by `<!-- copilot-agent-result -->`
  sentinel marker primarily, confirm `github-actions[bot]` author secondarily (FR-014)
- [ ] T036 [US1] Implement `post_timeout_failure()` in `agentic_devtools/cli/ci/result_poller.py` — post failure comment via GITHUB_TOKEN with polling duration, review ID, workflow run link (FR-016),
  return non-zero exit code
- [ ] T037 [US1] Write tests `tests/unit/cli/ci/result_poller/test_post_result_comment.py` — verify result comment includes `<!-- copilot-agent-result -->` sentinel, posted via GITHUB_TOKEN as
  `github-actions[bot]`, includes extracted agent output summary
- [ ] T038 [US1] Implement `post_result_comment()` in `agentic_devtools/cli/ci/result_poller.py` — extract agent output from completed Copilot session, post PR comment via GITHUB_TOKEN containing
  `<!-- copilot-agent-result -->` sentinel marker and session summary (FR-014); must be called after the Copilot session completes and before `poll_for_result_comment()` is invoked
- [ ] T039 [US1] Write tests `tests/unit/cli/ci/result_poller/test_await_copilot_session.py` — verify polling of GitHub Actions job status for Copilot agent session completion,
  verify configurable timeout (default 15min), verify extraction of session output on completion
- [ ] T040 [US1] Implement `await_copilot_session()` in `agentic_devtools/cli/ci/result_poller.py` — poll GitHub Actions workflow run job status via
  `CIPlatformProvider.get_workflow_run_status()` (T016) to detect when the Copilot agent session completes; on completion, extract session output via
  `CIPlatformProvider.get_workflow_run_logs()` (T017) so `post_result_comment()` can include it in the sentinel comment (FR-014). This is the mechanism that bridges
  trigger posting and result comment posting in the orchestrator flow (T058)

## Phase 4: User Story 2 — Automatic Thread Resolution (P1)

- [ ] T041 [US2] Write tests `tests/unit/cli/ci/thread_resolver/test_resolve_copilot_review_threads.py` — verify replies posted to all Copilot review comments linking result comment (FR-007), verify
  all threads resolved via GraphQL API (FR-008), verify 3 retries on failure
- [ ] T042 [US2] Implement `resolve_copilot_review_threads()` in `agentic_devtools/cli/ci/thread_resolver.py` — call existing `review_reply` Python functions directly to reply to every Copilot review
  comment with link to result comment (FR-007), then call existing `resolve_review_threads` Python functions directly to resolve threads via GraphQL (FR-008), retry up to 3 times per NFR-002

## Phase 5: User Story 3 — Commit Squash with Generated Message (P1)

- [ ] T043 [US3] Write tests `tests/unit/cli/ci/squash/test_generate_commit_message.py` — verify Copilot SDK called with PR change summary and COMMIT_CONVENTION.md (FR-010), verify local fallback on
  SDK timeout/failure (FR-010)
- [ ] T044 [US3] Write tests `tests/unit/cli/ci/squash/test_local_fallback_message.py` — verify fallback generates message from PR title + commit history following COMMIT_CONVENTION.md format (FR-010)
- [ ] T045 [US3] Write tests `tests/unit/cli/ci/squash/test_squash_and_force_push.py` — verify all commits squashed into one (FR-009), verify SHA verification before push (FR-017), verify
  force-with-lease using human PAT (FR-011), verify conflict error on SHA mismatch (FR-017)
- [ ] T046 [US3] Implement `_local_fallback_message()` in `agentic_devtools/cli/ci/squash.py` — generate conventional commit message from PR title and commit history per COMMIT_CONVENTION.md (FR-010
  fallback)
- [ ] T047 [US3] Implement `generate_commit_message()` in `agentic_devtools/cli/ci/squash.py` — call Copilot SDK with PR change summary and COMMIT_CONVENTION.md conventions (FR-010), 5-minute timeout,
  fall back to `_local_fallback_message()` on failure
- [ ] T048 [US3] Implement `squash_and_force_push()` in `agentic_devtools/cli/ci/squash.py` — squash all PR commits into single commit (FR-009), use generated message, guard against head SHA
  drift before push (FR-017), execute `git push --force-with-lease` with human PAT (FR-011), fail gracefully on SHA mismatch with conflict error

## Phase 6: User Story 4 — Template-Driven Comment Formatting (P2)

- [ ] T049 [P] [US4] Extend `tests/unit/cli/ci/templates/test_render_trigger_comment.py` — add cases verifying `pr_review_process.md` template includes all suppressed comments in body when rendered
  (folded into per-symbol test for `render_trigger_comment()` per 1:1:1 policy)
- [ ] T050 [P] [US4] Extend `tests/unit/cli/ci/templates/test_render_trigger_comment.py` — add cases verifying `ci_review_process.md` template includes direct links to failing check runs
  and their logs (FR-005)
  (folded into per-symbol test for `render_trigger_comment()` per 1:1:1 policy)
- [ ] T051 [US4] Update `agentic_devtools/prompts/ci/pr_review_process.md` — ensure suppressed comments section renders all comments from current review cycle with proper formatting
- [ ] T052 [US4] Update `agentic_devtools/prompts/ci/ci_review_process.md` — ensure failing check links section renders direct URLs to check runs and log artifacts

## Phase 7: User Story 5 — Platform-Agnostic Code (P2)

- [ ] T053 [US5] Verify business logic in `agentic_devtools/cli/ci/templates.py`, `trigger.py`, `result_poller.py`, `squash.py` uses only `CIPlatformProvider` ABC methods
  (FR-013) — no direct GitHub API calls in these modules. `result_poller.py` uses `get_workflow_run_status()` and `get_workflow_run_logs()` (added in T016/T017);
  `trigger.py` uses `list_review_comments()` (added in T013). Note: `thread_resolver.py` is intentionally excluded because T042 reuses existing `review_reply` and
  `resolve_review_threads` GitHub-specific Python functions directly; adding provider methods for thread reply/resolve is deferred until a second platform is supported
- [ ] T054 [US5] Add `validate_workflow_yaml()` function to `agentic_devtools/cli/ci/templates.py` — validates that the workflow YAML contains only orchestration (job defs, step sequencing,
  secret injection) and zero business logic (FR-013, NFR-006)
- [ ] T055 [US5] Write test `tests/unit/cli/ci/templates/test_validate_workflow_yaml.py` — assert `validate_workflow_yaml()` rejects YAML with business logic and accepts orchestration-only YAML
  (maps to the `validate_workflow_yaml` source symbol per 1:1:1 policy)

## Phase 8: User Story 6 — Deduplication of Trigger Comments (P2)

- [ ] T056 [US6] Extend `tests/unit/cli/ci/trigger/test_is_duplicate_trigger.py` — add cycle boundary cases: verify new review ID triggers new comment, same review ID is blocked (FR-012)
  (merged into per-symbol test for `is_duplicate_trigger()` per 1:1:1 policy; T029 creates the file, T056 extends it)
- [ ] T057 [US6] Add review cycle ID extraction logic to `is_duplicate_trigger()` — parse `<!-- copilot-trigger:REVIEW_ID -->` from existing comments, compare against current review cycle ID (FR-012)

## Phase 9: Orchestrator Integration & Workflow

- [ ] T058 Extend `run_ai_pr_loop()` in `agentic_devtools/cli/ci/orchestrator.py` — add Copilot review response path after review evaluation:
  trigger → `await_copilot_session()` → `post_result_comment()` → `poll_for_result_comment()` → resolve → squash → force-push (FR-013)
- [ ] T059 Add auth context management to `agentic_devtools/cli/ci/orchestrator.py` — model per-operation identity boundaries:
  PAT for `@copilot` trigger (`post_trigger_comment`), GITHUB_TOKEN for result/timeout comments (`post_result_comment`, `post_timeout_failure`),
  human PAT for force-push (`squash_and_force_push`). Inject the required token/env per operation to ensure FR-014 result comments
  are posted as `github-actions[bot]` and not the PAT identity
- [ ] T060 Add `fetch_suppressed_comments()` to `agentic_devtools/cli/ci/trigger.py` — retrieve the current Copilot review's
  suppressed/minimized comment bodies via `CIPlatformProvider.list_review_comments()` (T013) so the `pr_review_process.md`
  template `{{suppressed_comments}}` placeholder can be populated with actual comment text/links (FR-003)
- [ ] T061 Write tests `tests/unit/cli/ci/trigger/test_fetch_suppressed_comments.py` — verify suppressed comment bodies are retrieved for the current review cycle,
  verify empty list returned when no suppressed comments exist
- [ ] T062 Add structured audit logging in `agentic_devtools/cli/ci/orchestrator.py` for each major step: trigger, reply, resolve, squash, force-push (NFR-005)
- [ ] T063 Add `EXIT_POLL_TIMEOUT = 5` exit code constant to `agentic_devtools/cli/ci/orchestrator.py` for FR-016 timeout failure
- [ ] T064 Update `.github/workflows/ai-pr-loop.yml` — add `GITHUB_TOKEN` env var for result-posting and timeout-failure steps, verify PAT secret mapping, add concurrency group for dedup safety

## Final Phase: Polish & Cross-Cutting

- [ ] T065 Add `run_full_trigger_loop()` orchestration function to `agentic_devtools/cli/ci/trigger.py` — coordinates trigger → poll → resolve → squash → push sequence (NFR-004)
- [ ] T066 Write test `tests/unit/cli/ci/trigger/test_run_full_trigger_loop.py` — simulate full loop with mocked dependencies, verifying no duplicate side effects (NFR-004)
  (maps to the `run_full_trigger_loop` source symbol per 1:1:1 policy)
- [ ] T067 Update retry configuration in `agentic_devtools/cli/ci/retry.py` — change defaults from 5 retries / 1s initial / 60s max to 3 retries / 2s base / 16s max
  for the Copilot review response flow (NFR-002); existing callers continue using current defaults via explicit parameters
- [ ] T068 Write test `tests/unit/cli/ci/retry/test_retry_with_backoff.py` — verify retry logic: 3 retries with exponential backoff (base 2s,
  multiplier 2×, max 16s) on GitHub API failures (NFR-002)
  (moved to `retry/` source-file folder per 1:1:1 policy — tests the `retry_with_backoff` symbol)
- [ ] T069 Verify all new test files follow 1:1:1 structure — run `python scripts/validate_test_structure.py`
- [ ] T070 Run full test suite `agdt-test` + `agdt-task-wait` and verify 100% coverage for all new modules (NFR-003)
- [ ] T071 Run `bash scripts/run-pr-checks.sh` to validate all PR checks pass
- [ ] T072 Update `agentic_devtools/cli/ci/__init__.py` exports and verify `pyproject.toml` has no new entry points needed (existing `agdt-ai-pr-loop` covers the extended orchestrator)

---
*Generated by Copilot SDK (claude-opus-4.6)*
