# Implementation Plan: PR Review Scaffolding 403 Cross-Identity Thread Recovery

## 1. Technical Context

| Aspect | Detail |
|--------|--------|
| Language | Python >=3.10 |
| Package | `agentic_devtools` (pip-installable CLI) |
| Key modules | `agentic_devtools/cli/azure_devops/review_scaffold.py`, `agentic_devtools/cli/azure_devops/helpers.py`, `agentic_devtools/cli/azure_devops/status_cascade.py`, `agentic_devtools/cli/azure_devops/file_review_commands.py`, `agentic_devtools/cli/azure_devops/review_state.py`, `agentic_devtools/cli/azure_devops/auth.py` |
| External API | Azure DevOps REST API (mixed versions in current codebase: `7.0` and `7.1-preview.*`; PR threads/comments/connectionData typically `7.1-preview.1`) |
| Test framework | pytest with 100% branch coverage requirement |
| State persistence | `review-state.json` (dataclass-backed JSON) |
| Issue | [#1915](https://github.com/ayaiayorg/agentic-devtools/issues/1915) |

### Architecture Decisions

- **Proactive ownership detection** at recovery time via `_apis/connectionData` endpoint
- **Reply-based fallback** when PATCH is forbidden (full content, not delta)
- **Per-thread error isolation** — one 403 never aborts the batch
- **Single identity fetch per session** — cached for all comparisons

## 2. Research Summary

See existing artifacts (`spec.md` clarification history and `checklists/requirements.md`) for detailed decisions on:

- Identity detection endpoint choice (`_apis/connectionData` vs `_apis/profile`)
- Reply idempotency strategy (marker-based deduplication)
- Batch timeout enforcement approach
- Schema backward compatibility for `crossIdentity` field

## 3. Design Overview

```text
┌─────────────────────────────────────────────────────────────────┐
│                    Recovery Phase                                 │
│                                                                   │
│  _try_recover_state_from_pr_threads()                            │
│       │                                                           │
│       ├── IdentityCache.get_or_fetch()                           │
│       │     → resolve_pat_identity_snapshot()                    │
│       │         → {id, uniqueName, displayName}                  │
│       │                                                           │
│       ├── for each recovered thread:                             │
│       │     is_cross_identity(comment.author, cached_snapshot)   │
│       │       primary:  author.id vs cached.id                   │
│       │       fallback: author.uniqueName vs cached.uniqueName   │
│       │     if mismatch → tag FileEntry.crossIdentity = True     │
│       │     if duplicate → prefer current-identity thread        │
│       │                                                           │
│       └── save_review_state()                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Submission Phase                               │
│                                                                   │
│  execute_cascade() / _patch_comment_content()                    │
│       │                                                           │
│       ├── if crossIdentity → skip PATCH, go to reply path        │
│       │                                                           │
│       ├── try PATCH:                                             │
│       │     on 403 → mark crossIdentity, try reply path          │
│       │     on 2xx → success                                     │
│       │                                                           │
│       ├── try REPLY:                                             │
│       │     deduplicate via marker comment scan                  │
│       │     on 403 → record as blocked                           │
│       │     on 2xx → success                                     │
│       │                                                           │
│       └── if both blocked → local mark + activity-log entry      │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Identity Detection & Caching

**Deliverable**: Shared identity helper reused by review scaffolding and existing Azure DevOps callers

| Task | File | Description |
|------|------|-------------|
| 1.1 | `agentic_devtools/cli/azure_devops/finalization/identity.py` (or shared helper module) | Reuse the existing connectionData identity resolver and preserve `resolve_pat_identity()` return contract (`Optional[str]` user ID only) for current callers |
| 1.2 | Shared helper module | Add `resolve_pat_identity_snapshot()` (or equivalent) that returns `{id, uniqueName, displayName}` — `id` and `uniqueName` for ownership checks, `displayName` for user-facing attribution — without changing `resolve_pat_identity()` |
| 1.3 | Shared helper module | Add `IdentityCache` with `get_or_fetch()` method that caches the snapshot helper result for session lifetime |
| 1.4 | Shared helper module | Add `is_cross_identity(comment_author, cached_identity)` comparator — primary: `author.id` vs `cached.id`, fallback: `author.uniqueName` vs `cached.uniqueName` |
| 1.5 | Shared helper module + existing callers | Keep identity-fetch failure behavior as `None` + warning so fallback logic remains 403-based |
| 1.6 | Tests | Unit tests for contract preservation (`resolve_pat_identity`), snapshot helper, cache behavior, and comparator (mock HTTP responses) |

**TDD sequence**: Write failing tests that lock `resolve_pat_identity() -> str | None`
behavior, then add tests for `resolve_pat_identity_snapshot()` (via
`IdentityCache.get_or_fetch()`), `is_cross_identity`, and cache behavior before
implementation.

### Phase 2: Review State Schema Extension

**Deliverable**: `crossIdentity` field on `FileEntry`

| Task | File | Description |
|------|------|-------------|
| 2.1 | `review_state.py` | Add `crossIdentity: bool = False` field to `FileEntry` dataclass |
| 2.2 | `review_state.py` | Verify `from_dict()`/`to_dict()` handles missing field gracefully (backward compat) |
| 2.3 | Tests | Unit tests: serialize/deserialize with and without `crossIdentity` field |

### Phase 3: Recovery-Time Ownership Tagging

**Deliverable**: Modified `_try_recover_state_from_pr_threads` with ownership detection

| Task | File | Description |
|------|------|-------------|
| 3.1 | `review_scaffold.py` | Import and instantiate `IdentityCache` at start of recovery |
| 3.2 | `review_scaffold.py` | After recovering each file thread, call `is_cross_identity()` on `comments[0].author` |
| 3.3 | `review_scaffold.py` | Set `FileEntry.crossIdentity = True` for mismatched threads |
| 3.4 | `review_scaffold.py` | Implement duplicate-thread selection: prefer current-identity thread, else lowest `thread_id` |
| 3.5 | `review_scaffold.py` | Log ignored duplicate thread IDs in activity log entry |
| 3.6 | `review_scaffold.py` | Handle identity-fetch failure: skip tagging, log warning |
| 3.7 | Tests | Unit tests with mocked thread data (same-identity, cross-identity, duplicates, identity-fetch failure) |

### Phase 4: Reply-Based Update Path

**Deliverable**: Reused/shared reply-posting path for cross-identity scaffold updates

| Task | File | Description |
|------|------|-------------|
| 4.1 | `review_scaffold.py` + `helpers.py` | Reuse existing reply POST logic (`review_scaffold._post_reply`), extracting it into a shared helper only if needed instead of adding a third independent reply implementation; keep any shared helper signature aligned with existing `helpers.py` request helpers |
| 4.2 | `review_scaffold.py` + `review_templates.py` + `marker.py` | Build reply content so it starts with the existing subsequent-comment header (`### Commit:`), then includes an AGDT marker that embeds `mode:cross-identity-update` **inside** `<!-- agdt-review:... -->` (by extending `marker.build_marker(...)` or adding a helper that supports extra marker fields), plus an `**[Updated by {current_identity.displayName}]**` line in the reply body |
| 4.3 | `review_scaffold.py` + `helpers.py` | Implement idempotency using existing thread-comment retrieval: before posting, scan existing replies for the matching marker; if found, skip |
| 4.4 | `review_scaffold.py` + `helpers.py` | Return structured result from the reused/shared reply path: `{"method": "reply", "thread_id": ..., "success": True/False}` |
| 4.5 | Tests | Unit tests for reply posting, idempotency check, marker formatting |

### Phase 5: 403-Aware PATCH with Fallback

**Deliverable**: Modified `patch_comment`, `_patch_comment_content`, and file-summary PATCH call paths with 403 handling

| Task | File | Description |
|------|------|-------------|
| 5.1 | `helpers.py` | Modify `patch_comment` to catch 403 and explicitly raise `CrossIdentityForbiddenError` (no sentinel return path) |
| 5.2 | `helpers.py` | Create `CrossIdentityForbiddenError(requests.exceptions.HTTPError)` in helpers — subclassing `requests.exceptions.HTTPError` (not `urllib.error.HTTPError`) ensures existing `except requests.exceptions.HTTPError` handlers in Azure DevOps callers continue to catch it |
| 5.3 | `review_scaffold.py` + `helpers.py` + `file_review_commands.py` | Refactor `_patch_comment_content` and file-summary PATCH call sites to use a shared PATCH helper compatible with existing `threads_url` call sites (reusing `helpers.patch_comment` internals or a URL-based wrapper), then catch `CrossIdentityForbiddenError` and invoke the reused/shared reply-posting path from Phase 4 as fallback |
| 5.4 | `review_scaffold.py` | If reply also fails with 403, record as "blocked" and continue |
| 5.5 | `status_cascade.py` | Modify `execute_cascade` to wrap each `patch_comment`/`patch_thread_status` call in try/except, accumulating results per-operation |
| 5.6 | `status_cascade.py` | Return `CascadeResult` dataclass with `succeeded`, `fallen_back`, `blocked` lists |
| 5.7 | Tests | Unit tests for 403 catch → reply fallback → blocked recording |

### Phase 6: Batch Isolation & Timeout

**Deliverable**: Per-thread error isolation and 120s batch timeout

| Task | File | Description |
|------|------|-------------|
| 6.1 | `status_cascade.py` | Wrap each operation in the batch loop with individual try/except (not batch-level) |
| 6.2 | `status_cascade.py` + state/config read path | Add batch-level `time.monotonic()` tracking with configurable timeout override from state key `review.scaffold.cascade_timeout_seconds` (default `120`); if elapsed exceeds timeout, skip remaining updates and report timeout |
| 6.3 | `status_cascade.py` | Accumulate per-thread results: `success` / `fallback_reply` / `blocked` / `skipped_timeout` and include applied timeout value |
| 6.4 | Tests | Unit tests for partial success, timeout cutoff, result accumulation |

### Phase 7: Graceful Degradation (Both Forbidden)

**Deliverable**: Activity-log reply for fully blocked threads

| Task | File | Description |
|------|------|-------------|
| 7.1 | `review_scaffold.py` or `status_cascade.py` | After batch completes, collect all "blocked" entries |
| 7.2 | `review_scaffold.py` | Post reply to activity-log thread with structured list: thread IDs, file paths, reason |
| 7.3 | `review_scaffold.py` | For each blocked file, update `review-state.json` local file status directly (via review-state helpers); do **not** call `mark_file_reviewed` Azure DevOps API in this fallback path |
| 7.4 | Tests | Unit tests for activity-log reply content and local `review-state.json` status preservation, independent of any viewed-status API sync |

### Phase 8: Integration & Regression

**Deliverable**: End-to-end validation

| Task | Description |
|------|-------------|
| 8.1 | Integration test: full recovery → submit cycle with mixed-ownership threads (mocked API) |
| 8.2 | Integration test: identity-fetch failure → fallback to 403-based detection |
| 8.3 | Integration test: duplicate threads → correct selection logic |
| 8.4 | Run `agdt-test` full suite, verify 0 regressions |
| 8.5 | Run `bash scripts/targeted-checks.sh` for lint/format/coverage |

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `_apis/connectionData` endpoint unavailable in some Azure DevOps configurations | Low | Medium | Fallback to 403-based detection; identity fetch failure is non-fatal |
| Reply idempotency check has race condition (two agents posting simultaneously) | Low | Low | Marker-based dedup is best-effort; duplicate replies are cosmetic only |
| 120s batch timeout too aggressive for large PRs (>50 files) | Medium | Medium | Make timeout configurable via state key; document NFR boundary |
| Breaking existing callers of `patch_comment` | Medium | High | New exception type subclasses `requests.exceptions.HTTPError`; existing `except requests.exceptions.HTTPError` handlers still catch it |
| `review-state.json` backward compatibility | Low | High | `crossIdentity` defaults to `False`; `from_dict` ignores unknown/missing fields |

## 6. Dependencies

### Internal

| Module | Dependency Type |
|--------|----------------|
| `auth.py` | Uses existing `get_pat()` and `get_auth_headers()` |
| `review_state.py` | Schema extension (Phase 2) |
| `review_scaffold.py` | Major modification (Phases 3, 5, 7) |
| `helpers.py` | New functions + modified error handling (Phases 4, 5) |
| `status_cascade.py` | Batch isolation (Phases 5, 6) |
| `config.py` | Uses `AzureDevOpsConfig` for org URL |

### External

| Dependency | Purpose |
|-----------|---------|
| Azure DevOps REST API `_apis/connectionData` | Identity detection |
| Azure DevOps REST API `_apis/git/repositories/{repo}/pullRequests/{pr}/threads/{id}/comments` | Reply posting |
| `requests` library | HTTP calls (already a dependency) |

---
*Generated by Copilot SDK (claude-opus-4.6)*
