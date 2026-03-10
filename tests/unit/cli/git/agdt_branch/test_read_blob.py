"""Tests for agentic_devtools.cli.git.agdt_branch.read_blob."""

from unittest.mock import MagicMock, patch

import pytest

from agentic_devtools.cli.git.agdt_branch import GitPlumbingError, read_blob

_MOD = "agentic_devtools.cli.git.agdt_branch"


class TestReadBlob:
    """Tests for the read_blob function."""

    @patch(f"{_MOD}._run_plumbing")
    def test_returns_blob_content(self, mock_run):
        """read_blob returns stdout content from git cat-file."""
        mock_run.return_value = MagicMock(returncode=0, stdout="hello world\n", stderr="")
        assert read_blob("abc123") == "hello world\n"

    @patch(f"{_MOD}._run_plumbing")
    def test_calls_git_cat_file(self, mock_run):
        """read_blob invokes git cat-file -p with the blob SHA."""
        mock_run.return_value = MagicMock(returncode=0, stdout="content", stderr="")
        read_blob("blob_sha_123")
        mock_run.assert_called_once_with("cat-file", "-p", "blob_sha_123")

    @patch(f"{_MOD}._run_plumbing")
    def test_raises_on_failure(self, mock_run):
        """read_blob raises GitPlumbingError when git cat-file fails."""
        mock_run.return_value = MagicMock(returncode=128, stdout="", stderr="fatal: not a valid object")
        with pytest.raises(GitPlumbingError, match="git cat-file failed"):
            read_blob("bad_sha")

    @patch(f"{_MOD}._run_plumbing")
    def test_preserves_whitespace(self, mock_run):
        """read_blob does not strip whitespace from blob content."""
        mock_run.return_value = MagicMock(returncode=0, stdout="  spaces and\nnewlines  \n", stderr="")
        assert read_blob("sha") == "  spaces and\nnewlines  \n"

    @patch(f"{_MOD}._run_plumbing")
    def test_empty_blob_returns_empty_string(self, mock_run):
        """read_blob returns empty string for an empty blob."""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        assert read_blob("sha") == ""
