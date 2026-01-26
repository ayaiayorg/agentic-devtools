"""
Git workflow CLI commands and helpers.

Commands provide a streamlined interface for the single-commit workflow:
1. dfly-git-commit / dfly-git-sync: Fetch, rebase onto main, stage, commit, and publish
   - Fetches latest from origin/main and rebases if behind
   - Auto-aborts rebase on conflicts with manual resolution instructions
   - Detects if branch already has commits ahead of main for same issue
   - Automatically amends instead of creating new commit when appropriate
2. dfly-git-stage, dfly-git-push, dfly-git-force-push: Individual operations

The commit message is read from state (set via dfly-set commit_message "...").

Key advantage over PowerShell: multiline commit messages work natively
without replacement tokens or line-by-line builders!

Diff helpers provide utilities for extracting change information between refs,
used by PR analysis workflows.
"""

from .async_commands import (
    amend_async,
    commit_async,
    force_push_async,
    publish_async,
    push_async,
    stage_async,
    sync_async,
)
from .commands import (
    amend_cmd,
    commit_cmd,
    force_push_cmd,
    publish_cmd,
    push_cmd,
    stage_cmd,
    sync_cmd,
)
from .diff import (
    AddedLine,
    AddedLinesInfo,
    DiffEntry,
    get_added_lines_info,
    get_diff_entries,
    get_diff_patch,
    normalize_ref_name,
    sync_git_ref,
)
from .operations import (
    CheckoutResult,
    RebaseResult,
    checkout_branch,
    fetch_main,
    get_files_changed_on_branch,
    rebase_onto_main,
)

__all__ = [
    # Commands (sync)
    "commit_cmd",
    "sync_cmd",
    "amend_cmd",
    "stage_cmd",
    "push_cmd",
    "force_push_cmd",
    "publish_cmd",
    # Commands (async)
    "commit_async",
    "sync_async",
    "amend_async",
    "stage_async",
    "push_async",
    "force_push_async",
    "publish_async",
    # Diff helpers
    "DiffEntry",
    "AddedLine",
    "AddedLinesInfo",
    "normalize_ref_name",
    "sync_git_ref",
    "get_diff_entries",
    "get_added_lines_info",
    "get_diff_patch",
    # Branch operations
    "checkout_branch",
    "CheckoutResult",
    "fetch_main",
    "rebase_onto_main",
    "RebaseResult",
    "get_files_changed_on_branch",
]
