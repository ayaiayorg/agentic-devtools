# Implementation Plan: Shared Review Threads Across Identities

## Technical Context

- **Language**: Python 3.10+ with dataclass-based models
- **Package**: `agentic_devtools` (pip-installable CLI)
- **Key modules**:
  - `agentic_devtools/cli/azure_devops/marker.py` — HTML comment marker build/parse/classify
  - `agentic_devtools/cli/azure_devops/review_scaffold.py` — Thread scaffolding (fresh + incremental)
  - `agentic_devtools/cli/azure_devops/review_state.py` — `ReviewState`, `FileEntry`, `OverallSummary` dataclasses + CRUD
  - `agentic_devtools/cli/azure_devops/finalization/classification.py` — Author-filtered classification for finalization
- **API**: Azure DevOps REST API (threads, comments, PATCH/POST)
- **Testing**: 2000+ tests, 1:1:1 structure under `tests/unit/`, TDD workflow required
- **Issue**: [#1517](https://github.com/ayaiayorg/agentic-devtools/issues/1517)

## Research Summary

Key design decisions:

- Thread matching strategy (marker-based only, no author filtering for reuse)
- Reuse-reply idempotency mechanism (correlation marker in reply body)
- `originalAuthorId` field placement and backward compatibility

## Design Overview

```text
┌─────────────────────────────────────────────────────────┐
│           scaffold_review_threads() entry point          │
│  (currently: _fresh_scaffold / _incremental_rescaffold) │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│  NEW MODULE: thread_reuse.discover_reusable_threads()   │
│  - Fetch all PR threads                                 │
│  - classify_agdt_threads() by marker type               │
│  - For each target type (activity-log, overall-summary, │
│    file-summary), find best candidate                   │
│  - Return ThreadDiscoveryResult                         │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│  INTERNALS IN thread_reuse.py:                          │
│  - _resolve_single_match() for activity/overall         │
│  - _match_file_summary() for per-file matching          │
│  - Deterministic selection: prefer active > resolved,   │
│    then lowest thread ID                                │
│  - For file-summary: normalize_file_path equality       │
│  - Return matched thread_id + originalAuthorId or None  │
└─────────────┬───────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────┐
│         MODIFIED: _fresh_scaffold()                     │
│  - Before creating threads, call discovery              │
│  - For each target: reuse (post reply) OR create new    │
│  - Populate originalAuthorId on reused entries          │
│  - Emit structured log lines for each decision          │
└─────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Data Model Extension

**Deliverables**: Add `originalAuthorId` field to state dataclasses.

1. Add `originalAuthorId: str | None = None` to `OverallSummary` dataclass
2. Add `originalAuthorId: str | None = None` to `FileEntry` dataclass
3. Add `activityLogOriginalAuthorId: str | None = None` to `ReviewState` (for the activity-log thread)
4. Update `to_dict()` and `from_dict()` for all three (serialize only when not None for backward compat)
5. Write tests for serialization round-trip with and without the field

### Phase 2: Thread Discovery and Matching Logic

**Deliverables**: New module `agentic_devtools/cli/azure_devops/thread_reuse.py`

1. Create `thread_reuse.py` with:
   - `ThreadMatch` dataclass: `thread_id: int`, `comment_id: int`, `original_author_id: str | None`, `is_resolved: bool`
   - `ThreadDiscoveryResult` dataclass: `activity_log: ThreadMatch | None`, `overall_summary: ThreadMatch | None`, `file_summaries: dict[str, ThreadMatch]` (keyed by normalized path)
   - `discover_reusable_threads(threads, pull_request_id, target_files)` → `ThreadDiscoveryResult`
   - `_resolve_single_match(candidates, resolved_status_check)` → `ThreadMatch | None`
   - `_match_file_summary(candidates, target_path)` → `ThreadMatch | None`
2. Implement deterministic selection: active threads first, then lowest `thread["id"]`
3. Extract `original_author_id` from `thread["comments"][0]["author"]["id"]`
4. Use `parse_marker()` on first comment content for classification (no author filtering)
5. Use `normalize_file_path()` for file path comparison
6. Write comprehensive unit tests (TDD: red-green-refactor)

### Phase 3: Reuse-Reply Idempotency

**Deliverables**: Idempotent scaffolded-reply posting.

1. Define a reuse correlation marker format: `<!-- agdt-reuse:v1 session:{session_id} type:{type} -->`
2. Add `_has_reuse_reply(thread_comments, session_id, marker_type)` helper
3. Add `_post_reuse_reply(requests_module, headers, threads_url, thread_id, content, session_id, marker_type)` that checks for existing reuse-reply before posting
4. Write tests for idempotency detection (skip when reply already exists)

### Phase 4: Integrate Discovery into Scaffolding

**Deliverables**: Modify `_fresh_scaffold()` and `_incremental_rescaffold()` to use discovery.

1. In `_fresh_scaffold()`:
   - Before creating threads, call `discover_reusable_threads()` with current PR threads
   - For activity-log: if match found → reuse (post reply), else create new
   - For overall-summary: if match found → reuse (post reply), else create new
   - For each file: if match found → reuse (post reply), else create new
   - Populate `originalAuthorId` in state entries when reusing
2. In `_incremental_rescaffold()`:
   - Apply same discovery logic for new files being scaffolded
   - Existing files already have thread IDs — no change needed
3. Emit structured log lines: `f"Thread reuse: type={thread_type} thread_id={thread_id} action={action} original_author={author_id}"` (where `action` is `"reused"` or `"created"`)
4. Update `sync_review_state_from_threads()` to populate `originalAuthorId` on first encounter

### Phase 5: Finalization Compatibility

**Deliverables**: Ensure `finalization/classification.py` author filtering remains only for edit-permission scoping.

1. Verify `classify_eligible_comments()` uses author filtering only for determining which comments the current identity can PATCH (edit-permission scope)
2. Confirm the thread-matching logic in Phase 2 does NOT use author filtering
3. Add integration-level tests that exercise cross-identity reuse followed by finalization

### Phase 6: Logging and Dry-Run Support

**Deliverables**: Transparent reuse decisions + dry-run reporting.

1. In `_print_dry_run_plan()`, add output for reuse decisions (which threads would be reused vs created)
2. Emit structured log lines per NFR-002: thread type, thread ID, action, original author ID
3. Add tests for dry-run output format

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing scaffolding for in-progress reviews | High | `originalAuthorId` defaults to `None`; all new fields are optional in deserialization |
| Extra API call to fetch threads before scaffolding | Medium | Threads are already fetched in many code paths; reuse the existing fetch where possible |
| Reuse-reply duplication on retry/crash recovery | Medium | Correlation marker in reply body enables idempotent detection |
| Incorrect file-path matching across normalizations | Medium | Use existing `normalize_file_path()` on both sides; comprehensive test coverage |
| Performance regression on PRs with many threads | Low | Single-pass classification via `classify_agdt_threads()` (already O(n)); NFR-001 200ms budget |

## Dependencies

- **Internal**: `marker.py` (`parse_marker`, `classify_agdt_threads`, `build_marker`), `review_state.py` (`normalize_file_path`, dataclasses), `review_scaffold.py` (scaffolding functions)
- **External**: Azure DevOps REST API (threads endpoint, already used)
- **No new packages required**

---
*Generated by Copilot SDK (claude-opus-4.6)*
