# Implementation Plan: Thread Title Formatting for Subsequent Review Comments

## Technical Context

- **Stack**: Python >=3.10 package (`agentic-devtools`), pip-installable CLI
- **Key modules**: `agentic_devtools/cli/azure_devops/review_templates.py` (render functions), `review_scaffold.py` (thread creation/replies), `finalization/repair.py` (repair),
  `status_cascade.py` (PATCH operations), `file_review_commands.py` (file review CLI)
- **Existing constant**: `SHORT_HASH_LENGTH = 7` in `review_attribution.py`
- **Test framework**: pytest, 1:1:1 test structure under `tests/unit/`

## Research Summary

- Parameter placement stays surgical: add `is_subsequent: bool = False` to the existing summary render helpers instead of introducing new render entry points.
- Commit header formatting should reuse existing `commit_hash` and `commit_url` inputs, preserving the current top-level title format by default.
- Convergence repair remains focused on demoted summary replies only; top-level summary comments continue using the existing `## ... Summary` headings.

## Design Overview

The change is surgical: add an `is_subsequent: bool = False` parameter to `render_file_summary()` and `render_overall_summary()`. When `True`, the heading line changes from the full title to a compact
`### Commit: [<short_hash>](<commit_url>)` format. All callers that produce **reply** comments pass `is_subsequent=True`. All callers that produce **top-level PATCH updates** continue to pass `False`
(the default).

```text
┌──────────────────────────────────┐
│  render_file_summary()           │
│  render_overall_summary()        │
│  ─────────────────────────────── │
│  is_subsequent=False → ## Title  │
│  is_subsequent=True  → ### Commit│
└──────────────────────────────────┘
         ▲                    ▲
         │                    │
    PATCH flows          Reply flows
  (status_cascade,    (_demote_main_comment,
   file_review_cmds)   convergence repair)
```

## Implementation Phases

### Phase 1: Core Rendering Changes (review_templates.py)

**Deliverables:**

1. Add `is_subsequent: bool = False` parameter to `render_file_summary()`
2. Add `is_subsequent: bool = False` parameter to `render_overall_summary()`
3. Implement header selection logic:
   - `is_subsequent=False` → existing `## File Review Summary: {fileName}` / `## Overall PR Review Summary`
   - `is_subsequent=True` → `### Commit: [<short_hash>](<commit_url>)` (full form), `### Commit: <short_hash>` (no URL), or `### Commit: unknown` (no hash)
4. Extract `short_hash` via `commit_hash[:SHORT_HASH_LENGTH]` (reusing the constant from `review_attribution.py`) from the existing `commit_hash` parameter already passed to both functions

**Key implementation detail:** The `commit_hash` and `commit_url` parameters already exist on both render functions. When `is_subsequent=True`, the heading is derived from these same parameters using
the fallback chain defined in FR-008.

### Phase 2: Caller Updates — Reply Contexts

**Deliverables:**

1. `review_scaffold.py` — `_demote_main_comment()`: when preserving the old main-comment body as a reply, do **not** post the raw content unchanged. Before posting the reply payload, rewrite its top
   header into the compact subsequent-comment form so demoted replies no longer repeat the full `## ... Summary` title.
2. Add a small utility such as `rewrite_header_for_subsequent(content, commit_hash, commit_url)` that replaces the first heading line of previously rendered summary content with:
   - `### Commit: [<short_hash>](<commit_url>)` when both values are available,
   - `### Commit: <short_hash>` when only the hash is available,
   - `### Commit: unknown` when no hash is available.
3. Use that utility only for reply payloads created by the demotion flow. This keeps historical body text intact while aligning the reply header with the subsequent-comment format.
4. `finalization/convergence.py` — `_compute_file_summary_content()` and `_compute_overall_summary_content()` remain `is_subsequent=False` because they compute expected **top-level** comment content,
   not reply content.
5. The re-scaffolding flow in `review_scaffold.py` continues rendering **new top-level** threads, so it also remains on the default top-level header format.

**Phase 2 decision:** adopt the header-rewrite approach for `_demote_main_comment()` reply payloads and keep this plan focused on that final implementation path.

### Phase 3: Validation & Repair Logic

**Deliverables:**

1. Add `validate_comment_header(content: str, is_subsequent: bool) -> bool` to `review_templates.py`
   - `is_subsequent=False`: valid if starts with `## File Review Summary:` or `## Overall PR Review Summary`
   - `is_subsequent=True`: valid if starts with `### Commit:`
2. Add `repair_subsequent_header(content: str, review_state: ReviewState) -> str` to `review_templates.py`
   - Replaces `## File Review Summary: ...` or `## Overall PR Review Summary` with `### Commit: [<short_hash>](<commit_url>)` using ReviewState data
   - Falls back per FR-008 when metadata is missing
3. Extend finalization/convergence classification so `file-summary` and `overall-summary` threads inspect reply comments in addition to the first/top-level comment
   - Preserve current behavior for the top-level summary comment, but also collect reply candidates for validation/repair when a summary has been demoted into reply position
4. Add explicit eligibility rules in finalization for identifying demoted summary replies
   - Treat replies in `file-summary` / `overall-summary` threads as demoted-summary candidates when their content matches the corresponding summary template shape:
     stale `## File Review Summary:` / `## Overall PR Review Summary`, or a repaired `### Commit:` header; exclude ordinary discussion replies
   - Keep `activity-log-entry` reply scanning unchanged; this is an additional reply classification path for summary threads, not a replacement
5. Integrate validation/repair into convergence flow only for those eligible demoted-summary reply comments with stale `## <title>` headers

### Phase 4: Tests

**Deliverables:**

1. `tests/unit/cli/azure_devops/review_templates/test_render_file_summary.py` — add tests for `is_subsequent=True` with all fallback variants
2. `tests/unit/cli/azure_devops/review_templates/test_render_overall_summary.py` — add tests for `is_subsequent=True`
3. New test file: `tests/unit/cli/azure_devops/review_templates/test_validate_comment_header.py`
4. New test file: `tests/unit/cli/azure_devops/review_templates/test_repair_subsequent_header.py`
5. New test file: `tests/unit/cli/azure_devops/review_templates/test_rewrite_header_for_subsequent.py`
6. Regression test: verify `_format_activity_log_entry()` output is unchanged

### Phase 5: Integration & Regression Verification

**Deliverables:**

1. Run full test suite (`agdt-test`) — verify 0 regressions
2. Run `bash scripts/run-pr-checks.sh` — verify all CI checks pass
3. Manual verification: existing test assertions for `## File Review Summary:` in top-level contexts still pass (confirming backward compatibility)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing top-level PATCH content | Low | High | Default `is_subsequent=False` preserves all existing behavior |
| Convergence repair loops (old format → repair → re-check) | Medium | Medium | Repair is idempotent; `### Commit:` prefix check prevents double-rewrite |
| Missing commit_hash in ReviewState at reply time | Low | Low | FR-008 fallback (`### Commit: unknown`) is deterministic |
| Accidentally modifying `_format_activity_log_entry` | Low | High | FR-009 explicit prohibition + regression test |

## Dependencies

- **Internal**: `review_attribution.SHORT_HASH_LENGTH` (already exists, value = 7)
- **Internal**: `ReviewState.commitHash` field (already exists, full 40-char SHA)
- **Internal**: `build_commit_pr_url()` / `build_commit_file_url()` (already exist for URL generation)
- **No external dependencies** — pure rendering logic, no new API calls

---
_Generated by Copilot SDK (claude-opus-4.6)_
