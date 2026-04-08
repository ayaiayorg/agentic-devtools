"""Tests for resolve_review_threads_command CLI entry point."""

import json
from unittest.mock import patch

import pytest

from agentic_devtools import state
from agentic_devtools.cli.github.resolve_review_threads import (
    resolve_review_threads_command,
)

_MODULE = "agentic_devtools.cli.github.resolve_review_threads"


@pytest.fixture
def temp_state(tmp_path):
    """Create a temporary state directory with gh available by default."""
    with (
        patch.object(state, "get_state_dir", return_value=tmp_path),
        patch(f"{_MODULE}.shutil.which", return_value="/usr/bin/gh"),
    ):
        state.clear_state()
        yield tmp_path


class TestResolveReviewThreadsCommand:
    """Tests for resolve_review_threads_command."""

    @patch(f"{_MODULE}.resolve_review_threads")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_with_all_cli_args(self, mock_repo, mock_resolve, temp_state, capsys):
        """Parse CLI args and call resolve_review_threads."""
        mock_resolve.return_value = {"threadsResolved": 1, "verified": True}

        with patch("sys.argv", ["cmd", "--pr", "42", "--repo", "owner/repo", "--review-id", "999"]):
            resolve_review_threads_command()

        mock_resolve.assert_called_once_with(42, "owner/repo", 999, None)
        out = capsys.readouterr().out
        assert json.loads(out)["verified"] is True

    @patch(f"{_MODULE}.resolve_review_threads")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_with_comment_ids(self, mock_repo, mock_resolve, temp_state, capsys):
        """Parse comma-separated comment-ids."""
        mock_resolve.return_value = {"threadsResolved": 2, "verified": True}

        with patch("sys.argv", ["cmd", "--pr", "42", "--comment-ids", "10,20,30"]):
            resolve_review_threads_command()

        mock_resolve.assert_called_once_with(42, "owner/repo", None, [10, 20, 30])

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_missing_pr_exits(self, mock_repo, temp_state):
        """Exit 1 when PR number is not provided."""
        with patch("sys.argv", ["cmd", "--review-id", "999"]):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_missing_review_id_and_comment_ids_exits(self, mock_repo, temp_state):
        """Exit 1 when neither review-id nor comment-ids provided."""
        with patch("sys.argv", ["cmd", "--pr", "42"]):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1

    @patch(f"{_MODULE}.resolve_review_threads")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_pr_from_state(self, mock_repo, mock_resolve, temp_state, capsys):
        """Fall back to github.pull_request_number from state."""
        state.set_value("github.pull_request_number", 99)
        mock_resolve.return_value = {"threadsResolved": 0, "verified": True}

        with patch("sys.argv", ["cmd", "--review-id", "888"]):
            resolve_review_threads_command()

        mock_resolve.assert_called_once_with(99, "owner/repo", 888, None)

    @patch(f"{_MODULE}.resolve_review_threads")
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_review_id_from_state(self, mock_repo, mock_resolve, temp_state, capsys):
        """Fall back to github.copilot_review_id from state."""
        state.set_value("github.copilot_review_id", 777)
        mock_resolve.return_value = {"threadsResolved": 0, "verified": True}

        with patch("sys.argv", ["cmd", "--pr", "10"]):
            resolve_review_threads_command()

        mock_resolve.assert_called_once_with(10, "owner/repo", 777, None)

    @patch(f"{_MODULE}.resolve_review_threads", side_effect=RuntimeError("boom"))
    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_runtime_error_exits(self, mock_repo, mock_resolve, temp_state):
        """Exit 1 on RuntimeError from resolve_review_threads."""
        with patch("sys.argv", ["cmd", "--pr", "42", "--review-id", "999"]):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1

    def test_missing_gh_cli_exits(self, temp_state, capsys):
        """Exit 1 with helpful message when gh CLI is not installed."""
        with (
            patch(f"{_MODULE}.shutil.which", return_value=None),
            patch("sys.argv", ["cmd", "--pr", "42", "--review-id", "999"]),
        ):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "gh" in err
        assert "not installed" in err

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_invalid_pr_number_in_state_exits(self, mock_repo, temp_state, capsys):
        """Exit 1 when github.pull_request_number in state is non-numeric."""
        state.set_value("github.pull_request_number", "not-a-number")

        with patch("sys.argv", ["cmd", "--review-id", "999"]):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "github.pull_request_number" in err
        assert "integer" in err

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_invalid_review_id_in_state_exits(self, mock_repo, temp_state, capsys):
        """Exit 1 when github.copilot_review_id in state is non-numeric."""
        state.set_value("github.copilot_review_id", "not-a-number")

        with patch("sys.argv", ["cmd", "--pr", "42"]):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "github.copilot_review_id" in err
        assert "integer" in err

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_invalid_comment_ids_exits(self, mock_repo, temp_state, capsys):
        """Exit 1 when --comment-ids contains non-integer values."""
        with patch("sys.argv", ["cmd", "--pr", "42", "--comment-ids", "10,abc,30"]):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "integers" in err

    @patch(f"{_MODULE}.resolve_github_repo", return_value="owner/repo")
    def test_empty_comment_ids_exits(self, mock_repo, temp_state, capsys):
        """Exit 1 when --comment-ids parses to an empty list."""
        with patch("sys.argv", ["cmd", "--pr", "42", "--comment-ids", ",,,"]):
            with pytest.raises(SystemExit) as exc_info:
                resolve_review_threads_command()
        assert exc_info.value.code == 1
        err = capsys.readouterr().err
        assert "empty list" in err
