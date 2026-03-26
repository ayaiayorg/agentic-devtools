"""
GitHub Copilot CLI session management package.

Provides utilities for starting and managing gh copilot CLI sessions,
supporting both interactive and non-interactive modes.
"""

from .session import (
    DEFAULT_COPILOT_MODEL,
    CopilotSessionResult,
    build_copilot_args,
    get_default_copilot_model,
    is_gh_copilot_available,
    start_copilot_session,
)

__all__ = [
    "DEFAULT_COPILOT_MODEL",
    "build_copilot_args",
    "get_default_copilot_model",
    "is_gh_copilot_available",
    "start_copilot_session",
    "CopilotSessionResult",
]
