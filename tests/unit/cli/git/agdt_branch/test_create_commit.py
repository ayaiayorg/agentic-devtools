"""Tests for agentic_devtools.cli.git.agdt_branch.create_commit."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, create_commit


class TestCreateCommit:
    """Tests for the create_commit function."""

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_returns_commit_sha(self, mock_run):
        """create_commit returns the SHA from git commit-tree."""
        mock_run.return_value = MagicMock(returncode=0, stdout="commit_sha_123\n", stderr="")
        sha = create_commit("tree_sha", "parent_sha", "msg")
        assert sha == "commit_sha_123"

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_includes_parent_flag(self, mock_run):
        """create_commit passes -p <parent> when parent_sha is provided."""
        mock_run.return_value = MagicMock(returncode=0, stdout="sha\n", stderr="")
        create_commit("tree", "parent", "message")
        cmd = mock_run.call_args[0][0]
        assert "-p" in cmd
        idx = cmd.index("-p")
        assert cmd[idx + 1] == "parent"

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_no_parent_flag_when_none(self, mock_run):
        """create_commit omits -p when parent_sha is None (root commit)."""
        mock_run.return_value = MagicMock(returncode=0, stdout="sha\n", stderr="")
        create_commit("tree", None, "initial commit")
        cmd = mock_run.call_args[0][0]
        assert "-p" not in cmd

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_includes_message(self, mock_run):
        """create_commit passes -m <message>."""
        mock_run.return_value = MagicMock(returncode=0, stdout="sha\n", stderr="")
        create_commit("tree", None, "my message")
        cmd = mock_run.call_args[0][0]
        assert "-m" in cmd
        idx = cmd.index("-m")
        assert cmd[idx + 1] == "my message"

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_failure(self, mock_run):
        """create_commit raises GitPlumbingError on non-zero exit."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="bad tree")
        with pytest.raises(GitPlumbingError, match="git commit-tree failed"):
            create_commit("bad_tree", None, "msg")

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_empty_output(self, mock_run):
        """create_commit raises GitPlumbingError when stdout is empty."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with pytest.raises(GitPlumbingError, match="empty output"):
            create_commit("tree", None, "msg")
