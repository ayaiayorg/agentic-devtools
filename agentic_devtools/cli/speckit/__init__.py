"""
Speckit CLI commands.

Provides ``agdt-speckit-*`` entry points that read the corresponding
``.github/prompts/speckit.<name>.prompt.md`` template, substitute
``$ARGUMENTS`` with the user-supplied text, and launch an interactive
``gh copilot`` session.
"""

from .commands import (
    speckit_analyze,
    speckit_checklist,
    speckit_clarify,
    speckit_constitution,
    speckit_implement,
    speckit_plan,
    speckit_specify,
    speckit_tasks,
    speckit_taskstoissues,
)

__all__ = [
    "speckit_analyze",
    "speckit_checklist",
    "speckit_clarify",
    "speckit_constitution",
    "speckit_implement",
    "speckit_plan",
    "speckit_specify",
    "speckit_tasks",
    "speckit_taskstoissues",
]
