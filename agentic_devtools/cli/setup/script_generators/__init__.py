"""Script generators for modular setup scripts.

This package generates standalone Python scripts that are placed in
``.agdt/`` and the repository root.  The generated scripts use **only**
the Python standard library — they must never import ``agentic_devtools``
or any other third-party package.
"""

from .complete_setup import generate_complete_setup_script
from .configured_setup import generate_configured_setup_script
from .gitignore_updater import update_gitignore
from .legacy_migration import detect_legacy_script, migrate_legacy_content
from .repo_specific import generate_repo_specific_stub
from .required_setup import generate_required_setup_script
from .root_entry_point import generate_root_entry_point

__all__ = [
    "generate_complete_setup_script",
    "generate_configured_setup_script",
    "generate_repo_specific_stub",
    "generate_required_setup_script",
    "generate_root_entry_point",
    "detect_legacy_script",
    "migrate_legacy_content",
    "update_gitignore",
]
