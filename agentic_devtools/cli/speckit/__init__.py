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
from .cross_ref import cross_ref_command as speckit_cross_ref
from .pass_e2.validator import test_coverage_command as speckit_test_coverage
from .validate_checklists import validate_checklists_command as speckit_validate_checklists
from .validate_frs import validate_frs_command as speckit_validate_frs

__all__ = [
    "speckit_analyze",
    "speckit_checklist",
    "speckit_clarify",
    "speckit_constitution",
    "speckit_cross_ref",
    "speckit_implement",
    "speckit_test_coverage",
    "speckit_plan",
    "speckit_specify",
    "speckit_tasks",
    "speckit_taskstoissues",
    "speckit_validate_checklists",
    "speckit_validate_frs",
]
