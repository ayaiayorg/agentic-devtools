"""
Lazy singleton for the SubmissionManager.

Provides ``get_submission_manager()`` which returns a process-wide
singleton, creating it on first call.  The singleton uses the default
processor from :func:`create_submission_manager`.
"""

from __future__ import annotations

import threading

from agentic_devtools.submission_manager import SubmissionManager, create_submission_manager

_manager: SubmissionManager | None = None
_lock = threading.Lock()


def get_submission_manager() -> SubmissionManager:
    """Return the process-wide SubmissionManager singleton.

    Creates the manager lazily on the first call using the default
    processor from :func:`create_submission_manager`.  Thread-safe
    via a module-level lock.

    Returns:
        The shared :class:`SubmissionManager` instance.
    """
    global _manager  # noqa: PLW0603
    if _manager is None:
        with _lock:
            if _manager is None:
                _manager = create_submission_manager()
    return _manager
