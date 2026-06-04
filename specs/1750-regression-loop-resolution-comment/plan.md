# Implementation Plan: Restore Full Resolution Comment Format

## Technical Context

- **Language/Stack**: Python 3.x, pip-installable package `agentic-devtools`
- **Key Files**:
  - `agentic_devtools/cli/ci/github_provider.py` — `finalize_post_repair()` method (line ~2196–2219)
  - `agentic_devtools/cli/ci/resolution/reply_formatter.py` — `ReplyFormatter` class
  - `agentic_devtools/cli/ci/resolution/models.py` — `TierResult`, `ResolutionReply`
- **Testing**: pytest with 100% branch coverage requirement, 1:1:1 test structure under `tests/unit/`
- **CI**: Pre-push hooks run ruff, mypy, markdownlint, per-file coverage

## Research Summary

See [research.md](research.md) for detailed analysis. Key decisions:

1. HEAD commit link appended by caller (`finalize_post_repair()`), not by `ReplyFormatter`
2. Repository resolved via existing `self._resolve_repo()` — no new resolution logic
3. Link omitted silently when `head_sha` is empty/None — no error raised
4. `ReplyFormatter` remains a pure formatting class with no side effects

## Design Overview

```text
finalize_post_repair(head_sha=...)
  │
  ├─ COMMENT_RESOLVE path (line 2196+)
  │   ├─ tier_result is None → fallback text + HEAD link
  │   ├─ "fallback" in tier_name → format_unconfirmed_commit_change_reply() + HEAD link
  │   └─ tier_result available → build_full_reply() + HEAD link  ← FIX: always use this
  │
  └─ _build_head_commit_line(head_sha, repo) → "\n\n**HEAD**: [<short>](<url>)" or ""
```

The fix is surgical: replace the `else: reply_body = _ADDRESSED_REPLY_BODY` branch with
`build_full_reply()`, then append a HEAD commit link after all reply bodies in the
`COMMENT_RESOLVE` path.

## Implementation Phases

### Phase 1: Add HEAD Commit Link Helper (TDD Red → Green)

**Deliverables**: A private helper method and its tests.

1. **Write tests** for a new `_build_head_commit_line(head_sha: str, repo: str) -> str` method:
   - Returns `\n\n**HEAD**: [abc1234](https://github.com/owner/repo/commit/<full_sha>)` when both args valid
   - Returns `""` when `head_sha` is empty/None
   - Returns `""` when `head_sha` is too short (< 7 chars)
   - Test file: `tests/unit/cli/ci/github_provider/test__build_head_commit_line.py`

2. **Implement** `_build_head_commit_line()` as a `@staticmethod` on `GitHubPlatformProvider`:

   ```python
   @staticmethod
   def _build_head_commit_line(head_sha: str, repo: str) -> str:
       if not head_sha or len(head_sha) < 7:
           return ""
       short = head_sha[:7]
       return f"\n\n**HEAD**: [{short}](https://github.com/{repo}/commit/{head_sha})"
   ```

### Phase 2: Fix the Resolution Reply Logic (TDD Red → Green)

**Deliverables**: Corrected `COMMENT_RESOLVE` branch + tests.

1. **Write tests** for the modified `finalize_post_repair()` resolution reply paths:
   - Test file: `tests/unit/cli/ci/github_provider/test_finalize_post_repair_reply_format.py`
   - Cases:
     - (a) `tier_result` available, normal resolution → `build_full_reply()` + HEAD link
     - (b) `tier_result` available, fallback tier → `format_unconfirmed_commit_change_reply()` + HEAD link
     - (c) `tier_result` is None → `"Addressed on the updated PR branch."` + HEAD link
     - (d) HEAD SHA available → link present
     - (e) HEAD SHA empty → no link appended
     - (f) Post-confirmation re-evaluation → `build_full_reply()` + HEAD link

2. **Modify** `finalize_post_repair()` (lines 2206–2219):

   **Before** (line 2217–2218):

   ```python
   else:
       reply_body = _ADDRESSED_REPLY_BODY
   ```

   **After**:

   ```python
   elif tier_result is not None:
       reply_body = reply_formatter.build_full_reply(
           tier_result,
           model_id=self._model_id_for_tier_result(tier_result),
       )
   else:
       reply_body = _ADDRESSED_REPLY_BODY
   ```

3. **Append HEAD link** after `reply_body` is determined (before `_reply_to_review_comment`):

   ```python
   reply_body += self._build_head_commit_line(head_sha, repo)
   ```

### Phase 3: Add Inline Documentation

**Deliverables**: Docstring/comments mapping resolution scenarios to reply formats.

1. Add a module-level or method-level docstring block in the `COMMENT_RESOLVE` section
   documenting the reply format decision tree:

   ```python
   # Resolution reply format selection:
   # ┌─ "fallback" in tier_name → format_unconfirmed_commit_change_reply()
   # ├─ post_confirmation_reply (re-eval) → build_full_reply()
   # ├─ tier_result available (normal) → build_full_reply()
   # └─ tier_result is None → static fallback text
   # All cases append HEAD commit link when head_sha is available.
   ```

### Phase 4: Verification

1. Run `agdt-test-file --source-file agentic_devtools/cli/ci/github_provider.py` — verify 100% branch coverage on modified lines
2. Run `agdt-test` — full suite passes, existing `ReplyFormatter` tests unmodified
3. Run `bash scripts/targeted-checks.sh` — ruff, mypy, markdownlint pass

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Duplicate replies on old threads | Medium | Low | `_has_existing_addressed_reply` already detects `_RESOLUTION_TIER_MARKER_PREFIX` |
| `_resolve_repo()` raises in edge case | Low | Low | Method is called earlier in `finalize_post_repair()`; if it fails, the entire method aborts before reaching reply logic |
| Reply body exceeds GitHub comment size limit | Low | Very Low | Structured replies are ~200-500 chars; GitHub limit is 65536 |
| Existing tests break due to assertion on old format | Medium | Low | Old format only appeared in the `else` branch which had no dedicated test |

## Dependencies

- **Internal**: `ReplyFormatter.build_full_reply()` — already exists, well-tested
- **Internal**: `self._resolve_repo()` — already called earlier in the method
- **Internal**: `head_sha` parameter — already passed into `finalize_post_repair()`
- **External**: None — no new packages, API calls, or infrastructure needed

---
*Generated by Copilot SDK (claude-opus-4.6)*
