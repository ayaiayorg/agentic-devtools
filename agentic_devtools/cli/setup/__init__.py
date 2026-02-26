"""
Setup module for agentic-devtools.

Provides commands for installing external CLI dependencies and verifying
the environment is correctly configured.
"""

from .commands import setup_check_cmd, setup_cmd, setup_copilot_cli_cmd, setup_gh_cli_cmd

__all__ = [
    "setup_cmd",
    "setup_copilot_cli_cmd",
    "setup_gh_cli_cmd",
    "setup_check_cmd",
]
