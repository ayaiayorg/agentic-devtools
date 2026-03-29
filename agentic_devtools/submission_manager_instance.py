"""Lazy singleton for the file review SubmissionManager."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .submission_manager import SubmissionManager

_manager: SubmissionManager | None = None
_lock = threading.Lock()


def get_submission_manager() -> SubmissionManager:
    """Return (or create) the module-level SubmissionManager singleton.

    On first call the function resolves Azure DevOps configuration, auth
    headers, and the repository ID, then wires a real review processor via
    ``create_review_processor()`` and passes it into a new
    ``SubmissionManager``.  Subsequent calls return the same instance.

    Thread safety is guaranteed by double-checked locking with
    ``threading.Lock``.

    Raises:
        OSError: If the Azure DevOps PAT is not configured.
        RuntimeError: If configuration cannot be resolved.
    """
    global _manager  # noqa: PLW0603
    if _manager is not None:
        return _manager
    with _lock:
        if _manager is not None:  # pragma: no cover
            return _manager

        from .cli.azure_devops.auth import get_auth_headers, get_pat
        from .cli.azure_devops.config import AzureDevOpsConfig
        from .cli.azure_devops.helpers import get_repository_id
        from .submission_manager import SubmissionManager as SM
        from .submission_processor import create_review_processor

        config = AzureDevOpsConfig.from_state()
        headers = get_auth_headers(get_pat())
        repo_id = get_repository_id(config.organization, config.project, config.repository)
        processor = create_review_processor(config, headers, repo_id)
        _manager = SM(processor=processor)
        return _manager
