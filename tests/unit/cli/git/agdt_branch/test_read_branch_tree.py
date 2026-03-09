"""Tests for agentic_devtools.cli.git.agdt_branch.read_branch_tree."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, read_branch_tree


class TestReadBranchTree:
    """Tests for the read_branch_tree function."""

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_returns_dict(self, mock_run):
        """read_branch_tree returns a {path: blob_sha} dict."""
        mock_run.side_effect = [
            # rev-parse succeeds
            MagicMock(returncode=0, stdout="abc123\n", stderr=""),
            # ls-tree output
            MagicMock(
                returncode=0,
                stdout=("100644 blob sha1\tfile.txt\n100644 blob sha2\tdir/nested.txt\n"),
                stderr="",
            ),
        ]
        result = read_branch_tree("my-branch")
        assert result == {"file.txt": "sha1", "dir/nested.txt": "sha2"}

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_nonexistent_branch_returns_empty_dict(self, mock_run):
        """read_branch_tree returns {} when the branch does not exist."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a valid ref")
        result = read_branch_tree("no-such-branch")
        assert result == {}

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_empty_tree_returns_empty_dict(self, mock_run):
        """read_branch_tree returns {} for an empty tree (no files)."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        result = read_branch_tree("empty-branch")
        assert result == {}

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_ls_tree_failure(self, mock_run):
        """read_branch_tree raises GitPlumbingError if ls-tree fails."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc123\n", stderr=""),
            MagicMock(returncode=1, stdout="", stderr="ls-tree error"),
        ]
        with pytest.raises(GitPlumbingError, match="git ls-tree failed"):
            read_branch_tree("branch")

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_resolves_ref_with_full_path(self, mock_run):
        """read_branch_tree uses refs/heads/<branch> for rev-parse."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="abc\n", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]
        read_branch_tree("my-branch")
        rev_cmd = mock_run.call_args_list[0][0][0]
        assert rev_cmd == ["git", "rev-parse", "--verify", "refs/heads/my-branch"]

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_rev_parse_empty_stdout_returns_empty_dict(self, mock_run):
        """read_branch_tree returns {} when rev-parse returns empty stdout."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = read_branch_tree("branch")
        assert result == {}
