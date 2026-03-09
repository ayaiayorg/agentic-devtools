"""Tests for agentic_devtools.cli.git.agdt_branch.build_tree."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, build_tree


class TestBuildTree:
    """Tests for the build_tree function."""

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_returns_tree_sha(self, mock_run):
        """build_tree returns the SHA from git write-tree."""
        # update-index succeeds, then write-tree returns SHA
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # update-index
            MagicMock(returncode=0, stdout="tree_sha_abc\n", stderr=""),  # write-tree
        ]
        sha = build_tree({"file.txt": "blob_sha_1"})
        assert sha == "tree_sha_abc"

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_calls_update_index_per_entry(self, mock_run):
        """build_tree calls git update-index for each entry in sorted order."""
        mock_run.return_value = MagicMock(returncode=0, stdout="tree\n", stderr="")
        build_tree({"b.txt": "sha_b", "a.txt": "sha_a"})

        # First two calls are update-index (sorted: a.txt, b.txt)
        calls = mock_run.call_args_list
        assert len(calls) == 3  # 2 × update-index + 1 × write-tree

        first_cmd = calls[0][0][0]
        assert "update-index" in first_cmd
        assert "100644,sha_a,a.txt" in first_cmd

        second_cmd = calls[1][0][0]
        assert "100644,sha_b,b.txt" in second_cmd

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_uses_temp_index(self, mock_run):
        """build_tree passes GIT_INDEX_FILE env var."""
        mock_run.return_value = MagicMock(returncode=0, stdout="tree\n", stderr="")
        build_tree({"f.txt": "sha"})

        for c in mock_run.call_args_list:
            env = c[1].get("env") or c.kwargs.get("env")
            assert env is not None
            assert "GIT_INDEX_FILE" in env

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_update_index_failure(self, mock_run):
        """build_tree raises GitPlumbingError if update-index fails."""
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        with pytest.raises(GitPlumbingError, match="git update-index failed"):
            build_tree({"f.txt": "sha"})

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_write_tree_failure(self, mock_run):
        """build_tree raises GitPlumbingError if write-tree fails."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # update-index OK
            MagicMock(returncode=1, stdout="", stderr="write-tree error"),
        ]
        with pytest.raises(GitPlumbingError, match="git write-tree failed"):
            build_tree({"f.txt": "sha"})

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_write_tree_empty_output(self, mock_run):
        """build_tree raises GitPlumbingError if write-tree returns empty."""
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # update-index OK
            MagicMock(returncode=0, stdout="", stderr=""),  # write-tree empty
        ]
        with pytest.raises(GitPlumbingError, match="write-tree returned empty"):
            build_tree({"f.txt": "sha"})

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_empty_entries(self, mock_run):
        """build_tree with empty dict only calls write-tree."""
        mock_run.return_value = MagicMock(returncode=0, stdout="empty_tree\n", stderr="")
        sha = build_tree({})
        assert sha == "empty_tree"
        # Only write-tree should be called (no update-index)
        assert mock_run.call_count == 1
