"""
GitHub Copilot CLI session management package.

Provides utilities for starting and managing gh copilot CLI sessions,
supporting both interactive and non-interactive modes.
"""

from .session import CopilotSessionResult, is_gh_copilot_available, start_copilot_session

__all__ = [
    "is_gh_copilot_available",
    "start_copilot_session",
    "CopilotSessionResult",
]
