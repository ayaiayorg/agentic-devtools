# Research — Issue #1518: Thread Title Formatting for Subsequent Review Comments

## Problem Analysis

When `_demote_main_comment()` in `review_scaffold.py` posts the old main-comment body as a
reply (to make room for a fresh top-level summary), it posts the raw rendered content
unchanged. That raw content was produced by `render_file_summary()` or
`render_overall_summary()` with their default `## ... Summary` heading. The result is a
reply that carries a level-2 heading identical to the top-level summary heading,
confusing readers who expect the reply to identify _which_ commit it covers.

## Root Cause

`render_file_summary()` and `render_overall_summary()` produce a single heading format
regardless of where the content will be placed (top-level slot vs. reply slot). There is
no existing mechanism to request a compact, commit-scoped heading for reply contexts.

## Option Analysis

### Option A — New render entry points

Add `render_file_summary_subsequent()` / `render_overall_summary_subsequent()` helpers.

- Pro: zero impact on existing callers
- Con: code duplication; two code paths to maintain for what is a single-parameter variation

### Option B — `is_subsequent` parameter (selected)

Add `is_subsequent: bool = False` to both existing helpers. When `True`, emit
`### Commit: [<short_hash>](<commit_url>)` instead of `## ... Summary`.

- Pro: single render path, minimal diff surface, backward compatible (default `False`)
- Con: none identified

### Option C — Post-process header in caller

Have `_demote_main_comment()` rewrite the heading via a regex after rendering.

- Pro: no change to render functions
- Con: fragile string manipulation spread across callers; harder to test in isolation

**Decision: Option B** for render functions; a focused header-rewrite utility
(`rewrite_header_for_subsequent`) is used in `_demote_main_comment()` for the demotion flow
to keep historical body text intact while aligning the reply header.

## Convergence Repair Scope

Early analysis considered repairing demoted-summary reply headers via the convergence
finalization flow. The finalization classifier currently only inspects the _first_ comment
of `file-summary` / `overall-summary` threads for convergence eligibility, not replies.
Extending it to cover replies requires additional classification and eligibility changes
(Phase 3, deliverable 3–5 in `plan.md`). That scope is included but scoped tightly: only
replies whose content matches the summary template shape are eligible, preserving existing
`activity-log-entry` scanning unchanged.

## Existing Constants and Helpers

| Symbol | Location | Notes |
|--------|----------|-------|
| `SHORT_HASH_LENGTH = 7` | `review_attribution.py` | Used for `commit_hash[:SHORT_HASH_LENGTH]` |
| `build_commit_pr_url()` | `review_attribution.py` | URL for the commit link in headings |
| `ReviewState.commitHash` | `review_state.py` | Full 40-char SHA used as source |

No new external dependencies are required.
