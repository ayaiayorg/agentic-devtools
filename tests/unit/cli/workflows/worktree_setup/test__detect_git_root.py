"""Tests for _detect_git_root."""

from unittest.mock import MagicMock, patch

from agentic_devtools.cli.workflows.worktree_setup import _detect_git_root


class TestDetectGitRoot:
    """Tests for _detect_git_root function."""

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_root_from_cmd_directory(self, mock_run):
        """Test detection when git.exe is in <root>\\cmd\\git.exe."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=r"C:\Program Files\Git\cmd\git.exe" + "\n",
        )

        result = _detect_git_root()

        assert result == r"C:\Program Files\Git"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_root_from_bin_directory(self, mock_run):
        """Test detection when git.exe is in <root>\\bin\\git.exe."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=r"C:\tools\Git\bin\git.exe" + "\n",
        )

        result = _detect_git_root()

        assert result == r"C:\tools\Git"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_fallback_when_where_fails(self, mock_run):
        """Test fallback when where.exe returns non-zero exit code."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        result = _detect_git_root()

        assert result == r"C:\Program Files\Git"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_fallback_when_where_not_found(self, mock_run):
        """Test fallback when where.exe is not found (FileNotFoundError)."""
        mock_run.side_effect = FileNotFoundError("where.exe not found")

        result = _detect_git_root()

        assert result == r"C:\Program Files\Git"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_uses_first_result_when_multiple_matches(self, mock_run):
        """Test that the first result is used when where.exe returns multiple paths."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=r"C:\Program Files\Git\cmd\git.exe" + "\n" + r"C:\tools\Git\cmd\git.exe" + "\n",
        )

        result = _detect_git_root()

        assert result == r"C:\Program Files\Git"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_fallback_for_unexpected_path_structure(self, mock_run):
        """Test fallback when git.exe is not in a recognised parent directory."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=r"C:\custom\path\git.exe" + "\n",
        )

        result = _detect_git_root()

        assert result == r"C:\Program Files\Git"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_fallback_when_stdout_is_empty(self, mock_run):
        """Test fallback when where.exe succeeds but returns empty stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        result = _detect_git_root()

        assert result == r"C:\Program Files\Git"

    @patch("agentic_devtools.cli.workflows.worktree_setup.subprocess.run")
    def test_returns_fallback_when_stdout_is_only_whitespace(self, mock_run):
        """Test fallback when where.exe succeeds but returns only whitespace/newline."""
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")

        result = _detect_git_root()

        assert result == r"C:\Program Files\Git"
