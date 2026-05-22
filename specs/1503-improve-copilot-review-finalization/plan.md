# Implementation Plan: Improve Copilot Review Finalization

## Technical Context

- **Language**: Python >=3.10 with type annotations
- **Key File**: `agentic_devtools/cli/ci/github_provider.py` — contains `finalize_post_repair()`
- **Abstraction**: `CIPlatformProvider` ABC in `provider.py` with concrete `GitHubActionsProvider`
- **SDK**: `copilot` package (`CopilotClient`, `SubprocessConfig`) authenticated via `COPILOT_GITHUB_TOKEN`
- **Models**: Frozen dataclasses in `cli/ci/models.py` (`ReviewInfo`, `ReviewCommentInfo`, etc.)
- **Thread Resolution**: Delegated to `cli/github/resolve_review_threads.py` (GraphQL mutations)
- **Diff Utilities**: `cli/git/diff.py` — local `git diff` operations
- **Test Structure**: 1:1:1 under `tests/unit/cli/ci/github_provider/`
- **Existing constant**: `_ADDRESSED_REPLY_BODY = "Addressed on the updated PR branch."`

## Research Summary

See [research.md](research.md) for detailed decisions on:

- SDK prompt design for `COMMENT_RESOLVE`/`COMMENT_UNRESOLVE` verdicts
- Diff context extraction strategy (±50 lines vs full diff with 4k token budget)
- Return type change from `None` to `FinalizationResult` (backward compatibility)

## Design Overview

```text
finalize_post_repair()
  │
  ├── [1] Commit Guard (FR-001/002/014)
  │     └── Compare review.commit_sha vs HEAD → skip or proceed
  │
  ├── [2] Fetch Diff per Review (FR-003)
  │     └── git diff <review.commit_sha>..head_sha  ← keyed per review SHA
  │           (when iterating multiple reviews each may have a different commit_sha;
  │            diff is computed once per unique review.commit_sha to avoid verifying
  │            comments against the wrong change set)
  │
  ├── [3] Collect Unresolved Comments + Location Metadata (FR-009/010)
  │     └── Parse line/position/diff_hunk fields into ReviewCommentInfo for context building
  │
  ├── [4] Per-Comment SDK Verification Loop (FR-004/005/006/007/008)
  │     ├── Build VerificationPayload (comment + diff context keyed to that review's commit_sha)
  │     ├── Call Copilot SDK → VerificationVerdict
  │     ├── COMMENT_RESOLVE → reply + resolve thread
  │     └── COMMENT_UNRESOLVE / error → leave unresolved
  │
  └── [5] Build & Return FinalizationResult (FR-011/012)
```

## Implementation Phases

### Phase 1: Data Models & Result Structure (P3 — enables all phases)

**Deliverables:**

- `FinalizationResult` dataclass in `cli/ci/models.py`
- `VerificationVerdict` enum (`COMMENT_RESOLVE`, `COMMENT_UNRESOLVE`) in `cli/ci/models.py`
- `CommentResolution` dataclass (comment_id, thread_id, verdict, error)
- Extend `ReviewCommentInfo` with location metadata needed for context extraction
  (`line`, `position`, `diff_hunk`; optional for compatibility)
- Unit tests for all new models

**Files:**

- `agentic_devtools/cli/ci/models.py` — add dataclasses
- `agentic_devtools/cli/ci/github_provider.py` — parse additional review-comment metadata
- `tests/unit/cli/ci/models/test_finalizationresult.py`
- `tests/unit/cli/ci/models/test_verificationverdict.py`
- `tests/unit/cli/ci/github_provider/test_list_review_comments.py` — verify metadata parsing

### Phase 2: Commit Guard (P1 — User Story 1)

**Deliverables:**

- Guard logic at top of `finalize_post_repair()`
- Compare `review.commit_sha` (from `ReviewInfo`) to `head_sha` parameter
- Skip when equal; error-log when null/empty (FR-014)
- Return early `FinalizationResult(skipped=True, reason=...)`

**Files:**

- `agentic_devtools/cli/ci/github_provider.py` — modify `finalize_post_repair()`
- `agentic_devtools/cli/ci/provider.py` — update return type signature to `FinalizationResult`
- `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` — add guard tests

**Key Logic:**

```python
def finalize_post_repair(self, *, pr_number, base_branch, head_branch, head_sha, review_id) -> FinalizationResult:
    # Fetch review to get commit_sha
    reviews = self.list_reviews(pr_number)
    review = next((r for r in reviews if r.id == review_id), None)

    # FR-014: null/missing commit_sha → fail-safe skip
    if not review or not review.commit_sha:
        logger.error("Cannot determine review commit SHA — skipping finalization (fail-safe)")
        return FinalizationResult(skipped=True, reason="unresolvable_review_commit_sha")

    # FR-001/002: no new commit → skip
    if review.commit_sha == head_sha:
        logger.warning("No new commit since Copilot review — skipping finalization")
        return FinalizationResult(skipped=True, reason="no_new_commit")
```

### Phase 3: Diff Context Extraction (P1 — supports User Story 2)

**Deliverables:**

- `_build_verification_context()` helper method
- Line-anchored comments: ±50 lines from `git diff` around commented line when `line`/`position`
  metadata is available
- Fallback when line metadata is missing: use `diff_hunk` (or file-level diff slice) in payload so
  verification remains implementable for all comments
- PR-level comments: full diff up to 4,000-token budget with deterministic truncation
- Token estimation using character-based heuristic (4 chars ≈ 1 token)

**Files:**

- `agentic_devtools/cli/ci/github_provider.py` — new private method
- `tests/unit/cli/ci/github_provider/test_build_verification_context.py`

### Phase 4: SDK Verification Call (P1 — User Story 2 core)

**Deliverables:**

- `_verify_comment_via_sdk()` synchronous wrapper around an internal coroutine (matching
  `_generate_commit_message_via_sdk` pattern so `finalize_post_repair()` stays synchronous)
- Prompt: comment body + diff context → structured `COMMENT_RESOLVE`/`COMMENT_UNRESOLVE` response
- Parse response; treat unexpected values as `COMMENT_UNRESOLVE` (FR-005)
- Timeout/error → `COMMENT_UNRESOLVE` (FR-007/008)
- Rate-limit detection (HTTP 429) → stop loop, leave remaining unresolved (FR-008)

**Files:**

- `agentic_devtools/cli/ci/github_provider.py` — new private method
- `tests/unit/cli/ci/github_provider/test_verify_comment_via_sdk.py`

### Phase 5: Per-Comment Verification Loop (P1 — integrates Phase 2–4)

**Deliverables:**

- Refactored `finalize_post_repair()` main loop
- For each unresolved comment: check thread status (NFR-002 idempotency), build payload, call SDK, act on verdict
- Selective reply+resolve only for `COMMENT_RESOLVE` verdicts (FR-006)
- Already-resolved threads skipped silently (NFR-002)
- Accumulate results into `FinalizationResult`

**Files:**

- `agentic_devtools/cli/ci/github_provider.py` — rewrite loop body
- `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` — update/extend

### Phase 6: Multi-Review Processing (P2 — User Story 3)

**Deliverables:**

- Accept optional `review_id: int | None` (None = process all Copilot reviews)
- Iterate over all Copilot reviews (`list_reviews` filtered by `COPILOT_LOGINS`)
- Skip reviews with no unresolved comments (FR-010)
- Update `CIPlatformProvider` abstract signature
- **Update all orchestrator/call sites** that invoke `finalize_post_repair()` to pass
  `review_id=None` in scenarios where multi-review finalization is desired; call sites
  that retain an explicit `review_id` will continue finalizing only that single review

**Files:**

- `agentic_devtools/cli/ci/provider.py` — update signature
- `agentic_devtools/cli/ci/github_provider.py` — multi-review iteration
- `agentic_devtools/cli/ci/github_provider.py` — compute diff per unique `review.commit_sha`
  (cache keyed by SHA so identical SHAs across reviews share one `git diff` call)
- `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` — multi-review tests
- Orchestrator/caller modules (e.g., `cli/ci/`) — update all call sites to pass `review_id=None`
  where all-review finalization is desired

### Phase 7: Dry-Run Mode & Reporting (P3 — User Story 4)

**Deliverables:**

- `--dry-run` support reading from `is_dry_run()` state or parameter
- When dry-run: run SDK calls, classify verdicts, but skip actual resolve API calls
- `FinalizationResult` logged as structured JSON
- Return result from `finalize_post_repair()` for callers to use

**Files:**

- `agentic_devtools/cli/ci/github_provider.py` — dry-run conditional
- `tests/unit/cli/ci/github_provider/test_finalize_post_repair.py` — dry-run tests

### Phase 8: Integration & Regression Validation

**Deliverables:**

- Update all callers of `finalize_post_repair()` to handle new `FinalizationResult` return type
- **Orchestrator decision logic** must inspect `FinalizationResult.skipped`: do **not** record
  `finalized=True` or set `post_repair_soft_finalized` when `skipped=True` (e.g., no new commit
  since the Copilot review, or an unresolvable review commit SHA)
- **Orchestrator summary/reporting logic** must consume `FinalizationResult` fields
  (`resolved_count`, `unresolved_count`, `errors`) rather than treating any non-`None` return
  as unconditional success
- Ensure existing tests in `test_finalize_post_repair.py` still pass (SC-004)
- 100% coverage for new/modified code paths (SC-003)
- Run full suite: `agdt-test` + `agdt-task-wait`

## Risk Assessment

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Copilot SDK unavailable in CI | SDK calls fail → all threads left unresolved | Fail-safe default (FR-007); log warning and return gracefully |
| Token estimation inaccuracy | Context too large → SDK truncates or errors | Use conservative 4-char/token estimate; hard cap at 16,000 chars |
| Breaking change: `None` → `FinalizationResult` return type | Callers expecting old `None`/non-`None` semantics | Update call sites and orchestrator logic to branch on `FinalizationResult.skipped` and counts/errors instead of relying on truthiness |
| Rate limiting mid-loop | Partially processed reviews | FR-008: stop processing, include remaining in errors list |
| SDK latency (60s timeout per comment) | Slow finalization for many comments | Log progress; consider parallel batching in future |
| `review_id` parameter change to optional | ABC contract change | Update both providers (GitHub + ADO stub) simultaneously |

## Dependencies

- **Internal**: `copilot` SDK package (already used for commit messages)
- **Internal**: `cli/github/resolve_review_threads.py` (existing thread resolution)
- **Internal**: `cli/git/diff.py` (diff extraction utilities)
- **External**: `COPILOT_GITHUB_TOKEN` environment variable
- **External**: GitHub REST API (reviews, comments) and GraphQL API (thread resolution)

---
*Generated by Copilot SDK (claude-opus-4.6)*
