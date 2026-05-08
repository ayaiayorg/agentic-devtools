"""Tests for setup_git_hooks."""

import subprocess as _real_subprocess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.setup.script_generators.required_setup import setup_git_hooks

_MOD = "agentic_devtools.cli.setup.script_generators.required_setup"


class TestSetupGitHooks:
    """Tests for setup_git_hooks."""

    def test_returns_none_when_not_in_git_repo(self):
        """Returns None outside a git repository."""
        with patch(
            f"{_MOD}.subprocess.run",
            side_effect=_real_subprocess.CalledProcessError(128, "git"),
        ):
            result = setup_git_hooks()
            assert result is None

    def test_sets_hooks_path(self, tmp_path):
        """Sets core.hooksPath when in a git repo."""
        mock_run = MagicMock(
            side_effect=[
                MagicMock(returncode=0, stdout=".git\n"),  # rev-parse --git-dir
                MagicMock(returncode=1, stdout=""),  # config --get (not set)
                MagicMock(returncode=0),  # config set
                MagicMock(returncode=0, stdout=str(tmp_path) + "\n"),  # show-toplevel
            ]
        )
        with patch(f"{_MOD}.subprocess.run", mock_run):
            result = setup_git_hooks()
            assert result is not None
            assert "set to '.githooks'" in result

    def test_warns_on_different_hooks_path(self):
        """Warns when core.hooksPath is already set to a different value."""
        mock_run = MagicMock(
            side_effect=[
                MagicMock(returncode=0, stdout=".git\n"),
                MagicMock(returncode=0, stdout="/custom/hooks\n"),
            ]
        )
        with patch(f"{_MOD}.subprocess.run", mock_run):
            result = setup_git_hooks()
            assert result is not None
            assert "Overwriting" in result
