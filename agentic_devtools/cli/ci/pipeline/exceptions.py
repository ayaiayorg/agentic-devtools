"""Pipeline-specific exceptions for rebase operations."""

from __future__ import annotations


class RebaseConflictError(RuntimeError):
    """Raised when a rebase encounters unresolvable merge conflicts.

    The rebase has been aborted and the working tree is clean.
    """


class ForceWithLeaseError(RuntimeError):
    """Raised when a force-push-with-lease fails.

    This typically indicates a concurrent update to the remote branch.
    """
