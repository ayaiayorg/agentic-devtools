# Implementation Plan: Post-Agent Copilot Review Evaluator

## 1. Technical Context

- **Stack**: Python 3.10+, `gh` CLI for GitHub API, `agentic-devtools` pip package
- **Key Dependencies**:
  - `CIPlatformProvider` ABC in `agentic_devtools/cli/ci/provider.py`
  - `GitHubActionsProvider` in `agentic_devtools/cli/ci/github_provider.py`
  - `resolve_review_threads` in `agentic_devtools/cli/github/resolve_review_threads.py`
  - `retry_with_backoff` in `agentic_devtools/cli/ci/retry.py`
  - `run_ai_pr_loop` orchestrator in `agentic_devtools/cli/ci/orchestrator.py`
- **Architecture**: Provider-pattern with pure classification logic + injected side effects
- **CLI Pattern**: Entry points via `pyproject.toml` → `runner.run_as_script`
- **Existing Constraint**: In `run_ai_pr_loop`, the
  `_is_issue_comment_created(...)` guard returns early for `issue_comment`
  events (Step 2b). The evaluator needs a new dispatch path before that early
  return branch.

## 2. Research Summary

This plan captures the key research decisions directly, including:

- Lock mechanism implementation via PR comment
- Diff heuristic approach for thread verification
- Orchestrator integration strategy (new guard branch vs separate entry point)
- `ReviewCommentInfo` extension for line-range data

Key decisions:

1. **Standalone CLI command** (`agdt-evaluate-post-agent-state`) invoked from the orchestrator's `issue_comment` handler rather than inline in the orchestrator.
2. **Frozen dataclasses** for all domain models (immutable snapshots).
3. **Pure classification function** — zero I/O, fully unit-testable.
4. **Action handlers as a strategy map** keyed by classification enum value.

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────────┐
│  ai-pr-loop.yml (issue_comment trigger)                     │
│  → run_ai_pr_loop → _is_issue_comment_created              │
│    → NEW: detect post-agent scenario → invoke evaluator     │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  agdt-evaluate-post-agent-state (CLI entry point)           │
│  → snapshot.build_snapshot(provider, pr_number)             │
│    → classifier.classify_post_agent_state(snapshot)         │
│      → actions.dispatch(classification, provider, snapshot) │
│        → structured JSON output                             │
└─────────────────────────────────────────────────────────────┘
```

**Module layout** (new files under `agentic_devtools/cli/ci/`):

```text
agentic_devtools/cli/ci/
├── evaluator/
│   ├── __init__.py
│   ├── models.py          # PostAgentSnapshot, ThreadInfo, CommentInfo, enums, EvaluationResult
│   ├── classifier.py      # classify_post_agent_state() — pure function
│   ├── snapshot.py        # build_snapshot() — gathers data from provider
│   ├── actions.py         # Action handlers (verify_and_resolve, synthesize, etc.)
│   ├── diff_heuristic.py  # Heuristic line-range matching against HEAD diff
│   ├── lock.py            # Lock acquisition/release via comment marker
│   └── command.py         # Subcommand implementation: evaluate_post_agent_state_command()
```

## 4. Implementation Phases

### Phase 1: Data Models & Classification (FR-001, FR-002, FR-003, FR-004, FR-005, FR-014)

**Deliverables:**

- `evaluator/models.py` — `PostAgentSnapshot`, `ThreadInfo`, `CommentInfo`, `PostAgentClassification`, `PostAgentAction`, `EvaluationResult` dataclasses/enums
- `evaluator/classifier.py` — `classify_post_agent_state(snapshot) → PostAgentClassification`
- Extend `ReviewCommentInfo` in `cli/ci/models.py` with `start_line` and `end_line` fields
- Unit tests for all classification branches (100% coverage on classifier)

**Key implementation details:**

- `PostAgentClassification` enum: `agent_claims_fixed_no_sentinel`, `threads_resolved_no_sentinel`, `complete`, `changes_made_threads_unresolved`, `agent_silent`, `concurrent_evaluation_skipped`
- Classification priority: lock check first → `complete` → `threads_resolved_no_sentinel` → `agent_claims_fixed_no_sentinel` → `changes_made_threads_unresolved` → `agent_silent`

### Phase 2: Lock Mechanism (FR-014)

**Deliverables:**

- `evaluator/lock.py` — `acquire_lock()`, `release_lock()`, `check_lock_status()`
- Lock marker: `<!-- copilot-evaluator-lock -->`
- Comment body format encodes holder token from `get_dedup_writer_token()` (backed by `GITHUB_RUN_ID`/`GITHUB_RUN_ATTEMPT`, with local fallback), ISO-8601 acquisition time, and state (active/released)
- Single-comment invariant: create-or-update via `find_comment` + `update_comment`/`post_comment`
- Validate holder token before side-effect actions (skip when lock holder does not match current run)
- Keep workflow-level concurrency keyed by PR number in `ai-pr-loop.yml` as a second guard against concurrent evaluators
- Unit tests with mocked provider

### Phase 3: Snapshot Builder (FR-001–FR-005, FR-014)

**Deliverables:**

- `evaluator/snapshot.py` — `build_snapshot(provider, pr_number) → PostAgentSnapshot`
- Fetches: PR metadata, reviews, comments, threads, lock status, and unified diff via `provider.get_pr_diff(pr_number)`
- Populates all snapshot fields including `head_changed_since_review`, `lock_age_seconds`, and `diff_text`
- Uses `retry_with_backoff` via provider methods (already decorated)
- Unit tests with mocked provider

### Phase 4: Diff Heuristic (FR-008)

**Deliverables:**

- `evaluator/diff_heuristic.py` — `check_lines_modified(diff_text, path, start_line, end_line) → bool`
- Parses unified diff format to determine if specific line ranges were modified
- `verify_threads(provider, pr_number, threads, review_commit_sha) → VerificationResult`
- Diff retrieval: add `CIPlatformProvider.get_pr_diff(pr_number) → str` as a base provider method
  (default behavior raises `NotImplementedError`), and implement it in
  `GitHubActionsProvider` via `gh pr diff`; the result is stored in
  `PostAgentSnapshot.diff_text` by `build_snapshot` (Phase 3), keeping all provider I/O behind
  the provider abstraction
- Unit tests with sample diffs

### Phase 5: Action Handlers (FR-006, FR-007, FR-008, FR-009, FR-012)

**Deliverables:**

- `evaluator/actions.py`:
  - `verify_and_resolve(provider, snapshot) → EvaluationResult` — verifies
    threads via diff heuristic and resolves only verified thread comments via
    `resolve_review_threads(pr_number, repo, comment_ids=...)` (primary path)
  - `verify_and_resolve` fallback: when verified comment IDs cannot be derived, call `resolve_review_threads(pr_number, repo, review_id=...)` for the latest Copilot review
  - `synthesize_sentinel(provider, snapshot) → EvaluationResult` — posts sentinel comment
  - `trigger_re_review(provider, snapshot) → EvaluationResult` — calls `provider.request_reviewer`
  - `agentic_fallback(provider, snapshot) → EvaluationResult` — calls `provider.dispatch_repair`
  - `no_action(provider, snapshot) → EvaluationResult` — returns success immediately
- Action dispatch map: `classification → action function`
- Unit tests for each handler with mocked provider

### Phase 6: CLI Entry Point & Orchestrator Integration (FR-010, FR-011, FR-013, NFR-004, NFR-005)

**Deliverables:**

- `evaluator/command.py` — subcommand implementation `evaluate_post_agent_state_command()`
  - Reads `--pr` from CLI args or `github.pull_request_number` from state
  - Supports `--dry-run` flag
  - Outputs structured JSON to stdout
  - Updates state keys: `evaluator.classification`, `evaluator.action_taken`, `evaluator.success`
- Console entry point in `pyproject.toml`: `agdt-evaluate-post-agent-state = "agentic_devtools.cli.runner:run_as_script"`
- Runner dispatch mapping in `cli/runner.py`: `COMMAND_MAP["agdt-evaluate-post-agent-state"] = ("agentic_devtools.cli.ci.evaluator.command", "evaluate_post_agent_state_command")`
- Orchestrator integration: modify the `issue_comment` handler in `orchestrator.py` to detect post-agent scenarios and invoke evaluator
- Unit tests under `tests/unit/cli/ci/evaluator/` following 1:1:1 policy (one test file per symbol in each evaluator module)

### Phase 7: End-to-End Testing & Documentation

**Deliverables:**

- Full snapshot→classify→act flow test under `tests/unit/cli/ci/evaluator/` following 1:1:1 policy (mocked provider)
- Update `copilot-instructions.md` with new command documentation
- Update command mapping table
- Validate all tests pass via `agdt-test`

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `ReviewCommentInfo` extension breaks existing tests | Medium | Medium | Add fields with `None` default; backward compatible |
| Orchestrator `issue_comment` early-return conflicts | High | High | Add evaluator dispatch BEFORE the existing early return, with its own guard conditions |
| Lock race condition (two evaluators check simultaneously) | Low | Medium | Use dual guard: workflow `concurrency` keyed by PR + lock holder token validation before side effects |
| Diff heuristic false positives (lines modified but feedback not addressed) | Medium | Low | Documented as proxy signal; re-review cycle catches remaining issues |
| GitHub API rate limiting during thread resolution | Low | Medium | Existing `retry_with_backoff` handles; partial success reported in `EvaluationResult` |

## 6. Dependencies

**Internal:**

- `CIPlatformProvider.find_comment` — already exists
- `CIPlatformProvider.update_comment` — already exists
- `CIPlatformProvider.post_comment` — already exists
- `CIPlatformProvider.request_reviewer` — already exists
- `CIPlatformProvider.dispatch_repair` — already exists
- `CIPlatformProvider.list_review_comments` — already exists
- `get_dedup_writer_token()` — already exists (uses `GITHUB_RUN_ID`/`GITHUB_RUN_ATTEMPT` with local fallback)
- `CIPlatformProvider.get_pr_diff` — new base method to add (default raises `NotImplementedError`; `GitHubActionsProvider` wraps `gh pr diff` and returns unified diff as string)
- `resolve_review_threads(pr_number, repo, review_id | comment_ids)` — already exists (requires `pr_number` and `repo`, plus either `review_id` or `comment_ids`)
- `retry_with_backoff` decorator — already exists

**External:**

- `gh` CLI for GitHub API access
- GitHub REST API (reviews, comments, pulls endpoints)
- GitHub GraphQL API (thread resolution via existing `resolve_review_threads`)

**No new pip dependencies required.**

---
*Generated by Copilot SDK (claude-opus-4.6)*
