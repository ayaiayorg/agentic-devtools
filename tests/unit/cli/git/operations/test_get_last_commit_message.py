"""Tests for agentic_devtools.cli.git.operations.get_last_commit_message."""

from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

from agentic_devtools.cli.git.operations import get_last_commit_message

_RUN_GIT = "agentic_devtools.cli.git.operations.run_git"


class TestGetLastCommitMessage:
    """Tests for get_last_commit_message function."""

    def test_importable(self):
        """Test get_last_commit_message can be imported and is callable."""
        assert callable(get_last_commit_message)

    # -- non-zero returncode → None ------------------------------------------

    @patch(_RUN_GIT)
    def test_returns_none_on_nonzero_returncode(self, mock_run_git: MagicMock):
        """Non-zero returncode from git log should return None."""
        mock_run_git.return_value = CompletedProcess(
            args=["git", "log"], returncode=1, stdout="", stderr="fatal: error"
        )
        assert get_last_commit_message() is None

    @patch(_RUN_GIT)
    def test_returns_none_on_returncode_128(self, mock_run_git: MagicMock):
        """Returncode 128 (e.g. no commits yet) should return None."""
        mock_run_git.return_value = CompletedProcess(args=["git", "log"], returncode=128, stdout="", stderr="")
        assert get_last_commit_message() is None

    # -- successful result → stripped stdout ----------------------------------

    @patch(_RUN_GIT)
    def test_returns_stripped_message(self, mock_run_git: MagicMock):
        """Trailing newlines in stdout should be stripped."""
        mock_run_git.return_value = CompletedProcess(
            args=["git", "log"], returncode=0, stdout="feat: add widget\n\n", stderr=""
        )
        assert get_last_commit_message() == "feat: add widget"

    @patch(_RUN_GIT)
    def test_returns_multiline_message_stripped(self, mock_run_git: MagicMock):
        """Multi-line commit messages should be preserved but outer whitespace stripped."""
        msg = "feat: add widget\n\nDetailed description of the change."
        mock_run_git.return_value = CompletedProcess(args=["git", "log"], returncode=0, stdout=msg + "\n", stderr="")
        assert get_last_commit_message() == msg

    @patch(_RUN_GIT)
    def test_returns_message_with_leading_whitespace_stripped(self, mock_run_git: MagicMock):
        """Leading and trailing whitespace should be stripped."""
        mock_run_git.return_value = CompletedProcess(
            args=["git", "log"], returncode=0, stdout="  fix: typo  \n", stderr=""
        )
        assert get_last_commit_message() == "fix: typo"

    # -- empty / whitespace-only stdout → empty string ------------------------

    @patch(_RUN_GIT)
    def test_returns_empty_string_for_empty_stdout(self, mock_run_git: MagicMock):
        """Empty stdout with returncode 0 should return empty string, not None."""
        mock_run_git.return_value = CompletedProcess(args=["git", "log"], returncode=0, stdout="", stderr="")
        result = get_last_commit_message()
        assert result == ""
        assert result is not None

    @patch(_RUN_GIT)
    def test_returns_empty_string_for_whitespace_only_stdout(self, mock_run_git: MagicMock):
        """Whitespace-only stdout with returncode 0 should return empty string."""
        mock_run_git.return_value = CompletedProcess(args=["git", "log"], returncode=0, stdout="   \n\n  ", stderr="")
        result = get_last_commit_message()
        assert result == ""
        assert result is not None

    # -- run_git called correctly ---------------------------------------------

    @patch(_RUN_GIT)
    def test_calls_run_git_with_correct_args(self, mock_run_git: MagicMock):
        """Should invoke run_git with log -1 --format=%B and check=False."""
        mock_run_git.return_value = CompletedProcess(args=["git", "log"], returncode=0, stdout="msg\n", stderr="")
        get_last_commit_message()
        mock_run_git.assert_called_once_with("log", "-1", "--format=%B", check=False)
