"""
Setup module for agentic-devtools.

Provides commands for installing external CLI dependencies and verifying
the environment is correctly configured.
"""

from .commands import setup_certs_cmd, setup_check_cmd, setup_cmd, setup_copilot_cli_cmd, setup_gh_cli_cmd
from .gitignore_negations import ensure_root_gitignore_negations
from .version_guard import check_version_guard, compare_versions

__all__ = [
    "check_version_guard",
    "compare_versions",
    "ensure_root_gitignore_negations",
    "setup_cmd",
    "setup_copilot_cli_cmd",
    "setup_gh_cli_cmd",
    "setup_check_cmd",
    "setup_certs_cmd",
]
