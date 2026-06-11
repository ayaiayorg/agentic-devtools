"""Tests for _discover_git_root."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.commit_template import _discover_git_root

_MOD = "agentic_devtools.cli.git.commit_template"


class TestDiscoverGitRoot:
    """Tests for _discover_git_root."""

    @patch(f"{_MOD}.run_git")
    def test_returns_path_on_success(self, mock_run_git):
        """Returns Path when git rev-parse succeeds."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="/repo/root\n")
        result = _discover_git_root()
        assert result == Path("/repo/root")

    @patch(f"{_MOD}.run_git")
    def test_returns_none_on_nonzero_exit(self, mock_run_git):
        """Returns None when git rev-parse fails."""
        mock_run_git.return_value = MagicMock(returncode=128, stdout="")
        result = _discover_git_root()
        assert result is None

    @patch(f"{_MOD}.run_git")
    def test_returns_none_on_empty_stdout(self, mock_run_git):
        """Returns None when stdout is empty."""
        mock_run_git.return_value = MagicMock(returncode=0, stdout="  \n")
        result = _discover_git_root()
        assert result is None
