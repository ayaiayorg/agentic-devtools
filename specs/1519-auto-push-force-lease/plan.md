# Implementation Plan: Auto-push with --force-with-lease after Rebase

## Technical Context

- **Stack**: Python 3.x CLI package (`agentic-devtools`), installed via pip/pipx
- **Key modules**:
  - `agentic_devtools/cli/git/operations.py` — `force_push()`, `rebase_onto_main()`, `RebaseResult`
  - `agentic_devtools/cli/git/commands.py` — `commit_cmd()`, `_sync_with_main()`
  - `agentic_devtools/cli/azure_devops/review_commands.py` — `checkout_and_sync_branch()`
  - `agentic_devtools/cli/git/core.py` — `run_git()` (raises `SystemExit` on failure when `check=True`)
- **Error model**: `run_git(..., check=True)` prints to stderr then calls `sys.exit(returncode)` on failure
- **Existing behavior**: `commit_cmd()` already calls `force_push()` after rebase; `checkout_and_sync_branch()` does NOT push after rebase

## Research Summary

See [research.md](research.md) for details on:

- Push failure handling strategy (catch `SystemExit` vs. `check=False`)
- Return tuple extension approach for `checkout_and_sync_branch()`
- Dry-run reporting gap in `commit_cmd()`

## Design Overview

```text
┌─────────────────────────────────────────────────────────────┐
│ commit_cmd() [git save workflow]                            │
│  └─ _sync_with_main() → rebase_occurred: bool             │
│  └─ if needs_force_push: force_push(dry_run)              │
│  └─ FIX: dry-run path must also report push intent        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ checkout_and_sync_branch() [PR review workflow]             │
│  └─ rebase_onto_main() → RebaseResult                      │
│  └─ NEW: if is_success + was_rebased → force_push()       │
│  └─ NEW: catch SystemExit → push_succeeded=False          │
│  └─ NEW: return tuple extended with push_succeeded element │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Fix dry-run reporting in `commit_cmd()` (FR-1, FR-5)

**File**: `agentic_devtools/cli/git/commands.py`

**Current issue**: Lines 265-286 — when `dry_run=True`, the code jumps to line 285 printing
"[DRY RUN] No changes were made." without reporting the push that _would_ have occurred.

**Changes**:

1. After `_sync_with_main(dry_run, skip_rebase)` returns, when `dry_run=True` and `not skip_push`:
   - If `needs_force_push`: call `force_push(dry_run=True)` (prints "[DRY RUN] Would force push")
   - Else: call `publish_branch(dry_run=True)` (prints "[DRY RUN] Would publish branch")
2. Remove or keep the final "[DRY RUN] No changes were made." summary line (keep for consistency but ensure push intent is reported before it)

**Deliverable**: Dry-run output now reports the intended push action.

### Phase 2: Add auto-push to `checkout_and_sync_branch()` (FR-2, FR-3, FR-4, FR-5, FR-6, FR-7)

**File**: `agentic_devtools/cli/azure_devops/review_commands.py`

**Changes**:

1. **Extend return type** from `tuple[bool, str | None, set[str], bool]` to
   `tuple[bool, str | None, set[str], bool, bool | None]` — fifth element is `push_succeeded`.

2. **Add auto-push logic** after line 202 (`print("Branch is synced with main.")`):

   ```python
   if rebase_result.is_success and rebase_result.was_rebased:
       push_succeeded = _try_force_push_after_rebase(dry_run)
   ```

3. **Create helper `_try_force_push_after_rebase(dry_run: bool) -> bool | None`** that:
   - Imports `force_push` from `..git.operations`
   - If `dry_run`: calls `force_push(dry_run=True)`, returns `None`
   - Else: wraps `force_push(dry_run=False)` in a `try/except SystemExit` block
     - On success: returns `True`
     - On `SystemExit`: prints warning message (rebase OK, push failed, manual action needed), returns `False`

4. **Update all return statements** to include the fifth element (`push_succeeded`, defaulting to `None` when no push was attempted).

5. **Update callers** (NFR-1):
   - `setup_pull_request_review()` in `review_commands.py` line 872 — unpack 5th element
   - `checkout_and_sync_branch_async()` in `async_commands.py` — unpack 5th element
   - Any other callers found in tests

### Phase 3: Tests (SC-1 through SC-4)

Follow 1:1:1 test structure. Key test files:

| Test file | Covers |
|-----------|--------|
| `tests/unit/cli/git/commands/test__sync_with_main.py` | SC-1: force_push called after rebase |
| `tests/unit/cli/git/commands/test_commit_cmd.py` | SC-1, SC-3: dry-run reports push |
| `tests/unit/cli/azure_devops/review_commands/test_checkout_and_sync_branch.py` | SC-2, SC-3, SC-4: auto-push, dry-run, failure |

**Test scenarios**:

1. Successful rebase → `force_push()` called once, `push_succeeded=True`
2. No rebase needed (`was_rebased=False`) → no push, `push_succeeded=None`
3. Rebase conflicts → no push, `push_succeeded=None`
4. Fetch failed → no push, `push_succeeded=None`
5. `skip_rebase=True` → no push, `push_succeeded=None`
6. Push fails (`SystemExit`) → warning printed, `push_succeeded=False`, workflow continues
7. Dry-run → `force_push(dry_run=True)` called, `push_succeeded=None`
8. `commit_cmd()` dry-run reports push intent

### Phase 4: Documentation

- Update docstrings for `checkout_and_sync_branch()` and `commit_cmd()`
- Update copilot-instructions if any CLI behavior descriptions need adjustment

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Catching `SystemExit` catches too broadly | Low | Medium | Catch only in the specific `_try_force_push_after_rebase` helper, re-raise if exit code is 0 |
| Callers not updated for new tuple length | Low | High | grep for all `checkout_and_sync_branch(` calls; type checker will also catch |
| Existing tests break due to return type change | Medium | Low | Update test mocks/assertions in same PR |
| Force push to wrong branch | Very Low | High | `force_push()` uses current branch implicitly; already validated by checkout step |

## Dependencies

- **Internal**: `force_push()` in `operations.py` (reused, not modified)
- **Internal**: `run_git()` in `core.py` (behavior understood, not modified)
- **Internal**: `RebaseResult` class (read-only usage)
- **External**: None — no new packages needed

---
_Generated by Copilot SDK (claude-opus-4.6)_
