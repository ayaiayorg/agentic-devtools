"""Tests for GetMainRepoRoot."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import (
    get_main_repo_root,
)


class TestGetMainRepoRoot:
    """Tests for get_main_repo_root function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_main_repo_root_from_worktree(self, mock_run):
        """Test returning main repo root when in a worktree."""
        # Mock subprocess to return a .git directory path (indicating worktree)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="/repos/main-repo/.git/worktrees/DFLY-1234\n",
        )

        result = get_main_repo_root()

        # Result should be parent of .git directory
        assert "main-repo" in result or "repos" in result
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert call_args[0][0] == ["git", "rev-parse", "--git-common-dir"]

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_main_repo_root_from_main_repo(self, mock_run):
        """Test returning main repo root when in the main repo."""
        # Mock subprocess to return .git (indicating main repo)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=".git\n",
        )

        with patch("os.getcwd", return_value="/repos/main-repo"):
            result = get_main_repo_root()

        # Result should contain the repo path
        assert result is not None
        assert "main-repo" in result or "repos" in result

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_file_not_found(self, mock_run):
        """Test returning None when git not found."""
        mock_run.side_effect = FileNotFoundError("git not found")

        result = get_main_repo_root()

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_os_error(self, mock_run):
        """Test returning None on OS error."""
        mock_run.side_effect = OSError("Some OS error")

        result = get_main_repo_root()

        assert result is None

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_none_on_nonzero_return_code(self, mock_run):
        """Test returning None when git returns non-zero."""
        mock_run.return_value = MagicMock(
            returncode=128,
            stdout="",
            stderr="fatal: not a git repository",
        )

        result = get_main_repo_root()

        assert result is None
