# Implementation Plan: ai-pr-loop Complete Should State

**Issue**: [#1509](https://github.com/ayaiayorg/agentic-devtools/issues/1509)
**Branch**: `speckit/1509/phase-3-plan`

## Technical Context

- **Stack**: Python 3.10+, GitHub Actions, Copilot SDK (`copilot` package)
- **Architecture**: Provider pattern (`CIPlatformProvider` → `GitHubActionsProvider`) + orchestrator state machine
- **Key files**:
  - `agentic_devtools/cli/ci/orchestrator.py` — main loop state machine
  - `agentic_devtools/cli/ci/github_provider.py` — GitHub API interactions + SDK calls
  - `agentic_devtools/cli/ci/retry.py` — exponential backoff decorator
  - `agentic_devtools/cli/github/resolve_review_threads.py` — GraphQL thread resolution
  - `.github/workflows/ai-pr-loop.yml` — workflow definition
- **Test pattern**: 1:1:1 under `tests/unit/cli/ci/`; 100% coverage required

## Research Summary

See [research.md](research.md) for detailed decisions on:

- SDK evaluation prompt design for thread resolution
- Three-way merge context extraction strategy
- Post-conflict test validation approach
- Workflow approval monitor architecture

## Design Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                    ai-pr-loop.yml                            │
│  (existing triggers: PR, review, comment, workflow_run)      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               orchestrator.py                                │
│  Step 9: merge_pr(…, "rebase") ← FR-003                    │
│  Pre-merge guard: commit_count == 1 ← FR-003a              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│            github_provider.py                                │
│                                                             │
│  finalize_post_repair():                                    │
│    ├── _evaluate_thread_via_sdk() ← FR-001/002 (NEW)       │
│    ├── _reply + conditional resolve                         │
│    └── (remove unconditional resolve)                       │
│                                                             │
│  _squash_and_force_push():                                  │
│    ├── _resolve_conflicted_file_content_via_sdk()           │
│    │     └── enriched with 3-way context ← FR-004/005/006  │
│    ├── _run_post_conflict_tests() ← FR-007/008 (NEW)       │
│    └── force-push                                           │
│                                                             │
│  _generate_commit_message_via_sdk():                        │
│    └── enriched prompt ← FR-009/010                         │
│                                                             │
│  squash_post_repair():                                      │
│    └── _verify_copilot_review_triggered() ← FR-011 (NEW)   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│        workflow-approval-monitor.yml (NEW)                   │
│  Trigger: schedule (*/5 * * * *) + workflow_dispatch        │
│  Job: calls agdt-workflow-approval-monitor CLI              │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  agentic_devtools/cli/ci/workflow_approval_monitor.py (NEW)  │
│  ├── load_trusted_bots() from .github/ai-pr-loop-config.json│
│  ├── find_action_required_runs()                            │
│  ├── approve_run()                                          │
│  └── monitor_command() (CLI entry point)                    │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Rebase Merge Strategy (FR-003, FR-003a) — P1

**Deliverables**: Change merge strategy from squash to rebase with pre-merge commit count guard.

**Tasks**:

1. In `orchestrator.py` Step 9 merge handling, change `"squash"` → `"rebase"`
2. Add pre-merge guard before `merge_pr()` that calls `provider.count_commits_above_merge_base()` and re-triggers squash if count > 1
3. Add exit code for "squash re-triggered" scenario
4. Update `merge_pr()` in provider to handle `"rebase"` method value
5. Unit tests: `tests/unit/cli/ci/orchestrator/test_merge_rebase_strategy.py`, `test_merge_rebase_guard.py`

**Estimated complexity**: Low — minimal code change, high-confidence refactor.

---

### Phase 2: Enriched Commit Message Generation (FR-009, FR-010) — P2

**Deliverables**: SDK prompt includes `git diff --stat` and `COMMIT_CONVENTION.md` content.

**Tasks**:

1. In `_generate_commit_message_via_sdk()`, add `diff_stat` parameter (string from `git diff --stat`)
2. Add `commit_convention` parameter (content of `COMMIT_CONVENTION.md` or empty string)
3. In `_squash_and_force_push()`, run `git diff --stat origin/{base_branch}..HEAD` and read `COMMIT_CONVENTION.md`
4. Pass both to the SDK prompt with clear section delimiters
5. Unit tests: `tests/unit/cli/ci/github_provider/test__generate_commit_message_via_sdk_enriched.py`

**Estimated complexity**: Low — prompt enrichment, no control flow changes.

---

### Phase 3: Enriched Conflict Resolution Context (FR-004, FR-005, FR-006) — P1

**Deliverables**: SDK conflict resolution prompt includes three-way merge stages, commit messages, and file-type hints.

**Tasks**:

1. Create helper `_get_three_way_context(file_path)` that extracts `:1:`, `:2:`, `:3:` content via `git show`
2. Create helper `_get_file_commit_messages(file_path, base_branch, head_branch)` that runs `git log --oneline -- <path>` for both branches
3. Create helper `_get_file_type_hint(file_path)` returning resolution hints based on extension
4. Modify `_resolve_conflicted_file_content_via_sdk()` to accept and use enriched context in the prompt
5. Update `_resolve_rebase_conflicts_via_sdk()` to gather and pass the new context
6. Unit tests: `tests/unit/cli/ci/github_provider/test__get_three_way_context.py`, `test__get_file_commit_messages.py`, `test__get_file_type_hint.py`, `test__resolve_conflicted_enriched.py`

**Estimated complexity**: Medium — new git operations + prompt restructuring.

---

### Phase 4: Post-Conflict Test Validation (FR-007, FR-008) — P2

**Deliverables**: Full test suite runs after conflict resolution; abort rebase on failure.

**Tasks**:

1. Create `_run_post_conflict_tests(timeout_seconds=300)` method in provider
2. Integrate into `_squash_and_force_push()` after successful conflict resolution and before force-push
3. On test failure: `git rebase --abort`, post warning comment on PR, return early
4. On timeout: log warning, proceed with force-push (graceful degradation per NFR-002)
5. Add `post_conflict_test_command` config (default: `scripts/run-pr-checks.sh`)
6. Unit tests: `tests/unit/cli/ci/github_provider/test__run_post_conflict_tests.py`, `test_squash_and_force_push_test_failure.py`

**Estimated complexity**: Medium — subprocess management + error handling.

---

### Phase 5: SDK-Based Thread Evaluation (FR-001, FR-002) — P1

**Deliverables**: Thread resolution evaluates each comment via SDK before resolving.

**Tasks**:

1. Create new module `agentic_devtools/cli/ci/thread_evaluator.py`:
   - `evaluate_thread(comment_body, file_diff, agent_response) → ThreadVerdict`
   - `ThreadVerdict` enum: `ADDRESSED`, `NOT_ADDRESSED`, `AMBIGUOUS`
2. Modify `finalize_post_repair()` in provider:
   - For each comment: get file diff, get agent response comment, call evaluator
   - Only resolve threads where verdict is `ADDRESSED`
   - Leave `NOT_ADDRESSED` and `AMBIGUOUS` threads open
   - Log `AMBIGUOUS` raw responses for debugging
3. Add 30-second timeout per evaluation (NFR-001); timeout → leave unresolved
4. Unit tests: `tests/unit/cli/ci/thread_evaluator/test_evaluate_thread.py`, `test_evaluate_thread_timeout.py`, `test_evaluate_thread_ambiguous.py`
5. Integration test: `tests/unit/cli/ci/github_provider/test_finalize_post_repair_conditional_resolve.py`

**Estimated complexity**: High — new SDK integration pattern + flow restructuring.

---

### Phase 6: Copilot Review Re-Trigger Verification (FR-011) — P2

**Deliverables**: Polling loop verifies Copilot review appears after force-push with fallback.

**Tasks**:

1. Create `_verify_copilot_review_triggered(pr_number, poll_interval=10, initial_timeout=60, total_timeout=120)` method
2. Integrate into `squash_post_repair()` after the `_request_copilot_review()` call
3. First window (0–60s): poll `get_copilot_review_status()` every 10s
4. If no review: call `request_copilot_review()` explicitly
5. Second window (60–120s): poll again every 10s
6. If still no review after 120s: post warning comment, exit iteration
7. Unit tests: `tests/unit/cli/ci/github_provider/test__verify_copilot_review_triggered.py`

**Estimated complexity**: Medium — polling loop with two-phase fallback.

---

### Phase 7: Workflow Approval Monitor (FR-012, FR-013) — P3

**Deliverables**: Standalone workflow + Python CLI command for auto-approving trusted bot workflow runs.

**Tasks**:

1. Create `.github/ai-pr-loop-config.json` with `trusted_bots` allow-list
2. Create `agentic_devtools/cli/ci/workflow_approval_monitor.py`:
   - `load_trusted_bots(config_path)` — reads config
   - `find_action_required_runs(owner, repo)` — queries GitHub API
   - `approve_run(owner, repo, run_id)` — POST approval with 3 retries
   - `monitor_command()` — CLI entry point
3. Create `.github/workflows/workflow-approval-monitor.yml`:
   - Trigger: `schedule` (every 5 min) + `workflow_dispatch`
   - Job: runs `agdt-workflow-approval-monitor`
4. Add entry point in `pyproject.toml`
5. Unit tests: `tests/unit/cli/ci/workflow_approval_monitor/test_load_trusted_bots.py`, `test_find_action_required_runs.py`, `test_approve_run.py`, `test_monitor_command.py`

**Estimated complexity**: Medium — new module + workflow file, but straightforward pattern.

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| SDK evaluation adds latency exceeding NFR-008 (120s budget) | High | Medium | 30s per-thread timeout; evaluate in parallel where possible |
| Rebase merge fails on PRs that somehow have >1 commit | Medium | Low | Pre-merge guard re-triggers squash; already handled by existing `count_commits_above_merge_base` |
| Three-way context extraction fails (detached HEAD, shallow clone) | Medium | Medium | Graceful fallback: proceed with existing conflict content only |
| Post-conflict tests are flaky, blocking all conflict resolutions | High | Medium | 5-min timeout with graceful degradation; proceed on timeout |
| Workflow approval monitor approves malicious runs | Critical | Low | Strict allow-list; only `action_required` state; only listed bots |
| Copilot SDK unavailable in CI environment | Medium | Low | All SDK calls have `None` return fallbacks; existing pattern |

## Dependencies

### External

- **Copilot SDK** (`copilot` package) — used for thread evaluation, conflict resolution, commit messages
- **GitHub Actions API** — workflow run approval endpoint
- **`gh` CLI** — Copilot review status, thread resolution

### Internal

- `agentic_devtools/cli/ci/retry.py` — reuse `retry_with_backoff` for all new retry logic
- `agentic_devtools/cli/github/copilot_review_status.py` — reuse `get_copilot_review_status()`
- `agentic_devtools/cli/github/request_copilot_review.py` — reuse `request_copilot_review()`
- `agentic_devtools/cli/github/resolve_review_threads.py` — modified integration (conditional resolve)

### Ordering Constraints

- Phase 1 (rebase) is independent; can be done first
- Phase 2 (commit message) is independent
- Phase 3 (conflict context) must precede Phase 4 (post-conflict tests) since tests validate resolution quality
- Phase 5 (thread evaluation) is independent but highest complexity
- Phase 6 (review re-trigger) depends on Phase 1 being in place (rebase → force-push flow)
- Phase 7 (approval monitor) is fully independent

---
*Generated by Copilot SDK (claude-opus-4.6)*
