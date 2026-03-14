"""
GitHub Copilot CLI session management package.

Provides utilities for starting and managing gh copilot CLI sessions,
supporting both interactive and non-interactive modes.
"""

from .session import CopilotSessionResult, build_copilot_args, is_gh_copilot_available, start_copilot_session

__all__ = [
    "build_copilot_args",
    "is_gh_copilot_available",
    "start_copilot_session",
    "CopilotSessionResult",
]
