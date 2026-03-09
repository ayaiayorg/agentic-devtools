"""Tests for agentic_devtools.cli.git.agdt_branch.hash_object."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, hash_object


class TestHashObject:
    """Tests for the hash_object function."""

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_returns_blob_sha(self, mock_run):
        """hash_object returns the 40-char SHA from git hash-object."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="abc123def456abc123def456abc123def456abcd\n",
            stderr="",
        )
        sha = hash_object(b"hello world")
        assert sha == "abc123def456abc123def456abc123def456abcd"

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_calls_git_hash_object(self, mock_run):
        """hash_object invokes git hash-object -w -- <tmpfile>."""
        mock_run.return_value = MagicMock(returncode=0, stdout="abcd1234\n", stderr="")
        hash_object(b"data")
        args = mock_run.call_args[0][0]
        assert args[:3] == ["git", "hash-object", "-w"]
        assert "--" in args

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_failure(self, mock_run):
        """hash_object raises GitPlumbingError on non-zero exit."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a git repo")
        with pytest.raises(GitPlumbingError, match="git hash-object failed"):
            hash_object(b"data")

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_raises_on_empty_output(self, mock_run):
        """hash_object raises GitPlumbingError when stdout is empty."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        with pytest.raises(GitPlumbingError, match="empty output"):
            hash_object(b"data")

    @patch("agentic_devtools.cli.git.agdt_branch.run_safe")
    def test_strips_trailing_newline(self, mock_run):
        """Trailing whitespace is stripped from the SHA."""
        mock_run.return_value = MagicMock(returncode=0, stdout="  sha123  \n", stderr="")
        assert hash_object(b"x") == "sha123"
