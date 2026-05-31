# Implementation Plan: Suppressed Copilot Review Comments in Repair Dispatch

**Issue**: [#1653](https://github.com/ayaiayorg/agentic-devtools/issues/1653)

## 1. Technical Context

- **Language/Stack**: Python 3.10+, `gh` CLI for GitHub API, dataclasses for models
- **Key files**:
  - `agentic_devtools/cli/ci/github_provider.py` — `GitHubActionsProvider`, `list_review_comments()`, `_build_repair_comment()`, `dispatch_repair()`
  - `agentic_devtools/cli/ci/models.py` — `ReviewCommentInfo` dataclass (frozen, already has `is_suppressed` field)
  - `agentic_devtools/cli/ci/provider.py` — `CIPlatformProvider` abstract base (interface for `list_review_comments`)
  - `agentic_devtools/cli/ci/orchestrator.py` — `_dispatch_repair()` orchestration function
  - `agentic_devtools/cli/ci/pipeline/actions/dispatch_repair.py` — `DispatchRepairAction.execute()`
  - `agentic_devtools/cli/ci/pipeline/snapshot.py` — `copilot_review_inline_count` and unresolved-thread counts based on `len(list_review_comments(...))`
- **Existing support**: `_build_repair_comment()` already renders `is_suppressed=True` comments with `(suppressed comment)` label. `ReviewCommentInfo` already has `is_suppressed: bool = False`. No
  model or signature changes needed (NFR-002).

## 2. Research Summary

**Key decisions**:

1. Parse `<details>` block from review body HTML using `re` (no new dependency)
2. Add a single `GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}` API call
3. Implement `_parse_suppressed_from_review_body()` as a standalone utility in `github_provider.py`
4. Deduplication uses exact match after normalization only (no substring matching)
5. Merge suppressed comments into the existing `review_comments` list before passing to `_build_repair_comment()`

## 3. Design Overview

```text
┌──────────────────────────────┐
│ DispatchRepairAction.execute │
│   or _dispatch_repair()      │
└──────────┬───────────────────┘
           │ calls
           ▼
┌─────────────────────────────────┐
│ provider.list_review_comments() │ ← REST inline comments (existing)
└──────────┬──────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ provider._fetch_review_body()       │ ← NEW: GET .../reviews/{id}
└──────────┬──────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│ _parse_suppressed_from_review_body(body) │ ← NEW: standalone parser
└──────────┬───────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ _deduplicate_review_comments(       │ ← NEW: exact-match dedup
│   rest_comments, suppressed)        │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│ _build_repair_comment(          │ ← UNCHANGED (already handles
│   review_comments=merged_list)  │    is_suppressed=True)
└─────────────────────────────────┘
```

The integration point is inside `list_review_comments()`: after fetching REST inline comments,
fetch the review body, parse suppressed entries, deduplicate, and return the merged list.
Implementation remains in `github_provider.py` with no signature/interface changes, but behavior
is intentionally shared across existing callers (repair dispatch and snapshot counting paths).
The rollout must explicitly validate expected counting semantics where callers use
`len(list_review_comments(...))`, including `copilot_review_inline_count` and prior unresolved
thread counts in `pipeline/snapshot.py`.

## 4. Implementation Phases

### Phase 1: Standalone Suppressed-Comment Parser (FR-007, FR-002)

**Deliverable**: `_parse_suppressed_from_review_body()` function + unit tests

**File**: `agentic_devtools/cli/ci/github_provider.py`

**Function signature**:

```python
def _parse_suppressed_from_review_body(review_body: str) -> list[ReviewCommentInfo]:
```

**Logic**:

1. Use regex to find `<details>` block with summary containing "suppressed due to low confidence"
2. Parse individual entries within the block — each entry has a bold file path (`**path/to/file**`) or code-formatted path, plus comment body text
3. Create `ReviewCommentInfo` with `is_suppressed=True`, a unique negative sentinel `id`
   (e.g., `-1`, `-2`, … assigned sequentially so no two synthetic entries share an ID),
   `html_url=""`, path from parsing (or `(unknown file)` fallback)
   - Negative IDs are outside the GitHub database-ID range, making synthetic entries
     distinguishable from real ones. Downstream callers that key on `id` (for example
     `evaluator/snapshot.py` building `ThreadInfo(comment_id=rc.id)`) must add an
     explicit guard: skip thread-resolution lookup for entries where `rc.is_suppressed`
     is `True`, since those entries have no real GitHub thread to resolve.
4. Return empty list if no `<details>` block found or block is empty
5. Log warning on malformed HTML but never raise

**Tests** (1:1:1 structure): `tests/unit/cli/ci/github_provider/test__parse_suppressed_from_review_body.py`

- Valid entries with file paths (bold and code-formatted)
- Entries without file paths → `(unknown file)` marker
- Empty `<details>` block → empty list
- Malformed HTML → empty list + warning logged
- No `<details>` block → empty list
- Multiple entries in one block

### Phase 2: Review Body Fetch (FR-006)

**Deliverable**: Review body retrieval within `list_review_comments()`

**File**: `agentic_devtools/cli/ci/github_provider.py`

**Approach**: After fetching REST comments in `list_review_comments()`, add a targeted
`GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}` call to retrieve the
review object and extract `body`. This is a single additional API call. On failure,
log a warning and return only REST comments (FR-008).

### Phase 3: Deduplication Logic (FR-004)

**Deliverable**: `_deduplicate_review_comments()` function + unit tests

**File**: `agentic_devtools/cli/ci/github_provider.py`

**Function signature**:

```python
def _deduplicate_review_comments(
    rest_comments: list[ReviewCommentInfo],
    suppressed_comments: list[ReviewCommentInfo],
) -> list[ReviewCommentInfo]:
```

**Logic**:

1. Normalize paths: strip whitespace, remove one leading `/`
2. Normalize bodies: replace `\r\n` with `\n`, strip surrounding whitespace
3. Build a set of `(normalized_path, normalized_body)` from REST comments
4. For each suppressed comment, add to result only if its normalized key is not in the REST set
5. Return `rest_comments + filtered_suppressed_comments`

**Tests**: `tests/unit/cli/ci/github_provider/test__deduplicate_review_comments.py`

- No overlap → all preserved
- Exact duplicate → suppressed entry dropped, REST entry kept
- Whitespace/CRLF normalization
- Leading `/` normalization
- Partial match (substring) → both preserved (not deduplicated)

### Phase 4: Integration into `list_review_comments()` and downstream guards (FR-001, FR-005, FR-008)

**Deliverables**:

- Updated `list_review_comments()` that merges suppressed comments
- Explicit downstream guard for synthetic suppressed entries in ID-keyed evaluator flows

**Files**:

- `agentic_devtools/cli/ci/github_provider.py`
- `agentic_devtools/cli/ci/evaluator/snapshot.py`

**Changes to `list_review_comments()`**:

1. After existing REST comment fetch, call review-body fetch
2. Parse suppressed comments from body
3. Deduplicate
4. Return merged list

**Downstream guard changes**:

1. In evaluator snapshot/thread-resolution paths, skip ID-based resolution for `rc.is_suppressed`
2. Ensure synthetic negative IDs are never used as GitHub review-thread IDs

**Guard rails**:

- Wrap the entire suppressed-comment recovery in try/except; on any error, log warning and return REST-only comments (FR-008)
- When `review_id <= 0`, skip the fetch entirely (no review body to retrieve)

**Tests**: Update `tests/unit/cli/ci/github_provider/test_list_review_comments.py`

- Existing tests continue passing (FR-005)
- New test: review with both REST and suppressed comments → merged result
- New test: review body fetch fails → returns REST comments only
- New test: suppressed-only review → returns suppressed comments
- Add/extend snapshot tests under `tests/unit/cli/ci/pipeline/snapshot/` (for example a new file
  `tests/unit/cli/ci/pipeline/snapshot/test_build_pr_state_snapshot_suppressed.py`) to
  assert `copilot_review_inline_count` and unresolved-thread counting behavior with recovered
  suppressed comments.
- Add evaluator tests (1:1:1 layout under `tests/unit/cli/ci/evaluator/snapshot/`) verifying
  `is_suppressed` entries are excluded from ID-based thread-resolution lookups.

### Phase 5: Verification & Edge Cases

**Deliverable**: End-to-end validation

- Run `agdt-test` to verify full test suite passes
- Run `agdt-test-pattern tests/unit/cli/ci/github_provider/ -v` for targeted 1:1:1 coverage
- Run `bash scripts/targeted-checks.sh` for lint/format/type checks

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| HTML format changes in GitHub's `<details>` block | Medium | Medium | Fail-soft design (log warning, continue with REST comments); parser uses loose regex |
| Review body API call adds latency | Low | Low | Single API call; well within 120s NFR budget |
| Regex parser misses edge-case HTML formatting | Medium | Low | Comprehensive test fixtures; `(unknown file)` fallback; fail-soft |
| Breaking existing inline-comment behavior | Low | High | FR-005 explicitly tested; all existing tests must pass unchanged |

## 6. Dependencies

- **Internal**: `ReviewCommentInfo` dataclass (no changes needed), `_gh_api()` helper, `_build_repair_comment()` (no changes needed)
- **External**: GitHub REST API `GET /repos/{owner}/{repo}/pulls/{pr_number}/reviews/{review_id}` endpoint
- **No new Python dependencies**: Uses `re` from stdlib for HTML parsing

---
*Generated by Copilot SDK (claude-opus-4.6)*
