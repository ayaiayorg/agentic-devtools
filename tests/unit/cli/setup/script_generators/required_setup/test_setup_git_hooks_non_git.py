"""Tests for setup_git_hooks in non-git context."""

import subprocess as _real_subprocess
from unittest.mock import patch

from agentic_devtools.cli.setup.script_generators.required_setup import setup_git_hooks

_MOD = "agentic_devtools.cli.setup.script_generators.required_setup"


class TestSetupGitHooksNonGit:
    """Tests for setup_git_hooks when not in a git repo."""

    def test_returns_none_when_git_not_found(self):
        """Returns None when git binary is not found."""
        with patch(f"{_MOD}.subprocess.run", side_effect=FileNotFoundError("git not found")):
            assert setup_git_hooks() is None

    def test_returns_none_when_not_in_repo(self):
        """Returns None when rev-parse fails (not in a repo)."""
        with patch(
            f"{_MOD}.subprocess.run",
            side_effect=_real_subprocess.CalledProcessError(128, "git"),
        ):
            assert setup_git_hooks() is None
