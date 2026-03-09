"""Tests for agentic_devtools.cli.git.agdt_branch.update_ref."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, update_ref


class TestUpdateRef:
    """Tests for the update_ref function."""

    @patch("agentic_devtools.cli.git.agdt_branch._run_plumbing")
    def test_success(self, mock_run):
        """update_ref completes without error on success."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        update_ref("my-branch", "abc123")  # should not raise

    @patch("agentic_devtools.cli.git.agdt_branch._run_plumbing")
    def test_calls_git_update_ref(self, mock_run):
        """update_ref invokes _run_plumbing with update-ref refs/heads/<branch> <sha>."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        update_ref("my-branch", "abc123")
        args = mock_run.call_args[0]
        assert args == ("update-ref", "refs/heads/my-branch", "abc123")

    @patch("agentic_devtools.cli.git.agdt_branch._run_plumbing")
    def test_raises_on_failure(self, mock_run):
        """update_ref raises GitPlumbingError on non-zero exit."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="bad ref")
        with pytest.raises(GitPlumbingError, match="git update-ref failed"):
            update_ref("branch", "sha")
