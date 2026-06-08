# Implementation Plan: Fix Stale Prompt File on PR Review Re-Runs

## 1. Technical Context

| Aspect | Detail |
|--------|--------|
| Language | Python 3.10+ |
| Package | `agentic_devtools` (pip-installable CLI) |
| Key file | `agentic_devtools/cli/workflows/commands.py` (lines 592–643) |
| Supporting file | `agentic_devtools/cli/workflows/worktree_setup.py` (`_wait_for_prompt_file`, `_start_copilot_session_for_pr_review`) |
| Test file | `tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py` |
| Test policy | 1:1:1 structure, 100% branch coverage, TDD |
| Logging | `logging` stdlib module, logger via `logging.getLogger(__name__)` (already imported at line 18) |

## 2. Research Summary

See [spec.md](spec.md) for details on:

- **Existing implementation gap**: Code already partially addresses the issue but has ordering and logging deficiencies.
- **Error handling strategy**: `OSError` catch with `FileNotFoundError` pass-through.
- **Logging approach**: Use existing `logging.getLogger(__name__)` pattern already in the file.
- **Phase 3 artifacts present in this directory**: `spec.md`, `plan.md`, and `checklists/requirements.md`.

## 3. Design Overview

The fix modifies a ~30-line section of `initiate_pull_request_review_workflow()` (lines 606–635)
to:

1. **Replace `print()` with proper logging** — INFO when file removed, DEBUG when absent.
2. **Abort before spawning background setup** when deletion fails — move the
   `_stale_prompt_cleared` guard to *before* `setup_pull_request_review_async()`.
3. **Raise a clear error** (print to stderr + `sys.exit(1)`) on hard `OSError`, including
   file path and OS error reason.

```text
┌──────────────────────────────────────────┐
│ initiate_pull_request_review_workflow()   │
│                                          │
│  1. Resolve state dir                    │
│  2. Resolve prompt file path             │
│  3. ── NEW: Delete stale file ──────── ◄─┤── INFO log if removed
│  │   ├─ FileNotFoundError? → ignore      │     DEBUG log if absent
│  │   ├─ Other OSError? → abort (exit 1)  │     ERROR log + exit
│  │   └─ Not a file? → abort (exit 1)     │
│  4. spawn setup_pull_request_review_async │
│  5. _start_copilot_session_for_pr_review │
└──────────────────────────────────────────┘
```

## 4. Implementation Phases

### Phase 1: Write Failing Tests (RED)

**Deliverable**: Update existing stale-prompt tests and add any missing case(s) in
`test_initiate_pull_request_review_workflow.py`

| Test | Validates |
|------|-----------|
| Update `test_stale_prompt_file_deleted_before_async_setup` | FR-001, SC-001: stale file deleted, INFO logged, background setup proceeds |
| `test_no_stale_prompt_file_logs_debug` | FR-004, SC-003: DEBUG log when no file exists |
| Update `test_stale_prompt_unlink_error_skips_copilot_session` (rename to reflect exit-on-error semantics) | FR-002, SC-004: OSError → exit(1) before `setup_pull_request_review_async` is called |
| Update `test_directory_at_stale_prompt_path_prints_warning` (rename to reflect exit-on-error semantics) | FR-002: non-file path → exit(1) before background setup |
| `test_consecutive_reruns_each_clean_stale_file` | US-3, SC-002: three re-runs each clean prior file |

Also update test assertions to use `caplog` (with logger level set for the module logger) for
FR-001/FR-004 INFO/DEBUG requirements while continuing to use `capsys` for stderr output checks.

```bash
agdt-test-pattern tests/unit/cli/workflows/commands/test_initiate_pull_request_review_workflow.py -v
```

### Phase 2: Implement Fix (GREEN)

**Deliverable**: Modified `commands.py` lines 602–643

Changes to apply:

```python
    else:
        # Normal interactive path: spawn setup in background and start
        # a Copilot session that waits for the prompt file.

        # FR-001: Delete any stale prompt file from a previous review so that
        # _wait_for_prompt_file() doesn't return immediately before the
        # new background setup has completed.  See #1746.
        from .worktree_setup import _WORKFLOW_PROMPT_FILENAMES

        _logger = logging.getLogger(__name__)
        _stale_prompt = resolved_state_dir / _WORKFLOW_PROMPT_FILENAMES["pull-request-review"]

        if _stale_prompt.is_file():
            try:
                _stale_prompt.unlink()
                _logger.info("Removed stale prompt file: %s", _stale_prompt)
            except FileNotFoundError:
                # Race: file disappeared between is_file() and unlink() — benign.
                _logger.debug("Stale prompt file already gone: %s", _stale_prompt)
            except OSError as exc:
                # FR-002: Hard failure — file locked or permission denied.
                print(
                    f"ERROR: Cannot remove stale prompt file.\n"
                    f"  Path: {_stale_prompt}\n"
                    f"  Reason: {exc}\n"
                    f"  Action: Remove or unlock the file manually, then retry.",
                    file=sys.stderr,
                )
                sys.exit(1)
        elif _stale_prompt.exists():
            # Path exists but is not a regular file (symlink to dir, socket, etc.)
            print(
                f"ERROR: Stale prompt path exists but is not a regular file: {_stale_prompt}\n"
                f"  Action: Remove it manually, then retry.",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            _logger.debug("No stale prompt file found (first run): %s", _stale_prompt)

        # Only after successful cleanup, spawn background setup.
        from ..azure_devops.async_commands import setup_pull_request_review_async

        setup_pull_request_review_async(
            pull_request_id=int(resolved_pr_id),
            jira_issue_key=resolved_issue_key,
        )

        from .worktree_setup import _start_copilot_session_for_pr_review

        repo_root = get_git_repo_root() or os.getcwd()
        _start_copilot_session_for_pr_review(repo_root, interactive=interactive, model=model)
```

Key differences from existing code:

| Current behavior | New behavior |
|-----------------|--------------|
| `print("WARNING: ...")` on failure | `logging.getLogger(__name__).info/debug()` + `print(..., file=sys.stderr)` + `sys.exit(1)` |
| Spawns background setup THEN checks `_stale_prompt_cleared` | Exits BEFORE spawning background setup on error |
| Uses `unlink(missing_ok=True)` hiding `FileNotFoundError` | Explicit `FileNotFoundError` catch with DEBUG log for traceability |
| No log when file doesn't exist | DEBUG log on first-run (no stale file) |

### Phase 3: Verify & Refactor

**Deliverable**: All tests green, 100% branch coverage on modified code.

```bash
agdt-test-pattern tests/unit/cli/workflows/commands/ -v
bash scripts/targeted-checks.sh
```

### Phase 4: Run Full Suite & PR Checks

```bash
agdt-test
agdt-task-wait
bash scripts/targeted-checks.sh
```

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Breaking existing tests that mock the old print-based warnings | Medium | Low | Search for `"stale prompt"` in test assertions and update |
| `_WORKFLOW_PROMPT_FILENAMES` import at runtime adds latency | Low | Negligible | Import is from same package, already used in existing code |
| `sys.exit(1)` in library code (non-CLI context) | Low | Medium | Only reached in CLI entry point path; function is CLI-only |
| Test isolation — tests creating real files in temp dirs | Low | Low | Existing `temp_state_dir` fixture already handles this |

## 6. Dependencies

| Dependency | Type | Status |
|-----------|------|--------|
| `logging` stdlib | Internal | Already imported (line 18) |
| `_WORKFLOW_PROMPT_FILENAMES` constant | Internal | Already exists in `worktree_setup.py` |
| `resolved_state_dir` local variable | Internal | Already computed earlier in function |
| `sys` stdlib | Internal | Already imported |
| No new packages required | — | — |

---
*Generated by Copilot SDK (claude-opus-4.6)*
