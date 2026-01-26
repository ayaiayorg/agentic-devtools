"""
Jira CLI commands facade.

This module re-exports all CLI commands from their specialized modules
for backward compatibility. The actual implementations are in:
- create_commands.py: create_epic, create_issue, create_subtask, create_issue_sync
- comment_commands.py: add_comment
- get_commands.py: get_issue
"""

from .comment_commands import add_comment
from .create_commands import (
    create_epic,
    create_issue,
    create_issue_sync,
    create_subtask,
)
from .get_commands import get_issue

# Re-export for backward compatibility
__all__ = [
    "add_comment",
    "create_epic",
    "create_issue",
    "create_issue_sync",
    "create_subtask",
    "get_issue",
]
